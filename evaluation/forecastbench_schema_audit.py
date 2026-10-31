"""Audit a real archived ForecastBench question set without issuing model forecasts.

Network access is explicit and confined to an independently pinned Git blob.
The audit is source/schema validation, NEVER prospective performance evidence.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import sys
from urllib.request import Request, urlopen

from evaluation.prospective_forecast_runner import MARKET, ProspectiveError, parse_question_set

ARCHIVED_URL = (
    "https://raw.githubusercontent.com/forecastingresearch/"
    "forecastbench-datasets/main/datasets/question_sets/2026-10-25-llm.json"
)
ARCHIVED_BLOB_SHA1 = "d2f8e23707fd0859bf78d77fefbf1b74cbc8aabb"


def audit_archive(raw: bytes, *, expected_git_blob_sha: str = ARCHIVED_BLOB_SHA1) -> dict:
    if not isinstance(raw, bytes) or len(raw) > 8 * 1024 * 1024:
        raise ProspectiveError("archive missing or exceeds 8 MB size bound")
    git_blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if git_blob != expected_git_blob_sha:
        raise ProspectiveError("pinned real question-set Git blob SHA mismatch")
    try:
        document = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ProspectiveError("archived source is not UTF-8 JSON") from exc
    due, units = parse_question_set(document)
    all_questions = document["questions"]
    if len(all_questions) != 500:
        raise ProspectiveError("expected 500 official source questions")
    combinations = [row for row in all_questions if isinstance(row.get("id"), list)]
    eligible = [row for row in all_questions if isinstance(row.get("id"), str)]
    if len(combinations) + len(eligible) != len(all_questions):
        raise ProspectiveError("unrecognized question ID type")
    actual = Counter(row["source"] for row in all_questions)
    unit_counts = Counter(row["source"] for row in units)
    if not units:
        raise ProspectiveError("no eligible forecast units")
    return {
        "status": "ARCHIVED_SCHEMA_VERIFIED_NOT_PROSPECTIVE",
        "forecast_due_date": due.isoformat(),
        "git_blob_sha1": git_blob,
        "content_sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "question_count": len(all_questions),
        "eligible_questions": len(eligible),
        "excluded_combination_questions": len(combinations),
        "forecast_units": len(units),
        "three_arm_model_requests_required": 3 * len(units),
        "source_question_counts": dict(sorted(actual.items())),
        "forecast_unit_counts": dict(sorted(unit_counts.items())),
    }


def main(argv=None):
    p = argparse.ArgumentParser(description="Validate real archived ForecastBench schema and Git object hash")
    p.add_argument("--url", default=ARCHIVED_URL)
    p.add_argument("--expected-git-blob-sha", default=ARCHIVED_BLOB_SHA1)
    args = p.parse_args(argv)
    if args.url != ARCHIVED_URL:
        raise ProspectiveError("only audited public archived source URL is allowed")
    request = Request(args.url, headers={"User-Agent": "Project-FAR-forecastbench-schema-audit/0.1"})
    try:
        with urlopen(request, timeout=45) as response:
            raw = response.read(8 * 1024 * 1024 + 1)
        result = audit_archive(raw, expected_git_blob_sha=args.expected_git_blob_sha)
    except (OSError, ValueError) as exc:
        print("SCHEMA AUDIT FAILED: " + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
