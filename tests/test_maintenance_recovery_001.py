"""Offline contract checks for historical replay; no agent/model inference."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("historical_replay", Path(__file__).resolve().parents[1] / "research" / "maintainability" / "maintenance-recovery-001" / "replay.py")
b = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(b)

# Synthetic observer-contract fixtures; never presented as source-exact FAR code.
def fixture(arm: str) -> bytes:
    body = '''class FactoryError(ValueError): pass
SCHEMA = "far-software-factory/work-order/1"
def validate_order(data):
    tasks = data['tasks']
    if not tasks:
        raise FactoryError('no tasks')
    if RECURSIVE and len(tasks) >= 900:
        raise RecursionError('synthetic recursion control')
    if tasks[-1]['depends_on']:
        raise FactoryError('cyclic dependency')
    return data
'''
    return (f"RECURSIVE = {arm=='before'}\n" + body).encode()


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, check=True, text=True).stdout.strip()


def missing_pinned_history_in_shallow_clone(root: Path) -> bool:
    """Skip only an unresolvable historical pin in an explicitly shallow clone.

    Complete checkouts must still fail if a pinned source disappears; never
    interpret a synthetic fixture as historical source-exact verification.
    """
    shallow = subprocess.run(["git", "-C", str(root), "rev-parse", "--is-shallow-repository"],
                             capture_output=True, text=True, timeout=15, check=False)
    if shallow.returncode != 0 or shallow.stdout.strip() != "true":
        return False
    return any(subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{sha}:{b.SOURCE}"],
        capture_output=True, timeout=15, check=False
    ).returncode != 0 for sha, _blob in b.PINS.values())


class HistoricalReplayTests(unittest.TestCase):
    def test_expected_observer_outcomes(self):
        for arm in b.PINS:
            with self.subTest(arm=arm):
                self.assertEqual(b.execute_source(fixture(arm)), b.EXPECTED[arm])

    def test_git_identity_and_end_to_end_record(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            git(repo, "init", "-q")
            git(repo, "config", "user.email", "unit-test@invalid.example")
            git(repo, "config", "user.name", "Unit Test")
            src = repo / b.SOURCE
            src.parent.mkdir(parents=True)
            pins = {}
            for arm in b.PINS:
                raw = fixture(arm)
                src.write_bytes(raw)
                git(repo, "add", b.SOURCE)
                git(repo, "-c", "commit.gpgsign=false", "commit", "-qm", f"{arm} fixture")
                commit = git(repo, "rev-parse", "HEAD")
                blob = git(repo, "rev-parse", f"{commit}:{b.SOURCE}")
                self.assertEqual(blob, b.git_blob_sha(raw))
                pins[arm] = (commit, blob)
                self.assertEqual(b.source_at(repo, commit, blob), raw)
                with self.assertRaisesRegex(ValueError, "does not match"):
                    b.source_at(repo, commit, "0" * 40)
            with patch.dict(b.PINS, pins, clear=True):
                record = b.replay(repo)
            self.assertTrue(record["replay_passed"])
            self.assertEqual(record["cases"], b.EXPECTED)
            self.assertEqual(record["coding_agent_executions"], 0)
            self.assertEqual(record["blind_trial_status"], "NOT_EXECUTED_NO_ISOLATED_AGENT_RUNTIME")

    def test_exact_historical_source_replay_from_git_checkout(self):
        """Run the two actual pinned modules when complete Git history is present.

        Repository Health uses an all-history checkout; standalone bundles do
        not. Never silently count a synthetic fixture as this real replay.
        """
        root = Path(__file__).resolve().parents[1]
        if not (root / ".git").exists():
            self.skipTest("no Git checkout: source-exact replay not executed")
        if missing_pinned_history_in_shallow_clone(root):
            self.skipTest("shallow checkout lacks pinned historical commits: source-exact replay NOT EXECUTED")
        result = b.replay(root)
        self.assertTrue(result["replay_passed"], result)
        self.assertEqual(result["cases"], b.EXPECTED)
        self.assertEqual(result["coding_agent_executions"], 0)

    def test_shallow_checkout_missing_historical_pins_is_explicitly_unverified(self):
        with tempfile.TemporaryDirectory() as td:
            original = Path(td) / "original"
            original.mkdir()
            git(original, "init", "-q")
            git(original, "config", "user.email", "unit-test@invalid.example")
            git(original, "config", "user.name", "Unit Test")
            source = original / b.SOURCE
            source.parent.mkdir(parents=True)
            for index in range(2):
                source.write_bytes(fixture("before" if index == 0 else "after"))
                git(original, "add", b.SOURCE)
                git(original, "-c", "commit.gpgsign=false", "commit", "-qm",
                    f"synthetic fixture commit {index}")
            clone = Path(td) / "depth-one"
            subprocess.run(["git", "clone", "-q", "--depth", "1",
                            original.as_uri(), str(clone)],
                           check=True, capture_output=True, timeout=30)
            self.assertEqual(git(clone, "rev-parse", "--is-shallow-repository"), "true")
            self.assertTrue(missing_pinned_history_in_shallow_clone(clone))
            self.assertFalse(missing_pinned_history_in_shallow_clone(original))

    def test_missing_history_and_invalid_identity_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(RuntimeError, "unavailable"):
                b.source_at(Path(td), "1" * 40, "2" * 40)
            with self.assertRaises(ValueError):
                b.source_at(Path(td), "invalid", "2" * 40)

    def test_incomplete_or_crashing_observer_rejected(self):
        with self.assertRaises(ValueError):
            b.execute_source(b"print('{}')\nraise SystemExit(0)\n")
        with self.assertRaises(RuntimeError):
            b.execute_source(b"raise RuntimeError('failure')\n")

if __name__ == "__main__":
    unittest.main()
