"""Recorded real-neural-model trace extract must pass actual FAR-MECH audit.

These tests verify the *submitted* evidence contract and recorded metrics, not
the external experiment's source authenticity. Real saved-weight replay is
provided separately as optional executable PyTorch code.
"""
import copy
import json
from pathlib import Path
import unittest

from mechanization.far_mechanization.mechanistic_fidelity import (
    MechanismAudit, MechanismAuditError,
)

ROOT = Path(__file__).resolve().parents[1]
EXTRACT = ROOT / "evaluation/fixtures/real-digits-three-case-extract-v0.1.json"
SUMMARY = ROOT / "evaluation/results/real-digits-mechanistic-fidelity-20261030.json"


class RealDigitsMechanismEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.extract = json.loads(EXTRACT.read_text(encoding="utf-8"))
        cls.summary = json.loads(SUMMARY.read_text(encoding="utf-8"))

    def test_three_real_recorded_cases_pass_full_far_mech_contract(self):
        audit = MechanismAudit.from_dict(self.extract)
        result = audit.evaluate()
        self.assertEqual(result["data_class"], "submitted_experiment")
        self.assertEqual(result["status"], "SUBMITTED_INTERVENTIONS_NOT_INDEPENDENTLY_REPLAYED")
        self.assertEqual([result["by_split"][s]["n"] for s in
                          ("heldout", "adversarial", "control")], [1, 1, 1])
        self.assertEqual(result["by_split"]["adversarial"]["cases_worse_than_baseline"], 1)
        self.assertEqual(result["by_split"]["heldout"]["cases_worse_than_baseline"], 0)
        self.assertEqual(result["by_split"]["control"]["mean_downstream_kl"], "0.000000000")
        self.assertEqual(result["counterexamples"][0]["case_id"], "digits-1635")

    def test_model_digest_and_experiment_assurance_are_explicit(self):
        self.assertEqual(self.extract["model"]["artifact_sha256"],
                         self.summary["checkpoint_sha256"])
        self.assertEqual(self.summary["replay"]["cases_replayed"], 32)
        self.assertFalse(self.summary["replay"]["independent_data_origin_verification"])
        self.assertIn("NOT_SCIENTIFIC", self.summary["assurance"])

    def test_source_tampering_still_fails(self):
        data = copy.deepcopy(self.extract)
        data["sources"][0]["text"] += " tampered"
        with self.assertRaisesRegex(MechanismAuditError, "source bytes"):
            MechanismAudit.from_dict(data)

    def test_same_activation_different_output_in_control_fails(self):
        data = copy.deepcopy(self.extract)
        control = next(c for c in data["cases"] if c["split"] == "control")
        control["replacement_probs"] = list(data["cases"][0]["replacement_probs"])
        with self.assertRaisesRegex(MechanismAuditError, "unchanged activation"):
            MechanismAudit.from_dict(data)

    def test_repeated_real_input_across_splits_fails(self):
        data = copy.deepcopy(self.extract)
        data["cases"][1]["input_sha256"] = data["cases"][0]["input_sha256"]
        with self.assertRaisesRegex(MechanismAuditError, "duplicate input"):
            MechanismAudit.from_dict(data)


if __name__ == "__main__":
    unittest.main()
