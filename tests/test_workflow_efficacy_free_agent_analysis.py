"""Validation tests for the paired synthetic-agent analysis; no model requests."""
import tempfile
import json
import unittest
from pathlib import Path
from tools.workflow_efficacy_free_agent_analysis import analyze

class AnalysisTests(unittest.TestCase):
    def test_empty_folder_is_not_success(self):
        with tempfile.TemporaryDirectory() as d:
            report=analyze(d)
        self.assertEqual(report["status"],"INCOMPLETE_OR_INVALID")
        self.assertIn("WRONG_PAIR_FILE_COUNT",report["errors"])
        self.assertFalse(report["historical_pr_comparison_executed"])
    def test_empty_model_steps_never_count_as_execution(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(30):
                path=Path(d)/f"pair-{i:02d}.json"
                path.write_text(json.dumps([
                    {"task_id":f"FWE-{i+1:03d}","arm":"control","model_steps":0},
                    {"task_id":f"FWE-{i+1:03d}","arm":"treatment","model_steps":0}]))
            report=analyze(d)
        self.assertEqual(report["status"],"INCOMPLETE_OR_INVALID")
        self.assertTrue(any("NO_MODEL_STEPS" in x for x in report["errors"]))
        self.assertTrue(any("MISSING_OR_UNEXECUTED_GRADER" in x for x in report["errors"]))
    def test_partial_provider_error_cannot_count_as_agent_failure(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(30):
                records = []
                for arm in ("control", "treatment"):
                    records.append({
                        "task_id": f"FWE-{i+1:03d}",
                        "arm": arm,
                        "model_steps": 1,
                        "error_events": 1 if i == 0 and arm == "treatment" else 0,
                        "timeout": False, "cli_exit_code": 0,
                        "grader_status": "EXECUTED", "grader_exit_code": 1,
                        "outcome": "FAILURE",
                    })
                (Path(d)/f"pair-{i:02d}.json").write_text(json.dumps(records))
            report=analyze(d)
        self.assertEqual(report["status"], "INCOMPLETE_OR_INVALID")
        self.assertTrue(any("INCOMPLETE_PROVIDER_SESSION:FWE-001:treatment" in e
                            for e in report["errors"]))
    def test_completed_model_step_does_not_clear_timeout(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(30):
                records = [
                    {"task_id": f"FWE-{i+1:03d}", "arm": arm,
                     "model_steps": 1, "error_events": 0,
                     "timeout": arm == "control" and i == 0,
                     "cli_exit_code": 0,
                     "grader_status": "EXECUTED", "grader_exit_code": 1,
                     "outcome": "FAILURE"}
                    for arm in ("control","treatment")
                ]
                (Path(d)/f"pair-{i:02d}.json").write_text(json.dumps(records))
            report=analyze(d)
        self.assertIn("INCOMPLETE_AGENT_EXECUTION:FWE-001:control", report["errors"])

    def test_duplicate_arms_fail(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(30):
                item={"task_id":f"FWE-{i+1:03d}","arm":"control","model_steps":0}
                (Path(d)/f"pair-{i:02d}.json").write_text(json.dumps([item,item]))
            report=analyze(d)
        self.assertIn("DUPLICATE_RUN",report["errors"])
if __name__=="__main__":
    unittest.main()
