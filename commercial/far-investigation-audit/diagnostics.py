"""Scheme-specific objections: question generators, NEVER logical/factual verdicts.

Inspired by argumentation schemes and critical-question methodologies. The
rules flag verification obligations but cannot establish that they are unmet.
"""
from __future__ import annotations
import re

CRITICAL = (
    ("CAUSAL_IDENTIFICATION", re.compile(r"\b(caus(?:e|es|ed|ing)|results? in|leads? to|effect of|responsible for)\b",re.I),
     "Does independent causal-identification evidence address confounding, directionality and alternatives? Temporal sequence/correlation alone is insufficient."),
    ("UNIVERSAL_GENERALIZATION", re.compile(r"\b(all|every|always|never|no one|nobody|everyone)\b",re.I),
     "Does the sampled population and operational measure cover the full quantified population and exceptions?"),
    ("NUMERICAL_DENOMINATOR", re.compile(r"(?:\b\d+(?:\.\d+)?\s*%|\bpercent(?:age)?\b|\brate\b)",re.I),
     "Are denominator, reference period, sampling frame and measurement definition specified and source-backed?"),
    ("ABSENCE_OF_EVIDENCE", re.compile(r"\b(no evidence|never happened|did not happen|not found|no record)\b",re.I),
     "Is a search-coverage contract sufficient to distinguish no evidence found from evidence of absence?"),
    ("NORMATIVE_TRANSITION", re.compile(r"\b(should|ought|must be allowed|must be banned|morally)\b",re.I),
     "Which normative premise or decision rule bridges empirical observations to the stated obligation?"),
)


def critical_questions(claims: list[dict]) -> list[dict]:
    out=[]
    for c in claims:
        q=c["text"]
        for kind,pattern,question in CRITICAL:
            if pattern.search(q):
                out.append({"claim_id":c["id"],"scheme":kind,
                            "critical_question":question,"status":"QUESTION_NOT_ADJUDICATED",
                            "evidence_of_violation":False})
    return out
