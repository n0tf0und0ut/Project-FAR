"""Research-only deterministic semantic guard for bounded agent success metrics.

Adapts NVIDIA Auto Ontology's definition/answerability/provenance pattern without
running its services. Inputs are declared observations, not authenticated ground
truth; no FAR theory or general agent-reliability claim is certified here.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
import hashlib
import json
import re
from pathlib import Path
from typing import Any

FORMAT = "far-metric-grounding/0.1"
DATA_FORMAT = "far-metric-events/0.1"
CATALOG_FORMAT = "far-metric-catalog/0.1"
MAX_SLOTS = 10000
MAX_BYTES = 4_000_000
STATUS = {"success", "failure", "abstain", "unknown"}
OPS = {
    "registered_success_rate": {"unit": "percent", "formula": "success / registered", "arms": 1},
    "paired_success_delta_pp": {"unit": "percentage_points", "formula": "100 * (treatment_success / treatment_registered - control_success / control_registered)", "arms": 2},
}


class GroundingError(ValueError):
    """An invalid or unanswerable metric request; no numeric answer is authorized."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _require(test: bool, code: str, message: str):
    if not test:
        raise GroundingError(code, message)


def _unique_object(items):
    result = {}
    for key, val in items:
        _require(key not in result, "DUPLICATE_JSON_KEY", f"duplicate JSON key: {key}")
        result[key] = val
    return result


def strict_load(raw: bytes):
    _require(len(raw) <= MAX_BYTES, "SIZE_LIMIT", "input exceeds size limit")
    def forbidden_constant(val):
        raise GroundingError("NONFINITE_NUMBER", f"invalid JSON constant: {val}")
    def forbidden_float(val):
        raise GroundingError("FLOAT_FORBIDDEN", "use exact decimal strings, not floats")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object,
                          parse_constant=forbidden_constant, parse_float=forbidden_float)
    except (ValueError, UnicodeError) as exc:
        if isinstance(exc, GroundingError):
            raise
        raise GroundingError("INVALID_JSON", str(exc)) from exc


def _keys(value: Any, required: set[str], place: str):
    _require(type(value) is dict and set(value) == required,
             "BAD_SHAPE", f"{place} must contain exactly {sorted(required)}")


def _id(value: Any) -> bool:
    return type(value) is str and bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}", value))


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def catalog_validate(catalog: dict):
    _keys(catalog, {"format", "status", "metrics"}, "catalog")
    _require(catalog["format"] == CATALOG_FORMAT and catalog["status"] == "Research",
             "CATALOG_IDENTITY", "catalog format/status mismatch")
    _require(type(catalog["metrics"]) is list and 1 <= len(catalog["metrics"]) <= 2,
             "CATALOG_METRICS", "catalog needs supported metrics")
    seen = set()
    for entry in catalog["metrics"]:
        _keys(entry, {"id", "operator", "unit", "formula", "definition", "review_status"}, "metric")
        _require(_id(entry["id"]) and entry["id"] not in seen,
                 "METRIC_ID", "duplicate or invalid metric id")
        seen.add(entry["id"])
        _require(type(entry["operator"]) is str and entry["operator"] in OPS, "UNKNOWN_OPERATOR", "operator not implemented")
        contract = OPS[entry["operator"]]
        _require(entry["unit"] == contract["unit"] and entry["formula"] == contract["formula"],
                 "METRIC_REDEFINITION", "numeric meaning differs from executed operator")
        _require(type(entry["definition"]) is str and 0 < len(entry["definition"]) <= 1000,
                 "METRIC_DEFINITION", "metric needs a bounded description")
        _require(entry["review_status"] == "UNREVIEWED_RESEARCH",
                 "FALSE_CERTIFICATION", "this pilot cannot assert human certification")


def events_validate(data: dict):
    _keys(data, {"format", "study_id", "scope", "sources", "registered_slots", "observations"}, "events")
    _require(data["format"] == DATA_FORMAT and _id(data["study_id"]) and _id(data["scope"]),
             "EVENT_IDENTITY", "event dataset identity is invalid")
    _require(type(data["sources"]) is list and 1 <= len(data["sources"]) <= 100,
             "SOURCE_REGISTRY", "explicit source registry required")
    ids = set()
    for item in data["sources"]:
        _keys(item, {"id", "uri", "sha256", "assurance"}, "source")
        _require(_id(item["id"]) and item["id"] not in ids and
                 type(item["uri"]) is str and item["uri"].startswith(("https://", "file:")) and
                 type(item["sha256"]) is str and bool(re.fullmatch(r"[0-9a-f]{64}", item["sha256"])) and
                 item["assurance"] == "DECLARED_NOT_INDEPENDENTLY_VERIFIED",
                 "BAD_SOURCE", "source needs distinct identity, URI, digest, and honest assurance")
        ids.add(item["id"])
    slots = data["registered_slots"]
    _require(type(slots) is list and 1 <= len(slots) <= MAX_SLOTS,
             "REGISTERED_EXPOSURE", "registered eligible exposure is required")
    slot_map = {}
    cases = {"control": set(), "treatment": set()}
    for s in slots:
        _keys(s, {"id", "case_id", "arm"}, "registered slot")
        _require(_id(s["id"]) and _id(s["case_id"]) and
                 type(s["arm"]) is str and s["arm"] in cases and s["id"] not in slot_map and
                 s["case_id"] not in cases[s["arm"]],
                 "DUPLICATE_OR_INVALID_SLOT", "registered slot identity/arm invalid")
        slot_map[s["id"]] = s
        cases[s["arm"]].add(s["case_id"])
    observations = data["observations"]
    _require(type(observations) is list and len(observations) <= MAX_SLOTS,
             "OBSERVATIONS", "invalid observation list")
    by_slot = {}
    for o in observations:
        _keys(o, {"slot_id", "outcome", "source_id"}, "observation")
        _require(_id(o["slot_id"]) and o["slot_id"] in slot_map and
                 o["slot_id"] not in by_slot and type(o["outcome"]) is str and o["outcome"] in STATUS and
                 type(o["source_id"]) is str and o["source_id"] in ids,
                 "INVALID_OBSERVATION", "observation slot/outcome/source invalid or duplicated")
        by_slot[o["slot_id"]] = o
    return slot_map, by_slot, cases


def _as_display(value: Fraction, digits: int):
    _require(type(digits) is int and 0 <= digits <= 8, "SCALE", "digits must be 0..8")
    with localcontext() as ctx:
        ctx.prec = 60
        number = Decimal(value.numerator) / Decimal(value.denominator)
        return format(number.quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_EVEN), "f")


def answer(catalog: dict, data: dict, *, metric_id: str, arm: str | None = None,
           digits: int = 4, asserted_value: str | None = None) -> dict:
    """Compute a scoped metric. Missing/unknown observations make it unanswerable."""
    catalog_validate(catalog)
    slot_map, by_slot, cases = events_validate(data)
    definitions = {x["id"]: x for x in catalog["metrics"]}
    _require(type(metric_id) is str and metric_id in definitions, "UNANSWERABLE_METRIC", "metric is absent from declared catalog")
    spec = definitions[metric_id]
    operator = spec["operator"]
    if operator == "registered_success_rate":
        _require(type(arm) is str and arm in cases, "ARM_REQUIRED", "success rate requires one declared arm")
        arms = [arm]
    else:
        _require(arm is None, "WRONG_QUERY_SCOPE", "paired difference has no single arm filter")
        arms = ["control", "treatment"]
        _require(bool(cases["control"]) and cases["control"] == cases["treatment"],
                 "UNPAIRED_EXPOSURE", "arms must contain identical registered case IDs")
    grouped = {}
    for member in arms:
        rows = [s for s in slot_map.values() if s["arm"] == member]
        _require(len(rows) > 0, "EMPTY_ARM", "no eligible registered slots for arm")
        missing = [s["id"] for s in rows if s["id"] not in by_slot]
        _require(not missing, "MISSING_OBSERVATION", "missing registered observations: " + ",".join(sorted(missing)[:5]))
        unknown = [s["id"] for s in rows if by_slot[s["id"]]["outcome"] == "unknown"]
        _require(not unknown, "UNKNOWN_OUTCOME", "unknown outcomes: " + ",".join(sorted(unknown)[:5]))
        success = sum(by_slot[s["id"]]["outcome"] == "success" for s in rows)
        grouped[member] = {"success": success, "registered": len(rows)}
    if operator == "registered_success_rate":
        a = grouped[arm]
        value = Fraction(100 * a["success"], a["registered"])
    else:
        control, treat = grouped["control"], grouped["treatment"]
        value = 100 * (Fraction(treat["success"], treat["registered"]) -
                       Fraction(control["success"], control["registered"]))
    rendered = _as_display(value, digits)
    if asserted_value is not None:
        _require(type(asserted_value) is str and bool(re.fullmatch(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?", asserted_value)),
                 "ASSERTION_FORMAT", "proposed value must be a finite decimal string")
        _require(Decimal(asserted_value) == Decimal(rendered) and
                 len(asserted_value.partition(".")[2]) == digits,
                 "NUMERIC_CLAIM_MISMATCH", "proposed value disagrees with executed metric at declared precision")
    return {
        "format": FORMAT,
        "status": "DERIVED_FROM_DECLARED_EVENTS",
        "study_id": data["study_id"], "scope": data["scope"],
        "metric_id": metric_id, "operator": operator, "unit": spec["unit"],
        "arm": arm, "groups": grouped, "value": rendered, "digits": digits,
        "exact_fraction": {"numerator": value.numerator, "denominator": value.denominator},
        "source_ids": sorted({by_slot[s["id"]]["source_id"] for s in slot_map.values() if s["arm"] in arms}),
        "source_registry": sorted([x.copy() for x in data["sources"]], key=lambda x: x["id"]),
        "evidence_assurance": "SOURCE_REFERENCES_UNVERIFIED; NO_GENERAL_RELIABILITY_CLAIM",
    }


def evaluate(catalog_raw: bytes, data_raw: bytes, **kwargs):
    receipt = answer(strict_load(catalog_raw), strict_load(data_raw), **kwargs)
    receipt["catalog_sha256"] = _hash(catalog_raw)
    receipt["events_sha256"] = _hash(data_raw)
    return receipt


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--catalog", required=True, type=Path)
    ap.add_argument("--events", required=True, type=Path)
    ap.add_argument("--metric", required=True)
    ap.add_argument("--arm", choices=("control", "treatment"))
    ap.add_argument("--digits", type=int, default=4)
    ap.add_argument("--assert-value")
    args = ap.parse_args(argv)
    try:
        report = evaluate(args.catalog.read_bytes(), args.events.read_bytes(),
                          metric_id=args.metric, arm=args.arm, digits=args.digits,
                          asserted_value=args.assert_value)
    except (OSError, GroundingError) as exc:
        report = {"format": FORMAT, "status": "UNANSWERABLE",
                  "code": exc.code if isinstance(exc, GroundingError) else "FILE_ERROR",
                  "reason": str(exc)}
        print(json.dumps(report, sort_keys=True))
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
