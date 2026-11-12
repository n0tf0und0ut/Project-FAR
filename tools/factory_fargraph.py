#!/usr/bin/env python3
"""Read-only, exact-source FARGraph advice for the Research software factory.

This adapter reads a validated factory work order, pins a local Git checkout to an
exact head and base, and prints structural impact evidence. It never writes to the
factory queue, produces a review decision, executes code from the repository, or
certifies a merge. It requires the existing tools.software_factory parser.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from fargraph.core import MAX_SOURCE_BYTES, build, git_changed_files

_SHA = re.compile(r"[0-9a-f]{40}\Z")


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", "--no-replace-objects", "-C", str(root), *args], capture_output=True,
                          text=True, timeout=25, check=False)
    if proc.returncode != 0:
        raise ValueError("Git verification failed: " + (proc.stderr.strip() or "git exit " + str(proc.returncode)))
    return proc.stdout.strip()


def _git_bytes(root: Path, *args: str, input_bytes: bytes | None = None) -> bytes:
    proc = subprocess.run(
        ["git", "--no-replace-objects", "-C", str(root), *args],
        input=input_bytes, capture_output=True, timeout=25, check=False,
    )
    if proc.returncode != 0:
        raise ValueError("Git object verification failed: " + os.fsdecode(proc.stderr).strip())
    return proc.stdout


def _source_tree(root: Path, head: str) -> dict[str, tuple[bytes, int]]:
    files = {}
    for entry in _git_bytes(root, "ls-tree", "-rlz", "--full-tree", head).split(b"\0"):
        if not entry:
            continue
        metadata, path_bytes = entry.split(b"\t", 1)
        mode, kind, oid, raw_size = metadata.split()
        if mode in {b"100644", b"100755"} and kind == b"blob":
            files[os.fsdecode(path_bytes)] = (oid, int(raw_size))
    return files


def _verify_source_hashes(root: Path, files: dict[str, tuple[bytes, int]], hashes: dict[str, str]) -> None:
    # Git's clean status accounts for checkout transformations. Compare the
    # actual bytes indexed by the graph with the committed blobs instead.
    paths_by_oid: dict[bytes, list[str]] = {}
    sizes: dict[bytes, int] = {}
    for path in hashes:
        if path not in files:
            raise ValueError(f"Indexed path is not a committed regular Git blob: {path}")
        oid, size = files[path]
        if size > MAX_SOURCE_BYTES:
            raise ValueError(f"Committed Git blob exceeds the indexing limit: {path}")
        paths_by_oid.setdefault(oid, []).append(path)
        sizes[oid] = size

    oids = list(paths_by_oid)
    # Bound each subprocess's captured payload using the validated blob sizes.
    for start in range(0, len(oids), 32):
        batch = oids[start:start + 32]
        data = _git_bytes(root, "cat-file", "--batch", input_bytes=b"\n".join(batch) + b"\n")
        offset = 0
        for oid in batch:
            size = sizes[oid]
            header = oid + b" blob " + str(size).encode("ascii") + b"\n"
            begin = offset + len(header)
            end = begin + size
            if data[offset:begin] != header or data[end:end + 1] != b"\n":
                raise ValueError("Unexpected Git blob response")
            digest = hashlib.sha256(data[begin:end]).hexdigest()
            for path in paths_by_oid[oid]:
                if digest != hashes[path]:
                    raise ValueError(f"Indexed source differs from committed Git blob: {path}")
            offset = end + 1
        if offset != len(data):
            raise ValueError("Unexpected trailing Git blob data")


def _read_work_order(path: Path) -> tuple[dict, str]:
    # Import the authoritative factory input parser; do not duplicate its schema.
    from tools.software_factory import parse_order_text
    content = path.read_bytes()
    if len(content) > 2_000_000:
        raise ValueError("Work order exceeds 2 MB")
    data = parse_order_text(content.decode("utf-8"))
    return data, hashlib.sha256(content).hexdigest()


def evaluate(root: Path, work_order: Path, head_sha: str, repository: str,
             max_depth: int = 8) -> dict:
    root = root.resolve(strict=True)
    if not root.is_dir() or max_depth not in range(1, 33):
        raise ValueError("Invalid repository root or depth")
    if not _SHA.fullmatch(head_sha):
        raise ValueError("Candidate head must be a full lowercase 40-character Git SHA")
    order, order_source_hash = _read_work_order(work_order)
    if order["repository"].casefold() != repository.casefold():
        raise ValueError("Work-order repository identity does not match requested repository")
    live_head = _git(root, "rev-parse", "HEAD")
    if live_head != head_sha:
        raise ValueError("Checkout HEAD differs from requested exact candidate head")
    # Dirty or newly added local files would make the graph differ from the pinned commit.
    if _git(root, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Checkout is dirty: structural evidence cannot be bound to exact HEAD")
    base = order["base_sha"]
    if _git(root, "rev-parse", "--verify", base + "^{commit}") != base:
        raise ValueError("Work-order base is not an exact commit identity")
    ancestry = subprocess.run(["git", "--no-replace-objects", "-C", str(root), "merge-base", "--is-ancestor", base, head_sha],
                              capture_output=True, text=True, timeout=25, check=False)
    if ancestry.returncode != 0:
        raise ValueError("Work-order base is not an ancestor of the exact candidate head")
    changed = git_changed_files(root, base, head_sha)
    deleted = git_changed_files(root, base, head_sha, diff_filter="D")
    # Only indexed Git-tracked bytes can be attributed to exact HEAD.
    # Ignored local files are not evidence from the committed candidate.
    source_tree = _source_tree(root, head_sha)
    graph = build(root, tracked_only=True, source_paths=frozenset(source_tree))
    _verify_source_hashes(root, source_tree, graph.hashes)
    freshness = graph.freshness()
    if not freshness["fresh"] or _git(root, "rev-parse", "HEAD") != head_sha:
        raise ValueError("Repository changed while indexing; graph is not exact-source")
    impact = graph.impact(sorted(set(changed + deleted)), max_depth=max_depth)
    # This snapshot is advisory even when every known edge resolves; unknown relations remain.
    return {
        "schema": "fargraph-factory-advisory/0.1",
        "status": "ADVISORY_ONLY_NO_MERGE_AUTHORITY",
        "repository": order["repository"],
        "work_order_id": order["id"],
        "work_order_sha256": order_source_hash,
        "base_sha": base,
        "head_sha": head_sha,
        "graph_stats": graph.stats(),
        "indexed_source_hashes": dict(sorted(graph.hashes.items())),
        "index_freshness": freshness,
        "deleted_paths_with_unknown_prior_edges": deleted,
        "impact": impact,
        "diagnostics": sorted(graph.diagnostics, key=lambda d:(d["path"],d["line"],d["kind"],d["detail"])),
        "limitations": [
            "Syntactic and local-file dependency evidence only; missing edges never prove safety.",
            "Deleted paths and unsupported language behavior may not appear in the index.",
            "No authenticated worker, review, tests, gate verdict, or protected merge authorization.",
            "No factory state mutation or work-order submission is performed.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True)
    p.add_argument("--work-order", required=True)
    p.add_argument("--head-sha", required=True)
    p.add_argument("--repository", required=True)
    p.add_argument("--depth", type=int, default=8)
    args = p.parse_args(argv)
    try:
        data = evaluate(Path(args.root), Path(args.work_order), args.head_sha,
                        args.repository, max_depth=args.depth)
        print(json.dumps(data, sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError, UnicodeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "ERROR_NO_EVIDENCE", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
