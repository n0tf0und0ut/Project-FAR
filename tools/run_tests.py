#!/usr/bin/env python3
"""Canonical Project FAR unittest runner."""
from __future__ import annotations

import argparse
import importlib.util
import inspect
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST_ROOTS = (
    ROOT / "tests",
    ROOT / "commercial" / "far-decision-integrity" / "tests",
)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# Tests create and commit to temporary git repositories. The runner's global and system git
# configuration (for example commit signing or a signing helper) must not change their behavior.
os.environ["GIT_CONFIG_GLOBAL"] = os.devnull
os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
# git commit and merge start `git maintenance run --auto`, which detaches by default and takes
# .git/objects/maintenance.lock even when no task is due. A test's temporary repository could then be
# written while it is being removed ("Directory not empty").
_git_config = int(os.environ.get("GIT_CONFIG_COUNT") or 0)
if ("maintenance.auto", "false") not in {
    (os.environ.get(f"GIT_CONFIG_KEY_{i}"), os.environ.get(f"GIT_CONFIG_VALUE_{i}")) for i in range(_git_config)
}:
    os.environ[f"GIT_CONFIG_KEY_{_git_config}"] = "maintenance.auto"
    os.environ[f"GIT_CONFIG_VALUE_{_git_config}"] = "false"
    os.environ["GIT_CONFIG_COUNT"] = str(_git_config + 1)


class DiagnosticTextTestResult(unittest.TextTestResult):
    """Collect and print complete, test-addressable failure diagnostics."""

    def addFailure(self, test: unittest.case.TestCase, err) -> None:
        super().addFailure(test, err)
        self._print_structured_problem("FAILURE", test, err)

    def addError(self, test: unittest.case.TestCase, err) -> None:
        super().addError(test, err)
        self._print_structured_problem("ERROR", test, err)

    def _print_structured_problem(self, kind: str, test: unittest.case.TestCase, err) -> None:
        test_id = test.id()
        traceback_text = self._exc_info_to_string(err, test).rstrip()
        self.stream.writeln()
        self.stream.writeln(f"PROJECT_FAR_TEST_{kind}")
        self.stream.writeln(f"test: {test_id}")
        self.stream.writeln(f"location: {test_id.rsplit('.', 2)[0]}")
        self.stream.writeln("details:")
        for line in traceback_text.splitlines():
            self.stream.writeln(f"  {line}")
        self.stream.writeln(f"END_PROJECT_FAR_TEST_{kind}")


class DiagnosticTextTestRunner(unittest.TextTestRunner):
    resultclass = DiagnosticTextTestResult


def _function_case(function) -> unittest.FunctionTestCase:
    """Run a module-level pytest-style ``test_*`` function under unittest.

    Only the ``tmp_path`` fixture is supported; any other parameter fails the test instead of
    silently skipping it, so a module-level test can never be discovered and not executed.
    """
    parameters = list(inspect.signature(function).parameters)
    deferred = (inspect.iscoroutinefunction(function) or inspect.isgeneratorfunction(function)
                or inspect.isasyncgenfunction(function))

    def run() -> None:
        if deferred:
            # Calling one returns a coroutine or generator without running the body, so it would pass.
            raise TypeError(f"{function.__qualname__}: async and generator test functions are not supported")
        unsupported = [name for name in parameters if name != "tmp_path"]
        if unsupported:
            raise TypeError(f"{function.__qualname__}: unsupported test fixture(s) {unsupported}")
        if parameters:
            with tempfile.TemporaryDirectory() as tmp:
                function(tmp_path=Path(tmp))
        else:
            function()

    # FunctionTestCase.id() is the wrapped callable's name; without this every failure reads "run".
    run.__name__ = run.__qualname__ = f"{function.__module__}.{function.__name__}"
    return unittest.FunctionTestCase(run, description=f"{function.__module__}.{function.__name__}")


def _module_functions(module) -> list[unittest.FunctionTestCase]:
    return [
        _function_case(value)
        for name, value in sorted(vars(module).items())
        if name.startswith("test")
        and inspect.isfunction(value)
        and value.__module__ == module.__name__
    ]


def discover_suite(starts: Path | tuple[Path, ...] = TEST_ROOTS) -> unittest.TestSuite:
    """Discover every test surface that is part of the canonical merge-validation contract.

    A single ``Path`` remains supported for focused callers and the zero-discovery regression;
    the canonical default spans every root in ``TEST_ROOTS``.
    """
    if isinstance(starts, Path):
        starts = (starts,)
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    module_index = 0
    for start in starts:
        if not start.is_dir():
            raise FileNotFoundError(f"canonical test root is missing: {start.relative_to(ROOT)}")
        for path in sorted(start.rglob("test_*.py")):
            module_name = "project_far_test_" + str(module_index) + "_" + path.stem
            module_index += 1
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                raise ImportError(f"cannot import test module {path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            suite.addTests(loader.loadTestsFromModule(module))
            suite.addTests(_module_functions(module))
    return suite


def count_tests(suite: unittest.TestSuite) -> int:
    return suite.countTestCases()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run all intended Project FAR tests.")
    parser.add_argument(
        "--fast",
        action="store_true",
        help="reserved for future slow-test exclusion; currently runs the full test suite",
    )
    parser.parse_args(argv)
    suite = discover_suite()
    total = count_tests(suite)
    print(f"Project FAR test discovery: {total} tests")
    if total == 0:
        print("PROJECT FAR TESTS FAILED: zero tests discovered", file=sys.stderr)
        return 1
    start = time.monotonic()
    result = DiagnosticTextTestRunner(verbosity=2, buffer=False).run(suite)
    elapsed = time.monotonic() - start
    print(f"Project FAR tests run: {result.testsRun} in {elapsed:.3f}s")
    if result.testsRun == 0:
        print("PROJECT FAR TESTS FAILED: zero tests executed", file=sys.stderr)
        return 1
    if not result.wasSuccessful():
        print("PROJECT FAR TEST FAILURE SUMMARY", file=sys.stderr)
        print(f"failures: {len(result.failures)}", file=sys.stderr)
        print(f"errors: {len(result.errors)}", file=sys.stderr)
        print(f"skipped: {len(result.skipped)}", file=sys.stderr)
        for kind, entries in (("FAILURE", result.failures), ("ERROR", result.errors)):
            for test, traceback_text in entries:
                print(f"{kind}: {test.id()}", file=sys.stderr)
                print(traceback_text.rstrip(), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
