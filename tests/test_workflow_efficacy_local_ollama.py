import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools.workflow_efficacy_internal_fixtures import task
from tools.workflow_efficacy_local_ollama import (
 MODEL,OPTIONS,order,extract,model_sha,grade
)
class LocalInferenceTests(unittest.TestCase):
    def test_arm_order_balanced(self):
        self.assertEqual(sum(order(i)[0]=="control" for i in range(30)),15)
        self.assertEqual(sum(order(i)[0]=="treatment" for i in range(30)),15)
    def test_fixed_local_model(self):
        self.assertEqual(MODEL,"qwen2.5-coder:1.5b")
        self.assertEqual(OPTIONS["seed"],602)
        self.assertEqual(OPTIONS["temperature"],0)
    def test_extract_fenced_code(self):
        fence=chr(96)*3
        raw=fence+"python\ndef transform(x): return x\n"+fence
        self.assertEqual(extract(raw),"def transform(x): return x\n")
    def test_refuse_missing_model_digest(self):
        with patch("tools.workflow_efficacy_local_ollama.request",
          return_value={"models":[]}):
            with self.assertRaises(ValueError): model_sha()
    def test_grader_rejects_unexecuted_docker(self):
        with tempfile.TemporaryDirectory() as d:
            with patch("tools.workflow_efficacy_local_ollama.subprocess.run",
                side_effect=OSError("docker unavailable")):
                ran,passed,code,trace=grade("def transform(x): return 1",
                                           task(0),Path(d))
        self.assertFalse(ran)
        self.assertFalse(passed)
        self.assertIsNone(code)
if __name__=="__main__": unittest.main()
