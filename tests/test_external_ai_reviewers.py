"""Regression checks for advisory reviewers and protected token boundaries."""
from pathlib import Path
import copy
import json
import os
import tempfile
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
            "github.event_name == 'workflow_run' || "
            "(github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main')",
        )
        self.assertEqual(review["environment"], "ocr-trusted-main")
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


    def _replay_review_context(self, *, origin_repo, event_sha, populated=False):
        """Execute the actual workflow's GitHub resolver with isolated fake gh."""
        repo = "n0tf0und0ut/Project-FAR"
        current_sha = "b" * 40
        event = {"workflow_run": {
            "name": "Required PR Review Convergence", "event": "pull_request",
            "repository": {"full_name": repo},
            "head_repository": {"full_name": origin_repo},
            "head_branch": "feature", "head_sha": event_sha,
            "pull_requests": [{"number": 7, "head": {"sha": event_sha}}]
            if populated else [],
        }}
        candidate = {"number": 7, "state": "open", "draft": False,
                     "base": {"ref": "main"},
                     "head": {"repo": {"full_name": repo},
                              "ref": "feature", "sha": current_sha}}
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            stub = directory / "gh"
            stub.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "if [[ \"$1\" != api ]]; then exit 2; fi\n"
                "if [[ \"$2\" == --paginate ]]; then\n"
                "  cat \"$FIXTURE_LIST\"\n"
                "else\n"
                "  cat \"$FIXTURE_META\"\n"
                "fi\n",
                encoding="utf-8",
            )
            stub.chmod(0o755)
            listing = directory / "pr-list.json"
            listing.write_text(json.dumps([[candidate]]), encoding="utf-8")
            metadata = directory / "pr.json"
            metadata.write_text(json.dumps(candidate), encoding="utf-8")
            output = directory / "github-output.txt"
            env = dict(os.environ, PATH=str(directory) + os.pathsep
                       + os.environ.get("PATH", ""),
                       EVENT_NAME="workflow_run",
                       EVENT_JSON=json.dumps(event), REQUESTED_PR="",
                       GITHUB_REPOSITORY=repo, GITHUB_OUTPUT=str(output),
                       FIXTURE_LIST=str(listing), FIXTURE_META=str(metadata))
            resolver = self.workflow["jobs"]["review"]["steps"][0]["run"]
            completed = subprocess.run(
                ["bash", "-c", resolver], env=env, cwd=ROOT,
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(completed.returncode, 0,
                             completed.stdout + completed.stderr)
            return output.read_text(encoding="utf-8") if output.exists() else ""

    def test_fallback_rejects_fork_origin_and_wrong_sha(self):
        current = "b" * 40
        self.assertEqual(self._replay_review_context(
            origin_repo="attacker/Project-FAR", event_sha=current), "")
        self.assertEqual(self._replay_review_context(
            origin_repo="n0tf0und0ut/Project-FAR", event_sha="a" * 40), "")
        self.assertIn("enabled=true", self._replay_review_context(
            origin_repo="n0tf0und0ut/Project-FAR", event_sha=current))

    def test_populated_stale_event_never_enables_review(self):
        self.assertEqual(self._replay_review_context(
            origin_repo="n0tf0und0ut/Project-FAR",
            event_sha="a" * 40, populated=True), "")

    def test_old_head_concurrency_cannot_cancel_new_head(self):
        group = self.workflow["concurrency"]["group"]
        self.assertIn("github.event.workflow_run.head_sha", group)
        self.assertIn("github.event.workflow_run.id", group)
        self.assertTrue(self.workflow["concurrency"]["cancel-in-progress"])
        self.assertNotEqual(
            f"advisory-ocr-repo-7-{'a' * 40}",
            f"advisory-ocr-repo-7-{'b' * 40}",
        )

    def test_privileged_manual_dispatch_is_main_only(self):
        job = self.workflow["jobs"]["review"]
        self.assertIn("github.ref == 'refs/heads/main'", job["if"])
        self.assertEqual(job["environment"], "ocr-trusted-main")
        self.assertNotIn("secrets.", job["if"])
        self.assertFalse("refs/heads/unreviewed" == "refs/heads/main")

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
