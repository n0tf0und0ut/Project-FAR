#!/usr/bin/env python3
"""Canonical Project FAR unittest runner."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
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



def _canonical_cases(suite: unittest.TestSuite):
    """Unwrap the discovered suite without dropping module-level function cases."""
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from _canonical_cases(item)
        else:
            yield item


def _canonical_module(case) -> str:
    # unittest.TestCase classes can retain their original import-path module
    # even when discovered via a dynamically named source file.
    # FunctionTestCase is different: its wrapper class is unittest.case, but
    # the function ID is anchored to the actual dynamically loaded module.
    source = (
        case.id().rsplit(".", 1)[0]
        if isinstance(case, unittest.FunctionTestCase)
        else case.__class__.__module__
    )
    if not isinstance(source, str) or not re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*", source
    ) or source in {"unittest.case", "unittest.loader", "__main__"}:
        raise ValueError(f"cannot prove canonical test-module identity: {case.id()}")
    return source


def _suite_fingerprint(cases) -> str:
    identities = [test.id() for test in cases]
    if len(identities) != len(set(identities)):
        raise ValueError("canonical test discovery contains duplicate test IDs")
    records = [(test.id(), _canonical_module(test)) for test in cases]
    return hashlib.sha256(json.dumps(records, separators=(",", ":")).encode()).hexdigest()


def _test_shards(cases, jobs: int) -> list[list[int]]:
    """Keep each discovered test module on one worker (unittest class/module fixtures)."""
    if not 1 <= jobs <= 32:
        raise ValueError("canonical shard count must be in [1, 32]")
    by_module: dict[str, list[int]] = {}
    for index, case in enumerate(cases):
        source = _canonical_module(case)
        by_module.setdefault(source, []).append(index)
    if not by_module:
        raise ValueError("canonical test discovery is empty")
    jobs = min(jobs, len(by_module))
    allocations: list[list[int]] = [[] for _ in range(jobs)]
    loads = [0] * jobs
    for _, indices in sorted(by_module.items(), key=lambda item: (-len(item[1]), item[0])):
        slot = min(range(jobs), key=lambda index: (loads[index], index))
        allocations[slot].extend(indices)
        loads[slot] += len(indices)
    for indices in allocations:
        indices.sort()
    coverage = sorted(index for indices in allocations for index in indices)
    if coverage != list(range(len(cases))) or any(not indices for indices in allocations):
        raise ValueError("parallel canonical test partition is incomplete or duplicated")
    return allocations


def _worker_main(cases, args, digest: str) -> int:
    if (args._shard_index is None or args._shard_count is None
            or args._expected_digest is None or args._shard_count < 2
            or not 0 <= args._shard_index < args._shard_count):
        raise ValueError("invalid canonical worker identity")
    if args._expected_digest != digest:
        raise ValueError("canonical worker discovered a different test suite")
    shards = _test_shards(cases, args._shard_count)
    if len(shards) != args._shard_count:
        raise ValueError("canonical worker shard count changed")
    indices = shards[args._shard_index]
    selected = unittest.TestSuite(cases[index] for index in indices)
    started = time.monotonic()
    print(f"Project FAR test discovery: {len(indices)} tests in shard {args._shard_index + 1}/{args._shard_count}", flush=True)
    result = DiagnosticTextTestRunner(verbosity=2, buffer=False).run(selected)
    elapsed = time.monotonic() - started
    success = result.wasSuccessful() and 0 < result.testsRun <= len(indices)
    print(f"Project FAR tests run: {result.testsRun} in {elapsed:.3f}s", flush=True)
    receipt = {
        "index": args._shard_index,
        "jobs": args._shard_count,
        "suite_digest": digest,
        "selected": len(indices),
        "executed": result.testsRun,
        "skipped": len(result.skipped),
        "successful": success,
    }
    print("FAR_SHARD_RESULT " + json.dumps(receipt, sort_keys=True), flush=True)
    return 0 if success else 1


def _parallel_main(cases, jobs: int) -> int:
    digest = _suite_fingerprint(cases)
    shards = _test_shards(cases, jobs)
    jobs = len(shards)
    print(
        f"Project FAR parallel canonical discovery: {len(cases)} tests, {jobs} workers; "
        f"suite SHA-256 {digest}", flush=True,
    )
    with tempfile.TemporaryDirectory(prefix="far-parallel-tests-") as directory:
        launched = []
        try:
            for index in range(jobs):
                path = Path(directory) / f"shard-{index}.log"
                log = path.open("w+", encoding="utf-8")
                command = [
                    sys.executable, str(Path(__file__).resolve()),
                    "--_shard-index", str(index), "--_shard-count", str(jobs),
                    "--_expected-digest", digest,
                ]
                process = subprocess.Popen(
                    command, cwd=ROOT, env=dict(os.environ),
                    stdout=log, stderr=subprocess.STDOUT,
                )
                launched.append((process, log, path))
            okay = True
            executed = 0
            for index, (process, log, path) in enumerate(launched):
                returncode = process.wait()
                log.flush()
                output = path.read_text(encoding="utf-8", errors="replace")
                print(f"===== canonical shard {index + 1}/{jobs} (exit {returncode}) =====", flush=True)
                print(output, flush=True)
                receipts = [line[len("FAR_SHARD_RESULT "):] for line in output.splitlines()
                            if line.startswith("FAR_SHARD_RESULT ")]
                try:
                    if len(receipts) != 1:
                        raise ValueError("missing or duplicated canonical shard result")
                    receipt = json.loads(receipts[0])
                    if not isinstance(receipt, dict):
                        raise ValueError("canonical shard result must be an object")
                    expected = {
                        "index": index, "jobs": jobs, "suite_digest": digest,
                        "selected": len(shards[index]), "successful": True,
                    }
                    if any(receipt.get(key) != value for key, value in expected.items()):
                        raise ValueError("canonical shard result disagrees with parent discovery")
                    count = receipt.get("executed")
                    if (type(count) is not int or not 0 < count <= len(shards[index])
                            or returncode != 0):
                        raise ValueError("canonical shard did not complete successfully")
                    executed += count
                except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
                    okay = False
                    print(f"FAR canonical shard {index + 1} failure: {exc}", file=sys.stderr)
            print(f"Project FAR tests run: {executed} across {jobs} workers", flush=True)
            return 0 if okay and executed > 0 else 1
        finally:
            for process, log, _ in launched:
                if process.poll() is None:
                    process.kill()
                    process.wait()
                log.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run all intended Project FAR tests.")
    parser.add_argument(
        "--fast",
        action="store_true",
        help="reserved for future slow-test exclusion; currently runs the full test suite",
    )
    parser.add_argument("--jobs", type=int, default=1, help="parallel module workers (1 retains original serial semantics)")
    parser.add_argument("--_shard-index", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--_shard-count", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--_expected-digest", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    suite = discover_suite()
    total = count_tests(suite)
    if args.jobs < 1 or args.jobs > 32:
        parser.error("--jobs must be in [1, 32]")
    if args._shard_index is not None:
        try:
            cases = list(_canonical_cases(suite))
            return _worker_main(cases, args, _suite_fingerprint(cases))
        except ValueError as exc:
            print(f"FAR canonical worker invalid: {exc}", file=sys.stderr)
            return 2
    if args._shard_count is not None or args._expected_digest is not None:
        parser.error("incomplete internal shard arguments")
    if args.jobs > 1:
        try:
            cases = list(_canonical_cases(suite))
            return _parallel_main(cases, args.jobs)
        except ValueError as exc:
            print(f"FAR canonical sharding invalid: {exc}", file=sys.stderr)
            return 2
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
