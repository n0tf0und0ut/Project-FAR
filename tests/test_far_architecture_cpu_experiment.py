"""Negative/positive controls for the real offline model runner (network mocked)."""
import copy
import base64
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import far_architecture_cpu_experiment as ex
from tools.far_architecture_routing import load


class FakeResponse:
    status = 200

    def __init__(self, action="RUN_VERIFIER", token_count=17):
        self.data = json.dumps({
            "model": "frozen-local-model",
            "choices": [{"finish_reason": "stop", "message": {"content": action}}],
            "usage": {"total_tokens": token_count, "prompt_tokens": 15, "completion_tokens": 2}
        }).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, n):
        return self.data[:n]


class OfflinePilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = load()

    def test_request_restricted_to_loopback_and_exact_actions(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse()) as call:
            result = ex.request_decision(ex.ENDPOINT, "record metadata")
        self.assertEqual(call.call_count, 1)
        self.assertEqual(result["action"], "verify")
        self.assertEqual(result["total_tokens"], 17)
        self.assertEqual(len(result["response_sha256"]), 64)
        self.assertEqual(hashlib.sha256(base64.b64decode(result["raw_response_base64"])).hexdigest(),
                         result["response_sha256"])
        raw_request = json.dumps(result["request_body"], sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(raw_request).hexdigest(), result["request_sha256"])
        with patch("urllib.request.urlopen") as call:
            with self.assertRaisesRegex(ex.PilotError, "local"):
                ex.request_decision("https://another-provider.example/api", "record metadata")
            call.assert_not_called()
        for raw, expected in (("ABSTAIN", "abstain"), ("verify please", "invalid_action")):
            with patch("urllib.request.urlopen", return_value=FakeResponse(raw)):
                self.assertEqual(ex.request_decision(ex.ENDPOINT, "input")["action"], expected)

    def test_never_send_expected_outcome_or_report_to_model(self):
        from tools.far_architecture_routing import source_document
        for case in self.protocol["cases"]:
            text = ex.prompt_for(source_document(case))
            self.assertNotIn('"expected"', text)
            self.assertNotIn('"report"', text)
            self.assertIn("verify_current", text)

    def test_all_case_specific_prompts_have_distinct_hashes(self):
        from tools.far_architecture_routing import source_document
        from tools.far_architecture_cpu_experiment import sha256
        payloads = [ex.prompt_for(source_document(case)) for case in self.protocol["cases"]]
        self.assertEqual(len(set(sha256(x.encode("utf-8")) for x in payloads)), 12)
        self.assertTrue(all("contract_id" in x for x in payloads))
        self.assertTrue(all('"report"' not in x and '"expected"' not in x for x in payloads))

    def test_real_fixed_comparison_plus_mocked_model_is_not_claimed_external(self):
        counts = []
        def model(_, prompt):
            counts.append(prompt)
            return {"action": "verify", "total_tokens": 20,
                    "observed_model": "frozen-local-model", "request_sha256": "b" * 64,
                    "response_sha256": "c" * 64, "response": {"mock": True},
                    "raw_response_base64": "e30=", "request_body": {"mock": True}}
        with patch.object(ex, "file_sha256", return_value=ex.MODEL_SHA256):
            output = ex.run(self.protocol, Path("/fake/weights.gguf"), inference_fn=model)
        self.assertEqual(len(counts), 12)
        self.assertEqual(len(output["records"]), 36)
        self.assertEqual(len(output["raw_model_events"]), 12)
        self.assertEqual([output["summary"][a]["correct"] for a in ex.ARMS], [12, 12, 12])
        self.assertEqual([output["summary"][a]["total_tokens"] for a in ex.ARMS], [0, 0, 240])
        self.assertEqual(output["claim"], "SCOPED_INTERNAL_OBSERVATIONS_ONLY")
        self.assertEqual(output["status"], "EXECUTED_BOUNDED_LOCAL_OPEN_WEIGHT")
        from tools.far_architecture_routing import plan
        self.assertEqual([(r["case_id"], r["arm"]) for r in output["records"]],
                         [(x["case_id"], x["arm"]) for x in plan(self.protocol)])

    def test_invalid_model_action_counts_as_failure(self):
        def model(_, prompt):
            return {"action": "invalid_action", "total_tokens": 5,
                    "observed_model": "local", "request_sha256": "b" * 64,
                    "response_sha256": "c" * 64, "response": {"mock": True},
                    "raw_response_base64": "e30=", "request_body": {"mock": True}}
        with patch.object(ex, "file_sha256", return_value=ex.MODEL_SHA256):
            result = ex.run(self.protocol, Path("/fake/weights.gguf"), inference_fn=model)
        self.assertEqual(result["summary"]["agent"]["correct"], 0)
        self.assertEqual(result["summary"]["agent"]["n"], 12)
        self.assertEqual(result["summary"]["deterministic"]["correct"], 12)

    def test_reject_missing_or_drifting_weight_identity(self):
        with patch.object(ex, "file_sha256", return_value="wrong"):
            with self.assertRaisesRegex(ex.PilotError, "SHA-256"):
                ex.run(self.protocol, Path("/fake/weights.gguf"), inference_fn=lambda *_: None)
        calls = 0
        def unstable(_, prompt):
            nonlocal calls
            calls += 1
            return {"action": "verify", "total_tokens": 5,
                    "observed_model": ("a" if calls == 1 else "b"),
                    "request_sha256": "b" * 64,
                    "response_sha256": "c" * 64, "response": {"mock": True},
                    "raw_response_base64": "e30=", "request_body": {"mock": True}}
        with patch.object(ex, "file_sha256", return_value=ex.MODEL_SHA256):
            with self.assertRaisesRegex(ex.PilotError, "drift"):
                ex.run(self.protocol, Path("/fake/weights.gguf"), inference_fn=unstable)

    def test_partial_execution_persists_prior_raw_model_events(self):
        count = 0

        def model(_, prompt):
            nonlocal count
            count += 1
            if count == 2:
                raise ex.PilotError("injected second-call timeout")
            return {"action": "verify", "total_tokens": 20,
                    "observed_model": "frozen-local-model",
                    "request_sha256": "b" * 64, "response_sha256": "c" * 64,
                    "response": {"raw_response": "retained"},
                    "raw_response_base64": "e30=", "request_body": {"mock": True}}

        with tempfile.TemporaryDirectory() as directory:
            partial = Path(directory) / "results.partial.json"
            with patch.object(ex, "file_sha256", return_value=ex.MODEL_SHA256):
                with self.assertRaisesRegex(ex.PilotError, "second-call timeout"):
                    ex.run(self.protocol, Path("/fake/weights.gguf"), inference_fn=model,
                           progress=lambda snapshot: ex.persist_progress(snapshot, partial))
            self.assertEqual(count, 2)
            self.assertTrue(partial.exists(), "first model response must survive later failure")
            saved = json.loads(partial.read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], "INCOMPLETE")
            self.assertEqual(saved["claim"], "NOT_ESTABLISHED")
            self.assertEqual(saved["model_events"], 1)
            self.assertLess(saved["completed_cells"], 36)
            self.assertEqual(len(saved["raw_model_events"]), 1)
            self.assertEqual(saved["raw_model_events"][0]["raw_response"],
                             {"raw_response": "retained"})
            self.assertEqual(saved["raw_model_events"][0]["raw_response_base64"], "e30=")
            self.assertEqual(saved["raw_model_events"][0]["request_body"], {"mock": True})
            self.assertFalse(partial.with_suffix(".tmp").exists())

    def test_progress_checkpoints_are_monotone_and_final_clear_is_safe(self):
        snapshots = []

        def model(_, prompt):
            return {"action": "verify", "total_tokens": 20,
                    "observed_model": "frozen-local-model",
                    "request_sha256": "b" * 64, "response_sha256": "c" * 64,
                    "response": {"mock": True}, "raw_response_base64": "e30=",
                    "request_body": {"mock": True}}

        with patch.object(ex, "file_sha256", return_value=ex.MODEL_SHA256):
            result = ex.run(self.protocol, Path("/fake/weights.gguf"),
                            inference_fn=model,
                            progress=lambda snapshot: snapshots.append((
                                snapshot["completed_cells"], snapshot["model_events"],
                                snapshot["claim"])))
        self.assertEqual(len(snapshots), 36)
        self.assertEqual([x[0] for x in snapshots], list(range(1, 37)))
        self.assertEqual(snapshots[-1], (36, 12, "NOT_ESTABLISHED"))
        self.assertEqual(result["status"], "EXECUTED_BOUNDED_LOCAL_OPEN_WEIGHT")

    def test_checkpoint_write_is_atomic_and_replaces_previous_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "record.partial.json"
            ex.persist_progress({"model_events": 1, "status": "INCOMPLETE"}, path)
            ex.persist_progress({"model_events": 2, "status": "INCOMPLETE"}, path)
            self.assertEqual(json.loads(path.read_text())["model_events"], 2)
            self.assertFalse(path.with_name(path.name + ".tmp").exists())

    def test_invalid_telemetry_blocks_execution(self):
        for response in (
            {"model": "local", "choices": [{"finish_reason": "stop", "message": {"content": "RUN_VERIFIER"}}],
             "usage": {"total_tokens": 0}},
            {"model": "local", "choices": [], "usage": {"total_tokens": 10}},
        ):
            class Response(FakeResponse):
                def __init__(self):
                    self.data = json.dumps(response).encode()
            with patch("urllib.request.urlopen", return_value=Response()):
                with self.assertRaises(ex.PilotError):
                    ex.request_decision(ex.ENDPOINT, "x")


if __name__ == "__main__":
    unittest.main()
