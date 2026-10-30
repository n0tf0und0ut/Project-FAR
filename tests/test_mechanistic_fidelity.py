"""Adversarial regression suite for submitted mechanistic fidelity audits."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from mechanization.far_mechanization.mechanistic_fidelity import (
    MechanismAudit, MechanismAuditError, VERSION,
)
from mechanization.far_mechanization.mechanistic_toy_reference import (
    replay_case, model_probabilities,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples/mechanistic-fidelity/synthetic-neuron-replacement.json"


class MechanisticFidelityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def audit(self, doc=None):
        return MechanismAudit.from_dict(
            copy.deepcopy(self.fixture if doc is None else doc))

    def fails(self, change, match=None):
        doc = copy.deepcopy(self.fixture)
        change(doc)
        with self.assertRaises(MechanismAuditError) as raised:
            self.audit(doc)
        if match is not None:
            self.assertIn(match, str(raised.exception))

    def test_validated_synthetic_fixture_and_digest_roundtrip(self):
        doc = self.audit()
        self.assertEqual(doc.to_dict(), self.fixture)
        self.assertEqual(MechanismAudit.loads(
            json.dumps(self.fixture)).digest, doc.digest)
        self.assertEqual(doc.evaluate()["format_version"], VERSION)

    def test_local_activation_accuracy_does_not_certify_downstream_fidelity(self):
        result = self.audit().evaluate()
        self.assertEqual(result["by_split"]["adversarial"]["activation_mae"], "0.010000000")
        self.assertEqual(result["by_split"]["adversarial"]["cases_worse_than_baseline"], 2)
        self.assertGreater(
            float(result["by_split"]["adversarial"]["delta_kl"]), 0)
        self.assertLess(float(result["by_split"]["heldout"]["delta_kl"]), 0)
        self.assertEqual(result["status"], "SYNTHETIC_DEMONSTRATION_ONLY")
        self.assertEqual(len(result["counterexamples"]), 2)
        self.assertEqual(result["unverified"][1],
                         "whether the component was replaced as claimed")

    def test_every_synthetic_output_is_replayable_from_toy_equations(self):
        for case in self.fixture["cases"]:
            with self.subTest(case=case["id"]):
                self.assertTrue(replay_case(case))
        self.assertEqual(model_probabilities("1.000000"), ["0.200000", "0.800000"])
        self.assertEqual(model_probabilities("0.990000"), ["0.800000", "0.200000"])

    def test_impossible_same_activation_different_output_is_rejected(self):
        def impossible(doc):
            row = doc["cases"][0]
            row["explained_activation"] = row["observed_activation"]
        self.fails(impossible, "unchanged activation")

    def test_replay_detects_fabricated_replacement_probabilities(self):
        row = copy.deepcopy(self.fixture["cases"][0])
        row["replacement_probs"] = ["0.700000", "0.300000"]
        self.assertFalse(replay_case(row))
        # The general-purpose auditor cannot independently evaluate a foreign
        # network. The synthetic reference replay checks these toy numbers.
        self.assertEqual(self.audit().evaluate()["status"], "SYNTHETIC_DEMONSTRATION_ONLY")

    def test_control_has_zero_downstream_kl(self):
        result = self.audit().evaluate()
        self.assertEqual(result["by_split"]["control"]["mean_downstream_kl"], "0.000000000")
        self.assertEqual(result["by_split"]["control"]["delta_kl"], "0.000000000")

    def test_no_external_mechanism_claim_from_submitted_data(self):
        doc = copy.deepcopy(self.fixture)
        doc["data_class"] = "submitted_experiment"
        result = self.audit(doc).evaluate()
        self.assertEqual(result["status"], "SUBMITTED_INTERVENTIONS_NOT_INDEPENDENTLY_REPLAYED")
        self.assertEqual(result["assurance"],
                         "STRUCTURAL_AND_NUMERICAL_AUDIT_ONLY_NOT_CAUSAL_PROOF")

    def test_schema_rejects_undeclared_metadata(self):
        self.fails(lambda d: d.update(extra="not allowed"))
        self.fails(lambda d: d["cases"][0].update(extra="not allowed"))

    def test_duplicate_ids_fail_closed(self):
        self.fails(lambda d: d["cases"][1].update(id=d["cases"][0]["id"]), "duplicate case")
        self.fails(lambda d: d["sources"].append(copy.deepcopy(d["sources"][0])), "duplicate source")

    def test_source_hash_or_missing_reference_rejected(self):
        self.fails(lambda d: d["sources"][0].update(text="tamper"), "source bytes")
        self.fails(lambda d: d["cases"][0].update(source_ids=["unknown"]), "unresolved")
        self.fails(lambda d: d["explanation"].update(hypothesis_source_ids=["unknown"]), "unresolved")

    def test_probability_vectors_fail_closed(self):
        self.fails(lambda d: d["cases"][0].update(original_probs=["0.2", "0.2"]), "exactly one")
        self.fails(lambda d: d["cases"][0].update(original_probs=["1", "0"]), "strictly positive")
        self.fails(lambda d: d["cases"][0].update(replacement_probs=["0.5", "0.3", "0.2"]), "dimensions")
        self.fails(lambda d: d["cases"][0].update(baseline_probs=["NaN", "1"]))
        self.fails(lambda d: d["cases"][0].update(baseline_probs=[0.5, 0.5]))

    def test_time_and_leakage_guards(self):
        self.fails(lambda d: d["cases"][0].update(measured_at="2026-09-01T00:00:00Z"), "not after")
        self.fails(lambda d: d["cases"][0].update(measured_at="2026-10-30T12:00:00"))
        self.fails(lambda d: d.update(registered_at="invalid"))

    def test_splits_must_include_adversarial_and_control(self):
        self.fails(lambda d: d["cases"].__setitem__(
            slice(None), [x for x in d["cases"] if x["split"] != "adversarial"]), "required")
        self.fails(lambda d: d["cases"].__setitem__(
            slice(None), [x for x in d["cases"] if x["split"] != "control"]), "required")

    def test_invalid_sha_fails_closed(self):
        self.fails(lambda d: d["model"].update(artifact_sha256="123"))
        self.fails(lambda d: d["cases"][0].update(input_sha256="0" * 63))

    def test_duplicate_keys_and_nonfinite_json_rejected(self):
        with self.assertRaises(MechanismAuditError):
            MechanismAudit.loads('{"x":1,"x":2}')
        with self.assertRaises(MechanismAuditError):
            MechanismAudit.loads('{"x":NaN}')

    def test_no_mutation_from_audit_result(self):
        doc = self.audit()
        old = doc.digest
        d = doc.to_dict()
        d["cases"].clear()
        res = doc.evaluate()
        res["counterexamples"][0]["source_ids"].append("injected")
        self.assertEqual(doc.digest, old)
        self.assertEqual(len(doc.to_dict()["cases"]), 6)
        self.assertNotIn("injected", doc.evaluate()["counterexamples"][0]["source_ids"])

    def test_permutation_invariant_split_statistics(self):
        doc = copy.deepcopy(self.fixture)
        doc["cases"].reverse()
        left = self.audit().evaluate()
        right = self.audit(doc).evaluate()
        self.assertEqual(left["by_split"], right["by_split"])
        self.assertEqual(left["counterexamples"], right["counterexamples"])

    def test_adversarial_losses_not_hidden_in_aggregate(self):
        report = self.audit().evaluate()
        self.assertEqual(report["by_split"]["heldout"]["n"], 2)
        self.assertEqual(report["by_split"]["adversarial"]["n"], 2)
        self.assertEqual(report["by_split"]["control"]["n"], 2)
        self.assertEqual([x["case_id"] for x in report["counterexamples"]],
                         ["adversarial-1", "adversarial-2"])


if __name__ == "__main__":
    unittest.main()
