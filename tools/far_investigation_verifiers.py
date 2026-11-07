"""Bounded native verifiers for Research investigation contracts.

These functions validate declared calculations and byte projections. They never
turn a retrieved quotation or a model's semantic label into an external-world
proof. A determinate result concerns only the explicitly returned native scope.
The governed intake/freeze layer remains responsible for contract chronology.
"""
from __future__ import annotations

import ast
import itertools
import math
import operator
import re
from fractions import Fraction
from typing import Any

from mechanization.far_mechanization.intake_v1 import _strict_json_loads
from tools.far_investigation_retrieval import parse_receipt, receipt_bytes

MAX_EXPRESSION = 1024
MAX_AST_NODES = 96
MAX_NUMBER_BITS = 256
MAX_RESULT_BITS = 1024
MAX_STATISTICAL_COUNT = 1_000_000_000_000
NORMAL_975 = 1.959963984540054
CLAIM_TYPES = frozenset({"factual", "quantitative", "mathematical", "causal", "normative", "ambiguous"})
RELATIONS = frozenset({"SUPPORT", "CONTRADICT", "CONTEXT", "UNKNOWN"})
COMPARISONS = {"eq": operator.eq, "lt": operator.lt, "le": operator.le,
               "gt": operator.gt, "ge": operator.ge}
NUMBER = re.compile(r"(?<![\w.])(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?(?!\w|\.\d)")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _native(value: Any, depth: int = 0) -> None:
    _require(depth < 32, "plan nesting exceeds resource bound")
    if type(value) is dict:
        _require(len(value) <= 256, "plan object exceeds resource bound")
        _require(all(type(k) is str for k in value), "plan keys must be strings")
        for item in value.values():
            _native(item, depth + 1)
    elif type(value) is list:
        _require(len(value) <= 256, "plan array exceeds resource bound")
        for item in value:
            _native(item, depth + 1)
    elif type(value) is str:
        _require(len(value) <= 32_768, "plan string exceeds resource bound")
    elif type(value) is int:
        _require(value.bit_length() <= MAX_NUMBER_BITS, "integer exceeds resource bound")
    elif type(value) is float:
        _require(math.isfinite(value), "nonfinite number")
    else:
        _require(value is None or type(value) is bool, "non-JSON plan value")


def _fraction(text: str) -> Fraction:
    _require(type(text) is str and 0 < len(text) <= 128, "invalid numeric literal")
    _require(NUMBER.fullmatch(text) is not None, "number must be an unsigned decimal literal")
    if "e" in text.lower():
        _require(abs(int(text.lower().split("e")[1])) <= 100, "numeric exponent exceeds resource bound")
    value = Fraction(text)
    _require(max(value.numerator.bit_length(), value.denominator.bit_length()) <= MAX_NUMBER_BITS,
             "number exceeds resource bound")
    return value


def _numeric_text(value: Any) -> str:
    _require(type(value) in (int, str), "numeric contract value must be string or integer, not bool/float")
    result = str(value)
    _require(0 < len(result) <= 128, "numeric contract value exceeds resource bound")
    return result


def _source(source_id: str, sources: dict) -> tuple[dict, str]:
    _require(type(source_id) is str and source_id in sources, "unknown source reference")
    receipt = sources[source_id]
    _require(type(receipt) is dict, "source receipt must be object")
    try:
        projection = parse_receipt(receipt)
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError("source receipt cannot be authenticated to preserved bytes") from exc
    return receipt, projection["text"]


def _evidence(evidence_id: str, sources: dict, evidence: dict) -> dict:
    _require(type(evidence_id) is str and evidence_id in evidence, "unknown evidence reference")
    row = evidence[evidence_id]
    _require(type(row) is dict, "evidence must be object")
    _, text = _source(row.get("source_id"), sources)
    quote = row.get("quote")
    _require(type(quote) is str and 0 < len(quote) <= 32_768 and quote in text,
             "evidence quotation does not occur in preserved source projection")
    relation = row.get("relation", "UNKNOWN")
    _require(type(relation) is str and relation in RELATIONS, "invalid evidence relation")
    return row


def _bindings(plan: dict, sources: dict, evidence: dict) -> tuple[dict[str, Fraction], set[str]]:
    bindings = plan.get("bindings", {})
    _require(type(bindings) is dict and len(bindings) <= 32, "invalid arithmetic bindings")
    values, tokens = {}, set()
    for name, binding in bindings.items():
        _require(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,31}", name) is not None,
                 "binding name must be a bounded identifier")
        _require(type(binding) is dict and set(binding) == {"evidence_id", "value"},
                 "binding must name exactly evidence_id and value")
        row = _evidence(binding["evidence_id"], sources, evidence)
        raw = _numeric_text(binding["value"])
        _require(raw in {m.group() for m in NUMBER.finditer(row["quote"])},
                 "binding number absent from exact evidence quote")
        values[name] = _fraction(raw)
        tokens.add(raw)
    return values, tokens


def _expression(text: str, values: dict[str, Fraction], allowed_numbers: set[str]) -> Fraction:
    _require(type(text) is str and 0 < len(text) <= MAX_EXPRESSION, "expression exceeds resource bound")
    try:
        root = ast.parse(text, mode="eval")
    except (SyntaxError, RecursionError, ValueError) as exc:
        raise ValueError("arithmetic expression is not valid bounded syntax") from exc
    _require(sum(1 for _ in ast.walk(root)) <= MAX_AST_NODES, "expression node count exceeds resource bound")

    def evaluate(node: ast.AST) -> Fraction:
        if isinstance(node, ast.Expression):
            result = evaluate(node.body)
        elif isinstance(node, ast.Constant):
            _require(type(node.value) in (int, float), "only numeric literals are allowed")
            token = ast.get_source_segment(text, node)
            _require(token in allowed_numbers, "arithmetic number lacks question/evidence provenance")
            result = _fraction(token)
        elif isinstance(node, ast.Name):
            _require(node.id in values, "arithmetic name lacks evidence binding")
            result = values[node.id]
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            result = evaluate(node.operand)
            if isinstance(node.op, ast.USub):
                result = -result
        elif isinstance(node, ast.BinOp) and type(node.op) in (ast.Add, ast.Sub, ast.Mult, ast.Div):
            left, right = evaluate(node.left), evaluate(node.right)
            _require(not isinstance(node.op, ast.Div) or right != 0, "division by zero")
            result = {ast.Add: operator.add, ast.Sub: operator.sub,
                      ast.Mult: operator.mul, ast.Div: operator.truediv}[type(node.op)](left, right)
        else:
            raise ValueError("unsupported arithmetic syntax; no calls, powers, containers or attributes")
        _require(max(result.numerator.bit_length(), result.denominator.bit_length()) <= MAX_RESULT_BITS,
                 "arithmetic result exceeds resource bound")
        return result

    return evaluate(root)


def _arithmetic(plan: dict, question: str, sources: dict, evidence: dict) -> tuple[Fraction, Fraction]:
    _require(set(plan) <= {"kind", "expression", "operator", "expected", "bindings"}
             and {"kind", "expression", "operator", "expected"} <= set(plan),
             "arithmetic contract fields invalid")
    _require(type(plan["operator"]) is str and plan["operator"] in COMPARISONS,
             "unsupported arithmetic comparison")
    values, bound_numbers = _bindings(plan, sources, evidence)
    allowed = {m.group() for m in NUMBER.finditer(question)} | bound_numbers
    actual = _expression(plan["expression"], values, allowed)
    expected = _expression(_numeric_text(plan["expected"]), values, allowed)
    return actual, expected


def _pointer(document: Any, pointer: str) -> Any:
    _require(type(pointer) is str and len(pointer) <= 2048, "invalid JSON pointer")
    if pointer == "":
        return document
    _require(pointer.startswith("/"), "JSON pointer must be empty or start with slash")
    current = document
    for raw in pointer.split("/")[1:]:
        _require(re.search(r"~(?![01])", raw) is None, "invalid JSON pointer escape")
        key = raw.replace("~1", "/").replace("~0", "~")
        if type(current) is dict:
            _require(key in current, "JSON pointer absent from source")
            current = current[key]
        elif type(current) is list:
            _require(re.fullmatch(r"0|[1-9]\d*", key) is not None and len(key) <= 8,
                     "invalid JSON array index")
            index = int(key)
            _require(index < len(current), "JSON array index out of range")
            current = current[index]
        else:
            raise ValueError("JSON pointer traverses scalar")
    return current


def _json_projection(plan: dict, question: str, sources: dict) -> Any:
    _require(set(plan) == {"kind", "source_id", "pointer", "operator", "expected", "expected_quote"},
             "source JSON contract fields invalid")
    _require(plan["operator"] == "eq", "source JSON supports exact equality only")
    quote = plan["expected_quote"]
    _require(type(quote) is str and bool(quote) and quote in question,
             "expected quote must occur exactly in original question")
    expected = plan["expected"]
    _require(type(expected) in (str, bool, int, float, type(None)), "expected JSON value must be scalar")
    if type(expected) is str:
        _require(bool(expected) and expected in quote, "expected string absent from question quote")
    elif type(expected) in (int, float):
        _require(type(expected) is not float, "JSON expected numeric value must be integer or quoted source string")
        _require(str(abs(expected)) in {m.group() for m in NUMBER.finditer(quote)},
                 "expected number absent from question quote")
        if expected < 0:
            _require(str(expected) in quote, "expected numeric sign absent from question quote")
    else:
        lexical = "null" if expected is None else ("true" if expected else "false")
        _require(re.search(r"(?<!\w)" + lexical + r"(?!\w)", quote) is not None,
                 "expected JSON scalar absent from question quote")
    receipt, _ = _source(plan["source_id"], sources)
    try:
        document = _strict_json_loads(receipt_bytes(receipt).decode("utf-8"))
    except (ValueError, UnicodeError, KeyError, TypeError) as exc:
        raise ValueError("source is not strict UTF-8 JSON") from exc
    return _pointer(document, plan["pointer"])


def _two_proportion(plan: dict, question: str, sources: dict, evidence: dict) -> list[tuple[int, int]]:
    _require(set(plan) <= {"kind", "groups", "bindings", "question"}
             and {"kind", "groups", "bindings"} <= set(plan),
             "two-proportion contract fields invalid")
    _require("question" not in plan or plan["question"] == question,
             "statistical contract cannot replace original question")
    groups = plan["groups"]
    _require(type(groups) is list and len(groups) == 2, "exactly two groups required")
    values, _ = _bindings(plan, sources, evidence)
    counts = []
    for group in groups:
        _require(type(group) is dict and set(group) == {"successes", "total"},
                 "each group must bind successes and total")
        names = [group["successes"], group["total"]]
        _require(all(type(name) is str and name in values for name in names),
                 "statistical counts require quotation-backed numeric bindings")
        success, total = (values[name] for name in names)
        _require(success.denominator == total.denominator == 1,
                 "statistical counts must be integers")
        s, n = int(success), int(total)
        _require(0 <= s <= n and 0 < n <= MAX_STATISTICAL_COUNT,
                 "statistical counts require 0 <= successes <= positive bounded total")
        counts.append((s, n))
    return counts


def _wilson(successes: int, total: int) -> tuple[float, float]:
    """Wilson score interval, no continuity correction; fixed nominal 95%."""
    proportion = successes / total
    z2 = NORMAL_975 * NORMAL_975
    denominator = 1 + z2 / total
    center = (proportion + z2 / (2 * total)) / denominator
    half_width = NORMAL_975 * math.sqrt(proportion * (1 - proportion) / total
                                       + z2 / (4 * total * total)) / denominator
    return max(0.0, center - half_width), min(1.0, center + half_width)


def _formula(text: str) -> tuple[ast.Expression, set[str], int]:
    _require(type(text) is str and 0 < len(text) <= 4096, "formula length exceeds resource bound")
    try:
        root = ast.parse(text, mode="eval")
    except (SyntaxError, ValueError, RecursionError) as exc:
        raise ValueError("invalid bounded propositional formula") from exc
    nodes = list(ast.walk(root))
    _require(len(nodes) <= 512, "formula node count exceeds resource bound")
    variables = set()
    for node in nodes:
        if isinstance(node, ast.Name):
            _require(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,31}", node.id) is not None,
                     "invalid propositional variable")
            variables.add(node.id)
        elif isinstance(node, ast.Constant):
            _require(type(node.value) is bool, "only Boolean constants are allowed in a formula")
        elif not isinstance(node, (ast.Expression, ast.BoolOp, ast.UnaryOp, ast.And, ast.Or, ast.Not, ast.Load)):
            raise ValueError("formula permits only variables, Boolean constants, and/or/not")
        if isinstance(node, ast.UnaryOp):
            _require(isinstance(node.op, ast.Not), "only propositional not is allowed")
    return root, variables, len(nodes)


def _truth_table(plan: dict, question: str) -> tuple[list[ast.Expression], ast.Expression, list[str]]:
    _require(set(plan) == {"kind", "premises", "conclusion", "premise_quote", "conclusion_quote"},
             "truth-table contract fields invalid")
    premises = plan["premises"]
    _require(type(premises) is list and len(premises) <= 32,
             "premises must be a bounded formula list")
    for field in ("premise_quote", "conclusion_quote"):
        _require(type(plan[field]) is str and bool(plan[field]) and plan[field] in question,
                 "formal quote must occur exactly in original question")
    _require(all(type(p) is str and p in plan["premise_quote"] for p in premises),
             "each premise formula must occur literally in premise_quote")
    _require(type(plan["conclusion"]) is str and plan["conclusion"] in plan["conclusion_quote"],
             "conclusion formula must occur literally in conclusion_quote")
    parsed = [_formula(text) for text in [*premises, plan["conclusion"]]]
    variables = set().union(*(row[1] for row in parsed))
    _require(len(variables) <= 8 and sum(row[2] for row in parsed) <= 512,
             "truth table exceeds eight variables or 512 total syntax nodes")
    return [row[0] for row in parsed[:-1]], parsed[-1][0], sorted(variables)


def _truth_value(node: ast.AST, valuation: dict[str, bool]) -> bool:
    if isinstance(node, ast.Expression):
        return _truth_value(node.body, valuation)
    if isinstance(node, ast.Name):
        return valuation[node.id]
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp):
        return not _truth_value(node.operand, valuation)
    if isinstance(node.op, ast.And):
        return all(_truth_value(value, valuation) for value in node.values)
    return any(_truth_value(value, valuation) for value in node.values)


def validate_plan(plan: dict, question: str, sources: dict, evidence: dict) -> None:
    """Validate a complete bounded native contract before the intake freezes it."""
    _require(type(plan) is dict, "native contract must be object")
    _require(type(question) is str and 0 < len(question) <= 200_000, "invalid question")
    _require(type(sources) is dict and type(evidence) is dict, "invalid source/evidence maps")
    _native(plan)
    kind = plan.get("kind")
    if kind == "exact_arithmetic":
        _arithmetic(plan, question, sources, evidence)
    elif kind == "source_json":
        _json_projection(plan, question, sources)
    elif kind == "two_proportion":
        _two_proportion(plan, question, sources, evidence)
    elif kind == "truth_table":
        _truth_table(plan, question)
    elif kind == "evidence_assessment":
        _require(set(plan) <= {"kind", "evidence_ids", "claim_type", "question"}
                 and {"kind", "evidence_ids", "claim_type"} <= set(plan),
                 "evidence assessment fields invalid")
        _require(type(plan["claim_type"]) is str and plan["claim_type"] in CLAIM_TYPES,
                 "unknown claim type")
        _require("question" not in plan or plan["question"] == question,
                 "assessment cannot replace original question")
        ids = plan["evidence_ids"]
        _require(type(ids) is list and len(ids) <= 128 and all(type(i) is str for i in ids)
                 and len(ids) == len(set(ids)),
                 "evidence IDs must be a bounded unique list")
        for ident in ids:
            _evidence(ident, sources, evidence)
    else:
        raise ValueError("unsupported native verification kind")


def verify(plan: dict, question: str, sources: dict, evidence: dict) -> dict:
    """Evaluate only a validated native contract; never infer source truth."""
    validate_plan(plan, question, sources, evidence)
    kind = plan["kind"]
    common = {"method": kind, "counterexample": None}
    if kind == "exact_arithmetic":
        actual, expected = _arithmetic(plan, question, sources, evidence)
        passed = COMPARISONS[plan["operator"]](actual, expected)
        return {**common, "outcome": "PROVED" if passed else "REFUTED",
                "scope": "Exact rational comparison of the declared expression and expected value only.",
                "calculation": {"expression": plan["expression"], "actual": str(actual),
                                "operator": plan["operator"], "expected": str(expected)},
                "counterexample": None if passed else {"actual": str(actual), "expected": str(expected)},
                "uncertainty": ["The semantic translation from natural language to this expression is not proved.",
                                "Source-bound numbers retain their source's factual and measurement uncertainty."],
                "next_evidence": ["Independently validate the estimand, units, denominator and semantic translation."]}
    if kind == "source_json":
        observed = _json_projection(plan, question, sources)
        passed = type(observed) is type(plan["expected"]) and observed == plan["expected"]
        return {**common, "outcome": "PROVED" if passed else "REFUTED",
                "scope": "Exact typed JSON equality at the declared pointer in preserved source bytes only.",
                "projection": {"source_id": plan["source_id"], "pointer": plan["pointer"], "observed": observed,
                               "expected": plan["expected"], "source_sha256": sources[plan["source_id"]]["sha256"]},
                "counterexample": None if passed else {"observed": observed, "expected": plan["expected"]},
                "uncertainty": ["Source authority, source truth and the natural-language-to-pointer mapping remain unverified."],
                "next_evidence": ["Validate source applicability and compare a causally independent primary record."]}
    if kind == "two_proportion":
        counts = _two_proportion(plan, question, sources, evidence)
        (s1, n1), (s2, n2) = counts
        p1, p2 = Fraction(s1, n1), Fraction(s2, n2)
        difference = p1 - p2
        low1, high1 = _wilson(s1, n1)
        low2, high2 = _wilson(s2, n2)
        # Newcombe hybrid-score difference from independent Wilson intervals.
        # Method reference: statsmodels.stats.proportion.confint_proportions_2indep,
        # method='newcomb', compare='diff', alpha=0.05 (no continuity correction).
        low = float(difference) - math.hypot(float(p1) - low1, high2 - float(p2))
        high = float(difference) + math.hypot(high1 - float(p1), float(p2) - low2)
        standard_error = math.sqrt(float(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2))
        return {**common, "outcome": "Unknown",
                "scope": "Descriptive two-sample proportions and a nominal 95% Newcombe/Wilson interval under independent-binomial assumptions only.",
                "statistical_result": {"groups": [{"successes": s, "total": n, "proportion_exact": str(Fraction(s, n))}
                                                   for s, n in counts],
                                       "risk_difference_exact": str(difference),
                                       "risk_difference": float(difference),
                                       "standard_error": standard_error,
                                       "confidence_interval_95": [low, high],
                                       "method": "newcombe_hybrid_wilson_no_continuity_correction",
                                       "registered_constants": {"alpha": 0.05, "normal_975": NORMAL_975},
                                       "constants_basis": "Declared statistical method; not empirical observations.",
                                       "interval_excludes_zero": low > 0 or high < 0},
                "uncertainty": ["Independent binomial sampling, measurement comparability and absence of selection bias are not established by count quotations.",
                                "A confidence interval does not establish causality, equivalence, population generality or investigation closure."],
                "next_evidence": ["Validate group assignment, independence, denominators, outcome coding, missingness and target population.",
                                  "For causal conclusions, establish identification from the study design and test rival explanations."]}
    if kind == "truth_table":
        premises, conclusion, variables = _truth_table(plan, question)
        counterexample, models, checked = None, 0, 0
        for bits in itertools.product((False, True), repeat=len(variables)):
            valuation = dict(zip(variables, bits))
            checked += 1
            if all(_truth_value(premise, valuation) for premise in premises):
                models += 1
                if not _truth_value(conclusion, valuation) and counterexample is None:
                    counterexample = valuation
        return {**common, "outcome": "PROVED" if counterexample is None else "REFUTED",
                "scope": "Classical propositional entailment of the exact quoted premise formulas and conclusion formula only.",
                "counterexample": counterexample,
                "truth_table": {"variables": variables, "valuations_checked": checked,
                                "premise_models": models, "vacuous_entailment": models == 0,
                                "premises": plan["premises"], "conclusion": plan["conclusion"]},
                "uncertainty": ["Natural-language translation, premise truth and applicability of classical propositional semantics remain unverified.",
                                "Inconsistent premises entail every conclusion in this declared logic; this is reported as vacuous entailment."],
                "next_evidence": ["Independently validate the quoted formalization and factual or normative premises."]}
    rows = [(ident, _evidence(ident, sources, evidence)) for ident in plan["evidence_ids"]]
    support = [ident for ident, row in rows if row.get("relation") == "SUPPORT"]
    opposition = [ident for ident, row in rows if row.get("relation") == "CONTRADICT"]
    return {**common, "outcome": "Unknown",
            "scope": "Anchored evidence inventory; semantic relation labels are investigator hypotheses, not verified entailments.",
            "support": support, "counterevidence": opposition,
            "declared_conflict": bool(support and opposition),
            "uncertainty": ["Quotation fidelity does not establish truth, relevance, entailment or causal identification.",
                            "No native proof rule establishes this " + plan["claim_type"] + " proposition."],
            "next_evidence": ["Independently adjudicate source meaning, dependence, applicability and competing interpretations.",
                              "For causal claims, supply an identified estimand and evidence distinguishing rival explanations.",
                              "For normative claims, state the evaluative premises and justify their applicability."]}
