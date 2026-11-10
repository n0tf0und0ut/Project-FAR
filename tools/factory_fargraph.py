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
import re
import subprocess
import sys
from pathlib import Path

from fargraph.core import build, git_changed_files

_SHA = re.compile(r"[0-9a-f]{40}\Z")


def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                          text=True, timeout=25, check=False)
    if proc.returncode != 0:
        raise ValueError("Git verification failed: " + (proc.stderr.strip() or "git exit " + str(proc.returncode)))
    return proc.stdout.strip()


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
    ancestry = subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", base, head_sha],
                              capture_output=True, text=True, timeout=25, check=False)
    if ancestry.returncode != 0:
        raise ValueError("Work-order base is not an ancestor of the exact candidate head")
    changed = git_changed_files(root, base, head_sha)
    deleted = _git(root, "diff", "--name-only", "--diff-filter=D",
                   base + "..." + head_sha, "--").splitlines()
    graph = build(root)
    freshness = graph.freshness()
    if not freshness["fresh"]:
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
