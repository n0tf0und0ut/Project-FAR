"""Research-only declarative weight edits; no loading, code execution or approval.

The caller owns the trusted policy and checkpoint provenance. A successful audit
means only that the resulting tensor obeyed those bounds. It does not approve a
model-generated proposal, establish behavioral benefit, or authorize deployment.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any

SCHEMA = "far-weight-edit/0.1"
_COMMON = {"schema", "tensor", "base_tensor_sha256", "operation"}
_FIELDS = {
    "identity": set(),
    "scale_columns": {"columns", "factor"},
    "project_columns": {"columns", "direction", "strength"},
    "sparse_replace": {"indices", "values"},
}
_POLICY_FIELDS = {
    "tensor", "shape", "dtype", "max_changed_parameters", "max_relative_l2",
    "allowed_operations", "max_columns",
}


def canonical(value: Any) -> bytes:
    """Encode finite JSON with string-only keys and no custom object coercion."""
    def check(item: Any) -> None:
        if item is None or type(item) in (str, bool, int):
            return
        if type(item) is float:
            if not math.isfinite(item):
                raise ValueError("Nonfinite JSON number")
            return
        if type(item) is list:
            for child in item:
                check(child)
            return
        if type(item) is dict:
            if any(type(key) is not str for key in item):
                raise ValueError("JSON object keys must be strings")
            for child in item.values():
                check(child)
            return
        raise ValueError("Only ordinary JSON values are accepted")
    check(value)
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, UnicodeError) as exc:
        raise ValueError("Invalid canonical JSON") from exc


def sha(data: bytes) -> str:
    if type(data) is not bytes:
        raise ValueError("SHA input must be bytes")
    return hashlib.sha256(data).hexdigest()


def _array(value: Any):
    import numpy as np
    if type(value) is not np.ndarray or value.ndim != 2 or min(value.shape) < 1:
        raise ValueError("Tensor must be a nonempty ordinary 2D ndarray")
    if value.dtype.kind != "f" or value.dtype.itemsize not in (2, 4, 8):
        raise ValueError("Tensor dtype must be real float16, float32 or float64")
    if not np.isfinite(value).all():
        raise ValueError("Tensor contains nonfinite values")
    return value


def tensor_sha(value: Any) -> str:
    """Commit dtype (including byte order), shape and C-order tensor bytes."""
    value = _array(value)
    header = canonical({"dtype": value.dtype.str, "shape": list(value.shape)})
    return sha(header + b"\n" + value.tobytes(order="C"))


def _integer(value: Any, name: str, *, low: int = 0, high: int | None = None) -> int:
    if type(value) is not int or value < low or (high is not None and value > high):
        raise ValueError(f"Invalid {name}")
    return value


def _number(value: Any, name: str, *, low: float = 0, high: float | None = None) -> float:
    if type(value) not in (float, int):
        raise ValueError(f"Invalid {name}")
    try:
        output = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"Invalid {name}") from exc
    if not math.isfinite(output) or output < low or (high is not None and output > high):
        raise ValueError(f"Invalid {name}")
    return output


def _norm(value: Any) -> float:
    """L2 norm without overflowing intermediate squares."""
    import numpy as np
    magnitude = float(np.max(np.abs(value)))
    if magnitude == 0:
        return 0.0
    return magnitude * math.sqrt(float(np.square(value / magnitude).sum()))


def _columns(value: Any, width: int, limit: int) -> list[int]:
    if type(value) is not list or not value or len(value) > limit:
        raise ValueError("Invalid columns")
    output = [_integer(x, "column", high=width - 1) for x in value]
    if len(set(output)) != len(output):
        raise ValueError("Duplicate columns")
    return output


def apply_edit(original: Any, proposal: dict, policy: dict):
    """Return a new tensor and reproducible bounded-diff audit, or fail closed.

    Arithmetic is performed in float64 and explicitly rounded to the original
    dtype. ``touched_parameters`` counts addressed locations; ``changed_parameters``
    counts byte-distinct scalar values after rounding (including signed zero).
    Policies must come from the trusted experiment, never from proposal fields.
    """
    import numpy as np
    original = _array(original)
    if type(policy) is not dict or set(policy) != _POLICY_FIELDS:
        raise ValueError("Invalid trusted policy fields")
    if type(proposal) is not dict:
        raise ValueError("Proposal must be an object")
    canonical(policy)
    canonical(proposal)
    if type(policy["tensor"]) is not str or not policy["tensor"]:
        raise ValueError("Invalid policy tensor")
    shape = policy["shape"]
    if type(shape) is not list or len(shape) != 2:
        raise ValueError("Invalid policy shape")
    if tuple(_integer(n, "dimension", low=1) for n in shape) != original.shape:
        raise ValueError("Policy shape differs from tensor")
    if type(policy["dtype"]) is not str:
        raise ValueError("Invalid policy dtype")
    try:
        if np.dtype(policy["dtype"]) != original.dtype:
            raise ValueError("Policy dtype differs from tensor")
    except TypeError as exc:
        raise ValueError("Invalid policy dtype") from exc
    max_changed = _integer(policy["max_changed_parameters"], "changed-parameter budget")
    max_columns = _integer(policy["max_columns"], "column budget", high=original.shape[1])
    max_relative = _number(policy["max_relative_l2"], "relative L2 budget")
    allowed = policy["allowed_operations"]
    if (type(allowed) is not list or not allowed or
            any(type(op) is not str or op not in _FIELDS for op in allowed) or
            len(set(allowed)) != len(allowed)):
        raise ValueError("Invalid allowed operations")
    operation = proposal.get("operation")
    if type(operation) is not str or operation not in allowed:
        raise ValueError("Operation is not admitted by trusted policy")
    if set(proposal) != _COMMON | _FIELDS[operation]:
        raise ValueError("Unexpected or missing proposal fields")
    if proposal["schema"] != SCHEMA or proposal["tensor"] != policy["tensor"]:
        raise ValueError("Schema or target tensor mismatch")
    before_sha = tensor_sha(original)
    if proposal["base_tensor_sha256"] != before_sha:
        raise ValueError("Base tensor commitment mismatch")

    edited = original.copy(order="C")
    touched = 0
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        try:
            if operation in ("scale_columns", "project_columns"):
                cols = _columns(proposal["columns"], original.shape[1], max_columns)
                touched = original.shape[0] * len(cols)
                selected = original[:, cols].astype(np.float64)
                if operation == "scale_columns":
                    factor = _number(proposal["factor"], "factor", high=8)
                    updated = selected * factor
                else:
                    strength = _number(proposal["strength"], "strength", high=8)
                    direction = proposal["direction"]
                    if type(direction) is not list or len(direction) != original.shape[0]:
                        raise ValueError("Direction must match output dimension")
                    if any(type(x) not in (int, float) for x in direction):
                        raise ValueError("Direction must contain ordinary numbers")
                    u = np.array(direction, dtype=np.float64)
                    if not np.isfinite(u).all() or not np.any(u):
                        raise ValueError("Direction must be finite and nonzero")
                    # Normalize before multiplication; scale avoids overflow.
                    u /= np.max(np.abs(u))
                    u /= math.sqrt(float(np.square(u).sum()))
                    updated = selected - strength * u[:, None] * (u @ selected)[None, :]
                edited[:, cols] = updated.astype(original.dtype)
            elif operation == "sparse_replace":
                indices, values = proposal["indices"], proposal["values"]
                if (type(indices) is not list or not indices or type(values) is not list or
                        len(indices) != len(values)):
                    raise ValueError("Invalid sparse replacements")
                seen = set()
                for pair, value in zip(indices, values):
                    if type(pair) is not list or len(pair) != 2:
                        raise ValueError("Invalid sparse coordinate")
                    row = _integer(pair[0], "row", high=original.shape[0] - 1)
                    col = _integer(pair[1], "column", high=original.shape[1] - 1)
                    if (row, col) in seen:
                        raise ValueError("Duplicate sparse coordinate")
                    seen.add((row, col))
                    if type(value) not in (int, float) or not math.isfinite(float(value)):
                        raise ValueError("Sparse replacement must be finite")
                    edited[row, col] = value
                if len({col for _, col in seen}) > max_columns:
                    raise ValueError("Sparse edit exceeds column budget")
                touched = len(seen)
        except (FloatingPointError, OverflowError) as exc:
            raise ValueError("Intervention arithmetic overflowed") from exc
    _array(edited)
    # Bytewise comparison intentionally sees +0.0/-0.0 differences.
    original_bytes = np.ascontiguousarray(original).view(np.uint8).reshape(*original.shape, original.dtype.itemsize)
    edited_bytes = edited.view(np.uint8).reshape(*edited.shape, edited.dtype.itemsize)
    changed = np.any(original_bytes != edited_bytes, axis=-1)
    changed_count = int(changed.sum())
    if changed_count > max_changed:
        raise ValueError("Actual edit exceeds changed-parameter budget")
    delta = edited.astype(np.float64) - original.astype(np.float64)
    if not np.isfinite(delta).all():
        raise ValueError("Tensor delta overflowed")
    old_scale = float(np.max(np.abs(original)))
    if old_scale == 0:
        relative = 0.0 if not np.any(delta) else math.inf
    else:
        # Scale both norms by the same original magnitude before division.
        relative = _norm(delta / old_scale) / _norm(original.astype(np.float64) / old_scale)
    if not math.isfinite(relative) or relative > max_relative:
        raise ValueError("Actual edit exceeds relative L2 budget")
    coords = np.argwhere(changed).tolist()
    audit = {
        "schema": "far-weight-diff/0.1",
        "tensor": policy["tensor"],
        "operation": operation,
        "proposal_sha256": sha(canonical(proposal)),
        "policy_sha256": sha(canonical(policy)),
        "base_tensor_sha256": before_sha,
        "edited_tensor_sha256": tensor_sha(edited),
        "shape": list(original.shape),
        "dtype": original.dtype.str,
        "touched_parameters": touched,
        "changed_parameters": changed_count,
        "numerical_changed_parameters": int(np.count_nonzero(edited != original)),
        "relative_l2": relative,
        "changed_coordinates_sha256": sha(canonical(coords)),
        "interpretation": "MECHANICAL_BOUNDS_ONLY_NO_BEHAVIORAL_OR_PRODUCTION_APPROVAL",
    }
    if len(coords) <= 8192:
        audit["changed_coordinates"] = coords
    else:
        # Runs are [row, first-column, exclusive-end-column], in row-major order.
        runs = []
        for row, col in coords:
            if runs and runs[-1][0] == row and runs[-1][2] == col:
                runs[-1][2] = col + 1
            else:
                runs.append([row, col, col + 1])
        audit["changed_coordinate_row_runs"] = runs
    return edited, audit
