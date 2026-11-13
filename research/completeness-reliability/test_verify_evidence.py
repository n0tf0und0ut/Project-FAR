"""Adversarial regression tests for retrospective FAR reliability evidence audit."""
from __future__ import annotations

import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("far_reliability_audit", HERE / "verify_evidence.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class RetrospectiveEvidenceAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = audit.read_source_record()

    def test_exact_30_pairs_reconstruct_original_effect(self):
        out = audit.descriptive_analysis(self.record)
        self.assertEqual(out["success"]["control"], 11)
        self.assertEqual(out["success"]["far"], 10)
        self.assertEqual(out["success"]["both_succeeded"], 9)
        self.assertEqual(out["success"]["both_failed"], 18)
        self.assertEqual(out["success"]["far_only"], 1)
        self.assertEqual(out["success"]["control_only"], 2)
        self.assertAlmostEqual(out["success"]["far_minus_control"], -1 / 30)

    def test_exact_discordance_sign_probability(self):
        self.assertEqual(audit.exact_discordant_p(1, 2), 1)
        self.assertEqual(audit.exact_discordant_p(0, 0), 1)
        self.assertEqual(audit.exact_discordant_p(0, 4), 0.125)
        self.assertEqual(audit.exact_discordant_p(4, 0), 0.125)

    def test_post_hoc_family_resampling_not_inferential_promotion(self):
        r = audit.descriptive_analysis(self.record)
        self.assertEqual(r["primary_corpus"]["n_related_families"], 10)
        self.assertEqual(len(r["success"]["family_cluster_bootstrap_95pct_post_hoc"]), 2)
        self.assertFalse(r["audit"]["far_specific_causal_effect_identified"])
        self.assertFalse(r["audit"]["general_purpose_agent_reliability_established"])

    def test_failure_on_renamed_task(self):
        r = copy.deepcopy(self.record)
        r["paired_outcomes"][0]["task_id"] = "FORGED-001"
        with self.assertRaises(ValueError):
            audit.descriptive_analysis(r)

    def test_failure_on_favorable_regrade(self):
        r = copy.deepcopy(self.record)
        for p in r["paired_outcomes"]:
            if p["treatment_outcome"] == "FAILURE":
                p["treatment_outcome"] = "SUCCESS"
                break
        with self.assertRaises(ValueError):
            audit.descriptive_analysis(r)

    def test_missing_pair_rejected(self):
        r = copy.deepcopy(self.record)
        r["paired_outcomes"].pop()
        with self.assertRaises(ValueError):
            audit.descriptive_analysis(r)

    def test_duplicate_artifact_rejected(self):
        r = copy.deepcopy(self.record)
        r["artifact_manifest"][1]["name"] = r["artifact_manifest"][2]["name"]
        with self.assertRaises(ValueError):
            audit.descriptive_analysis(r)

    def test_forged_artifact_digest_rejected(self):
        r = copy.deepcopy(self.record)
        r["artifact_manifest"][1]["digest"] = "sha256:NOT_A_DIGEST"
        with self.assertRaises(ValueError):
            audit.descriptive_analysis(r)

    def test_raw_attempt_without_credentials_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                audit.verify_archived_raw(self.record, "", Path(tmp) / "evidence")

    def test_double_json_keys_rejected(self):
        with self.assertRaises(ValueError):
            audit.strict_json(b'{"status":"success","status":"failure"}')

    def test_nonfinite_json_rejected(self):
        with self.assertRaises(ValueError):
            audit.strict_json(b'{"success":NaN}')

    def test_forged_blob_identity_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "original.json"
            path.write_text(json.dumps(self.record))
            with self.assertRaises(ValueError):
                audit.read_source_record(path)

    def test_all_outcomes_original_and_models_locked(self):
        r = self.record
        self.assertEqual(r["provenance"]["execution_sha"], audit.EXECUTED_SHA)
        self.assertEqual(r["analysis"]["model_digest"], audit.MODEL_DIGEST)
        self.assertTrue(r["analysis"]["model_weights_identity_pinned"])
        self.assertFalse(r["analysis"]["autonomous_agent_efficacy_measured"])
        self.assertFalse(r["analysis"]["population_efficacy_established"])


if __name__ == "__main__":
    unittest.main()
