#!/usr/bin/env python3
"""Semantic guards for limitations, open problems, and claim-boundary language.

Whole-file hash pins on these living documents detect any edit, so a routine re-pin also
hides a buried promotion. These rules instead check meaning:

* registers only grow: no limitation or open-problem ID may disappear (closing a problem
  moves its row to the closure section; it never deletes it);
* every register row keeps a non-empty status/completion cell;
* canonical status surfaces may not assert that I2/I3 isolation, external validation or
  replication, novelty, priority, universality, necessity, minimality, or uniqueness is
  established unless the same clause negates or conditions it;
* the canonical status surface keeps a negated statement for each assurance boundary.

The promotion rule is a bounded clause-level heuristic; it is a complement to,
not a replacement for semantic review.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIMITATIONS = "docs/governance/limitations-register.md"
OPEN_PROBLEMS = "docs/governance/open-problems-register.md"
STATUS = "docs/project-status.md"
SURFACES = ("README.md", STATUS, "docs/CANONICAL_MAP.md", "docs/governance/claim-status-matrix.md")

# IDs present on main when this checker was introduced; registers may add IDs, never drop them.
LIMITATION_FLOOR = frozenset(f"LIM-{i:03d}" for i in range(1, 47))
OPEN_PROBLEM_FLOOR = frozenset(f"OP-{i:02d}" for i in range(1, 30))

ROW = re.compile(r"^\|\s*((?:LIM|OP)-\d+)\b[^|]*\|(.*)\|\s*$")
TOPIC = re.compile(
    r"\b(I2|I3|external (?:independent )?(?:validation|replication)|independent replication|novelty|priority"
    r"|universal(?:ity)?|primitive necessity|necessity|minimality|uniqueness)\b",
    re.I,
)
PROMOTION = re.compile(r"\b(established|proved|proven|demonstrated|confirmed|validated)\b", re.I)
# These scalar status atoms are also negation vocabulary. Keep their complete
# spans shared with STATUS_VALUE so a recognized negative status cannot erase
# the surrounding pair's conditional/prohibition scope. Qualifier introducers
# such as if/unless/whether remain separate from scalar status values.
NEGATIVE_STATUS = r"(?:unresolved|remains? open|refuted|impossible|nonclaims?|excluded|prohibit\w*)"
NEGATION = re.compile(
    rf"\b(not|no|neither|nor|without|never|cannot|{NEGATIVE_STATUS}|unless|whether|if)\b|n't",
    re.I,
)
CLAUSE = re.compile(r"[,;.:|()]|\s(?:and|but|while|whereas)\s|\s[—–-]\s")
# Structured status entries are still claims. The sentence-level CLAUSE splitter
# deliberately separates colons and table cells, so inspect label/value pairs
# independently instead of silently accepting "Novelty: established".
LABEL_PROMOTION = re.compile(
    rf"{TOPIC.pattern}(?:\*\*|\*)?\s*(?::|\||[—–-])\s*(?:\*\*|\*)?\s*{PROMOTION.pattern}(?:\*\*|\*)?",
    re.I,
)
# Commas can introduce a condition *belonging to the status claim*:
# "If replicated, novelty: established" and "Novelty: established, only if".
# Do not split there. Separate semicolons/sentences and explicit conjunctions,
# then scope each label to its own adjacent status statement below.
LABEL_STATEMENT = re.compile(r";|\.(?!\d)")
# Only an explicit condition column qualifies the preceding status. A
# neighboring non-condition cell must never hide an unsupported promotion.
CONDITION_PREFIX = r"(?:only\s+if|if|unless)"
CONDITION_CELL = re.compile(rf"^{CONDITION_PREFIX}\b", re.I)
# A leading condition may expressly govern a coordinated pair of statuses.
# Comma-separated independent assertions and separate table cells remain local.
# The finite conditional grammar permits an explicit consequent introducer.
SHARED_CONDITION = re.compile(rf"^\s*(?:[-+*]\s+)?{CONDITION_PREFIX}\b[^|]+,\s*(?:(?:only\s+)?then\b\s*)?(?:both\b\s*)?$", re.I)
CLAIM_COORDINATOR = re.compile(r"\b(?:and|but|while|whereas)\b\s*", re.I)
FORWARD_PROHIBITION = re.compile(
    r"(?:do\s+not\s+(?:assert|claim)|never\s+(?:assert|claim)"
    r"|no\s+basis\s+to\s+(?:assert|claim)|without\s+(?:asserting|claiming))",
    re.I,
)
COORDINATION = re.compile(r"\s+and\s+", re.I)
BOTH_PREFIX = re.compile(r"\bboth\s*$", re.I)
# Status values are consumed separately from pair-level qualifiers. A local
# "not established" in one member must never qualify the other member.
# This finite prefix grammar shares NEGATION's cannot/n't semantics; arbitrary
# adverbs and general English verb phrases are outside this scalar grammar.
NEGATIVE_STATUS_PREFIX = r"(?:(?:not|never)\s+(?:yet\s+)?|cannot\s+be\s+|(?:isn't|aren't|wasn't|weren't)\s+)"
STATUS_VALUE = re.compile(
    rf"\s*(?:{NEGATIVE_STATUS_PREFIX})?(?:{PROMOTION.pattern}|{NEGATIVE_STATUS}|unknown|open)\b",
    re.I,
)
INLINE_FORMATTING = re.compile(r"(\*\*|__|\*|_|`)(.+?)\1")
LABEL_MARKER = re.compile(
    rf"{TOPIC.pattern}(?:\*\*|\*)?\s*(?::|\||[—–-])",
    re.I,
)
REQUIRED_NEGATED_BOUNDARIES = ("I2", "I3", "novelty", "priority")


def register_rows(text: str) -> list[tuple[str, list[str]]]:
    rows = []
    for line in text.splitlines():
        match = ROW.match(line)
        if match:
            rows.append((match.group(1), [cell.strip() for cell in match.group(2).split("|")]))
    return rows


def following_claim_qualifier(context: str) -> tuple[int, str] | None:
    """Find a following claim's own qualifier after an independent join.

    Use the existing qualifier vocabulary for both conditions and prohibitions;
    "but if C, Y" and "but do not assert Y" have the same ownership boundary.
    "|" always ends this context, so another table cell cannot supply it.
    """
    boundaries = list(CLAIM_COORDINATOR.finditer(context))
    if boundaries:
        # Explicit comma-separated coordinators can introduce the next
        # status's own compound condition. Select its FIRST independent
        # boundary, not an internal repeated "and if": "but if C, and if D,
        # Y" governs Y as a unit. A "but only if C" segment instead
        # qualifies the preceding status; a later ", and if D, Y" begins
        # the next claim. These rules require punctuation and do not infer
        # arbitrary natural-language scope across cells or sentences.
        for candidate in re.finditer(
                rf",\s*(but|and|while|whereas)\s+({CONDITION_PREFIX})\b", context, re.I):
            if (candidate.group(1).lower() == "but"
                    and candidate.group(2).lower().startswith("only")):
                continue
            qualifier = context[candidate.end(1):].strip()
            if SHARED_CONDITION.fullmatch(qualifier):
                return candidate.start(1), qualifier
        last = boundaries[-1]
        last_tail = context[last.end():].strip()
        chain_start = len(boundaries) - 1
        # "both" introduces the following status group, not another part of
        # the forward-prohibition phrase. Classify the chain without that
        # introducer, while retaining the original context for group scoping.
        chain_tail = BOTH_PREFIX.sub("", last_tail).strip(" ,")
        if FORWARD_PROHIBITION.fullmatch(chain_tail):
            while chain_start > 0:
                preceding = context[boundaries[chain_start - 1].end():boundaries[chain_start].start()]
                if not FORWARD_PROHIBITION.fullmatch(preceding.strip(" ,")):
                    break
                chain_start -= 1
        # Coordinated forward prohibitions are one prefix unit; their internal
        # conjunction cannot leave half the prohibition with the prior claim.
        if chain_start < len(boundaries) - 1:
            boundaries = [boundaries[chain_start]]
        # A final join immediately before a label, or before its own local
        # qualifier, begins that independent claim. Earlier trailing conditions
        # stay with the previous label. Do not split conjunctions inside a
        # comma-terminated leading condition ("if C and D, Y").
        elif (
            not last_tail
            or re.search(r",\s*$", context[:last.start()])
            or ("," not in last_tail and NEGATION.search(last_tail))
        ):
            boundaries = [last]
    for boundary in boundaries:
        qualifier = context[boundary.end():].strip(" ,")
        if "|" not in qualifier and NEGATION.search(qualifier):
            # Keep a comma-terminated leading condition intact. Stripping its
            # final comma erases the shared-pair delimiter after a prior claim.
            scoped = context[boundary.end():].strip()
            return boundary.start(), scoped if SHARED_CONDITION.fullmatch(scoped) else qualifier
    return None


def label_prefix(statement: str, start: int) -> str:
    """Return only the local pre-label context, retaining its own condition."""
    earlier = list(LABEL_MARKER.finditer(statement[:start]))
    if not earlier:
        return statement[:start].rsplit("|", 1)[-1]
    previous = earlier[-1]
    if leading := following_claim_qualifier(statement[previous.end():start]):
        return leading[1]
    separator = statement.rfind(",", previous.end(), start)
    if separator >= 0:
        tail = statement[separator + 1:start].rsplit("|", 1)[-1]
    else:
        # An independent join can introduce the following "both" group even
        # without a comma. Keep only its own tail, never the previous status.
        context = statement[previous.end():start]
        joins = list(CLAIM_COORDINATOR.finditer(context))
        tail = context[joins[-1].end():].rsplit("|", 1)[-1] if joins else ""
    # A prior label's trailing qualifier cannot cross an independent
    # conjunction into this label. Leading conditions were retained above.
    return CLAUSE.split(tail)[-1]


def label_suffix(statement: str, end: int) -> str:
    """Return only this label's post-value context and explicit condition cell."""
    after = statement[end:]
    if later := LABEL_MARKER.search(after):
        after = after[:later.start()]
        if following := following_claim_qualifier(after):
            after = after[:following[0]]
    if "|" in after:
        first, next_cell, *_ = (after.split("|") + [""])[:3]
        next_cell = next_cell.strip()
        after = first + (" " + next_cell if CONDITION_CELL.match(next_cell) else "")
    return after


def shared_pair_contexts(statement: str) -> dict[int, str]:
    """Bind qualifiers to bounded two-status units before local label scans.

    Explicit "both" binds leading prohibitions and trailing qualification to
    the pair. An explicit leading condition also binds an adjacent X-and-Y
    pair. Status values, independent labels, table cells and clauses remain
    outside shared context; this is not a general natural-language parser.
    """
    shared = {}
    markers = list(LABEL_MARKER.finditer(statement))
    for left, right in zip(markers, markers[1:]):
        left_value = STATUS_VALUE.match(statement, left.end())
        right_value = STATUS_VALUE.match(statement, right.end())
        if not left_value or not right_value:
            continue
        if not COORDINATION.fullmatch(statement[left_value.end():right.start()]):
            continue
        prefix = label_prefix(statement, left.start())
        explicit_pair = BOTH_PREFIX.search(prefix)
        context = ""
        if explicit_pair or SHARED_CONDITION.fullmatch(prefix):
            context = prefix
        if explicit_pair:
            context += " " + label_suffix(statement, right_value.end())
        if NEGATION.search(context):
            shared[left.start()] = context
            shared[right.start()] = context
    return shared


def promotion_clauses(text: str) -> list[str]:
    found = []
    for line in text.splitlines():
        for clause in CLAUSE.split(line):
            if TOPIC.search(clause) and PROMOTION.search(clause) and not NEGATION.search(clause):
                found.append(clause.strip())
        for statement in LABEL_STATEMENT.split(line):
            # Normalize paired inline delimiters before interpreting labels or
            # their conditions. Formatting only part of a qualifier ("**only**
            # if") must have the same scope as formatting the whole qualifier.
            while (normalized := INLINE_FORMATTING.sub(r"\2", statement)) != statement:
                statement = normalized
            shared = shared_pair_contexts(statement)
            for match in LABEL_PROMOTION.finditer(statement):
                # A Markdown row can contain several label/value pairs.
                # Bound context to the nearest cell edges: a different pair's
                # "not established" must not suppress this pair's promotion.
                # Retain any leading prohibition and trailing condition.
                before = label_prefix(statement, match.start())
                after = label_suffix(statement, match.end())
                if NEGATION.search(" ".join((before, match.group(0), after, shared.get(match.start(), "")))):
                    continue
                label = match.group(0).strip()
                if label not in found:
                    found.append(label)
    return found


def negated_mentions(text: str, term: str) -> bool:
    pattern = re.compile(rf"\b{re.escape(term)}\b", re.I)
    for line in text.splitlines():
        if pattern.search(line) and NEGATION.search(line):
            return True
    return False


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    texts: dict[str, str] = {}
    for relative in (LIMITATIONS, OPEN_PROBLEMS, *SURFACES):
        path = root / relative
        if not path.is_file():
            errors.append(f"missing governance surface: {relative}")
        else:
            texts[relative] = path.read_text(encoding="utf-8")
    if errors:
        return errors

    for relative, floor in ((LIMITATIONS, LIMITATION_FLOOR), (OPEN_PROBLEMS, OPEN_PROBLEM_FLOOR)):
        rows = register_rows(texts[relative])
        if missing := sorted(floor - {identifier for identifier, _ in rows}):
            errors.append(f"{relative}: register entries removed: {', '.join(missing)}")
        for identifier, cells in rows:
            if not cells or not cells[-1]:
                errors.append(f"{relative}: {identifier} has an empty status/completion cell")

    for relative in SURFACES:
        for clause in promotion_clauses(texts[relative]):
            errors.append(f"{relative}: unnegated assurance promotion: {clause!r}")

    for term in REQUIRED_NEGATED_BOUNDARIES:
        if not negated_mentions(texts[STATUS], term):
            errors.append(f"{STATUS}: no negated boundary statement for {term}")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("governance register integrity: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1
    print("governance register integrity: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
