"""Real Git worktree before/after observations and adversarial runner controls.

These tests use isolated synthetic repositories, not FAR's enrolled pilot tasks.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools import factory_before_after as runner


class BeforeAfterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.repo = root / "source"
        self.repo.mkdir()
        self.out = root / "receipt"
        self.git("init", "-q")
        self.git("config", "user.name", "Research Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        (self.repo / "tests").mkdir()
        (self.repo / "demo.py").write_text("def execute():\n    return False\n")
        self.test_file = self.repo / "tests/test_demo.py"
        self.test_file.write_text(
            "import unittest\nfrom demo import execute\n\n"
            "class TestDemo(unittest.TestCase):\n"
            "    def test_enabled(self):\n"
            "        self.assertTrue(execute())\n",
        )
        self.oracle = runner.sha256_file(self.test_file)
        self.before = self.commit("failing baseline")
        (self.repo / "demo.py").write_text("def execute():\n    return True\n")
        self.after = self.commit("working candidate")

    def git(self, *args):
        proc = subprocess.run(["git", *args], cwd=self.repo, text=True,
                              capture_output=True, check=True)
        return proc.stdout.strip()

    def commit(self, message):
        self.git("add", "--all")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD")

    def measure(self, before=None, after=None, oracle=None, out=None, timeout=20):
        return runner.evaluate(
            self.repo, before or self.before, after or self.after,
            "test_demo.py", "tests/test_demo.py", oracle or self.oracle,
            out or self.out, timeout,
        )

    def test_actual_before_failure_after_pass_with_unchanged_oracle(self):
        result = self.measure()
        self.assertEqual(result["verdict"], "OBSERVED_EXIT_STATUS_IMPROVEMENT")
        self.assertEqual(result["before"]["status"], "FAIL")
        self.assertEqual(result["after"]["status"], "PASS")
        self.assertEqual(result["before"]["test_count_reported"], 1)
        self.assertEqual(result["after"]["test_count_reported"], 1)
        saved = json.loads((self.out / "receipt.json").read_text())
        self.assertEqual(saved["before"]["stderr"]["sha256"],
                         runner.sha256_file(self.out / "before.stderr"))
        self.assertEqual(saved["after"]["stdout"]["sha256"],
                         runner.sha256_file(self.out / "after.stdout"))
        self.assertEqual(self.git("worktree", "list", "--porcelain").count("worktree "), 1)

    def test_reversed_order_rejects_nonancestor_source(self):
        with self.assertRaisesRegex(runner.RunnerError, "ancestor"):
            self.measure(self.after, self.before)
        self.assertFalse(self.out.exists())

    def test_same_commit_is_not_evidence_of_change(self):
        with self.assertRaisesRegex(runner.RunnerError, "identical"):
            self.measure(self.before, self.before)

    def test_malformed_sha_and_shell_like_test_pattern_rejected(self):
        with self.assertRaisesRegex(runner.RunnerError, "exact lowercase"):
            self.measure(before="main")
        with self.assertRaisesRegex(runner.RunnerError, "test pattern"):
            runner.evaluate(self.repo, self.before, self.after, "*.py; touch /tmp/a",
                            "tests/test_demo.py", self.oracle, self.out)
        self.assertFalse(self.out.exists())

    def test_missing_oracle_hash_rejected(self):
        with self.assertRaisesRegex(runner.RunnerError, "expected oracle"):
            self.measure(oracle="0" * 63)

    def test_oracle_in_changed_candidate_is_incomparable_not_green(self):
        self.test_file.write_text(self.test_file.read_text() + "# modified\n")
        changed = self.commit("oracle changed after candidate")
        result = self.measure(after=changed)
        self.assertEqual(result["verdict"], "INCOMPARABLE")
        self.assertIsNone(result["before"])
        self.assertIsNone(result["after"])
        self.assertEqual(result["observed_oracle_sha256"]["before"], self.oracle)
        self.assertNotEqual(result["observed_oracle_sha256"]["after"], self.oracle)

    def test_wrong_independently_registered_oracle_digest_is_incomparable(self):
        result = self.measure(oracle="a" * 64)
        self.assertEqual(result["verdict"], "INCOMPARABLE")
        self.assertFalse((self.out / "before.stdout").exists())

    def test_runnable_no_tests_is_unknown_not_success(self):
        self.test_file.write_text("# no tests, identical contents for both commits\n")
        older = self.commit("empty oracle baseline")
        (self.repo / "demo.py").write_text("def execute():\n    return 'changed'\n")
        newer = self.commit("empty oracle candidate")
        oracle = runner.sha256_file(self.test_file)
        result = self.measure(older, newer, oracle)
        self.assertEqual(result["verdict"], "UNKNOWN")
        self.assertEqual(result["before"]["test_count_reported"], 0)
        self.assertEqual(result["after"]["test_count_reported"], 0)

    def test_timeout_does_not_count_as_regression_or_success(self):
        self.test_file.write_text(
            "import unittest\nfrom demo import execute\n"
            "class TestDemo(unittest.TestCase):\n"
            "    def test_slow(self):\n"
            "        self.assertTrue(execute())\n",
        )
        (self.repo / "demo.py").write_text("def execute():\n    return True\n")
        before = self.commit("fast run")
        (self.repo / "demo.py").write_text(
            "def execute():\n    import time\n    time.sleep(5)\n    return True\n",
        )
        after = self.commit("slow run")
        o = runner.sha256_file(self.test_file)
        result = self.measure(before, after, o, timeout=1)
        self.assertEqual(result["before"]["status"], "PASS")
        self.assertEqual(result["after"]["status"], "TIMEOUT")
        self.assertEqual(result["verdict"], "UNKNOWN")

    def test_source_modification_during_test_invalidates_receipt(self):
        self.test_file.write_text(
            "import unittest\nfrom pathlib import Path\n"
            "class TestMutate(unittest.TestCase):\n"
            "    def test_mutation(self):\n"
            "        Path('demo.py').write_text('modified by test')\n"
            "        self.assertTrue(True)\n",
        )
        before = self.commit("mutating oracle")
        (self.repo / "demo.py").write_text("def execute():\n    return 'other'\n")
        after = self.commit("changed target")
        result = self.measure(before, after, runner.sha256_file(self.test_file))
        self.assertEqual(result["before"]["status"], "UNKNOWN")
        self.assertTrue(result["before"]["tracked_checkout_modified"])
        self.assertEqual(result["verdict"], "UNKNOWN")

    def test_output_cannot_overwrite_or_mix_with_source(self):
        with self.assertRaisesRegex(runner.RunnerError, "outside"):
            self.measure(out=self.repo / "artifacts")
        self.out.mkdir()
        with self.assertRaisesRegex(runner.RunnerError, "never overwritten"):
            self.measure()

    def test_reject_oracle_path_traversal_and_mismatch(self):
        for path in ("tests/../test_demo.py", "/tmp/test_demo.py", "tests/not_demo.py",
                     "tests\\test_demo.py"):
            with self.subTest(path=path), self.assertRaisesRegex(runner.RunnerError, "oracle path"):
                runner.evaluate(self.repo, self.before, self.after, "test_demo.py",
                                path, self.oracle, self.out)

    def test_actual_regression_is_observed_not_renamed_improvement(self):
        (self.repo / "demo.py").write_text("def execute():\n    return False\n")
        bad = self.commit("introduce regression")
        outcome = self.measure(self.after, bad)
        self.assertEqual(outcome["before"]["status"], "PASS")
        self.assertEqual(outcome["after"]["status"], "FAIL")
        self.assertEqual(outcome["verdict"], "OBSERVED_REGRESSION")


if __name__ == "__main__":
    unittest.main()
