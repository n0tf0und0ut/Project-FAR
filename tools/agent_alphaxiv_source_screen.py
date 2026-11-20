"""Read-only source-availability audit for the fixed AgentAlphaXiv-002 candidate.

This tool checks *source coverage*, not scientific correctness or eligibility.
It never executes source code, extracts archives, repairs missing rows, or
changes the selection. Its output can support independent prospective screening.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

DATASET = "alphaXiv/AgentAlphaXiv"
REVISION = "cc892aab131be3872283e1a778af663382315817"
COUNTS = {"studies": 916, "paper_texts": 914, "artifacts": 82805, "versions": 1352}
PROTOCOL = "FAR-AGENT-ALPHAXIV-002/source-coverage-v0.1"
MANIFEST = "771d7b6cb86d93b804e165def7507a6ec517d59839d65e603c911459d0cab603"
HEX = re.compile(r"^[0-9a-f]{64}$")


def canonical(obj: object) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(obj: object) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


def verify_selection(receipt: dict) -> list[dict]:
    if (receipt.get("manifest_canonical_sha256"), receipt.get("dataset_revision"),
            receipt.get("sample_size")) != (MANIFEST, REVISION, 60):
        raise ValueError("unrecognized source or frozen selection")
    rows = receipt.get("selected")
    if not isinstance(rows, list) or len(rows) != 60:
        raise ValueError("expected 60 selected records")
    ids = [r.get("project_id") for r in rows]
    if any(not isinstance(v, str) or not v for v in ids) or len(set(ids)) != 60:
        raise ValueError("invalid or duplicate project IDs")
    if any(r.get("screening_status") != "UNSCREENED" for r in rows):
        raise ValueError("source screen must start with unadjudicated selection")
    return rows


def audit_source(receipt: dict, paper_rows: list[dict],
                 artifact_rows: list[dict], version_rows: list[dict],
                 release_paths: set[str], *, strict_counts: bool = True) -> dict:
    selected = verify_selection(receipt)
    if strict_counts and (len(paper_rows) != COUNTS["paper_texts"]
                         or len(artifact_rows) != COUNTS["artifacts"]
                         or len(version_rows) != COUNTS["versions"]):
        raise ValueError("upstream source count changed or is incomplete")
    if not isinstance(release_paths, set):
        raise ValueError("release paths must be an exact set")
    text_index = {}
    for r in paper_rows:
        pid = r.get("project_id")
        if not isinstance(pid, str) or pid in text_index or not isinstance(r.get("text"), str):
            raise ValueError("paper_texts schema/identity violation")
        text_index[pid] = r["text"]
    versions = defaultdict(list)
    for r in version_rows:
        versions[r.get("project_id")].append(r)
    artifacts = defaultdict(list)
    for r in artifact_rows:
        artifacts[r.get("project_id")].append(r)
    records = []
    for target in selected:
        pid = target["project_id"]
        version = target["latest_version_id"]
        latest = [v for v in versions[pid] if v.get("is_latest") is True]
        # Fail closed on a metadata contradiction, never select a favorable alternative.
        if len(latest) != 1 or latest[0].get("version_id") != version:
            raise ValueError(f"latest-version identity conflict: {pid}")
        text = text_index.get(pid)
        rows = artifacts[pid]
        for a in rows:
            if not isinstance(a.get("sha256"), str) or not HEX.fullmatch(a["sha256"]):
                raise ValueError(f"malformed artifact sha256: {pid}")
            if type(a.get("in_release_tar")) is not bool:
                raise ValueError(f"malformed in_release_tar field: {pid}")
        latest_rows = [a for a in rows if a.get("version_id") == version]
        kind_counts = Counter(str(a.get("kind")) for a in latest_rows)
        claimed_release = [a for a in latest_rows if a["in_release_tar"]]
        missing_release = [a for a in latest_rows if not a["in_release_tar"]]
        record = {
            "project_id": pid,
            "selected_version_id": version,
            "selection_digest": target["selection_digest"],
            "source_text_present": text is not None,
            "source_text_bytes": len(text.encode("utf-8")) if text is not None else None,
            "source_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest() if text is not None else None,
            "latest_version_found": True,
            "published_version_count": len(versions[pid]),
            "total_artifact_records": len(rows),
            "latest_artifact_records": len(latest_rows),
            "latest_artifact_kind_counts": dict(sorted(kind_counts.items())),
            "latest_marked_in_release_tar": len(claimed_release),
            "latest_marked_excluded_from_release": len(missing_release),
            "latest_marked_excluded_bytes": sum(int(a["byte_size"]) for a in missing_release),
            "pdf_path_present_in_source_listing": f"papers/{pid}.pdf" in release_paths,
            "tar_path_present_in_source_listing": f"artifacts/{pid}.tar" in release_paths,
            "pdf_bytes_independently_checked": False,
            "tar_bytes_independently_checked": False,
            "native_claims_screened": 0,
            "scientific_eligibility": "NOT_ADJUDICATED",
        }
        records.append(record)
    summary = {
        "selected": len(records),
        "paper_text_present": sum(int(r["source_text_present"]) for r in records),
        "pdf_paths_listed": sum(int(r["pdf_path_present_in_source_listing"]) for r in records),
        "tar_paths_listed": sum(int(r["tar_path_present_in_source_listing"]) for r in records),
        "papers_with_latest_artifact_rows": sum(int(r["latest_artifact_records"] > 0) for r in records),
        "latest_artifact_rows": sum(r["latest_artifact_records"] for r in records),
        "marked_latest_release_members": sum(r["latest_marked_in_release_tar"] for r in records),
        "marked_latest_unreleased_members": sum(r["latest_marked_excluded_from_release"] for r in records),
        "native_claims_adjudicated": 0,
        "paired_far_checker_runs": 0,
    }
    result = {
        "protocol": PROTOCOL,
        "source_revision": REVISION,
        "selection_manifest_sha256": MANIFEST,
        "status": "SOURCE_PRESENCE_AUDIT_ONLY_NOT_SCIENTIFIC_EVALUATION",
        "source_table_counts": {"paper_texts": len(paper_rows), "artifacts": len(artifact_rows), "versions": len(version_rows)},
        "summary": summary,
        "records": records,
        "limitations": [
            "Hugging Face release file listing is metadata, not independent byte verification.",
            "Extracted paper text and artifact inventory cannot prove experimental truth.",
            "Source release excludes approximately 62 GB of raw results, logs and checkpoints.",
            "No independent eligibility determination, source execution, or study-arm adjudication.",
        ],
    }
    result["receipt_sha256"] = digest(result)
    return result


def from_hub() -> tuple[list[dict], list[dict], list[dict], set[str]]:
    try:
        from datasets import load_dataset
        from huggingface_hub import HfApi
    except ImportError as exc:
        raise RuntimeError("install datasets==4.4.1 and huggingface-hub") from exc
    api = HfApi()
    info = api.dataset_info(DATASET, revision=REVISION)
    if info.sha != REVISION:
        raise ValueError("source revision resolved to unexpected commit")
    paths = set(api.list_repo_files(DATASET, repo_type="dataset", revision=REVISION))
    tables = [list(load_dataset(DATASET, name, split="train", revision=REVISION))
              for name in ("paper_texts", "artifacts", "versions")]
    return (*tables, paths)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = json.loads(args.selection.read_text(encoding="utf-8"))
    result = audit_source(receipt, *from_hub())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("SOURCE_AUDIT_SUMMARY=" + json.dumps(result["summary"], sort_keys=True), flush=True)
    print("SOURCE_AUDIT_RECEIPT_SHA256=" + result["receipt_sha256"], flush=True)
    print("SOURCE_AUDIT_INPUT_MANIFEST=" + result["selection_manifest_sha256"], flush=True)
    for record in result["records"]:
        print("SOURCE_AUDIT_ROW=" + json.dumps(record, sort_keys=True, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
