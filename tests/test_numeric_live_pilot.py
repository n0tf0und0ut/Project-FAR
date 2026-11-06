"""Prospective numeric-model pilot offline controls; these are NOT model runs."""
import copy
import base64
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"research"/"numeric-grounding"
spec=importlib.util.spec_from_file_location("far_numeric_live_pilot", SOURCE/"live_pilot.py")
pilot=importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)
observer=__import__("observe_live")


def provider_call(body, content):
    result={"model":pilot.MODEL,"done":True,"message":{"content":content},
            "prompt_eval_count":10,"eval_count":5}
    raw=pilot.canon(result)
    return {"request":body, "request_sha256":pilot.sha(pilot.canon(body)),
            "response":result, "response_sha256":pilot.sha(raw),
            "raw_response_utf8":raw.decode(), "elapsed_seconds":0.01}


def fixture_pair(p, task, arm):
    messages=pilot.conditions(task,p,arm)
    if arm=="control":
        answer=task["expected"]
        calls=[provider_call(pilot.request(messages,p),json.dumps({"answer":answer}))]
    else:
        first={"tool":"metric","id":pilot.SUPPORTED} if task["answerability"]=="REGISTERED_METRIC" else {"tool":"finish","answer":"UNKNOWN"}
        first_text=pilot.canon(first).decode()
        calls=[provider_call(pilot.request(messages,p),first_text)]
        if task["answerability"]=="REGISTERED_METRIC":
            observation={"metric_observation":{"id":pilot.SUPPORTED,"value":"100.0000",
                         "unit":"percent","scope":"v0.3-scored","status":"REPLAY_VERIFIED"}}
            next_messages=messages+[{"role":"assistant","content":first_text},
                                    {"role":"user","content":pilot.canon(observation).decode()}]
            calls.append(provider_call(pilot.request(next_messages,p),
                            json.dumps({"tool":"finish","answer":"100.0000"})))
    value,reason,used=pilot.predicted(task,arm,calls,{"value":"100.0000"})
    return {"schema":pilot.SCHEMA,"case_id":task["id"],"arm":arm,
            "calls":calls,"released":value,"release_reason":reason,"used_metric":used,
            "model_digest":pilot.MODEL_DIGEST,"protocol_sha256":pilot.sha(pilot.PFILE.read_bytes()),
            "source_archive_sha256":pilot.source_replay.ARCHIVE_SHA256,
            "run_commit":"0"*40}


class NumericLivePilotOfflineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p=pilot.protocol()
        cls.g=pilot.source_replay.grounded_report(asserted_value="100.0000")
        cls.rows=[fixture_pair(cls.p,t,arm) for t in cls.p["tasks"] for arm in ("control","treatment")]

    def test_protocol_frozen_cases_oracles_and_replay_source(self):
        self.assertEqual(len(self.p["tasks"]),16)
        self.assertEqual(self.g["value"],"100.0000")
        self.assertEqual(len(self.rows),32)

    def test_synthetic_replay_exact_counts_and_nonclaims(self):
        report=pilot.analyze(self.p,self.rows,self.g)
        self.assertEqual(report["paired_records"],32)
        self.assertEqual(report["summary"]["control"]["correct"],16)
        self.assertEqual(report["summary"]["treatment"]["correct"],16)
        self.assertEqual(report["summary"]["control"]["wrong_number"],0)
        self.assertEqual(report["trusted_execution_attestation"],"NOT_ESTABLISHED")

    def test_mutation_of_saved_raw_response_fails(self):
        rows=copy.deepcopy(self.rows)
        rows[0]["calls"][0]["raw_response_utf8"]="{}"
        with self.assertRaisesRegex(ValueError,"response-byte mismatch"):
            pilot.analyze(self.p,rows,self.g)

    def test_mutation_of_result_label_fails(self):
        rows=copy.deepcopy(self.rows)
        rows[0]["released"]="0.0000"
        with self.assertRaisesRegex(ValueError,"differs from deterministic replay"):
            pilot.analyze(self.p,rows,self.g)

    def test_missing_eligible_slot_fails_instead_of_reweighting(self):
        with self.assertRaisesRegex(ValueError,"incomplete registered experiment"):
            pilot.analyze(self.p,self.rows[:-1],self.g)

    def test_missing_required_followup_cannot_be_relabelled_as_abstention(self):
        rows=copy.deepcopy(self.rows)
        row=rows[1]
        row["calls"].pop()
        row["released"],row["release_reason"],row["used_metric"]=pilot.predicted(
            self.p["tasks"][0],"treatment",row["calls"],self.g)
        with self.assertRaisesRegex(ValueError,"model-call count"):
            pilot.analyze(self.p,rows,self.g)

    def test_unsolicited_second_call_fails_even_with_consistent_release(self):
        rows=copy.deepcopy(self.rows)
        row=rows[1]
        row["calls"][0]=provider_call(row["calls"][0]["request"],
                                    '{"tool":"finish","answer":"UNKNOWN"}')
        row["calls"][1]["request"]=copy.deepcopy(row["calls"][0]["request"])
        row["calls"][1]["request_sha256"]=row["calls"][0]["request_sha256"]
        row["released"],row["release_reason"],row["used_metric"]=pilot.predicted(
            self.p["tasks"][0],"treatment",row["calls"],self.g)
        with self.assertRaisesRegex(ValueError,"model-call count"):
            pilot.analyze(self.p,rows,self.g)

    def test_analysis_is_independent_of_record_enumeration_order(self):
        self.assertEqual(pilot.analyze(self.p,self.rows,self.g),
                         pilot.analyze(self.p,self.rows[::-1],self.g))

    def test_counterbalanced_run_round_trips_through_standalone_replay(self):
        replies=[]
        for index,task in enumerate(self.p["tasks"]):
            order=("control","treatment") if index%2==0 else ("treatment","control")
            for arm in order:
                replies.extend(fixture_pair(self.p,task,arm)["calls"])
        # Different durations expose order-sensitive floating accumulation too.
        for index,call in enumerate(replies):
            call["elapsed_seconds"]=0.01+index/10000
        def fake_invoke(body,timeout,on_response=None):
            call=replies.pop(0)
            self.assertEqual(body,call["request"])
            return call
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/"evidence"
            with (mock.patch.object(pilot,"local_model_digest",return_value=pilot.MODEL_DIGEST),
                  mock.patch.object(pilot.source_replay,"grounded_report",return_value=self.g),
                  mock.patch.object(pilot,"invoke",side_effect=fake_invoke),
                  mock.patch("builtins.print")):
                self.assertEqual(pilot.run(self.p,output,pilot.FROZEN_LAUNCH_SHA),0)
                self.assertEqual(pilot.main(["analyze","--output",str(output)]),0)
            self.assertEqual(replies,[])

    def test_legacy_saved_order_is_compatible_but_changed_score_is_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)
            rows=copy.deepcopy(self.rows)
            for row in rows:
                row["run_commit"]=pilot.FROZEN_LAUNCH_SHA
                (output/(row["case_id"]+"-"+row["arm"]+".json")).write_bytes(pilot.canon(row))
            saved=pilot.analyze(self.p,rows,self.g)
            saved["outcomes"].reverse()
            (output/"analysis.json").write_bytes(pilot.canon(saved))
            with (mock.patch.object(pilot.source_replay,"grounded_report",return_value=self.g),
                  mock.patch("builtins.print")):
                self.assertEqual(pilot.main(["analyze","--output",str(output)]),0)
                saved["summary"]["treatment"]["correct"]-=1
                (output/"analysis.json").write_bytes(pilot.canon(saved))
                with self.assertRaisesRegex(ValueError,"saved summary differs"):
                    pilot.main(["analyze","--output",str(output)])

    def test_preserved_original_live_artifact_replays_without_model_calls(self):
        # These are the original historical calls, not a newly executed study.
        with (mock.patch.object(observer,"record",side_effect=lambda value:value),
              mock.patch.object(pilot,"invoke",side_effect=AssertionError("no model calls"))):
            result=observer.preserved_observation()
        self.assertEqual(result["artifact_sha256"],observer.PRESERVED_SHA256)
        self.assertEqual(result["status"],"REPLAY_VERIFIED_BOUNDED_RESULT")
        self.assertEqual(result["paired_records"],32)
        self.assertFalse(result["registered_exploratory_gate_passed"])
        self.assertEqual([result["summary"][arm]["wrong_number"] for arm in ("control","treatment")],[0,0])
        self.assertEqual(result["workflow_conclusion"],"failure")

    def test_preserved_artifact_mutation_fails_before_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            changed=Path(tmp)/"archive.b64"
            raw=base64.b64decode(observer.PRESERVED_ARCHIVE.read_bytes().strip(),validate=True)
            changed.write_bytes(base64.b64encode(raw[:-1]+bytes([raw[-1]^1])))
            with (mock.patch.object(observer,"PRESERVED_ARCHIVE",changed),
                  mock.patch.object(observer,"replay_archive") as replay):
                with self.assertRaisesRegex(ValueError,"digest mismatch"):
                    observer.preserved_observation()
                replay.assert_not_called()

    def test_remote_observer_rejects_changed_original_archive(self):
        run={"id":42090379885,"head_sha":observer.FROZEN_LAUNCH_SHA,"event":"push",
             "status":"completed","conclusion":"failure"}
        artifact={"id":13445236161,"name":"numeric-grounding-live-v01-raw-42090379885",
                  "expired":False,"archive_download_url":"https://example.invalid/archive"}
        with (mock.patch.dict("os.environ",{"GH_TOKEN":"offline-test"}),
              mock.patch.object(observer,"fetch",side_effect=[
                  pilot.canon({"workflow_runs":[run]}),pilot.canon({"artifacts":[artifact]}),b"changed"]),
              mock.patch.object(observer,"record",side_effect=lambda value:value),
              mock.patch.object(observer,"replay_archive") as replay):
            result=observer.main(["--remote"])
        self.assertEqual(result["status"],"OBSERVER_ERROR")
        self.assertIn("remote original artifact digest mismatch",result["message"])
        replay.assert_not_called()

    def test_remote_archive_cannot_hide_extra_or_aliased_members(self):
        for member in ("extra.json","nested/../analysis.json","./analysis.json","state.json"):
            with self.subTest(member=member):
                raw=base64.b64decode(observer.PRESERVED_ARCHIVE.read_bytes().strip(),validate=True)
                buffer=io.BytesIO(raw)
                with zipfile.ZipFile(buffer,"a") as archive:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore",UserWarning)
                        archive.writestr(member,b"{}")
                with self.assertRaisesRegex(ValueError,"original artifact members"):
                    observer.replay_archive(buffer.getvalue())

    def test_remote_archive_cannot_claim_incomplete_state_as_verified(self):
        raw=base64.b64decode(observer.PRESERVED_ARCHIVE.read_bytes().strip(),validate=True)
        buffer=io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(raw)) as original,zipfile.ZipFile(buffer,"w") as changed:
            for name in original.namelist():
                value=original.read(name)
                if name=="state.json":
                    state=json.loads(value)
                    state["status"]="INCOMPLETE"
                    value=pilot.canon(state)
                changed.writestr(name,value)
        result=observer.replay_archive(buffer.getvalue())
        self.assertEqual(result["status"],"REPLAY_FAILED")
        self.assertIn("execution state",result["reason"])

    def test_replay_rejects_wrong_schema_and_boolean_integer_alias(self):
        for field,value in (("schema","other-study"),("used_metric",1)):
            rows=copy.deepcopy(self.rows)
            rows[1][field]=value
            with self.assertRaisesRegex(ValueError,"schema or metric-use"):
                pilot.analyze(self.p,rows,self.g)

    def test_unknown_case_refuses_unrelated_source_metric(self):
        task=self.p["tasks"][8]
        first=provider_call(pilot.request(pilot.conditions(task,self.p,"treatment"),self.p),
                            json.dumps({"tool":"metric","id":pilot.SUPPORTED}))
        value,reason,used=pilot.predicted(task,"treatment",[first],self.g)
        self.assertEqual((value,reason,used),("UNKNOWN","UNANSWERABLE_SCOPE",True))

    def test_numeric_finish_without_tool_is_rejected(self):
        task=self.p["tasks"][0]
        first=provider_call(pilot.request(pilot.conditions(task,self.p,"treatment"),self.p),
                            json.dumps({"tool":"finish","answer":"100.0000"}))
        self.assertEqual(pilot.predicted(task,"treatment",[first],self.g),
                         ("UNKNOWN","UNSUPPORTED_ACTION",False))

    def test_replay_rejects_invalid_provider_and_commit(self):
        for change in ({"model":"wrong-model"}, {"done":False}, {"eval_count":-5}):
            rows=copy.deepcopy(self.rows)
            payload=rows[0]["calls"][0]
            payload["response"].update(change)
            raw=pilot.canon(payload["response"])
            payload["raw_response_utf8"]=raw.decode()
            payload["response_sha256"]=pilot.sha(raw)
            with self.assertRaises(ValueError):
                pilot.analyze(self.p,rows,self.g)
        rows=copy.deepcopy(self.rows)
        rows[1]["run_commit"]="f"*40
        with self.assertRaises(ValueError):
            pilot.analyze(self.p,rows,self.g)
        with self.assertRaises(ValueError):
            pilot.analyze(self.p,self.rows,self.g,expected_run_commit="f"*40)

    def test_second_request_timeout_retains_attempt_journal(self):
        replies=['{"answer":"100.0000"}',
                 '{"tool":"metric","id":"v03_registered_success"}']
        counter=[0]
        def fake_invoke(body, timeout, on_response=None):
            counter[0]+=1
            if counter[0]==3:
                raise RuntimeError("timeout after metric request")
            call=provider_call(body,replies[counter[0]-1])
            if on_response:
                on_response(call["raw_response_utf8"].encode(),200,0.01)
            return call
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/"evidence"
            with (mock.patch.object(pilot,"local_model_digest",return_value=pilot.MODEL_DIGEST),
                  mock.patch.object(pilot.source_replay,"grounded_report",return_value=self.g),
                  mock.patch.object(pilot,"invoke",side_effect=fake_invoke)):
                with self.assertRaisesRegex(RuntimeError,"timeout after metric request"):
                    pilot.run(self.p,output,"0"*40)
            state=json.loads((output/"state.json").read_text())
            self.assertEqual(state["status"],"INCOMPLETE")
            self.assertEqual(state["records_attempted"],2)
            self.assertEqual(state["records_completed"],1)
            self.assertEqual(state["provider_calls_started"],3)
            self.assertEqual(state["provider_responses_received"],2)
            self.assertEqual(state["last_arm"],"treatment")
            self.assertTrue((output/"attempts"/"A01-treatment-call2-start.json").exists())
            self.assertFalse((output/"A01-treatment.json").exists())

    def test_wrong_final_metric_is_not_released(self):
        row=copy.deepcopy(self.rows[1])
        data=row["calls"][1]["response"]
        data["message"]["content"]=json.dumps({"tool":"finish","answer":"92.0000"})
        row["calls"][1]["raw_response_utf8"]=pilot.canon(data).decode()
        row["calls"][1]["response_sha256"]=pilot.sha(row["calls"][1]["raw_response_utf8"].encode())
        task=self.p["tasks"][0]
        self.assertEqual(pilot.predicted(task,"treatment",row["calls"],self.g),
                         ("UNKNOWN","FINAL_NOT_SOURCE_VERIFIED",True))


if __name__=="__main__":
    unittest.main()
