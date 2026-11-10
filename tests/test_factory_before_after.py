"""Real Git worktree before/after observations and adversarial runner controls.

These tests use isolated synthetic repositories, not FAR's enrolled pilot tasks.
"""
from __future__ import annotations

import hashlib
import importlib.machinery
import json
import os
import py_compile
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


    def test_nested_oracle_cannot_be_substituted_by_same_basename(self):
        nested = self.repo / "tests/frozen"
        nested.mkdir()
        (nested / "test_demo.py").write_text(
            "import unittest\nclass NeverPass(unittest.TestCase):\n"
            "    def test_fail(self):\n        self.fail('registered oracle should fail')\n"
        )
        sha = runner.sha256_file(nested / "test_demo.py")
        with self.assertRaisesRegex(runner.RunnerError, "oracle path"):
            runner.evaluate(self.repo, self.before, self.after, "test_demo.py",
                            "tests/frozen/test_demo.py", sha, self.out)
        self.assertFalse(self.out.exists())

    def test_ambiguous_same_basename_oracle_is_rejected(self):
        (self.repo / "tests/frozen").mkdir()
        (self.repo / "tests/frozen/test_demo.py").write_text(
            "import unittest\nclass Other(unittest.TestCase):\n"
            "    def test_other(self):\n        self.assertTrue(True)\n"
        )
        before = self.commit("two same-name test files")
        (self.repo / "demo.py").write_text("def execute():\n    return 'different'\n")
        after = self.commit("change source with duplicate test basename")
        with self.assertRaisesRegex(runner.RunnerError, "ambiguous"):
            self.measure(before, after, self.oracle)

    def test_unchecked_hash_pyc_cannot_substitute_frozen_oracle(self):
        # This reproduces the Codex review's executable-oracle substitution:
        # same registered test source bytes, but a checked-in unchecked-hash
        # compiled cache contains a different (passing) test body.
        (self.repo / "demo.py").write_text("def execute():\n    return False\n")
        older = self.commit("baseline still fails")
        source = self.test_file.read_text()
        self.test_file.write_text(
            "import unittest\nclass Forged(unittest.TestCase):\n"
            "    def test_always_pass(self):\n        self.assertTrue(True)\n"
        )
        cache = self.repo / "tests/__pycache__"
        cache.mkdir(exist_ok=True)
        pyc = cache / ("test_demo." + sys.implementation.cache_tag + ".pyc")
        py_compile.compile(str(self.test_file), cfile=str(pyc), doraise=True,
                           invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
        self.test_file.write_text(source)
        self.assertEqual(runner.sha256_file(self.test_file), self.oracle)
        newer = self.commit("candidate adds unregistered checked-in bytecode")
        with self.assertRaisesRegex(runner.RunnerError, "precompiled test bytecode"):
            self.measure(older, newer, self.oracle)
        self.assertTrue((self.out / "receipt.json").is_file())
        receipt = json.loads((self.out / "receipt.json").read_text())
        self.assertEqual(receipt["verdict"], "UNKNOWN")
        self.assertIsNone(receipt["after"])


    def test_native_extension_cannot_shadow_registered_test_source(self):
        # Native extensions take precedence over matching .py source imports.
        # A candidate must not supply a different test module body under the
        # same import name while claiming the frozen oracle's source digest.
        (self.repo / "demo.py").write_text("def execute():\n    return False\n")
        baseline = self.commit("unchanged failing source before extension")
        extension = self.repo / "tests" / (
            "test_demo" + importlib.machinery.EXTENSION_SUFFIXES[-1]
        )
        extension.write_bytes(b"candidate-controlled extension placeholder")
        candidate = self.commit("extension shadows source test module")
        self.assertEqual(runner.sha256_file(self.test_file), self.oracle)
        with self.assertRaisesRegex(runner.RunnerError, "native extension"):
            self.measure(baseline, candidate, self.oracle)
        receipt = json.loads((self.out / "receipt.json").read_text())
        self.assertIsNone(receipt["before"])
        self.assertIsNone(receipt["after"])
        self.assertEqual(receipt["verdict"], "UNKNOWN")

    def test_nested_native_oracle_alias_rejected_before_execution(self):
        (self.repo / "demo.py").write_text("def execute():\n    return False\n")
        baseline = self.commit("same frozen baseline")
        hidden = self.repo / "tests/hidden"
        hidden.mkdir()
        (hidden / ("test_demo" + importlib.machinery.EXTENSION_SUFFIXES[-1])).write_bytes(
            b"unregistered native test module"
        )
        candidate = self.commit("nested competing importable oracle")
        with self.assertRaisesRegex(runner.RunnerError, "native extension"):
            self.measure(baseline, candidate, self.oracle)

    def test_interpreter_uses_private_bytecode_cache(self):
        record = self.measure()
        self.assertIn("-X", record["before"]["command"])
        args = record["before"]["command"]
        self.assertTrue(any(value.startswith("pycache_prefix=") for value in args))
        self.assertEqual(list(self.out.glob("far-pycache-*")), [])

    @unittest.skipUnless(os.name == "posix", "requires POSIX symlink support")
    def test_symlinked_parent_cannot_redirect_receipts_into_source(self):
        alias = Path(self.tmp.name) / "alias"
        alias.symlink_to(self.repo, target_is_directory=True)
        with self.assertRaisesRegex(runner.RunnerError, "outside"):
            self.measure(out=alias / "artifacts")
        self.assertFalse((self.repo / "artifacts").exists())

    @unittest.skipUnless(os.name == "posix", "requires POSIX inherited pipes")
    def test_background_descendant_cannot_change_sealed_log_hash(self):
        self.test_file.write_text(
            "import subprocess\nimport sys\nimport unittest\n"
            "class TestBackground(unittest.TestCase):\n"
            "    def test_background(self):\n"
            "        subprocess.Popen([sys.executable, '-c', "
            "'import time; time.sleep(0.35); print(1234567)'])\n"
            "        self.assertTrue(True)\n"
        )
        older = self.commit("spawn late stdout writer")
        (self.repo / "demo.py").write_text("def execute():\n    return 'different'\n")
        newer = self.commit("source change with unchanged background oracle")
        result = self.measure(older, newer, runner.sha256_file(self.test_file), timeout=4)
        self.assertEqual(result["verdict"], "OBSERVED_NO_REGRESSION")
        for stage in ("before", "after"):
            path = self.out / (stage + ".stdout")
            self.assertIn(b"1234567", path.read_bytes())
            self.assertEqual(result[stage]["stdout"]["sha256"], runner.sha256_file(path))
        import time
        time.sleep(0.5)
        for stage in ("before", "after"):
            path = self.out / (stage + ".stdout")
            self.assertEqual(result[stage]["stdout"]["sha256"], runner.sha256_file(path))

    @unittest.skipUnless(os.name == "posix", "requires POSIX pipes")
    def test_unbounded_test_output_is_never_counted_as_success(self):
        self.test_file.write_text(
            "import unittest\nclass Flood(unittest.TestCase):\n"
            "    def test_flood(self):\n"
            "        print('x' * (8 * 1024 * 1024 + 4096))\n"
        )
        before = self.commit("large output oracle")
        (self.repo / "demo.py").write_text("def execute():\n    return 'different'\n")
        after = self.commit("changed source")
        result = self.measure(before, after, runner.sha256_file(self.test_file), timeout=10)
        self.assertEqual(result["verdict"], "UNKNOWN")
        self.assertTrue(result["before"]["stream_limit_exceeded"])
        self.assertLessEqual(result["before"]["stdout"]["size"], runner.MAX_STREAM_BYTES)


    def test_same_oracle_with_dropped_cases_is_incomparable(self):
        self.test_file.write_text(
            "import unittest\nfrom selector import load_tests\n"
            "class TestDemo(unittest.TestCase):\n"
            "    def test_fail(self):\n        self.fail('real failure')\n"
            "    def test_pass(self):\n        self.assertTrue(True)\n",
        )
        selector = self.repo / "selector.py"
        selector.write_text("def load_tests(loader, tests, pattern):\n    return tests\n")
        before = self.commit("two selected tests, one failing")
        selector.write_text(
            "def load_tests(loader, tests, pattern):\n"
            "    return loader.loadTestsFromName('test_demo.TestDemo.test_pass')\n",
        )
        after = self.commit("candidate suppresses failing case without changing oracle bytes")
        result = self.measure(before, after, runner.sha256_file(self.test_file))
        self.assertEqual(result["before"]["test_count_reported"], 2)
        self.assertEqual(result["after"]["test_count_reported"], 1)
        self.assertEqual(result["before"]["status"], "FAIL")
        self.assertEqual(result["after"]["status"], "PASS")
        self.assertEqual(result["verdict"], "INCOMPARABLE")

    def test_same_count_with_swapped_test_identity_is_incomparable(self):
        self.test_file.write_text(
            "import unittest\nfrom selector import load_tests\n"
            "class TestDemo(unittest.TestCase):\n"
            "    def test_fail(self):\n        self.fail('real failure')\n"
            "    def test_pass(self):\n        self.assertTrue(True)\n",
        )
        selector = self.repo / "selector.py"
        selector.write_text(
            "def load_tests(loader, tests, pattern):\n"
            "    return loader.loadTestsFromName('test_demo.TestDemo.test_fail')\n",
        )
        before = self.commit("one selected failing test")
        selector.write_text(
            "def load_tests(loader, tests, pattern):\n"
            "    return loader.loadTestsFromName('test_demo.TestDemo.test_pass')\n",
        )
        after = self.commit("one selected passing test with different identity")
        result = self.measure(before, after, runner.sha256_file(self.test_file))
        self.assertEqual(result["before"]["test_count_reported"], 1)
        self.assertEqual(result["after"]["test_count_reported"], 1)
        self.assertEqual(result["before"]["status"], "FAIL")
        self.assertEqual(result["after"]["status"], "PASS")
        self.assertEqual(result["verdict"], "INCOMPARABLE")


    def test_multiline_verbose_unittest_description_is_a_single_case(self):
        self.test_file.write_text(
            "import unittest\nfrom demo import execute\n"
            "class TestDemo(unittest.TestCase):\n"
            "    def test_enabled(self):\n"
            "        '''A narrated check with a multiline verbose description.'''\n"
            "        self.assertTrue(execute())\n",
        )
        (self.repo / "demo.py").write_text("def execute():\n    return False\n")
        baseline = self.commit("failing test with verbose description")
        (self.repo / "demo.py").write_text("def execute():\n    return True\n")
        candidate = self.commit("fixed behavior with identical narrated oracle")
        result = self.measure(baseline, candidate, runner.sha256_file(self.test_file))
        self.assertEqual(result["before"]["test_count_reported"], 1)
        self.assertEqual(result["after"]["test_count_reported"], 1)
        self.assertTrue(result["before"]["test_inventory_complete"])
        self.assertTrue(result["after"]["test_inventory_complete"])
        self.assertTrue(result["test_inventory_comparable"])
        self.assertEqual(result["verdict"], "OBSERVED_EXIT_STATUS_IMPROVEMENT")


if __name__ == "__main__":
    unittest.main()
