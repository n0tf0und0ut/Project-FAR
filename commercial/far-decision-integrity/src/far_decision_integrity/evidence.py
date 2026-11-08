from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .strict_json import loads_strict

EVIDENCE_MANIFEST_VERSION = "far-evidence-manifest/0.1"


def canonical_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_evidence_bundle(
    output_directory: str | Path,
    *,
    report_name: str,
    report_payload: Mapping[str, Any],
    source_files: Mapping[str, str | Path],
) -> tuple[Path, Path]:
    root = Path(output_directory)
    root.mkdir(parents=True, exist_ok=True)

    report_path = root / report_name
    report_bytes = canonical_json_bytes(report_payload)
    report_path.write_bytes(report_bytes)

    sources: list[dict[str, str]] = []
    for logical_name, source in sorted(source_files.items()):
        source_path = Path(source)
        try:
            data = source_path.read_bytes()
        except OSError as exc:
            raise ValueError(f"unable to read evidence source {source_path}: {exc}") from exc
        sources.append(
            {
                "name": logical_name,
                "path": str(source_path),
                "sha256": sha256_bytes(data),
            }
        )

    manifest = {
        "schema_version": EVIDENCE_MANIFEST_VERSION,
        "report": {
            "path": report_name,
            "sha256": sha256_bytes(report_bytes),
        },
        "sources": sources,
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_bytes(canonical_json_bytes(manifest))
    return report_path, manifest_path


def _safe_report_path(root: Path, raw_path: Any) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path or Path(raw_path).is_absolute():
        return None
    root_resolved = root.resolve()
    candidate = (root / raw_path).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        return None
    return candidate


def verify_evidence_bundle(output_directory: str | Path) -> bool:
    root = Path(output_directory)
    try:
        manifest = loads_strict((root / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(manifest, dict) or manifest.get("schema_version") != EVIDENCE_MANIFEST_VERSION:
        return False
    report = manifest.get("report")
    sources = manifest.get("sources")
    if not isinstance(report, dict) or not isinstance(sources, list):
        return False
    report_path = _safe_report_path(root, report.get("path"))
    expected_report_hash = report.get("sha256")
    if report_path is None or not isinstance(expected_report_hash, str):
        return False
    try:
        if sha256_bytes(report_path.read_bytes()) != expected_report_hash:
            return False
    except OSError:
        return False

    seen_names: set[str] = set()
    for source in sources:
        if not isinstance(source, dict):
            return False
        name = source.get("name")
        raw_path = source.get("path")
        expected_hash = source.get("sha256")
        if (
            not isinstance(name, str)
            or not name
            or name in seen_names
            or not isinstance(raw_path, str)
            or not raw_path
            or not isinstance(expected_hash, str)
            or len(expected_hash) != 64
        ):
            return False
        seen_names.add(name)
        source_path = Path(raw_path)
        try:
            if sha256_bytes(source_path.read_bytes()) != expected_hash:
                return False
        except OSError:
            return False
    return True
