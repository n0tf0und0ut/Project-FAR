"""Bounded read-only archive byte audit of 60 AgentAlphaXiv source archives.

No extracted files, model execution, scientific labels, or comparison-arm outputs.
Validate actual bytes against the inventory on one pinned external source
revision. Differences are recorded as reproducibility/provenance observations
and must NOT be interpreted as invalid scientific results without adjudication.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile
from typing import Callable

from agent_alphaxiv_source_screen import canonical, digest, verify_selection, verify_selection_receipt_hash, REVISION, DATASET

PROTOCOL = "FAR-AGENT-ALPHAXIV-002/archive-integrity-v0.1"
MAX_MEMBER_BYTES = 512 * 1024 * 1024
MAX_ARCHIVE_BYTES = 1024 * 1024 * 1024
MAX_TOTAL_BYTES = 4 * 1024 * 1024 * 1024
BUFFER_SIZE = 1024 * 1024


def hash_stream(handle) -> str:
    h = hashlib.sha256()
    for block in iter(lambda: handle.read(BUFFER_SIZE), b""):
        h.update(block)
    return h.hexdigest()


def audit_tar(path: Path, expected: list[dict]) -> dict:
    """Never extract a tar, invoke code, follow links, or trust unvetted names."""
    if path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("archive bytes exceed conservative bound")
    inventory = {}
    for r in expected:
        logical = r["logical_path"]
        if not isinstance(logical, str) or logical in inventory:
            raise ValueError("ambiguous or invalid artifact inventory path")
        inventory[logical] = r
    seen = set()
    present = set()
    matches = mismatches = size_mismatches = unindexed = undesired = 0
    safe_members = 0
    names_unindexed = []
    with tarfile.open(path, "r:*") as tf:
        for m in tf:
            raw = m.name
            parts = raw.split("/")
            if (not raw or raw.startswith("/") or "\\" in raw
                    or ".." in parts or "\x00" in raw or ":" in parts[0]):
                raise ValueError("unsafe tar member name")
            normalized = str(PurePosixPath(raw))
            if normalized in seen:
                raise ValueError("duplicate tar member path")
            seen.add(normalized)
            if m.isdir():
                continue
            if not m.isfile() or m.size < 0 or m.size > MAX_MEMBER_BYTES:
                raise ValueError("unsafe or oversized tar member")
            safe_members += 1
            entry = inventory.get(normalized)
            if entry is None:
                unindexed += 1
                names_unindexed.append(normalized)
                continue
            present.add(normalized)
            if entry.get("in_release_tar") is not True:
                undesired += 1
            if m.size != entry.get("byte_size"):
                size_mismatches += 1
            stream = tf.extractfile(m)
            if stream is None:
                raise ValueError("unreadable regular member")
            with stream:
                actual_hash = hash_stream(stream)
            if actual_hash == entry.get("sha256"):
                matches += 1
            else:
                mismatches += 1
    missing_claimed = sorted(k for k, r in inventory.items()
                             if r.get("in_release_tar") is True and k not in present)
    with path.open("rb") as stream:
        archive_sha256 = hash_stream(stream)
    return {
        "archive_sha256": archive_sha256,
        "archive_bytes": path.stat().st_size,
        "regular_members": safe_members,
        "members_matched_inventory_hash": matches,
        "members_mismatched_inventory_hash": mismatches,
        "members_mismatched_inventory_bytes": size_mismatches,
        "members_unindexed": unindexed,
        "members_marked_excluded_but_present": undesired,
        "members_marked_included_but_missing": len(missing_claimed),
        "unindexed_names_sha256": digest(sorted(names_unindexed)) if names_unindexed else None,
        "missing_included_names_sha256": digest(missing_claimed) if missing_claimed else None,
        "integrity_status": ("BYTE_INVENTORY_MATCH"
                             if not any((mismatches, size_mismatches, unindexed,
                                         undesired, len(missing_claimed)))
                             else "BYTE_INVENTORY_DISAGREEMENT_REQUIRES_ADJUDICATION"),
    }


def audit_archive_selection(receipt: dict, source_rows: list[dict],
                            artifact_rows: list[dict],
                            inventory_sizes: dict[str, int | None],
                            download: Callable[[str], Path],
                            *, max_total_bytes: int = MAX_TOTAL_BYTES) -> dict:
    selected = verify_selection(receipt)
    observed_source = {r["project_id"]: r for r in source_rows}
    if set(observed_source) != {r["project_id"] for r in selected}:
        raise ValueError("source coverage receipt no longer matches selected roster")
    grouped = defaultdict(list)
    for r in artifact_rows:
        grouped[(r.get("project_id"), r.get("version_id"))].append(r)
    rows = []
    remaining = max_total_bytes
    for target in selected:
        pid, vid = target["project_id"], target["latest_version_id"]
        meta = observed_source[pid]
        if meta.get("selected_version_id") != vid:
            raise ValueError("source version identity changed")
        relpath = f"artifacts/{pid}.tar"
        size_hint = inventory_sizes.get(relpath)
        row = {"project_id": pid, "latest_version_id": vid,
               "source_text_sha256": meta["source_text_sha256"],
               "archive_path": relpath,
               "archive_listed_bytes": size_hint,
               "scientific_adjudication": "NOT_PERFORMED",
               "source_code_executed": False}
        if size_hint is None:
            row.update(status="UNVERIFIED_ARCHIVE_SIZE_OR_MISSING")
        elif size_hint > MAX_ARCHIVE_BYTES or size_hint > remaining:
            row.update(status="SKIPPED_PREDECLARED_BYTE_BUDGET")
        else:
            try:
                archive = download(relpath)
                if not isinstance(archive, Path):
                    raise ValueError("download adapter must return a Path")
                result = audit_tar(archive, grouped[(pid, vid)])
                if result["archive_bytes"] != size_hint:
                    result["inventory_archive_size_disagrees"] = True
                    result["integrity_status"] = "BYTE_INVENTORY_DISAGREEMENT_REQUIRES_ADJUDICATION"
                else:
                    result["inventory_archive_size_disagrees"] = False
                remaining -= result["archive_bytes"]
                row.update(status="ARCHIVE_BYTES_EXAMINED", **result)
            except Exception as exc:
                row.update(status="UNVERIFIABLE_ARCHIVE_ERROR",
                           error_type=type(exc).__name__,
                           error_summary=str(exc)[:180])
        rows.append(row)
    summary = {
        "registered": len(rows),
        "archive_bytes_examined": sum(r.get("archive_bytes", 0) for r in rows),
        "archives_examined": sum(r["status"] == "ARCHIVE_BYTES_EXAMINED" for r in rows),
        "archive_download_errors": sum(r["status"] == "UNVERIFIABLE_ARCHIVE_ERROR" for r in rows),
        "archive_budget_or_size_skips": sum(r["status"] == "SKIPPED_PREDECLARED_BYTE_BUDGET" for r in rows),
        "archive_missing_size": sum(r["status"] == "UNVERIFIED_ARCHIVE_SIZE_OR_MISSING" for r in rows),
        "members_matching_inventory_sha256": sum(r.get("members_matched_inventory_hash", 0) for r in rows),
        "members_mismatching_inventory_sha256": sum(r.get("members_mismatched_inventory_hash", 0) for r in rows),
        "unmatched_archive_members": sum(r.get("members_unindexed", 0) for r in rows),
        "unreleased_declared_members_found": sum(r.get("members_marked_excluded_but_present", 0) for r in rows),
        "declared_included_members_missing": sum(r.get("members_marked_included_but_missing", 0) for r in rows),
        "independently_adjudicated_scientific_claims": 0,
        "paired_far_checker_executions": 0,
    }
    result = {"protocol": PROTOCOL, "dataset_revision": REVISION,
              "selection_manifest_sha256": receipt["manifest_canonical_sha256"],
              "source_coverage_sha256": "5fecd596dacc52ba696789ad57294b5b0544670f1b777ea0effd6c300917a21c",
              "status": "EXPLORATORY_SOURCE_BYTE_VERIFICATION_NOT_SCIENTIFIC_EVALUATION",
              "byte_budget": max_total_bytes,
              "summary": summary, "records": rows,
              "limitations": [
                  "Archive bytes are only release-visible, redacted artifacts.",
                  "Original inventory hashes may precede release redaction; a mismatch requires explanation, not a scientific verdict.",
                  "No source experiment code was executed; raw data and checkpoints excluded by publisher cannot be regenerated from these archives.",
                  "No independent human adjudication or prospective FAR-versus-checker study-arm execution has occurred.",
              ]}
    result["receipt_sha256"] = digest(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--source-coverage", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    from datasets import load_dataset
    from huggingface_hub import HfApi, hf_hub_download
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    verify_selection_receipt_hash(selection)
    source = json.loads(args.source_coverage.read_text(encoding="utf-8"))
    if source.get("receipt_sha256") != "5fecd596dacc52ba696789ad57294b5b0544670f1b777ea0effd6c300917a21c":
        raise ValueError("unrecognized source-coverage evidence")
    check_source = dict(source)
    check_source.pop("receipt_sha256")
    if digest(check_source) != source["receipt_sha256"]:
        raise ValueError("source-coverage evidence digest mismatch")
    api = HfApi()
    if api.dataset_info(DATASET, revision=REVISION).sha != REVISION:
        raise ValueError("pinned source commit changed")
    sizes = {item.path: item.size for item in api.list_repo_tree(
        DATASET, path_in_repo="artifacts", repo_type="dataset",
        revision=REVISION, recursive=False) if getattr(item, "path", "").endswith(".tar")}
    artifacts = list(load_dataset(DATASET, "artifacts", split="train", revision=REVISION))
    if len(artifacts) != 82805:
        raise ValueError("source artifact table count drift")
    def fetch(path: str) -> Path:
        return Path(hf_hub_download(DATASET, filename=path, repo_type="dataset",
                                    revision=REVISION))
    outcome = audit_archive_selection(selection, source["records"], artifacts, sizes, fetch)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(outcome, indent=2, ensure_ascii=False, sort_keys=True)+"\n", encoding="utf-8")
    print("SOURCE_BYTES_SUMMARY="+json.dumps(outcome["summary"], sort_keys=True), flush=True)
    print("SOURCE_BYTES_RECEIPT_SHA256="+outcome["receipt_sha256"], flush=True)
    for r in outcome["records"]:
        print("SOURCE_BYTES_ROW="+json.dumps(r, sort_keys=True, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
