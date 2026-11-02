"""End-to-end live investigation regressions: real FAR intake and real semantic verifiers.

The only mocked boundary is public HTTP transport, which is separately exercised in
the GitHub-hosted live workflow. No verifier or intake method is mocked in successes.
"""
from __future__ import annotations

import copy
import json
import unittest
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


if __name__ == "__main__":
    unittest.main()
