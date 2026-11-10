"""Bounded, provider-neutral candidate search for FAR factory research.

This orchestrates callbacks; it neither generates code nor authenticates an oracle,
GitHub check, reviewer, or protected merge. All evidence is an operator-supplied
assertion until an independent observer verifies it. Research only.
"""
from __future__ import annotations

import re
from typing import Callable

SHA = re.compile(r"[0-9a-f]{40}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
IDENT = re.compile(r"[A-Za-z0-9._-]{1,128}\Z")
STATES = frozenset({"PASS", "FAIL", "UNKNOWN"})
CANDIDATE_KEYS = {"candidate_id", "base_sha", "source_sha", "artifact_sha256"}
RECEIPT_KEYS = {
    "candidate_id", "source_sha", "oracle_sha256", "test_status",
    "contract_status", "cost_micro_usd", "elapsed_ms", "evidence_sha256",
}


class SearchInputError(ValueError):
    """The caller or candidate supplied a malformed search declaration."""


def _sha(value: object, pattern: re.Pattern, label: str) -> str:
    if type(value) is not str or pattern.fullmatch(value) is None:
        raise SearchInputError(f"invalid {label}")
    return value


def _candidate(raw: object, base_sha: str) -> dict:
    if type(raw) is not dict or set(raw) != CANDIDATE_KEYS:
        raise SearchInputError("candidate shape mismatch")
    candidate_id = _sha(raw["candidate_id"], IDENT, "candidate_id")
    if _sha(raw["base_sha"], SHA, "base_sha") != base_sha:
        raise SearchInputError("candidate base mismatch")
    source_sha = _sha(raw["source_sha"], SHA, "source_sha")
    _sha(raw["artifact_sha256"], DIGEST, "artifact_sha256")
    return dict(raw)


def _receipt(raw: object, candidate: dict, oracle_sha256: str) -> dict:
    if type(raw) is not dict or set(raw) != RECEIPT_KEYS:
        raise SearchInputError("receipt shape mismatch")
    if raw["candidate_id"] != candidate["candidate_id"]:
        raise SearchInputError("receipt candidate mismatch")
    if raw["source_sha"] != candidate["source_sha"]:
        raise SearchInputError("receipt source mismatch")
    if _sha(raw["oracle_sha256"], DIGEST, "oracle_sha256") != oracle_sha256:
        raise SearchInputError("receipt oracle mismatch")
    _sha(raw["evidence_sha256"], DIGEST, "evidence_sha256")
    if raw["test_status"] not in STATES or raw["contract_status"] not in STATES:
        raise SearchInputError("invalid evaluation status")
    for field in ("cost_micro_usd", "elapsed_ms"):
        if type(raw[field]) is not int or raw[field] < 0:
            raise SearchInputError(f"invalid {field}")
    return dict(raw)


def run_search(
    propose: Callable[[int, tuple[dict, ...]], dict],
    evaluate: Callable[[dict], dict],
    *,
    base_sha: str,
    oracle_sha256: str,
    max_candidates: int = 3,
    max_cost_micro_usd: int = 0,
) -> dict:
    """Try bounded candidate proposals, record failures, choose an eligible candidate.

    Only status summaries of prior attempts reach propose; raw evaluation
    receipts and oracle material never do. Callbacks are trusted operator wiring,
    not isolated sandboxes. The chosen artifact is pending independent review.
    A cost budget constrains reported consumption and cannot preauthorize spend.
    """
    _sha(base_sha, SHA, "base_sha")
    _sha(oracle_sha256, DIGEST, "oracle_sha256")
    if not callable(propose) or not callable(evaluate):
        raise SearchInputError("callable proposer and evaluator required")
    if type(max_candidates) is not int or not 1 <= max_candidates <= 32:
        raise SearchInputError("max_candidates must be between 1 and 32")
    if type(max_cost_micro_usd) is not int or max_cost_micro_usd < 0:
        raise SearchInputError("max_cost_micro_usd must be nonnegative integer")

    attempts: list[dict] = []
    feedback: list[dict] = []
    seen_ids: set[str] = set()
    seen_sources: set[str] = set()
    eligible: list[tuple[int, int, int, str, dict]] = []
    total_cost = 0
    terminated = "ATTEMPTS_EXHAUSTED"

    for slot in range(max_candidates):
        try:
            candidate = _candidate(propose(slot, tuple(dict(x) for x in feedback)), base_sha)
            if candidate["candidate_id"] in seen_ids or candidate["source_sha"] in seen_sources:
                raise SearchInputError("duplicate candidate identity or source")
            seen_ids.add(candidate["candidate_id"])
            seen_sources.add(candidate["source_sha"])
        except Exception as exc:
            # Retain the failed slot, but never pretend an invalid candidate ran.
            attempts.append({"slot": slot, "status": "INVALID_PROPOSAL", "error_type": type(exc).__name__})
            feedback.append({"slot": slot, "status": "INVALID_PROPOSAL"})
            continue

        try:
            receipt = _receipt(evaluate(dict(candidate)), candidate, oracle_sha256)
        except Exception as exc:
            attempts.append({"slot": slot, "candidate": candidate, "status": "EVALUATION_ERROR", "error_type": type(exc).__name__})
            feedback.append({"slot": slot, "status": "EVALUATION_ERROR"})
            continue

        total_cost += receipt["cost_micro_usd"]
        if total_cost > max_cost_micro_usd:
            attempts.append({"slot": slot, "candidate": candidate, "receipt": receipt, "status": "BUDGET_EXCEEDED"})
            terminated = "BUDGET_EXCEEDED"
            break
        status = "ELIGIBLE" if receipt["test_status"] == "PASS" and receipt["contract_status"] == "PASS" else "INELIGIBLE"
        attempts.append({"slot": slot, "candidate": candidate, "receipt": receipt, "status": status})
        feedback.append({"slot": slot, "status": status})
        if status == "ELIGIBLE":
            eligible.append((receipt["cost_micro_usd"], receipt["elapsed_ms"], slot, candidate["candidate_id"], candidate))

    selected = min(eligible)[-1] if eligible else None
    return {
        "schema": "far-guided-search/research-1",
        "status": "CANDIDATE_PENDING_INDEPENDENT_VERIFICATION" if selected else "NO_ELIGIBLE_CANDIDATE",
        "termination": terminated,
        "selected_candidate": selected,
        "total_reported_cost_micro_usd": total_cost,
        "attempts": attempts,
        "nonclaims": ["No source authenticity or external oracle validity established", "No independent review or protected delivery established"],
    }
