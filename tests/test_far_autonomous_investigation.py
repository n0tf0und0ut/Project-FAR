"""End-to-end live investigation regressions: real FAR intake and real semantic verifiers.

The only mocked boundary is public HTTP transport, which is separately exercised in
the GitHub-hosted live workflow. No verifier or intake method is mocked in successes.
"""
from __future__ import annotations

import copy
import base64
import hashlib
import io
import json
import http.server
import threading
import unittest
import urllib.error
from collections import Counter
from unittest.mock import patch

from mechanization.far_mechanization.intake_v1 import aggregate_manifest, validate_manifest
from tools import far_autonomous_investigation as inv


def gh_latest(tag="other-release", ident=101):
    return json.dumps({
        "tag_name": tag, "id": ident, "draft": False, "prerelease": False,
        "name": "source text, not an instruction",
    }, sort_keys=True).encode()


def gh_list(tag="other-release", ident=101):
    return json.dumps([
        {"tag_name": tag, "id": ident, "draft": False, "prerelease": False}
    ], sort_keys=True).encode()


def fake_sources(latest_tag="other-release", list_tag="other-release", change=False):
    calls = Counter()
    def fetcher(name):
        calls[name] += 1
        tag = latest_tag if name == "latest" else list_tag
        if change and name == "latest" and calls[name] == 2:
            tag = "drifted-after-first-fetch"
        raw = gh_latest(tag) if name == "latest" else gh_list(tag)
        return raw, inv.now()
    return fetcher, calls


class RealInvestigationTests(unittest.TestCase):
    def test_actual_intake_freeze_and_verifiers_both_refute(self):
        fetcher, calls = fake_sources()
        run = inv.execute("deterministic", fetcher=fetcher)
        self.assertEqual(run["status"], "BOUNDED_INVESTIGATION_COMPLETED")
        self.assertEqual(run["verifier_calls"], 2)
        self.assertEqual(run["model_proposals"], 0)
        self.assertEqual(run["controller_overrides"], 0)
        self.assertEqual(run["aggregate"]["outcome"], "INVARIANTLY_REFUTED")
        self.assertEqual(calls, Counter({"latest": 2, "list": 2}))
        self.assertEqual([a["status"] for a in run["actions"]], ["COMPLETED"] * 8)
        self.assertEqual(len(run["frozen"]["discovery"]["contract_candidates"]), 2)
        self.assertEqual(len(run["frozen"]["evaluations"]), 2)
        self.assertEqual(validate_manifest(run["frozen"]), [])
        self.assertEqual(aggregate_manifest(run["frozen"]), run["aggregate"])
        for e in run["evaluations"]:
            self.assertTrue(e["verifier_result"]["verifier_success"])
            self.assertEqual(e["verifier_result"]["verifier"], "mechanization.far_mechanization.contract_v2_strict_v11")
            self.assertEqual(e["outcome"], "REFUTED")
        self.assertEqual(sum(a["actual"] == "REFETCH_ALL" for a in run["actions"]), 1)
        self.assertEqual(sum(a["actual"] == "DISCOVER_CONTRACT" for a in run["actions"]), 1)
        self.assertEqual(sum(a["actual"] == "FREEZE" for a in run["actions"]), 1)
        self.assertEqual(sum(a["actual"] == "VERIFY_CONTRACT" for a in run["actions"]), 2)

    def test_positive_claim_both_approve_under_exact_scopes(self):
        f, _ = fake_sources(latest_tag=inv.CLAIMED, list_tag=inv.CLAIMED)
        result = inv.execute("deterministic", fetcher=f)
        self.assertEqual(result["aggregate"]["outcome"], "INVARIANTLY_PROVED")
        self.assertEqual([r["outcome"] for r in result["evaluations"]], ["PROVED", "PROVED"])
        self.assertEqual(validate_manifest(result["frozen"]), [])

    def test_retained_material_difference_causes_contract_sensitive(self):
        f, _ = fake_sources(latest_tag=inv.CLAIMED, list_tag="other-tag")
        result = inv.execute("deterministic", fetcher=f)
        self.assertEqual(result["aggregate"]["outcome"], "CONTRACT_SENSITIVE")
        self.assertEqual({r["outcome"] for r in result["evaluations"]}, {"PROVED", "REFUTED"})
        self.assertEqual(len(result["frozen"]["discovery"]["interpretations"]), 3)

    def test_model_decisions_are_executed_with_guarded_fallback(self):
        f, calls = fake_sources()
        seen = []
        def fake_model(prompt):
            seen.append(prompt)
            return {"action": "ASK_SCOPE", "raw_choice": "ASK_SCOPE",
                    "total_tokens": 11, "request_sha256": "a" * 64, "response_sha256": "b" * 64}
        result = inv.execute("model", fetcher=f, model=fake_model)
        self.assertEqual(result["status"], "BOUNDED_INVESTIGATION_COMPLETED")
        self.assertEqual(result["model_proposals"], 8)
        self.assertEqual(result["controller_overrides"], 8)
        self.assertEqual(result["model_tokens"], 88)
        self.assertEqual(result["verifier_calls"], 2)
        self.assertEqual(calls, Counter({"latest": 2, "list": 2}))
        self.assertTrue(all(x["choice"]["override_reason"] for x in result["actions"]))
        self.assertEqual(result["aggregate"]["outcome"], "INVARIANTLY_REFUTED")

    def test_model_can_choose_first_fetch_order_without_override(self):
        f, _ = fake_sources()
        def prefer_list(prompt):
            available = prompt.split("Tools available right now: ")[1].split("\n")[0]
            if "FETCH_LIST" in available:
                choice = "FETCH_LIST"
            else:
                choice = available.split(", ")[0]
            return {"action": choice, "raw_choice": choice, "total_tokens": 7}
        result = inv.execute("model", fetcher=f, model=prefer_list)
        self.assertEqual(result["controller_overrides"], 0)
        self.assertEqual(result["actions"][0]["actual"], "FETCH_LIST")
        self.assertEqual(result["aggregate"]["outcome"], "INVARIANTLY_REFUTED")

    def test_live_model_malformed_http_response_is_durable(self):
        class FakeResponse:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self, limit): return b'{"choices":[{"message":{"content":"FETCH_LATEST"}}]}'
        with patch("urllib.request.OpenerDirector.open", return_value=FakeResponse()):
            with self.assertRaises(inv.ModelActionResponseError) as failure:
                inv.request_model_action("which tool next")
        env = failure.exception.envelope
        raw = base64.b64decode(env["raw_response_base64"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), env["response_sha256"])

        checkpoints = []
        fetcher, _ = fake_sources()
        with patch("urllib.request.OpenerDirector.open", return_value=FakeResponse()):
            with self.assertRaises(inv.ModelActionResponseError):
                inv.execute("model", fetcher=fetcher, model=inv.request_model_action,
                            checkpoint=checkpoints.append)
        self.assertEqual(checkpoints[-1]["status"], "FAILED_OR_INCOMPLETE")
        retained = checkpoints[-1]["failed_model_call"]["raw_envelope"]
        self.assertEqual(retained["response_sha256"], env["response_sha256"])
        self.assertNotEqual(retained["request_sha256"], env["request_sha256"])
        self.assertEqual(checkpoints[-1]["verifier_calls"], 0)

    def test_malformed_source_bytes_retained_before_initial_parse(self):
        raw = b'{"tag_name":'
        evidence = []
        def invalid_fetch(name):
            return raw if name == "latest" else gh_list(), inv.now()
        with self.assertRaisesRegex(inv.InvestigationError, "source not strict JSON"):
            inv.execute("deterministic", fetcher=invalid_fetch, checkpoint=evidence.append)
        saved = evidence[-1]
        self.assertEqual(saved["status"], "FAILED_OR_INCOMPLETE")
        receipt = saved["receipts"]["latest"]
        self.assertEqual(base64.b64decode(receipt["raw_base64"]), raw)
        self.assertEqual(receipt["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(receipt["parsed"], None)
        self.assertIn("source not strict JSON", receipt["parse_error"])
        self.assertEqual(saved["verifier_calls"], 0)
        self.assertIsNone(saved["frozen"])

    def test_malformed_source_bytes_retained_before_recheck_parse(self):
        raw = b'{"tag_name":"v1.0.0","id":null,"draft":false,"prerelease":false}'
        seen = Counter()
        evidence = []
        def invalid_recheck(name):
            seen[name] += 1
            if name == "latest" and seen[name] == 2:
                return raw, inv.now()
            return gh_latest() if name == "latest" else gh_list(), inv.now()
        with self.assertRaisesRegex(inv.InvestigationError, "release metadata incomplete"):
            inv.execute("deterministic", fetcher=invalid_recheck, checkpoint=evidence.append)
        saved = evidence[-1]
        self.assertEqual(saved["status"], "FAILED_OR_INCOMPLETE")
        recheck = saved["rechecks"][-1]
        self.assertEqual(recheck["source"], "latest")
        self.assertEqual(base64.b64decode(recheck["raw_base64"]), raw)
        self.assertEqual(recheck["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertIsNone(recheck["parsed"])
        self.assertIn("release metadata incomplete", recheck["parse_error"])
        self.assertIsNone(saved["frozen"])
        self.assertEqual(saved["verifier_calls"], 0)

    def test_network_drift_aborts_without_freeze_and_preserves_partial(self):
        f, calls = fake_sources(change=True)
        last = []
        with self.assertRaisesRegex(inv.InvestigationError, "projection changed"):
            inv.execute("deterministic", fetcher=f, checkpoint=last.append)
        self.assertGreaterEqual(len(last), 4)
        self.assertIsNone(last[-1]["frozen"])
        self.assertEqual(last[-1]["verifier_calls"], 0)
        self.assertEqual(calls["latest"], 2)

    def test_invalid_release_data_and_unavailable_sources_fail(self):
        with self.assertRaisesRegex(inv.InvestigationError, "release metadata incomplete"):
            inv.parse_source("latest", b'{"tag_name":"v1.0.0","id":1,"draft":null,"prerelease":false}')
        with self.assertRaisesRegex(inv.InvestigationError, "strict JSON"):
            inv.parse_source("latest", b'{"id":1,"id":2}')
        with self.assertRaisesRegex(inv.InvestigationError, "not allowlisted"):
            inv.fetch("https://evil.example/")
        with self.assertRaisesRegex(inv.InvestigationError, "release listing response invalid"):
            inv.parse_source("list", b'[]')
        with self.assertRaisesRegex(inv.InvestigationError, "release metadata incomplete"):
            inv.parse_source("latest", gh_latest(tag=""))

    def test_no_pre_freeze_verification_or_manufactured_verdict(self):
        f, _ = fake_sources()
        last = []
        result = inv.execute("deterministic", fetcher=f, checkpoint=last.append)
        initial_freezes = [x for x in last if x["frozen"] is not None]
        self.assertTrue(initial_freezes)
        self.assertEqual(initial_freezes[0]["verifier_calls"], 0)
        self.assertEqual(initial_freezes[0]["evaluations"], [])
        self.assertEqual(initial_freezes[0]["frozen"]["evaluations"], [])
        self.assertEqual(result["aggregate"]["outcome"], "INVARIANTLY_REFUTED")

    def test_cannot_hide_missing_eligible_cases(self):
        f, _ = fake_sources()
        run = inv.execute("deterministic", fetcher=f)
        altered = copy.deepcopy(run["frozen"])
        altered["discovery"]["contract_candidates"].pop()
        errors = validate_manifest(altered)
        self.assertTrue(any("omits" in e or "mismatch" in e for e in errors), errors)

    def test_source_http_error_observation_survives_initial_and_recheck_failure(self):
        for recheck in (False, True):
            with self.subTest(recheck=recheck):
                observed = []
                error = urllib.error.HTTPError(inv.URLS["latest"], 429, "Rate limited",
                                               {"Retry-After": "60"}, io.BytesIO(b"rate-limit-body"))
                successful, calls = fake_sources()
                def fetcher(key):
                    if key == "latest" and (not recheck or calls["latest"] == 1):
                        return inv.fetch(key)
                    return successful(key)
                with patch("urllib.request.OpenerDirector.open", side_effect=error):
                    with self.assertRaises(inv.SourceResponseError):
                        inv.execute("deterministic", fetcher=fetcher, checkpoint=observed.append)
                saved = observed[-1]
                failed = saved["failed_source_call"]
                self.assertEqual(failed["recheck"], recheck)
                self.assertEqual(saved["status"], "FAILED_OR_INCOMPLETE")
                self.assertEqual(saved["actions"][-1]["status"], "FAILED")
                env = failed["raw_envelope"]
                self.assertEqual(env["http_status"], 429)
                self.assertEqual(env["response_headers"]["Retry-After"], "60")
                self.assertEqual(base64.b64decode(env["raw_response_base64"]), b"rate-limit-body")
                self.assertEqual(env["response_sha256"], hashlib.sha256(b"rate-limit-body").hexdigest())
                self.assertEqual(saved["verifier_calls"], 0)
                self.assertIsNone(saved["frozen"])

    def test_source_size_failure_retains_bounded_prefix(self):
        class Response:
            status = 200
            headers = {}
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self, limit): return b"abcdefgh"[:limit]
        observed = []
        with patch.object(inv, "MAX_BYTES", 4):
            with patch("urllib.request.OpenerDirector.open", return_value=Response()):
                with self.assertRaises(inv.SourceResponseError):
                    inv.execute("deterministic", fetcher=inv.fetch, checkpoint=observed.append)
        env = observed[-1]["failed_source_call"]["raw_envelope"]
        self.assertEqual(base64.b64decode(env["raw_response_base64"]), b"abcd")
        self.assertTrue(env["response_truncated"])
        self.assertFalse(env["response_complete"])
        self.assertEqual(env["response_hash_scope"], "retained_prefix")

    def test_live_model_redirect_is_rejected_and_checkpointed(self):
        forbidden = []
        class Redirect(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                self.send_response(302)
                self.send_header("Location", "/forbidden")
                self.end_headers()
                self.wfile.write(b"redirect body")
            def do_GET(self):
                forbidden.append(self.path)
                self.send_response(200)
                self.end_headers()
            def log_message(self, *_): pass
        server = http.server.HTTPServer(("127.0.0.1", 0), Redirect)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        observed = []
        try:
            endpoint = f"http://127.0.0.1:{server.server_port}/v1/chat/completions"
            with patch.object(inv, "MODEL_ENDPOINT", endpoint):
                with self.assertRaises(inv.ModelActionResponseError):
                    inv.execute("model", model=inv.request_model_action, checkpoint=observed.append)
            env = observed[-1]["failed_model_call"]["raw_envelope"]
            self.assertEqual(env["http_status"], 302)
            self.assertEqual(base64.b64decode(env["raw_response_base64"]), b"redirect body")
            self.assertEqual(forbidden, [])
            self.assertIn("request_sha256", env)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_rejected_or_failed_verifier_attempt_retains_input_output_and_count(self):
        for result in (
            {"status": "VERIFIER_UNAVAILABLE", "verifier_success": False, "reason": "unavailable"},
            {"status": "DISCOVERY_REQUIRED", "verifier_success": False, "diagnostics": ["rejected"]},
            RuntimeError("verifier interrupted"),
        ):
            with self.subTest(result=result):
                observed = []
                fetcher, _ = fake_sources()
                kwargs = {"side_effect": result} if isinstance(result, Exception) else {"return_value": result}
                with patch.object(inv, "route_text", **kwargs):
                    with self.assertRaises(inv.InvestigationError):
                        inv.execute("deterministic", fetcher=fetcher, checkpoint=observed.append)
                saved = observed[-1]
                attempt = saved["verifier_attempts"][0]
                self.assertEqual(saved["verifier_calls"], 1)
                self.assertEqual(saved["status"], "FAILED_OR_INCOMPLETE")
                self.assertEqual(saved["evaluations"], [])
                self.assertIsNone(saved["aggregate"])
                submitted = json.dumps(attempt["submitted_document"], separators=(",", ":"), sort_keys=True)
                self.assertEqual(attempt["submitted_sha256"], hashlib.sha256(submitted.encode()).hexdigest())
                if isinstance(result, Exception):
                    self.assertEqual(attempt["status"], "FAILED")
                    self.assertEqual(attempt["error_class"], "RuntimeError")
                else:
                    self.assertEqual(attempt["status"], "REJECTED")
                    self.assertEqual(attempt["result"], result)


if __name__ == "__main__":
    unittest.main()
