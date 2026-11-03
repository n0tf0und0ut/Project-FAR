"""Detect replay of rounded rather than actual registered interventions."""
import struct
import unittest

from evaluation.replay_pretrained_lm_metrics import reconstructed_interventions


class UnroundedInterventionTests(unittest.TestCase):
    def test_real_failure_amplitude_keeps_the_registered_float32_coordinate(self):
        slope = 0.010620787570484621
        intercept = 3.6144075770965207
        exact = slope * 65 + intercept
        row = {"explained_activation": "4.304759", "baseline_activation": "4.267586"}
        patched, baseline = reconstructed_interventions(
            row, {"split": "heldout"}, 65, 4.3, slope, intercept, 4.2675861)
        self.assertEqual(patched, exact)
        self.assertNotEqual(struct.pack("f", patched), struct.pack("f", float(row["explained_activation"])))
        self.assertEqual(baseline, 4.2675861)

    def test_identity_control_preserves_actual_activation_without_rounding(self):
        row = {"explained_activation": "4.304759", "baseline_activation": "1.000000"}
        result, _ = reconstructed_interventions(
            row, {"split": "control"}, 65, 4.304758769178021, 0, 0, 1.0)
        self.assertEqual(result, 4.304758769178021)

    def test_tampered_amplitude_and_nonfinite_fit_fail_closed(self):
        row = {"explained_activation": "4.000000", "baseline_activation": "1.000000"}
        with self.assertRaisesRegex(ValueError, "amplitude"):
            reconstructed_interventions(row, {"split": "heldout"}, 1, 0, 1, 2, 1)
        with self.assertRaisesRegex(ValueError, "amplitude"):
            reconstructed_interventions(row, {"split": "heldout"}, 1, 0, float("nan"), 2, 1)


if __name__ == "__main__":
    unittest.main()
