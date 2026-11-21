"""Synthetic provider and tool seams only; never represent scored model inference."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import replanning_study_runner as study
from tools import workflow_efficacy_internal_fixtures as fixtures


def reply(action, *, model=study.MODEL['name'], prompt_tokens=10, output_tokens=10):
    return json.dumps({"model": model, "done": True,
                       "message": {"role": "assistant", "content": json.dumps(action)},
                       "prompt_eval_count": prompt_tokens,
                       "eval_count": output_tokens}, separators=(',',':')).encode()


class SyntheticProvider:
    def __init__(self, actions):
        self.actions = list(actions)
        self.calls = []

    def __call__(self, request, timeout):
        self.calls.append((json.loads(request), timeout))
        if not self.actions:
            raise AssertionError('unexpected model request')
        return 200, reply(self.actions.pop(0))


class StudyRunnerTests(unittest.TestCase):
    def setUp(self):
        self.ws = {"solution.py": "def transform(d): return 0\n", "README.md": "test", "test_public.py": "print('example')"}
        self.counter = study.Counter(provider=SyntheticProvider([]))
        self.fault = {"used":False}

    def test_initial_action_namespace_is_exact(self):
        for action in ({"action":"delete_file","path":"solution.py"},
                       {"action":"read_file","path":"../../etc/passwd"},
                       {"action":"read_file","path":"README.md","extra":1},
                       {"action":"write_file","path":"test_public.py","content":"x"},
                       {"action":"write_file","path":"/tmp/x","content":"x"},
                       {"action":"finish","path":"solution.py"}):
            with self.subTest(action=action):
                with self.assertRaises(study.StopRun):
                    study.Counter(provider=SyntheticProvider([])).tool(action, self.ws,
                                         inject_fault=False, fault_state={"used":False})
        self.assertEqual(self.ws["solution.py"], "def transform(d): return 0\n")

    def test_read_discloses_only_allowlisted_files(self):
        o,_ = self.counter.tool({"action":"list_files"}, self.ws, inject_fault=False, fault_state=self.fault)
        self.assertEqual(o["files"], ["README.md","solution.py","test_public.py"])
        r,_ = self.counter.tool({"action":"read_file","path":"solution.py"}, self.ws, inject_fault=False, fault_state=self.fault)
        self.assertEqual(r["content"], self.ws["solution.py"])
        self.assertEqual(len(self.counter.tools), 2)
        self.assertTrue(all(len(x["receipt_sha256"]) == 64 for x in self.counter.tools))

    def test_injected_fault_does_not_write_and_is_one_shot(self):
        action={"action":"write_file","path":"solution.py","content":"def transform(d): return 1\n"}
        first,fault = self.counter.tool(action,self.ws,inject_fault=True,fault_state=self.fault)
        self.assertTrue(fault)
        self.assertEqual(first["error"],"INJECTED_TRANSIENT_WRITE_FAILURE")
        self.assertEqual(self.ws["solution.py"],"def transform(d): return 0\n")
        second,fault = self.counter.tool(action,self.ws,inject_fault=True,fault_state=self.fault)
        self.assertFalse(fault)
        self.assertEqual(second["written"],"solution.py")
        self.assertEqual(self.ws["solution.py"],"def transform(d): return 1\n")

    def test_output_size_bounded(self):
        with self.assertRaisesRegex(study.StopRun, "WRITE_TOO_LARGE"):
            self.counter.tool({"action":"write_file","path":"solution.py","content":"a"*32769},
                              self.ws,inject_fault=False,fault_state=self.fault)

    def test_shared_tool_budget_exhaustion(self):
        self.counter.tool_calls=60
        with self.assertRaisesRegex(study.StopRun, "TOOL_CALL_BUDGET"):
            self.counter.tool({"action":"finish"},self.ws,inject_fault=False,fault_state=self.fault)

    def test_model_request_has_bounded_identity_and_no_secrets(self):
        x=SyntheticProvider([{"action":"finish"}])
        c=study.Counter(provider=x)
        out=c.model([{"role":"user","content":"test"}],purpose="worker")
        self.assertEqual(out,{"action":"finish"})
        self.assertEqual(c.tokens,20)
        self.assertEqual(x.calls[0][0]["model"],study.MODEL["name"])
        self.assertEqual(x.calls[0][0]["options"]["num_ctx"],2048)
        self.assertEqual(x.calls[0][0]["options"]["num_predict"],512)
        self.assertEqual(c.requests[0]["kind"],"synthetic_provider_test")
        self.assertEqual(c.requests[0]["response_sha256"],study._sha(reply({"action":"finish"})))

    def test_token_overage_fails_closed(self):
        # Provider counters that contradict the request budget are NOT ignored.
        def fake(request,timeout):
            return 200,reply({"action":"finish"},prompt_tokens=15001,output_tokens=1)
        c=study.Counter(provider=fake)
        with self.assertRaisesRegex(study.StopRun, "MODEL_TOKEN_OVERAGE"):
            c.model([{"role":"user","content":"x"}],purpose="worker")

    def test_low_remaining_budget_disallows_call(self):
        c=study.Counter(provider=SyntheticProvider([]));c.tokens=15000-2000
        with self.assertRaisesRegex(study.StopRun,"MODEL_TOKEN_BUDGET"):
            c.model([],purpose="worker")

    def test_wrong_model_envelope_fails(self):
        def wrong(_request,_timeout):
            return 200,reply({"action":"finish"},model="unfrozen-model:latest")
        with self.assertRaisesRegex(study.StopRun,"INVALID_MODEL_JSON"):
            study.Counter(provider=wrong).model([],purpose="worker")

    def test_incorrect_transport_is_failure_not_success(self):
        def bad(_request,_timeout):
            return 200,"not bytes"
        with self.assertRaisesRegex(study.StopRun,"INVALID_PROVIDER_RESPONSE"):
            study.Counter(provider=bad).model([],purpose="worker")

    def test_base_and_treatment_execute_same_frozen_objective(self):
        task=fixtures.task(0)
        def fake_grade(source,t,root):
            value=source.read_text()
            valid="return 1" in value
            trace=json.dumps({"fake":True,"valid":valid})
            return valid,0 if valid else 1,study._sha(trace.encode()),trace,True
        control=SyntheticProvider([{"action":"write_file","path":"solution.py","content":"def transform(d): return 1\n"}])
        treatment=SyntheticProvider([
            {"action":"write_file","path":"solution.py","content":"def transform(d): return 1\n"},
            {"action":"write_file","path":"solution.py","content":"def transform(d): return 1\n"},
            {"action":"finish"},
        ])
        # Planner receives an unpredictable genuine receipt id, so synthesize
        # its compliant response from the actual input event, not a hard-coded id.
        def treatment_transport(req,timeout):
            q=json.loads(req)
            if q["messages"][0]["content"]==study.PLANNER_SYSTEM:
                event=json.loads(q["messages"][1]["content"])["event_id"]
                return 200,reply({"intent_id":"recovery-1","event_id":event,
                                  "agent_id":"worker","instruction":"Retry write"})
            return treatment(req,timeout)
        with patch.object(study.free,"grade",side_effect=fake_grade):
            a=study.run_arm(task,"control",inject_fault=True,provider=control)
            b=study.run_arm(task,"replanning",inject_fault=True,provider=treatment_transport)
        self.assertEqual(a["provenance"],"SYNTHETIC_TEST")
        self.assertEqual(b["provenance"],"SYNTHETIC_TEST")
        self.assertEqual(a["trace_status"],"failed")
        self.assertEqual(b["grade"]["success"],True)
        self.assertEqual(len(a["orchestration_result_sha256"]),1)
        self.assertEqual(len(b["orchestration_result_sha256"]),2)
        self.assertEqual(a["grade"]["success"],False)
        self.assertEqual(a["initial_file_sha256"],b["initial_file_sha256"])
        self.assertEqual(a["fault_injected"],b["fault_injected"])

    def test_actual_provider_refuses_unverified_registry(self):
        with patch.object(study.tar,"local_provider",study.tar.local_provider):
            with self.assertRaisesRegex(study.StopRun,"MODEL_IDENTITY_UNATTESTED"):
                study.run_arm(fixtures.task(0),"control",inject_fault=False)

    def test_running_without_independent_manifest_does_not_call_model(self):
        with patch.object(study.tar,"installed_digest",side_effect=AssertionError("model should not run")):
            self.assertEqual(study.main(["run-slot","--slot","1"]),2)

    def test_preflight_checks_registry_without_exposing_task(self):
        with patch.object(study.tar,"installed_digest",return_value=study.MODEL["digest"]) as check:
            self.assertEqual(study.main(["provider-preflight"]),0)
            check.assert_called_once_with(study.MODEL)


if __name__=="__main__":
    unittest.main()
