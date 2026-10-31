"""Negative tests for source-bound pretrained result correctness and risk metrics."""
from __future__ import annotations

import copy
from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest

from evaluation.validate_pretrained_lm_result import verify, _binary_kl
from evaluation.run_pretrained_lm_fidelity import MODEL_ID, REVISION
from mechanization.far_mechanization.mechanistic_fidelity import MechanismAudit


def fixture():
    registered = "2026-10-30T00:00:00Z"
    logged = "2026-10-30T01:00:00Z"
    source = "Source-bound synthetic verifier fixture; no pretrained run asserted."
    digest = hashlib.sha256(source.encode()).hexdigest()
    rows = []
    records = []
    for split in ("heldout", "adversarial", "control"):
        original = ["0.600000", "0.400000"]
        explained = original if split == "control" else ["0.590000", "0.410000"]
        baseline = ["0.550000", "0.450000"]
        row = {
            "id": split+"-00", "split":split,
            "input_sha256": hashlib.sha256(split.encode()).hexdigest(),
            "measured_at":logged, "source_ids":["synthetic"],
            "observed_activation":"1.000000",
            "explained_activation":"1.000000" if split=="control" else "0.990000",
            "baseline_activation":"0.900000",
            "original_probs":original, "replacement_probs":explained,
            "baseline_probs":baseline,
        }
        rows.append(row)
        records.append({
            "id": row["id"], "split":split, "gold":"yes",
            "base_correct":True, "replacement_correct":True, "mean_correct":True,
            "base_entropy":-sum(float(p)*math.log(float(p)) for p in original),
            "explanation_kl": _binary_kl(original, explained),
            "mean_kl": _binary_kl(original, baseline),
            "full_vocabulary_explanation_kl":0 if split=="control" else 0.001,
            "full_vocabulary_mean_kl":0.005,
        })
    document = {
        "format_version":"FAR-MECH/0.1","status":"Research",
        "id":"synthetic-validator-falsification", "data_class":"synthetic",
        "registered_at":registered,
        "model":{
            "artifact_sha256":"a"*64,"component_id":"layer0.downproj.in.0",
            "intervention_type":"single_component_activation_replacement",
            "reference_population_sha256":"b"*64,
            "execution_contract":{"deterministic":True,"same_nonintervened_state":True,
                                  "exact_output_distributions":True}},
        "explanation":{"id":"synthetic","description":"synthetic trace",
                       "hypothesis_source_ids":["synthetic"]},
        "sources":[{"id":"synthetic","text":source,"sha256":digest}],
        "cases":rows,
    }
    audit = MechanismAudit.from_dict(document).evaluate()
    summary = {}
    for rec in records:
        summary[rec["split"]] = {
            "n":1, "model_accuracy":1.0, "replacement_accuracy":1.0,
            "mean_baseline_accuracy":1.0, "fidelity_gate_accepted":1,
            "fidelity_gate_accuracy":1.0,"confidence_matched_accuracy":1.0,
            "hash_matched_accuracy":1.0,
            "explanation_kl":rec["explanation_kl"],
            "baseline_kl":rec["mean_kl"],
            "full_vocabulary_probe_kl":rec["full_vocabulary_explanation_kl"],
            "full_vocabulary_baseline_kl":rec["full_vocabulary_mean_kl"],
            "cases_worse_than_baseline_full_vocabulary":0,
        }
    return document, {
        "manifest":{"model_id":MODEL_ID,"model_revision":REVISION,
                    "weights_sha256":"a"*64,"answer_tokens":["yes","no"],
                    "evaluation_n":3},
        "individual_results":records,
        "mechanism_audit":audit,
        "task_accuracy_and_selective_risk":summary,
        "status":"EXPLORATORY_PRETRAINED_LM_PILOT_NO_EXTERNAL_SUPERIORITY_CLAIM",
    }


class ResultVerifierMutationTests(unittest.TestCase):
    def check(self, document, report):
        with tempfile.TemporaryDirectory() as temp:
            a = Path(temp)/"trace.json"
            b = Path(temp)/"result.json"
            a.write_text(json.dumps(document), encoding="utf-8")
            b.write_text(json.dumps(report), encoding="utf-8")
            return verify(a,b)

    def test_valid_self_consistent_synthetic_case_is_not_world_certification(self):
        trace, report = fixture()
        result = self.check(trace,report)
        self.assertEqual(result["n"],3)
        self.assertFalse(result["full_vocab_logits_replayed"])

    def test_forged_correctness_flags_even_with_coordinated_aggregate_rejected(self):
        trace, report = fixture()
        for row in report["individual_results"]:
            row["base_correct"] = row["replacement_correct"] = row["mean_correct"] = False
        for split in report["task_accuracy_and_selective_risk"]:
            row = report["task_accuracy_and_selective_risk"][split]
            for k in ("model_accuracy","replacement_accuracy","mean_baseline_accuracy",
                      "fidelity_gate_accuracy","confidence_matched_accuracy","hash_matched_accuracy"):
                row[k] = 0.0
        with self.assertRaisesRegex(ValueError,"correctness"):
            self.check(trace,report)

    def test_forged_binary_kl_and_matching_aggregate_rejected(self):
        trace, report = fixture()
        row = report["individual_results"][0]
        row["explanation_kl"] = 0.0
        report["task_accuracy_and_selective_risk"]["heldout"]["explanation_kl"] = 0.0
        with self.assertRaisesRegex(ValueError,"explanation_kl"):
            self.check(trace,report)

    def test_forged_fidelity_gate_accuracy_rejected(self):
        trace, report = fixture()
        report["task_accuracy_and_selective_risk"]["heldout"]["fidelity_gate_accuracy"]=0.5
        with self.assertRaisesRegex(ValueError,"fidelity_gate_accuracy"):
            self.check(trace,report)

    def test_forged_confidence_matched_accuracy_rejected(self):
        trace, report = fixture()
        report["task_accuracy_and_selective_risk"]["adversarial"]["confidence_matched_accuracy"]=0.5
        with self.assertRaisesRegex(ValueError,"confidence_matched_accuracy"):
            self.check(trace,report)

    def test_forged_hash_matched_accuracy_rejected(self):
        trace, report = fixture()
        report["task_accuracy_and_selective_risk"]["control"]["hash_matched_accuracy"]=0.5
        with self.assertRaisesRegex(ValueError,"hash_matched_accuracy"):
            self.check(trace,report)

    def test_wrong_gold_label_rejected(self):
        trace, report = fixture()
        report["individual_results"][0]["gold"]="no"
        with self.assertRaisesRegex(ValueError,"gold"):
            self.check(trace,report)

    def test_duplicate_identity_rejected(self):
        trace, report = fixture()
        report["individual_results"].append(copy.deepcopy(report["individual_results"][0]))
        with self.assertRaisesRegex(ValueError,"identities"):
            self.check(trace,report)

    def test_forged_report_full_vocab_mean_rejected(self):
        trace, report = fixture()
        report["task_accuracy_and_selective_risk"]["heldout"]["full_vocabulary_probe_kl"]=0.0005
        with self.assertRaisesRegex(ValueError,"full_vocabulary_probe_kl"):
            self.check(trace,report)


if __name__=="__main__":
    unittest.main()
