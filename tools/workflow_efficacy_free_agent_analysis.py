"""Fail-closed descriptive analysis for 60 keyless synthetic agent observations.

Never promote this exploratory pilot to the historical-FAR efficacy study.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import random
from pathlib import Path
from statistics import mean
from tools.workflow_efficacy_internal_fixtures import fingerprint
from tools.workflow_efficacy_free_agent import MODEL, OPENCODE_VERSION, order_for, instructions

def analyze(folder):
    files = sorted(Path(folder).rglob("pair-*.json"))
    rows = []
    errors = []
    if len(files) != 30:
        errors.append("WRONG_PAIR_FILE_COUNT")
    for path in files:
        try:
            values = json.loads(path.read_text())
            if not isinstance(values, list) or len(values) != 2:
                raise ValueError("not two observations")
            rows.extend(values)
        except (OSError, ValueError, TypeError) as exc:
            errors.append("INVALID_PAIR_FILE:" + path.name + ":" + type(exc).__name__)
    keyed = {}
    for row in rows:
        if not isinstance(row, dict):
            errors.append("INVALID_RECORD_TYPE")
            continue
        t, arm = row.get("task_id"), row.get("arm")
        if t not in {f"FWE-{i+1:03d}" for i in range(30)} or arm not in ("control","treatment"):
            errors.append("UNREGISTERED_RUN")
            continue
        key = (t, arm)
        if key in keyed:
            errors.append("DUPLICATE_RUN")
        keyed[key] = row
        exp_sha = hashlib.sha256(instructions(arm)).hexdigest()
        if row.get("instructions_sha256") != exp_sha or row.get("corpus_hash") != fingerprint():
            errors.append("SNAPSHOT_MISMATCH:" + t + ":" + arm)
        if row.get("model_alias") != MODEL or row.get("opencode_version") != OPENCODE_VERSION:
            errors.append("MODEL_OR_HARNESS_ALIAS_DRIFT:" + t + ":" + arm)
        if not isinstance(row.get("model_steps"), int) or row["model_steps"] <= 0:
            errors.append("NO_MODEL_STEPS:" + t + ":" + arm)
        if row.get("reported_cost_usd") != 0:
            errors.append("NONFREE_MODEL_CHARGE:" + t + ":" + arm)
        if row.get("grader_status") != "EXECUTED" or row.get("grader_exit_code") not in (0, 1):
            errors.append("MISSING_OR_UNEXECUTED_GRADER:" + t + ":" + arm)
        if row.get("outcome") not in ("SUCCESS", "FAILURE"):
            errors.append("INVALID_OUTCOME:" + t + ":" + arm)
        if row.get("outcome") == "SUCCESS" and row.get("grader_exit_code") != 0:
            errors.append("CONTRADICTORY_SUCCESS_WITH_FAILED_GRADER:" + t + ":" + arm)
        if row.get("unauthorized_changes"):
            errors.append("AGENT_MODIFIED_UNAUTHORIZED_FILES:" + t + ":" + arm)
        # Source, events and grader output are retained for independent replay.
        evidence = Path(folder) / "evidence" / (t + "-" + arm)
        file_hashes = {
            "submitted-solution.py": "source_after_sha256",
            "agent-events.ndjson": "raw_event_stream_sha256",
            "grader-trace.txt": "grader_trace_hash",
        }
        for filename, field in file_hashes.items():
            path = evidence / filename
            if not path.is_file():
                errors.append("MISSING_REPLAY_ARTIFACT:" + t + ":" + arm + ":" + filename)
            elif hashlib.sha256(path.read_bytes()).hexdigest() != row.get(field):
                errors.append("REPLAY_ARTIFACT_HASH_MISMATCH:" + t + ":" + arm + ":" + filename)
    expected={(f"FWE-{i+1:03d}",arm) for i in range(30) for arm in ("control","treatment")}
    if set(keyed) != expected:
        errors.append("MISSING_EXPERIMENT_SLOTS")
    for i in range(30):
        case_id = f"FWE-{i+1:03d}"
        if any((case_id, arm) not in keyed for arm in order_for(i)):
            errors.append("MISSING_COUNTERBALANCED_PAIR:" + case_id)
    base = {"schema":"far-workflow-free-agent-analysis/0.2","experiment":"exploratory_internal_synthetic_tasks",
            "expected_pairs":30, "expected_runs":60,
            "observed_records":len(rows), "unique_slots":len(keyed),
            "corpus_hash":fingerprint(), "model_alias":MODEL,
            "provider_build_immutable":False,
            "historical_pr_comparison_executed":False,
            "external_independence":False, "errors":errors}
    if errors:
        return dict(base,status="INCOMPLETE_OR_INVALID",claim="NO_VALID_EFFECT_ESTIMATE")
    differences=[]
    for i in range(30):
        t=f"FWE-{i+1:03d}"
        c=keyed[(t,"control")]["outcome"]=="SUCCESS"
        v=keyed[(t,"treatment")]["outcome"]=="SUCCESS"
        differences.append(int(v)-int(c))
    pos=sum(v==1 for v in differences)
    neg=sum(v==-1 for v in differences)
    disc=pos+neg
    p=min(1.0,2*sum(math.comb(disc,k) for k in range(min(pos,neg)+1))/(2**disc)) if disc else 1.0
    rng=random.Random(60520261102)
    boot=sorted(mean(rng.choice(differences) for _ in range(30)) for _ in range(10000))
    def delta(key):
        return mean(keyed[(f"FWE-{i+1:03d}","treatment")][key] -
                    keyed[(f"FWE-{i+1:03d}","control")][key] for i in range(30))
    return dict(base,status="COMPLETE_60_EXPLORATORY_AGENT_RUNS",
                control_success=sum(keyed[(f"FWE-{i+1:03d}","control")]["outcome"]=="SUCCESS" for i in range(30)),
                treatment_success=sum(keyed[(f"FWE-{i+1:03d}","treatment")]["outcome"]=="SUCCESS" for i in range(30)),
                paired_success_delta=mean(differences),
                paired_bootstrap_interval_95pct=[boot[249],boot[9749]],
                discordant_treatment_wins=pos,discordant_control_wins=neg,
                exact_sign_test_two_sided_p=p,
                mean_elapsed_delta_seconds=delta("elapsed_seconds"),
                mean_input_token_delta=delta("input_tokens"),
                mean_output_token_delta=delta("output_tokens"),
                claim="DESCRIPTIVE_INTERNAL_RESULT_ONLY_NO_IMMUTABLE_MODEL_BUILD_OR_EXTERNAL_VALIDATION")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--results",required=True,type=Path)
    ap.add_argument("--output",type=Path)
    args=ap.parse_args()
    result=analyze(args.results)
    text=json.dumps(result,indent=2,sort_keys=True)+"\n"
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(text)
    return 0 if result["status"]=="COMPLETE_60_EXPLORATORY_AGENT_RUNS" else 2

if __name__=="__main__":
    raise SystemExit(main())
