"""Optional live train -> FAR-MECH audit -> separate forward-hook replay.

This is a genuinely executed integration test only when torch, numpy, and
sklearn are available. Canonical FAR CI must not silently count an optional
skip as evidence of live model execution.
"""
import importlib.util
import json
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
            original = json.loads((directory / "digits_mechanism_traces.json").read_text())
            wrong_component = json.loads(json.dumps(original))
            wrong_component["model"]["component_id"] = "fc1.relu.5"
            changed = directory / "wrong_component.json"
            changed.write_text(json.dumps(wrong_component), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "component id"):
                replay(directory / "digits_checkpoint.json", changed)
            nonfinite = json.loads(json.dumps(original))
            nonfinite["cases"][0]["replacement_probs"][0] = "NaN"
            changed.write_text(json.dumps(nonfinite), encoding="utf-8")
            with self.assertRaises(ValueError):
                replay(directory / "digits_checkpoint.json", changed)
            nan_observed = json.loads(json.dumps(original))
            nan_observed["cases"][0]["observed_activation"] = "NaN"
            changed.write_text(json.dumps(nan_observed), encoding="utf-8")
            with self.assertRaises(ValueError):
                replay(directory / "digits_checkpoint.json", changed)


if __name__ == "__main__":
    unittest.main()
