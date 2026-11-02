"""Execution-level FAR routing gate: explicit contracts never require an agent.

Research/operational implementation; not a new FAR evaluation method.
The current FAR verification authorities perform all substantive semantic checks.
Unknown, malformed, or incomplete input enters governed contract discovery.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VERIFIERS = {
    "far-ir/2.0": "mechanization.far_mechanization.contract_v2_strict_v11",
    "far-ir/2.1": "mechanization.far_mechanization.contract_v21_errata1",
}
DECLARATIVE_STEPS = {
    "far-ir/2.0": ("verify_current_far_ir_2_0",),
    "far-ir/2.1": ("verify_current_far_ir_2_1",),
}
ALLOWED_MODES = frozenset({"deterministic", "declarative"})


class RoutingError(ValueError):
    pass


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for k, v in pairs:
        if k in result:
            raise RoutingError("duplicate JSON object key")
        result[k] = v
    return result


def _reject_constant(value: str) -> None:
    raise RoutingError("non-finite JSON constant")


def _check_native(value: Any, seen: set[int] | None = None) -> None:
    if seen is None:
        seen = set()
    if type(value) is dict:
        if id(value) in seen:
            raise RoutingError("cyclic object")
        for k, v in value.items():
            if type(k) is not str:
                raise RoutingError("non-string object key")
            _check_native(v, seen | {id(value)})
    elif type(value) is list:
        if id(value) in seen:
            raise RoutingError("cyclic list")
        for v in value:
            _check_native(v, seen | {id(value)})
    elif type(value) is float:
        if not math.isfinite(value):
            raise RoutingError("nonfinite float")
    elif type(value) not in (str, bool, int, type(None)):
        raise RoutingError("not a native JSON value")


def _parse(raw: str) -> Any:
    try:
        doc = json.loads(raw, object_pairs_hook=_reject_duplicates, parse_constant=_reject_constant)
    except (ValueError, RecursionError, UnicodeError) as exc:
        raise RoutingError("invalid strict JSON: " + type(exc).__name__) from exc
    _check_native(doc)
    return doc


def _discovery(sha: str, reason: str, *, format_version: str | None = None,
               diagnostics: list[str] | None = None) -> dict:
    return {
        "status": "DISCOVERY_REQUIRED",
        "source_sha256": sha,
        "format_version": format_version,
        "route": "methodology/contract-discovery-protocol.md",
        "verifier": None,
        "verifier_success": False,
        "outcome": None,
        "reason": reason,
        "diagnostics": diagnostics or [],
        "model_calls": 0,
        "does_not_bypass_intake": True,
    }


def route_text(raw: str, *, mode: str = "deterministic") -> dict:
    """Decide and execute the authorized route; no autonomous selection.

    Explicit downstream intake bypass requires *successful* semantic validation.
    Rejecting a supplied contract does not authorize a result from that contract.
    """
    if type(raw) is not str:
        raise RoutingError("raw input must be a string")
    if mode not in ALLOWED_MODES:
        raise RoutingError("only deterministic/declarative routes are allowed")
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    try:
        doc = _parse(raw)
    except RoutingError as exc:
        return _discovery(digest, "INVALID_TRANSPORT", diagnostics=[str(exc)])
    if type(doc) is not dict:
        return _discovery(digest, "NOT_STRUCTURED_CONTRACT")
    version = doc.get("format_version")
    if version == "far-intake/1.0":
        return _discovery(digest, "INTAKE_MANIFEST_IS_NOT_DOWNSTREAM_CONTRACT", format_version=version)
    if not isinstance(version, str) or version not in VERIFIERS:
        return _discovery(digest, "NO_RECOGNIZED_EXPLICIT_CONTRACT", format_version=version if type(version) is str else None)

    if mode == "declarative":
        steps = DECLARATIVE_STEPS.get(version)
        if steps != (("verify_current_far_ir_2_0",) if version == "far-ir/2.0"
                     else ("verify_current_far_ir_2_1",)):
            raise RoutingError("declarative workflow drift")
    # Import only the trusted current verifier for the declared format.
    try:
        if version == "far-ir/2.0":
            from mechanization.far_mechanization.contract_v2_strict_v11 import validate_contract
        else:
            from mechanization.far_mechanization.contract_v21_errata1 import validate_contract
        result = validate_contract(doc)
    except Exception as exc:
        # Infrastructure failures never count as validation rejection or a verdict.
        return {
            "status": "VERIFIER_UNAVAILABLE", "source_sha256": digest,
            "format_version": version, "route": None, "verifier": VERIFIERS[version],
            "verifier_success": False, "outcome": None,
            "reason": "VERIFIER_EXECUTION_FAILED", "error_class": type(exc).__name__,
            "diagnostics": [], "model_calls": 0, "does_not_bypass_intake": True,
        }
    diagnostics = [str(d.code) for d in result.diagnostics]
    if not result.success:
        return _discovery(digest, "DOWNSTREAM_CONTRACT_REJECTED",
                          format_version=version, diagnostics=diagnostics)
    reported = doc.get("report", {}).get("outcome")
    # The verifier determines validity; never manufacture a determinate outcome.
    if reported not in ("PROVED", "REFUTED"):
        return _discovery(digest, "OUTCOME_NOT_DETERMINATE", format_version=version)
    return {
        "status": "VERIFIED_EXPLICIT_CONTRACT",
        "source_sha256": digest,
        "format_version": version,
        "route": "verify_current",
        "dispatch_policy": mode,
        "verifier": VERIFIERS[version],
        "verifier_success": True,
        "outcome": reported,
        "reason": "VALIDATED_DOWNSTREAM_CONTRACT",
        "diagnostics": diagnostics,
        "model_calls": 0,
        "does_not_bypass_intake": False,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", help="UTF-8 input file or - for stdin")
    parser.add_argument("--mode", choices=sorted(ALLOWED_MODES), default="deterministic")
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.read() if args.path == "-" else Path(args.path).read_text(encoding="utf-8")
        output = route_text(raw, mode=args.mode)
    except (OSError, ValueError, UnicodeError) as exc:
        print(json.dumps({"status": "INPUT_UNAVAILABLE", "error_class": type(exc).__name__,
                          "model_calls": 0}), file=sys.stderr)
        return 2
    print(json.dumps(output, sort_keys=True, indent=2))
    return {"VERIFIED_EXPLICIT_CONTRACT": 0, "DISCOVERY_REQUIRED": 3}.get(output["status"], 2)


if __name__ == "__main__":
    raise SystemExit(main())
