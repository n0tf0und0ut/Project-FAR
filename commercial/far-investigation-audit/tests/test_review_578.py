"""PR #578 review-counterexample tests: deliberately adversarial inputs.

Each regression is keyed to a violated invariant rather than a reviewer comment ID.
No test authenticates external sources, semantic mapping, or real-world verdicts.
"""
from __future__ import annotations

import copy
import json
import base64
from types import SimpleNamespace
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from engine import InvalidBundle, audit, digest
from full_cli import write_package, verify_package
from independent_check import IndependentCheckError, check_report
from presentation import render_markdown
from workflow import investigate

CUTOFF = "2026-10-17T12:00:00Z"


def source(sid, text, *, origin=None):
    return {"id": sid, "text": text, "sha256": digest(text.encode("utf-8")),
            "origin_id": origin, "published_at": "2026-10-16T12:00:00Z",
            "captured_at": CUTOFF, "publication_date_verified": True,
            "origin_verified": False}


def bundle(primary="Exactly 1 row reported.", secondary="One observation supports the record."):
    return {
        "schema": "far-investigation-audit/0.1", "investigation_id": "review_578",
        "as_of": CUTOFF, "atoms": {"P": "A declared observation"},
        "sources": [source("primary", primary), source("ev1", secondary, origin="origin-A")],
        "claims": [{"id": "c1", "text": primary, "source_id": "primary",
                    "span": {"start": 0, "end": len(primary), "quote": primary},
                    "formula": {"atom": "P"}, "mapping_status": "unreviewed"}],
        "evidence": [{"id": "e1", "claim_id": "c1", "source_id": "ev1",
                      "span": {"start": 0, "end": len(secondary), "quote": secondary},
                      "formula": {"atom": "P"}, "relation": "supports",
                      "mapping_status": "unreviewed"}],
        "interpretations": [], "unknowns": []}


class Review578RegressionTests(unittest.TestCase):
    def test_replay_method_downgrade_cannot_keep_original_audit_identity(self):
        pkg = investigate({"investigation_id": "capture_commitment",
                           "captured_at": CUTOFF,
                           "source": {"kind": "text", "text": "There are exactly six items."}})
        old_identity = pkg["audit"]["report_sha256"]
        self.assertEqual(pkg["acquisition"][0]["extraction"], "text_provided_v1")
        pkg["acquisition"][0]["extraction"] = "pypdf_text_v1"
        pkg["acquisition"][0].pop("raw_snapshot_utf8")
        pkg["report_md"] = render_markdown(pkg["bundle"], pkg["audit"],
                                           acquisition=pkg["acquisition"],
                                           discovery=pkg["discovery"],
                                           questions=pkg["critical_questions"])
        pkg["manifest"]["report_md_sha256"] = digest(pkg["report_md"].encode("utf-8"))
        self.assertEqual(pkg["audit"]["report_sha256"], old_identity)
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "pkg"
            write_package(path, pkg)
            with self.assertRaisesRegex(InvalidBundle, "acquisition commitment mismatch"):
                verify_package(path)

    def test_source_origin_must_be_checked_independently(self):
        b = bundle()
        wrong = copy.deepcopy(audit(b))
        wrong["claims"]["c1"]["evidence"][0]["origin_id"] = "origin-B"
        wrong["claims"]["c1"]["support_origin_ids"] = ["origin-B"]
        with self.assertRaisesRegex(IndependentCheckError, "origin"):
            check_report(b, wrong)

    def test_overlapping_same_source_claim_is_not_corrobating_evidence(self):
        b = bundle()
        b["evidence"][0]["source_id"] = "primary"
        text = b["sources"][0]["text"]
        b["evidence"][0]["span"] = {"start": 0, "end": len(text) - 1,
                                    "quote": text[:-1]}
        result = audit(b)
        self.assertEqual(result["claims"]["c1"]["status"], "NOT_ESTABLISHED")
        self.assertEqual(result["claims"]["c1"]["evidence"][0]["formal_relation"],
                         "SELF_REFERENCE_NOT_CORROBORATION")
        self.assertTrue(check_report(b, result)["independent_algorithm_agrees"])

    def test_independent_checker_detects_forged_structured_summary(self):
        b = bundle(secondary='[{"count": 1}]')
        b["claims"][0]["quantity"] = {
            "value": "1", "number_span": {"start": 8, "end": 9}, "unit": "rows"}
        b["evidence"][0].pop("formula")
        b["evidence"][0]["data_check"] = {"operation": "count_rows", "pointer": ""}
        report = audit(b)
        self.assertEqual(report["claims"]["c1"]["structured_value_checks"]["matches"], 1)
        self.assertTrue(check_report(b, report)["independent_algorithm_agrees"])
        forged = copy.deepcopy(report)
        forged["claims"]["c1"]["structured_value_checks"]["status"] = "CONFLICTING_STRUCTURED_VALUES"
        forged["claims"]["c1"]["structured_value_checks"]["matches"] = 0
        forged["claims"]["c1"]["structured_value_checks"]["mismatches"] = 99
        with self.assertRaisesRegex(IndependentCheckError, "structured.*summary"):
            check_report(b, forged)

    def test_remote_capture_is_recorded_after_fetch_not_at_cutoff(self):
        raw = "<p>This example asserts a concrete measured result.</p>"
        text = "This example asserts a concrete measured result."
        def fake_fetch(url, *, permit_network):
            self.assertTrue(permit_network)
            return {"text": text, "raw_snapshot_utf8": raw,
                    "raw_sha256": digest(raw.encode("utf-8")),
                    "extraction": "html_visible_text_v1", "url": url}
        with patch("workflow._now", side_effect=["2026-10-20T00:00:00Z",
                                                  "2026-10-20T00:00:05Z"]):
            pkg = investigate({"source": {"kind": "url",
                                         "url": "https://example.net/observation"}},
                              permit_network=True, source_fetcher=fake_fetch)
        self.assertEqual(pkg["bundle"]["as_of"], "2026-10-20T00:00:00Z")
        self.assertEqual(pkg["bundle"]["sources"][0]["captured_at"],
                         "2026-10-20T00:00:05Z")
        self.assertEqual(pkg["audit"]["source_temporal_status"]["primary"],
                         "AFTER_CUTOFF_OR_UNVERIFIED_HISTORICAL_VERSION")

    def test_report_escapes_untrusted_html_and_markdown(self):
        text = "Exactly 1 row reported."
        proposal = {"method": "supplied", "claims": [{"id": "c1", "quote": text}],
                    "unknowns": ["<img src=x onerror=alert(1)>",
                                 "[forged link](https://evil.example)"],
                    "arguments": []}
        pkg = investigate({"captured_at": CUTOFF, "source": {"kind": "text", "text": text},
                           "proposal_mode": "supplied", "proposal": proposal})
        md = pkg["report_md"]
        self.assertNotIn("<img", md)
        self.assertNotIn("[forged link](https://evil.example)", md)
        self.assertIn("&lt;img", md)
        with tempfile.TemporaryDirectory() as tmp:
            target = pathlib.Path(tmp) / "pkg"
            write_package(target, pkg)
            self.assertTrue(verify_package(target)["replay_match"])


    def test_report_quote_preserves_exact_markup_and_backticks_as_code(self):
        quote = "Record <img src=x onerror=alert(1)> contains ``` markup."
        proposal = {"method": "supplied", "claims": [{"id": "c1", "quote": quote}],
                    "unknowns": [], "arguments": []}
        pkg = investigate({"captured_at": CUTOFF, "source": {"kind": "text", "text": quote},
                           "proposal_mode": "supplied", "proposal": proposal})
        md = pkg["report_md"]
        # An adaptive backtick fence keeps raw HTML inert in Markdown while
        # preserving the exact quoted bytes for visual forensic inspection.
        self.assertIn("\n````text\n" + quote + "\n````\n", md)
        self.assertEqual(pkg["bundle"]["claims"][0]["span"]["quote"], quote)
        with tempfile.TemporaryDirectory() as tmp:
            target = pathlib.Path(tmp) / "pkg"
            write_package(target, pkg)
            self.assertTrue(verify_package(target)["replay_match"])




    def test_numeric_oracle_respects_bounded_decimal_contract(self):
        b = bundle(secondary='{"rows":[{"x":1e100}]}')
        b["claims"][0]["quantity"] = {
            "value": "1", "number_span": {"start": 8, "end": 9}, "unit": "rows"}
        b["evidence"][0].pop("formula")
        b["evidence"][0]["data_check"] = {
            "operation": "sum_field", "pointer": "/rows", "field": "x"}
        report = audit(b)
        self.assertEqual(report["claims"]["c1"]["evidence"][0]["structured_check"]["status"],
                         "STRUCTURED_UNVERIFIABLE")
        self.assertTrue(check_report(b, report)["independent_algorithm_agrees"])

    def test_external_model_proposal_declares_provider_network_usage(self):
        raw = "Exactly 1 row reported."
        response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
            content=json.dumps({"claims": [{"id": "c1", "quote": raw, "source_id": "primary"}],
                                "unknowns": [], "evidence": [], "arguments": []})))])
        fake = SimpleNamespace(chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kwargs: response)))
        pkg = investigate({"captured_at": CUTOFF, "source": {"kind": "text", "text": raw},
                           "proposal_mode": "openai"}, permit_model=True, model_client=fake)
        self.assertTrue(pkg["manifest"]["network_used"])

    def test_external_transcription_declares_provider_network_usage(self):
        fake_transcription = {
            "text": "Exactly 1 row reported.", "raw_sha256": "0" * 64,
            "extraction": "external_speech_transcription_gpt_4o_transcribe_v1",
            "transcript_model": "gpt-4o-transcribe"}
        with patch("workflow.read_local_file", return_value=fake_transcription):
            pkg = investigate({"captured_at": CUTOFF,
                               "source": {"kind": "media_file", "path": "/fictional.wav"}},
                              permit_files=True, permit_model=True)
        self.assertTrue(pkg["manifest"]["network_used"])

    def test_signed_review_rejects_ambiguous_cross_type_object_identity(self):
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
            from cryptography.hazmat.primitives import serialization
        except ImportError:
            self.skipTest("optional Ed25519 review backend unavailable")
        from review import verify_review
        b = bundle()
        b["evidence"][0]["id"] = "c1"  # Same ID as a different claim object.
        report = audit(b)
        record = {"schema": "far-review-attestation/1.0",
                  "input_sha256": report["input_sha256"],
                  "report_sha256": report["report_sha256"],
                  "reviewer": "Independent reviewer label",
                  "decisions": [{"object_id": "c1", "decision": "agree", "notes": "ambiguous"}]}
        key = Ed25519PrivateKey.generate()
        public = key.public_key().public_bytes(serialization.Encoding.Raw,
                                               serialization.PublicFormat.Raw)
        signed = {"review": record, "public_key_b64": base64.b64encode(public).decode(),
                  "signature_b64": base64.b64encode(key.sign(
                      json.dumps(record, sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=False, allow_nan=False).encode())).decode()}
        with self.assertRaisesRegex(InvalidBundle, "ambiguous review object"):
            verify_review(signed, report)

    def test_checker_binds_reported_interpretation_operands_and_premises(self):
        b = json.loads((pathlib.Path(__file__).resolve().parents[1] /
                        "examples/causal_jump.json").read_text())
        report = audit(b)
        self.assertTrue(check_report(b, report)["independent_algorithm_agrees"])
        forged = copy.deepcopy(report)
        forged["interpretations"][0]["premises"] = []
        forged["interpretations"][0]["conclusion"] = b["interpretations"][0]["premises"][0]
        forged["interpretations"][0]["premises_without_uncontested_formal_evidence"] = []
        with self.assertRaisesRegex(IndependentCheckError, "interpretation .*mismatch"):
            check_report(b, forged)

    def test_checker_rejects_duplicate_interpretations_with_missing_reading(self):
        b = json.loads((pathlib.Path(__file__).resolve().parents[1] /
                        "examples/causal_jump.json").read_text())
        copied = copy.deepcopy(b["interpretations"][0])
        copied["id"] = "other_reading"
        b["interpretations"].append(copied)
        report = audit(b)
        self.assertTrue(check_report(b, report)["independent_algorithm_agrees"])
        forged = copy.deepcopy(report)
        forged["interpretations"][1] = copy.deepcopy(forged["interpretations"][0])
        with self.assertRaisesRegex(IndependentCheckError, "interpretation (?:coverage|duplicate)"):
            check_report(b, forged)




    def test_model_network_provenance_survives_manifest_replay(self):
        raw = "Exactly 1 row reported."
        response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
            content=json.dumps({"claims": [{"id": "c1", "quote": raw, "source_id": "primary"}],
                                "unknowns": [], "evidence": [], "arguments": []})))])
        fake = SimpleNamespace(chat=SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kwargs: response)))
        pkg = investigate({"captured_at": CUTOFF, "source": {"kind": "text", "text": raw},
                           "proposal_mode": "openai"}, permit_model=True, model_client=fake)
        with tempfile.TemporaryDirectory() as tmp:
            target = pathlib.Path(tmp) / "pkg"
            write_package(target, pkg)
            self.assertTrue(verify_package(target)["replay_match"])
            manifest_path = target / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            self.assertTrue(manifest["network_used"])
            # Manifest hashes are self-declared; verification must rebuild
            # the provider-boundary flag, not trust an unsigned field.
            manifest["network_used"] = False
            manifest_path.write_text(json.dumps(manifest, sort_keys=True,
                                                separators=(",", ":")) + "\n")
            with self.assertRaisesRegex(InvalidBundle, "network provenance mismatch"):
                verify_package(target)




if __name__ == "__main__":
    unittest.main()
