"""Fail-closed analysis of the frozen finite-corpus scripted-repair pilot.

Retained provider responses, submitted source and trusted output comparisons are
reconciled independently of the runner's summary. This is internal descriptive
evidence; neither model execution nor a statistical diagnostic proves efficacy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import subprocess
from pathlib import Path
from statistics import mean

from tools.workflow_efficacy_internal_fixtures import fingerprint, task
from tools.workflow_efficacy_free_agent import (
    CANDIDATE_STARTED, HARNESS_VERSION, MAX_CANDIDATE_OUTPUT_BYTES,
    MODEL, MODEL_DIGEST, ROOT,
    candidate_output, extract_patch, instructions, order_for,
)

COMPLETE = "COMPLETE_60_EXPLORATORY_SCRIPTED_REPAIR_RUNS"
OBSERVATION_SCHEMA = "far-workflow-scripted-repair-observation/0.4"


def _reject_constant(value):
    raise ValueError("nonfinite JSON constant: " + value)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result


def _json_loads(text):
    try:
        return json.loads(text, parse_constant=_reject_constant,
                          object_pairs_hook=_unique_object)
    except (RecursionError, OverflowError) as exc:
        raise ValueError("JSON exceeds decoder resource limits") from exc


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def execution_commit():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                   text=True, timeout=15).strip()


def _finite_nonnegative(value):
    try:
        return type(value) in (int, float) and math.isfinite(value) and value >= 0
    except (TypeError, OverflowError):
        return False


def _validate_grade(trace, case, row, error):
    """Recompute each host-recorded comparison from its retained output."""
    if not isinstance(trace, dict) or trace.get("schema") != "far-isolated-output-grade/1":
        error("INVALID_GRADER_TRACE_SCHEMA")
        return False
    comparisons = trace.get("comparisons")
    expected = [(group, i, example) for group in ("public", "hidden")
                for i, example in enumerate(case[group])]
    if not isinstance(comparisons, list) or len(comparisons) != len(expected):
        error("WRONG_GRADER_COMPARISON_COUNT")
        return False
    statuses = []
    for comparison, (group, index, example) in zip(comparisons, expected):
        if not isinstance(comparison, dict):
            error("INVALID_GRADER_COMPARISON")
            continue
        if comparison.get("group") != group or type(comparison.get("index")) is not int or comparison["index"] != index:
            error("GRADER_COMPARISON_ORDER_MISMATCH")
        status = comparison.get("status")
        if type(status) is not str or status not in ("PASS", "FAILURE", "RESOURCE_LIMIT", "OUTPUT_LIMIT", "INFRA_FAILURE"):
            error("INVALID_GRADER_COMPARISON_STATUS")
            continue
        statuses.append(status)
        if status == "INFRA_FAILURE":
            error("MISSING_OR_UNEXECUTED_GRADER")
            continue
        stderr = comparison.get("stderr")
        stdout = comparison.get("stdout")
        if not isinstance(stdout, str) or not isinstance(stderr, str):
            error("INVALID_GRADER_PROCESS_RESULT")
        started = ((isinstance(stdout, str) and stdout.startswith(CANDIDATE_STARTED + "\n"))
                   or (isinstance(stderr, str) and CANDIDATE_STARTED in stderr))
        if not started:
            error("GRADER_CANDIDATE_NOT_STARTED")
        counts = [comparison.get(field) for field in
                  ("stdout_bytes_observed", "stderr_bytes_observed")]
        counts_valid = all(type(count) is int and count >= 0 for count in counts)
        if not counts_valid:
            error("INVALID_GRADER_OUTPUT_COUNTS")
        over_limit = counts_valid and any(count > MAX_CANDIDATE_OUTPUT_BYTES for count in counts)
        expected_timeout = status == "RESOURCE_LIMIT"
        expected_output_limit = status == "OUTPUT_LIMIT"
        if (comparison.get("timed_out") is not expected_timeout
                or comparison.get("output_limited") is not expected_output_limit
                or (counts_valid and over_limit != expected_output_limit)):
            error("GRADER_LIMIT_EVIDENCE_MISMATCH")
        code = comparison.get("exit_code")
        if status in ("RESOURCE_LIMIT", "OUTPUT_LIMIT"):
            if code is not None:
                error("INVALID_LIMIT_EXIT_CODE")
            continue
        if type(code) is not int or not isinstance(stdout, str):
            error("INVALID_GRADER_PROCESS_RESULT")
            continue
        passed = False
        if code == 0:
            try:
                passed = candidate_output(stdout) == example["expected"]
            except (ValueError, TypeError, RecursionError, OverflowError):
                pass
        if (status == "PASS") != passed:
            error("GRADER_COMPARISON_VERDICT_MISMATCH")
    executed = len(statuses) == len(expected) and "INFRA_FAILURE" not in statuses
    success = executed and all(status == "PASS" for status in statuses)
    if trace.get("executed") is not executed or trace.get("success") is not success:
        error("GRADER_TRACE_SUMMARY_MISMATCH")
    expected_code = (0 if success else 1) if executed else None
    if (row.get("grader_status") != ("EXECUTED" if executed else "INFRA_FAILURE")
            or row.get("grader_exit_code") != expected_code
            or type(row.get("grader_exit_code")) is not int):
        error("GRADER_RECORD_MISMATCH")
    return success


def _validate_artifacts(folder, case, row, error):
    evidence = Path(folder) / "evidence" / (row["task_id"] + "-" + row["arm"])
    data = {}
    for filename, field in {
        "submitted-solution.py": "source_after_sha256",
        "agent-events.ndjson": "raw_event_stream_sha256",
        "grader-trace.txt": "grader_trace_hash",
    }.items():
        try:
            data[filename] = (evidence / filename).read_bytes()
        except OSError:
            error("MISSING_REPLAY_ARTIFACT:" + filename)
            continue
        if _hash(data[filename]) != row.get(field):
            error("REPLAY_ARTIFACT_HASH_MISMATCH:" + filename)
    try:
        raw = _json_loads(data["agent-events.ndjson"])
        if not isinstance(raw, dict):
            raise ValueError("provider response is not an object")
        message = raw.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise ValueError("missing generated content")
        if raw.get("done") is not True or raw.get("error"):
            raise ValueError("incomplete provider response")
        if "model" in raw and raw["model"] != MODEL.removeprefix("ollama/"):
            raise ValueError("unexpected provider model")
        for raw_key, row_key in (("prompt_eval_count", "input_tokens"), ("eval_count", "output_tokens")):
            if type(raw.get(raw_key)) is not int or raw[raw_key] <= 0 or raw[raw_key] != row.get(row_key):
                raise ValueError("invalid or inconsistent token counters")
        patch = extract_patch(message["content"])
        if row.get("patch_parsed") is not (patch is not None):
            error("PATCH_PARSE_MISMATCH")
        expected_source = (patch if patch is not None else case["source"]).encode()
        if data.get("submitted-solution.py") != expected_source:
            error("SUBMISSION_PROVIDER_RESPONSE_MISMATCH")
    except (KeyError, UnicodeError, ValueError, TypeError, RecursionError, OverflowError):
        error("INVALID_OR_UNRECONCILED_PROVIDER_RESPONSE")
    try:
        trace = _json_loads(data["grader-trace.txt"])
        grade_success = _validate_grade(trace, case, row, error)
    except (KeyError, UnicodeError, ValueError, TypeError, RecursionError, OverflowError):
        error("INVALID_GRADER_TRACE")
        grade_success = False
    expected_success = bool(grade_success and row.get("patch_parsed") is True
                            and row.get("source_after_sha256") != _hash(case["source"].encode())
                            and row.get("unauthorized_changes") == [])
    if row.get("outcome") != ("SUCCESS" if expected_success else "FAILURE"):
        error("OUTCOME_EVIDENCE_MISMATCH")


def analyze(folder):
    files = sorted(Path(folder).rglob("pair-*.json"))
    rows, errors, keyed = [], [], {}
    corpus_hash = fingerprint()
    source_commit = execution_commit()
    arm_hashes = {arm: _hash(instructions(arm)) for arm in ("control", "treatment")}
    if len(files) != 30:
        errors.append("WRONG_PAIR_FILE_COUNT")
    for path in files:
        try:
            values = _json_loads(path.read_bytes())
            if not isinstance(values, list) or len(values) != 2:
                raise ValueError("not two observations")
            match = re.fullmatch(r"pair-(0|[1-9][0-9]?)\.json", path.name)
            if not match or int(match[1]) >= 30:
                errors.append("UNREGISTERED_PAIR_FILE:" + path.name)
            else:
                index = int(match[1])
                if (any(not isinstance(v, dict) or v.get("task_id") != task(index)["task_id"] for v in values)
                        or [v.get("arm") for v in values if isinstance(v, dict)] != list(order_for(index))):
                    errors.append("PAIR_IDENTITY_OR_ORDER_MISMATCH:" + path.name)
            rows.extend(values)
        except (OSError, UnicodeError, ValueError, TypeError) as exc:
            errors.append("INVALID_PAIR_FILE:" + path.name + ":" + type(exc).__name__)
    registered = {task(i)["task_id"]: task(i) for i in range(30)}
    for row in rows:
        if not isinstance(row, dict):
            errors.append("INVALID_RECORD_TYPE")
            continue
        t, arm = row.get("task_id"), row.get("arm")
        if type(t) is not str or t not in registered or type(arm) is not str or arm not in ("control", "treatment"):
            errors.append("UNREGISTERED_RUN")
            continue
        def error(message):
            errors.append(message + ":" + t + ":" + arm)
        key = (t, arm)
        if key in keyed:
            error("DUPLICATE_RUN")
        keyed[key] = row
        case = registered[t]
        if row.get("schema") != OBSERVATION_SCHEMA:
            error("UNKNOWN_OBSERVATION_SCHEMA")
        if row.get("execution_commit") != source_commit:
            error("EXECUTION_COMMIT_MISMATCH")
        if row.get("instructions_sha256") != arm_hashes[arm] or row.get("corpus_hash") != corpus_hash:
            error("SNAPSHOT_MISMATCH")
        if row.get("model_digest") != MODEL_DIGEST:
            error("UNPINNED_LOCAL_MODEL_DIGEST")
        if row.get("model_alias") != MODEL or row.get("harness_version") != HARNESS_VERSION:
            error("MODEL_OR_HARNESS_ALIAS_DRIFT")
        if row.get("source_before_sha256") != _hash(case["source"].encode()):
            error("STARTER_SOURCE_MISMATCH")
        if type(row.get("model_steps")) is not int or row["model_steps"] != 1:
            error("NOT_EXACTLY_ONE_MODEL_STEP")
        if type(row.get("error_events")) is not int or row["error_events"] != 0:
            error("INCOMPLETE_PROVIDER_SESSION")
        if row.get("timeout") is not False or type(row.get("cli_exit_code")) is not int or row["cli_exit_code"] != 0:
            error("INCOMPLETE_MODEL_EXECUTION")
        if not _finite_nonnegative(row.get("reported_cost_usd")) or row["reported_cost_usd"] != 0:
            error("NONFREE_OR_INVALID_MODEL_CHARGE")
        for metric in ("elapsed_seconds", "input_tokens", "output_tokens"):
            if not _finite_nonnegative(row.get(metric)):
                error("INVALID_NUMERIC_METRIC:" + metric)
        for metric in ("input_tokens", "output_tokens"):
            if type(row.get(metric)) is not int or row[metric] <= 0:
                error("INVALID_TOKEN_COUNT:" + metric)
        if type(row.get("patch_parsed")) is not bool:
            error("INVALID_PATCH_PARSE_FLAG")
        changes = row.get("unauthorized_changes")
        if not isinstance(changes, list) or any(type(change) is not str for change in changes):
            error("INVALID_UNAUTHORIZED_CHANGE_RECORD")
        if row.get("grader_status") != "EXECUTED" or type(row.get("grader_exit_code")) is not int or row["grader_exit_code"] not in (0, 1):
            error("MISSING_OR_UNEXECUTED_GRADER")
        _validate_artifacts(folder, case, row, error)
    expected = {(t, arm) for t in registered for arm in ("control", "treatment")}
    if set(keyed) != expected:
        errors.append("MISSING_EXPERIMENT_SLOTS")
    base = {
        "schema": "far-workflow-scripted-repair-analysis/0.4",
        "experiment": "exploratory_local_model_scripted_repair",
        "expected_pairs": 30, "expected_runs": 60,
        "observed_records": len(rows), "unique_slots": len(keyed),
        "corpus_hash": corpus_hash, "model_alias": MODEL,
        "model_digest": MODEL_DIGEST, "execution_commit": source_commit,
        "model_weights_identity_pinned": True,
        "historical_pr_comparison_executed": False,
        "autonomous_agent_efficacy_measured": False,
        "external_independence": False, "population_efficacy_established": False,
        "errors": errors,
    }
    if errors:
        return dict(base, status="INCOMPLETE_OR_INVALID", claim="NO_VALID_EFFECT_ESTIMATE")
    differences = [int(keyed[(t, "treatment")]["outcome"] == "SUCCESS") -
                   int(keyed[(t, "control")]["outcome"] == "SUCCESS") for t in registered]
    pos, neg = sum(v == 1 for v in differences), sum(v == -1 for v in differences)
    disc = pos + neg
    p = min(1.0, 2 * sum(math.comb(disc, k) for k in range(min(pos, neg) + 1)) / (2 ** disc)) if disc else 1.0
    rng = random.Random(60520261102)
    boot = sorted(mean(rng.choice(differences) for _ in range(30)) for _ in range(10000))
    def delta(key):
        return mean(keyed[(t, "treatment")][key] - keyed[(t, "control")][key] for t in registered)
    return dict(
        base, status=COMPLETE,
        control_success=sum(keyed[(t, "control")]["outcome"] == "SUCCESS" for t in registered),
        treatment_success=sum(keyed[(t, "treatment")]["outcome"] == "SUCCESS" for t in registered),
        paired_success_delta=mean(differences),
        discordant_treatment_wins=pos, discordant_control_wins=neg,
        exploratory_paired_bootstrap_interval_95pct=[boot[249], boot[9749]],
        exploratory_exact_sign_test_two_sided_p=p,
        statistical_diagnostic_limits="Fixed authored corpus, deterministic generations, and ten shared task families; resampling/sign-test diagnostics do not establish population uncertainty or significance.",
        mean_generation_elapsed_delta_seconds=delta("elapsed_seconds"),
        generation_timing_scope="Provider request only; excludes model installation, task setup and grading.",
        mean_input_token_delta=delta("input_tokens"),
        mean_output_token_delta=delta("output_tokens"),
        claim="DESCRIPTIVE_INTERNAL_FINITE_CORPUS_SCRIPTED_REPAIR_RESULT_ONLY",
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = analyze(args.results)
    text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    return 0 if result["status"] == COMPLETE else 2


if __name__ == "__main__":
    raise SystemExit(main())
