"""Source-bound, limited correspondence for a real FAR adjudication status resolver.

The verifier binds an actual committed Python source artifact, checks the
semantic form of its status branch, then builds an eight-state Moore envelope
for the *post-finding accumulation* observation. It is not a proof of the
whole adjudication runtime, its environment, or any external I3 replication.
"""
from __future__ import annotations

import ast
import hashlib
from itertools import product
from pathlib import Path
from typing import Iterable

# This is a real, already existing Project FAR application implementation,
# not the model/evidence_gate.py fixture or a newly authored model program.
SOURCE_REL = Path("commercial/far-decision-integrity/src/far_decision_integrity/adjudicate.py")
# Fetched from protected main aa5cb8faf36b5e033bb96bf6e9f7f3f351387913.
SOURCE_GIT_BLOB = "d6167a41ddff47675db004da2f1bfe409acd7251"

UNSUPPORTED = frozenset({
    "authorization-dependency-missing", "required-node-invalid", "evidence-contradicted",
    "semantic-material-loss", "semantic-outside-tolerance",
})
UNVERIFIABLE = frozenset({
    "declared-unknowns", "trace-incomplete", "semantic-contract-required",
    "semantic-contract-unknown", "semantic-contract-invalid", "semantic-verifier-unavailable",
})
ALTERNATIVE = "material-alternatives-remain"
ACTION_RULES = (
    "authorization-dependency-missing", ALTERNATIVE, "declared-unknowns", "unrelated-rule",
)
STATUS_NAMES = ("JUSTIFIED", "UNSUPPORTED", "UNDERDETERMINED", "UNVERIFIABLE")


class SourceCorrespondenceError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def require(condition: bool, code: str) -> None:
    if not condition:
        raise SourceCorrespondenceError(code)


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\x00" + raw).hexdigest()


def _same(actual: ast.AST, expected: ast.AST) -> bool:
    return ast.dump(actual, include_attributes=False) == ast.dump(expected, include_attributes=False)


def _expected_resolver() -> list[ast.stmt]:
    return ast.parse('''
rule_ids = {finding.rule_id for finding in findings}
unsupported = {
    "authorization-dependency-missing", "required-node-invalid", "evidence-contradicted",
    "semantic-material-loss", "semantic-outside-tolerance",
}
unverifiable = {
    "declared-unknowns", "trace-incomplete", "semantic-contract-required",
    "semantic-contract-unknown", "semantic-contract-invalid", "semantic-verifier-unavailable",
}
if rule_ids & unsupported:
    status = IntegrityStatus.UNSUPPORTED
elif "material-alternatives-remain" in rule_ids:
    status = IntegrityStatus.UNDERDETERMINED
elif rule_ids & unverifiable:
    status = IntegrityStatus.UNVERIFIABLE
else:
    status = IntegrityStatus.JUSTIFIED
return Adjudication(package.decision_id, status, tuple(findings), semantic_audits)
''').body


def inspect_source(raw: bytes) -> dict:
    """Fail closed on source drift and semantic drift from reviewed real source.

    Every check concerns the production terminal status block;
    earlier findings generation and imported code are out of scope.
    """
    require(git_blob_sha(raw) == SOURCE_GIT_BLOB, "SOURCE_BLOB_MISMATCH")
    return _check_fragment(raw)


def _check_fragment(raw: bytes) -> dict:
    """Test-only shape analyzer; without source identity this is not a certificate."""
    try:
        parsed = ast.parse(raw.decode("utf-8", errors="strict"))
    except (UnicodeError, SyntaxError) as exc:
        raise SourceCorrespondenceError("SOURCE_PARSE_ERROR") from exc
    functions = [x for x in parsed.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and x.name == "adjudicate"]
    require(len(functions) == 1 and isinstance(functions[0], ast.FunctionDef), "SUBJECT_FUNCTION")
    fn = functions[0]
    require(not fn.decorator_list, "SUBJECT_DECORATOR")
    expected = _expected_resolver()
    require(len(fn.body) >= len(expected), "SOURCE_FRAGMENT_MISSING")
    actual = fn.body[-len(expected):]
    require(all(_same(a, b) for a, b in zip(actual, expected)), "SOURCE_SEMANTICS_DRIFT")
    require(len(set(ACTION_RULES)) == len(ACTION_RULES)
            and not (UNSUPPORTED & UNVERIFIABLE)
            and ALTERNATIVE not in UNSUPPORTED | UNVERIFIABLE, "CATEGORY_CONTRACT")
    return {"source_git_blob": git_blob_sha(raw),
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "executable_source_path": SOURCE_REL.as_posix(),
            "bound_fragment": "adjudicate/post-findings-status-resolution",
            "matched_ast_statements": len(expected),
            "verified_status_priority": list(STATUS_NAMES),
            "source_semantics": "STRICT_AST_FRAGMENT_MATCH_WITH_IMMUTABLE_GIT_BLOB"}


def alpha(rule_ids: Iterable[str]) -> tuple[bool, bool, bool]:
    values = set(rule_ids)
    return bool(values & UNSUPPORTED), ALTERNATIVE in values, bool(values & UNVERIFIABLE)


def status_of_flags(flags: tuple[bool, bool, bool]) -> str:
    # Exactly the priority in the structurally checked production source.
    u, a, v = flags
    if u:
        return "UNSUPPORTED"
    if a:
        return "UNDERDETERMINED"
    if v:
        return "UNVERIFIABLE"
    return "JUSTIFIED"


def add_rule(rule_ids: frozenset[str], rule_id: str) -> frozenset[str]:
    """Analysis wrapper event; not an API or transition in production adjudicate."""
    return rule_ids | frozenset((rule_id,))


def abstract_add(flags: tuple[bool, bool, bool], rule_id: str) -> tuple[bool, bool, bool]:
    a = alpha((rule_id,))
    return tuple(x or y for x, y in zip(flags, a))


def certify_source(root: Path) -> dict:
    root = root.resolve()
    source = (root / SOURCE_REL).resolve()
    require(source.is_relative_to(root) and source.is_file(), "SOURCE_UNAVAILABLE")
    report = inspect_source(source.read_bytes())
    flags = tuple(product((False, True), repeat=3))
    outcomes = []
    transitions = []
    # Independent finite truth-table check for the 8-state analysis wrapper.
    for current in flags:
        outcomes.append(status_of_flags(current))
        transitions.append([flags.index(abstract_add(current, rule)) for rule in ACTION_RULES])
        for action in ACTION_RULES:
            representative = frozenset(rule for bit, rule in
                                       zip(current, ACTION_RULES[:3]) if bit)
            concrete_next = add_rule(representative, action)
            require(alpha(concrete_next) == abstract_add(current, action), "TRANSITION_MISMATCH")
            require(status_of_flags(alpha(representative)) == status_of_flags(current),
                    "OUTPUT_MISMATCH")
    from research.uq_t33_effective_quotients.finite_state import quotient
    classes, _ = quotient(tuple(outcomes), tuple(tuple(row) for row in transitions))
    report.update({
        "result": "SOURCE_BOUND_STATUS_FRAGMENT_VERIFIED",
        "subject": "EXISTING_FAR_DECISION_INTEGRITY_ADJUDICATOR",
        "abstraction_states": len(flags),
        "action_categories": list(ACTION_RULES),
        "finite_wrapper_transition_obligations": len(flags) * len(ACTION_RULES),
        "observable_classes": len(set(classes)),
        "word_length_horizon": max(len(flags) - 2, 0),
        "actual_program_scope": "TERMINAL_STATUS_RESOLUTION_ONLY",
        "whole_program_correspondence": "NOT_VERIFIED",
        "deployed_environment_correspondence": "NOT_VERIFIED",
        "independent_external_replication": "NOT_OBTAINED",
        "method": "PINNED_SOURCE_AST_PLUS_FINITE_WRAPPER_INDUCTION",
    })
    return report
