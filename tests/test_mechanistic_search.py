"""Counterexample generation on a replayable deterministic mechanism."""
from __future__ import annotations

import unittest

from mechanization.far_mechanization.mechanistic_fidelity import MechanismAuditError
from mechanization.far_mechanization.mechanistic_search import search_counterexamples
from mechanization.far_mechanization.mechanistic_toy_reference import model_probabilities


def run(inputs, explained=None, baseline=None):
    return search_counterexamples(
        inputs,
        observed_activation=lambda key: key,
        explained_activation=explained or (
            lambda key: "0.990000" if key == "1.000000" else key),
        baseline_activation=baseline or (
            lambda key: "0.998333" if key == "1.000000" else key),
        output_distribution=lambda _key, activation: model_probabilities(activation),
    )


class MechanisticSearchTests(unittest.TestCase):
    def test_search_finds_adversarial_case_by_actual_toy_forward_pass(self):
        rows = run(["0.990000", "0.995000", "1.000000"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["input_key"], "1.000000")
        self.assertEqual(rows[0]["classification"], "UNVERIFIED_ADVERSARIAL_CANDIDATE")
        self.assertEqual(rows[0]["activation_error"], "0.010000000")
        self.assertGreater(float(rows[0]["delta_kl"]), 0.8)

    def test_exact_explanation_gives_no_candidates(self):
        self.assertEqual(
            run(["0.990000", "0.995000", "1.000000"],
                explained=lambda x: x, baseline=lambda x: x), [])

    def test_comparator_superiority_is_required_not_just_any_change(self):
        rows = run(["1.000000"], explained=lambda _x: "0.999900",
                   baseline=lambda _x: "0.995000")
        self.assertEqual(rows, [])

    def test_nonunique_or_too_many_inputs_rejected(self):
        with self.assertRaisesRegex(MechanismAuditError, "duplicate"):
            run(["1.000000", "1.000000"])
        with self.assertRaisesRegex(MechanismAuditError, "exceeds bound"):
            run(["0.999900"] * 257)
        with self.assertRaises(MechanismAuditError):
            run([])

    def test_invalid_predictions_rejected(self):
        for value in ("NaN", "1e100000", "0." + "0" * 1000, "1.0000000"):
            with self.subTest(value=value[:25]):
                with self.assertRaises(MechanismAuditError):
                    run(["1.000000"], explained=lambda _x: value)

    def test_inconsistent_distribution_rejected(self):
        with self.assertRaises(MechanismAuditError):
            search_counterexamples(
                ["1.000000"], observed_activation=lambda x: x,
                explained_activation=lambda _: "0.990000",
                baseline_activation=lambda _: "0.998333",
                output_distribution=lambda key, z: ["0.5", "0.4"])

    def test_search_is_input_order_invariant(self):
        x = ["0.995000", "1.000000", "0.990000"]
        self.assertEqual(run(x), run(list(reversed(x))))

    def test_unbounded_search_limit_rejected(self):
        with self.assertRaises(MechanismAuditError):
            search_counterexamples(
                ["1.000000"], observed_activation=lambda x: x,
                explained_activation=lambda x: x, baseline_activation=lambda x: x,
                output_distribution=lambda k, z: model_probabilities(z),
                max_cases=1000000)


if __name__ == "__main__":
    unittest.main()
