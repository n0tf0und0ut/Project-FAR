"""Adversarial regression tests. No model/network calls or subjective verdict fixtures."""
import copy
import hashlib
import json
import pathlib
import random
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from engine import InvalidBundle, audit, entailment
from structured import parse_snapshot, pointer, StructuredInputError
from capture import capture_source, exact_anchor


def atom(x):
    return {"atom": x}


def negate(x):
    return {"not": x}


def span(text):
    return {"start": 0, "end": len(text), "quote": text}


def source(id, text, origin=None, published="2026-01-01T00:00:00Z", captured="2026-01-02T00:00:00Z"):
    return {"id": id, "text": text, "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "origin_id": origin or id, "published_at": published, "captured_at": captured,
            "publication_date_verified": True}


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

    def test_unknown_date_remains_explicit_unknown_not_fake_admissible(self):
        b = base()
        b["sources"][1]["published_at"] = None
        r = audit(b)
        self.assertEqual(r["source_temporal_status"]["record"], "UNKNOWN_TEMPORAL_ELIGIBILITY")
        self.assertEqual(r["claims"]["p"]["status"], "NOT_ESTABLISHED")

    def test_unverified_source_still_requires_well_formed_timestamps(self):
        b = base()
        b["sources"][1]["publication_date_verified"] = False
        b["sources"][1]["published_at"] = "yesterday"
        with self.assertRaises(InvalidBundle):
            audit(b)

    def test_unverified_source_cannot_invert_publication_and_capture(self):
        b = base()
        b["sources"][1]["publication_date_verified"] = False
        b["sources"][1]["published_at"] = "2026-01-04T00:00:00Z"
        with self.assertRaisesRegex(InvalidBundle, "publication after capture"):
            audit(b)

    def test_unknown_source_lineage_not_reported_as_independent(self):
        b = base()
        b["sources"][1]["origin_id"] = None
        r = audit(b)
        self.assertEqual(r["claims"]["p"]["support_origin_ids"], [])
        self.assertEqual(r["claims"]["p"]["support_sources_with_unknown_origin"], ["record"])

    def test_claim_cannot_prove_itself_through_the_same_quote(self):
        b = base()
        b["evidence"] = [{"id": "self", "source_id": "speech", "claim_id": "p",
                          "span": b["claims"][0]["span"], "formula": atom("P"),
                          "relation": "supports", "mapping_status": "unreviewed"}]
        r = audit(b)
        self.assertEqual(r["claims"]["p"]["status"], "NOT_ESTABLISHED")
        self.assertEqual(r["claims"]["p"]["evidence"][0]["formal_relation"], "SELF_REFERENCE_NOT_CORROBORATION")

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


    def numeric_case(self):
        b = base()
        speech = "2 experiments passed. The product is safe."
        data = '{"experiments":[{"passed":true},{"passed":false},{"passed":true}]}'
        b["sources"][0] = source("speech", speech)
        b["sources"][1] = source("record", data, origin="dataset_one")
        b["claims"][0].update(text="2 experiments passed.",
            span={"start": 0, "end": 21, "quote": "2 experiments passed."},
            quantity={"value":"2", "number_span":{"start":0,"end":1}, "unit":"experiments"})
        b["claims"][1].update(text="The product is safe.",
            span={"start": 22, "end": 42, "quote": "The product is safe."})
        b["evidence"][0] = {"id":"data","source_id":"record", "claim_id":"p",
            "span":span(data), "relation":"supports", "mapping_status":"review_recorded",
            "data_check":{"operation":"count_where","pointer":"/experiments",
                "where":{"field":"passed", "equals":True}}}
        return b

    def test_count_where_calculates_verified_snapshot_value_not_truth(self):
        b = self.numeric_case()
        r = audit(b)
        q = r["claims"]["p"]["structured_value_checks"]
        self.assertEqual(q["status"], "STRUCTURED_VALUE_MATCH_CONDITIONALLY")
        self.assertEqual(q["matches"], 1)
        self.assertEqual(r["claims"]["p"]["status"], "NOT_ESTABLISHED")
        ck = r["claims"]["p"]["evidence"][0]
        self.assertEqual(ck["formal_relation"], "NOT_APPLICABLE_TO_STRUCTURED_CHECK")
        self.assertEqual(ck["structured_check"]["computed_value"], "2")
        self.assertFalse(ck["structured_check"]["source_authenticity_verified"])
        self.assertEqual(r["interpretations"][0]["premises_without_uncontested_formal_evidence"], ["p"])

    def test_count_where_can_disagree_without_promoting_contradiction(self):
        b = self.numeric_case()
        b["claims"][0]["quantity"]["value"] = "3"
        b["claims"][0]["quantity"]["number_span"] = {"start":0,"end":1}
        with self.assertRaisesRegex(InvalidBundle, "token does not match"):
            audit(b)
        b = self.numeric_case()
        text = "3 experiments passed. The product is safe."
        b["sources"][0] = source("speech", text)
        b["claims"][0]["span"]["quote"] = "3 experiments passed."
        b["claims"][0]["quantity"]["value"] = "3"
        r = audit(b)
        self.assertEqual(r["claims"]["p"]["structured_value_checks"]["status"],
                         "STRUCTURED_VALUE_MISMATCH_CONDITIONALLY")
        self.assertTrue(r["claims"]["p"]["evidence"][0]["assessment_disagrees_with_structured_check"])

    def test_future_data_does_not_qualify_as_structured_evidence(self):
        b = self.numeric_case()
        b["sources"][1]["captured_at"] = "2026-02-02T00:00:00Z"
        r = audit(b)
        self.assertEqual(r["claims"]["p"]["structured_value_checks"]["matches"], 0)
        self.assertEqual(r["claims"]["p"]["evidence"][0]["formal_relation"], "TEMPORAL_NOT_ADMISSIBLE")

    def test_sum_field_uses_exact_decimal_not_binary_float(self):
        b = self.numeric_case()
        text = "0.3 dollars received. The product is safe."
        b["sources"][0] = source("speech",text)
        b["claims"][0].update(span={"start":0,"end":21,"quote":"0.3 dollars received."},
            quantity={"value":"0.3","number_span":{"start":0,"end":3},"unit":"dollars"})
        raw = '{"observations":[{"amount":0.1},{"amount":0.2}]}'
        b["sources"][1] = source("record",raw)
        b["evidence"][0]["span"] = span(raw)
        b["evidence"][0]["data_check"] = {"operation":"sum_field", "pointer":"/observations","field":"amount"}
        r = audit(b)
        self.assertEqual(r["claims"]["p"]["evidence"][0]["structured_check"]["computed_value"],"0.3")

    def test_count_rows_and_json_pointer_escaping(self):
        b = self.numeric_case()
        raw = '{"a/b":{"t~n":[1,2]}}'
        b["sources"][1] = source("record",raw)
        b["evidence"][0]["span"] = span(raw)
        b["evidence"][0]["data_check"] = {"operation":"count_rows","pointer":"/a~1b/t~0n"}
        self.assertEqual(audit(b)["claims"]["p"]["structured_value_checks"]["matches"],1)

    def test_duplicate_json_keys_fail_safe_as_unverifiable(self):
        b = self.numeric_case()
        raw = '{"experiments":[],"experiments":[{"passed":true},{"passed":true}]}'
        b["sources"][1] = source("record",raw)
        b["evidence"][0]["span"] = span(raw)
        r = audit(b)
        self.assertEqual(r["claims"]["p"]["evidence"][0]["structured_check"]["status"],"STRUCTURED_UNVERIFIABLE")

    def test_missing_rows_not_silently_counted_as_false(self):
        b = self.numeric_case()
        raw = '{"experiments":[{"passed":true},{}]}'
        b["sources"][1] = source("record",raw)
        b["evidence"][0]["span"] = span(raw)
        r = audit(b)
        self.assertEqual(r["claims"]["p"]["evidence"][0]["structured_check"]["status"],"STRUCTURED_UNVERIFIABLE")

    def test_where_boolean_cannot_implicitly_match_numeric_one(self):
        b = self.numeric_case()
        raw = '{"experiments":[{"passed":1},{"passed":true},{"passed":true}]}'
        b["sources"][1] = source("record",raw)
        b["evidence"][0]["span"] = span(raw)
        r = audit(b)
        self.assertEqual(r["claims"]["p"]["evidence"][0]["structured_check"]["computed_value"],"2")

    def test_invalid_data_contract_does_not_pass_silently(self):
        b = self.numeric_case()
        b["evidence"][0]["data_check"]["operation"] = "python_eval"
        with self.assertRaisesRegex(InvalidBundle,"unsupported structured operation"):
            audit(b)

    def test_structured_and_propositional_checks_must_be_separate(self):
        b = self.numeric_case()
        b["evidence"][0]["formula"] = atom("P")
        with self.assertRaisesRegex(InvalidBundle,"separate records"):
            audit(b)

    def test_replay_rejects_tampered_report_even_if_attacker_changes_hash(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        b = self.numeric_case()
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)/"in.json"; f = pathlib.Path(d)/"report.json"
            p.write_text(json.dumps(b),encoding="utf-8")
            r=audit(b); f.write_text(json.dumps(r),encoding="utf-8")
            cmd=[sys.executable,str(root/"verify.py"),str(p),str(f)]
            self.assertEqual(subprocess.run(cmd,capture_output=True).returncode,0)
            r["claims"]["p"]["structured_value_checks"]["matches"]=4
            r["report_sha256"] = hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest()
            f.write_text(json.dumps(r))
            result=subprocess.run(cmd,capture_output=True,text=True)
            self.assertEqual(result.returncode,1)
            self.assertIn("FAR_REPLAY_MISMATCH",result.stderr)

    def test_numeric_exponent_bomb_fails_as_unverifiable(self):
        b=self.numeric_case()
        raw='{"experiments":[{"amount":1e99999999}]}'
        b["sources"][1]=source("record",raw)
        b["evidence"][0]["span"]=span(raw)
        b["evidence"][0]["data_check"]={"operation":"sum_field","pointer":"/experiments","field":"amount"}
        self.assertEqual(audit(b)["claims"]["p"]["evidence"][0]["structured_check"]["status"],"STRUCTURED_UNVERIFIABLE")

    def test_structured_sum_does_not_lose_decimal_precision(self):
        b=self.numeric_case()
        text="0.300000000000000000000000001 dollars. The product is safe."
        b["sources"][0]=source("speech",text)
        b["claims"][0].update(text="0.300000000000000000000000001 dollars.",
            span={"start":0,"end":len("0.300000000000000000000000001 dollars."),"quote":"0.300000000000000000000000001 dollars."},
            quantity={"value":"0.300000000000000000000000001","number_span":{"start":0,"end":29},"unit":"dollars"})
        safe_span_start=text.index("The product is safe.")
        b["claims"][1]["span"]={"start":safe_span_start,"end":len(text),"quote":"The product is safe."}
        raw='{"observations":[{"amount":0.1},{"amount":0.200000000000000000000000001}]}'
        b["sources"][1]=source("record",raw)
        b["evidence"][0]["span"]=span(raw)
        b["evidence"][0]["data_check"]={"operation":"sum_field","pointer":"/observations","field":"amount"}
        self.assertEqual(audit(b)["claims"]["p"]["evidence"][0]["structured_check"]["computed_value"],"0.300000000000000000000000001")

    def test_randomized_count_differential_against_plain_python_oracle(self):
        rng = random.Random(20261017)
        for n in range(1, 101):
            rows = [{"passed": rng.choice((True, False))} for _ in range(rng.randint(0, 50))]
            actual = sum(1 for row in rows if row["passed"] is True)
            b = self.numeric_case()
            claim_text = f"{actual} experiments passed. The product is safe."
            quote = f"{actual} experiments passed."
            b["sources"][0] = source("speech", claim_text)
            b["claims"][0]["text"] = quote
            b["claims"][0]["span"] = {"start":0,"end":len(quote),"quote":quote}
            b["claims"][0]["quantity"] = {"value":str(actual),"number_span":{"start":0,"end":len(str(actual))},"unit":"experiments"}
            statement = "The product is safe."
            where = claim_text.index(statement)
            b["claims"][1]["span"] = {"start":where,"end":where+len(statement),"quote":statement}
            raw = json.dumps({"experiments": rows})
            b["sources"][1] = source("record", raw)
            b["evidence"][0]["span"] = span(raw)
            report = audit(b)
            ck = report["claims"]["p"]["evidence"][0]["structured_check"]
            self.assertEqual(ck["computed_value"], str(actual))
            self.assertEqual(ck["status"], "STRUCTURED_VALUE_MATCH")

    def test_local_capture_records_actual_bytes_without_inventing_dates(self):
        text="alpha 12 beta"
        src=capture_source(text.encode(),source_id="snapshot",captured_at="2026-02-01T00:00:00Z")
        self.assertEqual(src["sha256"],hashlib.sha256(text.encode()).hexdigest())
        self.assertIsNone(src["published_at"])
        self.assertFalse(src["origin_verified"])
        self.assertEqual(exact_anchor(src["text"],"12"),{"start":6,"end":8,"quote":"12"})

    def test_local_capture_rejects_multiple_matching_spans(self):
        with self.assertRaisesRegex(InvalidBundle,"ambiguous repeated"):
            exact_anchor("x y x", "x")
        self.assertEqual(exact_anchor("x y x", "x", start=4)["start"],4)

    def test_capture_rejects_fabricated_published_after_capture(self):
        with self.assertRaisesRegex(InvalidBundle,"later"):
            capture_source(b"test",source_id="x",captured_at="2026-01-01T00:00:00Z",
                published_at="2026-02-01T00:00:00Z")

    def test_example_structured_fixture_and_replay(self):
        root=pathlib.Path(__file__).resolve().parents[1]
        src=root/"examples/structured_tally.json"
        b=json.loads(src.read_text())
        r=audit(b)
        self.assertEqual(r["claims"]["p"]["structured_value_checks"]["status"],"STRUCTURED_VALUE_MATCH_CONDITIONALLY")
        with tempfile.TemporaryDirectory() as d:
            report=pathlib.Path(d)/"report.json"
            report.write_text(json.dumps(r))
            result=subprocess.run([sys.executable,str(root/"verify.py"),str(src),str(report)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_nonfinite_bundle_values_fail_closed(self):
        b=self.numeric_case()
        b["atoms"]["P"] = float("nan")
        with self.assertRaisesRegex(InvalidBundle, "non-JSON or non-finite"):
            audit(b)

    def test_machine_arithmetic_does_not_validate_source_meaning(self):
        b = self.numeric_case()
        b["claims"][0]["mapping_status"] = "review_recorded"
        report=audit(b)
        self.assertFalse(report["claims"]["p"]["structured_value_checks"]["claim_meaning_verified"])
        self.assertEqual(report["assurance_boundary"]["real_world_truth"], "not established")


if __name__ == "__main__":
    unittest.main()
