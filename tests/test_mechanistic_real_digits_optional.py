"""Optional live train -> FAR-MECH audit -> separate forward-hook replay.

This is a genuinely executed integration test only when torch, numpy, and
sklearn are available. Canonical FAR CI must not silently count an optional
skip as evidence of live model execution.
"""
import importlib.util
import tempfile
from pathlib import Path
import unittest

HAS_SCIENTIFIC_DEPS = all(importlib.util.find_spec(x) is not None
                          for x in ("numpy", "torch", "sklearn"))


@unittest.skipUnless(HAS_SCIENTIFIC_DEPS,
                     "optional scientific dependencies unavailable; no live-model claim")
class LiveDigitsTrainingTests(unittest.TestCase):
    def test_actual_training_audit_and_independent_hook_replay(self):
        from evaluation.run_real_digits_mechanism import run
        from evaluation.replay_real_digits_mechanism import replay
        from mechanization.far_mechanization.mechanistic_fidelity import MechanismAudit
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            summary = run(directory)
            self.assertEqual((summary["heldout"], summary["adversarial"],
                              summary["control"]), (16, 8, 8))
            self.assertGreater(summary["test_accuracy"], 0.90)
            audit = MechanismAudit.load(directory / "digits_mechanism_traces.json")
            scores = audit.evaluate()["by_split"]
            self.assertLess(float(scores["heldout"]["delta_kl"]), 0)
            self.assertGreater(float(scores["adversarial"]["delta_kl"]), 0)
            self.assertEqual(scores["control"]["mean_downstream_kl"], "0.000000000")
            verified = replay(directory / "digits_checkpoint.json",
                              directory / "digits_mechanism_traces.json")
            self.assertEqual(verified["status"], "SAVED_WEIGHT_MODEL_REPLAY_VERIFIED")
            self.assertEqual(verified["n"], 32)
            self.assertLessEqual(verified["max_absolute_probability_deviation"], 0.000002)


if __name__ == "__main__":
    unittest.main()
