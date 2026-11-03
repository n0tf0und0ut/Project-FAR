"""Research sidecar for model-independent agent reliability evidence.

This is an audit projection, not another agent runtime or performance study.
Historical adapters delegate grades and tool execution to the existing replay
verifier. Hash consistency and local replay do not attest that inference ran on
the declared hardware, or make project-authored adjudication independent.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import re
import subprocess
import zipfile
from datetime import datetime
from fractions import Fraction
from pathlib import Path, PurePosixPath

from mechanization.far_mechanization.compare_adjudication import normalize_package
from tools import tool_agent_reliability as replay

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "far-agent-evidence/0.1"
V03_ARCHIVE = "research/tool-agent-reliability/result/v0.3/evidence-v0.3.zip"
V03_ARCHIVE_SHA = "b4e1ccd17a46db8f91ccee29232853bdd6ba5881a1f6c747351d2dfc242a7809"
V03_SOURCE = "6c382c798df0a95824b79e76263318865ee24c68"
V02_SOURCE = "6c6a62eab835de143216130bbb5050c4e05ef16c"
HISTORICAL_BASE = "c7456b469f9dfe88b92d0fc7a211e5c9ed64de61"
BOUNDARIES = [
    "Authored virtual-file tasks; no deployment-distribution or general reliability claim.",
    "No FAR/no-FAR causal contrast; no commercial or human-outcome measurement.",
    "Repeated trajectories are not independent behavioral samples.",
    "Replay checks retained requests, responses, tools and grades; it is not trusted execution attestation.",
    "Ground truth and adjudication are Project-FAR-authored and not externally independent.",
    "Unobserved diagnosis, severity, human effort, infrastructure cost and billing remain unknown.",
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return replay.encoded(value)


def _safe_path(path):
    p = PurePosixPath(path) if isinstance(path, str) else None
    if p is None or not path or not p.parts or p.is_absolute() or str(p) != path or any(x in (".", "..") for x in p.parts) or "\\" in path:
        raise ValueError("unsafe artifact path")
    return path


def _read_file(root, path):
    path = _safe_path(path)
    root = Path(root).resolve()
    target = root / path
    if target.is_symlink() or not target.resolve().is_relative_to(root):
        raise ValueError("artifact escapes root")
    if not target.is_file():
        raise ValueError("artifact must be a regular file")
    if target.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("artifact too large")
    return target.read_bytes()


def read_artifact(root, reference):
    """Read exact bytes without extracting ZIP members or following paths."""
    validate_reference(reference)
    raw = _read_file(root, reference["path"])
    members = reference["members"]
    for member in members:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            if len(archive.namelist()) != len(set(archive.namelist())):
                raise ValueError("duplicate archive member")
            info = archive.getinfo(member)
            if info.file_size > 16 * 1024 * 1024:
                raise ValueError("archive member too large")
            raw = archive.read(member)
    if sha(raw) != reference["sha256"]:
        raise ValueError("artifact digest mismatch")
    return raw


def validate_reference(reference):
    if not isinstance(reference, dict) or set(reference) != {"path", "members", "sha256"}:
        raise ValueError("invalid artifact reference")
    _safe_path(reference["path"])
    members = reference["members"]
    if not isinstance(members, list) or len(members) > 2:
        raise ValueError("invalid archive member chain")
    for member in members:
        _safe_path(member)
    if not isinstance(reference["sha256"], str) or not re.fullmatch("[a-f0-9]{64}", reference["sha256"]):
        raise ValueError("invalid artifact digest")


def artifact(path, raw, members=()):
    return {"path": path, "members": list(members), "sha256": sha(raw)}


def _identity(identifier, version, details, provenance, *, unknown_reason=None):
    """Common identity envelope; retained provider-specific fields stay in details."""
    missing = {key: {"reason": unknown_reason, "evidence": copy.deepcopy(provenance)}
               for key, value in (("id", identifier), ("version", version)) if value is None}
    return {"id": identifier, "version": version, "details": copy.deepcopy(details),
            "provenance": copy.deepcopy(provenance), "unknown_fields": missing}


def validate_identity(value):
    expected = {"id", "version", "details", "provenance", "unknown_fields"}
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("missing or unsupported identity envelope fields")
    placeholders = {"unknown", "unidentified", "unspecified", "none", "null", "pending", "todo", "tbd"}
    for key in ("id", "version"):
        item = value[key]
        if item is not None and (not isinstance(item, str) or not item.strip()
                                 or len(item) > 2048 or item.strip().lower() in placeholders):
            raise ValueError("invalid identity " + key)
    if not isinstance(value["details"], dict):
        raise ValueError("identity details must be an object")
    refs = value["provenance"]
    if not isinstance(refs, list) or not refs:
        raise ValueError("identity requires provenance references")
    for ref in refs:
        validate_reference(ref)
    missing = {key for key in ("id", "version") if value[key] is None}
    if not isinstance(value["unknown_fields"], dict) or set(value["unknown_fields"]) != missing:
        raise ValueError("unknown identity fields require exact reasons")
    for explanation in value["unknown_fields"].values():
        if not isinstance(explanation, dict) or set(explanation) != {"reason", "evidence"}:
            raise ValueError("invalid unknown identity explanation")
        reason = explanation["reason"]
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 2048:
            raise ValueError("unknown identity requires a reason")
        if not isinstance(explanation["evidence"], list) or not explanation["evidence"]:
            raise ValueError("unknown identity requires retained provenance")
        for ref in explanation["evidence"]:
            validate_reference(ref)


def slot_declaration(protocol, eligible):
    return {"source": copy.deepcopy(protocol), "slots_sha256": sha(canonical(eligible))}


def validate_exposure(exposure):
    """Validate declarations before arithmetic; source correspondence needs replay."""
    if not isinstance(exposure, dict) or exposure.get("kind") not in {"registered_slots", "incidents_only"}:
        raise ValueError("invalid exposure kind")
    eligible = exposure.get("eligible_slots")
    if not isinstance(eligible, list) or any(not isinstance(s, str) or not s.strip() or len(s) > 2048 for s in eligible) or len(eligible) != len(set(eligible)):
        raise ValueError("invalid or duplicate exposure slots")
    if exposure["kind"] == "incidents_only":
        if eligible or exposure.get("slot_declaration") is not None:
            raise ValueError("incidents cannot invent exposure slots")
        if exposure.get("protocol") is not None:
            validate_reference(exposure["protocol"])
        return
    validate_reference(exposure.get("protocol"))
    declaration = exposure.get("slot_declaration")
    if not isinstance(declaration, dict) or set(declaration) != {"source", "slots_sha256"}:
        raise ValueError("registered exposure needs a slot declaration")
    validate_reference(declaration["source"])
    if declaration["source"] != exposure["protocol"] or declaration["slots_sha256"] != sha(canonical(eligible)):
        raise ValueError("slot declaration does not match protocol or slots")


def _git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True).stdout


def verify_source(root, source, expected_commit):
    """Bind the original source manifest to immutable Git objects, not current files."""
    if not isinstance(source, dict) or set(source) != {"commit", "tree", "files"} or source["commit"] != expected_commit:
        raise ValueError("unexpected execution source")
    if _git(root, "rev-parse", expected_commit + "^{tree}").decode().strip() != source["tree"]:
        raise ValueError("source tree mismatch")
    for path, identity in source["files"].items():
        _safe_path(path)
        if not isinstance(identity, dict) or set(identity) != {"git_blob", "sha256"}:
            raise ValueError("invalid source identity")
        spec = expected_commit + ":" + path
        raw = _git(root, "show", spec)
        if sha(raw) != identity["sha256"] or _git(root, "rev-parse", spec).decode().strip() != identity["git_blob"]:
            raise ValueError("source bytes mismatch")


def _time(value):
    if not isinstance(value, str):
        raise ValueError("missing timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp needs timezone")
    return parsed


def _finite_nonnegative(value, label):
    import math
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError("invalid " + label)


def _failure_observation(task, record):
    """Report observable failures without inventing an earliest mental cause."""
    first = None
    errors = []
    for i, event in enumerate(record["events"]):
        receipt = event.get("receipt")
        action = event.get("action")
        if isinstance(receipt, dict) and not receipt.get("ok", False):
            errors.append(i)
        if isinstance(action, dict) and isinstance(receipt, dict):
            one = replay.grade(task, task["files"], [{"action": action, "receipt": receipt}], "UNFINISHED")
            if one["unsafe_attempts"] and first is None:
                first = {"event_index": i, "category": "POLICY_VIOLATION", "basis": "Trusted replay of action and authorization oracle."}
    if first is None and record["terminal_reason"] != "FINISHED":
        first = {"event_index": len(record["events"]) - 1 if record["events"] else None,
                 "category": record["terminal_reason"], "basis": "Observed termination; upstream mechanism not identified."}
    elif first is None and not record["grade"]["passed"]:
        first = {"event_index": None, "category": "OUTCOME_MISMATCH", "basis": "Trusted final checks; earliest consequential deviation unknown."}
    return {
        "first_consequential_error": {"status": "unknown" if first else "not_observed", "event_index": None,
                                       "basis": "No independent causal localization was performed."},
        "first_observed_failure": first,
        "failed_tool_observation_indexes": errors,
        "recovery": {"tool_error_then_later_success": bool(errors and record["grade"]["passed"]),
                     "causal_repair_verified": False, "recurrence_test": "NOT_PERFORMED", "evidence": []},
        "diagnosis": {"detection": "replayed_binary_task_checks", "localization": "UNKNOWN",
                      "causal_attribution": "UNKNOWN", "intervention": "NOT_TESTED", "regressions": "NOT_TESTED", "evidence": []},
        "human_interventions": {"count": 0, "basis": "Frozen harness has no intervention or fallback-planner path; external activity is unattested."},
        "provider_retries": 0,
        "provider_retry_basis": "Frozen harness dispatches each recorded provider call once; external activity is unattested.",
    }


def project_run(task, record, reference, protocol_ref, source):
    """Adapter projection reuses the existing deterministic state/grade verifier."""
    result = replay.replay(record, task, protocol_ref["sha256"], source,
                           agent_policy=record.get("agent_policy", "v0.1"), model_config=record["model"])
    start, finish = _time(record["started_at"]), _time(record["finished_at"])
    if finish < start or abs((finish - start).total_seconds() - result["elapsed_seconds"]) > 0.1:
        raise ValueError("wall timestamp/elapsed inconsistency")
    steps = [{"action": e.get("action"), "observation": e.get("receipt")} for e in record["events"]]
    slot = task["id"] + "/seed" + str(record["seed"])
    return {
        "run_id": record["program_id"] + "/" + record["execution"]["GITHUB_RUN_ID"] + "/" + slot,
        "slot_id": slot,
        "task": {"id": task["id"], "family": task["family"], "sha256": sha(canonical(task)), "phase": task["phase"]},
        "identities": {
            "model": _identity(record["model"]["name"], record["model"]["digest"], record["model"], [reference]),
            "harness": _identity("Project-FAR/tool-agent-reliability", source["commit"], source, [reference]),
            "tools": _identity("virtual-files-and-bounded-integer-calculator", source["files"]["tools/tool_agent_reliability.py"]["sha256"],
                               {"implementation": "tools/tool_agent_reliability.py"}, [reference]),
            "policy": _identity("tool-agent-authorization-policy", record.get("agent_policy", "v0.1"),
                                {"system_sha256": record.get("system_sha256", sha(replay.SYSTEM.encode()))}, [reference]),
            "configuration": _identity(protocol_ref["path"], protocol_ref["sha256"], protocol_ref, [protocol_ref]),
            "environment": _identity("observed-process-runtime", None, record["runtime"], [reference],
                                     unknown_reason="Python/platform were observed; an immutable image/package-lock identity was not retained.")},
        "trace": {"artifact": reference, "complete": True, "scope": "Every harness-recorded request, response, model action and tool observation.",
                  "trajectory_sha256": sha(canonical(steps)), "model_actions": steps, "provenance": record["provenance"],
                  "execution": copy.deepcopy(record["execution"]), "trusted_execution_attestation": False},
        "outcome": {"grade": "success" if result["passed"] else "failure" if result["valid"] else "unknown",
                    "valid": result["valid"], "checks": copy.deepcopy(record["grade"]["checks"]),
                    "terminal_reason": result["terminal_reason"], "partial_success": "NOT_SEPARATELY_GRADED",
                    "abstention": "NOT_SEPARATELY_GRADED"},
        "ground_truth": {"source": copy.deepcopy(protocol_ref), "oracle_sha256": sha(canonical(task["oracle"])),
                         "adjudicator": "Project-FAR-authored deterministic harness", "independence": "NOT_EXTERNAL",
                         "independence_evidence": [],
                         "oracle_exposure": "Registered prompt reconstruction excludes oracle objects; investigators authored unsealed oracles."},
        "failure": _failure_observation(task, record),
        "safety": {"unauthorized_action_count": result["unsafe_attempts"], "unauthorized_write_count": result["unsafe_writes"],
                   "severity": "UNKNOWN", "severity_rubric": None,
                   "unknown_measurements": {},
                   "reversibility": "Virtual state reconstructible from initial snapshot; real-world impact not measured."},
        "resources": {"input_tokens": result["input_tokens"], "output_tokens": result["output_tokens"],
                      "model_calls": result["model_calls"], "tool_actions": result["tool_actions"],
                      "elapsed_seconds": result["elapsed_seconds"], "provider_seconds": result["provider_seconds"],
                      "setup_seconds": None, "human_review_seconds": None,
                      "unknown_measurements": {name: {"reason": reason, "evidence": [reference["path"]]} for name, reason in
                                               (("setup_seconds", "Provisioning/setup duration was not retained by this harness."),
                                                ("human_review_seconds", "Human review effort was not measured in this study."))},
                      "billing": {"status": "unknown", "amount": None, "currency": None, "source": None}},
        "timestamps": {"started_at": record["started_at"], "finished_at": record["finished_at"]},
        "limitations": list(BOUNDARIES),
    }


def summarize(exposure, runs):
    """Incident collections have no failure-rate denominator; no IID estimates."""
    validate_exposure(exposure)
    eligible = exposure["eligible_slots"]
    ids, slots = set(), set()
    counts = {key: 0 for key in ("success", "partial_success", "failure", "abstention", "unknown")}
    trajectories = set()
    for run in runs:
        if run["run_id"] in ids or run["slot_id"] in slots:
            raise ValueError("duplicate run or slot")
        ids.add(run["run_id"]); slots.add(run["slot_id"])
        if exposure["kind"] == "registered_slots" and run["slot_id"] not in eligible:
            raise ValueError("unregistered run")
        if run["outcome"]["grade"] not in counts:
            raise ValueError("invalid outcome grade")
        counts[run["outcome"]["grade"]] += 1
        trajectories.add(run["trace"]["trajectory_sha256"])
    complete = exposure["kind"] == "registered_slots" and bool(eligible) and slots == set(eligible) and counts["unknown"] == 0
    def fraction(n):
        value = Fraction(n, len(eligible))
        return {"numerator": value.numerator, "denominator": value.denominator}
    return {"observed_runs": len(runs), "eligible_exposures": len(eligible) if exposure["kind"] == "registered_slots" else None,
            "missing_slots": sorted(set(eligible) - slots), "outcomes": counts, "complete": complete,
            "success_fraction": fraction(counts["success"]) if complete else None,
            "failure_fraction": fraction(counts["failure"]) if complete else None,
            "rate_scope": "Conditional declared-slot fraction; evidence replay must establish the registered exposure." if complete else "NO_RATE_WITHOUT_COMPLETE_KNOWN_EXPOSURE",
            "distinct_action_observation_trajectories": len(trajectories), "independent_behavioral_samples": "NOT_ESTABLISHED",
            "general_agent_reliability": "NOT_ESTABLISHED", "far_causal_benefit": "NOT_TESTED"}


def validate_profile(profile):
    """Validate the common cross-model measurement surface without self-grading."""
    required = {"schema", "status", "cohort_id", "adapter", "evidence_package", "exposure", "runs", "summary", "limitations"}
    if not isinstance(profile, dict) or set(profile) != required or profile["schema"] != SCHEMA or profile["status"] != "Research":
        raise ValueError("invalid evidence profile")
    package = normalize_package(profile["evidence_package"])
    if package.get("schema") != "far-evidence-package/1.0" or package.get("metadata", {}).get("agent_evidence_profile") != SCHEMA:
        raise ValueError("missing existing evidence-package envelope")
    if not isinstance(profile["runs"], list) or not profile["limitations"]:
        raise ValueError("missing runs/limitations")
    def fields(value, required, label):
        if not isinstance(value, dict) or set(value) != set(required.split()):
            raise ValueError("missing or unsupported " + label + " fields")
    def text(value, label, maximum=2048):
        if not isinstance(value, str) or not value.strip() or len(value) > maximum:
            raise ValueError("invalid or missing " + label)
    def nonnegative(value, label, unknown=False):
        if value is None and unknown:
            return
        if type(value) is not int or value < 0:
            raise ValueError("invalid " + label)
    def references(value, label):
        if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() or len(v) > 2048 for v in value):
            raise ValueError("invalid " + label)
    def unknowns(value, names, label):
        unknown = value["unknown_measurements"]
        if not isinstance(unknown, dict) or set(unknown) != {name for name in names if value[name] is None}:
            raise ValueError("unknown " + label + " measurements need exact reasons")
        for name, explanation in unknown.items():
            fields(explanation, "reason evidence", "unknown measurement")
            text(explanation["reason"], "unknown measurement reason")
            references(explanation["evidence"], "unknown measurement evidence")
    text(profile["cohort_id"], "cohort identity", maximum=256)
    text(profile["adapter"], "adapter identity", maximum=256)
    fields(profile["exposure"], "kind unit eligible_slots sampling_frame independence protocol slot_declaration", "exposure")
    validate_exposure(profile["exposure"])
    references(profile["limitations"], "profile limitations")
    for name in ("unit", "sampling_frame", "independence"):
        text(profile["exposure"][name], "exposure " + name)
    for run in profile["runs"]:
        keys = {"run_id", "slot_id", "task", "identities", "trace", "outcome", "ground_truth", "failure", "safety", "resources", "timestamps", "limitations"}
        if not isinstance(run, dict) or set(run) != keys or not run["limitations"]:
            raise ValueError("missing run measurement dimension")
        text(run["run_id"], "run ID"); text(run["slot_id"], "slot ID")
        references(run["limitations"], "run limitations")
        fields(run["identities"], "model harness tools policy configuration environment", "runtime identity")
        for identity in run["identities"].values():
            validate_identity(identity)
        validate_reference(run["identities"]["configuration"]["details"])
        fields(run["task"], "id family sha256 phase", "task")
        for name in ("id", "family", "phase"):
            text(run["task"][name], "task " + name)
        if not isinstance(run["task"]["sha256"], str) or not re.fullmatch("[a-f0-9]{64}", run["task"]["sha256"]):
            raise ValueError("invalid task digest")
        fields(run["trace"], "artifact complete scope trajectory_sha256 model_actions provenance execution trusted_execution_attestation", "trace")
        validate_reference(run["trace"]["artifact"])
        text(run["trace"]["scope"], "trace scope"); text(run["trace"]["provenance"], "trace provenance")
        if not isinstance(run["trace"]["execution"], dict) or not run["trace"]["execution"]:
            raise ValueError("missing execution provenance")
        if type(run["trace"].get("complete")) is not bool or (not run["trace"]["complete"] and (run["outcome"]["grade"] != "unknown" or run["outcome"]["valid"] is not False)) or run["trace"].get("trusted_execution_attestation") is not False:
            raise ValueError("invalid trace assurance")
        if not isinstance(run["trace"]["model_actions"], list):
            raise ValueError("invalid model actions")
        for step in run["trace"]["model_actions"]:
            fields(step, "action observation", "action/observation")
        if run["trace"]["trajectory_sha256"] != sha(canonical(run["trace"]["model_actions"])):
            raise ValueError("trajectory mismatch")
        fields(run["outcome"], "grade valid checks terminal_reason partial_success abstention", "outcome")
        for name in ("terminal_reason", "partial_success", "abstention"):
            text(run["outcome"][name], "outcome " + name)
        fields(run["ground_truth"], "source oracle_sha256 adjudicator independence independence_evidence oracle_exposure", "ground truth")
        validate_reference(run["ground_truth"]["source"])
        if not isinstance(run["ground_truth"]["oracle_sha256"], str) or not re.fullmatch("[a-f0-9]{64}", run["ground_truth"]["oracle_sha256"]):
            raise ValueError("invalid oracle digest")
        references(run["ground_truth"]["independence_evidence"], "independence evidence")
        for name in ("adjudicator", "oracle_exposure"):
            text(run["ground_truth"][name], name)
        if run["ground_truth"].get("independence") not in {"NOT_EXTERNAL", "UNKNOWN", "EXTERNALLY_DOCUMENTED"}:
            raise ValueError("invalid independence status")
        if run["ground_truth"]["independence"] == "EXTERNALLY_DOCUMENTED" and not run["ground_truth"]["independence_evidence"]:
            raise ValueError("external independence needs evidence")
        fields(run["failure"], "first_consequential_error first_observed_failure failed_tool_observation_indexes recovery diagnosis human_interventions provider_retries provider_retry_basis", "failure")
        failure = run["failure"]
        first = failure["first_consequential_error"]
        fields(first, "status event_index basis", "first consequential error")
        if first["status"] not in {"unknown", "not_observed", "observed"}:
            raise ValueError("invalid first consequential error status")
        def index(value, label):
            if type(value) is not int or not 0 <= value < len(run["trace"]["model_actions"]):
                raise ValueError("invalid " + label + " event index")
        if first["status"] == "observed":
            index(first["event_index"], "first consequential error")
        elif first["event_index"] is not None:
            raise ValueError("unknown/unobserved error cannot name a step")
        text(first["basis"], "first consequential error basis")
        observed = failure["first_observed_failure"]
        if observed is not None:
            fields(observed, "event_index category basis", "observed failure")
            if observed["event_index"] is not None:
                index(observed["event_index"], "observed failure")
            text(observed["category"], "failure category"); text(observed["basis"], "observed failure basis")
        positions = failure["failed_tool_observation_indexes"]
        if not isinstance(positions, list):
            raise ValueError("invalid failed-tool observations")
        for position in positions:
            index(position, "failed-tool observation")
        recovery = failure["recovery"]
        fields(recovery, "tool_error_then_later_success causal_repair_verified recurrence_test evidence", "recovery")
        if type(recovery["tool_error_then_later_success"]) is not bool or type(recovery["causal_repair_verified"]) is not bool or recovery["recurrence_test"] not in {"NOT_PERFORMED", "EVIDENCE_BOUND"}:
            raise ValueError("invalid recovery status")
        references(recovery["evidence"], "recovery evidence")
        if (recovery["causal_repair_verified"] or recovery["recurrence_test"] == "EVIDENCE_BOUND") and not recovery["evidence"]:
            raise ValueError("causal repair/recurrence claim needs evidence")
        diagnosis = failure["diagnosis"]
        fields(diagnosis, "detection localization causal_attribution intervention regressions evidence", "diagnosis")
        permitted = {"detection": {"UNKNOWN", "replayed_binary_task_checks", "EVIDENCE_BOUND"},
                     "localization": {"UNKNOWN", "EVIDENCE_BOUND"}, "causal_attribution": {"UNKNOWN", "INTERVENTION_SUPPORTED"},
                     "intervention": {"NOT_TESTED", "EVIDENCE_BOUND"}, "regressions": {"NOT_TESTED", "EVIDENCE_BOUND"}}
        if any(diagnosis[key] not in values for key, values in permitted.items()):
            raise ValueError("invalid diagnosis status")
        references(diagnosis["evidence"], "diagnosis evidence")
        if any(diagnosis[key] in {"EVIDENCE_BOUND", "INTERVENTION_SUPPORTED"} for key in permitted) and not diagnosis["evidence"]:
            raise ValueError("diagnosis claim needs evidence")
        fields(failure["human_interventions"], "count basis", "human interventions")
        nonnegative(failure["human_interventions"]["count"], "human interventions", unknown=True)
        text(failure["human_interventions"]["basis"], "intervention basis")
        nonnegative(failure["provider_retries"], "provider retries", unknown=True)
        text(failure["provider_retry_basis"], "provider retry basis")
        fields(run["safety"], "unauthorized_action_count unauthorized_write_count severity severity_rubric reversibility unknown_measurements", "safety")
        safety_names = ("unauthorized_action_count", "unauthorized_write_count")
        for name in safety_names:
            nonnegative(run["safety"][name], name, unknown=True)
        unknowns(run["safety"], safety_names, "safety")
        if all(run["safety"][name] is not None for name in safety_names) and run["safety"]["unauthorized_write_count"] > run["safety"]["unauthorized_action_count"]:
            raise ValueError("unauthorized write count exceeds action count")
        text(run["safety"]["severity"], "severity"); text(run["safety"]["reversibility"], "reversibility")
        if run["safety"]["severity"] != "UNKNOWN":
            text(run["safety"]["severity_rubric"], "severity rubric")
        fields(run["resources"], "input_tokens output_tokens model_calls tool_actions elapsed_seconds provider_seconds setup_seconds human_review_seconds billing unknown_measurements", "resources")
        counter_names = ("input_tokens", "output_tokens", "model_calls", "tool_actions")
        seconds_names = ("elapsed_seconds", "provider_seconds", "setup_seconds", "human_review_seconds")
        unknowns(run["resources"], counter_names + seconds_names, "resource")
        for key in counter_names:
            value = run["resources"][key]
            nonnegative(value, "resource counter", unknown=True)
        for key in seconds_names:
            if run["resources"][key] is not None:
                _finite_nonnegative(run["resources"][key], key)
        elapsed, provider = run["resources"]["elapsed_seconds"], run["resources"]["provider_seconds"]
        if elapsed is not None and provider is not None and provider > elapsed + 1e-6:
            raise ValueError("provider time exceeds total elapsed time")
        fields(run["timestamps"], "started_at finished_at", "timestamps")
        delta = (_time(run["timestamps"]["finished_at"]) - _time(run["timestamps"]["started_at"])).total_seconds()
        if delta < 0 or (elapsed is not None and abs(delta - elapsed) > 0.1):
            raise ValueError("inconsistent timestamps")
        if provider is not None and provider > delta + 0.1:
            raise ValueError("provider time exceeds observed wall interval")
        bill = run["resources"]["billing"]
        if set(bill) != {"status", "amount", "currency", "source"} or bill["status"] not in {"unknown", "observed", "estimated"}:
            raise ValueError("invalid billing status")
        if bill["status"] == "unknown":
            if any(bill[k] is not None for k in ("amount", "currency", "source")):
                raise ValueError("unknown billing cannot claim zero or other amount")
        else:
            if not isinstance(bill["amount"], str) or len(bill["amount"]) > 128 or not re.fullmatch(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", bill["amount"]) or not isinstance(bill["currency"], str) or not re.fullmatch("[A-Z]{3}", bill["currency"]):
                raise ValueError("cost claim needs exact nonnegative decimal, currency and evidence")
            text(bill["source"], "billing evidence reference")
        checks = run["outcome"]["checks"]
        if not isinstance(checks, dict) or not checks or any(type(value) is not bool for value in checks.values()):
            raise ValueError("missing or invalid grade checks")
        if type(run["outcome"]["valid"]) is not bool or (not run["outcome"]["valid"] and run["outcome"]["grade"] != "unknown"):
            raise ValueError("invalid execution cannot receive known outcome")
        if run["outcome"]["grade"] == "success" and (not run["outcome"]["valid"] or not all(checks.values()) or any(run["safety"][name] != 0 for name in safety_names)):
            raise ValueError("fabricated success contradicts checks or safety")
    if canonical(profile["summary"]) != canonical(summarize(profile["exposure"], profile["runs"])):
        raise ValueError("summary or denominator mismatch")
    return True


def _historical_records(root, cohort):
    if cohort == "tool-agent-v03-scored":
        protocol_path = "research/tool-agent-reliability/protocol-v0.3.json"
        raw_archive = _read_file(root, V03_ARCHIVE)
        if sha(raw_archive) != V03_ARCHIVE_SHA:
            raise ValueError("frozen public archive mutation")
        members = ("original-artifacts/13224187919.zip",)
        records = []
        with zipfile.ZipFile(io.BytesIO(raw_archive)) as outer:
            with zipfile.ZipFile(io.BytesIO(outer.read(members[0]))) as inner:
                for name in sorted(inner.namelist()):
                    if name.startswith("scored/") and name.endswith(".json"):
                        raw = inner.read(name)
                        records.append((replay.strict_json(raw), artifact(V03_ARCHIVE, raw, (*members, name))))
        return protocol_path, records, V03_SOURCE, "scored"
    if cohort == "tool-agent-v02-preflight":
        protocol_path = "research/tool-agent-reliability/protocol-v0.2.json"
        records = []
        for i in range(4, 7):
            path = "research/tool-agent-reliability/result/v0.2/preflight/TAR-P0" + str(i) + "-seed0.json"
            raw = _read_file(root, path)
            if raw != _git(root, "show", HISTORICAL_BASE + ":" + path):
                raise ValueError("frozen preflight evidence mutation")
            records.append((replay.strict_json(raw), artifact(path, raw)))
        return protocol_path, records, V02_SOURCE, "preflight"
    raise ValueError("no registered historical adapter for cohort")


def build_historical(root=ROOT, cohort="tool-agent-v03-scored"):
    protocol_path, retained, commit, phase = _historical_records(root, cohort)
    raw_protocol = _read_file(root, protocol_path)
    protocol = replay.strict_json(raw_protocol)
    replay.validate_protocol(protocol)
    protocol_ref = artifact(protocol_path, raw_protocol)
    tasks = {task["id"]: task for task in protocol["tasks"] if task["phase"] == phase}
    source = retained[0][0]["source"]
    verify_source(root, source, commit)
    if source["files"][protocol_path]["sha256"] != protocol_ref["sha256"]:
        raise ValueError("frozen protocol mutation")
    expected_files = {"tools/tool_agent_reliability.py", protocol_path}
    if phase == "scored":
        expected_files |= {"scripts/tool_agent_reliability_start_7b.sh", ".github/workflows/far-tool-agent-reliability-v03.yml"}
    else:
        expected_files |= {"scripts/workflow_efficacy_start_ollama.sh", "tools/workflow_efficacy_free_agent.py", ".github/workflows/far-tool-agent-reliability-v02.yml"}
    if set(source["files"]) != expected_files:
        raise ValueError("incomplete execution-source binding")
    runs = [project_run(tasks[record["task_id"]], record, reference, protocol_ref, source) for record, reference in retained]
    seeds = protocol["seeds"] if phase == "scored" else [0]
    exposure = {"kind": "registered_slots", "unit": "execution_slot", "eligible_slots": [task_id + "/seed" + str(seed) for task_id in tasks for seed in seeds],
                "sampling_frame": "Frozen project-authored virtual-file tasks in " + protocol_path,
                "independence": "NOT_ESTABLISHED", "protocol": protocol_ref}
    exposure["slot_declaration"] = slot_declaration(protocol_ref, exposure["eligible_slots"])
    summary = summarize(exposure, runs)
    package = {"schema": "far-evidence-package/1.0", "package_id": cohort, "subject_id": "FAR-TOOL-AGENT-001",
               "metadata": {"agent_evidence_profile": SCHEMA, "execution_source_commit": commit, "adapter": "existing-tool-agent-replay"},
               "claims": [{"claim_id": "bounded-retained-run-audit", "statement": "Retained run outcomes replay against the frozen authored task oracle.",
                           "status": "observed", "support": [protocol_path, *sorted({reference["path"] for _, reference in retained})],
                           "assumptions": ["Public retained evidence is the original execution record; no external execution attestation exists."],
                           "contradicts": [], "boundaries": list(BOUNDARIES)}], "boundaries": list(BOUNDARIES)}
    profile = {"schema": SCHEMA, "status": "Research", "cohort_id": cohort, "adapter": "existing-tool-agent-replay",
               "evidence_package": package, "exposure": exposure, "runs": runs, "summary": summary, "limitations": list(BOUNDARIES)}
    validate_profile(profile)
    return profile


def verify_historical(profile, root=ROOT):
    """Rebuild every projected measurement; caller-supplied grades never suffice."""
    validate_profile(profile)
    if canonical(profile) != canonical(build_historical(root, profile["cohort_id"])):
        raise ValueError("profile differs from replayed frozen artifacts")
    return profile["summary"]


def historical_audit(root=ROOT):
    """Small reproducible receipt; full views regenerate without duplicating traces."""
    profiles = [build_historical(root, cohort) for cohort in ("tool-agent-v03-scored", "tool-agent-v02-preflight")]
    return {"schema": "far-agent-evidence-audit/0.1", "status": "Research",
            "observation_kind": "post-execution historical evidence replay; zero new model calls",
            "audit_source_sha256": sha(Path(__file__).read_bytes()),
            "cohorts": [{"cohort_id": p["cohort_id"], "profile_canonical_sha256": sha(canonical(p)), "summary": p["summary"]} for p in profiles],
            "frozen_artifacts_modified": False, "limitations": list(BOUNDARIES)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify", "audit"))
    parser.add_argument("--cohort", choices=("tool-agent-v03-scored", "tool-agent-v02-preflight"), default="tool-agent-v03-scored")
    parser.add_argument("--file", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command in {"build", "audit"}:
        result = build_historical(cohort=args.cohort) if args.command == "build" else historical_audit()
        args.file.parent.mkdir(parents=True, exist_ok=True)
        args.file.write_bytes(json.dumps(result, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n")
        print(json.dumps(result["summary"] if args.command == "build" else result, sort_keys=True))
    else:
        result = replay.strict_json(args.file.read_bytes())
        print(json.dumps(verify_historical(result), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
