"""Strict JSON ingestion for commercial FAR decision artifacts.

Duplicate object members and non-finite numbers are rejected before domain
validation so two consumers cannot silently interpret the same bytes differently.
"""

from __future__ import annotations

import json
import math
from typing import Any


def _unique_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    members: dict[str, Any] = {}
    for key, value in pairs:
        if key in members:
            raise ValueError(f"duplicate JSON object member {key!r}")
        members[key] = value
    return members


def _reject_constant(token: str) -> None:
    raise ValueError(f"non-JSON numeric constant {token!r}")


def _finite_float(token: str) -> float:
    result = float(token)
    if not math.isfinite(result):
        raise ValueError(f"non-finite JSON number {token!r}")
    return result


def loads_strict(source: str) -> Any:
    """Parse JSON without duplicate members, NaN/Infinity or float overflow."""
    return json.loads(
        source,
        object_pairs_hook=_unique_members,
        parse_constant=_reject_constant,
        parse_float=_finite_float,
    )
