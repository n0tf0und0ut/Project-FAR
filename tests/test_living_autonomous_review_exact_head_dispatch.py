from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AutonomousReviewExactHeadDispatchTests(unittest.TestCase):
    def test_exact_head_supports_explicit_trusted_dispatch(self):
        workflow = (ROOT / ".github/workflows/exact-head-assurance.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("head_sha:", workflow)
        self.assertIn("base_sha:", workflow)
        self.assertIn("FAR_ASSURANCE_DISPATCH_HEAD", workflow)
        self.assertIn("FAR_ASSURANCE_DISPATCH_BASE", workflow)
        self.assertIn("FAR_ASSURANCE_DISPATCH_WORKFLOW_SHA", workflow)
        self.assertIn("invalid dispatched exact-head SHA", workflow)
        self.assertIn("dispatched exact-head checkout mismatch", workflow)
        self.assertIn("dispatched exact-head base differs from trusted main workflow ref", workflow)
        self.assertIn("dispatched exact-head review head is not a direct child of frozen main", workflow)
        self.assertIn("git merge-base --is-ancestor", workflow)
        self.assertIn("Publish dispatched assurance on reviewed head", workflow)
        self.assertIn("/check-runs", workflow)
        self.assertIn("--arg head_sha \"$FAR_ASSURANCE_DISPATCH_HEAD\"", workflow)
        self.assertIn("--arg name exact-head-assurance", workflow)

        # Untrusted review code executes only in the read-only validation job. The
        # checks:write capability is isolated in a publisher job that never checks
        # out or executes repository-controlled code.
        permissions = workflow.index("permissions:\n  contents: read")
        jobs = workflow.index("jobs:")
        validation_job = workflow.index("  exact-head-assurance:", jobs)
        publisher_job = workflow.index("  publish-dispatched-assurance:", validation_job)
        publisher = workflow[publisher_job:]
        validation = workflow[validation_job:publisher_job]
        self.assertLess(permissions, jobs)
        self.assertNotIn("checks: write", validation)
        self.assertIn("permissions:\n      checks: write", publisher)
        self.assertIn("needs: exact-head-assurance", publisher)
        self.assertIn("if: always() && github.event_name == 'workflow_dispatch'", publisher)
        self.assertNotIn("actions/checkout", publisher)
        self.assertNotIn("actions/setup-python", publisher)
        self.assertNotIn("Install dependencies", publisher)

        preflight = validation.index("- name: Validate dispatched identity before checkout")
        checkout = validation.index("- uses: actions/checkout@")
        lineage = validation.index("- name: Verify dispatched checkout lineage before repository code runs")
        setup = validation.index("- uses: actions/setup-python@")
        install = validation.index("- name: Install dependencies and trace backend")
        upload = validation.index("- name: Upload assurance evidence")
        publish = publisher.index("- name: Publish dispatched assurance on reviewed head")
        self.assertLess(preflight, checkout)
        self.assertLess(checkout, lineage)
        self.assertLess(lineage, setup)
        self.assertLess(setup, install)
        self.assertGreater(upload, install)
        self.assertGreaterEqual(publish, 0)

    def test_autonomous_review_dispatches_trusted_main_and_publishes_on_head(self):
        workflow = (ROOT / ".github/workflows/living-autonomous-review-v2.yml").read_text(encoding="utf-8")
        self.assertIn("python -m tools.run_living_autonomous_review --help", workflow)
        self.assertIn("python -m tools.run_living_autonomous_review", workflow)
        self.assertNotIn("python tools/run_living_autonomous_review.py", workflow)
        expected = (
            'gh workflow run exact-head-assurance.yml --repo "$GITHUB_REPOSITORY" --ref main '
            '\\\n            -f head_sha="$head_sha" -f base_sha="$base_sha"'
        )
        self.assertIn(expected, workflow)

        assurance = (ROOT / ".github/workflows/exact-head-assurance.yml").read_text(encoding="utf-8")
        self.assertIn("Publish dispatched assurance on reviewed head", assurance)
        self.assertIn("head_sha:$head_sha", assurance)
        self.assertIn("name:$name", assurance)
        self.assertIn("status:\"completed\"", assurance)


if __name__ == "__main__":
    unittest.main()
