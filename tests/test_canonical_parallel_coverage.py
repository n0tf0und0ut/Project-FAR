"""Fail-closed canonical parallel suite partition and worker accounting."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tools" / "run_tests.py"
SPEC = importlib.util.spec_from_file_location("far_parallel_test_runner", RUNNER)
assert SPEC is not None and SPEC.loader is not None
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _case(module: str, identity: str):
    cls = type("Case", (unittest.TestCase,), {
        "__module__": module, "runTest": lambda self: None,
        "id": lambda self: identity,
    })
    return cls()


class CanonicalParallelCoverageTests(unittest.TestCase):
    def _cases(self):
        return [
            _case(f"project_far_test_{i}_test_module", f"project_far_test_{i}_test_module.Case.test_{j}")
            for i in range(5) for j in range(i + 1)
        ]

    def test_each_test_runs_exactly_once_and_module_fixtures_stay_together(self) -> None:
        cases = self._cases()
        for jobs in (1, 2, 3, 4, 8):
            with self.subTest(jobs=jobs):
                shards = runner._test_shards(cases, jobs)
                flattened = [index for shard in shards for index in shard]
                self.assertEqual(sorted(flattened), list(range(len(cases))))
                self.assertTrue(all(shard for shard in shards))
                for i in range(5):
                    members = [j for j, c in enumerate(cases) if c.id().startswith(f"project_far_test_{i}_")]
                    self.assertEqual(1, sum(all(j in shard for j in members) for shard in shards))

    def test_discovery_fingerprint_changes_on_reorder_and_duplicate_fails(self) -> None:
        cases = self._cases()
        self.assertNotEqual(
            runner._suite_fingerprint(cases),
            runner._suite_fingerprint(list(reversed(cases))),
        )
        with self.assertRaisesRegex(ValueError, "duplicate"):
            runner._suite_fingerprint([cases[0], cases[0]])

    def test_unattributable_module_and_invalid_worker_count_fail_closed(self) -> None:
        for invalid in ("unknown bad module", "__main__"):
            with self.subTest(test=invalid):
                with self.assertRaisesRegex(ValueError, "identity"):
                    runner._test_shards([_case(invalid, "bad.case")], 2)
        for jobs in (0, -1, 33):
            with self.assertRaisesRegex(ValueError, "count"):
                runner._test_shards(self._cases(), jobs)

    def test_original_import_module_names_and_function_cases_are_supported(self) -> None:
        original = _case("tests.test_far_investigation_benchmark",
                         "tests.test_far_investigation_benchmark.FrozenSemanticTests.test_one")
        wrapped = lambda: None
        wrapped.__name__ = "project_far_test_1_test_example.test_function"
        function_case = unittest.FunctionTestCase(wrapped)
        self.assertEqual(runner._canonical_module(original), "tests.test_far_investigation_benchmark")
        self.assertEqual(runner._canonical_module(function_case), "project_far_test_1_test_example")
        self.assertEqual(len(runner._test_shards([original, function_case], 2)), 2)

    def test_serial_is_unmodified_default_and_parallel_is_opt_in(self) -> None:
        import json
        manifest = json.loads((ROOT / "validation" / "manifest.json").read_text())
        check = next(item for item in manifest["checks"] if item["id"] == "tests.canonical")
        self.assertEqual(check["command"], ["python", "tools/run_tests.py", "--fast", "--jobs", "4"])
        self.assertEqual(runner.main.__defaults__, (None,))


if __name__ == "__main__":
    unittest.main()
