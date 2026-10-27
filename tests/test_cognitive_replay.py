"""Bind CI to the preserved corrected internal run, without promoting it."""
import subprocess
import sys
import unittest
from pathlib import Path


class CognitiveReplayTests(unittest.TestCase):
    def test_committed_internal_results_replay_from_pinned_inputs(self):
        result = subprocess.run([sys.executable, 'tools/evaluate_cognitive_audit.py', '--check'],
                                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__': unittest.main()
