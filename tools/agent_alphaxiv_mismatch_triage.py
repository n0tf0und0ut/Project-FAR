"""Second-pass forensic classification of already observed release-member mismatches.

Re-downloads the exact pinned 60 archives, requires their byte-identical
SHA-256 digests from the first pass, then reports mismatch kind and format.
No source code is executed. Cannot establish why a member changed: release
redaction is a hypothesis, not an independently verified explanation.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

from agent_alphaxiv_source_screen import digest, REVISION, DATASET
from agent_alphaxiv_byte_audit import audit_tar, hash_stream, BUFFER_SIZE

PROTOCOL = "FAR-AGENT-ALPHAXIV-002/archive-mismatch-triage-v0.1"
ORIGINAL_RECEIPT_SHA256 = "dd0375ea74c91ca65cc19eb6bf03ea3dea24c6ff338b90fbcba0c73c5911ad86"


def classify_mismatches(archive: Path, metadata: list[dict], expected_prior: dict) -> dict:
    with archive.open("rb") as handle:
        current_sha = hash_stream(handle)
    if current_sha != expected_prior["archive_sha256"]:
        raise ValueError("original archive bytes changed")
    verification = audit_tar(archive, metadata)
    for field in ("archive_sha256", "archive_bytes", "regular_members",
                  "members_matched_inventory_hash", "members_mismatched_inventory_hash",
                  "members_mismatched_inventory_bytes", "members_unindexed",
                  "members_marked_excluded_but_present", "members_marked_included_but_missing",
                  "integrity_status"):
        if verification.get(field) != expected_prior.get(field):
            raise ValueError("original archive audit did not reproduce: " + field)
    inventory = {r["logical_path"]: r for r in metadata}
    details = []
    with tarfile.open(archive, mode="r:*") as tf:
        for member in tf:
            if not member.isfile():
                continue
            name = str(PurePosixPath(member.name))
            entry = inventory.get(name)
            if entry is None:
                continue  # Already counted by audit_tar, and must be zero in frozen prior.
            data = tf.extractfile(member)
            if data is None:
                raise ValueError("unreadable tar member")
            with data:
                h = hash_stream(data)
            if h != entry["sha256"]:
                details.append({
                    "artifact_kind": str(entry.get("kind")),
                    "artifact_content_type": str(entry.get("content_type")),
                    "extension": PurePosixPath(name).suffix.lower(),
                    "logical_path_sha256": hashlib.sha256(name.encode("utf-8")).hexdigest(),
                    "declared_sha256": entry["sha256"],
                    "released_sha256": h,
                    "declared_bytes": entry.get("byte_size"),
                    "released_bytes": member.size,
                    "size_changed": entry.get("byte_size") != member.size,
                })
    if len(details) != verification["members_mismatched_inventory_hash"]:
        raise ValueError("mismatch diagnosis does not reconcile with first audit")
    return {"project_id": expected_prior["project_id"],
            "archive_sha256": current_sha,
            "mismatches": sorted(details, key=lambda x: x["logical_path_sha256"])}


def summarize(rows: list[dict], expected_count: int) -> dict:
    if len(rows) != 60:
        raise ValueError("must account for exact 60 selected archives")
    details = [d for row in rows for d in row["mismatches"]]
    if len(details) != expected_count:
        raise ValueError("mismatch total drift")
    kinds = Counter(d["artifact_kind"] for d in details)
    extensions = Counter(d["extension"] for d in details)
    content_types = Counter(d["artifact_content_type"] for d in details)
    return {
        "archives_reverified_identical": len(rows),
        "mismatching_members": len(details),
        "members_with_changed_byte_size": sum(d["size_changed"] for d in details),
        "affected_archives": sum(bool(row["mismatches"]) for row in rows),
        "mismatches_by_artifact_kind": dict(sorted(kinds.items())),
        "mismatches_by_file_extension": dict(sorted(extensions.items())),
        "mismatches_by_content_type": dict(sorted(content_types.items())),
        "scientific_errors_adjudicated": 0,
        "publisher_redaction_causes_proven": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior-receipt", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    prior = json.loads(args.prior_receipt.read_text(encoding="utf-8"))
    prior_hash = prior.pop("receipt_sha256", None)
    if prior_hash != ORIGINAL_RECEIPT_SHA256 or digest(prior) != prior_hash:
        raise ValueError("prior byte receipt changed")
    if len(prior["records"]) != 60 or prior["dataset_revision"] != REVISION:
        raise ValueError("prior roster not recognized")
    from datasets import load_dataset
    from huggingface_hub import HfApi, hf_hub_download
    if HfApi().dataset_info(DATASET, revision=REVISION).sha != REVISION:
        raise ValueError("dataset revision changed")
    artifacts = list(load_dataset(DATASET, "artifacts", split="train", revision=REVISION))
    if len(artifacts) != 82805:
        raise ValueError("artifact source count changed")
    grouped = defaultdict(list)
    for a in artifacts:
        grouped[(a["project_id"], a["version_id"])].append(a)
    results = []
    for prior_record in prior["records"]:
        pid = prior_record["project_id"]
        archive = Path(hf_hub_download(DATASET, filename=f"artifacts/{pid}.tar",
                        repo_type="dataset", revision=REVISION))
        result = classify_mismatches(archive,
                    grouped[(pid, prior_record["latest_version_id"])], prior_record)
        results.append(result)
    summary = summarize(results, prior["summary"]["members_mismatching_inventory_sha256"])
    outcome = {
        "protocol": PROTOCOL, "status": "EXPLORATORY_RELEASE_TRANSFORM_DIAGNOSTIC",
        "dataset_revision": REVISION, "original_byte_receipt_sha256": ORIGINAL_RECEIPT_SHA256,
        "summary": summary, "records": results,
        "limitations": [
            "Exact archive re-verification supports reproducibility of release bytes only.",
            "File-type grouping cannot prove source-of-change or scientific correctness.",
            "Redaction is documented by the publisher but original pre-redaction bytes are not available.",
            "No independently adjudicated experimental claims or matched FAR/checker comparison.",
        ],
    }
    outcome["receipt_sha256"] = digest(outcome)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(outcome, indent=2, ensure_ascii=False, sort_keys=True)+"\n", encoding="utf-8")
    print("MISMATCH_TRIAGE_SUMMARY="+json.dumps(summary, sort_keys=True), flush=True)
    print("MISMATCH_TRIAGE_RECEIPT_SHA256="+outcome["receipt_sha256"], flush=True)
    for row in results:
        print("MISMATCH_TRIAGE_ROW="+json.dumps(row, sort_keys=True, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
