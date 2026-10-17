"""Adversarial regression tests. No model/network calls or subjective verdict fixtures."""
import copy
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from engine import InvalidBundle, audit, entailment


def atom(x):
    return {"atom": x}


def negate(x):
    return {"not": x}


def span(text):
    return {"start": 0, "end": len(text), "quote": text}


def source(id, text, origin=None, published="2026-01-01T00:00:00Z", captured="2026-01-02T00:00:00Z"):
    return {"id": id, "text": text, "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "origin_id": origin or id, "published_at": published, "captured_at": captured}


def base():
    return {"schema": "far-investigation-audit/0.1", "investigation_id": "test_case",
            "as_of": "2026-02-01T00:00:00Z", "atoms": {"P": "The observation occurred", "Q": "The proposed cause occurred"},
            "sources": [source("speech", "P was observed. Therefore Q was caused."),
                        source("record", "P was observed in the official record.")],
            "claims": [
                {"id": "p", "text": "P was observed.", "source_id": "speech", "span": {"start": 0, "end": 15, "quote": "P was observed."}, "formula": atom("P"), "mapping_status": "unreviewed"},
                {"id": "q", "text": "Q was caused.", "source_id": "speech", "span": {"start": 26, "end": 39, "quote": "Q was caused."}, "formula": atom("Q"), "mapping_status": "unreviewed"},
            ],
            "evidence": [{"id": "e1", "source_id": "record", "claim_id": "p", "span": span("P was observed in the official record."),
                          "relation": "supports", "formula": atom("P"), "mapping_status": "unreviewed"}],
            "interpretations": [{"id": "literal", "premises": ["p"], "conclusion": "q", "mapping_status": "unreviewed"}],
            "unknowns": ["Whether P is causally relevant to Q"]}


class InvestigationAuditTests(unittest.TestCase):
    def test_countermodel_for_true_premise_bad_causal_inference(self):
        report = audit(base())
        r = report["interpretations"][0]["formal_inference"]
        self.assertEqual(r["status"], "DOES_NOT_ENTAIL")
        self.assertEqual(r["countermodel"], {"P": True, "Q": False})
        self.assertEqual(report["claims"]["p"]["status"], "CONDITIONAL_FORMAL_SUPPORT_RECORDED")
        self.assertFalse(report["interpretations"][0]["semantic_fidelity_independently_verified"])
        self.assertEqual(report["unknowns"], ["Whether P is causally relevant to Q"])

    def test_modus_ponens_in_the_bounded_language(self):
        b = base()
        c = copy.deepcopy(b["claims"][0]); c.update(id="rule", formula={"implies": [atom("P"), atom("Q")]})
        b["claims"].append(c)
        b["interpretations"][0]["premises"] = ["p", "rule"]
        r = audit(b)
        self.assertEqual(r["interpretations"][0]["formal_inference"]["status"], "ENTAILS_CONDITIONALLY")
        self.assertEqual(r["interpretations"][0]["premises_without_uncontested_formal_evidence"], ["rule"])

    def test_inconsistent_premises_do_not_pass_by_vacuous_entailment(self):
        b = base()
        c = copy.deepcopy(b["claims"][0]); c.update(id="not_p", formula=negate(atom("P")))
        b["claims"].append(c)
        b["interpretations"][0]["premises"] = ["p", "not_p"]
        r = audit(b)
        self.assertEqual(r["interpretations"][0]["formal_inference"]["status"], "INCONSISTENT_PREMISES")

    def test_interpretations_preserved_not_majority_voted(self):
        b = base()
        c = copy.deepcopy(b["claims"][0]); c.update(id="conditional", formula={"implies": [atom("P"), atom("Q")]})
        b["claims"].append(c)
        b["interpretations"].append({"id": "alternative", "premises": ["p", "conditional"], "conclusion": "q", "mapping_status": "unreviewed"})
        r = audit(b)
        self.assertTrue(r["interpretation_sensitive_inference"])
        self.assertEqual([i["formal_inference"]["status"] for i in r["interpretations"]], ["DOES_NOT_ENTAIL", "ENTAILS_CONDITIONALLY"])

    def test_evidence_claimed_support_is_not_formal_support(self):
        b = base()
        b["evidence"][0]["formula"] = atom("Q")
        r = audit(b)
        self.assertEqual(r["claims"]["p"]["status"], "NOT_ESTABLISHED")
        self.assertTrue(r["claims"]["p"]["evidence"][0]["assessment_disagrees_with_formalization"])
        self.assertEqual(r["claims"]["p"]["evidence"][0]["formal_relation"], "DOES_NOT_ESTABLISH")

    def test_evidence_can_logically_contradict_a_claim(self):
        b = base()
        b["evidence"][0]["formula"] = negate(atom("P"))
        b["evidence"][0]["relation"] = "contradicts"
        r = audit(b)
        self.assertEqual(r["claims"]["p"]["status"], "CONDITIONAL_FORMAL_CONTRADICTION_RECORDED")

    def test_unformalized_citation_not_promoted(self):
        b = base()
        del b["evidence"][0]["formula"]
        r = audit(b)
        self.assertEqual(r["claims"]["p"]["status"], "NOT_ESTABLISHED")
        self.assertEqual(r["claims"]["p"]["evidence"][0]["formal_relation"], "UNTESTED_SEMANTIC_ASSESSMENT")

    def test_excludes_hindsight_evidence(self):
        b = base()
        b["sources"][1] = source("record", "P was observed in the official record.", captured="2026-02-02T00:00:00Z")
        r = audit(b)
        self.assertEqual(r["claims"]["p"]["evidence"][0]["formal_relation"], "TEMPORAL_NOT_ADMISSIBLE")
        self.assertEqual(r["claims"]["p"]["status"], "NOT_ESTABLISHED")

    def test_rejects_wrong_quote_even_if_matching_source_id(self):
        b = base()
        b["evidence"][0]["span"]["quote"] = "Something not in the source"
        with self.assertRaisesRegex(InvalidBundle, "exact source span"):
            audit(b)

    def test_rejects_tampered_source(self):
        b = base(); b["sources"][1]["text"] += "tampering"
        with self.assertRaisesRegex(InvalidBundle, "hash mismatch"):
            audit(b)

    def test_reports_lineage_not_verified_independence(self):
        b = base()
        second = source("record_copy", "P was observed in an echoed record.", origin="record")
        b["sources"].append(second)
        b["evidence"].append({"id": "e2", "source_id": "record_copy", "claim_id": "p", "span": span(second["text"]),
                              "relation": "supports", "formula": atom("P"), "mapping_status": "review_recorded"})
        r = audit(b)
        self.assertEqual(r["claims"]["p"]["support_origin_ids"], ["record"])
        self.assertFalse(r["claims"]["p"]["origin_independence_verified"])

    def test_undecidable_by_bounded_checker_fails_closed(self):
        premises = [{"atom": f"A{i}"} for i in range(13)]
        result = entailment(premises, {"atom": "A0"})
        self.assertEqual(result["status"], "NOT_CHECKED_ATOM_LIMIT")

    def test_deterministic_report_hash(self):
        r1, r2 = audit(base()), audit(copy.deepcopy(base()))
        self.assertEqual(r1, r2)
        self.assertEqual(len(r1["report_sha256"]), 64)
        self.assertNotIn("truth_verdict", r1)

    def test_rejects_undeclared_atom(self):
        b = base(); b["claims"][0]["formula"] = {"atom": "OTHER"}
        with self.assertRaisesRegex(InvalidBundle, "undeclared"):
            audit(b)

    def test_rejects_duplicate_evidence(self):
        b = base(); b["evidence"].append(copy.deepcopy(b["evidence"][0]))
        with self.assertRaisesRegex(InvalidBundle, "duplicate id"):
            audit(b)

    def test_rejects_bad_timestamps(self):
        b = base(); b["sources"][0]["published_at"] = "2026-02-03T00:00:00Z"
        with self.assertRaisesRegex(InvalidBundle, "publication after capture"):
            audit(b)

    def test_cli_replay(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "input.json"; out = pathlib.Path(d) / "report.json"
            p.write_text(json.dumps(base()))
            result = subprocess.run([sys.executable, str(root / "cli.py"), str(p), "--output", str(out)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(out.read_text()), audit(base()))
            p.write_text("{}")
            result = subprocess.run([sys.executable, str(root / "cli.py"), str(p)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("FAR_AUDIT_INVALID", result.stderr)


if __name__ == "__main__":
    unittest.main()
