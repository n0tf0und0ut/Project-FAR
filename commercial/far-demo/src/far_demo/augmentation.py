"""Research-only human reasoning augmentation, with replayable user-owned sessions.

This layer only checks fields the user supplied. It does not evaluate the truth of
arbitrary claims, convert prose to a governed FAR contract, or certify reasoning.
The prompts reuse FAR-ELENCHUS question *purposes*, not its conforming session
format. Existing canonical validators are deliberately not impersonated.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

router = APIRouter()
SCHEMA = "far-augmentation-prototype/0.1"
MAX_BODY = 500_000
MAX_SESSION_BODY = 8 * 1024 * 1024
# A generated history has <=20 revisions, each <=3000+3000+8*2000
# characters, and <=57,200 basis characters. Even 12-byte JSON surrogate-pair
# escaping plus metadata/report overhead fits 8 MiB. Initial submissions keep
# their 500 KB cap; only endpoints carrying existing histories use this bound.
MAX_REVISIONS = 20
LIMITATIONS = (
    "All observations, source labels and explanations are user supplied and unverified.",
    "Question coverage is structural; it is not semantic critique, formal proof, or a FAR-ELENCHUS-1.0 session.",
    "SHA-256 detects unchanged bytes relative to this record; it is not authentication or proof of real-world events.",
    "No improvement in human reasoning, accuracy, calibration or learning has been established.",
)


def _text(value: Any, name: str, *, max_length: int = 3000, optional: bool = False) -> str:
    if not isinstance(value, str) or len(value) > max_length:
        raise ValueError(f"{name} must be text of at most {max_length} characters")
    if not value.strip() and not optional:
        raise ValueError(f"{name} cannot be empty")
    return value


def _percent(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
        raise ValueError(f"{name} must be an integer from 0 to 100")
    return value


def _list_of_text(value: Any, name: str) -> list[str]:
    if not isinstance(value, list) or len(value) > 12:
        raise ValueError(f"{name} must be a list of at most 12 statements")
    return [_text(item, f"{name}[{i}]", max_length=800) for i, item in enumerate(value)]


def _evidence(value: Any, name: str) -> list[dict[str, str]]:
    if not isinstance(value, list) or len(value) > 12:
        raise ValueError(f"{name} must be a list of at most 12 entries")
    result = []
    for i, entry in enumerate(value):
        if not isinstance(entry, dict) or set(entry) != {"statement", "source"}:
            raise ValueError(f"{name}[{i}] requires exactly statement and source")
        result.append({
            "statement": _text(entry["statement"], f"{name}[{i}].statement", max_length=800),
            "source": _text(entry["source"], f"{name}[{i}].source", max_length=500, optional=True),
        })
    return result


def _basis(raw: Any) -> dict[str, Any]:
    fields = {"claim", "reasoning", "confidence", "supporting_evidence", "challenging_evidence",
              "assumptions", "alternatives", "falsifier"}
    if not isinstance(raw, dict) or set(raw) != fields:
        raise ValueError("input requires exactly the documented eight fields")
    return {
        "claim": _text(raw["claim"], "claim"),
        "reasoning": _text(raw["reasoning"], "reasoning", optional=True),
        "confidence": _percent(raw["confidence"], "confidence"),
        "supporting_evidence": _evidence(raw["supporting_evidence"], "supporting_evidence"),
        "challenging_evidence": _evidence(raw["challenging_evidence"], "challenging_evidence"),
        "assumptions": _list_of_text(raw["assumptions"], "assumptions"),
        "alternatives": _list_of_text(raw["alternatives"], "alternatives"),
        "falsifier": _text(raw["falsifier"], "falsifier", max_length=800, optional=True),
    }


def _questions(basis: dict[str, Any]) -> list[dict[str, str]]:
    # These are prompts about recorded omissions, not inferred mental errors.
    rules = [
        ("source", "TEST_WARRANT", not basis["supporting_evidence"],
         "Which direct observation supports this claim, and where could someone inspect it?"),
        ("provenance", "TEST_WARRANT", any(not e["source"].strip() for e in basis["supporting_evidence"]),
         "Which supplied observations lack a traceable source or method?"),
        ("counterevidence", "SEEK_COUNTEREXAMPLE", not basis["challenging_evidence"],
         "What is the strongest relevant counterevidence you have sought, including evidence against your preferred answer?"),
        ("assumption", "EXPOSE_ASSUMPTION", not basis["assumptions"],
         "Which premise must be true for your inference to hold? What would happen if it were false?"),
        ("alternatives", "DISTINGUISH_INTERPRETATIONS", not basis["alternatives"],
         "What competing explanation fits the same observations? What test distinguishes it?"),
        ("falsifier", "SEEK_COUNTEREXAMPLE", not basis["falsifier"].strip(),
         "What specific observation would cause you to withdraw or materially weaken your claim?"),
        ("warrant", "TEST_WARRANT", not basis["reasoning"].strip(),
         "State the inference rule or reasoning connecting those observations to your conclusion."),
    ]
    found = [{"id": code, "purpose": purpose, "question": prompt,
              "reason": "A required field is missing or an evidence source is not recorded."}
             for code, purpose, missing, prompt in rules if missing]
    if basis["confidence"] >= 90 and found:
        found.append({"id": "certainty", "purpose": "TEST_WARRANT",
                      "question": "What independent test would justify this confidence level despite the recorded gaps?",
                      "reason": "High stated confidence coexists with missing fields; no calibration claim is implied."})
    if not found:
        found.append({"id": "stress-test", "purpose": "TEST_CONSEQUENCE",
                      "question": "Even with every field supplied, which observation would most strongly distinguish your explanation from the strongest alternative?",
                      "reason": "Completeness of supplied fields cannot establish truth or relevance."})
    return found


def _hash(data: dict[str, Any]) -> str:
    canonical = json.dumps({k: v for k, v in data.items() if k != "sha256"},
                           sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _sealed(data: dict[str, Any]) -> dict[str, Any]:
    result = dict(data)
    result["sha256"] = _hash(result)
    return result


def start(raw: Any) -> dict[str, Any]:
    basis = _basis(raw)
    return _sealed({"schema": SCHEMA, "basis": basis, "basis_sha256": _hash(basis), "questions": _questions(basis),
                    "revisions": [], "limitations": list(LIMITATIONS),
                    "interpretation": "UNKNOWN", "evidence_status": "USER_SUPPLIED_UNVERIFIED"})


def verify(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != {"schema", "basis", "basis_sha256", "questions", "revisions", "limitations",
                                                  "interpretation", "evidence_status", "sha256"}:
        raise ValueError("Invalid augmentation session structure")
    if raw["schema"] != SCHEMA or raw["interpretation"] != "UNKNOWN" or raw["evidence_status"] != "USER_SUPPLIED_UNVERIFIED":
        raise ValueError("Unknown augmentation session schema/status")
    basis = _basis(raw["basis"])
    if basis != raw["basis"] or _hash(basis) != raw["basis_sha256"] or _questions(basis) != raw["questions"] or raw["limitations"] != list(LIMITATIONS):
        raise ValueError("Session basis, diagnostic questions or limitations were changed")
    events = raw["revisions"]
    if not isinstance(events, list) or len(events) > MAX_REVISIONS:
        raise ValueError("Invalid revision history")
    expected_previous = _hash({k: v for k, v in raw.items() if k not in {"revisions", "sha256"}} | {"revisions": []})
    previous_time = None
    for i, event in enumerate(events):
        if not isinstance(event, dict) or set(event) != {"index", "previous_sha256", "recorded_at", "revised_claim",
                                                        "confidence", "rationale", "answers", "sha256"}:
            raise ValueError(f"Invalid revision {i} structure")
        if type(event["index"]) is not int or event["index"] != i + 1 or event["previous_sha256"] != expected_previous:
            raise ValueError(f"Invalid revision {i} sequence or linkage")
        if not isinstance(event["recorded_at"], str) or not event["recorded_at"].endswith("+00:00"):
            raise ValueError(f"Invalid revision {i} time representation")
        try:
            this_time = datetime.fromisoformat(event["recorded_at"])
            if this_time.tzinfo is None or this_time.utcoffset() != timedelta(0):
                raise ValueError("Revision time must be timezone-aware UTC")
            if previous_time is not None and this_time < previous_time:
                raise ValueError("Revision times must be nondecreasing")
            previous_time = this_time
        except ValueError as exc:
            raise ValueError(f"Invalid revision {i} time") from exc
        _text(event["revised_claim"], "revised_claim")
        _percent(event["confidence"], "confidence")
        _text(event["rationale"], "rationale")
        _answers(event["answers"], raw["questions"])
        if _hash(event) != event["sha256"]:
            raise ValueError(f"Revision {i} fingerprint mismatch")
        expected_previous = event["sha256"]
    if not isinstance(raw["sha256"], str) or _hash(raw) != raw["sha256"]:
        raise ValueError("Session fingerprint mismatch")
    return {"valid": True, "sha256": raw["sha256"], "revision_count": len(events),
            "assurance": "STRUCTURAL_INTEGRITY_ONLY"}


def _answers(raw: Any, questions: list[dict[str, str]]) -> dict[str, str]:
    ids = {q["id"] for q in questions}
    if not isinstance(raw, dict) or not raw or not set(raw).issubset(ids) or len(raw) > len(ids):
        raise ValueError("Answer at least one registered question using its exact question ID")
    return {key: _text(value, f"answers.{key}", max_length=2000) for key, value in raw.items()}


def revise(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != {"session", "revised_claim", "confidence", "rationale", "answers"}:
        raise ValueError("Revision requires session, revised_claim, confidence, rationale and answers")
    session = raw["session"]
    verify(session)
    if len(session["revisions"]) >= MAX_REVISIONS:
        raise ValueError("Maximum revisions reached; export this session and start another")
    event = _sealed({
        "index": len(session["revisions"]) + 1,
        "previous_sha256": session["revisions"][-1]["sha256"] if session["revisions"] else
                           _hash({k: v for k, v in session.items() if k not in {"revisions", "sha256"}} | {"revisions": []}),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "revised_claim": _text(raw["revised_claim"], "revised_claim"),
        "confidence": _percent(raw["confidence"], "confidence"),
        "rationale": _text(raw["rationale"], "rationale"),
        "answers": _answers(raw["answers"], session["questions"]),
    })
    updated = _sealed({**{k: v for k, v in session.items() if k != "sha256"},
                       "revisions": [*session["revisions"], event]})
    verify(updated)
    return updated


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _finite_float(token: str) -> float:
    value = float(token)
    if not math.isfinite(value):
        raise ValueError("Non-finite JSON number")
    return value


def _strict_json_loads(source: str | bytes) -> Any:
    try:
        return json.loads(source, object_pairs_hook=_unique_pairs,
                          parse_float=_finite_float,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Invalid numeric constant")))
    except RecursionError as exc:
        raise ValueError("JSON nesting exceeds the supported decoder limit") from exc


async def _json(request: Request, *, max_body: int = MAX_BODY) -> Any:
    body = await request.body()
    if len(body) > max_body:
        raise HTTPException(413, "Augmentation input exceeds the permitted request size")
    try:
        return _strict_json_loads(body)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(400, f"Invalid JSON: {exc}") from exc


@router.get("/augment", response_class=HTMLResponse)
def augmentation_page() -> str:
    return (Path(__file__).parent / "augmentation.html").read_text(encoding="utf-8")


@router.post("/api/augment/start")
async def augmentation_start(request: Request) -> dict[str, Any]:
    try:
        return start(await _json(request))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/api/augment/revise")
async def augmentation_revise(request: Request) -> dict[str, Any]:
    try:
        return revise(await _json(request, max_body=MAX_SESSION_BODY))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/api/augment/verify")
async def augmentation_verify(request: Request) -> dict[str, Any]:
    try:
        return verify(await _json(request, max_body=MAX_SESSION_BODY))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
