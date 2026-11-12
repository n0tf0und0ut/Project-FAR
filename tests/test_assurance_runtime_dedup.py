"""Regression contract: full assurance runs the canonical suite once per lane.

The full health check's public standalone default remains complete. Only the
manifest-owned invocation may skip the suite, and it must depend on a successful
canonical-test result in the same signed validation run.
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AssuranceRuntimeDedupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads((ROOT / "validation" / "manifest.json").read_text(encoding="utf-8"))
        cls.checks = {check["id"]: check for check in cls.manifest["checks"]}

    def test_full_health_skips_only_its_duplicate_canonical_suite(self) -> None:
        check = self.checks["repository.health-full"]
        self.assertEqual(
            check["command"],
            ["python", "tools/repo_health_check.py", "--full", "--skip-canonical-tests"],
        )
        self.assertIn("tests.canonical", check.get("depends_on", []))
        self.assertEqual(
            self.checks["tests.canonical"]["command"],
            ["python", "tools/run_tests.py", "--fast", "--jobs", "4"],
        )
        self.assertIs(check.get("cacheable"), False)
        self.assertEqual(check["timeout_seconds"], 1800)

    def test_every_full_health_profile_retains_canonical_tests(self) -> None:
        for profile, selected in self.manifest["profiles"].items():
            if "repository.health-full" not in selected:
                continue
            with self.subTest(profile=profile):
                self.assertIn("tests.canonical", selected)
        self.assertIn("repository.health-full", self.manifest["profiles"]["pr-full"])
        self.assertIn("tests.canonical", self.manifest["profiles"]["pr-full"])

    def test_standalone_health_still_runs_tests_by_default(self) -> None:
        text = (ROOT / "tools" / "repo_health_check.py").read_text(encoding="utf-8")
        self.assertIn("if not args.skip_canonical_tests: add('canonical tests'", text)
        self.assertIn("parser.add_argument('--skip-canonical-tests',action='store_true'", text)


if __name__ == "__main__":
    unittest.main()
