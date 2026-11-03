import tempfile
import json
import unittest
from pathlib import Path
from tools.workflow_efficacy_local_analysis import analyze
from tools.workflow_efficacy_local_ollama import MODEL, OPTIONS, HARNESS_VERSION, order, instructions, prompt, sha
from tools.workflow_efficacy_internal_fixtures import task, fingerprint
from tests.test_workflow_efficacy_free_agent_analysis import SyntheticCampaign

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

class LocalReplayTests(unittest.TestCase):
    """Fabricated test fixtures exercise validators, never empirical model results."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        source=SyntheticCampaign(self.root/"shared")
        self.rows={}
        for i in range(30):
            for arm in order(i):
                original=source.rows[(i,arm)]
                folder=self.root/(task(i)["task_id"]+"-"+arm)
                folder.mkdir()
                code=(source.evidence(i,arm)/"submitted-solution.py").read_text()
                provider={"model":MODEL,"done":True,"done_reason":"stop","response":code,
                          "prompt_eval_count":100,"eval_count":25}
                trace=(source.evidence(i,arm)/"grader-trace.txt").read_bytes()
                row={"task_id":task(i)["task_id"],"arm":arm,"model":MODEL,"options":OPTIONS,
                     "model_digest":"a"*64,"harness_version":HARNESS_VERSION,
                     "corpus_sha":fingerprint(),"instructions_sha":sha(instructions(arm)),
                     "prompt_sha":sha(prompt(i,arm).encode()),"duration_s":1,
                     "done":True,"done_reason":"stop","provider_error_class":None,
                     "input_tokens":100,"output_tokens":25,"grader_executed":True,
                     "grader_exit_code":original["grader_exit_code"],"outcome":original["outcome"]}
                for filename,data,field in (("model-output.txt",code.encode(),"model_output_sha"),
                    ("solution.py",code.encode(),"solution_sha"),("grade.txt",trace,"grade_sha"),
                    ("provider-response.json",json.dumps(provider).encode(),"provider_response_sha")):
                    (folder/filename).write_bytes(data)
                    row[field]=sha(data)
                self.rows[(i,arm)]=row
            self.save(i)

    def save(self,i):
        (self.root/f"pair-{i:02d}.json").write_text(json.dumps([self.rows[(i,a)] for a in order(i)]))

    def invalid(self,code):
        report=analyze(self.root)
        self.assertEqual(report["status"],"INCOMPLETE_OR_INVALID")
        self.assertTrue(any(code in error for error in report["errors"]),report["errors"])
        self.assertNotIn("paired_delta",report)

    def test_complete_synthetic_fixture_replays_without_model_calls(self):
        report=analyze(self.root)
        self.assertEqual(report["errors"],[])
        self.assertEqual((report["control_success"],report["treatment_success"]),(10,15))

    def test_rehashed_false_pass_is_recomputed_from_retained_outputs(self):
        folder=self.root/(task(1)["task_id"]+"-control")
        path=folder/"grade.txt"
        trace=json.loads(path.read_text())
        trace["success"]=True
        for comparison in trace["comparisons"]:
            comparison["status"]="PASS"
        path.write_text(json.dumps(trace))
        row=self.rows[(1,"control")]
        row.update(outcome="SUCCESS",grader_exit_code=0,grade_sha=sha(path.read_bytes()))
        self.save(1)
        self.invalid("GRADER_COMPARISON_VERDICT_MISMATCH")

    def test_length_finish_with_rehashed_provider_is_incomplete(self):
        folder=self.root/(task(0)["task_id"]+"-control")
        path=folder/"provider-response.json"
        response=json.loads(path.read_text())
        response["done_reason"]="length"
        path.write_text(json.dumps(response))
        self.rows[(0,"control")].update(done_reason="length",provider_response_sha=sha(path.read_bytes()))
        self.save(0)
        self.invalid("UNFINISHED_INFERENCE")

    def test_malformed_digest_and_large_duration_fail_without_crashing(self):
        self.rows[(0,"control")].update(model_digest=[],duration_s=10**400)
        self.save(0)
        self.invalid("INVALID_DURATION")

    def test_duplicate_pair_record_file_is_not_extra_exposure(self):
        (self.root/"pair-30.json").write_bytes((self.root/"pair-00.json").read_bytes())
        self.invalid("WRONG_PAIR_FILE_SET")

if __name__=="__main__":
    unittest.main()
