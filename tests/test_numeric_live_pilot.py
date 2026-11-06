"""Prospective numeric-model pilot offline controls; these are NOT model runs."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"research"/"numeric-grounding"
spec=importlib.util.spec_from_file_location("far_numeric_live_pilot", SOURCE/"live_pilot.py")
pilot=importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)


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
