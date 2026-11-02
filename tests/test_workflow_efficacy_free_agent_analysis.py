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
    def test_duplicate_arms_fail(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(30):
                item={"task_id":f"FWE-{i+1:03d}","arm":"control","model_steps":0}
                (Path(d)/f"pair-{i:02d}.json").write_text(json.dumps([item,item]))
            report=analyze(d)
        self.assertIn("DUPLICATE_RUN",report["errors"])
if __name__=="__main__":
    unittest.main()
