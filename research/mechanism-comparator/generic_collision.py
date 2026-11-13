"""Generic independent finite-table semantic collision checker (Research only).

No import from Project FAR; consumes the SAME source/representation/behavior
tables and the same JSON Schema as the evaluated FAR verifier.

This checker deliberately does NOT validate freeze hashes, claims, audit
evidence or provenance. Those are separately measured integrity guarantees,
and cost comparisons must never pretend the three lanes do identical work.
"""
from __future__ import annotations

import json
from typing import Any

from jsonschema import Draft202012Validator


class GenericCollisionError(ValueError):
    pass


def canonical(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False,
        allow_nan=False, separators=(",", ":"),
    )


def _table(rows: object, case_ids: set[str], field: str) -> dict[str, str]:
    if not isinstance(rows, list):
        raise GenericCollisionError(field + " table not a list")
    result = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"case_id", "value"}:
            raise GenericCollisionError(field + " row shape invalid")
        key = row["case_id"]
        if type(key) is not str or key in result:
            raise GenericCollisionError(field + " duplicate/invalid case")
        result[key] = canonical(row["value"])
    if set(result) != case_ids:
        raise GenericCollisionError(field + " coverage mismatch")
    return result


def classify(document: object, schema_validator: Draft202012Validator) -> str:
    """Classify NO_LOSS / LOSS / INVALID using schema and explicit table evidence."""
    if not schema_validator.is_valid(document):
        return "INVALID"
    try:
        assert isinstance(document, dict)
        contract: Any = document["contract"]
        cases: Any = contract["source_domain"]["cases"]
        if not isinstance(cases, list):
            raise GenericCollisionError("invalid source cases")
        ids = []
        for item in cases:
            if not isinstance(item, dict) or type(item.get("id")) is not str:
                raise GenericCollisionError("invalid source case id")
            ids.append(item["id"])
        if len(set(ids)) != len(ids):
            raise GenericCollisionError("duplicate source case")
        ids_set = set(ids)
        representation = _table(contract["representation"]["table"], ids_set, "representation")
        behavior = _table(contract["required_behavior"]["table"], ids_set, "required_behavior")
        # O(n): same encoded representation must map to one target outcome.
        targets = {}
        for case in ids:
            rep = representation[case]
            target = behavior[case]
            if rep in targets and targets[rep] != target:
                return "LOSS"
            targets[rep] = target
        return "NO_LOSS"
    except (KeyError, TypeError, ValueError, AssertionError, OverflowError, RecursionError):
        return "INVALID"
