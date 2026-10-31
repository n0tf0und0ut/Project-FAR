"""Independently recompute FAR-MECH binary fidelity and reasoning outcomes.

The full-vocabulary KL metrics remain *reported summaries* until replayed from
a checkpoint or supplemented with complete source logits. They are checked for
finiteness, case closure and aggregation here, not independently reconstructed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from evaluation.run_pretrained_lm_fidelity import MODEL_ID, REVISION, task_cases
from mechanization.far_mechanization.mechanistic_fidelity import MechanismAudit


def _binary_kl(p, q):
    a = [float(v) for v in p]
    b = [float(v) for v in q]
    return sum(x * math.log(x / y) for x, y in zip(a, b))


def _require_close(value, expected, label, atol=1e-10):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(label + ": nonfinite or nonnumeric")
    if not math.isclose(value, expected, rel_tol=1e-9, abs_tol=atol):
        raise ValueError(label + ": recorded value inconsistent with evidence")


def _accuracy(items):
    return sum(x["base_correct"] for x in items) / len(items) if items else None


def _require_accuracy(value, expected, label):
    if expected is None:
        if value is not None:
            raise ValueError(label + ": empty accepted sample must be null")
    else:
        _require_close(value, expected, label, atol=1e-12)


def verify(trace_path: Path, report_path: Path):
    trace = MechanismAudit.load(trace_path)
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    reaudited = trace.evaluate()
    if report["mechanism_audit"] != reaudited:
        raise ValueError("FAR-MECH report audit does not match source-committed trace")
    raw = trace.to_dict()
    source_cases = {c["id"]: c for c in raw["cases"]}
    entries = report["individual_results"]
    metrics = {x["id"]: x for x in entries}
    if len(metrics) != len(entries) or set(source_cases) != set(metrics):
        raise ValueError("report case identities do not match trace")
    frozen_tasks = {c["id"]: c for c in task_cases() if c["split"] != "train"}
    manifest = report["manifest"]
    if (manifest["model_id"] != MODEL_ID or manifest["model_revision"] != REVISION or
            manifest["weights_sha256"] != raw["model"]["artifact_sha256"] or
            manifest["answer_tokens"] != ["yes", "no"]):
        raise ValueError("model, token labels or checkpoint commitment mismatch")
    if len(source_cases) != manifest["evaluation_n"]:
        raise ValueError("evaluation cohort size disagrees with manifest")

    for case_id, case in source_cases.items():
        if case_id not in frozen_tasks:
            raise ValueError("case has no frozen task identity")
        task = frozen_tasks[case_id]
        row = metrics[case_id]
        if row["split"] != case["split"] or row["gold"] != task["gold"]:
            raise ValueError("case split or independently keyed gold label mismatch")
        if case["split"] == "control":
            if case["observed_activation"] != case["explained_activation"]:
                raise ValueError("identity control not intact")
        for source_field, result_field in (
            ("original_probs", "base_correct"),
            ("replacement_probs", "replacement_correct"),
            ("baseline_probs", "mean_correct"),
        ):
            p = [float(v) for v in case[source_field]]
            if abs(p[0] - p[1]) <= 2e-6:
                raise ValueError("rounded answer-probability near tie cannot certify correctness")
            predicted = "yes" if p[0] > p[1] else "no"
            if type(row[result_field]) is not bool or row[result_field] != (predicted == task["gold"]):
                raise ValueError("case correctness disagrees with source trace")
        for src_field, reported_field in (
            ("replacement_probs", "explanation_kl"),
            ("baseline_probs", "mean_kl"),
        ):
            derived = _binary_kl(case["original_probs"], case[src_field])
            _require_close(row[reported_field], derived, case_id + "/" + reported_field,
                           atol=2e-9)
        original = [float(v) for v in case["original_probs"]]
        ent = -sum(p * math.log(p) for p in original)
        _require_close(row["base_entropy"], ent, case_id + "/entropy", atol=5e-6)
        for field in ("full_vocabulary_explanation_kl", "full_vocabulary_mean_kl"):
            x = row[field]
            if type(x) not in (int, float) or not math.isfinite(x) or x < 0:
                raise ValueError("nonfinite/negative reported full-vocabulary KL")
        if case["split"] == "control" and row["full_vocabulary_explanation_kl"] > 1e-10:
            raise ValueError("identity intervention changed full-vocabulary distribution")

    summaries = report["task_accuracy_and_selective_risk"]
    if set(summaries) != {"heldout", "adversarial", "control"}:
        raise ValueError("missing or unexpected evaluation split")
    for split in ("heldout", "adversarial", "control"):
        sample = [metrics[c["id"]] for c in raw["cases"] if c["split"] == split]
        n = len(sample)
        target = summaries[split]
        if n == 0 or n != target["n"]:
            raise ValueError("empty/mismatched evaluation split")
        for aggregate, field in (
            ("full_vocabulary_probe_kl", "full_vocabulary_explanation_kl"),
            ("full_vocabulary_baseline_kl", "full_vocabulary_mean_kl"),
            ("explanation_kl", "explanation_kl"),
            ("baseline_kl", "mean_kl"),
        ):
            observed = sum(x[field] for x in sample) / n
            _require_close(target[aggregate], observed, split + "/" + aggregate)
        worse = sum(x["full_vocabulary_explanation_kl"] > x["full_vocabulary_mean_kl"]
                    for x in sample)
        if worse != target["cases_worse_than_baseline_full_vocabulary"]:
            raise ValueError("wrong counterexample count")
        for name, field in (
            ("model_accuracy", "base_correct"),
            ("replacement_accuracy", "replacement_correct"),
            ("mean_baseline_accuracy", "mean_correct"),
        ):
            observed = sum(x[field] for x in sample) / n
            _require_close(target[name], observed, split + "/" + name, atol=1e-12)

        accepted = [x for x in sample if x["explanation_kl"] <= 0.02]
        k = len(accepted)
        if target["fidelity_gate_accepted"] != k:
            raise ValueError("wrong fidelity gate count")
        confidence = sorted(sample, key=lambda x: (x["base_entropy"], x["id"]))[:k]
        hashed = sorted(sample, key=lambda x: hashlib.sha256(x["id"].encode()).hexdigest())[:k]
        for field, group in (
            ("fidelity_gate_accuracy", accepted),
            ("confidence_matched_accuracy", confidence),
            ("hash_matched_accuracy", hashed),
        ):
            _require_accuracy(target[field], _accuracy(group), split + "/" + field)

    if report["status"] != "EXPLORATORY_PRETRAINED_LM_PILOT_NO_EXTERNAL_SUPERIORITY_CLAIM":
        raise ValueError("unjustified assurance promotion")
    return {
        "status": "PASSED_BINARY_OUTCOME_RECOMPUTATION_AND_FULLVOCAB_AGGREGATE_CHECK",
        "n": len(source_cases),
        "trace_digest": trace.digest,
        "full_vocab_logits_replayed": False,
        "no_superiority_claim": True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=Path)
    parser.add_argument("result", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.trace, args.result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
