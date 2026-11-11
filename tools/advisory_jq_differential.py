#!/usr/bin/env python3
"""Execute the actual advisory OCR fallback jq filter against adversarial fixtures.

Read-only contract check for the PR-event job. This is not reviewer
execution or protected merge assurance. It deliberately runs system jq here,
rather than inside the separately governed traced canonical validation suite.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/advisory-open-code-review.yml"
REPO = "n0tf0und0ut/Project-FAR"
SHA = "b" * 40


def main() -> int:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    resolver = workflow["jobs"]["review"]["steps"][0]["run"]
    candidates = re.findall(
        r"'(\[\.\[\]\[\] \| select\([^\n']+\) \| \.number\] \| unique)'",
        resolver,
    )
    if len(candidates) != 1:
        raise ValueError("cannot uniquely locate actual jq fallback selector")
    selector = candidates[0]
    fixture = [{
        "number": 7,
        "head": {
            "ref": "feature",
            "repo": {"full_name": REPO},
            "sha": SHA,
        },
    }]
    cases = [
        ("current head", REPO, SHA, [7]),
        ("stale source SHA", REPO, "a" * 40, []),
        ("fork origin", "attacker/Project-FAR", SHA, []),
        ("different branch", REPO, SHA, []),
    ]
    for label, repo, source_sha, expected in cases:
        branch = "other" if label == "different branch" else "feature"
        result = subprocess.run(
            ["jq", "--arg", "branch", branch, "--arg", "repo", repo,
             "--arg", "source_sha", source_sha, selector],
            input=json.dumps([fixture]), capture_output=True,
            text=True, check=False, timeout=15,
        )
        if result.returncode:
            raise RuntimeError(f"jq selector failed for {label}: {result.stderr[:300]}")
        observed = json.loads(result.stdout)
        if observed != expected:
            raise AssertionError(
                f"{label}: source selector returned {observed!r}, expected {expected!r}"
            )
    print("Advisory OCR deployed jq selector differential: PASS (4 cases)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError, RuntimeError, AssertionError,
            subprocess.SubprocessError) as exc:
        print(f"Advisory OCR jq selector differential: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
