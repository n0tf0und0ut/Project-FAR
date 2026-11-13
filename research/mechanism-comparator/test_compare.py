"""Adversarial tests for preregistered FAR-MECH-COMP-001."""
from __future__ import annotations

import copy
import json
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import compare
from generic_collision import classify, canonical


class TestGenericChecker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases, cls.integrity = compare.prepare_corpus()
        cls.validator = compare.make_validator()

    def test_exhaustive_registered_corpus_identity_and_counts(self):
        self.assertEqual(len(self.cases), 18)
        self.assertEqual(len(self.integrity), 3)
        self.assertEqual(len({x["id"] for x in self.cases}), 18)
        self.assertEqual(sum(x["kind"] == "mutant" for x in self.cases), 6)

    def test_generic_semantic_parity_every_frozen_case(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(
                    classify(case["document"], self.validator), case["label"]
                )

    def test_real_far_semantic_parity_every_frozen_case(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                actual, codes = compare.classify_far(case["document"])
                self.assertEqual(actual, case["label"], codes)

    def test_schema_only_detects_no_registered_semantic_collisions(self):
        for case in self.cases:
            self.assertEqual(compare.classify_schema_only(case["document"], self.validator), "NO_LOSS")

    def test_reference_oracle_independent_of_report_outcome(self):
        a = next(x["document"] for x in self.cases if x["kind"] == "mutant")
        b = copy.deepcopy(a)
        b["report"]["outcome"] = "PROVED"
        self.assertEqual(compare.reference_truth(b), "LOSS")
        b["report"]["outcome"] = "REFUTED"
        self.assertEqual(compare.reference_truth(b), "LOSS")

    def test_source_case_duplicate_rejected(self):
        a = copy.deepcopy(self.cases[0]["document"])
        a["contract"]["source_domain"]["cases"][1]["id"] = a["contract"]["source_domain"]["cases"][0]["id"]
        self.assertEqual(classify(a, self.validator), "INVALID")

    def test_undefined_target_table_rejected(self):
        a = copy.deepcopy(self.cases[0]["document"])
        a["contract"]["required_behavior"]["table"].pop()
        self.assertEqual(classify(a, self.validator), "INVALID")

    def test_invalid_shape_rejected(self):
        self.assertEqual(classify({}, self.validator), "INVALID")
        self.assertEqual(classify(None, self.validator), "INVALID")
        self.assertEqual(classify("not a contract", self.validator), "INVALID")

    def test_schema_and_semantic_not_conflated(self):
        x = next(v for v in self.cases if v["kind"] == "mutant")
        self.assertEqual(compare.classify_schema_only(x["document"], self.validator), "NO_LOSS")
        self.assertEqual(classify(x["document"], self.validator), "LOSS")

    def test_finite_collision_mutation_detected(self):
        clean = next(v for v in self.cases if v["kind"] == "clean")
        mutant = copy.deepcopy(clean["document"])
        rows = mutant["contract"]["representation"]["table"]
        rows[1]["value"] = copy.deepcopy(rows[0]["value"])
        self.assertEqual(compare.reference_truth(mutant), "LOSS")
        self.assertEqual(classify(mutant, self.validator), "LOSS")

    def test_secondary_integrity_does_not_create_semantic_loss(self):
        for x in self.integrity:
            self.assertEqual(compare.reference_truth(x["document"]), "NO_LOSS")
            self.assertEqual(classify(x["document"], self.validator), "NO_LOSS")
            far, _ = compare.classify_far(x["document"])
            self.assertEqual(far, "INVALID", x["id"])

    def test_invalid_contract_must_not_be_semantic_collision(self):
        a = copy.deepcopy(self.cases[0]["document"])
        a["freeze"]["contract_sha256"] = "0" * 64
        far, codes = compare.classify_far(a)
        self.assertEqual(far, "INVALID", codes)

    def test_mixed_results_score_with_invalid_fail_closed(self):
        matrix = [
            {"truth": "NO_LOSS", "predictions": {"far": {"class": "NO_LOSS"}}},
            {"truth": "LOSS", "predictions": {"far": {"class": "LOSS"}}},
            {"truth": "LOSS", "predictions": {"far": {"class": "INVALID"}}},
        ]
        self.assertEqual(compare.score(matrix, "far"),
                         {"tp": 1, "fn": 1, "tn": 1, "fp": 0, "invalid": 1,
                          "correct": 2, "total": 3})

    def test_percentile_definition_no_interpolation(self):
        self.assertEqual(compare._percentile_ns([1, 2, 3, 4, 5], 95), 5)
        self.assertEqual(compare._percentile_ns([1, 2, 3, 4, 5], 50), 3)

    def test_canonical_order_is_value_order_invariant(self):
        self.assertEqual(canonical({"b": 2, "a": [1]}), canonical({"a": [1], "b": 2}))
        with self.assertRaises(ValueError):
            canonical({"not-finite": float("nan")})

    def test_generic_checker_code_does_not_import_far(self):
        source = (HERE / "generic_collision.py").read_text()
        self.assertNotIn("mechanization", source)
        self.assertNotIn("tools.check_pca", source)
        self.assertNotIn("from far_", source)


if __name__ == "__main__":
    unittest.main()
