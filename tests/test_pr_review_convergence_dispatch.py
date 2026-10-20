"""Execute the actual trusted-main PR discovery Bash step against adversarial inputs."""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/pr-review-convergence.yml"


def discovery_step() -> str:
    """Read the exact workflow run-block, not a duplicate of its algorithm."""
    lines = WORKFLOW.read_text(encoding="utf-8").splitlines()
    anchor = next(i for i, line in enumerate(lines)
                  if line.strip() == "- name: Determine PR identities without running PR code")
    start = next(i + 1 for i in range(anchor, len(lines)) if lines[i].strip() == "run: |")
    script: list[str] = []
    for line in lines[start:]:
        if line.startswith("          "):
            script.append(line[10:])
        elif not line.strip():
            script.append("")
        else:
            break
    if not script or script[0] != "set -euo pipefail":
        raise AssertionError("cannot identify trusted PR discovery run-block")
    return "\n".join(script) + "\n"


class DispatchNumberTests(unittest.TestCase):
    def run_discovery(self, event: str, value: str, *, comment_author: str = "",
                      pr_number: str = "") -> tuple[subprocess.CompletedProcess[str], str]:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            mock_gh = home / "gh"
            # A deterministic paginated CLI mock. Invoked only for all-open queries.
            mock_gh.write_text("#!/bin/sh\nprintf '587\\n578\\n'\n", encoding="utf-8")
            mock_gh.chmod(0o700)
            output = home / "outputs"
            env = dict(os.environ, PATH=str(home) + os.pathsep + os.environ["PATH"],
                       GH_EVENT_NAME=event, INPUT_PR_NUMBER=value,
                       EVENT_PR_NUMBER=pr_number, EVENT_ISSUE_NUMBER=pr_number,
                       EVENT_COMMENT_AUTHOR=comment_author, GITHUB_OUTPUT=str(output),
                       GITHUB_REPOSITORY="n0tf0und0ut/Project-FAR", GH_TOKEN="synthetic")
            completed = subprocess.run(["bash", "-c", discovery_step()], env=env,
                                       text=True, capture_output=True, check=False, timeout=10)
            return completed, output.read_text(encoding="utf-8") if output.exists() else ""

    def test_integer_valued_dispatch_as_decimal(self):
        for raw in ("587", "587.0", "587.00", "1.0"):
            with self.subTest(raw=raw):
                result, output = self.run_discovery("workflow_dispatch", raw)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(output, f"numbers=[{raw.split('.')[0]}]\n")

    def test_default_zero_dispatch_publishes_for_all_open_prs(self):
        for raw in ("0", "0.0", "0.000"):
            with self.subTest(raw=raw):
                result, output = self.run_discovery("workflow_dispatch", raw)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(output, "numbers=[587,578]\n")

    def test_fractional_negative_noncanonical_and_injection_fail_closed(self):
        for raw in ("587.5", "-1", "+587", "0587", "587.1",
                    "587.0.0", "1e3", "587;echo compromised", "", ".0", "0.5"):
            with self.subTest(raw=raw):
                result, output = self.run_discovery("workflow_dispatch", raw)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(output, "")

    def test_schedule_still_discovers_all(self):
        result, output = self.run_discovery("schedule", "")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output, "numbers=[587,578]\n")

    def test_pr_review_event_still_targets_one(self):
        result, output = self.run_discovery("pull_request_review", "", pr_number="587")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output, "numbers=[587]\n")

    def test_non_codex_issue_comment_does_not_request_any_work(self):
        result, output = self.run_discovery("issue_comment", "",
                                            pr_number="587", comment_author="contributor")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output, "numbers=[]\n")

    def test_codex_issue_comment_takes_its_pr_identity(self):
        result, output = self.run_discovery("issue_comment", "", pr_number="587",
                                            comment_author="chatgpt-codex-connector[bot]")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output, "numbers=[587]\n")


if __name__ == "__main__":
    unittest.main()
