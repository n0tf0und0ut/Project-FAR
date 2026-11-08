from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .strict_json import loads_strict


class RegressionDecision(str, Enum):
    PASS = "pass"
    REVIEW = "review"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class RunResult:
    case_id: str
    integrity_status: str
    disposition: str
    finding_ids: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunResult":
        if not isinstance(data, dict):
            raise ValueError("run result must be an object")
        try:
            case_id = data["case_id"]
            status = data["integrity_status"]
            disposition = data["disposition"]
            findings = data.get("finding_ids", [])
        except KeyError as exc:
            raise ValueError(f"missing required field {exc.args[0]!r}") from exc
        if not all(isinstance(value, str) and value for value in (case_id, status, disposition)):
            raise ValueError("case_id, integrity_status, and disposition must be non-empty strings")
        if not isinstance(findings, list) or any(not isinstance(item, str) or not item for item in findings):
            raise ValueError("finding_ids must be an array of non-empty strings")
        return cls(case_id, status, disposition, tuple(sorted(set(findings))))


@dataclass(frozen=True, slots=True)
class CaseRegression:
    case_id: str
    baseline: RunResult
    candidate: RunResult
    classification: str
    changed_findings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RegressionReport:
    suite_id: str
    decision: RegressionDecision
    cases: tuple[CaseRegression, ...]


def compare_corpus(suite_id: str, baseline: list[RunResult], candidate: list[RunResult]) -> RegressionReport:
    if not suite_id:
        raise ValueError("suite_id must be non-empty")
    base = _index(baseline, "baseline")
    cand = _index(candidate, "candidate")
    if set(base) != set(cand):
        missing = sorted(set(base) - set(cand))
        added = sorted(set(cand) - set(base))
        raise ValueError(f"corpus case mismatch: missing={missing}, added={added}")

    cases: list[CaseRegression] = []
    decision = RegressionDecision.PASS
    for case_id in sorted(base):
        before, after = base[case_id], cand[case_id]
        classification = _classify(before, after)
        changed = tuple(sorted(set(before.finding_ids) ^ set(after.finding_ids)))
        cases.append(CaseRegression(case_id, before, after, classification, changed))
        if classification in {"authorization-expanded", "integrity-degraded"}:
            decision = RegressionDecision.BLOCKED
        elif classification != "preserved" and decision is RegressionDecision.PASS:
            decision = RegressionDecision.REVIEW
    return RegressionReport(suite_id, decision, tuple(cases))


def load_suite(path: str | Path) -> tuple[str, list[RunResult], list[RunResult]]:
    try:
        payload = loads_strict(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"unable to load regression suite: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("regression suite must be an object")
    suite_id = payload.get("suite_id")
    if not isinstance(suite_id, str) or not suite_id:
        raise ValueError("suite_id must be a non-empty string")
    baseline = payload.get("baseline")
    candidate = payload.get("candidate")
    if not isinstance(baseline, list) or not isinstance(candidate, list):
        raise ValueError("baseline and candidate must be arrays")
    return suite_id, [RunResult.from_dict(item) for item in baseline], [RunResult.from_dict(item) for item in candidate]


def report_payload(report: RegressionReport) -> dict[str, Any]:
    return {
        "schema_version": "far-reasoning-regression/0.1",
        "suite_id": report.suite_id,
        "decision": report.decision.value,
        "summary": {
            "total": len(report.cases),
            "changed": sum(case.classification != "preserved" for case in report.cases),
        },
        "cases": [
            {
                "case_id": case.case_id,
                "classification": case.classification,
                "baseline": {
                    "integrity_status": case.baseline.integrity_status,
                    "disposition": case.baseline.disposition,
                },
                "candidate": {
                    "integrity_status": case.candidate.integrity_status,
                    "disposition": case.candidate.disposition,
                },
                "changed_findings": list(case.changed_findings),
            }
            for case in report.cases
        ],
    }


def _index(results: list[RunResult], label: str) -> dict[str, RunResult]:
    indexed: dict[str, RunResult] = {}
    for result in results:
        if result.case_id in indexed:
            raise ValueError(f"duplicate {label} case_id {result.case_id!r}")
        indexed[result.case_id] = result
    return indexed


def _classify(before: RunResult, after: RunResult) -> str:
    if before == after:
        return "preserved"
    disposition_rank = {"block": 0, "escalate": 1, "allow": 2}
    status_rank = {"unsupported": 0, "unverifiable": 1, "underdetermined": 1, "justified": 2}
    if disposition_rank.get(after.disposition, -1) > disposition_rank.get(before.disposition, -1):
        return "authorization-expanded"
    if status_rank.get(after.integrity_status, -1) < status_rank.get(before.integrity_status, -1):
        return "integrity-degraded"
    if after.disposition != before.disposition:
        return "authorization-restricted"
    if after.integrity_status != before.integrity_status:
        return "integrity-changed"
    return "reasoning-changed"
