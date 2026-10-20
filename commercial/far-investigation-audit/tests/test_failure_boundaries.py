"""Public intake and optional provider failures must retain bounded errors."""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from acquire import AcquisitionError
from engine import InvalidBundle
from local_media import transcribe_local
from proposals import openai_proposal
from workflow import investigate


class FailureBoundaryTests(unittest.TestCase):
    def test_all_json_clis_reject_parser_recursion_without_tracebacks(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            nested = pathlib.Path(d) / "nested.json"
            nested.write_text("[" * 10000 + "0" + "]" * 10000)
            commands = [
                ("cli.py", [str(nested)], "FAR_AUDIT_INVALID"),
                ("verify.py", [str(nested), str(nested)], "FAR_REPLAY_INVALID"),
                ("field_validation.py", ["--predictions", str(nested), "--adjudications", str(nested)], "FAR_FIELD_EVAL_INVALID"),
                ("review.py", [str(nested), "--private-key", str(pathlib.Path(d) / "absent.pem"),
                               "--output", str(pathlib.Path(d) / "out.json")], "FAR_REVIEW_INVALID"),
            ]
            for script, arguments, prefix in commands:
                with self.subTest(script=script):
                    result = subprocess.run([sys.executable, str(root / script), *arguments],
                                            capture_output=True, text=True, timeout=10)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertTrue(result.stderr.startswith(prefix), result.stderr)
                    self.assertNotIn("Traceback", result.stderr)

    def test_over_nested_search_response_is_a_bounded_provider_failure(self):
        from discovery import DiscoveryError, tavily_search
        connection = SimpleNamespace(
            request=lambda *a, **kw: None, close=lambda: None,
            getresponse=lambda: SimpleNamespace(status=200, read=lambda n:
                ("[" * 10000 + "0" + "]" * 10000).encode()))
        with patch.dict("os.environ", {"TAVILY_API_KEY": "synthetic-test-key"}), \
                patch("discovery.resolve_public", return_value=["93.184.216.34"]), \
                patch("discovery._PinnedHTTPS", return_value=connection):
            with self.assertRaisesRegex(DiscoveryError, "search provider request failed"):
                tavily_search(["bounded query"], allow_network=True)

    def test_malformed_sources_are_validated_before_network_time_guard(self):
        for change in ({"source": []}, {"evidence_sources": None}):
            with self.subTest(change=change):
                config = {"captured_at": "2026-10-17T12:00:00Z",
                          "source": {"kind": "text", "text": "A bounded source."},
                          **change}
                with self.assertRaises(InvalidBundle):
                    investigate(config, permit_network=True)

    def test_model_client_initialization_is_a_redacted_workflow_failure(self):
        def constructor(**kwargs):
            raise RuntimeError("private client configuration")
        with patch.dict(sys.modules, {"openai": SimpleNamespace(OpenAI=constructor)}):
            with self.assertRaisesRegex(InvalidBundle, "model proposal provider unavailable"):
                openai_proposal("A bounded source.", {})

    def test_transcription_client_initialization_is_a_redacted_workflow_failure(self):
        def constructor(**kwargs):
            raise RuntimeError("private client configuration")
        def convert(command, **kwargs):
            pathlib.Path(command[-1]).write_bytes(b"fake bounded audio")
            return SimpleNamespace(returncode=0)
        with tempfile.TemporaryDirectory() as d:
            source = pathlib.Path(d) / "source.wav"
            source.write_bytes(b"fake source")
            with patch.dict(sys.modules, {"openai": SimpleNamespace(OpenAI=constructor)}), \
                    patch("local_media.subprocess.run", side_effect=convert):
                with self.assertRaisesRegex(AcquisitionError, "transcription provider unavailable"):
                    transcribe_local(source, permit_model=True)

    def test_over_nested_model_response_is_a_bounded_workflow_failure(self):
        response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
            content="[" * 10000 + "0" + "]" * 10000))])
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: response)))
        with self.assertRaisesRegex(InvalidBundle, "invalid JSON or response"):
            openai_proposal("A bounded source.", {}, client=client)


class WebFailureBoundaryTests(unittest.TestCase):
    def test_over_nested_request_returns_422_and_releases_worker(self):
        from fastapi.testclient import TestClient
        from webapp import app
        with TestClient(app) as client:
            response = client.post("/api/investigate", content="[" * 10000 + "0" + "]" * 10000,
                                   headers={"content-type": "application/json"})
            self.assertEqual(response.status_code, 422)
            self.assertNotIn("Traceback", response.text)
            valid = client.post("/api/investigate", json={"source": {
                "kind": "text", "text": "A bounded source."}})
            self.assertEqual(valid.status_code, 200)


if __name__ == "__main__":
    unittest.main()
