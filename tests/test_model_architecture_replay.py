"""Regression controls for exact source-bound and thread-bound FAR MAS replay."""
import copy
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import model_architecture_replay as replay
import torch


class ReplayTests(unittest.TestCase):
    def report(self):
        return {"environment": {"threads": 1}, "protocol": {"device": "cpu"}}

    def test_enforces_recorded_cpu_thread_count_before_verifier(self):
        report = self.report()
        original = torch.get_num_threads()
        try:
            torch.set_num_threads(4)
            with patch.object(replay.replication, "validate_report") as validator:
                replay.verify_with_recorded_threads(report, b"evidence")
                self.assertEqual(torch.get_num_threads(), 1)
                validator.assert_called_once_with(report, b"evidence", replay=True)
        finally:
            torch.set_num_threads(original)

    def test_fail_closed_on_unrecorded_and_inconsistent_configuration(self):
        for bad in (None, 0, 2, True, "1"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                r = self.report()
                r["environment"]["threads"] = bad
                replay.verify_with_recorded_threads(r, b"")
        r = self.report()
        r["protocol"]["device"] = "cuda"
        with self.assertRaises(ValueError):
            replay.verify_with_recorded_threads(r, b"")


if __name__ == "__main__":
    unittest.main()
