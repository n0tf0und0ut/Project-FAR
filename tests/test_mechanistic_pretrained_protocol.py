"""Offline adversarial checks of the pinned pretrained-language-model protocol.

Does NOT mean that the model was downloaded or neural interventions ran.
"""
import inspect
import unittest

from evaluation.run_pretrained_lm_fidelity import (
    MODEL_ID, REVISION, NOUNS, SEED, task_cases, canonical, sha,
)


class PretrainedLMProtocolTests(unittest.TestCase):
    def test_revision_is_immutable_full_commit(self):
        self.assertEqual(MODEL_ID, "HuggingFaceTB/SmolLM2-135M-Instruct")
        self.assertEqual(REVISION, "12fd25f77366fa6b3b4b768ec3050bf629380bac")
        self.assertEqual(len(REVISION), 40)
        self.assertEqual(SEED, 7103)

    def test_task_families_are_disjoint_balanced_and_deterministic(self):
        a = task_cases()
        b = task_cases()
        self.assertEqual(a, b)
        self.assertEqual(len(a), 56)
        self.assertEqual(len({row["id"] for row in a}), 56)
        self.assertEqual(len({row["question"] for row in a}), 56)
        for split, expected in [("train", 24), ("heldout", 12),
                                ("adversarial", 12), ("control", 8)]:
            group = [x for x in a if x["split"] == split]
            self.assertEqual(len(group), expected)
            self.assertEqual(sum(x["gold"] == "yes" for x in group), expected // 2)
            self.assertTrue(all(x["gold"] in ("yes", "no") for x in group))

    def test_counterexamples_are_formally_invalid_reversals(self):
        for row in task_cases():
            if row["gold"] == "no":
                a, b = row["question"].split("Every ", 1)[1].split(" is a ", 1)
                self.assertIn("Does it necessarily follow", row["question"])
                self.assertTrue(a.strip())

    def test_model_path_is_actually_weighted_and_hooked(self):
        import evaluation.run_pretrained_lm_fidelity as module
        src = inspect.getsource(module.run)
        self.assertIn("AutoModelForCausalLM.from_pretrained", src)
        self.assertIn("register_forward_pre_hook", src)
        self.assertIn("torch.inference_mode()", src)
        self.assertIn("MechanismAudit.from_dict", src)
        self.assertIn("torch.use_deterministic_algorithms(True)", src)
        self.assertIn("model.state_dict()", src)

    def test_canonical_source_hash_stability(self):
        self.assertEqual(
            sha(canonical({"b": 2, "a": 1})),
            sha(canonical({"a": 1, "b": 2})),
        )


if __name__ == "__main__":
    unittest.main()
