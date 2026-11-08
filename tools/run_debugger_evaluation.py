#!/usr/bin/env python3
"""Registered internal debugger campaign. Never overwrites inputs or outcomes."""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
COMPONENT=ROOT/"commercial/far-investigation-audit"
CORPUS=COMPONENT/"evaluation/debugger-001"


def sha(raw):return hashlib.sha256(raw).hexdigest()
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("x",encoding="utf-8") as f:json.dump(value,f,sort_keys=True,indent=2,allow_nan=False);f.write("\n")


def runtime_files():
    return [*sorted(COMPONENT.glob("*.py")),ROOT/"tools/run_debugger_evaluation.py",CORPUS/"semantic-cases-v1.json",CORPUS/"protocol-v1.json",
            COMPONENT/"evaluation/internal-001/cases-v1.json"]


def freeze(path,baseline,noesis):
    pin=subprocess.check_output(["git","-C",str(baseline),"rev-parse","HEAD"],text=True).strip()
    record={"schema":"far-debugger-registration/1.0","status":"FROZEN_INTERNAL_EXPLORATORY",
            "created_at":datetime.now(timezone.utc).isoformat(),"independent":False,"baseline_commit":pin,
            "source_files":{str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in runtime_files()},
            "versions":{k:importlib.metadata.version(k) for k in ["sympy","hypothesis","jsonschema","noesis-evidence"]},
            "noesis_cli_sha256":sha(noesis.read_bytes()),"noesis_commit":"d38eb1fd956843b6eeeaeb582d3b4e1092255d94",
            "external_calls":0,"external_truth_accuracy":None,"EFR":"NOT_EXECUTED"}
    write(path,record)
    return record


def synthetic_configs():
    cases=json.loads((CORPUS/"semantic-cases-v1.json").read_text())
    rows=[]
    for c in cases:
        a,b=c["source"],c["interpretation"]
        rows.append({"case_id":"semantic-"+c["id"],"reference":c,"config":{
            "investigation_id":"semantic-"+c["id"],"captured_at":"2026-10-27T12:00:00Z",
            "source":{"kind":"text","text":a+"\n"+b},"proposal_mode":"supplied","proposal":{
                "atoms":{"P":b},"claims":[{"id":"c1","quote":a,"start":0,"formula":{"atom":"P"}},
                                              {"id":"c2","quote":b,"start":len(a)+1,"formula":{"atom":"P"}}],
                "arguments":[{"id":"reading","premises":["c1"],"conclusion":"c2"}],"evidence":[],"unknowns":[]}}})
    return rows


def worker(root,output,enabled):
    sys.path.insert(0,str(root/"commercial/far-investigation-audit"))
    from workflow import investigate
    from full_cli import write_package,verify_package
    rows=json.loads((COMPONENT/"evaluation/internal-001/cases-v1.json").read_text())["source_to_report"]+synthetic_configs()
    results=[]
    for row in rows:
        config=copy.deepcopy(row["config"])
        if enabled:config["debugger"]=True
        start=time.perf_counter()
        p=investigate(config)
        path=output/row["case_id"]
        write_package(path,p)
        verified=verify_package(path)
        results.append({"case_id":row["case_id"],"elapsed_seconds":time.perf_counter()-start,
                        "formal_statuses":[r["formal_inference"]["status"] for r in p["audit"]["interpretations"]],
                        "factual_verdicts":["NOT_ADJUDICATED" for x in p["audit"]["claims"].values()],
                        "semantic_statuses":{k:v["status"] for k,v in p.get("debugger",{}).get("claims",{}).items()},
                        "acceptance":[r["acceptance"] for r in p.get("debugger",{}).get("readings",[])],
                        "verified":verified["replay_match"]})
    write(output/"results.json",results)


def run(registration,baseline,output,noesis):
    record=json.loads(registration.read_text())
    for name,expected in record["source_files"].items():
        if sha((ROOT/name).read_bytes())!=expected:raise ValueError("registered source drift: "+name)
    if subprocess.check_output(["git","-C",str(baseline),"rev-parse","HEAD"],text=True).strip()!=record["baseline_commit"]:
        raise ValueError("baseline drift")
    if sha(noesis.read_bytes())!=record["noesis_cli_sha256"]:raise ValueError("Noesis CLI drift")
    output.mkdir(parents=True,exist_ok=False)
    write(output/"registration.json",record)
    commands=[]
    for name,root,enabled in [("baseline",baseline,False),("debugger",ROOT,True)]:
        cmd=[sys.executable,str(Path(__file__).resolve()),"worker","--root",str(root),"--output",str(output/name)]
        if enabled:cmd.append("--enabled")
        start=time.perf_counter()
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=180,cwd=ROOT)
        receipt={"argv":cmd,"returncode":result.returncode,"stdout":result.stdout,"stderr":result.stderr,"elapsed_seconds":time.perf_counter()-start}
        write(output/(name+"-receipt.json"),receipt);commands.append(receipt)
        if result.returncode:raise ValueError("failed worker; retained "+name+"-receipt.json")
    sys.path.insert(0,str(ROOT/"tools"))
    import run_internal_investigation_evaluation as prior
    old=json.loads((COMPONENT/"evaluation/internal-001/cases-v1.json").read_text())
    comparisons=[]
    for row in old["source_to_report"]:
        if row["case_id"] in old["raw_comparison_case_ids"]:
            dest=output/"noesis"/row["case_id"];dest.mkdir(parents=True)
            try:
                comparisons.append({"case_id":row["case_id"],"result":prior.raw_noesis(row["config"],"Identify the checkable claims and the reasoning errors in the supplied documents.",dest,noesis)})
            except Exception as exc:
                comparisons.append({"case_id":row["case_id"],"status":"FAILED_EXECUTION_NOT_COMPETITOR_LOSS","error":str(exc)})
    write(output/"noesis-results.json",comparisons)
    import statistics
    new=json.loads((output/"debugger/results.json").read_text());old_results=json.loads((output/"baseline/results.json").read_text())
    cases=synthetic_configs()
    metrics={"confusion":{},"coverage":{},"latency_mean_seconds":{k:statistics.mean(r["elapsed_seconds"] for r in rs) for k,rs in [("baseline",old_results),("debugger",new)]}}
    refs={r["case_id"]:r["reference"]["expected"] for r in cases}
    for r in new:
        if r["case_id"] in refs:
            key=refs[r["case_id"]]+" -> "+r["semantic_statuses"]["c1"]
            metrics["confusion"][key]=metrics["confusion"].get(key,0)+1
    metrics["coverage"]={"source_to_report_cases":len(new),"new_factual_verdicts":{x:sum(r["factual_verdicts"].count(x) for r in new) for x in set(sum([r["factual_verdicts"] for r in new],[]))},
                         "semantic_acceptances":sum(r["acceptance"].count("CONDITIONAL_ON_GRAMMAR_AND_PREMISES") for r in new),"unseen_or_independent_cases":0}
    write(output/"summary.json",{"schema":"far-debugger-results/1.0","metrics":metrics,"noesis_runs":comparisons,
                                "missingness":{"frontier_model":"NOT_RUN_NO_CONFIGURED_BENCHMARK_PROVIDER","QURI":"NOT_RUN_SERVICE_CONFIG_UNAVAILABLE","Factiverse":"NOT_RUN_AUTHENTICATED_ARM_UNAVAILABLE","Fact_Engineering":"NOT_RUN_AUTHENTICATED_ARM_UNAVAILABLE","Minerval":"NOT_RUN_LOCAL_SERVICE_MODEL_CONFIGURATION_UNAVAILABLE","scite":"NOT_RUN_MATCHED_PRODUCT_ARM_UNAVAILABLE","ASPARTIX_DoWhy_Graphiti":"PRIOR_ART_ONLY_NOT_EXECUTED"},
                                "accuracy_world_truth":None,"commercial_advantage":"UNESTABLISHED","external_API_charge":0,"host_and_analyst_cost":"UNMEASURED"})
    return metrics


def main():
    p=argparse.ArgumentParser();s=p.add_subparsers(dest="command",required=True)
    f=s.add_parser("freeze");f.add_argument("--output",type=Path,required=True);f.add_argument("--baseline",type=Path,required=True);f.add_argument("--noesis",type=Path,required=True)
    r=s.add_parser("run");r.add_argument("--registration",type=Path,required=True);r.add_argument("--output",type=Path,required=True);r.add_argument("--baseline",type=Path,required=True);r.add_argument("--noesis",type=Path,required=True)
    w=s.add_parser("worker");w.add_argument("--root",type=Path,required=True);w.add_argument("--output",type=Path,required=True);w.add_argument("--enabled",action="store_true")
    a=p.parse_args()
    if a.command=="freeze":value=freeze(a.output,a.baseline,a.noesis)
    elif a.command=="worker":value=worker(a.root,a.output,a.enabled)
    else:value=run(a.registration,a.baseline,a.output,a.noesis)
    print(json.dumps(value,sort_keys=True))


if __name__=="__main__":main()
