"""Read-only equal-interface checker calibration; no agent runtime or launch authority.

Consumes the same complete far-ir/2.0 input bytes for either arm. The generic arm
reads only the projection needed for its frozen finite table check. The FAR arm
uses the actual current strict rule-v1.1 verifier. The different evidence
requirements are an experimental treatment difference, not external efficacy.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import verify_candidate as registration
from tools.efr_generic_collision_checker import check as generic_check
from mechanization.far_mechanization.contract_v2_strict_v11 import (
    validate_contract as far_validate,
)

MAX_INPUT_BYTES = 2 * 1024 * 1024
LABELS = ("NO_LOSS", "LOSS", "INVALID")


def _strict_input(raw: bytes) -> object:
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_INPUT_BYTES:
        raise ValueError("invalid or oversized calibration input")
    result = registration.exact_json(raw)

    def bound(v: object, depth: int = 0) -> None:
        if depth > 64:
            raise ValueError("JSON nesting exceeds calibration limit")
        if isinstance(v, dict):
            for x in v.values():
                bound(x, depth + 1)
        elif isinstance(v, list):
            for x in v:
                bound(x, depth + 1)

    bound(result)
    return result


def _finite_projection(document: object) -> dict:
    if not isinstance(document, dict):
        raise ValueError("contract must be object")
    contract = document.get("contract")
    if not isinstance(contract, dict):
        raise ValueError("missing contract")
    representation, behavior = contract.get("representation"), contract.get("required_behavior")
    if not isinstance(representation, dict) or not isinstance(behavior, dict):
        raise ValueError("missing finite tables")
    return {"representation": representation.get("table"),
            "required_behavior": behavior.get("table")}


def evaluate(arm: str, raw: bytes) -> dict:
    """One public shape regardless of arm; does NOT provide runtime receipts."""
    if arm not in ("generic_checker", "far"):
        raise ValueError("unregistered checker arm")
    document = _strict_input(raw)
    if arm == "generic_checker":
        result = generic_check(_finite_projection(document))
        classification = "LOSS" if result["result"] == "INCONSISTENT" else "NO_LOSS"
        diagnostics = ["GENERIC_COLLISION"] if classification == "LOSS" else []
        extra = {"conflicting_pairs": len(result["conflicting_pairs"])}
    else:
        result = far_validate(document)
        diagnostics = sorted({str(d.code) for d in result.diagnostics})
        report = document.get("report", {}) if isinstance(document, dict) else {}
        evidence = report.get("evidence", {}) if isinstance(report, dict) else {}
        outcome = report.get("outcome") if isinstance(report, dict) else None
        kind = evidence.get("kind") if isinstance(evidence, dict) else None
        status = evidence.get("status") if isinstance(evidence, dict) else None
        if result.success and (outcome, kind, status) == (
            "PROVED", "factorization", "CHECKED_FINITE_EXPLICIT"
        ):
            classification = "NO_LOSS"
        elif result.success and (outcome, kind, status) == (
            "REFUTED", "collision", "CHECKED_FINITE_EXPLICIT"
        ):
            classification = "LOSS"
        elif "FACTORIZATION_FAILURE" in diagnostics:
            classification = "LOSS"
        else:
            classification = "INVALID"
        extra = {"conflicting_pairs": None}
    if classification not in LABELS:
        raise ValueError("unexpected classification")
    return {
        "schema": "far-agent-checker-calibration/1",
        "mode": "CALIBRATION_ONLY_NO_AGENT",
        "classification": classification,
        "diagnostic_codes": diagnostics,
        "conflicting_pairs": extra["conflicting_pairs"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibration-only", action="store_true", required=True)
    parser.add_argument("--arm", choices=("generic_checker", "far"), required=True)
    args = parser.parse_args()
    if not args.calibration_only:
        raise ValueError("no runtime/launch mode exists")
    # Source and currently false execution gates must be verified before any
    # local calibration. This does not satisfy a single external launch gate.
    state = registration.check_candidate(
        registration.PROTOCOL.read_bytes(), registration.LAUNCH.read_bytes())
    if state["model_calls_authorized"] is not False:
        raise ValueError("unexpected active experiment")
    payload = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    try:
        out = evaluate(args.arm, payload)
    except (ValueError, UnicodeError, KeyError, TypeError) as exc:
        out = {
            "schema": "far-agent-checker-calibration/1",
            "mode": "CALIBRATION_ONLY_NO_AGENT",
            "classification": "INVALID",
            "diagnostic_codes": ["INVALID_CALIBRATION_INPUT"],
            "conflicting_pairs": None,
            "error": str(exc),
        }
    print(json.dumps(out, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
