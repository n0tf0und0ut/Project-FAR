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
NEGATION = re.compile(
    r"\b(not|no|neither|nor|without|never|cannot|unresolved|remains? open|refuted|impossible|nonclaims?"
    r"|excluded|prohibit\w*|unless|whether|if)\b|n't",
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
LABEL_STATEMENT = re.compile(r"[;.]")
# Only an explicit condition column qualifies the preceding status. A
# neighboring non-condition cell must never hide an unsupported promotion.
CONDITION_CELL = re.compile(r"^(?:only\\s+if|if|unless)\\b", re.I)
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


def promotion_clauses(text: str) -> list[str]:
    found = []
    for line in text.splitlines():
        for clause in CLAUSE.split(line):
            if TOPIC.search(clause) and PROMOTION.search(clause) and not NEGATION.search(clause):
                found.append(clause.strip())
        for statement in LABEL_STATEMENT.split(line):
            for match in LABEL_PROMOTION.finditer(statement):
                # A Markdown row can contain several label/value pairs.
                # Bound context to the nearest cell edges: a different pair's
                # "not established" must not suppress this pair's promotion.
                # Retain any leading prohibition and trailing condition.
                before = statement[:match.start()].rsplit("|", 1)[-1]
                # If another status label precedes this one, its conditions
                # and negations are independent. Bound preceding context to
                # the last comma after that preceding label (or to empty
                # context for adjacent labels without a comma).
                earlier = list(LABEL_MARKER.finditer(statement[:match.start()]))
                if earlier:
                    separator = statement.rfind(",", earlier[-1].end(), match.start())
                    before = (
                        statement[separator + 1:match.start()].rsplit("|", 1)[-1]
                        if separator >= 0 else ""
                    )
                after = statement[match.end():]
                later = LABEL_MARKER.search(after)
                if later:
                    after = after[:later.start()]
                # The next Markdown table cell may expressly state a
                # condition: "| Novelty | established | only if ... |".
                # Keep only that one condition cell, never an arbitrary
                # adjacent cell or the next independently labeled status.
                if "|" in after:
                    first, next_cell, *_ = (after.split("|") + [""])[:3]
                    after = first + (
                        " " + next_cell
                        if CONDITION_CELL.match(next_cell.strip()) else ""
                    )
                if NEGATION.search(before + match.group(0) + after):
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
