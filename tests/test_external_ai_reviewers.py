"""Regression checks for advisory reviewers and protected token boundaries."""
from pathlib import Path
import copy
import re
import subprocess
import sys
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/advisory-open-code-review.yml"
CODERABBIT = ROOT / ".coderabbit.yaml"


def _events(document):
    return document.get("on", document.get(True, {}))


def _is_advisory_coderabbit(document):
    reviews = document.get("reviews", {})
    return (
        reviews.get("auto_review", {}).get("enabled") is True
        and reviews.get("auto_review", {}).get("drafts") is False
        and reviews.get("auto_approvals", {}).get("enabled") is False
        and reviews.get("finishing_touches", {}).get("autofix", {}).get("enabled") is False
    )


class ExternalAIReviewerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        cls.coderabbit = yaml.safe_load(CODERABBIT.read_text(encoding="utf-8"))

    def test_coderabbit_has_advisory_only_contract(self):
        self.assertTrue(_is_advisory_coderabbit(self.coderabbit))
        paths = {
            entry["path"] for entry in self.coderabbit["reviews"]["path_instructions"]
        }
        self.assertTrue({
            ".github/workflows/**", "tools/**", "tests/**", "docs/governance/**"
        }.issubset(paths))

    def test_coderabbit_approval_or_autofix_regression_is_caught(self):
        for path in [
            ("auto_approvals", "enabled"),
            ("finishing_touches", "autofix", "enabled"),
        ]:
            broken = copy.deepcopy(self.coderabbit)
            node = broken["reviews"]
            for key in path[:-1]:
                node = node[key]
            node[path[-1]] = True
            self.assertFalse(_is_advisory_coderabbit(broken), path)

    def test_review_job_is_not_reachable_from_candidate_event(self):
        events = _events(self.workflow)
        self.assertIn("pull_request", events)
        self.assertIn("workflow_run", events)
        self.assertIn("workflow_dispatch", events)
        review = self.workflow["jobs"]["review"]
        self.assertEqual(
            review["if"],
            "github.event_name == 'workflow_run' || github.event_name == 'workflow_dispatch'",
        )
        self.assertEqual(review["permissions"], {
            "contents": "read", "pull-requests": "write",
        })
        self.assertEqual(self.workflow["permissions"], {"contents": "read"})
        for step in review["steps"]:
            self.assertFalse(
                str(step.get("uses", "")).startswith("actions/checkout@"),
                "privileged review must not execute a checkout of candidate code",
            )

    def test_exact_head_and_eligibility_are_rechecked_before_credentials(self):
        review = self.workflow["jobs"]["review"]["steps"]
        bind = review[0]
        self.assertIn("gh api", bind["run"])
        for required in (
            ".base.ref", ".head.repo.full_name", ".head.sha", ".draft",
            ".state", "origin", "target", "head",
            "GITHUB_OUTPUT",
        ):
            self.assertIn(required, bind["run"])
        self.assertNotIn("secrets.", yaml.safe_dump(bind))
        self.assertIn("steps.context.outputs.enabled == 'true'", review[1]["if"])
        self.assertIn("steps.provider.outputs.configured == 'true'", review[2]["if"])

    def test_vendor_action_and_cli_are_immutably_pinned(self):
        run_step = self.workflow["jobs"]["review"]["steps"][-1]
        self.assertRegex(
            run_step["uses"],
            r"^alibaba/open-code-review@[0-9a-f]{40}$",
        )
        self.assertEqual(run_step["with"]["ocr_version"], "1.13.7")
        self.assertEqual(run_step["with"]["resolve_outdated"], "false")
        self.assertEqual(run_step["with"]["upload_artifacts"], "true")
        self.assertEqual(run_step["with"]["head_sha"],
                         "\u0024{{ steps.context.outputs.head_sha }}")
        self.assertIn("workflow_run", _events(self.workflow))

    def test_hygiene_recognizes_real_coderabbit_globs(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools/check_repository_hygiene.py")],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Repository hygiene OK", result.stdout)

    def test_required_convergence_workflow_not_replaced(self):
        required = yaml.safe_load(
            (ROOT / ".github/workflows/required-pr-review-convergence.yml")
            .read_text(encoding="utf-8")
        )
        self.assertIn("required-review", required["jobs"])
        job = required["jobs"]["required-review"]
        self.assertEqual(job["name"], "pr-review-convergence-observation")
        self.assertEqual(job["permissions"]["contents"], "read")
        self.assertNotIn("if", job)


if __name__ == "__main__":
    unittest.main()
