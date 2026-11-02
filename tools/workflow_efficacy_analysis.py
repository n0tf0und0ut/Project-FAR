"""Analyze paired agent-workflow experiments without treating missing runs as evidence.

This tool never manufactures model outputs or asserts independence from metadata.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "research/workflow-efficacy/protocol-v0.1.json"
ARMS = ("control", "treatment")


def load_protocol(path=PROTOCOL):
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    assert obj["schema"] == "far-agent-workflow-differential/0.1"
    cases = obj["historical_candidates"]
    assert len(cases) == 30
    assert len({c["id"] for c in cases}) == 30
    assert len({c["pr"] for c in cases}) == 30
    assert len({c["historical_candidate_head"] for c in cases}) == 30
    assert obj["run_plan"]["planned_runs"] == 60
    assert obj["run_plan"]["arms"] == list(ARMS)
    for c in cases:
        assert len(c["base_commit"]) == len(c["historical_candidate_head"]) == 40
        assert all(v in "0123456789abcdef" for v in c["base_commit"] + c["historical_candidate_head"])
    return obj


def planned_runs(protocol):
    cases = protocol["historical_candidates"]
    result = []
    # Exactly 15 control-first and 15 treatment-first pairs.
    order_keys = sorted((hashlib.sha256(("far-workflow-v0.1|"+c["id"]).encode()).hexdigest(), c["id"]) for c in cases)
    first_control = {task_id for _, task_id in order_keys[:15]}
    for c in cases:
        first = "control" if c["id"] in first_control else "treatment"
        second = "treatment" if first == "control" else "control"
        for arm in (first, second):
            result.append({"run_id": c["id"]+"-"+arm, "task_id": c["id"], "arm": arm})
    assert len(result) == 60 and sum(v["arm"] == "control" for v in result) == 30
    return result


def analyze(protocol, records):
    # A fabricated JSONL cannot bypass prospectively frozen study prerequisites.
    if (protocol.get("fixed_task_bundles") != "FROZEN"
            or not isinstance(protocol.get("runtime_hash"), str)
            or not protocol["runtime_hash"]
            or protocol["runtime_hash"] == "NOT_FROZEN"
            or not isinstance(protocol.get("tool_config_hash"), str)
            or not protocol["tool_config_hash"]
            or protocol["tool_config_hash"] == "NOT_FROZEN"
            or protocol.get("model_identity") in ("UNRESOLVED", None)
            or protocol.get("agent_executor") in ("UNAVAILABLE_IN_CURRENT_TOOL_RUNTIME", None)
            or protocol.get("isolation_verified") is not True
            or protocol.get("blinded_evaluator") in ("NOT_ASSIGNED", None)
            or protocol.get("budget") != "FROZEN"):
        return {"status": "STUDY_PRECONDITIONS_UNMET", "claim": "NOT_ESTABLISHED"}
    if any(not isinstance(c.get("task_bundle_hash"), str) or not c["task_bundle_hash"]
           for c in protocol["historical_candidates"]):
        return {"status": "STUDY_PRECONDITIONS_UNMET", "claim": "NOT_ESTABLISHED"}
    expected = {x["run_id"]: x for x in planned_runs(protocol)}
    case_by_id = {c["id"]: c for c in protocol["historical_candidates"]}
    if len(records) != len(expected) or {r.get("run_id") for r in records} != set(expected):
        return {"status": "INCOMPLETE_OR_DUPLICATE", "expected_runs": 60,
                "observed_runs": len(records), "claim": "NOT_ESTABLISHED"}
    seen = set()
    by_case = {}
    global_identity = None
    required_identity = ("model_id", "runtime_hash", "tool_config_hash", "task_bundle_hash",
                         "evaluator_id", "instruction_ref", "provenance_verified", "isolation_verified")
    for r in records:
        run = r["run_id"]
        if run in seen:
            return {"status": "DUPLICATE_RUN", "claim": "NOT_ESTABLISHED"}
        seen.add(run)
        expected_item = expected[run]
        if r.get("task_id") != expected_item["task_id"] or r.get("arm") != expected_item["arm"]:
            return {"status": "IDENTITY_MISMATCH", "claim": "NOT_ESTABLISHED"}
        expected_instruction_ref = protocol[r["arm"] + "_instructions"]["repo_commit"]
        if r.get("instruction_ref") != expected_instruction_ref:
            return {"status": "INSTRUCTION_VERSION_MISMATCH", "claim": "NOT_ESTABLISHED"}
        if any(f not in r for f in required_identity):
            return {"status": "MISSING_PROVENANCE", "claim": "NOT_ESTABLISHED"}
        identity_keys = ("model_id", "runtime_hash", "tool_config_hash", "task_bundle_hash", "evaluator_id")
        if any(not isinstance(r[k], str) or not r[k].strip() for k in identity_keys):
            return {"status": "EMPTY_OR_NULL_IDENTITY", "claim": "NOT_ESTABLISHED"}
        if (r["model_id"] != protocol["model_identity"]
                or r["runtime_hash"] != protocol["runtime_hash"]
                or r["tool_config_hash"] != protocol["tool_config_hash"]
                or r["evaluator_id"] != protocol["blinded_evaluator"]
                or r["task_bundle_hash"] != case_by_id[r["task_id"]]["task_bundle_hash"]):
            return {"status": "NOT_FROZEN_IDENTITY", "claim": "NOT_ESTABLISHED"}
        if r.get("provenance_verified") is not True or r.get("isolation_verified") is not True:
            return {"status": "UNVERIFIED_ISOLATION_OR_PROVENANCE", "claim": "NOT_ESTABLISHED"}
        fingerprint = tuple(r[k] for k in ("model_id", "runtime_hash", "tool_config_hash", "evaluator_id"))
        if global_identity is None:
            global_identity = fingerprint
        elif global_identity != fingerprint:
            return {"status": "CROSS_TASK_MODEL_OR_TOOL_DRIFT", "claim": "NOT_ESTABLISHED"}
        if type(r.get("success")) is not bool:
            return {"status": "UNVERIFIED_OR_MISSING_OUTCOME", "claim": "NOT_ESTABLISHED"}
        if r["success"] and r.get("new_regressions", 0) != 0:
            return {"status": "CONTRADICTORY_SUCCESS_AND_REGRESSIONS", "claim": "NOT_ESTABLISHED"}
        if any(type(r.get(k)) not in (int, float) or not math.isfinite(r[k]) or r[k] < 0
               for k in ("elapsed_seconds", "total_tokens", "provider_cost_usd", "new_regressions", "rework_count")):
            return {"status": "INVALID_RESOURCE_ACCOUNTING", "claim": "NOT_ESTABLISHED"}
        by_case.setdefault(r["task_id"], {})[r["arm"]] = r
    pairs = []
    for task_id, pair in sorted(by_case.items()):
        if set(pair) != set(ARMS):
            return {"status": "MISSING_PAIR", "claim": "NOT_ESTABLISHED"}
        a, b = pair["control"], pair["treatment"]
        if (a["model_id"], a["runtime_hash"], a["tool_config_hash"], a["task_bundle_hash"], a["evaluator_id"]) != (
                b["model_id"], b["runtime_hash"], b["tool_config_hash"], b["task_bundle_hash"], b["evaluator_id"]):
            return {"status": "UNMATCHED_CONDITIONS", "task_id": task_id, "claim": "NOT_ESTABLISHED"}
        pairs.append((a, b))
    differences = [int(t["success"]) - int(c["success"]) for c, t in pairs]
    plus = sum(x == 1 for x in differences)
    minus = sum(x == -1 for x in differences)
    discordant = plus + minus
    p = min(1.0, 2 * sum(math.comb(discordant, i) for i in range(min(plus, minus)+1)) / (2**discordant)) if discordant else 1.0
    rng = random.Random(60220261102)
    boot = sorted(sum(rng.choice(differences) for _ in differences) / len(differences) for _ in range(10000))
    def delta(field):
        return sum(t[field] - c[field] for c, t in pairs) / len(pairs)
    return {"status": "STRUCTURALLY_VALID_SELF_REPORTED_PAIRED_DATA", "n_pairs": len(pairs),
            "treatment_success": sum(int(t["success"]) for _, t in pairs),
            "control_success": sum(int(c["success"]) for c, _ in pairs),
            "paired_success_delta": sum(differences)/len(differences),
            "paired_bootstrap_interval_95pct": [boot[249], boot[9749]],
            "discordant_improvements": plus, "discordant_regressions": minus,
            "exact_sign_test_two_sided_p": p,
            "mean_elapsed_delta_seconds": delta("elapsed_seconds"),
            "mean_token_delta": delta("total_tokens"),
            "mean_provider_cost_delta_usd": delta("provider_cost_usd"),
            "mean_rework_delta": delta("rework_count"),
            "mean_new_regression_delta": delta("new_regressions"),
            "claim": "ARITHMETIC_ON_SUBMITTED_RECORDS_ONLY; INDEPENDENCE_AND_REALITY_REQUIRE_EXTERNAL_AUDIT"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["verify", "schedule", "analyze"])
    parser.add_argument("--protocol", default=str(PROTOCOL))
    parser.add_argument("--runs", type=Path)
    args = parser.parse_args(argv)
    protocol = load_protocol(args.protocol)
    if args.action == "verify":
        outcome = {"status": protocol["current_execution"]["status"],
                   "historical_candidates": len(protocol["historical_candidates"]),
                   "planned_runs": len(planned_runs(protocol)),
                   "model_identity": protocol["model_identity"],
                   "claim": "NOT_ESTABLISHED"}
    elif args.action == "schedule":
        outcome = {"status": "PLANNED_NOT_EXECUTED", "runs": planned_runs(protocol)}
    else:
        if not args.runs:
            parser.error("--runs is required for analyze")
        records = [json.loads(s) for s in args.runs.read_text().splitlines() if s.strip()]
        outcome = analyze(protocol, records)
    print(json.dumps(outcome, sort_keys=True, indent=2))
    return 0 if outcome["status"] in {"STRUCTURALLY_VALID_SELF_REPORTED_PAIRED_DATA", "NOT_EXECUTED", "PLANNED_NOT_EXECUTED"} else 2


if __name__ == "__main__":
    sys.exit(main())
