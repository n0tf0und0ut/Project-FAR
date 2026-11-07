"""Defect-detecting controls for native Research verification boundaries."""
import base64
import copy
import hashlib
import math
import unittest

from tools.far_investigation_verifiers import validate_plan, verify


def receipt(raw: bytes, content_type="text/plain"):
    return {"raw_base64": base64.b64encode(raw).decode("ascii"),
            "sha256": hashlib.sha256(raw).hexdigest(), "observed_bytes": len(raw),
            "status": "RETRIEVED", "truncated": False, "content_type": content_type,
            "request": {"url": "https://example.org/evidence"}}


class NativeVerifierTests(unittest.TestCase):
    def setUp(self):
        self.sources = {"s1": receipt(b"Observed counts: 80 repairs from 200 tasks."),
                        "s2": receipt(b"A competing explanation remained possible.")}
        self.evidence = {"e1": {"source_id": "s1", "quote": "80 repairs from 200 tasks", "relation": "SUPPORT"},
                         "e2": {"source_id": "s2", "quote": "competing explanation remained possible", "relation": "CONTRADICT"}}

    def arithmetic(self, expression="(80 / 200)", expected="0.4"):
        return {"kind": "exact_arithmetic", "expression": expression, "operator": "eq", "expected": expected}

    def test_exact_decimal_arithmetic_avoids_float_error(self):
        plan = self.arithmetic("0.1 + 0.2", "0.3")
        result = verify(plan, "Is 0.1 + 0.2 exactly 0.3?", {}, {})
        self.assertEqual(result["outcome"], "PROVED")
        self.assertEqual(result["calculation"]["actual"], "3/10")

    def test_source_bound_ratio(self):
        plan = self.arithmetic("success / total", "0.4")
        plan["bindings"] = {"success": {"evidence_id": "e1", "value": 80},
                            "total": {"evidence_id": "e1", "value": 200}}
        result = verify(plan, "Does the repair rate equal 0.4?", self.sources, self.evidence)
        self.assertEqual(result["outcome"], "PROVED")
        self.assertIn("not proved", result["uncertainty"][0])

    def test_refutation_returns_computed_counterexample(self):
        result = verify(self.arithmetic("80 / 200", "0.5"), "Does 80 / 200 equal 0.5?", {}, {})
        self.assertEqual(result["outcome"], "REFUTED")
        self.assertEqual(result["counterexample"], {"actual": "2/5", "expected": "1/2"})

    def test_unknown_literal_cannot_enter_calculation(self):
        with self.assertRaisesRegex(ValueError, "provenance"):
            verify(self.arithmetic("80 / 200", "0.4"), "Does this claim hold?", {}, {})

    def test_numeric_substring_is_not_provenance(self):
        with self.assertRaisesRegex(ValueError, "provenance"):
            verify(self.arithmetic("2", "2"), "The number is 200.", {}, {})

    def test_forged_binding_rejected(self):
        plan = self.arithmetic("x", "0.4")
        plan["bindings"] = {"x": {"evidence_id": "e1", "value": 800}}
        with self.assertRaisesRegex(ValueError, "absent"):
            verify(plan, "Is it 0.4?", self.sources, self.evidence)

    def test_forged_quote_and_hash_rejected(self):
        for change in ("quote", "hash"):
            sources, evidence = copy.deepcopy(self.sources), copy.deepcopy(self.evidence)
            if change == "quote":
                evidence["e1"]["quote"] = "A result not present in source"
            else:
                sources["s1"]["sha256"] = "0" * 64
            with self.subTest(change=change), self.assertRaises(ValueError):
                verify({"kind": "evidence_assessment", "evidence_ids": ["e1"], "claim_type": "factual"},
                       "Is the claim true?", sources, evidence)

    def test_no_arbitrary_python_or_exponential_resource_exhaustion(self):
        for expression in ("__import__('os').system('echo x')", "(1).__class__", "2 ** 200", "[1][0]", "1 // 2", "True", "1e999999", "9" * 100):
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                verify(self.arithmetic(expression, "1"), "Question contains 1 2 200 1e999999 " + "9" * 100, {}, {})

    def test_bool_expected_and_nonfinite_values_rejected(self):
        for value in (True, 0.4, float("nan")):
            plan = self.arithmetic()
            plan["expected"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                verify(plan, "80 200 0.4 true", {}, {})

    def test_division_by_zero_and_many_nodes_rejected(self):
        for expression in ("1 / 0", " + ".join(["1"] * 60)):
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                verify(self.arithmetic(expression, "1"), "Question 1 0", {}, {})

    def test_json_pointer_escaping_and_exact_equality(self):
        sources = {"s": receipt(b'{"a/b":{"~key":["v1.0.0"]}}', "application/json")}
        plan = {"kind": "source_json", "source_id": "s", "pointer": "/a~1b/~0key/0", "operator": "eq",
                "expected": "v1.0.0", "expected_quote": "v1.0.0"}
        result = verify(plan, "Is this tag v1.0.0?", sources, {})
        self.assertEqual(result["outcome"], "PROVED")
        self.assertIn("preserved source bytes only", result["scope"])

    def test_json_bool_not_equal_to_integer(self):
        sources = {"s": receipt(b'{"count":true}', "application/json")}
        plan = {"kind": "source_json", "source_id": "s", "pointer": "/count", "operator": "eq",
                "expected": 1, "expected_quote": "1"}
        result = verify(plan, "Does count equal 1?", sources, {})
        self.assertEqual(result["outcome"], "REFUTED")

    def test_json_expected_cannot_be_invented(self):
        plan = {"kind": "source_json", "source_id": "s", "pointer": "/count", "operator": "eq",
                "expected": "invention", "expected_quote": "known"}
        with self.assertRaisesRegex(ValueError, "absent"):
            verify(plan, "Is it known?", {"s": receipt(b'{"count":"invention"}', "application/json")}, {})

    def test_invalid_pointer_and_duplicate_json_rejected(self):
        for raw, pointer in ((b'{"x":1}', "/x~2"), (b'{"x":[1]}', "/x/00"), (b'{"x":1,"x":2}', "/x")):
            plan = {"kind": "source_json", "source_id": "s", "pointer": pointer, "operator": "eq",
                    "expected": 1, "expected_quote": "1"}
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                verify(plan, "Is it 1?", {"s": receipt(raw, "application/json")}, {})

    def test_causal_normative_and_factual_labels_cannot_prove_claims(self):
        for claim_type in ("causal", "normative", "factual", "mathematical", "ambiguous"):
            result = verify({"kind": "evidence_assessment", "evidence_ids": ["e1", "e2"], "claim_type": claim_type},
                            "Does the claim hold?", self.sources, self.evidence)
            self.assertEqual(result["outcome"], "Unknown")
            self.assertEqual(result["support"], ["e1"])
            self.assertEqual(result["counterevidence"], ["e2"])
            self.assertTrue(result["declared_conflict"])

    def test_unknown_reference_or_question_replacement_rejected(self):
        for ids, question in ((["absent"], "Original"), (["e1"], "Replacement")):
            with self.subTest(ids=ids), self.assertRaises(ValueError):
                verify({"kind": "evidence_assessment", "evidence_ids": ids, "claim_type": "factual", "question": question},
                       "Original", self.sources, self.evidence)

    def test_unsupported_contract_or_hidden_outcome_rejected(self):
        for plan in ({"kind": "causal_proof", "outcome": "PROVED"},
                     {**self.arithmetic(), "outcome": "PROVED"}):
            with self.subTest(plan=plan), self.assertRaises(ValueError):
                validate_plan(plan, "80 200 0.4", self.sources, self.evidence)


class StatisticalVerifierTests(unittest.TestCase):
    def fixture(self, s1=11, n1=30, s2=10, n2=30):
        raw = f"Group A: {s1} successes out of {n1}. Group B: {s2} successes out of {n2}.".encode()
        sources = {"s": receipt(raw)}
        evidence = {"a": {"source_id": "s", "quote": f"Group A: {s1} successes out of {n1}.", "relation": "CONTEXT"},
                    "b": {"source_id": "s", "quote": f"Group B: {s2} successes out of {n2}.", "relation": "CONTEXT"}}
        bindings = {"s1": {"evidence_id": "a", "value": str(s1)}, "n1": {"evidence_id": "a", "value": str(n1)},
                    "s2": {"evidence_id": "b", "value": str(s2)}, "n2": {"evidence_id": "b", "value": str(n2)}}
        plan = {"kind": "two_proportion", "groups": [{"successes": "s1", "total": "n1"},
                                                      {"successes": "s2", "total": "n2"}], "bindings": bindings}
        return plan, sources, evidence

    def test_independent_package_numeric_regression(self):
        # Fixed expected interval generated with statsmodels 0.15.0,
        # confint_proportions_2indep(11,30,10,30,method='newcomb',compare='diff',alpha=.05).
        plan, sources, evidence = self.fixture()
        result = verify(plan, "Does A cause more success than B?", sources, evidence)
        statistical = result["statistical_result"]
        self.assertEqual(result["outcome"], "Unknown")
        self.assertEqual(statistical["risk_difference_exact"], "1/30")
        self.assertAlmostEqual(statistical["standard_error"], math.sqrt((11 / 30 * 19 / 30 + 10 / 30 * 20 / 30) / 30))
        self.assertAlmostEqual(statistical["confidence_interval_95"][0], -0.1987779173730728, places=12)
        self.assertAlmostEqual(statistical["confidence_interval_95"][1], 0.2605852097777606, places=12)
        self.assertFalse(statistical["interval_excludes_zero"])

    def test_reversed_groups_negate_difference_and_interval(self):
        plan, sources, evidence = self.fixture(80, 200, 60, 200)
        first = verify(plan, "Compare these groups.", sources, evidence)["statistical_result"]
        plan["groups"].reverse()
        second = verify(plan, "Compare these groups.", sources, evidence)["statistical_result"]
        self.assertAlmostEqual(first["risk_difference"], -second["risk_difference"])
        self.assertAlmostEqual(first["confidence_interval_95"][0], -second["confidence_interval_95"][1])
        self.assertAlmostEqual(first["confidence_interval_95"][1], -second["confidence_interval_95"][0])
        self.assertEqual(first["method"], "newcombe_hybrid_wilson_no_continuity_correction")

    def test_zero_successes_and_all_successes_not_zero_uncertainty(self):
        plan, sources, evidence = self.fixture(0, 10, 10, 10)
        result = verify(plan, "Compare these groups.", sources, evidence)
        statistical = result["statistical_result"]
        self.assertEqual(statistical["risk_difference_exact"], "-1")
        self.assertEqual(statistical["standard_error"], 0.0)
        self.assertLess(statistical["confidence_interval_95"][0], statistical["confidence_interval_95"][1])
        self.assertAlmostEqual(statistical["confidence_interval_95"][0], -1.0)

    def test_empty_or_impossible_counts_rejected(self):
        for counts in ((0, 0, 1, 2), (4, 3, 1, 2), (1, 1_000_000_000_001, 1, 2)):
            plan, sources, evidence = self.fixture(*counts)
            with self.subTest(counts=counts), self.assertRaises(ValueError):
                validate_plan(plan, "Compare.", sources, evidence)

    def test_fractional_and_fabricated_counts_rejected(self):
        for replacement in ("11.5", "999"):
            plan, sources, evidence = self.fixture()
            plan["bindings"]["s1"]["value"] = replacement
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                verify(plan, "Compare.", sources, evidence)

    def test_count_literal_cannot_replace_required_binding(self):
        plan, sources, evidence = self.fixture()
        plan["groups"][0]["successes"] = 11
        with self.assertRaisesRegex(ValueError, "bindings"):
            verify(plan, "Compare 11 counts.", sources, evidence)

    def test_question_cannot_be_rewritten(self):
        plan, sources, evidence = self.fixture()
        plan["question"] = "Different causal hypothesis"
        with self.assertRaisesRegex(ValueError, "replace"):
            verify(plan, "Original question", sources, evidence)


class PropositionalVerifierTests(unittest.TestCase):
    def plan(self, premises=None, conclusion="p"):
        premises = ["p and q"] if premises is None else premises
        return {"kind": "truth_table", "premises": premises, "conclusion": conclusion,
                "premise_quote": "; ".join(premises) or "no premises", "conclusion_quote": conclusion}

    def run_plan(self, plan):
        question = "Premises: " + plan["premise_quote"] + ". Conclusion: " + plan["conclusion_quote"]
        return verify(plan, question, {}, {})

    def test_entailment_checks_all_valuations(self):
        result = self.run_plan(self.plan())
        self.assertEqual(result["outcome"], "PROVED")
        self.assertEqual(result["truth_table"]["valuations_checked"], 4)
        self.assertEqual(result["truth_table"]["premise_models"], 1)
        self.assertFalse(result["truth_table"]["vacuous_entailment"])

    def test_nonentailment_has_concrete_valuation(self):
        result = self.run_plan(self.plan(["p or q"], "p"))
        self.assertEqual(result["outcome"], "REFUTED")
        self.assertEqual(result["counterexample"], {"p": False, "q": True})

    def test_vacuity_and_tautology_are_explicit(self):
        result = self.run_plan(self.plan(["p", "not p"], "q"))
        self.assertEqual(result["outcome"], "PROVED")
        self.assertTrue(result["truth_table"]["vacuous_entailment"])
        self.assertEqual(result["truth_table"]["premise_models"], 0)
        tautology = self.run_plan(self.plan([], "p or not p"))
        self.assertEqual(tautology["outcome"], "PROVED")
        self.assertFalse(tautology["truth_table"]["vacuous_entailment"])

    def test_eight_variable_limit_and_total_node_limit(self):
        for formula in (" or ".join("p" + str(i) for i in range(9)), " and ".join(["p"] * 260)):
            with self.subTest(formula=formula[:30]), self.assertRaises(ValueError):
                self.run_plan(self.plan([formula]))

    def test_no_arbitrary_code_or_nonboolean_literals(self):
        for formula in ("__import__('os').system('echo x')", "p.__class__", "p ** q", "p + q", "1", "[p]", "p == q", "+p"):
            with self.subTest(formula=formula), self.assertRaises(ValueError):
                self.run_plan(self.plan([formula]))

    def test_formulas_must_be_literal_question_substrings(self):
        plan = self.plan()
        with self.assertRaisesRegex(ValueError, "quote"):
            verify(plan, "Different question.", {}, {})
        plan["premise_quote"] = "known premise"
        with self.assertRaisesRegex(ValueError, "literally"):
            self.run_plan(plan)

    def test_false_constant_counterexample_has_empty_valuation(self):
        result = self.run_plan(self.plan([], "False"))
        self.assertEqual(result["outcome"], "REFUTED")
        self.assertEqual(result["counterexample"], {})
        self.assertEqual(result["truth_table"]["valuations_checked"], 1)

    def test_malformed_selector_types_raise_controlled_value_error(self):
        for plan in ({"kind": "exact_arithmetic", "expression": "80/200", "expected": "0.4", "operator": []},
                     {"kind": "evidence_assessment", "claim_type": [], "evidence_ids": []},
                     {"kind": "evidence_assessment", "claim_type": "factual", "evidence_ids": [{}]}):
            with self.subTest(plan=plan), self.assertRaises(ValueError):
                validate_plan(plan, "80 200 0.4", {}, {})


if __name__ == "__main__":
    unittest.main()
