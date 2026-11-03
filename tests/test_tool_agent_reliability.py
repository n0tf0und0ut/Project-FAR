"""Offline adversarial checks; synthetic providers never count as model evidence."""
import base64
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import tool_agent_reliability as r


SOURCE = {"commit": "a"*40, "tree": "b"*40, "files": {}}


def action(tool, **args):
    return {"tool": tool, "args": args}


def provider(actions, model=r.MODEL):
    sequence = iter(actions)
    def call(request, timeout):
        v = next(sequence)
        content = v if isinstance(v, str) else json.dumps(v)
        return 200, r.encoded({"model":model, "done":True, "message":{"role":"assistant","content":content}, "prompt_eval_count":100,"eval_count":20})
    return call


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.protocol_path = r.ROOT / "research/tool-agent-reliability/protocol-v0.1.json"
        self.protocol = r.load_protocol(self.protocol_path)
        self.digest = r.sha(self.protocol_path.read_bytes())
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / "record.json"
        self.task = copy.deepcopy(self.protocol["tasks"][0])

    def run_actions(self, actions, task=None, seed=0, **kwargs):
        return r.run_task(task or self.task,seed,self.digest,SOURCE,self.out,
                          provider=provider(actions),digest=r.MODEL_DIGEST,**kwargs)

    def replay(self, record, task=None):
        return r.replay(record,task or self.task,self.digest,SOURCE,allow_synthetic=True)

    def test_real_multiturn_observation_precedes_answer(self):
        result = self.run_actions([action("read_file",path="facts.json"),action("finish",answer="blue")])
        self.assertTrue(result["grade"]["passed"])
        self.assertEqual(self.replay(result)["model_calls"],2)
        second = json.loads(result["events"][1]["request_utf8"])
        self.assertEqual(json.loads(second["messages"][-1]["content"])["observation"]["result"],self.task["files"]["facts.json"])
        self.assertNotIn("oracle",result["events"][0]["request_utf8"])
        self.assertNotIn("blue",result["events"][0]["request_utf8"])

    def test_guessed_correct_answer_without_read_fails(self):
        result = self.run_actions([action("finish",answer="blue")])
        self.assertFalse(result["grade"]["passed"])
        self.assertFalse(result["grade"]["checks"]["reads"])
        self.replay(result)

    def test_scripted_provider_cannot_be_counted_as_live_model(self):
        result = self.run_actions([action("finish",answer="blue")])
        with self.assertRaisesRegex(ValueError,"not genuine"):
            r.replay(result,self.task,self.digest,SOURCE)

    def test_malformed_action_shapes_are_measured_failures(self):
        for malformed in (None,[],{"tool":[],"args":{}},{"tool":"read_file","args":[]},"not json","["*2000+"0"+"]"*2000):
            with self.subTest(malformed=str(malformed)[:60]):
                result = self.run_actions([json.dumps(malformed) if malformed is None else malformed])
                self.assertEqual(result["terminal_reason"],"INVALID_ACTION")
                self.assertTrue(result["valid"])
                self.assertFalse(result["grade"]["passed"])
                self.replay(result)

    def test_duplicate_nonfinite_and_surrogate_action_json_fail(self):
        for malformed in ('{"tool":"finish","tool":"read_file","args":{}}','{"tool":"finish","args":{"answer":1e999}}','{"tool":"finish","args":{"answer":"\\ud800"}}'):
            with self.subTest(malformed=malformed):
                result=self.run_actions([malformed])
                self.assertEqual(result["terminal_reason"],"INVALID_ACTION")
                self.replay(result)

    def test_calculator_is_bounded_and_has_no_execution(self):
        self.assertEqual(r.compute("(12+3)*4"),60)
        for expr in ("__import__('os').system('true')","2**1000000000","True+1","1.5+2","1000000000000*2","1/2","1//0"):
            with self.subTest(expr=expr), self.assertRaises((ValueError,ZeroDivisionError)):
                r.compute(expr)

    def test_failed_or_irrelevant_calculator_does_not_satisfy_arithmetic(self):
        task=copy.deepcopy(self.protocol["tasks"][1])
        for expr in ("1//0","1+1"):
            result=self.run_actions([action("read_file",path="numbers.txt"),action("calculator",expression=expr),action("finish",answer=214)],task)
            self.assertFalse(result["grade"]["passed"])
            self.assertFalse(result["grade"]["checks"]["calculator_result"])
            self.replay(result,task)

    def test_correct_calculator_based_answer_passes(self):
        task=copy.deepcopy(self.protocol["tasks"][1])
        result=self.run_actions([action("read_file",path="numbers.txt"),action("calculator",expression="35*6+4"),action("finish",answer=214)],task)
        self.assertTrue(result["grade"]["passed"])
        self.replay(result,task)

    def test_transient_protected_mutation_cannot_be_undone(self):
        result=self.run_actions([action("read_file",path="facts.json"),action("write_file",path="facts.json",content="wrong"),action("write_file",path="facts.json",content=self.task["files"]["facts.json"]),action("finish",answer="blue")])
        self.assertEqual(result["final_files"],self.task["files"])
        self.assertFalse(result["grade"]["passed"])
        self.assertEqual(result["grade"]["unsafe_writes"],1)
        self.replay(result)

    def test_unauthorized_new_file_counts_unsafe_write(self):
        result=self.run_actions([action("read_file",path="facts.json"),action("write_file",path="leak.txt",content="x"),action("finish",answer="blue")])
        self.assertEqual(result["grade"]["unsafe_writes"],1)
        self.assertFalse(result["grade"]["passed"])
        self.replay(result)

    def test_traversal_is_measured_and_does_not_reach_host(self):
        for path in ("../secret","/etc/passwd","a/../../secret","a\\b"):
            result=self.run_actions([action("read_file",path=path)])
            self.assertEqual(result["terminal_reason"],"INVALID_ACTION")
            self.assertEqual(result["final_files"],self.task["files"])
            self.replay(result)

    def test_output_write_is_actual_state_change_not_answer_prose(self):
        task=copy.deepcopy(self.task)
        task["oracle"]["files"]={"output.txt":"blue"}
        good=self.run_actions([action("read_file",path="facts.json"),action("write_file",path="output.txt",content="blue"),action("finish",answer="blue")],task)
        self.assertTrue(good["grade"]["passed"])
        self.replay(good,task)
        bad=self.run_actions([action("read_file",path="facts.json"),action("finish",answer="blue")],task)
        self.assertFalse(bad["grade"]["checks"]["files"])

    def test_missing_file_recovery_order_is_enforced(self):
        task=copy.deepcopy(self.task)
        task["oracle"]["expected_read_errors"]=["old.txt"]
        good=self.run_actions([action("read_file",path="old.txt"),action("read_file",path="facts.json"),action("finish",answer="blue")],task)
        self.assertTrue(good["grade"]["passed"])
        self.replay(good,task)
        bad=self.run_actions([action("read_file",path="facts.json"),action("read_file",path="old.txt"),action("finish",answer="blue")],task)
        self.assertFalse(bad["grade"]["checks"]["recovery_order"])
        self.replay(bad,task)

    def test_recovery_listing_after_target_read_does_not_count(self):
        task=copy.deepcopy(self.task)
        task["oracle"]["expected_read_errors"]=["old.txt"]
        task["oracle"]["required_tools"].append("list_files")
        bad=self.run_actions([action("read_file",path="old.txt"),action("read_file",path="facts.json"),action("list_files"),action("finish",answer="blue")],task)
        self.assertFalse(bad["grade"]["checks"]["recovery_order"])
        self.replay(bad,task)
        good=self.run_actions([action("read_file",path="old.txt"),action("list_files"),action("read_file",path="facts.json"),action("finish",answer="blue")],task)
        self.assertTrue(good["grade"]["passed"])
        self.replay(good,task)

    def test_recovery_task_malformed_arguments_remain_measured(self):
        task=copy.deepcopy(self.task)
        task["oracle"]["expected_read_errors"]=["old.txt"]
        result=self.run_actions([{"tool":"read_file","args":[]}],task)
        self.assertEqual(result["terminal_reason"],"INVALID_ACTION")
        self.replay(result,task)

    def test_write_surrogate_is_measured_without_checkpoint_crash(self):
        result=self.run_actions(['{"tool":"write_file","args":{"path":"out.txt","content":"\\ud800"}}'])
        self.assertEqual(result["terminal_reason"],"INVALID_ACTION")
        self.replay(result)

    def test_complete_72_slot_panel_is_recomputed_and_descriptive(self):
        records=[]
        for task in [t for t in self.protocol["tasks"] if t["phase"]=="scored"]:
            for seed in (0,1,2):
                actions=[action("read_file",path=path) for path in task["oracle"].get("expected_read_errors",[])]
                if "list_files" in task["oracle"]["required_tools"]:
                    actions.append(action("list_files"))
                actions += [action("read_file",path=path) for path in task["oracle"]["required_reads"]]
                if "calculator" in task["oracle"]["required_tools"]:
                    actions.append(action("calculator",expression=str(task["oracle"]["answer"])))
                for path,value in task["oracle"]["files"].items():
                    actions.append(action("write_file",path=path,content=value))
                actions.append(action("finish",answer=task["oracle"]["answer"]))
                records.append(self.run_actions(actions,task,seed=seed))
        report=r.analyze(self.protocol,records,self.digest,SOURCE,phase="scored",allow_synthetic=True)
        self.assertTrue(report["complete"],report["errors"])
        self.assertEqual(report["passed"],72)
        self.assertEqual(report["all_three_successful_tasks"],24)
        self.assertEqual(report["at_least_one_successful_tasks"],24)
        self.assertEqual(report["first_attempt_passed"],24)
        self.assertTrue(report["scored_engineering_screen_passed"])
        self.assertEqual({v["passed"] for v in report["families"].values()},{12})
        self.assertGreater(report["totals"]["tool_actions"],72)
        self.assertEqual(report["totals"]["input_tokens"],report["totals"]["model_calls"]*100)
        self.assertEqual(report["general_agent_reliability"],"NOT_ESTABLISHED")
        self.assertEqual(report["far_causal_effect"],"NOT_TESTED")

    def test_provider_failure_retains_prior_raw_evidence_without_retry(self):
        calls=[]
        first=provider([action("read_file",path="facts.json")])
        def failing(request,timeout):
            calls.append(request)
            if len(calls)==1:return first(request,timeout)
            raise TimeoutError("unavailable")
        result=r.run_task(self.task,0,self.digest,SOURCE,self.out,provider=failing,digest=r.MODEL_DIGEST)
        self.assertEqual(len(calls),2)
        self.assertEqual(result["terminal_reason"],"PROVIDER_ERROR")
        self.assertFalse(result["valid"])
        self.assertIsNotNone(result["events"][0]["response_base64"])
        self.assertEqual(r.strict_json(self.out.read_bytes()),result)
        self.replay(result)

    def test_malformed_provider_bytes_preserved_before_validation(self):
        raw=b'\xffbroken'
        result=r.run_task(self.task,0,self.digest,SOURCE,self.out,provider=lambda *a:(200,raw),digest=r.MODEL_DIGEST)
        self.assertFalse(result["valid"])
        self.assertEqual(base64.b64decode(result["events"][0]["response_base64"]),raw)
        self.replay(result)

    def test_excessive_response_is_retained_as_invalid(self):
        raw=b'x'*(r.MAX_RESPONSE+1)
        result=r.run_task(self.task,0,self.digest,SOURCE,self.out,provider=lambda *a:(200,raw),digest=r.MODEL_DIGEST)
        self.assertEqual(result["terminal_reason"],"PROVIDER_ERROR")
        self.replay(result)

    def test_success_after_deadline_cannot_pass(self):
        current=[0.0]
        base=provider([action("finish",answer="blue")])
        def slow(request,timeout):
            current[0]=601.0
            return base(request,timeout)
        result=r.run_task(self.task,0,self.digest,SOURCE,self.out,provider=slow,digest=r.MODEL_DIGEST,clock=lambda:current[0])
        self.assertEqual(result["terminal_reason"],"TIME_LIMIT")
        self.assertFalse(result["grade"]["passed"])
        self.assertIsNone(result["events"][0]["action"])
        self.replay(result)

    def test_finish_processing_cannot_cross_global_deadline(self):
        current=[0.0]
        actual_checkpoint=r.checkpoint
        def slow_checkpoint(path, record):
            if record["events"] and record["events"][-1].get("receipt") is not None:
                current[0]=600.1
            actual_checkpoint(path,record)
        # Read is not required here: isolate finish timing from grading failure.
        task=copy.deepcopy(self.task);task["oracle"]["required_reads"]=[];task["oracle"]["required_tools"]=[]
        with patch.object(r,"checkpoint",side_effect=slow_checkpoint):
            result=r.run_task(task,0,self.digest,SOURCE,self.out,provider=provider([action("finish",answer="blue")]),digest=r.MODEL_DIGEST,clock=lambda:current[0])
        self.assertEqual(result["terminal_reason"],"TIME_LIMIT")
        self.assertFalse(result["grade"]["passed"])
        self.replay(result,task)

    def test_request_deadline_is_enforced_even_before_total_deadline(self):
        current=[0.0]
        base=provider([action("finish",answer="blue")])
        def slow(request,timeout):
            current[0]=121.0
            return base(request,timeout)
        result=r.run_task(self.task,0,self.digest,SOURCE,self.out,provider=slow,digest=r.MODEL_DIGEST,clock=lambda:current[0])
        self.assertEqual(result["terminal_reason"],"TIME_LIMIT")
        self.replay(result)

    def test_action_limit_is_not_success(self):
        result=self.run_actions([action("list_files")]*8)
        self.assertEqual(result["terminal_reason"],"ACTION_LIMIT")
        self.assertFalse(result["grade"]["passed"])
        self.replay(result)

    def test_checkpoint_precedes_provider_and_each_successor(self):
        seen=[]
        base=provider([action("read_file",path="facts.json"),action("finish",answer="blue")])
        def inspect(request,timeout):
            record=r.strict_json(self.out.read_bytes())
            self.assertEqual(record["status"],"RUNNING")
            self.assertIsNone(record["events"][-1]["response_base64"])
            if seen:self.assertTrue(record["events"][-2]["receipt"]["ok"])
            seen.append(record)
            return base(request,timeout)
        result=r.run_task(self.task,0,self.digest,SOURCE,self.out,provider=inspect,digest=r.MODEL_DIGEST)
        self.assertEqual(len(seen),2)
        self.replay(result)

    def test_replay_rejects_mutated_messages_receipts_state_and_score(self):
        result=self.run_actions([action("read_file",path="facts.json"),action("finish",answer="blue")])
        mutators=[lambda v:v["events"][0].update(request_sha256="0"*64),lambda v:v["events"][0].update(response_sha256="0"*64),lambda v:v["events"][0]["receipt"].update(result="wrong"),lambda v:v["grade"].update(passed=False),lambda v:v["final_files"].update(hacked="yes"),lambda v:v.update(valid=False),lambda v:v.update(terminal_reason="PROVIDER_ERROR")]
        for mutate in mutators:
            bad=copy.deepcopy(result);mutate(bad)
            with self.assertRaises(ValueError):self.replay(bad)

    def test_exact_source_model_protocol_and_seed_are_required(self):
        result=self.run_actions([action("finish",answer="blue")])
        for key,value in (("source",{}),("model",{}),("protocol_sha256","0"*64),("seed",1)):
            bad=copy.deepcopy(result);bad[key]=value
            with self.assertRaises(ValueError):self.replay(bad)

    def test_legacy_records_without_policy_metadata_replay_only_original_system(self):
        result=self.run_actions([action("read_file",path="facts.json"),action("finish",answer="blue")])
        result.pop("agent_policy");result.pop("system_sha256")
        self.assertTrue(self.replay(result)["passed"])
        with self.assertRaisesRegex(ValueError,"policy identity"):
            r.replay(result,self.task,self.digest,SOURCE,allow_synthetic=True,agent_policy="v0.2")

    def test_missing_duplicate_and_synthetic_rows_fail_closed(self):
        result=self.run_actions([action("read_file",path="facts.json"),action("finish",answer="blue")])
        report=r.analyze(self.protocol,[result,result],self.digest,SOURCE,phase="preflight",allow_synthetic=True)
        self.assertFalse(report["complete"])
        self.assertTrue(report["errors"])
        self.assertEqual(len(report["missing_slots"]),2)
        report=r.analyze(self.protocol,[result],self.digest,SOURCE,phase="preflight")
        self.assertEqual(report["replayed_records"],0)
        self.assertFalse(report["preflight_gate_passed"])

    def test_preflight_gate_replays_three_slots_and_stops_on_unsafe(self):
        tasks=[t for t in self.protocol["tasks"] if t["phase"]=="preflight"]
        records=[]
        for task in tasks:
            actions=[action("read_file",path=path) for path in task["oracle"]["required_reads"]]
            if "calculator" in task["oracle"]["required_tools"]:actions.append(action("calculator",expression="35*6+4"))
            for path,value in task["oracle"]["files"].items():actions.append(action("write_file",path=path,content=value))
            actions.append(action("finish",answer=task["oracle"]["answer"]))
            records.append(self.run_actions(actions,task))
        report=r.analyze(self.protocol,records,self.digest,SOURCE,phase="preflight",allow_synthetic=True)
        self.assertTrue(report["preflight_gate_passed"])
        self.assertEqual(report["passed"],3)
        self.assertEqual(report["general_agent_reliability"],"NOT_ESTABLISHED")

    def test_protocol_rejects_mutated_gates_and_oracles(self):
        for mutate in (lambda p:p["limits"].update(max_actions=9),lambda p:p["model"].update(digest="0"*64),lambda p:p["preflight_gate"].update(minimum_successes=1),lambda p:p["preflight_gate"].update(no_outcome_based_tuning=1),lambda p:p["scored_criteria"].update(minimum_slot_success_fraction=0.1),lambda p:p["tasks"][0]["oracle"].update(required_tools=["shell"])):
            bad=copy.deepcopy(self.protocol);mutate(bad)
            with self.assertRaises(ValueError):r.validate_protocol(bad)

    def test_cli_scored_launch_requires_raw_preflight_before_model_access(self):
        with patch.object(r,"source_identity",return_value=SOURCE),patch.object(r,"installed_digest",side_effect=AssertionError("must not inspect provider")):
            with self.assertRaises(SystemExit):r.main(["run","--phase","scored","--out",str(self.out)])

    def test_cli_preflight_runs_all_three_tasks_in_single_job(self):
        new_protocol = r.load_protocol()
        with patch.object(r,"source_identity",return_value=SOURCE),patch.object(r,"installed_digest",return_value=r.MODEL_DIGEST_7B),patch.object(r,"run_task",return_value={"valid":True,"grade":{"passed":False},"terminal_reason":"INVALID_ACTION"}) as run:
            r.main(["run","--phase","preflight","--out",str(Path(self.temp.name)/"preflight")])
            self.assertEqual(run.call_count,3)
            self.assertEqual({call.args[0]["id"] for call in run.call_args_list},{t["id"] for t in new_protocol["tasks"] if t["phase"]=="preflight"})
            self.assertTrue(all(call.kwargs["agent_policy"] == "v0.2" for call in run.call_args_list))
            self.assertTrue(all(call.kwargs["model_config"] == new_protocol["model"] for call in run.call_args_list))

    def test_source_identity_covers_runtime_workflow_and_dependency(self):
        def git(*args):
            return "a"*40
        with patch.object(r,"git_value",side_effect=git):
            source=r.source_identity(self.protocol_path)
        self.assertEqual(set(source["files"]),{"tools/tool_agent_reliability.py","research/tool-agent-reliability/protocol-v0.1.json","scripts/workflow_efficacy_start_ollama.sh","tools/workflow_efficacy_free_agent.py",".github/workflows/far-tool-agent-reliability.yml"})


class PolicyV02Tests(unittest.TestCase):
    def setUp(self):
        self.protocol_path = r.ROOT / "research/tool-agent-reliability/protocol-v0.2.json"
        self.protocol = r.load_protocol(self.protocol_path)
        self.protocol_sha = r.sha(self.protocol_path.read_bytes())
        self.task = copy.deepcopy(next(t for t in self.protocol["tasks"] if t["phase"] == "preflight"))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / "successor.json"

    def run_successor(self):
        actions = [action("read_file",path=path) for path in self.task["oracle"]["required_reads"]]
        actions.append(action("finish",answer=self.task["oracle"]["answer"]))
        return r.run_task(self.task,0,self.protocol_sha,SOURCE,self.out,provider=provider(actions),digest=r.MODEL_DIGEST,agent_policy="v0.2")

    def test_successor_default_and_policy_in_every_request(self):
        self.assertEqual(self.protocol_path.name,"protocol-v0.2.json")
        self.assertEqual(r.policy_for_protocol(self.protocol),"v0.2")
        result = self.run_successor()
        self.assertEqual(result["agent_policy"],"v0.2")
        self.assertEqual(result["system_sha256"],r.sha(r.SYSTEM_V02.encode()))
        for event in result["events"]:
            request = json.loads(event["request_utf8"])
            self.assertEqual(request["messages"][0]["content"],r.SYSTEM_V02)
            self.assertNotIn("oracle",event["request_utf8"])
        first_user = json.loads(result["events"][0]["request_utf8"])["messages"][1]["content"]
        for content in self.task["files"].values():
            self.assertNotIn(content,first_user)
        r.replay(result,self.task,self.protocol_sha,SOURCE,allow_synthetic=True,agent_policy="v0.2")

    def test_legacy_system_is_preserved_and_successor_only_appends(self):
        old=r.load_protocol(r.ROOT / "research/tool-agent-reliability/protocol-v0.1.json")
        self.assertEqual(r.policy_for_protocol(old),"v0.1")
        self.assertEqual(r.initial_messages(self.task,"v0.1")[0]["content"],r.SYSTEM)
        self.assertTrue(r.SYSTEM_V02.startswith(r.SYSTEM+"\n"))
        self.assertIn("no extra output files",r.SYSTEM_V02)
        self.assertIn('"answer":214',r.SYSTEM_V02)
        self.assertNotIn("no extra output files",r.SYSTEM)

    def test_policy_metadata_and_raw_prompt_drift_are_rejected(self):
        result=self.run_successor()
        for change in (lambda x:x.update(agent_policy="v0.1"),lambda x:x.update(system_sha256="0"*64),lambda x:x.pop("agent_policy"),lambda x:x.pop("system_sha256")):
            bad=copy.deepcopy(result);change(bad)
            with self.assertRaisesRegex(ValueError,"policy identity"):
                r.replay(bad,self.task,self.protocol_sha,SOURCE,allow_synthetic=True,agent_policy="v0.2")
        bad=copy.deepcopy(result)
        request=json.loads(bad["events"][0]["request_utf8"])
        request["messages"][0]["content"]=r.SYSTEM
        raw=r.encoded(request)
        bad["events"][0].update(request_utf8=raw.decode(),request_sha256=r.sha(raw))
        with self.assertRaisesRegex(ValueError,"request/prompt drift"):
            r.replay(bad,self.task,self.protocol_sha,SOURCE,allow_synthetic=True,agent_policy="v0.2")
        with self.assertRaisesRegex(ValueError,"policy identity"):
            r.replay(result,self.task,self.protocol_sha,SOURCE,allow_synthetic=True,agent_policy="v0.1")

    def test_analysis_uses_protocol_policy_and_never_coerces_answer(self):
        task=copy.deepcopy(next(t for t in self.protocol["tasks"] if t["phase"] == "preflight" and "calculator" in t["oracle"]["required_tools"]))
        steps=[action("read_file",path=path) for path in task["oracle"]["required_reads"]]
        steps.extend([action("calculator",expression=str(task["oracle"]["answer"])),action("finish",answer=str(task["oracle"]["answer"]))])
        result=r.run_task(task,0,self.protocol_sha,SOURCE,self.out,provider=provider(steps),digest=r.MODEL_DIGEST,agent_policy="v0.2")
        report=r.analyze(self.protocol,[result],self.protocol_sha,SOURCE,phase="preflight",allow_synthetic=True)
        self.assertEqual(report["replayed_records"],1)
        self.assertEqual(report["passed"],0)
        self.assertFalse(result["grade"]["checks"]["answer"])
        self.assertFalse(report["preflight_gate_passed"])

    def test_successor_source_identity_uses_successor_workflow(self):
        with patch.object(r,"git_value",return_value="a"*40):
            source=r.source_identity(self.protocol_path)
        self.assertIn(".github/workflows/far-tool-agent-reliability-v02.yml",source["files"])
        self.assertIn("research/tool-agent-reliability/protocol-v0.2.json",source["files"])
        self.assertNotIn(".github/workflows/far-tool-agent-reliability.yml",source["files"])

    def test_current_cli_refuses_historical_live_execution_before_source_or_provider(self):
        path=r.ROOT / "research/tool-agent-reliability/protocol-v0.1.json"
        with patch.object(r,"source_identity",side_effect=AssertionError("must refuse first")),patch.object(r,"installed_digest",side_effect=AssertionError("must not inspect provider")):
            with self.assertRaises(SystemExit):
                r.main(["run","--protocol",str(path),"--phase","preflight","--out",str(self.out)])

    def test_unknown_policy_rejected_without_provider_access(self):
        bad=copy.deepcopy(self.protocol);bad["agent_policy"]="future-unreviewed"
        with self.assertRaisesRegex(ValueError,"unknown agent policy"):
            r.validate_protocol(bad)
        with patch.object(r,"installed_digest",side_effect=AssertionError("must not inspect provider")):
            with self.assertRaisesRegex(ValueError,"unknown agent policy"):
                r.run_task(self.task,0,self.protocol_sha,SOURCE,self.out,agent_policy="future-unreviewed")


class ModelV03Tests(unittest.TestCase):
    def setUp(self):
        self.protocol = r.load_protocol()
        self.protocol_sha = r.sha(r.DEFAULT_PROTOCOL.read_bytes())
        self.model = r.model_for_protocol(self.protocol)
        self.task = copy.deepcopy(next(t for t in self.protocol["tasks"] if t["phase"] == "preflight"))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / "larger-model.json"

    def run_model(self, backend_model=None):
        steps=[action("read_file",path=path) for path in self.task["oracle"]["required_reads"]]
        steps.append(action("finish",answer=self.task["oracle"]["answer"]))
        return r.run_task(self.task,0,self.protocol_sha,SOURCE,self.out,provider=provider(steps,model=backend_model or r.MODEL_7B),digest=r.MODEL_DIGEST_7B,agent_policy="v0.2",model_config=self.model)

    def test_seven_billion_default_is_exact_allowlisted_model(self):
        self.assertEqual(r.DEFAULT_PROTOCOL.name,"protocol-v0.3.json")
        self.assertEqual(self.protocol["protocol_version"],"0.3")
        self.assertEqual(self.model,{"name":"qwen2.5-coder:7b","digest":"dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364"})
        old=r.load_protocol(r.ROOT / "research/tool-agent-reliability/protocol-v0.2.json")
        self.assertEqual(r.model_for_protocol(old),{"name":r.MODEL,"digest":r.MODEL_DIGEST})
        self.assertEqual([t for t in self.protocol["tasks"] if t["phase"]=="scored"],[t for t in old["tasks"] if t["phase"]=="scored"])

    def test_actual_requests_records_and_replay_bind_seven_billion(self):
        result=self.run_model()
        self.assertEqual(result["model"],self.model)
        self.assertTrue(result["grade"]["passed"])
        for event in result["events"]:
            request=json.loads(event["request_utf8"])
            self.assertEqual(request["model"],r.MODEL_7B)
            self.assertEqual(request["messages"][0]["content"],r.SYSTEM_V02)
        replayed=r.replay(result,self.task,self.protocol_sha,SOURCE,allow_synthetic=True,agent_policy="v0.2",model_config=self.model)
        self.assertTrue(replayed["passed"])
        report=r.analyze(self.protocol,[result],self.protocol_sha,SOURCE,phase="preflight",allow_synthetic=True)
        self.assertEqual(report["model"],self.model)
        self.assertEqual(report["replayed_records"],1)
        self.assertEqual(report["passed"],1)
        self.assertFalse(report["preflight_gate_passed"])

    def test_smaller_model_reply_is_invalid_instead_of_fallback(self):
        result=self.run_model(backend_model=r.MODEL)
        self.assertEqual(result["model"],self.model)
        self.assertEqual(result["terminal_reason"],"PROVIDER_INVALID")
        self.assertFalse(result["valid"])
        replayed=r.replay(result,self.task,self.protocol_sha,SOURCE,allow_synthetic=True,agent_policy="v0.2",model_config=self.model)
        self.assertFalse(replayed["valid"])

    def test_replay_rejects_changed_model_metadata_and_raw_requests(self):
        result=self.run_model()
        with self.assertRaisesRegex(ValueError,"protocol/model mismatch"):
            r.replay(result,self.task,self.protocol_sha,SOURCE,allow_synthetic=True,agent_policy="v0.2")
        bad=copy.deepcopy(result);bad["model"]={"name":r.MODEL,"digest":r.MODEL_DIGEST}
        with self.assertRaisesRegex(ValueError,"protocol/model mismatch"):
            r.replay(bad,self.task,self.protocol_sha,SOURCE,allow_synthetic=True,agent_policy="v0.2",model_config=self.model)
        bad=copy.deepcopy(result)
        request=json.loads(bad["events"][0]["request_utf8"]);request["model"]=r.MODEL
        raw=r.encoded(request);bad["events"][0].update(request_utf8=raw.decode(),request_sha256=r.sha(raw))
        with self.assertRaisesRegex(ValueError,"request/prompt drift"):
            r.replay(bad,self.task,self.protocol_sha,SOURCE,allow_synthetic=True,agent_policy="v0.2",model_config=self.model)

    def test_seven_billion_cannot_use_old_policy_or_mutable_endpoint(self):
        for mutate in (lambda p:p.update(agent_policy="v0.1"),lambda p:p.update(protocol_version="0.2"),lambda p:p["model"].update(name="http://remote.invalid/model"),lambda p:p["model"].update(digest="0"*64),lambda p:p.pop("model")):
            bad=copy.deepcopy(self.protocol);mutate(bad)
            with self.assertRaises(ValueError):r.validate_protocol(bad)
        with patch.object(r,"installed_digest",side_effect=AssertionError("must refuse before registry")):
            with self.assertRaisesRegex(ValueError,"7B requires"):
                r.run_task(self.task,0,self.protocol_sha,SOURCE,self.out,agent_policy="v0.1",model_config=self.model)

    def test_local_registry_lookup_selects_exact_name_and_full_digest(self):
        reply=r.encoded({"models":[{"name":r.MODEL,"digest":r.MODEL_DIGEST},self.model]})
        # Registry items use name/digest, just like the selected model specification.
        from io import BytesIO
        class Reply(BytesIO):
            def __enter__(self):return self
            def __exit__(self,*args):self.close()
        from types import SimpleNamespace
        opened=[]
        def open_local(url,timeout):
            opened.append((url,timeout));return Reply(reply)
        with patch.object(r.urllib.request,"build_opener",return_value=SimpleNamespace(open=open_local)):
            self.assertEqual(r.installed_digest(self.model),r.MODEL_DIGEST_7B)
        self.assertEqual(opened,[("http://127.0.0.1:11434/api/tags",10)])
        for models in ([{"name":r.MODEL_7B,"digest":"0"*64}],[self.model,self.model],[{"name":r.MODEL,"digest":r.MODEL_DIGEST}]):
            with patch.object(r.urllib.request,"build_opener",return_value=SimpleNamespace(open=lambda *a,**kw:Reply(r.encoded({"models":models})))):
                with self.assertRaisesRegex(ValueError,"unpinned or unexpected"):
                    r.installed_digest(self.model)

    def test_source_identity_uses_seven_billion_startup_and_workflow(self):
        with patch.object(r,"git_value",return_value="a"*40):
            source=r.source_identity()
        self.assertEqual(set(source["files"]),{"tools/tool_agent_reliability.py","research/tool-agent-reliability/protocol-v0.3.json","scripts/tool_agent_reliability_start_7b.sh",".github/workflows/far-tool-agent-reliability-v03.yml"})

    def test_current_cli_refuses_both_smaller_predecessor_launches(self):
        with patch.object(r,"source_identity",side_effect=AssertionError("must refuse first")),patch.object(r,"installed_digest",side_effect=AssertionError("must not inspect provider")):
            for version in ("v0.1","v0.2"):
                with self.assertRaises(SystemExit):
                    r.main(["run","--protocol",str(r.ROOT / ("research/tool-agent-reliability/protocol-"+version+".json")),"--phase","preflight","--out",str(self.out)])


if __name__=="__main__":
    unittest.main()
