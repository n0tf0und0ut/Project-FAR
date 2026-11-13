from __future__ import annotations

import io
import json
import subprocess
import tarfile
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from tools import run_living_autonomous_review as ar
from tools.validate_research_carry import validate_ref_paths

ROOT = Path(__file__).resolve().parents[1]
CID = "FAR-LIT-55DC0543A2C4B8A2"
URL = "https://doi.org/10.0000/far-test"
NOW = datetime(2026, 9, 22, 20, 0, tzinfo=timezone.utc)


def meta(ok: bool = True, retrieved_url: str = URL):
    return {
        "model": "fake",
        "url_context_metadata": {
            "urlMetadata": [{
                "retrievedUrl": retrieved_url,
                "urlRetrievalStatus": "URL_RETRIEVAL_STATUS_SUCCESS" if ok else "URL_RETRIEVAL_STATUS_ERROR",
            }]
        },
        "grounding_metadata": {},
        "usage_metadata": {},
    }


class FakeModel:
    def __init__(
        self,
        disposition: str,
        *,
        verified: bool = True,
        implementation: bool = False,
        contradiction_flags: bool = True,
        prior_art_flags: bool = True,
        prior_art_strength: str = "DIRECT",
        retrieved_url: str = URL,
        fail_role: str | None = None,
        no_op_scientific: bool = False,
        no_op_implementation: bool = False,
        screening_relevant: bool | None = None,
    ):
        self.disposition = disposition
        self.verified = verified
        self.implementation = implementation
        self.contradiction_flags = contradiction_flags
        self.prior_art_flags = prior_art_flags
        self.prior_art_strength = prior_art_strength
        self.retrieved_url = retrieved_url
        self.fail_role = fail_role
        self.no_op_scientific = no_op_scientific
        self.no_op_implementation = no_op_implementation
        self.screening_relevant = (
            disposition != "IRRELEVANT_FALSE_POSITIVE"
            if screening_relevant is None
            else screening_relevant
        )
        self.calls: list[str] = []

    def generate(self, *, role, prompt, schema, urls=None):
        self.calls.append(role)
        if role == self.fail_role:
            raise ar.CandidateReviewError(f"forced {role} failure")
        if role == "screening":
            return {
                "primary_source_verified": self.verified,
                "relevant": self.screening_relevant,
                "source_urls_used": [URL],
                "evaluated_claim_ids": ["FAR-CORE-001"],
                "claim_assessments": [{
                    "claim_id": "FAR-CORE-001",
                    "relevant": self.screening_relevant,
                    "premise_match": self.screening_relevant,
                    "scope_match": self.screening_relevant,
                    "reason": "claim-specific screening",
                }],
                "affected_claim_ids": ["FAR-CORE-001"] if self.screening_relevant else [],
                "premise_match": self.screening_relevant,
                "scope_match": self.screening_relevant,
                "summary": "Direct source review.",
                "evidence_locations": ["primary source"],
                "limits": [],
            }, meta(self.verified, self.retrieved_url)
        if role == "attack":
            change = self.disposition == "PROJECT_CHANGE_REQUIRED"
            prior = self.disposition == "N1_PRIOR_ART_LEAD"
            contradiction = change and self.contradiction_flags
            prior_found = prior and self.prior_art_flags
            strength = self.prior_art_strength if prior_found else "NONE"
            return {
                "contradiction_found": contradiction,
                "prior_art_found": prior_found,
                "prior_art_strength": strength,
                "source_urls_used": [URL],
                "evaluated_claim_ids": ["FAR-CORE-001"],
                "claim_assessments": [{
                    "claim_id": "FAR-CORE-001",
                    "contradiction_found": contradiction,
                    "prior_art_found": prior_found,
                    "prior_art_strength": strength,
                    "reason": "claim-specific attack",
                }],
                "affected_claim_ids": ["FAR-CORE-001"] if (contradiction or prior_found) else [],
                "exact_reason": "bounded attack",
                "reproducible_attack": "construct the bound counterexample" if contradiction else "",
                "source_locations": ["primary source"],
                "limits": [],
            }, meta(True, self.retrieved_url)
        if role == "replication":
            change = self.disposition == "PROJECT_CHANGE_REQUIRED"
            prior = self.disposition == "N1_PRIOR_ART_LEAD"
            contradiction = change and self.contradiction_flags
            prior_found = prior and self.prior_art_flags
            strength = self.prior_art_strength if prior_found else "NONE"
            return {
                "contradiction_found": contradiction,
                "prior_art_found": prior_found,
                "prior_art_strength": strength,
                "source_urls_used": [URL],
                "evaluated_claim_ids": ["FAR-CORE-001"],
                "claim_assessments": [{
                    "claim_id": "FAR-CORE-001",
                    "contradiction_found": contradiction,
                    "prior_art_found": prior_found,
                    "prior_art_strength": strength,
                    "attack_reproduced": contradiction,
                    "reason": "claim-specific replication",
                }],
                "affected_claim_ids": ["FAR-CORE-001"] if (contradiction or prior_found) else [],
                "independent_reason": "independent bounded check",
                "attack_reproduced": contradiction,
                "source_locations": ["primary source"],
                "limits": [],
            }, meta(True, self.retrieved_url)
        if role == "adjudication":
            change = self.disposition == "PROJECT_CHANGE_REQUIRED"
            return {
                "disposition": self.disposition,
                "project_change_required": change,
                "scientific_targets": ["docs/research/living-autonomous-test.md"] if change else [],
                "implementation_required": self.implementation if change else False,
                "implementation_targets": ["tools/living-autonomous-test.py"] if (change and self.implementation) else [],
                "rationale": "test adjudication",
                "limits": [],
            }, {"model": "fake-adjudicator", "finish_reason": "STOP"}
        if role == "scientific_change_generator":
            content = "" if self.no_op_scientific else "# corrected\n"
            return {"files": [{"path": "docs/research/living-autonomous-test.md", "content": content}]}, {}
        if role == "implementation_change_generator":
            content = "" if self.no_op_implementation else "VALUE = 1\n"
            return {"files": [{"path": "tools/living-autonomous-test.py", "content": content}]}, {}
        raise AssertionError(role)


def source_fixture(root: Path):
    candidate = {
        "schema_version": "1.0",
        "record_type": "CANDIDATE_LITERATURE",
        "authority": "Research",
        "authority_boundary": "Research candidate only.",
        "candidate_id": CID,
        "source_key": "doi:10.0000/far-test",
        "sources": [{"provider": "OpenAlex", "doi": "10.0000/far-test", "url": URL, "title": "FAR test source"}],
        "potential_claim_ids": ["FAR-CORE-001"],
        "lifecycle": {"stage": "DISCOVERED"},
        "triage": {"status": "UNREVIEWED_CANDIDATE"},
    }
    path = root / ar.CANDIDATES / f"{CID}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(candidate, sort_keys=True) + "\n", encoding="utf-8")
    state = {"core_claim_review_queue": [{
        "candidate_id": CID,
        "claim_ids": ["FAR-CORE-001"],
        "downstream_claim_ids": ["FAR-CORE-002"],
        "attention_terms": ["counterexample"],
    }]}
    p = root / ar.STATE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, sort_keys=True) + "\n", encoding="utf-8")


def screening_record(*, relevant: bool = True, claim: str = "FAR-CORE-001", source: str = URL):
    return {
        "primary_source_verified": True,
        "relevant": relevant,
        "source_urls_used": [source],
        "evaluated_claim_ids": [claim],
        "claim_assessments": [{
            "claim_id": claim,
            "relevant": relevant,
            "premise_match": relevant,
            "scope_match": relevant,
            "reason": "direct",
        }],
        "affected_claim_ids": [claim] if relevant else [],
        "premise_match": relevant,
        "scope_match": relevant,
        "summary": "direct",
        "evidence_locations": ["source"],
        "limits": [],
    }


def attack_record(
    *,
    contradiction: bool,
    claim: str = "FAR-CORE-001",
    source: str = URL,
    prior: bool = False,
    strength: str | None = None,
):
    resolved_strength = strength if strength is not None else ("DIRECT" if prior else "NONE")
    return {
        "contradiction_found": contradiction,
        "prior_art_found": prior,
        "prior_art_strength": resolved_strength,
        "source_urls_used": [source],
        "evaluated_claim_ids": [claim],
        "claim_assessments": [{
            "claim_id": claim,
            "contradiction_found": contradiction,
            "prior_art_found": prior,
            "prior_art_strength": resolved_strength,
            "reason": "attack",
        }],
        "affected_claim_ids": [claim] if (contradiction or prior) else [],
        "exact_reason": "attack",
        "reproducible_attack": "repro" if contradiction else "",
        "source_locations": ["source"],
        "limits": [],
    }


def replication_record(
    *,
    contradiction: bool,
    reproduced: bool,
    claim: str = "FAR-CORE-001",
    source: str = URL,
    prior: bool = False,
    strength: str | None = None,
):
    resolved_strength = strength if strength is not None else ("DIRECT" if prior else "NONE")
    return {
        "contradiction_found": contradiction,
        "prior_art_found": prior,
        "prior_art_strength": resolved_strength,
        "source_urls_used": [source],
        "evaluated_claim_ids": [claim],
        "claim_assessments": [{
            "claim_id": claim,
            "contradiction_found": contradiction,
            "prior_art_found": prior,
            "prior_art_strength": resolved_strength,
            "attack_reproduced": reproduced,
            "reason": "replication",
        }],
        "affected_claim_ids": [claim] if (contradiction or prior) else [],
        "independent_reason": "replication",
        "attack_reproduced": reproduced,
        "source_locations": ["source"],
        "limits": [],
    }


def decision_record(disposition: str, *, implementation_required: bool = False):
    project = disposition == "PROJECT_CHANGE_REQUIRED"
    return {
        "disposition": disposition,
        "project_change_required": project,
        "scientific_targets": ["docs/research/living-autonomous-test.md"] if project else [],
        "implementation_required": implementation_required,
        "implementation_targets": ["tools/living-autonomous-test.py"] if implementation_required else [],
        "rationale": "decision",
        "limits": [],
    }


class AutonomousLivingReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.source = Path(self.tmp.name)
        source_fixture(self.source)

    def tearDown(self):
        self.tmp.cleanup()

    def test_generate_content_uses_documented_structured_output_shape(self):
        schema = ar.object_schema({"ok": ar.BOOL}, ["ok"])
        self.assertIs(False, schema["additionalProperties"])
        config = ar.generation_config(schema)
        self.assertEqual("application/json", config["responseMimeType"])
        self.assertEqual(schema, config["responseSchema"])
        self.assertNotIn("responseFormat", config)
        self.assertIn("claim_assessments", ar.SCREEN_SCHEMA["required"])
        self.assertIn("claim_assessments", ar.ATTACK_SCHEMA["required"])
        self.assertIn("claim_assessments", ar.REPLICATION_SCHEMA["required"])

    def test_structured_output_primary_and_legacy_shapes(self):
        schema = ar.object_schema({"ok": ar.BOOL}, ["ok"])
        config = ar.generation_config(schema)
        self.assertEqual("application/json", config["responseMimeType"])
        self.assertEqual(schema, config["responseSchema"])
        self.assertNotIn("responseFormat", config)

    def test_model_uses_single_generate_content_request_without_400_probe(self):
        payload = {
            "modelVersion": "gemini-test",
            "responseId": "response-1",
            "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": '{"ok": true}'}]}}],
        }
        model = ar.GeminiModel("gemini-3.8-flash", "key")
        with mock.patch.object(model, "_call", return_value=payload) as call:
            result, metadata = model.generate(
                role="test", prompt="x", schema=ar.object_schema({"ok": ar.BOOL}, ["ok"]),
            )
        self.assertEqual({"ok": True}, result)
        self.assertEqual(1, call.call_count)
        body = call.call_args.args[0]
        self.assertEqual("application/json", body["generationConfig"]["responseMimeType"])
        self.assertNotIn("responseFormat", body["generationConfig"])
        self.assertEqual("generateContent.responseSchema", metadata["structured_output_mode"])

    def test_http_400_retries_legacy_structured_output(self):
        model = ar.GeminiModel("gemini-3.8-flash", "key")
        error = ar.ModelRequestError("Gemini HTTP 400: invalid request")
        with mock.patch.object(model, "_call", side_effect=error) as call:
            with self.assertRaisesRegex(ar.ModelRequestError, "HTTP 400"):
                model.generate(role="test", prompt="x", schema=ar.object_schema({"ok": ar.BOOL}, ["ok"]))
        self.assertEqual(1, call.call_count)

    def test_non_stop_model_output_is_rejected(self):
        payload = {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": '{"ok": true}'}]}}]}
        model = ar.GeminiModel("gemini-3.8-flash", "key")
        with mock.patch.object(model, "_call", return_value=payload):
            with self.assertRaisesRegex(ar.CandidateReviewError, "did not complete normally"):
                model.generate(role="test", prompt="x", schema=ar.object_schema({"ok": ar.BOOL}, ["ok"]))

    def test_multiple_model_candidates_are_rejected(self):
        payload = {"candidates": [
            {"finishReason": "STOP", "content": {"parts": [{"text": '{"ok": true}'}]}},
            {"finishReason": "STOP", "content": {"parts": [{"text": '{"ok": true}'}]}},
        ]}
        model = ar.GeminiModel("gemini-3.8-flash", "key")
        with mock.patch.object(model, "_call", return_value=payload):
            with self.assertRaisesRegex(ar.CandidateReviewError, "candidate count"):
                model.generate(role="test", prompt="x", schema=ar.object_schema({"ok": ar.BOOL}, ["ok"]))

    def test_screening_uses_url_context_without_broad_search(self):
        payload = {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": '{"ok": true}'}]}}]}
        model = ar.GeminiModel("gemini-3.8-flash", "key")
        with mock.patch.object(model, "_call", return_value=payload) as call:
            model.generate(role="screening", prompt=f"source {URL}", schema=ar.object_schema({"ok": ar.BOOL}, ["ok"]), urls=[URL])
        self.assertEqual([{"url_context": {}}], call.call_args.args[0]["tools"])

    def test_successful_retrieval_status_requires_exact_enum(self):
        suspicious = {"url_context_metadata": {"urlMetadata": [{
            "retrievedUrl": URL,
            "urlRetrievalStatus": "URL_RETRIEVAL_STATUS_NOT_SUCCESS",
        }]}}
        self.assertEqual(set(), ar.successful_retrieval_urls(suspicious))

    def test_duplicate_affected_claim_ids_are_rejected(self):
        with self.assertRaisesRegex(ar.CandidateReviewError, "duplicates"):
            ar.validate_claim_ids(["FAR-CORE-001", "FAR-CORE-001"], {"FAR-CORE-001"}, "attack")

    def test_evaluated_claim_ids_cannot_substitute_for_per_claim_assessments(self):
        record = screening_record()
        record["evaluated_claim_ids"] = ["FAR-CORE-001", "FAR-CORE-002"]
        with self.assertRaisesRegex(ar.CandidateReviewError, "per-claim assessment coverage"):
            ar.require_full_claim_coverage(record, {"FAR-CORE-001", "FAR-CORE-002"}, "screening")

    def test_per_claim_and_aggregate_findings_must_agree(self):
        record = attack_record(contradiction=False)
        record["claim_assessments"][0]["contradiction_found"] = True
        with self.assertRaisesRegex(ar.CandidateReviewError, "affected_claim_ids disagree|aggregate contradiction disagrees"):
            ar.require_full_claim_coverage(record, {"FAR-CORE-001"}, "attack")

    def test_candidate_identity_binds_id_source_key_and_source_record(self):
        candidate_path = self.source / ar.CANDIDATES / f"{CID}.json"
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        self.assertTrue(ar.candidate_identity_valid(candidate))
        tampered_key = dict(candidate)
        tampered_key["source_key"] = "doi:10.9999/tampered"
        self.assertFalse(ar.candidate_identity_valid(tampered_key))
        rebound = dict(candidate)
        rebound["source_key"] = "doi:10.9999/tampered"
        rebound["candidate_id"] = "FAR-LIT-" + ar.digest(rebound["source_key"].encode("utf-8"))[:16].upper()
        self.assertFalse(ar.candidate_identity_valid(rebound))

    def test_candidate_urls_ignore_unbound_extra_source_rows(self):
        candidate_path = self.source / ar.CANDIDATES / f"{CID}.json"
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        candidate["sources"].insert(0, {
            "provider": "Crossref", "doi": "10.9999/poison", "url": "https://example.invalid/poison",
        })
        self.assertTrue(ar.candidate_identity_valid(candidate))
        self.assertEqual([URL], ar.candidate_urls(candidate, 10))

    def test_fallback_discovery_identity_fails_closed_for_autonomous_review(self):
        source_key = "crossref-fallback:" + "a" * 64
        candidate = {
            "candidate_id": "FAR-LIT-" + ar.digest(source_key.encode("utf-8"))[:16].upper(),
            "source_key": source_key,
            "sources": [{"provider": "Crossref", "url": "https://example.invalid/fallback"}],
        }
        self.assertFalse(ar.candidate_identity_valid(candidate))
        self.assertEqual([], ar.candidate_urls(candidate, 10))

    def test_tampered_candidate_identity_is_blocked_before_model_use(self):
        candidate_path = self.source / ar.CANDIDATES / f"{CID}.json"
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        candidate["source_key"] = "doi:10.9999/tampered"
        candidate_path.write_text(json.dumps(candidate, sort_keys=True) + "\n", encoding="utf-8")
        model = FakeModel("ADJACENT_NO_CONTRADICTION")
        plan = ar.build_plan(ROOT, self.source, model, NOW)
        self.assertEqual("source_blocked", plan["status"])
        self.assertEqual([], model.calls)

    def test_source_verification_failure_records_retry_only(self):
        plan = ar.build_plan(ROOT, self.source, FakeModel("ADJACENT_NO_CONTRADICTION", verified=False), NOW)
        self.assertEqual("source_blocked", plan["status"])
        self.assertFalse(plan["review_files"])
        self.assertTrue(any("autonomous-review-attempts" in p for p in plan["inbox_files"]))

    def test_source_url_claim_must_match_successful_retrieval(self):
        plan = ar.build_plan(ROOT, self.source, FakeModel("ADJACENT_NO_CONTRADICTION", retrieved_url="https://example.invalid/not-source"), NOW)
        self.assertEqual("source_blocked", plan["status"])
        record = json.loads(next(iter(plan["inbox_files"].values())))
        self.assertIn("not successfully retrieved", record["reason"])

    def test_model_failure_is_backed_off_instead_of_starving_queue(self):
        plan = ar.build_plan(ROOT, self.source, FakeModel("ADJACENT_NO_CONTRADICTION", fail_role="attack"), NOW)
        self.assertEqual("review_retry_blocked", plan["status"])
        attempt_path, attempt_raw = next(iter(plan["inbox_files"].items()))
        target = self.source / attempt_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(attempt_raw)
        self.assertIsNone(ar.select_candidate(ROOT, self.source, NOW))

    def test_queue_candidate_claim_binding_drift_is_blocked_before_model_use(self):
        candidate_path = self.source / ar.CANDIDATES / f"{CID}.json"
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        candidate["potential_claim_ids"] = ["FAR-CORE-002"]
        candidate_path.write_text(json.dumps(candidate, sort_keys=True) + "\n", encoding="utf-8")
        model = FakeModel("ADJACENT_NO_CONTRADICTION")
        plan = ar.build_plan(ROOT, self.source, model, NOW)
        self.assertEqual("review_retry_blocked", plan["status"])
        self.assertEqual([], model.calls)

    def test_candidate_level_disposition_requires_every_frozen_claim_evaluated(self):
        candidate_path = self.source / ar.CANDIDATES / f"{CID}.json"
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        candidate["potential_claim_ids"] = ["FAR-CORE-001", "FAR-CORE-002"]
        candidate_path.write_text(json.dumps(candidate, sort_keys=True) + "\n", encoding="utf-8")
        state_path = self.source / ar.STATE
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["core_claim_review_queue"][0]["claim_ids"] = ["FAR-CORE-001", "FAR-CORE-002"]
        state_path.write_text(json.dumps(state, sort_keys=True) + "\n", encoding="utf-8")
        plan = ar.build_plan(ROOT, self.source, FakeModel("ADJACENT_NO_CONTRADICTION"), NOW)
        self.assertEqual("review_retry_blocked", plan["status"])
        record = json.loads(next(iter(plan["inbox_files"].values())))
        self.assertIn("incomplete frozen claim coverage", record["reason"])

    def test_adjacent_review_prepares_snapshot_authority(self):
        model = FakeModel("ADJACENT_NO_CONTRADICTION")
        plan = ar.build_plan(ROOT, self.source, model, NOW)
        self.assertEqual("review_ready", plan["status"])
        self.assertEqual(["screening", "attack", "replication", "adjudication"], model.calls)
        self.assertFalse(plan["inbox_files"])
        snapshots = json.loads(plan["review_files"][ar.SNAPSHOT_AUTHS.as_posix()])
        self.assertEqual(CID, snapshots["authorizations"][-1]["candidate_id"])
        execution_path = next(p for p in plan["review_files"] if p.endswith("/execution.json"))
        execution = json.loads(plan["review_files"][execution_path])
        self.assertIn("adjudication", execution["model_metadata"])

    def test_irrelevant_false_positive_requires_irrelevant_screen_and_has_no_snapshot_authorization(self):
        plan = ar.build_plan(ROOT, self.source, FakeModel("IRRELEVANT_FALSE_POSITIVE"), NOW)
        self.assertEqual("review_ready", plan["status"])
        self.assertNotIn(ar.SNAPSHOT_AUTHS.as_posix(), plan["review_files"])
        bad = ar.build_plan(ROOT, self.source, FakeModel("IRRELEVANT_FALSE_POSITIVE", screening_relevant=True), NOW)
        self.assertEqual("review_retry_blocked", bad["status"])

    def test_irrelevant_false_positive_has_no_snapshot_authorization(self):
        plan = ar.build_plan(ROOT, self.source, FakeModel("IRRELEVANT_FALSE_POSITIVE"), NOW)
        self.assertEqual("review_ready", plan["status"])
        self.assertNotIn(ar.SNAPSHOT_AUTHS.as_posix(), plan["review_files"])

    def test_adjacent_disposition_cannot_override_irrelevant_screen(self):
        policy = ar.load_json(ROOT / ar.POLICY)
        with self.assertRaisesRegex(ar.CandidateReviewError, "requires screening relevance"):
            ar.validate_decision(
                decision_record("ADJACENT_NO_CONTRADICTION"), policy, ROOT, {"FAR-CORE-001"},
                screening_record(relevant=False), attack_record(contradiction=False),
                replication_record(contradiction=False, reproduced=False), meta(), meta(), meta(),
            )

    def test_project_change_requires_explicit_contradiction_flags(self):
        plan = ar.build_plan(ROOT, self.source, FakeModel("PROJECT_CHANGE_REQUIRED", contradiction_flags=False), NOW)
        self.assertEqual("review_retry_blocked", plan["status"])
        record = json.loads(next(iter(plan["inbox_files"].values())))
        self.assertIn("contradiction", record["reason"])

    def test_contradiction_role_disagreement_is_retry_blocked(self):
        policy = ar.load_json(ROOT / ar.POLICY)
        with self.assertRaisesRegex(ar.CandidateReviewError, "contradiction disagreement"):
            ar.validate_decision(
                decision_record("ADJACENT_NO_CONTRADICTION"), policy, ROOT, {"FAR-CORE-001"},
                screening_record(), attack_record(contradiction=True),
                replication_record(contradiction=False, reproduced=False), meta(), meta(), meta(),
            )

    def test_reproduced_contradiction_cannot_be_downgraded(self):
        policy = ar.load_json(ROOT / ar.POLICY)
        with self.assertRaisesRegex(ar.CandidateReviewError, "downgraded"):
            ar.validate_decision(
                decision_record("ADJACENT_NO_CONTRADICTION"), policy, ROOT, {"FAR-CORE-001"},
                screening_record(), attack_record(contradiction=True),
                replication_record(contradiction=True, reproduced=True), meta(), meta(), meta(),
            )

    def test_project_change_requires_screening_attack_replication_same_claim(self):
        policy = ar.load_json(ROOT / ar.POLICY)
        with self.assertRaisesRegex(ar.CandidateReviewError, "common exact claim|exact screening"):
            ar.validate_decision(
                decision_record("PROJECT_CHANGE_REQUIRED"), policy, ROOT, {"FAR-CORE-001", "FAR-CORE-002"},
                screening_record(claim="FAR-CORE-001"), attack_record(contradiction=True, claim="FAR-CORE-002"),
                replication_record(contradiction=True, reproduced=True, claim="FAR-CORE-002"), meta(), meta(), meta(),
            )

    def test_project_change_requires_common_primary_source_across_roles(self):
        policy = ar.load_json(ROOT / ar.POLICY)
        other = "https://example.org/other"
        with self.assertRaisesRegex(ar.CandidateReviewError, "common retrieved primary source"):
            ar.validate_decision(
                decision_record("PROJECT_CHANGE_REQUIRED"), policy, ROOT, {"FAR-CORE-001"},
                screening_record(source=URL), attack_record(contradiction=True, source=other),
                replication_record(contradiction=True, reproduced=True, source=other),
                meta(retrieved_url=URL), meta(retrieved_url=other), meta(retrieved_url=other),
            )

    def test_non_project_disposition_cannot_smuggle_implementation_work(self):
        policy = ar.load_json(ROOT / ar.POLICY)
        with self.assertRaisesRegex(ar.CandidateReviewError, "non-project-change.*implementation"):
            ar.validate_decision(
                decision_record("ADJACENT_NO_CONTRADICTION", implementation_required=True), policy, ROOT,
                {"FAR-CORE-001"}, screening_record(), attack_record(contradiction=False),
                replication_record(contradiction=False, reproduced=False), meta(), meta(), meta(),
            )

    def test_prior_art_lead_requires_both_roles_and_direct_strength(self):
        plan = ar.build_plan(ROOT, self.source, FakeModel("N1_PRIOR_ART_LEAD", prior_art_flags=False), NOW)
        self.assertEqual("review_retry_blocked", plan["status"])
        plan = ar.build_plan(ROOT, self.source, FakeModel("N1_PRIOR_ART_LEAD", prior_art_strength="ADJACENT"), NOW)
        self.assertEqual("review_retry_blocked", plan["status"])

    def test_prior_art_flag_and_strength_must_be_consistent(self):
        with self.assertRaisesRegex(ar.CandidateReviewError, "must be NONE"):
            ar.validate_finding_record(
                "attack", attack_record(contradiction=False, prior=False, strength="DIRECT"), meta(), attack_record=True,
            )

    def test_all_noop_scientific_correction_is_rejected_even_for_absent_empty_file(self):
        plan = ar.build_plan(ROOT, self.source, FakeModel("PROJECT_CHANGE_REQUIRED", no_op_scientific=True), NOW)
        self.assertEqual("review_retry_blocked", plan["status"])
        record = json.loads(next(iter(plan["inbox_files"].values())))
        self.assertIn("no-op", record["reason"])

    def test_all_noop_scientific_correction_is_rejected(self):
        plan = ar.build_plan(ROOT, self.source, FakeModel("PROJECT_CHANGE_REQUIRED", no_op_scientific=True), NOW)
        self.assertEqual("review_retry_blocked", plan["status"])
        record = json.loads(next(iter(plan["inbox_files"].values())))
        self.assertIn("no-op", record["reason"])

    def test_partial_noop_replacement_set_is_rejected(self):
        with self.assertRaisesRegex(ar.CandidateReviewError, "no-op targets: a"):
            ar.validate_replacement_set(
                kind="scientific", targets=["a", "b"], current_raw={"a": b"same", "b": b"old"},
                out={"a": b"same", "b": b"new"}, max_bytes=100,
            )

    def test_combined_replacement_bound_applies_across_scientific_and_implementation(self):
        with self.assertRaisesRegex(ar.CandidateReviewError, "combined replacement byte bound"):
            ar.enforce_total_replacement_bytes(5, {"a": b"123"}, {"b": b"456"})

    def test_project_change_proposal_bytes_live_only_on_human_review_pr(self):
        plan = ar.build_plan(ROOT, self.source, FakeModel("PROJECT_CHANGE_REQUIRED", implementation=True), NOW)
        self.assertEqual("review_ready", plan["status"])
        self.assertFalse(plan["inbox_files"])
        review_paths = set(plan["review_files"])
        self.assertTrue(any(p.startswith(ar.PROMOTION_PROPOSALS.as_posix() + "/") for p in review_paths))
        self.assertTrue(any(p.startswith(ar.PROMOTION_PAYLOADS.as_posix() + "/") for p in review_paths))
        self.assertTrue(any(p.startswith(ar.IMPLEMENTATION_PROPOSALS.as_posix() + "/") for p in review_paths))
        self.assertTrue(any(p.startswith(ar.IMPLEMENTATION_PAYLOADS.as_posix() + "/") for p in review_paths))

    def test_materializer_separates_review_and_retry_surfaces(self):
        plan = ar.build_plan(ROOT, self.source, FakeModel("ADJACENT_NO_CONTRADICTION"), NOW)
        out = self.source / "out"
        ar.materialize(plan, out)
        self.assertTrue((out / "manifest.json").is_file())
        self.assertTrue((out / "review" / ar.REVIEWS).is_file())
        self.assertFalse((out / "inbox" / ar.REVIEWS).exists())

    def test_privileged_review_archives_only_validated_data(self):
        workflow = (ROOT / ".github/workflows/living-autonomous-review-v2.yml").read_text(encoding="utf-8")
        extract = workflow.split("      - name: Extract exact inbox snapshot", 1)[1].split(
            "      - name: Execute bounded autonomous adjudication", 1)[0]
        self.assertIn("set -euo pipefail", extract)
        self.assertIn("snapshot_paths=(research/living/repository-state-v1.0.json)", extract)
        self.assertIn("research/living/inbox research/living/runs research/living/state-v1.0.json", extract)
        self.assertIn('python tools/validate_research_carry.py --ref "$source_sha" "${validation_args[@]}"', extract)
        self.assertIn('git archive --worktree-attributes "$source_sha" -- "${snapshot_paths[@]}"', extract)
        self.assertLess(extract.index("python tools/validate_research_carry.py"), extract.index("git archive"))
        self.assertNotIn('git archive "${{ steps.freeze.outputs.source_sha }}" |', extract)

    def test_research_carry_validator_rejects_symlinked_state_and_accepts_blob(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
            rel = "research/living/repository-state-v1.0.json"
            state = repo / rel
            state.parent.mkdir(parents=True)
            state.symlink_to("/scratch/outside.json")
            subprocess.run(["git", "-C", str(repo), "add", "--", rel], check=True)
            subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture",
                            "-c", "user.email=fixture@example.invalid", "commit", "-qm", "symlink"], check=True)
            with self.assertRaisesRegex(ValueError, "forbidden carried git object"):
                validate_ref_paths(repo, "HEAD", [rel])
            state.unlink()
            state.write_text('{"core_claim_review_queue":[]}', encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "--", rel], check=True)
            subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture",
                            "-c", "user.email=fixture@example.invalid", "commit", "-qm", "blob"], check=True)
            validate_ref_paths(repo, "HEAD", [rel])

    def test_validated_snapshot_preserves_retry_writer_inputs(self):
        # Reproduce the retry-only path's copy requirements from the exact
        # extraction inputs, including the permanent nonmergeable inbox anchor.
        workflow = (ROOT / ".github/workflows/living-autonomous-review-v2.yml").read_text(encoding="utf-8")
        extract = workflow.split("      - name: Extract exact inbox snapshot", 1)[1].split(
            "      - name: Execute bounded autonomous adjudication", 1)[0]
        retry = workflow.split("      - name: Persist bounded retry record only", 1)[1].split(
            "      - name: Materialize and validate human-review branch", 1)[0]
        paths = ("research/living/inbox", "research/living/runs",
                 "research/living/state-v1.0.json", "research/living/repository-state-v1.0.json")
        for path in paths:
            self.assertIn(path, extract)
            self.assertIn(path, retry)

        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
            files = {
                "research/living/inbox/.rolling-pr-anchor.json": "anchor",
                "research/living/inbox/candidates/candidate.json": "candidate",
                "research/living/runs/record.json": "run-history",
                "research/living/state-v1.0.json": "cursor",
                "research/living/repository-state-v1.0.json": "queue",
            }
            for rel, value in files.items():
                target = repo / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(value, encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "research/living"], check=True)
            subprocess.run(["git", "-C", str(repo), "-c", "user.name=Fixture",
                            "-c", "user.email=fixture@example.invalid", "commit",
                            "-qm", "carry"], check=True)
            validate_ref_paths(repo, "HEAD", list(paths))
            archive = subprocess.run(
                ["git", "-C", str(repo), "archive", "HEAD", "--", *paths],
                check=True, capture_output=True, timeout=10,
            ).stdout
            with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as bundle:
                members = {item.name.rstrip("/"): item for item in bundle.getmembers()}
                for rel, expected in files.items():
                    self.assertIn(rel, members)
                    self.assertTrue(members[rel].isfile())
                    self.assertEqual(expected.encode(), bundle.extractfile(members[rel]).read())

    def test_archive_ignores_untrusted_source_export_attributes(self):
        # A source-commit .gitattributes is outside the selected data paths
        # yet can silently substitute JSON bytes or export-ignore retry data.
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
            state_rel = "research/living/repository-state-v1.0.json"
            candidate_rel = "research/living/inbox/candidates/one.json"
            state = repo / state_rel
            candidate = repo / candidate_rel
            state.parent.mkdir(parents=True)
            candidate.parent.mkdir(parents=True)
            original_state = b'{"source":"$Format:%H$"}\n'
            original_candidate = b'{"candidate":"test"}\n'
            state.write_bytes(original_state)
            candidate.write_bytes(original_candidate)
            subprocess.run(["git", "-C", str(repo), "add", "research/living"], check=True)
            identity = ["git", "-C", str(repo), "-c", "user.name=Fixture",
                        "-c", "user.email=fixture@example.invalid"]
            subprocess.run([*identity, "commit", "-qm", "trusted"], check=True)
            subprocess.run(["git", "-C", str(repo), "branch", "-M", "main"], check=True)
            subprocess.run(["git", "-C", str(repo), "switch", "-q", "-c", "untrusted"], check=True)
            (repo / ".gitattributes").write_text(
                state_rel + " export-subst\n" + candidate_rel + " export-ignore\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "-C", str(repo), "add", ".gitattributes"], check=True)
            subprocess.run([*identity, "commit", "-qm", "untrusted-attributes"], check=True)
            source_sha = subprocess.run(
                ["git", "-C", str(repo), "rev-parse", "HEAD"],
                check=True, capture_output=True, text=True,
            ).stdout.strip()
            subprocess.run(["git", "-C", str(repo), "switch", "-q", "main"], check=True)
            validate_ref_paths(repo, source_sha, [state_rel, candidate_rel])

            def archived(*flags):
                payload = subprocess.run(
                    ["git", "-C", str(repo), "archive", *flags, source_sha,
                     "--", state_rel, candidate_rel],
                    check=True, capture_output=True, timeout=10,
                ).stdout
                with tarfile.open(fileobj=io.BytesIO(payload), mode="r:") as bundle:
                    return {
                        entry.name: bundle.extractfile(entry).read()
                        for entry in bundle.getmembers() if entry.isfile()
                    }

            unsafe = archived()
            self.assertNotEqual(original_state, unsafe[state_rel])
            self.assertNotIn(candidate_rel, unsafe)
            safe = archived("--worktree-attributes")
            self.assertEqual(original_state, safe[state_rel])
            self.assertEqual(original_candidate, safe[candidate_rel])

    def test_workflow_contains_race_serialization_retry_validation_and_explicit_dispatch_guards(self):
        workflow = (ROOT / ".github/workflows/living-autonomous-review-v2.yml").read_text(encoding="utf-8")
        self.assertIn("headRepositoryOwner", workflow)
        self.assertIn("$GITHUB_RUN_ATTEMPT", workflow)
        self.assertIn("main advanced during autonomous review", workflow)
        self.assertIn("living inbox advanced during autonomous review", workflow)
        self.assertIn("retry-only inbox push head mismatch", workflow)
        self.assertIn("gh workflow run validator-assurance.yml", workflow)
        self.assertIn("gh workflow run living-research.yml", workflow)
        self.assertIn("gh workflow run living-autonomous-review-v2.yml", workflow)
        self.assertIn(
            'gh workflow run living-research.yml --repo "$GITHUB_REPOSITORY" --ref "$SOURCE_BRANCH" -f mode=validate', workflow,
        )
        self.assertNotIn("Persist generated inbox data transactionally", workflow)

    def test_workflow_contains_race_serialization_and_explicit_dispatch_guards(self):
        workflow = (ROOT / ".github/workflows/living-autonomous-review-v2.yml").read_text(encoding="utf-8")
        self.assertIn("headRepositoryOwner", workflow)
        self.assertIn("$GITHUB_RUN_ATTEMPT", workflow)
        self.assertIn("main advanced during autonomous review", workflow)
        self.assertIn("living inbox advanced during autonomous review", workflow)
        self.assertIn("gh workflow run validator-assurance.yml", workflow)
        self.assertIn("gh workflow run living-autonomous-review-v2.yml", workflow)


if __name__ == "__main__":
    unittest.main()
