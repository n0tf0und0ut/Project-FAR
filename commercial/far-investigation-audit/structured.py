"""Bounded, deterministic JSON-table arithmetic, not natural-language verification.

Structured data and recorded numeric propositions are kept separate from the
propositional evidence-formula lane. No model calls or external trusted data.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation, localcontext
from typing import Any

MAX_ROWS = 10000
MAX_DIGITS = 40
MAX_DECIMAL_EXPONENT = 40
NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")
# Recognize the *whole* source token, including unsupported notation, before
# accepting a span. A signed, grouped, fractional or scientific number must
# never be converted to a different quantity by selecting only some digits.
# A terminal sentence period is punctuation; a period followed by digits is not.
SOURCE_DECIMAL = r"[-+−]?(?:\d+(?:[.,_]\d+)*|[.,]\d+)(?:[eE][-+−]?\d*)?"
SOURCE_NUMBER = re.compile(rf"{SOURCE_DECIMAL}(?:\s*[/⁄∕:]\s*{SOURCE_DECIMAL})*")


class StructuredInputError(ValueError):
    """Malformed declared computation contract."""


class StructuredUnverifiable(ValueError):
    """Well-formed contract cannot be evaluated against supplied source data."""


def numeric(value: Any) -> Decimal:
    if not isinstance(value, str) or NUMBER.fullmatch(value) is None:
        raise StructuredInputError("expected decimal string without exponent")
    try:
        out = Decimal(value)
    except InvalidOperation as exc:
        raise StructuredInputError("invalid numeric value") from exc
    if not out.is_finite() or len(out.as_tuple().digits) > MAX_DIGITS or abs(out.as_tuple().exponent) > MAX_DECIMAL_EXPONENT:
        raise StructuredInputError("numeric value exceeds bounded finite decimal contract")
    return out


def _duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for k, value in pairs:
        if k in result:
            raise StructuredUnverifiable("source contains duplicate JSON keys")
        result[k] = value
    return result


def _nonfinite(token: str) -> None:
    raise StructuredUnverifiable(f"non-finite source number: {token}")


def parse_snapshot(raw: str) -> Any:
    try:
        return json.loads(raw, parse_float=Decimal, parse_int=int, parse_constant=_nonfinite, object_pairs_hook=_duplicates)
    except InvalidOperation as exc:
        raise StructuredUnverifiable("source number exceeds decimal parser range") from exc
    except (ValueError, TypeError, RecursionError) as exc:
        raise StructuredUnverifiable(f"cannot parse unambiguous JSON source: {exc}") from exc


def pointer(value: Any, path: str) -> Any:
    if not isinstance(path, str) or (path and not path.startswith("/")) or len(path) > 1024:
        raise StructuredInputError("invalid JSON Pointer")
    for part in path.split("/")[1:] if path else []:
        if re.search(r"~(?![01])", part):
            raise StructuredInputError("invalid JSON Pointer escape")
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict):
            if part not in value:
                raise StructuredUnverifiable(f"JSON Pointer field absent: {part!r}")
            value = value[part]
        elif isinstance(value, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", part):
                raise StructuredInputError("invalid JSON array index")
            idx = int(part)
            if idx >= len(value):
                raise StructuredUnverifiable("JSON array index out of bounds")
            value = value[idx]
        else:
            raise StructuredUnverifiable("JSON Pointer descends into scalar")
    return value


def _sum_field(rows: list[Any], field: str) -> Decimal:
    total = Decimal(0)
    with localcontext() as ctx:
        # A 40-digit coefficient at exponent +40 and a term at -40 can
        # occupy 120 significant places. Reserve row-count carry places too;
        # 100 digits silently lost small terms before later cancellation.
        ctx.prec = MAX_DIGITS + 2 * MAX_DECIMAL_EXPONENT + len(str(MAX_ROWS))
        for row in rows:
            if not isinstance(row, dict) or field not in row:
                raise StructuredUnverifiable("sum field missing or row is not an object")
            value = row[field]
            if isinstance(value, bool) or not isinstance(value, (int, Decimal)):
                raise StructuredUnverifiable("sum field is not a finite JSON number")
            value = Decimal(value)
            if (not value.is_finite() or len(value.as_tuple().digits) > MAX_DIGITS or
                    abs(value.as_tuple().exponent) > MAX_DECIMAL_EXPONENT):
                raise StructuredUnverifiable("source numeric value exceeds bounded decimal contract")
            total += value
        return +total


def _strict_equal(left: Any, right: Any) -> bool:
    # Do not allow e.g. True == 1 to turn a boolean into a count selector.
    return type(left) is type(right) and left == right


def evaluate_structured(claim: dict[str, Any], evidence: dict[str, Any], source_text: str,
                        *, claim_source_text: str) -> dict[str, Any]:
    """Check a recorded number against a disclosed computation on frozen JSON.

    Even a match is conditional on correct field selection, metric definition,
    origin, source authenticity, population, timing, and claim interpretation.
    """
    config = evidence.get("data_check")
    if not isinstance(config, dict) or set(config) not in (
        {"operation", "pointer"}, {"operation", "pointer", "field"},
        {"operation", "pointer", "where"},
    ):
        raise StructuredInputError("data_check requires exact operation/pointer/field or where schema")
    op = config.get("operation")
    if op not in ("count_rows", "count_where", "sum_field"):
        raise StructuredInputError("unsupported structured operation")
    if op == "count_rows" and set(config) != {"operation", "pointer"}:
        raise StructuredInputError("count_rows accepts only operation and pointer")
    if op == "sum_field" and set(config) != {"operation", "pointer", "field"}:
        raise StructuredInputError("sum_field requires field")
    if op == "count_where" and set(config) != {"operation", "pointer", "where"}:
        raise StructuredInputError("count_where requires where")
    quantity = claim.get("quantity")
    if not isinstance(quantity, dict) or set(quantity) != {"value", "number_span", "unit"}:
        raise StructuredInputError("claim quantity requires value, number_span, unit")
    value = numeric(quantity["value"])
    unit = quantity["unit"]
    if not isinstance(unit, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,39}", unit):
        raise StructuredInputError("invalid quantity unit")
    token = quantity["number_span"]
    if not isinstance(token, dict) or set(token) != {"start", "end"}:
        raise StructuredInputError("invalid quantity number_span")
    start, end = token["start"], token["end"]
    quote = claim["span"]["quote"]
    if type(start) is not int or type(end) is not int or not (0 <= start < end <= len(quote)):
        raise StructuredInputError("quantity number_span outside claimed quotation")
    if quote[start:end] != quantity["value"]:
        raise StructuredInputError("quantity token does not match the attributed source quotation")
    literal_text = claim_source_text
    offset = claim["span"]["start"]
    if not any(match.span() == (offset + start, offset + end)
               and (match.start() == 0 or not (
                   literal_text[match.start() - 1].isalnum() or literal_text[match.start() - 1] == "_"))
               and (match.end() == len(literal_text) or not (
                   literal_text[match.end()].isalnum() or literal_text[match.end()] == "_"))
               for match in SOURCE_NUMBER.finditer(literal_text)):
        raise StructuredInputError("quantity span must cover a complete numeric literal")
    if not isinstance(config["pointer"], str):
        raise StructuredInputError("JSON Pointer must be a string")
    if op == "sum_field":
        field = config["field"]
        if not isinstance(field, str) or not 1 <= len(field) <= 100:
            raise StructuredInputError("invalid sum field")
    if op == "count_where":
        where = config["where"]
        if not isinstance(where, dict) or set(where) != {"field", "equals"}:
            raise StructuredInputError("where requires field and equals")
        if not isinstance(where["field"], str) or not 1 <= len(where["field"]) <= 100:
            raise StructuredInputError("invalid where field")
        expected = where["equals"]
        if not (type(expected) in (str, int, bool) or expected is None):
            raise StructuredInputError("where value must be string, integer, boolean, or null")
    try:
        data = parse_snapshot(source_text)
        rows = pointer(data, config["pointer"])
        if not isinstance(rows, list) or len(rows) > MAX_ROWS:
            raise StructuredUnverifiable("source selection is not a bounded JSON list")
        if op == "count_rows":
            computed = Decimal(len(rows))
        elif op == "sum_field":
            computed = _sum_field(rows, field)
        else:
            computed = Decimal(0)
            for row in rows:
                if not isinstance(row, dict) or where["field"] not in row:
                    raise StructuredUnverifiable("where field missing or row not an object")
                if _strict_equal(row[where["field"]], expected):
                    computed += 1
        return {"status": "STRUCTURED_VALUE_MATCH" if computed == value else "STRUCTURED_VALUE_MISMATCH",
                "declared_value": quantity["value"], "computed_value": format(computed, "f"),
                "unit": unit, "operation": op, "rows_inspected": len(rows),
                "semantic_mapping_verified": False, "source_authenticity_verified": False}
    except StructuredUnverifiable as exc:
        return {"status": "STRUCTURED_UNVERIFIABLE", "reason": str(exc),
                "declared_value": quantity["value"], "unit": unit,
                "semantic_mapping_verified": False, "source_authenticity_verified": False}
