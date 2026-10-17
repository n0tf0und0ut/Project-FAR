#!/usr/bin/env python3
"""Validate unprotected living-research carry data before checkout.

Only ordinary, non-executable Git blobs are admitted. Symlinks, executable blobs,
submodules, and other object modes fail closed before bytes reach the working tree.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def _entries(repo: Path, ref: str, path: str) -> list[tuple[str, str, str]]:
    proc = subprocess.run(
        ["git", "-C", str(repo), "ls-tree", "-rz", ref, "--", path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise ValueError(proc.stderr.decode("utf-8", "replace").strip() or f"cannot inspect carried path: {path}")
    rows: list[tuple[str, str, str]] = []
    for record in proc.stdout.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_name = record.split(b"\t", 1)
            mode, object_type, _object_sha = metadata.decode("ascii").split(" ", 2)
            name = raw_name.decode("utf-8", "strict")
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError(f"malformed git tree entry for carried path: {path}") from exc
        rows.append((mode, object_type, name))
    return rows


def validate_ref_paths(repo: Path, ref: str, paths: list[str]) -> None:
    for path in paths:
        rows = _entries(repo, ref, path)
        if not rows:
            raise ValueError(f"carried path has no regular git objects: {path}")
        for mode, object_type, name in rows:
            if mode != "100644" or object_type != "blob":
                raise ValueError(
                    "forbidden carried git object: "
                    f"path={name} mode={mode} type={object_type}; only 100644 blobs are allowed"
                )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--ref", required=True)
    parser.add_argument("--path", action="append", dest="paths", required=True)
    args = parser.parse_args()
    validate_ref_paths(args.repo.resolve(), args.ref, args.paths)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
