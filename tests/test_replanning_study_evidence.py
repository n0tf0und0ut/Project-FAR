"""Mutation and census tests for structural-only evidence replay."""
import copy
import json
import unittest

from tools import replanning_study_evidence as ev
from tools import replanning_study_gate as gate
from tools import replanning_study_runner as runner


def specimen():
    comparisons=[{"group":g,"index":i,"status":"FAILURE"} for g,n in (("public",2),("hidden",4)) for i in range(n)]
    trace=gate.canonical({"schema":"far-isolated-output-grade/1","comparisons":comparisons,
                          "executed":True,"success":False}).decode()
    task={"task_id":"FWE-999","source":"buggy","source_sha256":gate.digest(b"buggy"),"interrupted":False}
    row={"schema":"far-replan-candidate-arm/1","task_id":"FWE-999","arm":"control",
         "provenance":"SYNTHETIC_TEST","model":runner.MODEL,
         "status":"DIAGNOSTIC_ONLY_NOT_INDEPENDENTLY_ATTESTED", "trace_status":"completed",
         "initial_file_sha256":task["source_sha256"],"final_file_sha256":gate.digest(b"buggy"),
         "fault_injected":False,"fault_required":False,"orchestration_result_sha256":["a"*64],
         "model_requests":[],"tool_execution_receipts":[],
         "grade":{"source":"trusted-host-docker-grader","executed":True,"success":False,
                  "exit_status":1,"trace_sha256":gate.digest(trace.encode()),"trace":trace},
         "usage":{"model_tokens":0,"tool_calls":0,"wall_seconds":0.0},
         "not_scored_reason":"External evaluator not present"}
    return task,row


class StructuralReplayTests(unittest.TestCase):
    def setUp(self):
        self.task,self.row=specimen()

    def check(self,row=None,task=None):
        return ev.verify_arm(self.row if row is None else row,self.task if task is None else task,"control")

    def test_genuine_synthetic_result_is_never_independently_attested(self):
        a=self.check()
        self.assertTrue(a["structurally_consistent"])
        self.assertIsNone(a["independently_attested_success"])
        self.assertFalse(a["grader_claimed_success"])

    def test_provenance_cannot_promote_to_verified(self):
        for status in ("VERIFIED", "SUCCEEDED", "SCORED"):
            row=copy.deepcopy(self.row);row["status"]=status
            with self.assertRaises(ev.EvidenceError):self.check(row)

    def test_unauthorized_model_identity(self):
        row=copy.deepcopy(self.row);row["model"]["digest"]="0"*64
        with self.assertRaisesRegex(ev.EvidenceError,"model manifest"):self.check(row)

    def test_unauthorized_source_or_arm(self):
        for key,value in (("task_id","FWE-001"),("arm","replanning"),("initial_file_sha256","a"*64)):
            row=copy.deepcopy(self.row);row[key]=value
            with self.assertRaises(ev.EvidenceError):self.check(row)

    def test_grade_trace_tamper_detected(self):
        row=copy.deepcopy(self.row);row["grade"]["trace"]+=" "
        with self.assertRaisesRegex(ev.EvidenceError,"grader trace hash"):self.check(row)

    def test_grade_cannot_claim_success_without_six_passes(self):
        row=copy.deepcopy(self.row)
        tr=json.loads(row["grade"]["trace"]);tr["success"]=True
        raw=gate.canonical(tr).decode();row["grade"].update(success=True,exit_status=0,trace=raw,trace_sha256=gate.digest(raw.encode()))
        with self.assertRaisesRegex(ev.EvidenceError,"self-contradicting grade"):self.check(row)

    def test_grade_rejects_missing_hidden_test_cases(self):
        row=copy.deepcopy(self.row)
        tr=json.loads(row["grade"]["trace"]);tr["comparisons"].pop()
        raw=gate.canonical(tr).decode();row["grade"].update(trace=raw,trace_sha256=gate.digest(raw.encode()))
        with self.assertRaisesRegex(ev.EvidenceError,"comparison inventory"):self.check(row)

    def test_grade_must_not_hide_infrastructure_failure(self):
        row=copy.deepcopy(self.row)
        tr=json.loads(row["grade"]["trace"]);tr["comparisons"][0]["status"]="INFRA_FAILURE"
        raw=gate.canonical(tr).decode();row["grade"].update(trace=raw,trace_sha256=gate.digest(raw.encode()))
        with self.assertRaisesRegex(ev.EvidenceError,"self-contradicting grade"):self.check(row)

    def test_unapproved_tool_receipt_rejected(self):
        row=copy.deepcopy(self.row)
        action={"action":"exec","cmd":"rm -rf /"}
        row["tool_execution_receipts"]=[{"action":action,"tool_number":1,
                                         "result":{"ok":True},"receipt_sha256":gate.digest(b"fake")}]
        row["usage"]["tool_calls"]=1
        with self.assertRaisesRegex(ev.EvidenceError,"unapproved tool receipt|no corresponding model action"):self.check(row)

    def test_tool_receipt_mutation_detected(self):
        row=copy.deepcopy(self.row)
        action={"action":"finish"}
        result={"finished":True}
        bound=gate.digest(gate.canonical({"action":action,"result":result,"tool_number":1}))
        row["tool_execution_receipts"]=[{"action":action,"tool_number":1,"result":result,"receipt_sha256":bound}]
        row["usage"]["tool_calls"]=1
        # The matching synthetic model response and receipt are bound together.
        from base64 import b64encode
        model_response=gate.canonical({"model":runner.MODEL["name"], "done":True,
            "message":{"content":gate.canonical(action).decode()}, "prompt_eval_count":0,"eval_count":0})
        model_request=gate.canonical({"model":runner.MODEL["name"]})
        row["model_requests"]=[{"kind":"synthetic_provider_test","purpose":"worker",
            "request_base64":b64encode(model_request).decode(),"request_sha256":gate.digest(model_request),
            "response_base64":b64encode(model_response).decode(),"response_sha256":gate.digest(model_response),
            "http_status":200,"error":None}]
        self.check(row)
        row["tool_execution_receipts"][0]["result"]["finished"]=False
        with self.assertRaisesRegex(ev.EvidenceError,"invalid finish receipt|tool execution receipt modified"):self.check(row)

    def test_tool_receipt_numbering_and_usage_reconciled(self):
        row=copy.deepcopy(self.row);row["usage"]["tool_calls"]=1
        with self.assertRaisesRegex(ev.EvidenceError,"tool budget/trace"):self.check(row)

    def test_token_wall_budget_violations_fail(self):
        for key,value in (("model_tokens",15001),("model_tokens",True),("wall_seconds",2700.1),
                          ("wall_seconds",-0.1),("tool_calls",True)):
            row=copy.deepcopy(self.row);row["usage"][key]=value
            with self.assertRaises(ev.EvidenceError):self.check(row)

    def test_fault_schedule_cannot_change_after_freeze(self):
        row=copy.deepcopy(self.row);row["fault_required"]=True
        with self.assertRaisesRegex(ev.EvidenceError,"frozen interruption changed"):self.check(row)

    def test_source_and_result_hashes_are_required(self):
        row=copy.deepcopy(self.row);row["orchestration_result_sha256"]=["bad"]
        with self.assertRaisesRegex(ev.EvidenceError,"orchestration result binding"):self.check(row)

    def test_24_missing_slots_are_preserved_in_original_denominator(self):
        tasks=[{"task_id":f"FWE-{i:03d}","source_sha256":"a"*64,"interrupted":False} for i in range(1,13)]
        schedule=[{"slot":i*2+arm_index+1,"task_id":task["task_id"],"arm":arm}
                  for i,task in enumerate(tasks) for arm_index,arm in enumerate(("control","replanning"))]
        result=ev.analyze({"task_rows":tasks},{},schedule)
        self.assertEqual(result["denominator_pairs"],12)
        self.assertEqual(result["records_missing"],24)
        self.assertIsNone(result["paired_verified_completion_difference"])
        self.assertEqual(result["status"],"NOT_ESTABLISHED_NO_INDEPENDENT_RECEIPT_ATTESTATION")

    def test_unauthorized_extra_slot_and_duplicate_slot_refused(self):
        tasks=[{"task_id":f"FWE-{i:03d}","source_sha256":"a"*64,"interrupted":False} for i in range(1,13)]
        schedule=[{"slot":i*2+arm_index+1,"task_id":task["task_id"],"arm":arm}
                  for i,task in enumerate(tasks) for arm_index,arm in enumerate(("control","replanning"))]
        with self.assertRaisesRegex(ev.EvidenceError,"unregistered extra receipt"):
            ev.analyze({"task_rows":tasks},{"slot-25":{}},schedule)
        schedule[0]["slot"]=2
        with self.assertRaisesRegex(ev.EvidenceError,"slot order invalid"):
            ev.analyze({"task_rows":tasks},{},schedule)

    def test_wrong_provider_trace_not_a_valid_result(self):
        row=copy.deepcopy(self.row);row["provenance"]="INDEPENDENTLY_GRADED"
        with self.assertRaises(ev.EvidenceError):self.check(row)

    def test_model_request_raw_digest_detects_replacement(self):
        row=copy.deepcopy(self.row)
        raw=gate.canonical({"model":runner.MODEL["name"]})
        row["model_requests"]=[{"kind":"synthetic_provider_test","purpose":"worker",
            "request_base64":__import__('base64').b64encode(raw).decode(),
            "request_sha256":"f"*64,"response_base64":None,
            "response_sha256":None,"http_status":None,"error":None}]
        with self.assertRaisesRegex(ev.EvidenceError,"digest mismatch"):self.check(row)


    def test_fault_flags_must_match_schedule_and_first_write_only(self):
        row=copy.deepcopy(self.row)
        action={"action":"write_file","path":"solution.py","content":"correct"}
        result={"error":"INJECTED_TRANSIENT_WRITE_FAILURE","executed":False}
        row["tool_execution_receipts"]=[{"action":action,"tool_number":1,"result":result,
              "receipt_sha256":gate.digest(gate.canonical({"action":action,"tool_number":1,"result":result}))}]
        row["usage"]["tool_calls"]=1
        from base64 import b64encode
        req=gate.canonical({"model":runner.MODEL["name"]})
        resp=gate.canonical({"model":runner.MODEL["name"],"done":True,
             "message":{"content":gate.canonical(action).decode()},"prompt_eval_count":0,"eval_count":0})
        row["model_requests"]=[{"kind":"synthetic_provider_test","purpose":"worker",
            "request_base64":b64encode(req).decode(),"request_sha256":gate.digest(req),
            "response_base64":b64encode(resp).decode(),"response_sha256":gate.digest(resp),
            "http_status":200,"error":None}]
        with self.assertRaisesRegex(ev.EvidenceError,"unscheduled"):self.check(row)
        row["fault_required"]=True
        row["fault_injected"]=True
        task={**self.task,"interrupted":True}
        self.assertTrue(self.check(row,task)["structurally_consistent"])

    def test_final_source_digest_must_match_replayed_writes(self):
        row=copy.deepcopy(self.row);row["final_file_sha256"]="e"*64
        with self.assertRaisesRegex(ev.EvidenceError,"final source digest"):self.check(row)

    def test_nonobject_model_request_is_invalid_without_crashing_census(self):
        row=copy.deepcopy(self.row)
        import base64
        raw=b'[]'
        row["model_requests"]=[{"kind":"synthetic_provider_test","purpose":"worker",
            "request_base64":base64.b64encode(raw).decode(),"request_sha256":gate.digest(raw),
            "response_base64":None,"response_sha256":None,"http_status":None,"error":None}]
        with self.assertRaisesRegex(ev.EvidenceError,"model request must be a JSON object"):self.check(row)

    def test_worker_model_action_must_match_tool_receipt(self):
        row=copy.deepcopy(self.row)
        import base64
        request=gate.canonical({"model":runner.MODEL["name"]})
        response=gate.canonical({"model":runner.MODEL["name"],"done":True,
            "message":{"content":gate.canonical({"action":"finish"}).decode()},
            "prompt_eval_count":0,"eval_count":0})
        row["model_requests"]=[{"kind":"synthetic_provider_test","purpose":"worker",
            "request_base64":base64.b64encode(request).decode(),"request_sha256":gate.digest(request),
            "response_base64":base64.b64encode(response).decode(),"response_sha256":gate.digest(response),
            "http_status":200,"error":None}]
        action={"action":"list_files"};result={"files":["solution.py"]}
        row["tool_execution_receipts"]=[{"action":action,"tool_number":1,"result":result,
            "receipt_sha256":gate.digest(gate.canonical({"action":action,"tool_number":1,"result":result}))}]
        row["usage"]["tool_calls"]=1
        with self.assertRaisesRegex(ev.EvidenceError,"decoded worker response"):self.check(row)

    def test_grader_status_must_be_known(self):
        row=copy.deepcopy(self.row)
        trace=json.loads(row["grade"]["trace"])
        del trace["comparisons"][0]["status"]
        raw=gate.canonical(trace).decode()
        row["grade"].update(trace=raw,trace_sha256=gate.digest(raw.encode()))
        with self.assertRaisesRegex(ev.EvidenceError,"grader comparison status"):self.check(row)


if __name__=="__main__":unittest.main()
