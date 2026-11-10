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
