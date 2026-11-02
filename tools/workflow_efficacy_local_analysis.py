"""Fail-closed analysis of all 60 real local-model coding-repair observations."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import random
from pathlib import Path
from statistics import mean
from tools.workflow_efficacy_internal_fixtures import fingerprint, task
from tools.workflow_efficacy_local_ollama import MODEL, OPTIONS, instructions, sha

def analyze(root):
    root=Path(root)
    failures=[]
    rows={}
    for i in range(30):
        name=f"pair-{i:02d}.json"
        path=root/name
        if not path.is_file():
            failures.append("MISSING_PAIR:"+name)
            continue
        try:
            pair=json.loads(path.read_text())
            assert isinstance(pair,list) and len(pair)==2
        except (ValueError,AssertionError,OSError,TypeError):
            failures.append("MALFORMED_PAIR:"+name)
            continue
        for record in pair:
            if not isinstance(record,dict):
                failures.append("MALFORMED_RECORD:"+name)
                continue
            tid=task(i)["task_id"]
            arm=record.get("arm")
            key=(tid,arm)
            if arm not in ("control","treatment") or record.get("task_id")!=tid or key in rows:
                failures.append("BAD_RUN_ID:"+name)
                continue
            rows[key]=record
            if record.get("corpus_sha")!=fingerprint():
                failures.append("CORPUS_MISMATCH:"+name)
            if record.get("model")!=MODEL or record.get("options")!=OPTIONS:
                failures.append("MODEL_OR_OPTIONS_MISMATCH:"+name)
            if record.get("instructions_sha")!=sha(instructions(arm)):
                failures.append("INSTRUCTIONS_MISMATCH:"+name)
            if record.get("done") is not True or record.get("provider_error_class") is not None:
                failures.append("UNFINISHED_INFERENCE:"+name)
            if type(record.get("output_tokens")) is not int or record["output_tokens"]<=0:
                failures.append("NO_VERIFIED_TOKENS:"+name)
            if record.get("grader_executed") is not True or record.get("grader_exit_code") not in (0,1):
                failures.append("MISSING_GRADER:"+name)
            if record.get("outcome") not in ("SUCCESS","FAILURE"):
                failures.append("INVALID_OUTCOME:"+name)
            if record.get("outcome")=="SUCCESS" and record.get("grader_exit_code")!=0:
                failures.append("CONTRADICTORY_SUCCESS:"+name)
            folder=root/(tid+"-"+arm)
            for filename,field in [("model-output.txt","model_output_sha"),
                                    ("solution.py","solution_sha"),("grade.txt","grade_sha")]:
                f=folder/filename
                if not f.is_file() or sha(f.read_bytes())!=record.get(field):
                    failures.append("EVIDENCE_MISMATCH:"+name+":"+filename)
    digests={r.get("model_digest") for r in rows.values()}
    if len(digests)!=1 or any(not isinstance(x,str) or len(x)<60 for x in digests):
        failures.append("MODEL_DIGEST_NOT_CONSTANT")
    if len(rows)!=60:
        failures.append("NOT_60_UNIQUE_RUNS")
    base={"schema":"far-local-ollama-analysis/0.1",
          "scope":"one-shot synthetic coding repair, NOT autonomous FAR development",
          "expected_runs":60,"observed_unique_runs":len(rows),
          "model":MODEL,"model_digests":sorted(str(x) for x in digests),
          "errors":failures,"causal_generalization":False}
    if failures:
        return dict(base,status="INCOMPLETE_OR_INVALID",claim="NO_PERFORMANCE_ESTIMATE")
    diffs=[]
    for i in range(30):
        key=task(i)["task_id"]
        diffs.append(int(rows[(key,"treatment")]["outcome"]=="SUCCESS") -
                     int(rows[(key,"control")]["outcome"]=="SUCCESS"))
    wins=sum(x==1 for x in diffs)
    losses=sum(x==-1 for x in diffs)
    discordant=wins+losses
    p=min(1.0,2*sum(math.comb(discordant,i) for i in range(min(wins,losses)+1))/2**discordant) if discordant else 1.0
    rng=random.Random(606602)
    boot=sorted(mean(rng.choice(diffs) for _ in range(30)) for _ in range(10000))
    return dict(base,status="COMPLETE_INTERNAL_SYNTHETIC_60_RUN_SAMPLE",
        control_success=sum(rows[(task(i)["task_id"],"control")]["outcome"]=="SUCCESS" for i in range(30)),
        treatment_success=sum(rows[(task(i)["task_id"],"treatment")]["outcome"]=="SUCCESS" for i in range(30)),
        paired_delta=mean(diffs),
        bootstrap_interval_95pct=[boot[249],boot[9749]],
        discordant_treatment_wins=wins,discordant_control_wins=losses,
        exact_sign_test_p=p,
        mean_duration_delta_seconds=mean(
            rows[(task(i)["task_id"],"treatment")]["duration_s"] -
            rows[(task(i)["task_id"],"control")]["duration_s"] for i in range(30)),
        claim="EXPLORATORY_SYNTHETIC_ONE_SHOT_RESULT_ONLY")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",type=Path,required=True)
    parser.add_argument("--out",type=Path)
    args=parser.parse_args()
    result=analyze(args.root)
    rendered=json.dumps(result,indent=2,sort_keys=True)+"\n"
    print(rendered)
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(rendered)
    return 0 if result["status"]=="COMPLETE_INTERNAL_SYNTHETIC_60_RUN_SAMPLE" else 2

if __name__=="__main__":
    raise SystemExit(main())
