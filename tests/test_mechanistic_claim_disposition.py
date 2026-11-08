"""Finite-evidence falsification regression; no population/semantic certification."""
from __future__ import annotations
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "evaluation/results/smollm2-135m-fullvocab-followup-20261031.json"
DISPOSITION = ROOT / "evaluation/results/far-mech-exact-scope-disposition-20261031.json"


class MechanisticClaimDispositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RESULT.read_text(encoding="utf-8"))
        cls.certificate = json.loads(DISPOSITION.read_text(encoding="utf-8"))

    def test_source_identity_is_stable(self):
        source = self.certificate["source"]
        self.assertEqual(source["revision"], self.record["model_revision"])
        self.assertEqual(source["weight_tensor_sha256"], self.record["weight_tensor_sha256"])
        self.assertEqual(source["result_json_sha256"], self.record["result_json_sha256"])
        self.assertEqual(source["trace_json_sha256"], self.record["trace_json_sha256"])
        self.assertEqual(source["workflow_run"], self.record["workflow_run_id"])

    def test_every_split_aggregate_matches_original_frozen_result(self):
        for name, original in self.record["split_results"].items():
            if name == "adversarial_framing":
                name = "adversarial"
            row = self.certificate["finite_evidence"][name]
            self.assertEqual(row["n"], original["n"])
            self.assertEqual(row["probe_worse_cases"], original["worse"])
            self.assertEqual(row["original_correct"], original["model_correct"])
            self.assertEqual(row["probe_correct"], original["probe_correct"])
            self.assertEqual(row["mean_correct"], original["mean_correct"])
            self.assertEqual(row["gate_accepted"], original["fidelity_accepted"])
            self.assertAlmostEqual(row["probe_kl_mean"], original["full_vocabulary_probe_kl"], places=13)
            self.assertAlmostEqual(row["mean_replacement_kl_mean"], original["full_vocabulary_mean_baseline_kl"], places=13)

    def test_exact_adversarial_failure_is_preserved(self):
        row = self.certificate["finite_evidence"]["adversarial"]
        self.assertEqual(row["probe_worse_cases"], row["n"])
        self.assertGreater(row["probe_kl_mean"], row["mean_replacement_kl_mean"])
        self.assertEqual(
            self.certificate["dispositions"]["probe_uniformly_better_than_mean_on_adversarial"],
            "REFUTED_ON_FROZEN_SET")

    def test_heldout_positive_finding_is_also_preserved(self):
        row = self.certificate["finite_evidence"]["heldout"]
        self.assertLess(row["probe_kl_mean"], row["mean_replacement_kl_mean"])
        self.assertEqual(row["probe_worse_cases"], 1)

    def test_full_coverage_precludes_selective_accuracy_gain(self):
        for row in self.certificate["finite_evidence"].values():
            self.assertEqual(row["n"], row["gate_accepted"])
        self.assertEqual(self.certificate["dispositions"]["fidelity_gate_selective_reliability_uplift"],
                         "REFUTED_ON_FROZEN_SET")

    def test_no_probe_specific_accuracy_improvement(self):
        rows = [self.certificate["finite_evidence"][x] for x in ("heldout", "adversarial")]
        self.assertEqual(sum(x["original_correct"] for x in rows), 13)
        self.assertEqual(sum(x["probe_correct"] for x in rows), 14)
        self.assertEqual(sum(x["mean_correct"] for x in rows), 14)
        self.assertEqual(self.certificate["dispositions"]["reasoning_accuracy_gain_specific_to_probe"],
                         "NOT_OBSERVED_VS_MEAN")

    def test_unsupported_universal_or_competitive_promotions_forbidden(self):
        claims = self.certificate["dispositions"]
        self.assertEqual(claims["superior_to_mib_das_sae"], "NOT_TESTED")
        self.assertEqual(claims["correct_semantic_circuit_explanation"], "NOT_ESTABLISHED")
        self.assertEqual(claims["universal_general_reasoning_reliability"],
                         "NOT_IDENTIFIABLE_FROM_FINITE_COHORT")

    def test_finite_observation_countermodel_exists(self):
        for n in (1, 2, 24, 32, 1000):
            observed = set(range(n))
            witness = min(x for x in range(n + 1) if x not in observed)
            f = lambda x: 0
            g = lambda x: int(x == witness)
            self.assertTrue(all(f(x) == g(x) for x in observed))
            self.assertNotEqual(f(witness), g(witness))
        self.assertTrue(self.certificate["nonidentifiability_witness"]["differ_outside_S"])

    def test_unreviewed_experiment_cannot_be_claimed_independent(self):
        self.assertFalse(self.certificate["proof_obligations"]["independent_model_forward_replay"])
        self.assertFalse(self.certificate["proof_obligations"]["matched_strong_baselines"])
        self.assertEqual(self.certificate["status"], "Research")


if __name__ == "__main__":
    unittest.main()
