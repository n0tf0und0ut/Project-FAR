"""Regression tests for the synthetic fault campaign (not model evaluations)."""
import copy
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from tools import tool_agent_fault_campaign as faults


class ToolAgentFaultCampaignTests(unittest.TestCase):
    def test_all_fault_classes_and_tamper_checks(self):
        report = faults.campaign()
        self.assertEqual(report["status"], "PASS", report)
        self.assertEqual(report["tested"], len(faults.CASES) + len(faults.MUTATIONS))
        self.assertTrue(all(row["ok"] for row in report["cases"]))
        self.assertEqual(report["model_calls"], 0)
        self.assertEqual(report["general_agent_reliability"], "NOT_ESTABLISHED")
        self.assertFalse(report["model_provenance_attested"])

    def test_repeatable_record_from_real_checkpoint_and_runner(self):
        a = faults.execute_case("clean")
        b = faults.execute_case("clean")
        self.assertEqual(faults.host.encoded(a), faults.host.encoded(b))
        self.assertEqual(faults.verify_record(a)["passed"], True)
        self.assertEqual(a["provenance"], "SYNTHETIC_TEST")
        self.assertTrue(faults.sentinel_passes(a))

    def test_transient_unsafe_mutation_not_redeemed_by_undo(self):
        record = faults.execute_case("protected_write_undone")
        self.assertEqual(record["final_files"]["facts.txt"], faults.TASK["files"]["facts.txt"])
        self.assertEqual(record["terminal_reason"], "FINISHED")
        self.assertGreater(faults.verify_record(record)["unsafe_attempts"], 0)
        self.assertFalse(record["grade"]["passed"])
        self.assertFalse(faults.sentinel_passes(record))

    def test_independent_sentinel_disagrees_with_forged_state(self):
        clean = faults.execute_case("clean")
        forged = copy.deepcopy(clean)
        forged["final_files"]["answer.txt"] = "red"
        self.assertFalse(faults.sentinel_passes(forged))
        with self.assertRaises(ValueError):
            faults.verify_record(forged)

    def test_fault_campaign_fails_closed_if_replayer_accepts_everything(self):
        with patch.object(faults.host, "replay", return_value={
            "passed": True, "terminal_reason": "FINISHED", "unsafe_attempts": 0,
        }):
            report = faults.campaign()
        self.assertEqual(report["status"], "FAIL")
        self.assertTrue(any(not row["ok"] for row in report["cases"]))

    def test_replay_is_not_model_origin_authentication(self):
        # The archive records an origin label, not a signed runtime witness.
        # A relabeled synthetic response can pass deterministic replay.
        record = faults.execute_case("clean")
        forged = copy.deepcopy(record)
        forged["provenance"] = "LOCAL_OLLAMA"
        replayed = faults.host.replay(
            forged, faults.TASK, faults.PROTOCOL_SHA, faults.SOURCE,
            allow_synthetic=False,
        )
        self.assertTrue(replayed["passed"])

    def test_cli_emits_machine_readable_report(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = faults.main([])
        report = json.loads(stdout.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
