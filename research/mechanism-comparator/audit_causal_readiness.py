"""Read-only causal-identification and execution authorization audit.

Current v3 is an existing *design only* preregistered experiment. This tool
CANNOT launch an agent, model, pilot, confirmatory benchmark or access a task.
Never turn a gate on, invent an independent identity or synthesize outcomes.

It reports both (a) whether the current frozen three-arm protocol can identify
a distinctive FAR-vs-generic mechanism effect and (b) whether the existing
prospective launch boundary permits real model execution.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
V3 = ROOT / "research/external-validation/swe-agent-v3"


def exact_json(path: Path) -> dict[str, Any]:
    def no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        obj: dict[str, Any] = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError(f"duplicate JSON key: {key}")
            obj[key] = value
        return obj

    obj = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=no_duplicate_keys)
    if not isinstance(obj, dict):
        raise ValueError("contract must be an object")
    return obj


def audit_design(protocol: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    """Conservative audit: never infer external authorization from internal flags."""
    if protocol.get("program_id") != "FAR-SWE-V3-001" or gate.get("program_id") != "FAR-SWE-V3-001":
        raise ValueError("unexpected experimental program identity")
    arms = protocol.get("arms")
    if not isinstance(arms, list) or not all(isinstance(a, dict) for a in arms):
        raise ValueError("invalid experimental arms")
    names = [a.get("id") for a in arms]
    if any(not isinstance(name, str) for name in names) or len(names) != len(set(names)):
        raise ValueError("duplicate or invalid arm name")
    for needed in ("baseline", "placebo", "far"):
        if needed not in names:
            raise ValueError("missing required preregistered arm: " + needed)
    pilots, confirm = gate.get("pilot_gates"), gate.get("gates")
    if not isinstance(pilots, dict) or not isinstance(confirm, dict):
        raise ValueError("missing launch-gate objects")
    if not pilots or not confirm or not all(type(x) is bool for x in [*pilots.values(), *confirm.values()]):
        raise ValueError("invalid launch-gate booleans")
    flags = ("execution_authorized", "model_calls_authorized",
             "benchmark_execution_authorized", "pilot_execution_authorized",
             "confirmatory_execution_authorized")
    if not all(type(gate.get(f)) is bool for f in flags):
        raise ValueError("invalid launch authorization flag types")
    launch_record = gate.get("launch_record_required_bindings")
    if not isinstance(launch_record, list) or not launch_record or len(launch_record) != len(set(launch_record)):
        raise ValueError("invalid prospective launch bindings")
    if "manual_authorization_record_identity" not in launch_record:
        raise ValueError("no manual authorization binding")

    # A true flag and all gates would still NOT be sufficient without a separately
    # committed, complete and verified prospective launch record.
    pilot_flags = gate["execution_authorized"] and gate["model_calls_authorized"] \
        and gate["pilot_execution_authorized"]
    confirm_flags = gate["execution_authorized"] and gate["model_calls_authorized"] \
        and gate["benchmark_execution_authorized"] and gate["confirmatory_execution_authorized"]
    return {
        "schema": "far-swe-v3-authorization-and-identification-audit/1",
        "program_id": "FAR-SWE-V3-001",
        "status": "READ_ONLY_DESIGN_AUDIT",
        "arm_names": names,
        "number_of_arms": len(names),
        "contains_matched_generic_active_comparator": "generic_checker" in names,
        "far_minus_generic_checker_identified_by_protocol": (
            "generic_checker" in names and "far" in names
            and "far_minus_generic_checker" in protocol.get("secondary_contrasts", [])
        ),
        "far_mechanism_exercised_by_executions": "UNKNOWN_NO_VERIFIED_TOOL_EXECUTION_RECEIPTS",
        "pilot_total_gates": len(pilots),
        "pilot_true_gates": sum(pilots.values()),
        "confirmatory_total_gates": len(confirm),
        "confirmatory_true_gates": sum(confirm.values()),
        "pilot_all_flags_and_gates_true": pilot_flags and all(pilots.values()),
        "confirmatory_all_flags_and_gates_true": confirm_flags and all(confirm.values()),
        "prospective_fully_bound_launch_record_verified": False,
        "pilot_model_calls_permitted_by_this_audit": False,
        "confirmatory_model_calls_permitted_by_this_audit": False,
        "causal_effect_estimated": False,
        "experimental_outcomes_presented": False,
        "verdict": "FAR_SPECIFIC_GENERAL_AGENT_RELIABILITY_EFFECT_NOT_IDENTIFIED",
        "notes": [
            "Current v3 identifies far-minus-placebo only after authorized real execution.",
            "No generic-checker arm means no FAR-minus-generic mechanism effect is identified.",
            "Even positive far-minus-placebo would not imply actual FAR tool invocation.",
            "A verified prospective launch record and independent authorization are mandatory.",
            "The only way to establish causal effects is to execute a properly authorized trial.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    protocol = exact_json(V3 / "preregistration-v1.0.json")
    gate = exact_json(V3 / "execution-gate-v1.0.json")
    result = audit_design(protocol, gate)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload)
    print("PASS_FAIL_CLOSED_NO_EXECUTION_AUTHORITY " + payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
