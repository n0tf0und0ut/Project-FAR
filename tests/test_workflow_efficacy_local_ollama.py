import json
from types import SimpleNamespace
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
    def test_exact_instruction_section_extraction(self):
        from tools.workflow_efficacy_local_ollama import extract_section
        source=b"## Relevant\ntext\n\n## Other\nend\n"
        self.assertEqual(extract_section(source,"## Relevant"),b"## Relevant\ntext")
        with self.assertRaises(ValueError):
            extract_section(source,"## Nonexistent")
    def test_extract_fenced_code(self):
        fence=chr(96)*3
        raw=fence+"python\ndef transform(x): return x\n"+fence
        self.assertEqual(extract(raw),"def transform(x): return x\n")
    def test_refuse_missing_model_digest(self):
        with patch("tools.workflow_efficacy_local_ollama.request",
          return_value={"models":[]}):
            with self.assertRaises(ValueError): model_sha()
    def test_grader_rejects_unexecuted_docker(self):
        from tools import workflow_efficacy_free_agent as shared
        with tempfile.TemporaryDirectory() as d:
            with patch.object(shared,"capture_candidate_process",
                side_effect=OSError("docker unavailable")) as transport, patch.object(
                shared.subprocess,"Popen",side_effect=AssertionError(
                "offline transport-failure fixture must not launch Docker")) as spawned, patch.object(
                shared.subprocess,"run",return_value=SimpleNamespace(
                returncode=0,stdout="",stderr="")) as cleanup:
                ran,passed,code,trace=grade("def transform(x): return 1",
                                           task(0),Path(d))
        self.assertFalse(ran)
        self.assertFalse(passed)
        self.assertIsNone(code)
        self.assertEqual(transport.call_count,6)
        self.assertEqual(cleanup.call_count,6)
        spawned.assert_not_called()
    def run_provider_reply(self, reason, **changes):
        from tools import workflow_efficacy_local_ollama as runner
        with tempfile.TemporaryDirectory() as d, patch.object(runner,"model_sha",return_value="a"*64), patch.object(
                runner,"instructions",return_value=b"rules"), patch.object(runner,"prompt",return_value="prompt"), patch.object(
                runner,"request",return_value={"response":"def transform(x): return None","done":True,
                "done_reason":reason,"model":MODEL,"eval_count":320,"prompt_eval_count":100,**changes}), patch.object(
                runner,"grade",return_value=(True,False,1,"failure")) as grader:
            record=runner.run_one(0,"control",Path(d))
            raw=(Path(d)/"FWE-001-control"/"provider-response.json").read_bytes()
        self.assertEqual(record["provider_response_sha"],runner.sha(raw))
        return record,grader.call_count

    def test_token_limit_completion_cannot_be_scored(self):
        record,calls=self.run_provider_reply("length")
        self.assertEqual(record["outcome"],"INCOMPLETE")
        self.assertEqual(record["done_reason"],"length")
        self.assertEqual(calls,0)

    def test_missing_termination_reason_cannot_be_scored(self):
        record,calls=self.run_provider_reply(None)
        self.assertEqual(record["outcome"],"INCOMPLETE")
        self.assertEqual(calls,0)

    def test_malformed_content_or_input_telemetry_never_executes_code(self):
        for changes in ({"response":[]},{"response":None},{"prompt_eval_count":True},{"prompt_eval_count":0}):
            with self.subTest(changes=changes):
                record,calls=self.run_provider_reply("stop",**changes)
                self.assertEqual(record["outcome"],"INCOMPLETE")
                self.assertEqual(calls,0)

    def test_natural_stop_can_be_a_measured_failure(self):
        record,calls=self.run_provider_reply("stop")
        self.assertEqual(record["outcome"],"FAILURE")
        self.assertEqual(calls,1)

    def test_local_wrapper_uses_existing_trusted_host_assertions(self):
        from tests.test_workflow_efficacy_free_agent import local_grader_transport
        from tools import workflow_efficacy_free_agent as shared
        malicious="import unittest\nunittest.TestCase.assertEqual=lambda *a,**kw:None\ndef transform(x): return None\n"
        with tempfile.TemporaryDirectory() as d, patch.object(shared,"capture_candidate_process",
                side_effect=local_grader_transport), patch.object(shared.subprocess,"run",
                return_value=SimpleNamespace(returncode=0,stdout="",stderr="")):
            ran,passed,code,trace=grade(malicious,task(0),Path(d))
        self.assertTrue(ran)
        self.assertFalse(passed)
        self.assertEqual(code,1)
        self.assertEqual(json.loads(trace)["schema"],"far-isolated-output-grade/1")

    def test_local_wrapper_cleans_each_named_container_after_timeout(self):
        from tools import workflow_efficacy_free_agent as shared
        import subprocess
        with tempfile.TemporaryDirectory() as d, patch.object(shared,"capture_candidate_process",
                side_effect=subprocess.TimeoutExpired("docker",10)), patch.object(shared.subprocess,"run",
                return_value=SimpleNamespace(returncode=0,stdout="",stderr="")) as cleanup:
            ran,passed,code,trace=grade("def transform(x): return None",task(0),Path(d))
        self.assertFalse(ran)
        self.assertFalse(passed)
        self.assertIsNone(code)
        self.assertEqual(cleanup.call_count,6)
        names=[c.args[0] for c in cleanup.call_args_list]
        self.assertTrue(all(c[:3]==["docker","rm","--force"] for c in names))
        self.assertEqual(len({c[3] for c in names}),6)

if __name__=="__main__": unittest.main()
