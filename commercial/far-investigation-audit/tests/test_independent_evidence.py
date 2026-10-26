"""Independent evidence-oracle regressions for PR #578."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import audit, digest
from independent_check import check_report, IndependentCheckError
from proposals import compile_proposal


def evidence_bundle(evidence_formula, *, separate=True):
    primary = "Rain is falling."
    supporting = "Evidence about rain."
    as_of = "2026-10-17T12:00:00Z"
    def src(sid, text):
        return {"id": sid, "text": text, "sha256": digest(text.encode()),
                "origin_id": None, "published_at": "2026-10-16T12:00:00Z",
                "captured_at": as_of, "publication_date_verified": True,
                "origin_verified": False}
    sources = [src("primary", primary), src("ev1", supporting)]
    claim = {"id": "c1", "text": primary, "source_id": "primary",
             "span": {"start": 0, "end": len(primary), "quote": primary},
             "formula": {"atom": "P"}, "mapping_status": "unreviewed"}
    evidence = {"id": "e1", "claim_id": "c1", "source_id": "ev1",
                "span": {"start": 0, "end": len(supporting), "quote": supporting},
                "formula": evidence_formula, "relation": "supports",
                "mapping_status": "unreviewed"}
    return {"schema": "far-investigation-audit/0.1", "investigation_id": "independent_evidence",
            "as_of": as_of, "atoms": {"P": "Rain falls", "Q": "Grass grows"},
            "sources": sources, "claims": [claim], "evidence": [evidence],
            "interpretations": [], "unknowns": []}


class IndependentEvidenceCheckTests(unittest.TestCase):
    def test_omitted_optional_evidence_and_unknowns_match_engine_defaults(self):
        # An empty list and an absent key have the same *declared input*
        # meaning, while the canonical input SHA still binds exact bytes.
        for omitted in (("unknowns",), ("evidence",), ("evidence", "unknowns")):
            bundle = evidence_bundle({"atom": "P"})
            for name in omitted:
                bundle.pop(name)
            with self.subTest(omitted=omitted):
                report = audit(bundle)
                result = check_report(bundle, report)
                self.assertTrue(result["independent_algorithm_agrees"])
                self.assertEqual(report["unknowns"], [])
                if "evidence" in omitted:
                    self.assertEqual(report["claims"]["c1"]["evidence"], [])
                tampered = copy.deepcopy(report)
                tampered["unknowns"] = ["forged open question"]
                with self.assertRaisesRegex(IndependentCheckError,
                                            "assurance boundary mismatch: unknowns"):
                    check_report(bundle, tampered)

    def test_rechecks_support_contradiction_and_inconsistency(self):
        cases = (
            ({"atom": "P"}, "FORMALLY_SUPPORTS_IF_MAPPINGS_CORRECT"),
            ({"not": {"atom": "P"}}, "FORMALLY_CONTRADICTS_IF_MAPPINGS_CORRECT"),
            ({"and": [{"atom": "P"}, {"not": {"atom": "P"}}]}, "INCONSISTENT_EVIDENCE_FORMULA"),
            ({"atom": "Q"}, "DOES_NOT_ESTABLISH"),
        )
        for formula, expected in cases:
            with self.subTest(expected=expected):
                bundle = evidence_bundle(formula)
                report = audit(bundle)
                self.assertEqual(report["claims"]["c1"]["evidence"][0]["formal_relation"], expected)
                result = check_report(bundle, report)
                self.assertTrue(result["independent_algorithm_agrees"])
                self.assertEqual(result["evidence_formulas_rechecked"], 1)

    def test_detects_forged_formal_evidence_and_claim_status(self):
        bundle = evidence_bundle({"atom": "P"})
        report = audit(bundle)
        tampered = copy.deepcopy(report)
        tampered["claims"]["c1"]["evidence"][0]["formal_relation"] = "DOES_NOT_ESTABLISH"
        tampered["claims"]["c1"]["status"] = "NOT_ESTABLISHED"
        with self.assertRaisesRegex(IndependentCheckError, "formal evidence mismatch"):
            check_report(bundle, tampered)

    def test_detects_forged_temporal_eligibility(self):
        bundle = evidence_bundle({"atom": "P"})
        report = audit(bundle)
        tampered = copy.deepcopy(report)
        tampered["source_temporal_status"]["ev1"] = "UNKNOWN_TEMPORAL_ELIGIBILITY"
        tampered["claims"]["c1"]["evidence"][0]["temporal_status"] = "UNKNOWN_TEMPORAL_ELIGIBILITY"
        tampered["claims"]["c1"]["evidence"][0]["formal_relation"] = "TEMPORAL_NOT_ADMISSIBLE"
        tampered["claims"]["c1"]["status"] = "NOT_ESTABLISHED"
        with self.assertRaisesRegex(IndependentCheckError, "temporal eligibility mismatch"):
            check_report(bundle, tampered)

    def test_detects_corrupted_countermodel(self):
        bundle = evidence_bundle({"atom": "Q"})
        report = audit(bundle)
        tampered = copy.deepcopy(report)
        tampered["claims"]["c1"]["evidence"][0]["countermodel"] = {"P": True, "Q": True}
        with self.assertRaisesRegex(IndependentCheckError, "countermodel mismatch"):
            check_report(bundle, tampered)

    def test_replay_rejects_unknown_method_relabel_even_with_rehashed_manifest(self):
        import hashlib
        import json
        import tempfile
        from full_cli import write_package, verify_package
        from workflow import investigate
        from engine import InvalidBundle, canonical
        config = {"investigation_id": "replay_method_attack",
                  "source": {"kind": "text", "text": "This is a concrete source sentence."},
                  "captured_at": "2026-10-17T12:00:00Z"}
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root) / "package"
            write_package(directory, investigate(config))
            self.assertTrue(verify_package(directory)["replay_match"])
            acquisition = json.loads((directory / "acquisition.json").read_bytes())
            acquisition[0]["extraction"] = "unrecognized_nonreplayable_attacker_label"
            acquisition[0].pop("raw_snapshot_utf8")
            replacement = canonical(acquisition) + b"\n"
            (directory / "acquisition.json").write_bytes(replacement)
            manifest = json.loads((directory / "manifest.json").read_bytes())
            manifest["files_sha256"]["acquisition.json"] = hashlib.sha256(replacement).hexdigest()
            (directory / "manifest.json").write_bytes(canonical(manifest) + b"\n")
            with self.assertRaisesRegex(InvalidBundle, "unrecognized acquisition extraction method"):
                verify_package(directory)

    def test_explicit_formula_with_implicit_claim_id(self):
        quote_a = "One premise is offered."
        quote_b = "A second conclusion is offered."
        source_text = quote_a + " " + quote_b
        proposal = {"claims": [
            {"quote": quote_a, "formula": {"atom": "P1"}},
            {"id": "c2", "quote": quote_b, "formula": {"atom": "P2"}}],
            "arguments": [{"id": "r1", "premises": ["c1"], "conclusion": "c2"}],
            "method": "supplied"}
        bundle = compile_proposal(proposal, {"primary": source_text},
            investigation_id="implicit_id", captured_at="2026-10-17T12:00:00Z",
            published_at_by_source={"primary": None})
        self.assertEqual(bundle["interpretations"][0]["formalization_basis"], "explicit_formulas")


if __name__ == "__main__":
    unittest.main()
