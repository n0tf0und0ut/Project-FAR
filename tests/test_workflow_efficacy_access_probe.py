"""Mock-only contract tests; never contact the provider."""
import io
import json
import unittest
import urllib.error
from unittest.mock import patch
from tools.workflow_efficacy_access_probe import BODY, HASH, MODEL, ENDPOINT, contract, probe

class FakeResponse:
    status = 200
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self, n):
        return json.dumps({"modelVersion": MODEL + "-002", "candidates": [
            {"content": {"parts": [{"text": "READY"}]}}],
            "usageMetadata": {"totalTokenCount": 23}}).encode()

class ProbeTests(unittest.TestCase):
    def test_request_contract(self):
        self.assertEqual(contract()["max_requests"], 1)
        self.assertEqual(contract()["request_sha256"], HASH)
        self.assertIn(b"READY", BODY)
    def test_absent_key_no_request(self):
        with patch("urllib.request.urlopen") as request:
            result = probe("")
        request.assert_not_called()
        self.assertEqual(result["status"], "NO_CREDENTIAL")
    def test_usable_response_no_secret_or_text(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse()) as request:
            result = probe("secret-never-log")
        self.assertEqual(request.call_count, 1)
        self.assertEqual(result["status"], "ACCESS_VERIFIED")
        self.assertNotIn("secret-never-log", json.dumps(result))
        self.assertNotIn("READY", json.dumps(result))
    def test_provider_errors_redacted(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
            ENDPOINT, 403, "denied", None, io.BytesIO(b"SECRET"))):
            result = probe("secret-never-log")
        self.assertEqual(result["status"], "PROVIDER_HTTP_ERROR")
        self.assertNotIn("SECRET", json.dumps(result))
if __name__ == "__main__":
    unittest.main()
