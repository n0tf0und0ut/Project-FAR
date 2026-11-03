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


    def test_negative_post_relu_intervention_replayed_and_zero_forgery_rejected(self):
        import numpy as np
        import torch
        from evaluation.run_real_digits_mechanism import run
        from evaluation.replay_real_digits_mechanism import replay
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run(root)
            checkpoint_path = root / "digits_checkpoint.json"
            checkpoint = json.loads(checkpoint_path.read_text())
            trace = json.loads((root / "digits_mechanism_traces.json").read_text())
            row = trace["cases"][0]
            self.assertEqual(row["split"], "heldout")
            index = row["id"].split("-")[1]
            x = torch.tensor(checkpoint["cases"][index], dtype=torch.float32)[None, :]
            state = {key: torch.tensor(value, dtype=torch.float32).reshape(checkpoint["shapes"][key])
                     for key, value in checkpoint["weights"].items()}
            hidden = torch.relu(torch.nn.functional.linear(x, state["fc1.weight"], state["fc1.bias"]))

            def measured(replacement):
                h = hidden.clone()
                h[:, checkpoint["hidden_unit"]] = replacement
                z = torch.nn.functional.linear(h, state["fc2.weight"], state["fc2.bias"])[0].numpy().astype(np.float64) / 2
                exp = np.exp(z - z.max())
                p = 0.995 * exp / exp.sum() + 0.005 / len(exp)
                units = np.floor(p * 1_000_000).astype(int)
                fractions = p * 1_000_000 - units
                for i in sorted(range(len(p)), key=lambda i: (-fractions[i], i))[:1_000_000 - int(units.sum())]:
                    units[i] += 1
                return [f"{v / 1_000_000:.6f}" for v in units]

            negative = measured(-1.0)
            zero = measured(0.0)
            self.assertNotEqual(negative, zero)
            row["explained_activation"] = "-1.000000"
            row["replacement_probs"] = negative
            path = root / "negative-post-relu.json"
            path.write_text(json.dumps(trace))
            self.assertEqual(replay(checkpoint_path, path)["status"], "SAVED_WEIGHT_MODEL_REPLAY_VERIFIED")
            row["replacement_probs"] = zero
            path.write_text(json.dumps(trace))
            with self.assertRaisesRegex(ValueError, "replay mismatch"):
                replay(checkpoint_path, path)


if __name__ == "__main__":
    unittest.main()
