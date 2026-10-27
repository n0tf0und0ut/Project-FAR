"""Minimal local PEP 517/660 backend for the Phase 3 mechanization MVP."""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import os
import zipfile
from pathlib import Path

NAME = "project_far_mechanization"
VERSION = "0.6.0"
DIST_INFO = f"{NAME}-{VERSION}.dist-info"


def get_requires_for_build_wheel(config_settings=None):
    return []


def get_requires_for_build_editable(config_settings=None):
    return []


def _metadata() -> str:
    return "\n".join([
        "Metadata-Version: 2.1",
        "Name: project-far-mechanization",
        f"Version: {VERSION}",
        "Summary: Project FAR Phase 3 mechanization MVP",
        "Requires-Python: >=3.11",
        "Requires-Dist: PyYAML>=6.0,<7",
        "",
    ])


def _wheel() -> str:
    return "\n".join([
        "Wheel-Version: 1.0",
        "Generator: project-far-local-backend",
        "Root-Is-Purelib: true",
        "Tag: py3-none-any",
        "",
    ])


def _entry_points() -> str:
    return (
        "[console_scripts]\n"
        "far = mechanization.far_mechanization.cli:main\n"
        "far-evidence = mechanization.far_mechanization.compare_adjudication:main\n"
        "far-intake = mechanization.far_mechanization.intake_v1:main\n"
    )


def _hash(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    return "sha256=" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _write_wheel(path: Path, files: dict[str, bytes]) -> None:
    records: list[tuple[str, str, str]] = []
    record_name = f"{DIST_INFO}/RECORD"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in sorted(files.items()):
            zf.writestr(name, data)
            records.append((name, _hash(data), str(len(data))))
        records.append((record_name, "", ""))
        out = io.StringIO()
        writer = csv.writer(out, lineterminator="\n")
        writer.writerows(records)
        zf.writestr(record_name, out.getvalue().encode("utf-8"))


def _runtime_files(root: Path) -> dict[str, bytes]:
    """Collect the pure-Python runtime and schemas needed by a relocated wheel."""
    files: dict[str, bytes] = {}
    for directory in (root / "mechanization" / "far_mechanization", root / "jsonschema", root / "far_validation"):
        for path in sorted(directory.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            files[path.relative_to(root).as_posix()] = path.read_bytes()
    for path in sorted((root / "schemas").rglob("*.json")):
        files[path.relative_to(root).as_posix()] = path.read_bytes()
    return files


def _dist_info_files() -> dict[str, bytes]:
    return {
        f"{DIST_INFO}/METADATA": _metadata().encode("utf-8"),
        f"{DIST_INFO}/WHEEL": _wheel().encode("utf-8"),
        f"{DIST_INFO}/entry_points.txt": _entry_points().encode("utf-8"),
    }


def prepare_metadata_for_build_wheel(metadata_directory, config_settings=None):
    dist = Path(metadata_directory) / DIST_INFO
    dist.mkdir(parents=True, exist_ok=True)
    (dist / "METADATA").write_text(_metadata(), encoding="utf-8")
    (dist / "WHEEL").write_text(_wheel(), encoding="utf-8")
    (dist / "entry_points.txt").write_text(_entry_points(), encoding="utf-8")
    return DIST_INFO


def prepare_metadata_for_build_editable(metadata_directory, config_settings=None):
    return prepare_metadata_for_build_wheel(metadata_directory, config_settings)


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    root = Path(__file__).resolve().parent
    wheel_name = f"{NAME}-{VERSION}-py3-none-any.whl"
    files = {
        f"{NAME}.pth": (str(root) + os.linesep).encode("utf-8"),
        **_dist_info_files(),
    }
    _write_wheel(Path(wheel_directory) / wheel_name, files)
    return wheel_name


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    root = Path(__file__).resolve().parent
    wheel_name = f"{NAME}-{VERSION}-py3-none-any.whl"
    files = _runtime_files(root)
    files.update(_dist_info_files())
    _write_wheel(Path(wheel_directory) / wheel_name, files)
    return wheel_name
