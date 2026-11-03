"""Executable product-loop and adversarial integrity checks for augmentation prototype."""
from __future__ import annotations

import copy
import importlib.util
import json
import unittest

if importlib.util.find_spec("fastapi") is None or importlib.util.find_spec("httpx") is None:
    raise unittest.SkipTest("far-demo optional FastAPI/httpx dependencies are required")

from fastapi import FastAPI
from fastapi.testclient import TestClient
from far_demo.augmentation import _hash, router


INPUT = {
    "claim": "The new process prevents errors.",
    "reasoning": "Our reports contain fewer errors after launch.",
    "confidence": 95,
    "supporting_evidence": [{"statement": "Reports show fewer errors", "source": "internal report"}],
    "challenging_evidence": [],
    "assumptions": [],
    "alternatives": [],
    "falsifier": "",
}


class AugmentationTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def start(self, data=None):
        return self.client.post("/api/augment/start", json=data or INPUT)

    def revise(self, session, **changes):
        payload = {"session": session, "revised_claim": "The process might reduce errors.",
                   "confidence": 60, "rationale": "A competing explanation remains possible.",
                   "answers": {"counterevidence": "Older logs might reveal the same trend."}}
        payload.update(changes)
        return self.client.post("/api/augment/revise", json=payload)

    def test_full_journey_with_revisions_and_export_replay(self):
        start = self.start()
        self.assertEqual(start.status_code, 200)
        session = start.json()
        self.assertEqual(session["schema"], "far-augmentation-prototype/0.1")
        self.assertEqual(session["evidence_status"], "USER_SUPPLIED_UNVERIFIED")
        self.assertEqual(session["interpretation"], "UNKNOWN")
        self.assertIn("counterevidence", {q["id"] for q in session["questions"]})
        self.assertEqual(self.client.post("/api/augment/verify", json=session).json()["revision_count"], 0)
        revised = self.revise(session)
        self.assertEqual(revised.status_code, 200, revised.text)
        after = revised.json()
        self.assertEqual(after["basis"], session["basis"])
        self.assertEqual(session["revisions"], [])
        self.assertEqual(after["revisions"][0]["previous_sha256"], session["sha256"])
        self.assertEqual(self.client.post("/api/augment/verify", json=after).json()["revision_count"], 1)
        again = self.revise(after, revised_claim="The evidence is inconclusive", confidence=40)
        self.assertEqual(again.status_code, 200, again.text)
        twice = again.json()
        self.assertEqual(len(twice["revisions"]), 2)
        self.assertEqual(twice["revisions"][1]["previous_sha256"], twice["revisions"][0]["sha256"])
        self.assertEqual(twice["revisions"][0]["revised_claim"], "The process might reduce errors.")
        self.assertEqual(self.client.post("/api/augment/verify", json=twice).json()["revision_count"], 2)

    def test_preserves_exact_claim_wording(self):
        data = copy.deepcopy(INPUT)
        data["claim"] = "  Distinct meaning with spaces.  "
        session = self.start(data).json()
        self.assertEqual(session["basis"]["claim"], data["claim"])
        self.assertEqual(self.client.post("/api/augment/verify", json=session).status_code, 200)

    def test_missing_source_does_not_become_verified(self):
        data = copy.deepcopy(INPUT)
        data["supporting_evidence"][0]["source"] = ""
        s = self.start(data).json()
        self.assertIn("provenance", {q["id"] for q in s["questions"]})
        self.assertEqual(s["evidence_status"], "USER_SUPPLIED_UNVERIFIED")
        self.assertIn("No improvement", " ".join(s["limitations"]))

    def test_complete_supplied_fields_still_not_semantically_verified(self):
        data = copy.deepcopy(INPUT)
        data.update(challenging_evidence=[{"statement": "A rival mechanism is possible", "source": "audit"}],
                    assumptions=["Measurement method stayed constant"], alternatives=["Selection bias"],
                    falsifier="A blinded replication with no improvement")
        s = self.start(data).json()
        self.assertIn("stress-test", {q["id"] for q in s["questions"]})
        self.assertEqual(s["interpretation"], "UNKNOWN")

    def test_corrupted_basis_rejected_even_if_outer_fingerprint_recomputed(self):
        session = self.start().json()
        altered = copy.deepcopy(session)
        altered["basis"]["claim"] = "A different claim"
        altered["sha256"] = _hash(altered)
        self.assertEqual(self.client.post("/api/augment/verify", json=altered).status_code, 422)

    def test_corrupted_revision_rejected_even_if_outer_fingerprint_recomputed(self):
        original = self.revise(self.start().json()).json()
        altered = copy.deepcopy(original)
        altered["revisions"][0]["confidence"] = 100
        altered["sha256"] = _hash(altered)
        self.assertEqual(self.client.post("/api/augment/verify", json=altered).status_code, 422)

    def test_reject_out_of_order_history(self):
        first = self.revise(self.start().json()).json()
        second = self.revise(first).json()
        altered = copy.deepcopy(second)
        altered["revisions"][1]["recorded_at"] = "2020-01-01T00:00:00+00:00"
        altered["revisions"][1]["sha256"] = _hash(altered["revisions"][1])
        altered["sha256"] = _hash(altered)
        self.assertEqual(self.client.post("/api/augment/verify", json=altered).status_code, 422)

    def test_reject_unknown_question_and_missing_answer(self):
        original = self.start().json()
        self.assertEqual(self.revise(original, answers={"invented": "Text"}).status_code, 422)
        self.assertEqual(self.revise(original, answers={}).status_code, 422)

    def test_rejects_extra_fields_bool_confidence_and_excessive_lists(self):
        data = copy.deepcopy(INPUT)
        data["verified"] = True
        self.assertEqual(self.start(data).status_code, 422)
        data = copy.deepcopy(INPUT)
        data["confidence"] = True
        self.assertEqual(self.start(data).status_code, 422)
        data = copy.deepcopy(INPUT)
        data["alternatives"] = ["x"] * 13
        self.assertEqual(self.start(data).status_code, 422)

    def test_rejects_duplicate_keys_nan_and_large_bodies(self):
        self.assertEqual(self.client.post("/api/augment/start", content=b'{"claim":"x","claim":"y"}').status_code, 400)
        self.assertEqual(self.client.post("/api/augment/start", content=b'{"confidence":NaN}').status_code, 400)
        self.assertEqual(self.client.post("/api/augment/start", content=b'x' * 500001).status_code, 413)

    def test_accepted_unicode_history_over_initial_limit_can_verify_and_revise(self):
        basis = {**INPUT, "reasoning": "", "supporting_evidence": []}
        session = self.start(basis).json()
        encode = lambda data: json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()
        for _ in range(7):
            request = {"session": session, "revised_claim": "x", "confidence": 50, "rationale": "r",
                       "answers": {q["id"]: "a" for q in session["questions"]}}
            fields = [(request, "revised_claim", 3000), (request, "rationale", 3000)]
            fields += [(request["answers"], q["id"], 2000) for q in session["questions"]]
            for owner, key, limit in fields:
                room = 499950 - len(encode(request))
                owner[key] = "🙂" * min(limit, max(1, (room + 1) // 4))
            self.assertLess(len(encode(request)), 500000)
            response = self.client.post("/api/augment/revise", content=encode(request))
            self.assertEqual(response.status_code, 200, response.text)
            session = response.json()
        self.assertGreater(len(encode(session)), 500000)
        self.assertEqual(self.client.post("/api/augment/verify", content=encode(session)).status_code, 200)
        self.assertEqual(self.revise(session).status_code, 200)

    def test_existing_history_bound_does_not_relax_revision_count_or_initial_input(self):
        session = self.start().json()
        for _ in range(20):
            response = self.revise(session)
            self.assertEqual(response.status_code, 200, response.text)
            session = response.json()
        self.assertEqual(self.revise(session).status_code, 422)
        for route in ("verify", "revise"):
            self.assertEqual(self.client.post("/api/augment/" + route, content=b'x' * (8 * 1024 * 1024 + 1)).status_code, 413)
        self.assertEqual(self.client.post("/api/augment/start", content=b'x' * 500001).status_code, 413)

    def test_page_is_accessible_and_user_text_not_reflected_as_html(self):
        page = self.client.get("/augment")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Make your reasoning inspectable", page.text)
        self.assertIn("textContent", page.text)
        payload = copy.deepcopy(INPUT)
        payload["claim"] = '<img src=x onerror=alert(1)>'
        self.assertEqual(self.start(payload).json()["basis"]["claim"], payload["claim"])
        self.assertNotIn(payload["claim"], page.text)

    def test_no_session_persistence_on_server(self):
        first = self.start().json()
        second = self.start().json()
        self.assertEqual(first, second)
        self.assertNotIn("session_id", first)


if __name__ == "__main__":
    unittest.main()
