"""Source-bound metrics for FAR's frozen v0.3 tool-agent traces.

This adapter calls the existing independent-from-metric runner replay, not
a client-supplied success/denominator declaration. Audit strength: exact
historical-byte and deterministic trace correspondence, not external truth
or trusted model-execution attestation.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import zipfile

from tools import tool_agent_reliability as runner

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_PATH = "research/tool-agent-reliability/result/v0.3/evidence-v0.3.zip"
ARCHIVE_SHA256 = "b4e1ccd17a46db8f91ccee29232853bdd6ba5881a1f6c747351d2dfc242a7809"
PROTOCOL_PATH = "research/tool-agent-reliability/protocol-v0.3.json"
PROTOCOL_SHA256 = "ab6325bbf76d5b02b2a766402147f03eb2c8454b18a9f5896431546f41106e33"
SOURCE_COMMIT = "6c382c798df0a95824b79e76263318865ee24c68"
NESTED_ARCHIVE = "original-artifacts/13224187919.zip"
MAX_ARCHIVE = 100_000_000
MAX_MEMBER = 4_000_000

spec = importlib.util.spec_from_file_location("far_metric_grounding", Path(__file__).with_name("metric_grounding.py"))
if spec is None or spec.loader is None:
    raise RuntimeError("metric guard source unavailable")
mg = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mg
spec.loader.exec_module(mg)


def _require(condition, code, description):
    if not condition:
        raise mg.GroundingError(code, description)


def _read_pinned(root: Path, relative: str, digest: str, *, limit: int = MAX_ARCHIVE) -> bytes:
    path = Path(root).resolve() / relative
    _require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(Path(root).resolve()),
             "SOURCE_MISSING", "expected frozen source file not available as a regular file")
    _require(path.stat().st_size <= limit, "SOURCE_SIZE_LIMIT", "frozen source too large")
    raw = path.read_bytes()
    _require(hashlib.sha256(raw).hexdigest() == digest, "SOURCE_DIGEST_MISMATCH",
             "frozen source bytes differ from the recorded original")
    return raw


def _archive_jsons(raw: bytes) -> list[dict]:
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as outer:
            _require(len(outer.infolist()) == len({x.filename for x in outer.infolist()}),
                     "DUPLICATE_ARCHIVE_MEMBER", "outer archive has duplicate entries")
            member = outer.getinfo(NESTED_ARCHIVE)
            _require(member.file_size <= MAX_ARCHIVE, "SOURCE_SIZE_LIMIT", "nested evidence archive too large")
            nested_bytes = outer.read(member)
        with zipfile.ZipFile(io.BytesIO(nested_bytes)) as inner:
            items = inner.infolist()
            _require(len(items) == len({x.filename for x in items}),
                     "DUPLICATE_ARCHIVE_MEMBER", "nested archive has duplicate entries")
            names = sorted(x.filename for x in items if x.filename.startswith("scored/") and x.filename.endswith(".json"))
            _require(len(names) == 72, "EVIDENCE_INCOMPLETE", "frozen scored archive must contain 72 run records")
            records = []
            for name in names:
                info = inner.getinfo(name)
                _require(info.file_size <= MAX_MEMBER and not info.is_dir(),
                         "SOURCE_SIZE_LIMIT", "individual trace exceeds recorded limit")
                records.append(runner.strict_json(inner.read(info)))
            return records
    except (zipfile.BadZipFile, KeyError, RuntimeError, OSError) as exc:
        raise mg.GroundingError("INVALID_SOURCE_ARCHIVE", "frozen evidence could not be decoded") from exc


def metric_catalog():
    return {"format": mg.CATALOG_FORMAT, "status": "Research", "metrics": [{
        "id": "v03_registered_success",
        "operator": "registered_success_rate", "unit": "percent",
        "formula": "success / registered",
        "definition": "Succeeded executions divided by all 72 preregistered slots on the frozen FAR-TOOL-AGENT-001 v0.3 scored authored simulation; excludes disjoint preflight; not a population reliability estimate.",
        "review_status": "UNREVIEWED_RESEARCH",
    }]}


def reconstruct_events(root: Path = ROOT) -> dict:
    """Rebuild eligible slots and outcomes from a pinned protocol and all raw traces."""
    raw_protocol = _read_pinned(root, PROTOCOL_PATH, PROTOCOL_SHA256, limit=MAX_MEMBER)
    protocol = runner.strict_json(raw_protocol)
    runner.validate_protocol(protocol)
    raw_archive = _read_pinned(root, ARCHIVE_PATH, ARCHIVE_SHA256)
    records = _archive_jsons(raw_archive)
    sources = [rec.get("source") for rec in records]
    _require(all(type(src) is dict and src.get("commit") == SOURCE_COMMIT and src == sources[0] for src in sources),
             "EXECUTION_SOURCE_DRIFT", "raw execution sources do not match the frozen execution commit")
    summary = runner.analyze(protocol, records, PROTOCOL_SHA256, source=sources[0], phase="scored")
    _require(summary["complete"] and summary["expected_slots"] == 72 and summary["replayed_records"] == 72,
             "TRACE_REPLAY_FAILURE", "raw replay did not verify every registered execution")
    scored = [task for task in protocol["tasks"] if task["phase"] == "scored"]
    slots = [{"id": f"{task['id']}-seed{seed}", "case_id": f"{task['id']}-seed{seed}", "arm": "control"}
             for task in scored for seed in protocol["seeds"]]
    outcomes = {(row["task_id"], row["seed"]): row for row in summary["rows"]}
    observations = [{"slot_id": slot["id"],
                     "outcome": "success" if outcomes[(task["id"], seed)]["passed"] else "failure",
                     "source_id": "frozen-v03"}
                    for task in scored for seed in protocol["seeds"]
                    for slot in [{"id": f"{task['id']}-seed{seed}"}]]
    data = {
        "format": mg.DATA_FORMAT,
        "study_id": "FAR-TOOL-AGENT-001-v03",
        "scope": "original-authored-virtual-workspace-scored-only",
        "sources": [{"id": "frozen-v03", "uri": "file:" + ARCHIVE_PATH,
                     "sha256": ARCHIVE_SHA256,
                     "assurance": "DECLARED_NOT_INDEPENDENTLY_VERIFIED"}],
        "registered_slots": slots, "observations": observations,
    }
    mg.events_validate(data)
    return data


def verify_events(submitted: dict, *, root: Path = ROOT):
    """Reject a coherent but invented table, not merely a wrong aggregate."""
    correct = reconstruct_events(root)
    _require(mg.strict_load(json.dumps(submitted, sort_keys=True, allow_nan=False).encode()) == correct,
             "SOURCE_CORRESPONDENCE_FAILURE", "submitted rows differ from frozen replayed records")
    return correct


def grounded_report(*, root: Path = ROOT, asserted_value: str | None = None,
                    submitted_events: dict | None = None) -> dict:
    data = reconstruct_events(root) if submitted_events is None else verify_events(submitted_events, root=root)
    catalog_raw = json.dumps(metric_catalog(), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    events_raw = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    result = mg.evaluate(catalog_raw, events_raw, metric_id="v03_registered_success",
                         arm="control", asserted_value=asserted_value)
    result["source_correspondence"] = {
        "status": "PINNED_ARCHIVE_AND_ALL_72_RAW_TRACES_REPLAYED",
        "archive_sha256": ARCHIVE_SHA256,
        "protocol_sha256": PROTOCOL_SHA256,
        "original_execution_source_commit": SOURCE_COMMIT,
        "external_attestation": "NOT_ESTABLISHED",
        "independent_ground_truth": "NOT_ESTABLISHED",
    }
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--assert-value")
    args = parser.parse_args(argv)
    try:
        result = grounded_report(root=args.root, asserted_value=args.assert_value)
    except (mg.GroundingError, ValueError, TypeError, KeyError, OSError) as exc:
        error = {"status": "UNANSWERABLE", "code": getattr(exc, "code", "SOURCE_REPLAY_ERROR"),
                 "reason": str(exc)}
        print(json.dumps(error, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
