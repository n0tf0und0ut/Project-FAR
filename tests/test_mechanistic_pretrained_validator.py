"""Negative tests for source-bound pretrained result correctness and risk metrics."""
from __future__ import annotations

import copy
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest

from evaluation.validate_pretrained_lm_result import verify, _binary_kl
from evaluation.run_pretrained_lm_fidelity import MODEL_ID, REVISION, task_cases, canonical
from mechanization.far_mechanization.mechanistic_fidelity import MechanismAudit


def fixture():
    registered = "2026-10-30T00:00:00Z"
    logged = "2026-10-30T01:00:00Z"
    source = "Source-bound synthetic verifier fixture; no pretrained run asserted."
    digest = hashlib.sha256(source.encode()).hexdigest()
    rows = []
    records = []
    for task in (c for c in task_cases() if c["split"] != "train"):
        split = task["split"]
        original = ["0.600000", "0.400000"] if task["gold"] == "yes" else ["0.400000", "0.600000"]
        explained = original if split == "control" else (["0.590000", "0.410000"] if task["gold"] == "yes" else ["0.410000", "0.590000"])
        baseline = ["0.550000", "0.450000"] if task["gold"] == "yes" else ["0.450000", "0.550000"]
        row = {
            "id": task["id"], "split":split,
            "input_sha256": hashlib.sha256(task["id"].encode()).hexdigest(),
            "measured_at":logged, "source_ids":["synthetic"],
            "observed_activation":"1.000000",
            "explained_activation":"1.000000" if split=="control" else "0.990000",
            "baseline_activation":"0.900000",
            "original_probs":original, "replacement_probs":explained,
            "baseline_probs":baseline,
        }
        rows.append(row)
        records.append({
            "id": row["id"], "split":split, "gold":task["gold"],
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
            "reference_population_sha256":hashlib.sha256(canonical([c["question"] for c in task_cases() if c["split"] == "train"])).hexdigest(),
            "execution_contract":{"deterministic":True,"same_nonintervened_state":True,
                                  "exact_output_distributions":True}},
        "explanation":{"id":"synthetic","description":"synthetic trace",
                       "hypothesis_source_ids":["synthetic"]},
        "sources":[{"id":"synthetic","text":source,"sha256":digest}],
        "cases":rows,
    }
    audit = MechanismAudit.from_dict(document).evaluate()
    summary = {}
    for split in ("heldout", "adversarial", "control"):
        group = [r for r in records if r["split"] == split]
        n = len(group)
        summary[split] = {
            "n":n, "model_accuracy":1.0, "replacement_accuracy":1.0,
            "mean_baseline_accuracy":1.0, "fidelity_gate_accepted":n,
            "fidelity_gate_accuracy":1.0,"confidence_matched_accuracy":1.0,
            "hash_matched_accuracy":1.0,
            "explanation_kl":sum(r["explanation_kl"] for r in group)/n,
            "baseline_kl":sum(r["mean_kl"] for r in group)/n,
            "full_vocabulary_probe_kl":sum(r["full_vocabulary_explanation_kl"] for r in group)/n,
            "full_vocabulary_baseline_kl":sum(r["full_vocabulary_mean_kl"] for r in group)/n,
            "cases_worse_than_baseline_full_vocabulary":0,
        }
    report = {
        "manifest":{"model_id":MODEL_ID,"model_revision":REVISION,
                    "weights_sha256":"a"*64,"answer_tokens":["yes","no"],
                    "evaluation_n":32,"per_split":12,"train_n":24},
        "individual_results":records,
        "mechanism_audit":audit,
        "task_accuracy_and_selective_risk":summary,
        "status":"EXPLORATORY_PRETRAINED_LM_PILOT_NO_EXTERNAL_SUPERIORITY_CLAIM",
    }
    source_text=json.dumps(report["manifest"],sort_keys=True)
    document["sources"].append({"id":"run-manifest","text":source_text,
                                "sha256":hashlib.sha256(source_text.encode()).hexdigest()})
    report["mechanism_audit"]=MechanismAudit.from_dict(document).evaluate()
    return document,report


class ResultVerifierMutationTests(unittest.TestCase):
    def test_4494409924_coordinated_subcohort_cannot_override_committed_manifest(self):
        trace,report=fixture()
        source=next(s for s in trace["sources"] if s["id"]=="run-manifest")
        committed=source["text"]
        trace["cases"]=[c for c in trace["cases"] if int(c["id"].rsplit("-",1)[1])<2]
        report["individual_results"]=[c for c in report["individual_results"] if int(c["id"].rsplit("-",1)[1])<2]
        report["manifest"].update(per_split=2,evaluation_n=6)
        report["mechanism_audit"]=MechanismAudit.from_dict(trace).evaluate()
        for summary in report["task_accuracy_and_selective_risk"].values():
            summary.update(n=2,fidelity_gate_accepted=2)
        self.assertEqual(source["text"],committed)
        self.assertEqual(json.loads(committed)["per_split"],12)
        with self.assertRaisesRegex(ValueError,"committed.*manifest"):
            self.check(trace,report)

    def test_preserved_actual_full_cohort_manifest_agrees(self):
        import zipfile
        root=Path(__file__).resolve().parents[1]
        with zipfile.ZipFile(root/"evaluation/evidence/pretrained-original-13051320299.zip") as archive:
            trace=json.loads(archive.read("far_mech_pretrained_trace.json"))
            report=json.loads(archive.read("far_mech_pretrained_result.json"))
        self.assertEqual(self.check(trace,report)["n"],32)

    def test_smaller_cohort_requires_its_own_committed_manifest(self):
        trace,report=fixture()
        trace["cases"]=[c for c in trace["cases"] if int(c["id"].rsplit("-",1)[1])<2]
        report["individual_results"]=[c for c in report["individual_results"] if int(c["id"].rsplit("-",1)[1])<2]
        report["manifest"].update(per_split=2,evaluation_n=6)
        for summary in report["task_accuracy_and_selective_risk"].values():
            summary.update(n=2,fidelity_gate_accepted=2)
        source=next(s for s in trace["sources"] if s["id"]=="run-manifest")
        source["text"]=json.dumps(report["manifest"],sort_keys=True)
        source["sha256"]=hashlib.sha256(source["text"].encode()).hexdigest()
        report["mechanism_audit"]=MechanismAudit.from_dict(trace).evaluate()
        self.assertEqual(self.check(trace,report)["n"],6)

    def test_missing_malformed_or_ambiguous_committed_manifest_is_rejected(self):
        for text in (None, "[]", '{"per_split":2,"per_split":12}'):
            trace,report=fixture()
            source=next(s for s in trace["sources"] if s["id"]=="run-manifest")
            if text is None:
                trace["sources"].remove(source)
            else:
                source["text"]=text
                source["sha256"]=hashlib.sha256(text.encode()).hexdigest()
            report["mechanism_audit"]=MechanismAudit.from_dict(trace).evaluate()
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.check(trace,report)

    def test_ambiguous_raw_report_cannot_choose_its_assurance_or_model_identity(self):
        trace, report = fixture()
        raw = json.dumps(report)
        bounded = report["status"]
        variants = [
            raw.replace(json.dumps("status")+": "+json.dumps(bounded),
                        '"status":"CLAIMS_SUPERIORITY", "status":'+json.dumps(bounded)),
            raw.replace(json.dumps("model_id")+": "+json.dumps(MODEL_ID),
                        '"model_id":"different-model", "model_id":'+json.dumps(MODEL_ID)),
        ]
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/"trace.json";source.write_text(json.dumps(trace))
            result=Path(temp)/"result.json"
            for index, candidate in enumerate(variants):
                result.write_text(candidate)
                with self.subTest(variant=index), self.assertRaisesRegex(ValueError,"duplicate JSON key"):
                    verify(source,result)

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
        self.assertEqual(result["n"],32)
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

    def test_coordinated_split_reassignment_rejected(self):
        trace, report = fixture()
        for row in trace["cases"] + report["individual_results"]:
            if row["split"] == "heldout":
                row["split"] = "adversarial"
            elif row["split"] == "adversarial":
                row["split"] = "heldout"
        report["mechanism_audit"] = MechanismAudit.from_dict(trace).evaluate()
        with self.assertRaisesRegex(ValueError, "split"):
            self.check(trace, report)

    def test_coordinated_missing_run_and_denominator_rewrite_rejected(self):
        trace, report = fixture()
        trace["cases"].pop(1)
        report["individual_results"].pop(1)
        report["manifest"]["evaluation_n"] -= 1
        report["task_accuracy_and_selective_risk"]["heldout"]["n"] -= 1
        report["task_accuracy_and_selective_risk"]["heldout"]["fidelity_gate_accepted"] -= 1
        report["mechanism_audit"] = MechanismAudit.from_dict(trace).evaluate()
        with self.assertRaisesRegex(ValueError, "cohort"):
            self.check(trace, report)

    def test_substituted_training_population_commitment_rejected(self):
        trace, report = fixture()
        trace["model"]["reference_population_sha256"] = "b" * 64
        report["mechanism_audit"] = MechanismAudit.from_dict(trace).evaluate()
        with self.assertRaisesRegex(ValueError, "population commitment"):
            self.check(trace, report)

    def test_third_outcome_mass_cannot_dilute_binary_metrics(self):
        trace, report = fixture()
        by_id = {r["id"]: r for r in report["individual_results"]}
        for case in trace["cases"]:
            for field in ("original_probs", "replacement_probs", "baseline_probs"):
                case[field] = [f"{Decimal(v) * Decimal('0.9'):.6f}" for v in case[field]] + ["0.100000"]
            rec = by_id[case["id"]]
            rec["explanation_kl"] = sum(float(a) * math.log(float(a) / float(b))
                                        for a, b in zip(case["original_probs"], case["replacement_probs"]))
            rec["mean_kl"] = sum(float(a) * math.log(float(a) / float(b))
                                 for a, b in zip(case["original_probs"], case["baseline_probs"]))
            rec["base_entropy"] = -sum(float(p) * math.log(float(p)) for p in case["original_probs"])
        for split, summary in report["task_accuracy_and_selective_risk"].items():
            group = [r for r in report["individual_results"] if r["split"] == split]
            for out, field in (("explanation_kl", "explanation_kl"), ("baseline_kl", "mean_kl")):
                summary[out] = sum(r[field] for r in group) / len(group)
        report["mechanism_audit"] = MechanismAudit.from_dict(trace).evaluate()
        self.assertEqual(report["manifest"]["answer_tokens"], ["yes", "no"])
        with self.assertRaisesRegex(ValueError, "two.*outcomes"):
            self.check(trace, report)

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
