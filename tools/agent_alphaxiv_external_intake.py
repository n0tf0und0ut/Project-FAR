"""Reproducible metadata intake for the AgentAlphaXiv external-corpus *candidate* pilot.

Does not perform evidence adjudication or certify a research claim. Does not run
code from the dataset. The source revision and expected paper-cohort counts are
pinned. Any mismatch fails closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Iterable

DATASET = "alphaXiv/AgentAlphaXiv"
REVISION = "a63f46066ac16fcb470f41933415e175825b6bcc"
EXPECTED_STUDIES = 961
EXPECTED_COHORT = 926
SAMPLE_SIZE = 60
SELECTION_LABEL = "FAR-AGENT-ALPHAXIV-001/candidate-v0.1"

# Distinct, nonconfirmatory candidate source registrations. The unavailable
# 001 source and expected counts remain immutable; 002 never substitutes for it.
SOURCES = {
    "001": (REVISION, EXPECTED_STUDIES, EXPECTED_COHORT, SELECTION_LABEL),
    "002": (
        "cc892aab131be3872283e1a778af663382315817",
        916,
        881,
        "FAR-AGENT-ALPHAXIV-002/candidate-v0.1",
    ),
}


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _hash(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def selection_key(project_id: str, *, label: str = SELECTION_LABEL) -> str:
    return hashlib.sha256((label + "\n" + project_id).encode("utf-8")).hexdigest()


def build_manifest(rows: Iterable[dict], *, strict: bool = True, sample_size: int = SAMPLE_SIZE, candidate: str = "001") -> dict:
    try:
        source_revision, source_studies, source_cohort, source_label = SOURCES[candidate]
    except KeyError as exc:
        raise ValueError("unregistered candidate ID") from exc
    if sample_size < 1:
        raise ValueError("sample_size must be positive")
    studies: list[dict] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"row {index} must be an object")
        for field in ("project_id", "lab", "title", "latest_version_id", "slug"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"row {index} missing nonempty {field}")
        if type(row.get("in_paper_cohort")) is not bool:
            raise ValueError(f"row {index} needs boolean in_paper_cohort")
        project_id = row["project_id"]
        if project_id in seen:
            raise ValueError(f"duplicate project_id: {project_id}")
        seen.add(project_id)
        studies.append({k: row[k] for k in ("project_id", "lab", "title", "latest_version_id", "slug", "in_paper_cohort")})
    cohort = [r for r in studies if r["in_paper_cohort"]]
    if strict and (len(studies), len(cohort)) != (source_studies, source_cohort):
        raise ValueError(f"source count mismatch: got {len(studies)} studies, {len(cohort)} in cohort; expected {source_studies}, {source_cohort}")
    if len(cohort) < sample_size:
        raise ValueError(f"insufficient eligible cohort metadata: {len(cohort)} < {sample_size}")

    # One deterministic minimum-hash paper per lab first, then global minimum-hash fill.
    # Selection does not depend on titles, abstracts, review outcomes, or defect labels.
    ordered = sorted(cohort, key=lambda r: (selection_key(r["project_id"], label=source_label), r["project_id"]))
    first_per_lab: dict[str, dict] = {}
    for r in ordered:
        first_per_lab.setdefault(r["lab"], r)
    if len(first_per_lab) > sample_size:
        raise ValueError("sample_size smaller than number of represented labs")
    selected_ids = {r["project_id"] for r in first_per_lab.values()}
    for row in ordered:
        if len(selected_ids) == sample_size:
            break
        selected_ids.add(row["project_id"])
    selected = [
        {"project_id": r["project_id"], "lab": r["lab"], "title": r["title"],
         "slug": r["slug"], "latest_version_id": r["latest_version_id"],
         "selection_digest": selection_key(r["project_id"], label=source_label),
         "screening_status": "UNSCREENED"}
        for r in ordered if r["project_id"] in selected_ids
    ]
    data = {
        "protocol": source_label,
        "status": "RESEARCH_CANDIDATE_NOT_LAUNCHED",
        "dataset": DATASET,
        "dataset_revision": source_revision,
        "all_studies": len(studies),
        "paper_cohort": len(cohort),
        "represented_labs": len({r["lab"] for r in cohort}),
        "sample_size": sample_size,
        "input_row_metadata_sha256": _hash(sorted(studies, key=lambda r: r["project_id"])),
        "selection_rule": "min SHA256(label + LF + project_id) per lab; then global min SHA256 fill",
        "selected": selected,
        "verified_empirical_claims": 0,
    }
    data["manifest_sha256"] = _hash(data)
    return data


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def load_hub(*, candidate: str = "001") -> list[dict]:
    try:
        from datasets import load_dataset  # type: ignore
    except ImportError as exc:
        raise RuntimeError("from-hub requires 'pip install datasets'; no fallback revision is permitted") from exc
    if candidate not in SOURCES:
        raise ValueError("unregistered candidate ID")
    return list(load_dataset(DATASET, "studies", split="train", revision=SOURCES[candidate][0]))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--from-hub", action="store_true", help="fetch pinned Hugging Face studies config")
    source.add_argument("--input-jsonl", type=Path, help="previously exported studies JSONL")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--candidate", choices=tuple(SOURCES), default="001",
                        help="explicit source candidate ID; default retains original 001 registration")
    args = parser.parse_args()
    rows = load_hub(candidate=args.candidate) if args.from_hub else load_jsonl(args.input_jsonl)
    manifest = build_manifest(rows, candidate=args.candidate)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(f"UNSCREENED candidate sample: {len(manifest['selected'])}; manifest_sha256={manifest['manifest_sha256']}")


if __name__ == "__main__":
    main()
