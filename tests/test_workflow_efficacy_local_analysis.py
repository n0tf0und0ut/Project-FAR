import tempfile
import json
import unittest
from pathlib import Path
from tools.workflow_efficacy_local_analysis import analyze

class LocalAnalysisTests(unittest.TestCase):
    def test_empty_is_not_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            a=analyze(d)
        self.assertEqual(a["status"],"INCOMPLETE_OR_INVALID")
        self.assertEqual(a["observed_unique_runs"],0)
        self.assertEqual(a["claim"],"NO_PERFORMANCE_ESTIMATE")
    def test_fabricated_60_records_do_not_pass(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(30):
                records=[{"task_id":f"FWE-{i+1:03d}","arm":arm,
                          "model":"qwen2.5-coder:1.5b","outcome":"SUCCESS"}
                         for arm in ("control","treatment")]
                (Path(d)/f"pair-{i:02d}.json").write_text(json.dumps(records))
            a=analyze(d)
        self.assertEqual(a["status"],"INCOMPLETE_OR_INVALID")
        self.assertIn("MODEL_DIGEST_NOT_CONSTANT",a["errors"])
        self.assertTrue(any("EVIDENCE_MISMATCH" in e for e in a["errors"]))
    def test_duplicate_arm_pair_fails(self):
        with tempfile.TemporaryDirectory() as d:
            for i in range(30):
                r={"task_id":f"FWE-{i+1:03d}","arm":"control"}
                (Path(d)/f"pair-{i:02d}.json").write_text(json.dumps([r,r]))
            a=analyze(d)
        self.assertTrue(any("BAD_RUN_ID" in e for e in a["errors"]))
if __name__=="__main__":
    unittest.main()
