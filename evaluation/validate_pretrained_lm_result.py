"""Fail-closed audit of pretrained-model run artifacts, independent of LLM weights.

This checks the submitted FAR-MECH trace, per-case and aggregate summaries,
including full-vocabulary KL statistics. It does NOT independently replay
pretrained model weights or authenticate the provenance of remote executions.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
from mechanization.far_mechanization.mechanistic_fidelity import MechanismAudit


def verify(trace_path: Path, report_path: Path):
    trace=MechanismAudit.load(trace_path)
    report=json.loads(report_path.read_text(encoding="utf-8"))
    reaudited=trace.evaluate()
    if report["mechanism_audit"] != reaudited:
        raise ValueError("FAR-MECH audit does not match raw trace")
    raw=trace.to_dict()
    cases={x["id"]:x for x in raw["cases"]}
    metrics={x["id"]:x for x in report["individual_results"]}
    if set(cases)!=set(metrics):
        raise ValueError("case identities do not match")
    for key, case in cases.items():
        line=metrics[key]
        if line["split"]!=case["split"]:
            raise ValueError("split identity mismatch")
        for field in ("full_vocabulary_explanation_kl","full_vocabulary_mean_kl"):
            value=line[field]
            if not isinstance(value,(int,float)) or not math.isfinite(value) or value < 0:
                raise ValueError("missing/nonfinite full-vocabulary KL")
        if case["split"]=="control" and line["full_vocabulary_explanation_kl"] > 1e-10:
            raise ValueError("identity intervention changed full-vocabulary distribution")
    summaries=report["task_accuracy_and_selective_risk"]
    for split in ("heldout","adversarial","control"):
        lines=[x for x in metrics.values() if x["split"]==split]
        n=len(lines)
        if n==0 or n!=summaries[split]["n"]:
            raise ValueError("empty/mismatched split")
        target=summaries[split]
        candidates=(
            ("full_vocabulary_probe_kl","full_vocabulary_explanation_kl"),
            ("full_vocabulary_baseline_kl","full_vocabulary_mean_kl"),
            ("explanation_kl","explanation_kl"),
            ("baseline_kl","mean_kl"),
        )
        for aggregate,field in candidates:
            mean=sum(x[field] for x in lines)/n
            if not math.isclose(mean,target[aggregate],rel_tol=1e-9,abs_tol=1e-11):
                raise ValueError("aggregate "+aggregate+" mismatch for "+split)
        worse=sum(x["full_vocabulary_explanation_kl"] > x["full_vocabulary_mean_kl"] for x in lines)
        if worse!=target["cases_worse_than_baseline_full_vocabulary"]:
            raise ValueError("counterexample count mismatch")
        for score_key, outcome_key in (("model_accuracy","base_correct"),
                                       ("replacement_accuracy","replacement_correct"),
                                       ("mean_baseline_accuracy","mean_correct")):
            rate=sum(int(x[outcome_key]) for x in lines)/n
            if not math.isclose(rate,target[score_key],abs_tol=1e-12):
                raise ValueError("reasoning accuracy mismatch")
        if target["fidelity_gate_accepted"]!=sum(x["explanation_kl"]<=0.02 for x in lines):
            raise ValueError("fidelity gate count mismatch")
    manifest=report["manifest"]
    if manifest["model_revision"]!="12fd25f77366fa6b3b4b768ec3050bf629380bac":
        raise ValueError("unexpected model revision")
    if manifest["weights_sha256"]!=raw["model"]["artifact_sha256"]:
        raise ValueError("weight commitment mismatch")
    if report["status"]!="EXPLORATORY_PRETRAINED_LM_PILOT_NO_EXTERNAL_SUPERIORITY_CLAIM":
        raise ValueError("unjustified assurance promotion")
    return {"status":"PASSED_SUBMITTED_RESULT_CONSISTENCY_ONLY",
            "n":len(cases),"trace_digest":trace.digest,
            "no_superiority_claim":True}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("trace",type=Path)
    parser.add_argument("result",type=Path)
    args=parser.parse_args()
    print(json.dumps(verify(args.trace,args.result),indent=2,sort_keys=True))


if __name__=="__main__":
    main()
