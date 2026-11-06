"""Reject ambiguous debugger requests before invoking the investigation."""
import asyncio
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from starlette.requests import Request
import webapp


class DebuggerJSONIntakeTests(unittest.TestCase):
    def request(self, raw):
        async def receive():
            return {"type": "http.request", "body": raw, "more_body": False}
        return Request({"type": "http", "headers": [(b"content-type", b"application/json")]}, receive)

    def test_ambiguous_or_nonfinite_requests_never_reach_investigation(self):
        cases = [
            b'{"debugger":true,"debugger":false}',
            b'{"source":{"kind":"text","text":"original","text":"replacement"}}',
            b'{"debugger":true,"unused":NaN}',
            b'[' * 10000 + b'0' + b']' * 10000,
        ]
        for raw in cases:
            with self.subTest(raw=raw[:80]), patch.object(webapp, "investigate", return_value={}) as run:
                with self.assertRaises(HTTPException) as caught:
                    asyncio.run(webapp.analyze(self.request(raw)))
                self.assertEqual(caught.exception.status_code, 422)
                run.assert_not_called()

    def test_valid_request_works_after_a_rejection(self):
        raw = b'{"debugger":true,"source":{"kind":"text","text":"Claim."}}'
        with patch.object(webapp, "investigate", return_value={"accepted": True}) as run:
            response = asyncio.run(webapp.analyze(self.request(raw)))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.body)["accepted"])
        self.assertIs(run.call_args.args[0]["debugger"], True)


if __name__ == "__main__":
    unittest.main()
