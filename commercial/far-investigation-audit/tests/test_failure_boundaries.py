"""Public intake and optional provider failures must retain bounded errors."""
from __future__ import annotations

import json
import pathlib
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
