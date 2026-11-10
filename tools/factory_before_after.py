#!/usr/bin/env python3
"""Bounded Research before/after unittest runner for exact Git commits.

Runs identical pre-registered test-oracle bytes on two isolated Git worktrees.
This executes repository code. Git worktrees and environment filtering are NOT
security sandboxes; use a dedicated ephemeral, unprivileged, credential-free
trusted runner. It is not a factory-vs-control experiment or verifier of
scientific superiority or protected GitHub delivery.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import selectors
import signal
import tempfile
import subprocess
import sys
import tempfile
import time

SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
PATTERN = re.compile(r"^test_[A-Za-z0-9_]+\.py$")
RESULTS = {"OBSERVED_EXIT_STATUS_IMPROVEMENT", "NO_OBSERVED_IMPROVEMENT",
           "OBSERVED_NO_REGRESSION", "OBSERVED_REGRESSION", "INCOMPARABLE", "UNKNOWN"}
MAX_TIMEOUT = 600
MAX_STREAM_BYTES = 8 * 1024 * 1024
# Conservative reconstruction of actual unittest method IDs from verbose output.
# Unrecognized/dynamic output fails closed; the test process is not authenticated.
OBSERVED_TEST_ID = re.compile(rb"(?m)^(test_[A-Za-z0-9_]+ \([A-Za-z_][A-Za-z0-9_.]*\)) \.\.\. ")


class RunnerError(ValueError):
    """Preflight or local execution failure; never claimed as a passing test."""


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def sha256_file(path: Path) -> str:
    dig = hashlib.sha256()
    with path.open("rb") as reader:
        while chunk := reader.read(65536):
            dig.update(chunk)
    return dig.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    try:
        p = subprocess.run(["git", *args], cwd=repo, stdin=subprocess.DEVNULL,
                           capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RunnerError("Git inspection/checkout unavailable") from exc
    if check and p.returncode:
        raise RunnerError("Git operation failed: " + " ".join(args[:2]))
    return p


def _validate_input(repo: Path, before: str, after: str, pattern: str,
                    oracle_path: str, oracle_sha256: str, timeout: int) -> None:
    if any(type(x) is not str or not SHA40.fullmatch(x) for x in (before, after)):
        raise RunnerError("both source SHAs must be exact lowercase 40-character commits")
    if before == after:
        raise RunnerError("identical source SHAs do not constitute before/after comparison")
    if type(pattern) is not str or not PATTERN.fullmatch(pattern):
        raise RunnerError("test pattern must be a single unittest test_*.py filename")
    if type(oracle_path) is not str:
        raise RunnerError("oracle path must be a repository-relative source path")
    pure = PurePosixPath(oracle_path)
    if (not pure.parts or pure.is_absolute() or any(part in (".", "..") for part in pure.parts)
            or "\\" in oracle_path or str(pure) != oracle_path
            or tuple(pure.parts) != ("tests", pattern)):
        raise RunnerError("oracle path must match tests/<same test pattern> without traversal")
    if type(oracle_sha256) is not str or not SHA256.fullmatch(oracle_sha256):
        raise RunnerError("trusted expected oracle SHA-256 is required")
    if type(timeout) is not int or not 1 <= timeout <= MAX_TIMEOUT:
        raise RunnerError("timeout must be an integer between 1 and 600 seconds")
    if not repo.is_dir() or _git(repo, "rev-parse", "--show-toplevel").stdout.strip().decode() != str(repo):
        raise RunnerError("repository must be its exact Git working-tree root")
    for commit in (before, after):
        if _git(repo, "cat-file", "-t", commit).stdout.strip() != b"commit":
            raise RunnerError("source identifier does not name an exact commit")
    if _git(repo, "merge-base", "--is-ancestor", before, after, check=False).returncode != 0:
        raise RunnerError("baseline must be an ancestor of candidate")


def _oracle_digest(worktree: Path, path: str) -> str:
    current = worktree
    for part in PurePosixPath(path).parts:
        current = current / part
        if current.is_symlink():
            raise RunnerError("oracle path includes a symbolic link")
    if not current.is_file() or not current.resolve().is_relative_to(worktree.resolve()):
        raise RunnerError("exact oracle source is absent from one commit")
    if current.stat().st_size > 1024 * 1024:
        raise RunnerError("oracle test source is too large")
    # Discovery selects by basename, so conservatively reject any second file
    # with that name (including nested packages not discovered by unittest).
    matches = list((worktree / "tests").rglob(current.name))
    if len(matches) != 1 or matches[0] != current:
        raise RunnerError("ambiguous discovered test oracle basename")
    # An unchecked-hash .pyc in either checkout can override otherwise
    # identical registered .py bytes even when bytecode writes are disabled.
    # Fail closed instead of allowing the candidate to supply executable test
    # code whose bytes were never compared to the frozen oracle digest.
    if any((worktree / "tests").rglob("*.pyc")):
        raise RunnerError("precompiled test bytecode is forbidden")
    return sha256_file(current)


def _terminate_group(child: subprocess.Popen) -> None:
    """Do not leave same-process-group descendants able to write test pipes."""
    try:
        if os.name == "posix":
            os.killpg(child.pid, signal.SIGKILL)
        elif child.poll() is None:
            child.kill()
    except ProcessLookupError:
        pass


def _run_test(worktree: Path, label: str, pattern: str, timeout: int,
              out: Path, repo: Path) -> dict:
    # The streamed descriptor collector currently requires POSIX anonymous
    # pipes and process groups; unsupported hosts must fail rather than attest
    # that their subprocess trees have been sealed.
    if os.name != "posix":
        raise RunnerError("source-exact test collector requires POSIX process groups")
    stdout = out / (label + ".stdout")
    stderr = out / (label + ".stderr")
    # A private empty alternate cache prevents even imported modules from
    # consulting source-tree __pycache__ entries while discovery runs.
    # Clean-up occurs after child process-group finalization.
    cache = tempfile.TemporaryDirectory(prefix="far-pycache-", dir=out)
    command = [sys.executable, "-X", "pycache_prefix=" + cache.name,
               "-m", "unittest", "discover", "-s", "tests",
               "-p", pattern, "-v"]
    env = {"PATH": os.defpath, "HOME": str(worktree), "TMPDIR": str(worktree),
           "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PYTHONHASHSEED": "0",
           "PYTHONDONTWRITEBYTECODE": "1"}
    started = utc()
    start = time.monotonic()
    deadline = start + timeout
    timed_out = False
    overflow = False
    count = {"stdout": 0, "stderr": 0}
    code = None
    with stdout.open("wb") as so, stderr.open("wb") as se:
        try:
            child = subprocess.Popen(command, cwd=worktree, env=env, stdin=subprocess.DEVNULL,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     start_new_session=True, close_fds=True)
        except OSError as exc:
            raise RunnerError("test interpreter could not start") from exc
        # Only the trusted collector owns the output files; tested code sees
        # anonymous pipes. EOF from BOTH pipes is required before hashes are
        # finalized, including output inherited by background descendants.
        selector = selectors.DefaultSelector()
        try:
            for label_stream, stream in (("stdout", child.stdout), ("stderr", child.stderr)):
                assert stream is not None
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, (label_stream, so if label_stream == "stdout" else se))
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    timed_out = True
                    break
                for key, _ in selector.select(timeout=min(remaining, 0.2)):
                    stream_name, writer = key.data
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                        continue
                    free = MAX_STREAM_BYTES - count[stream_name]
                    if len(chunk) > free:
                        if free:
                            writer.write(chunk[:free])
                        count[stream_name] += max(0, free)
                        overflow = True
                        break
                    writer.write(chunk)
                    count[stream_name] += len(chunk)
                if overflow:
                    break
            if not timed_out and not overflow:
                try:
                    code = child.wait(timeout=max(0.001, deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    timed_out = True
        finally:
            _terminate_group(child)
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired as exc:
                raise RunnerError("test leader could not be terminated") from exc
            for stream in (child.stdout, child.stderr):
                if stream is not None:
                    stream.close()
            selector.close()
            cache.cleanup()
        if code is None:
            code = child.returncode
    seconds = round(time.monotonic() - start, 6)
    finished = utc()
    raw_stderr = stderr.read_bytes()
    counts = re.findall(rb"\bRan ([0-9]+) tests? in ", raw_stderr)
    test_count = int(counts[-1]) if counts else 0
    observed_ids = [match.decode("ascii") for match in OBSERVED_TEST_ID.findall(raw_stderr)]
    inventory_complete = (test_count > 0 and len(observed_ids) == test_count
                          and len(set(observed_ids)) == test_count)
    status = "TIMEOUT" if timed_out else "UNKNOWN"
    if not timed_out and not overflow and inventory_complete:
        status = "PASS" if code == 0 else "FAIL"
    dirty = bool(_git(worktree, "status", "--porcelain", "--untracked-files=no").stdout.strip())
    if dirty:
        status = "UNKNOWN"  # tested source changed after receipt's initial identity
    return {
        "status": status, "exit_code": code, "test_count_reported": test_count,
        "observed_test_ids": sorted(observed_ids),
        "test_inventory_complete": inventory_complete,
        "started_at": started, "finished_at": finished, "wall_seconds": seconds,
        "tracked_checkout_modified": dirty, "command": command,
        "stream_limit_exceeded": overflow,
        "stdout": {"path": stdout.name, "sha256": sha256_file(stdout), "size": stdout.stat().st_size},
        "stderr": {"path": stderr.name, "sha256": sha256_file(stderr), "size": stderr.stat().st_size},
    }


def evaluate(repository: Path, baseline: str, candidate: str, pattern: str,
             oracle_path: str, oracle_sha256: str, output_dir: Path,
             timeout_seconds: int = 120) -> dict:
    repository = repository.resolve()
    _validate_input(repository, baseline, candidate, pattern, oracle_path, oracle_sha256, timeout_seconds)
    output_dir = output_dir.resolve()  # Resolve symlinked parents before containment checks.
    if output_dir.exists():
        raise RunnerError("output directory already exists: receipts are never overwritten")
    if output_dir.is_relative_to(repository):
        raise RunnerError("receipt directory must be outside the repository under test")
    output_dir.mkdir(parents=True, mode=0o700)
    trial = {
        "schema": "far-factory-before-after-execution/1",
        "status": "Research-operational-observation-not-scientific-evidence",
        "repository": str(repository), "baseline_sha": baseline, "candidate_sha": candidate,
        "test_pattern": pattern, "oracle_path": oracle_path,
        "registered_oracle_sha256": oracle_sha256,
        "environment": {"python": sys.version.split()[0], "platform": platform.platform(),
                        "runner": "Python unittest / Git worktree (no network isolation)"},
        "started_at": utc(), "completed_at": None, "before": None, "after": None,
        "verdict": "UNKNOWN", "limitations": [
            "This is observed unittest process behavior, not semantic correctness.",
            "A Git worktree does not isolate network, secrets, filesystem or subprocess effects.",
            "Artifacts are local bytes, not independently signed or immutable GitHub evidence.",
            "This is not the preregistered factory-versus-control comparative trial.",
        ],
    }
    worktrees: list[Path] = []
    try:
        with tempfile.TemporaryDirectory(prefix="far-before-after-") as tmp:
            for label, sha in (("before", baseline), ("after", candidate)):
                path = Path(tmp) / label
                _git(repository, "worktree", "add", "--detach", str(path), sha)
                worktrees.append(path)
            digests = {label: _oracle_digest(wt, oracle_path)
                       for label, wt in zip(("before", "after"), worktrees)}
            trial["observed_oracle_sha256"] = digests
            if any(value != oracle_sha256 for value in digests.values()):
                trial["verdict"] = "INCOMPARABLE"
            else:
                trial["before"] = _run_test(worktrees[0], "before", pattern, timeout_seconds, output_dir, repository)
                trial["after"] = _run_test(worktrees[1], "after", pattern, timeout_seconds, output_dir, repository)
                b, c = trial["before"]["status"], trial["after"]["status"]
                inventories_complete = (trial["before"]["test_inventory_complete"]
                                        and trial["after"]["test_inventory_complete"])
                trial["test_inventory_comparable"] = (inventories_complete
                    and trial["before"]["observed_test_ids"] == trial["after"]["observed_test_ids"])
                if inventories_complete and not trial["test_inventory_comparable"]:
                    trial["verdict"] = "INCOMPARABLE"
                else:
                    trial["verdict"] = {
                        ("FAIL", "PASS"): "OBSERVED_EXIT_STATUS_IMPROVEMENT",
                        ("PASS", "FAIL"): "OBSERVED_REGRESSION",
                        ("PASS", "PASS"): "OBSERVED_NO_REGRESSION",
                        ("FAIL", "FAIL"): "NO_OBSERVED_IMPROVEMENT",
                    }.get((b, c), "UNKNOWN")
    finally:
        for tree in reversed(worktrees):
            _git(repository, "worktree", "remove", "--force", str(tree))
        trial["completed_at"] = utc()
        (output_dir / "receipt.json").write_text(json.dumps(trial, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return trial


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repository", type=Path, required=True)
    p.add_argument("--baseline", required=True)
    p.add_argument("--candidate", required=True)
    p.add_argument("--test-pattern", required=True)
    p.add_argument("--oracle-path", required=True)
    p.add_argument("--expected-oracle-sha256", required=True)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--timeout-seconds", type=int, default=120)
    args = p.parse_args(argv)
    try:
        outcome = evaluate(args.repository, args.baseline, args.candidate, args.test_pattern,
                           args.oracle_path, args.expected_oracle_sha256, args.output,
                           args.timeout_seconds)
    except (RunnerError, OSError, subprocess.SubprocessError) as exc:
        print("INVALID/UNAVAILABLE: " + str(exc), file=sys.stderr)
        return 2
    print(outcome["verdict"] + " receipt=" + str(args.output / "receipt.json"))
    return 0 if outcome["verdict"] not in ("UNKNOWN", "INCOMPARABLE", "OBSERVED_REGRESSION") else 1


if __name__ == "__main__":
    raise SystemExit(main())
