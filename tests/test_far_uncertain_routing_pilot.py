"""Set-valued ambiguous routing pilot tests; model/network is mocked in unit tests."""
import base64
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import far_uncertain_routing_pilot as study


class FakeResponse:
    status = 200
    def __init__(self, choice="ASK_SCOPE"):
        self.raw = json.dumps({
            "model": "/tmp/pinned-model.gguf",
            "choices": [{"message": {"content": choice}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 44},
        }).encode()
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self, n): return self.raw[:n]


class UncertainRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p, cls.digest = study.load()

    def test_frozen_cases_have_nontrivial_admissible_action_sets(self):
        self.assertEqual(self.p["case_count"], 12)
        self.assertEqual(len(self.p["tasks"]), 12)
        self.assertTrue(all(len(t["admissible"]) >= 2 for t in self.p["tasks"]))
        self.assertTrue(all("VERIFY_EXPLICIT" not in t["admissible"] for t in self.p["tasks"]))
        self.assertEqual(len(set(t["prompt"] for t in self.p["tasks"])), 12)
        self.assertEqual(len(self.digest), 64)
        self.assertEqual(self.p["status"], "RESEARCH_FROZEN_TASK_AUTHOR")

    def test_model_request_separates_public_task_from_gold_action_set(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse()) as mock:
            x = study.request_model("No contract supplied")
        self.assertEqual(mock.call_count, 1)
        self.assertEqual(x["action"], "ASK_SCOPE")
        request = x["request"]
        self.assertEqual(request["messages"][1]["content"], "Case text (untrusted task data):\nNo contract supplied")
        self.assertNotIn('"admissible"', json.dumps(request))
        self.assertEqual(hashlib.sha256(base64.b64decode(x["raw_response_base64"])).hexdigest(),
                         x["response_sha256"])
        body = json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(body).hexdigest(), x["request_sha256"])

    def test_network_restricted_and_uninterpretable_completion_not_inferred(self):
        with patch("urllib.request.urlopen") as mock:
            with self.assertRaises(study.StudyError):
                study.request_model("x", endpoint="https://api.example")
            mock.assert_not_called()
        with patch("urllib.request.urlopen", return_value=FakeResponse("Maybe ask?")):
            x = study.request_model("under-specified")
        self.assertEqual(x["action"], "INVALID_ACTION")

    def test_complete_mock_run_reports_set_valued_admissibility(self):
        def simulated(prompt):
            return {"action": "DISCOVER_CONTRACT", "reported_model": "pinned",
                    "total_tokens": 20, "raw_response_base64": "e30=",
                    "request": {}, "request_sha256": "a" * 64,
                    "response_sha256": "b" * 64}
        with patch.object(study, "sha256_file", return_value=study.MODEL_SHA256):
            result = study.evaluate(self.p, self.digest, Path("/fake/model.gguf"),
                                    runner=simulated)
        self.assertEqual(result["status"], "EXECUTED_INTERNAL_RESEARCH")
        self.assertEqual(len(result["records"]), 12)
        self.assertEqual(result["summary"]["agent_admissible"],
                         result["summary"]["fixed_discover_contract_admissible"])
        self.assertEqual(result["summary"]["model_tokens"], 240)
        self.assertEqual(result["summary"]["unsafe_verification"], 0)
        self.assertEqual(result["claim"], "SCOPED_TASK_AUTHOR_SET_VALUED_OBSERVATION_ONLY")

    def test_all_constant_routing_baselines_expose_nonadaptive_model(self):
        def ask_every_time(prompt):
            return {"action": "ASK_SCOPE", "reported_model": "pinned",
                    "total_tokens": 12}
        with patch.object(study, "sha256_file", return_value=study.MODEL_SHA256):
            output = study.evaluate(self.p, self.digest, Path("/fake"), runner=ask_every_time)
        summary = output["summary"]
        self.assertEqual(summary["agent_admissible"], 11)
        self.assertEqual(summary["fixed_action_scores"]["ASK_SCOPE"], 11)
        self.assertEqual(summary["fixed_action_scores"]["DISCOVER_CONTRACT"], 6)
        self.assertEqual(summary["model_action_counts"]["ASK_SCOPE"], 12)
        self.assertEqual(summary["unique_model_actions"], 1)
        self.assertEqual(summary["model_minus_best_constant"], 0)

    def test_action_diversity_reported_without_claiming_unique_correct_action(self):
        case_actions = iter([row["admissible"][0] for row in self.p["tasks"]])
        def admit_each(prompt):
            return {"action": next(case_actions), "reported_model": "pinned",
                    "total_tokens": 12}
        with patch.object(study, "sha256_file", return_value=study.MODEL_SHA256):
            output = study.evaluate(self.p, self.digest, Path("/fake"), runner=admit_each)
        self.assertEqual(output["summary"]["agent_admissible"], 12)
        self.assertGreater(output["summary"]["unique_model_actions"], 1)
        self.assertEqual(output["summary"]["model_minus_best_constant"], 1)
        self.assertIn("task_author", output["claim"].lower())

    def test_unsafe_verification_is_counted_not_promoted(self):
        def bad(prompt):
            return {"action": "VERIFY_EXPLICIT", "reported_model": "pinned",
                    "total_tokens": 20}
        with patch.object(study, "sha256_file", return_value=study.MODEL_SHA256):
            result = study.evaluate(self.p, self.digest, Path("/fake"), runner=bad)
        self.assertEqual(result["summary"]["unsafe_verification"], 12)
        self.assertEqual(result["summary"]["agent_admissible"], 0)

    def test_malformed_http_200_preserves_raw_response_and_request_in_partial(self):
        # Regression for Codex: missing model telemetry must never discard bytes
        # already received from an actual HTTP 200 model call.
        class BadResponse(FakeResponse):
            def __init__(self):
                self.raw = b'{"model":"local","choices":[{"message":{"content":"ASK_SCOPE"}}]}'

        with tempfile.TemporaryDirectory() as directory:
            partial = Path(directory) / "raw-failure.json"
            def store(record):
                study.persist(partial, record)
            with patch.object(study, "sha256_file", return_value=study.MODEL_SHA256):
                with patch("urllib.request.urlopen", return_value=BadResponse()):
                    with self.assertRaises(study.ModelResponseError):
                        study.evaluate(
                            self.p, self.digest, Path("/fake"),
                            checkpoint=store,
                        )
            artifact = json.loads(partial.read_text())
            self.assertEqual(artifact["status"], "FAILED_OR_INCOMPLETE")
            self.assertEqual(artifact["completed"], 0)
            failed = artifact["failed_model_call"]
            self.assertEqual(failed["case_id"], self.p["tasks"][0]["id"])
            envelope = failed["raw_envelope"]
            self.assertEqual(
                hashlib.sha256(base64.b64decode(envelope["raw_response_base64"])).hexdigest(),
                envelope["response_sha256"])
            self.assertEqual(
                hashlib.sha256(json.dumps(
                    envelope["request"], sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                envelope["request_sha256"])

    def test_partial_evidence_survives_second_model_timeout(self):
        calls = 0
        def broken(prompt):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise study.StudyError("second call transport failure")
            return {"action": "ASK_SCOPE", "reported_model": "pinned", "total_tokens": 20,
                    "raw_response_base64": "e30=", "request_sha256": "a" * 64,
                    "response_sha256": "b" * 64}
        with tempfile.TemporaryDirectory() as directory:
            partial = Path(directory) / "partial.json"
            with patch.object(study, "sha256_file", return_value=study.MODEL_SHA256):
                with self.assertRaisesRegex(study.StudyError, "transport failure"):
                    study.evaluate(self.p, self.digest, Path("/fake"), runner=broken,
                                   checkpoint=lambda record: study.persist(partial, record))
            data = json.loads(partial.read_text())
            self.assertEqual(data["status"], "INCOMPLETE")
            self.assertEqual(data["completed"], 1)
            self.assertEqual(len(data["records"]), 1)
            self.assertEqual(data["claim"], "NOT_ESTABLISHED")

    def test_invalid_model_or_malformed_protocol_blocks(self):
        with patch.object(study, "sha256_file", return_value="0" * 64):
            with self.assertRaisesRegex(study.StudyError, "SHA-256"):
                study.evaluate(self.p, self.digest, Path("/fake"), runner=lambda _: {})
        mutated = copy.deepcopy(self.p)
        mutated["tasks"][0]["admissible"] = ["VERIFY_EXPLICIT"]
        with tempfile.TemporaryDirectory() as directory:
            location = Path(directory) / "invalid.json"
            location.write_text(json.dumps(mutated), encoding="utf-8")
            with patch.object(study, "FROZEN", location):
                with self.assertRaisesRegex(study.StudyError, "admissibility"):
                    study.load()

    def test_distinct_model_identity_required(self):
        count = 0
        def varied(prompt):
            nonlocal count
            count += 1
            return {"action": "ASK_SCOPE", "reported_model": str(count % 2),
                    "total_tokens": 5}
        with patch.object(study, "sha256_file", return_value=study.MODEL_SHA256):
            with self.assertRaisesRegex(study.StudyError, "identity drift"):
                study.evaluate(self.p, self.digest, Path("/fake"), runner=varied)


if __name__ == "__main__":
    unittest.main()
