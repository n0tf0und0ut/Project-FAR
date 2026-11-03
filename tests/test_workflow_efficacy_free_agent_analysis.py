"""Synthetic validation evidence only: this suite never calls a model provider."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.workflow_efficacy_free_agent import (
    CANDIDATE_STARTED, HARNESS_VERSION, MAX_CANDIDATE_OUTPUT_BYTES,
    MODEL, MODEL_DIGEST, instructions, order_for,
)
from tools.workflow_efficacy_internal_fixtures import fingerprint, task
from tools.workflow_efficacy_free_agent_analysis import (
    COMPLETE, OBSERVATION_SCHEMA, analyze, execution_commit,
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


class SyntheticCampaign:
    """A complete, explicitly fabricated sample for analyzer mutation tests."""
    def __init__(self, root):
        self.root = root
        self.rows = {}
        commit, corpus = execution_commit(), fingerprint()
        arm_hashes = {arm: digest(instructions(arm)) for arm in ("control", "treatment")}
        for index in range(30):
            case = task(index)
            for arm in order_for(index):
                success = index % (3 if arm == "control" else 2) == 0
                # Synthetic successful source covers the six fixture inputs;
                # these are validation artifacts, never scientific observations.
                source = "def transform(d):\n"
                if success:
                    for example in case["public"] + case["hidden"]:
                        source += f"    if d == {example['input']!r}: return {example['expected']!r}\n"
                source += "    return None\n"
                raw = {"model": MODEL.removeprefix("ollama/"), "done": True,
                       "message": {"role": "assistant", "content": source},
                       "prompt_eval_count": 100 if arm == "control" else 150,
                       "eval_count": 25}
                comparisons = []
                for group in ("public", "hidden"):
                    for i, example in enumerate(case[group]):
                        stdout = json.dumps(example["expected"] if success else None)
                        stderr = CANDIDATE_STARTED + "\n"
                        comparisons.append({"group": group, "index": i,
                            "status": "PASS" if success else "FAILURE", "exit_code": 0,
                            "stdout": stdout, "stderr": stderr,
                            "stdout_bytes_observed": len(stdout.encode()),
                            "stderr_bytes_observed": len(stderr.encode()),
                            "timed_out": False, "output_limited": False})
                trace = {"schema": "far-isolated-output-grade/1",
                         "comparisons": comparisons, "executed": True, "success": success}
                row = {"schema": OBSERVATION_SCHEMA, "task_id": case["task_id"], "arm": arm,
                       "execution_commit": commit, "corpus_hash": corpus,
                       "instructions_sha256": arm_hashes[arm], "model_alias": MODEL,
                       "model_digest": MODEL_DIGEST, "harness_version": HARNESS_VERSION,
                       "source_before_sha256": digest(case["source"].encode()),
                       "elapsed_seconds": 1 if arm == "control" else 2,
                       "model_steps": 1, "error_events": 0, "timeout": False,
                       "cli_exit_code": 0, "reported_cost_usd": 0.0,
                       "input_tokens": raw["prompt_eval_count"], "output_tokens": raw["eval_count"],
                       "patch_parsed": True, "unauthorized_changes": [],
                       "grader_status": "EXECUTED", "grader_exit_code": 0 if success else 1,
                       "outcome": "SUCCESS" if success else "FAILURE"}
                self.rows[(index, arm)] = row
                self.artifact(index, arm, "submitted-solution.py", source.encode())
                self.artifact(index, arm, "agent-events.ndjson", raw)
                self.artifact(index, arm, "grader-trace.txt", trace)
            self.save(index)

    def evidence(self, index, arm):
        return self.root / "evidence" / (task(index)["task_id"] + "-" + arm)

    def artifact(self, index, arm, filename, value):
        data = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True).encode()
        folder = self.evidence(index, arm)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / filename).write_bytes(data)
        field = {"submitted-solution.py": "source_after_sha256",
                 "agent-events.ndjson": "raw_event_stream_sha256",
                 "grader-trace.txt": "grader_trace_hash"}[filename]
        self.rows[(index, arm)][field] = digest(data)

    def load(self, index, arm, filename):
        return json.loads((self.evidence(index, arm) / filename).read_text())

    def save(self, index):
        (self.root / f"pair-{index}.json").write_text(json.dumps(
            [self.rows[(index, arm)] for arm in order_for(index)]))


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.sample = SyntheticCampaign(self.root)

    def assertInvalid(self, code):
        report = analyze(self.root)
        self.assertEqual(report["status"], "INCOMPLETE_OR_INVALID")
        self.assertEqual(report["claim"], "NO_VALID_EFFECT_ESTIMATE")
        self.assertTrue(any(code in error for error in report["errors"]), report["errors"])
        self.assertNotIn("paired_success_delta", report)

    def test_complete_valid_sample_has_exact_descriptive_result(self):
        report = analyze(self.root)
        self.assertEqual(report["status"], COMPLETE, report["errors"])
        self.assertEqual(report["observed_records"], 60)
        self.assertEqual(report["control_success"], 10)
        self.assertEqual(report["treatment_success"], 15)
        self.assertAlmostEqual(report["paired_success_delta"], 5 / 30)
        self.assertEqual(report["discordant_treatment_wins"], 10)
        self.assertEqual(report["discordant_control_wins"], 5)
        self.assertEqual(report["mean_generation_elapsed_delta_seconds"], 1)
        self.assertEqual(report["mean_input_token_delta"], 50)
        self.assertFalse(report["population_efficacy_established"])
        self.assertFalse(report["historical_pr_comparison_executed"])
        self.assertIn("shared task families", report["statistical_diagnostic_limits"])

    def test_empty_folder_is_not_execution(self):
        with tempfile.TemporaryDirectory() as empty:
            report = analyze(empty)
        self.assertEqual(report["status"], "INCOMPLETE_OR_INVALID")
        self.assertIn("WRONG_PAIR_FILE_COUNT", report["errors"])

    def test_summary_metadata_mutations_fail_closed(self):
        row = self.sample.rows[(0, "control")]
        original = copy.deepcopy(row)
        mutations = (
            ("schema", "future/999", "UNKNOWN_OBSERVATION_SCHEMA"),
            ("execution_commit", "0" * 40, "EXECUTION_COMMIT_MISMATCH"),
            ("model_digest", MODEL_DIGEST[:12] + "0" * 52, "UNPINNED_LOCAL_MODEL_DIGEST"),
            ("model_alias", "other/model", "MODEL_OR_HARNESS_ALIAS_DRIFT"),
            ("harness_version", "future", "MODEL_OR_HARNESS_ALIAS_DRIFT"),
            ("instructions_sha256", "0" * 64, "SNAPSHOT_MISMATCH"),
            ("source_before_sha256", "0" * 64, "STARTER_SOURCE_MISMATCH"),
            ("model_steps", 0, "NOT_EXACTLY_ONE_MODEL_STEP"),
            ("model_steps", True, "NOT_EXACTLY_ONE_MODEL_STEP"),
            ("model_steps", 2, "NOT_EXACTLY_ONE_MODEL_STEP"),
            ("error_events", 1, "INCOMPLETE_PROVIDER_SESSION"),
            ("timeout", True, "INCOMPLETE_MODEL_EXECUTION"),
            ("cli_exit_code", False, "INCOMPLETE_MODEL_EXECUTION"),
            ("reported_cost_usd", 1, "NONFREE_OR_INVALID_MODEL_CHARGE"),
            ("elapsed_seconds", -1, "INVALID_NUMERIC_METRIC"),
            ("elapsed_seconds", "fast", "INVALID_NUMERIC_METRIC"),
            ("elapsed_seconds", 10 ** 400, "INVALID_NUMERIC_METRIC"),
            ("input_tokens", True, "INVALID_TOKEN_COUNT"),
            ("output_tokens", 0, "INVALID_TOKEN_COUNT"),
            ("patch_parsed", False, "PATCH_PARSE_MISMATCH"),
            ("unauthorized_changes", "README.md", "INVALID_UNAUTHORIZED_CHANGE_RECORD"),
            ("grader_status", "INFRA_FAILURE", "MISSING_OR_UNEXECUTED_GRADER"),
            ("grader_exit_code", 1, "GRADER_RECORD_MISMATCH"),
            ("outcome", "FAILURE", "OUTCOME_EVIDENCE_MISMATCH"),
        )
        for field, value, error in mutations:
            with self.subTest(field=field, value=value):
                row.clear(); row.update(copy.deepcopy(original)); row[field] = value
                self.sample.save(0)
                self.assertInvalid(error)

    def test_reversed_or_cross_task_pair_is_rejected(self):
        path = self.root / "pair-0.json"
        values = json.loads(path.read_text())
        path.write_text(json.dumps(values[::-1]))
        self.assertInvalid("PAIR_IDENTITY_OR_ORDER_MISMATCH")
        values[0]["task_id"] = "FWE-002"
        path.write_text(json.dumps(values))
        self.assertInvalid("PAIR_IDENTITY_OR_ORDER_MISMATCH")

    def test_missing_duplicate_and_nonobject_records_are_rejected(self):
        path = self.root / "pair-0.json"
        row = self.sample.rows[(0, "control")]
        path.write_text(json.dumps([row, row]))
        self.assertInvalid("DUPLICATE_RUN")
        path.write_text(json.dumps([[], None]))
        self.assertInvalid("INVALID_RECORD_TYPE")
        path.unlink()
        self.assertInvalid("MISSING_EXPERIMENT_SLOTS")

    def test_invalid_nonfinite_and_ambiguous_json_is_rejected(self):
        path = self.root / "pair-0.json"
        for text in ("not JSON", '[{"a":NaN},{}]', '[{"a":1,"a":2},{}]'):
            with self.subTest(text=text):
                path.write_text(text)
                self.assertInvalid("INVALID_PAIR_FILE")

    def test_raw_provider_response_mutations_are_rejected_with_valid_hash(self):
        original = self.sample.load(0, "control", "agent-events.ndjson")
        mutations = ({}, {"done": False}, {"model": "wrong"},
                     {"eval_count": 0}, {"prompt_eval_count": 101},
                     {"eval_count": True}, {"error": "rate limited"},
                     {"message": {"content": None}})
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                raw = copy.deepcopy(original); raw.update(mutation)
                self.sample.artifact(0, "control", "agent-events.ndjson", {} if mutation == {} else raw)
                self.sample.save(0)
                self.assertInvalid("INVALID_OR_UNRECONCILED_PROVIDER_RESPONSE")

    def test_source_and_response_must_match_beyond_hashes(self):
        self.sample.artifact(0, "control", "submitted-solution.py", b"def transform(d): return None\n")
        self.sample.save(0)
        self.assertInvalid("SUBMISSION_PROVIDER_RESPONSE_MISMATCH")

    def test_missing_or_hash_mismatched_evidence_is_rejected(self):
        path = self.sample.evidence(0, "control") / "agent-events.ndjson"
        path.write_text("{}")
        self.assertInvalid("REPLAY_ARTIFACT_HASH_MISMATCH")
        path.unlink()
        self.assertInvalid("MISSING_REPLAY_ARTIFACT")

    def test_grader_mutations_are_rejected_even_after_rehashing(self):
        original = self.sample.load(0, "control", "grader-trace.txt")
        for kind in ("schema", "missing", "order", "skip", "missing_marker", "wrong_output", "summary"):
            with self.subTest(kind=kind):
                trace = copy.deepcopy(original)
                if kind == "schema": trace["schema"] = "future/2"
                elif kind == "missing": trace["comparisons"].pop()
                elif kind == "order": trace["comparisons"].reverse()
                elif kind == "skip": trace["comparisons"][0]["status"] = "SKIPPED"
                elif kind == "missing_marker": trace["comparisons"][0]["stderr"] = ""
                elif kind == "wrong_output": trace["comparisons"][0]["stdout"] = "null"
                elif kind == "summary": trace["success"] = False
                self.sample.artifact(0, "control", "grader-trace.txt", trace)
                self.sample.save(0)
                self.assertInvalid("GRADER")

    def test_started_resource_limit_is_measured_failure(self):
        row = self.sample.rows[(0, "control")]
        trace = self.sample.load(0, "control", "grader-trace.txt")
        trace["comparisons"][0].update(status="RESOURCE_LIMIT", exit_code=None,
                                       timed_out=True)
        trace["success"] = False
        row.update(outcome="FAILURE", grader_exit_code=1)
        self.sample.artifact(0, "control", "grader-trace.txt", trace)
        self.sample.save(0)
        report = analyze(self.root)
        self.assertEqual(report["status"], COMPLETE, report["errors"])
        self.assertEqual(report["control_success"], 9)

    def test_started_output_limit_is_measured_failure(self):
        row = self.sample.rows[(0, "control")]
        trace = self.sample.load(0, "control", "grader-trace.txt")
        trace["comparisons"][0].update(
            status="OUTPUT_LIMIT", exit_code=None, output_limited=True,
            stdout="x" * MAX_CANDIDATE_OUTPUT_BYTES,
            stdout_bytes_observed=MAX_CANDIDATE_OUTPUT_BYTES + 1)
        trace["success"] = False
        row.update(outcome="FAILURE", grader_exit_code=1)
        self.sample.artifact(0, "control", "grader-trace.txt", trace)
        self.sample.save(0)
        report = analyze(self.root)
        self.assertEqual(report["status"], COMPLETE, report["errors"])
        self.assertEqual(report["control_success"], 9)

    def test_stdout_startup_marker_is_trusted_and_removed_once(self):
        trace = self.sample.load(0, "control", "grader-trace.txt")
        comparison = trace["comparisons"][0]
        comparison["stdout"] = CANDIDATE_STARTED + "\n" + comparison["stdout"]
        comparison.update(stderr="", stderr_bytes_observed=0,
                          stdout_bytes_observed=len(comparison["stdout"].encode()))
        self.sample.artifact(0, "control", "grader-trace.txt", trace)
        self.sample.save(0)
        report = analyze(self.root)
        self.assertEqual(report["status"], COMPLETE, report["errors"])
        comparison["stdout"] = CANDIDATE_STARTED + "\n" + comparison["stdout"]
        comparison["stdout_bytes_observed"] = len(comparison["stdout"].encode())
        self.sample.artifact(0, "control", "grader-trace.txt", trace)
        self.sample.save(0)
        self.assertInvalid("GRADER_COMPARISON_VERDICT_MISMATCH")

    def test_output_and_time_limit_evidence_is_validated(self):
        original = self.sample.load(0, "control", "grader-trace.txt")
        mutations = (
            ({"stdout_bytes_observed": -1}, "INVALID_GRADER_OUTPUT_COUNTS"),
            ({"stderr_bytes_observed": True}, "INVALID_GRADER_OUTPUT_COUNTS"),
            ({"timed_out": True}, "GRADER_LIMIT_EVIDENCE_MISMATCH"),
            ({"output_limited": None}, "GRADER_LIMIT_EVIDENCE_MISMATCH"),
            ({"stdout_bytes_observed": MAX_CANDIDATE_OUTPUT_BYTES + 1}, "GRADER_LIMIT_EVIDENCE_MISMATCH"),
            ({"status": "OUTPUT_LIMIT", "exit_code": None}, "GRADER_LIMIT_EVIDENCE_MISMATCH"),
            ({"status": "OUTPUT_LIMIT", "exit_code": None, "output_limited": True}, "GRADER_LIMIT_EVIDENCE_MISMATCH"),
            ({"status": "OUTPUT_LIMIT", "exit_code": 0, "output_limited": True,
              "stdout_bytes_observed": MAX_CANDIDATE_OUTPUT_BYTES + 1}, "INVALID_LIMIT_EXIT_CODE"),
            ({"status": "RESOURCE_LIMIT", "exit_code": None}, "GRADER_LIMIT_EVIDENCE_MISMATCH"),
            ({"status": "RESOURCE_LIMIT", "exit_code": None, "timed_out": True,
              "stderr_bytes_observed": MAX_CANDIDATE_OUTPUT_BYTES + 1}, "GRADER_LIMIT_EVIDENCE_MISMATCH"),
        )
        for mutation, error in mutations:
            with self.subTest(mutation=mutation):
                trace = copy.deepcopy(original)
                trace["comparisons"][0].update(mutation)
                if mutation.get("status") in ("OUTPUT_LIMIT", "RESOURCE_LIMIT"):
                    trace["success"] = False
                    self.sample.rows[(0, "control")].update(outcome="FAILURE", grader_exit_code=1)
                else:
                    self.sample.rows[(0, "control")].update(outcome="SUCCESS", grader_exit_code=0)
                self.sample.artifact(0, "control", "grader-trace.txt", trace)
                self.sample.save(0)
                self.assertInvalid(error)

    def test_deep_candidate_json_is_measured_failure_without_analyzer_recursion(self):
        row = self.sample.rows[(0, "control")]
        trace = self.sample.load(0, "control", "grader-trace.txt")
        stdout = "[" * 20_000 + "0" + "]" * 20_000
        trace["comparisons"][0].update(status="FAILURE", stdout=stdout,
                                       stdout_bytes_observed=len(stdout))
        trace["success"] = False
        row.update(outcome="FAILURE", grader_exit_code=1)
        self.sample.artifact(0, "control", "grader-trace.txt", trace)
        self.sample.save(0)
        report = analyze(self.root)
        self.assertEqual(report["status"], COMPLETE, report["errors"])
        self.assertEqual(report["control_success"], 9)

    def test_deep_pair_json_is_invalid_without_analyzer_recursion(self):
        (self.root / "pair-0.json").write_text("[" * 20_000 + "0" + "]" * 20_000)
        self.assertInvalid("INVALID_PAIR_FILE")

    def test_completed_generation_without_parseable_patch_is_measured_failure(self):
        row = self.sample.rows[(1, "control")]
        raw = self.sample.load(1, "control", "agent-events.ndjson")
        raw["message"]["content"] = "Here is a plan without any Python source."
        self.sample.artifact(1, "control", "agent-events.ndjson", raw)
        self.sample.artifact(1, "control", "submitted-solution.py", task(1)["source"].encode())
        row["patch_parsed"] = False
        self.sample.save(1)
        report = analyze(self.root)
        self.assertEqual(report["status"], COMPLETE, report["errors"])
        self.assertEqual(report["control_success"], 10)

    def test_unstarted_or_infrastructure_timeout_remains_incomplete(self):
        trace = self.sample.load(0, "control", "grader-trace.txt")
        trace["comparisons"][0].update(status="INFRA_FAILURE", exit_code=None, stderr="")
        trace.update(executed=False, success=False)
        row = self.sample.rows[(0, "control")]
        row.update(outcome="FAILURE", grader_status="INFRA_FAILURE", grader_exit_code=None)
        self.sample.artifact(0, "control", "grader-trace.txt", trace)
        self.sample.save(0)
        self.assertInvalid("MISSING_OR_UNEXECUTED_GRADER")

    def test_graded_unauthorized_edit_is_measured_failure(self):
        row = self.sample.rows[(0, "control")]
        row.update(unauthorized_changes=["README.md"], outcome="FAILURE")
        self.sample.save(0)
        report = analyze(self.root)
        self.assertEqual(report["status"], COMPLETE, report["errors"])
        self.assertEqual(report["control_success"], 9)


if __name__ == "__main__":
    unittest.main()
