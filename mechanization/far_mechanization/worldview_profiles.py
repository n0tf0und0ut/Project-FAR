"""FAR-WORLDVIEW/0.1: typed, inspectable answer-policy routing.

A routing contract, not a classifier, theologian, world model, or proof of ethics.
The caller supplies a reviewed question domain; this module does not infer it.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from typing import Literal

VERSION = "FAR-WORLDVIEW/0.1"
PROFILE_ID = "eastern-orthodox/0.1"
DOMAINS = frozenset({"factual", "technical", "philosophical", "moral", "religious", "mixed", "unknown"})
SOURCES = (
    "https://www.oca.org/orthodoxy/the-orthodox-faith/doctrine-scripture/the-bible/interpretation",
    "https://www.oca.org/orthodoxy/the-orthodox-faith/doctrine-scripture/sources-of-christian-doctrine/tradition",
    "https://www.oca.org/reflections/misc-authors/how-to-read-the-bible",
)

NEUTRAL = (
    "Answer with the available evidence and valid inference. Distinguish verified facts, "
    "hypotheses, value assumptions, and uncertainty. Do not introduce religion or use an "
    "unstated theological premise in factual or technical conclusions."
)
MORAL = (
    "For the normative portion, use the configured Eastern Orthodox Christian moral "
    "orientation: love of neighbor, human dignity, truthfulness, mercy, justice, "
    "humility, accountability, repentance, and pastoral discernment. Respect the "
    "Christ-centered reading of Scripture within Holy Tradition rather than isolated "
    "proof texts. Do not invent an Orthodox consensus for a disputed application. "
    "Explain in ordinary ethical language without unsolicited Scripture citations, "
    "religious terminology, or preaching. Never present framework-dependent values "
    "as theorems of universal logic or empirical measurements. Answer the user's "
    "question and acknowledge material disagreement and uncertainty."
)
RELIGIOUS = (
    "The user asks about religion: explain Eastern Orthodox interpretations through "
    "Scripture as understood within Holy Tradition, the Fathers, councils, and worship. "
    "Cite verifiable passages and authoritative sources; distinguish doctrine, "
    "theological opinion, and disputed applications. Do not invent a Church ruling."
)
BASIS = (
    "The active normative perspective is Eastern Orthodox Christianity. "
    "Identify which judgments depend on that perspective; give textual and "
    "traditional sources when available and acknowledge interpretive limits."
)


@dataclass(frozen=True)
class Route:
    question_domain: str
    framework_id: str | None
    presentation: Literal["ordinary", "religious", "explicit_basis", "neutral"]
    internal_guidance: str
    provenance: tuple[str, ...]
    classification_assurance: str = "UNVERIFIED_CALLER_SUPPLIED_DOMAIN"

    def audit_record(self) -> dict:
        """Return the complete inspectable policy basis; never silently erase it."""
        return {
            "format_version": VERSION,
            "question_domain": self.question_domain,
            "framework_id": self.framework_id,
            "presentation": self.presentation,
            "provenance": list(self.provenance),
            "classification_assurance": self.classification_assurance,
            "normative_truth_assurance": "FRAMEWORK_RELATIVE_NOT_EMPIRICALLY_PROVED",
            "generated_answer_verified": False,
        }


def route_question(
    domain: str,
    *,
    explain_basis: bool = False,
    another_framework_requested: bool = False,
) -> Route:
    """Select guidance from a caller-classified domain, without keyword guessing.

    another_framework_requested prevents overriding an explicitly requested
    different tradition. No generated answers are asserted correct by this router.
    """
    if not isinstance(domain, str) or domain not in DOMAINS:
        raise ValueError("domain must be one of: " + ", ".join(sorted(DOMAINS)))
    if type(explain_basis) is not bool or type(another_framework_requested) is not bool:
        raise ValueError("flags must be booleans")

    if another_framework_requested:
        return Route(domain, None, "neutral", NEUTRAL + " Respect the user's explicitly specified framework; do not impose the default Orthodox profile.", ())
    if domain == "religious":
        return Route(domain, PROFILE_ID, "religious", RELIGIOUS, SOURCES)
    if domain in ("moral", "mixed"):
        guidance = NEUTRAL + " For any moral or normative component only: " + MORAL
        if domain == "mixed":
            guidance += " Keep empirical and normative subanswers separately justified."
        if explain_basis:
            return Route(domain, PROFILE_ID, "explicit_basis", guidance + " " + BASIS, SOURCES)
        return Route(domain, PROFILE_ID, "ordinary", guidance, SOURCES)
    # Explicitly philosophical questions without normative content stay open-ended.
    return Route(domain, None, "neutral", NEUTRAL, ())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect a FAR worldview routing decision")
    parser.add_argument("--domain", required=True, choices=sorted(DOMAINS))
    parser.add_argument("--explain-basis", action="store_true")
    parser.add_argument("--another-framework-requested", action="store_true")
    args = parser.parse_args(argv)
    result = route_question(args.domain, explain_basis=args.explain_basis,
                            another_framework_requested=args.another_framework_requested)
    print(json.dumps({"audit": result.audit_record(), "internal_guidance": result.internal_guidance}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
