#!/usr/bin/env python3
"""Reproduce the internal distribution-shift and specific fault-injection controls."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import tempfile
import time
import collections
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
COMPONENT=ROOT/"commercial/far-investigation-audit"
sys.path.insert(0,str(COMPONENT))


def shift(source):
    from workflow import investigate
    from full_cli import write_package,verify_package
    protocol=json.loads((COMPONENT/"evaluation/debugger-001/distribution-shift-protocol-v1.json").read_text())
    raw=source.read_bytes()
    if len(raw)>1_000_000 or hashlib.sha256(raw).hexdigest()!=protocol["source_sha256"]:
        raise ValueError("registered distribution source mismatch")
    rows=[]
    with tempfile.TemporaryDirectory() as t:
        for i,problem in enumerate(ET.fromstring(raw).findall("problem")):
            selected=[n for n in problem.findall("p/english")+problem.findall("h/english") if n.text and n.text.strip()]
            text="\n".join(" ".join(n.text.split()) for n in selected)
            if not text:
                rows.append({"id":problem.get("id"),"status":"MISSING_ENGLISH_TEXT"});continue
            start=time.perf_counter()
            try:
                result=investigate({"investigation_id":"fracas-"+str(i),"captured_at":"2026-10-27T12:00:00Z","source":{"kind":"text","text":text},"debugger":True})
                dest=Path(t)/str(i);write_package(dest,result);verified=verify_package(dest)
                statuses=[r["status"] for r in result["debugger"]["claims"].values()]
                rows.append({"id":problem.get("id"),"input_sha256":result["audit"]["input_sha256"],"status":"EXECUTED","claim_count":len(statuses),"semantic_statuses":statuses,
                             "acceptances":[r["acceptance"] for r in result["debugger"]["readings"]],"replay_match":verified["replay_match"],"elapsed_seconds":time.perf_counter()-start})
            except Exception as exc:
                rows.append({"id":problem.get("id"),"status":"FAILED","error":type(exc).__name__+": "+str(exc)})
    counts=collections.Counter(s for row in rows for s in row.get("semantic_statuses",[]))
    return {"schema":"far-debugger-distribution-shift-results/1.0","protocol":protocol,"cases":rows,
            "summary":{"total":len(rows),"executed":sum(r["status"]=="EXECUTED" for r in rows),"status_counts":dict(collections.Counter(r["status"] for r in rows)),"semantic_status_counts":dict(counts),"factual_accuracy":None,"NLI_accuracy":None,
                       "meaning":"Coverage-only distribution shift; exact copied text does not independently validate interpretation. Outcomes did not drive grammar edits."}}


def mutations():
    import semantic,debugger,memory
    sys.path.insert(0,str(COMPONENT/"tests"))
    import test_debugger
    controls=[]
    original_compile=semantic.compile_text
    with patch("semantic.compile_text",side_effect=lambda x,**kw:original_compile(x.replace("Some ","All "),**kw)):
        r=semantic.fidelity("Some birds are blue.",{"atom":"P"},{"P":"All birds are blue."})
        controls.append({"mutation":"collapse some to all","killed":r["status"]!="CONTRADICTED","observed":r["status"]})
    original_fidelity=debugger.fidelity
    def false_mapping(*a,**kw):
        result=original_fidelity(*a,**kw);result["status"]="SUPPORTED_IN_GRAMMAR";return result
    with patch("debugger.fidelity",side_effect=false_mapping):
        result=unittest.TestResult();test_debugger.SemanticAcceptance("test_quantifier_proof_gate").run(result)
        controls.append({"mutation":"accept every semantic mapping","killed":bool(result.failures or result.errors),"failures":len(result.failures),"errors":len(result.errors)})
    original_project=memory.Memory._project
    def no_invalidation(*a,**kw):
        result=original_project(*a,**kw);result["invalidated"]=[];return result
    with patch.object(memory.Memory,"_project",staticmethod(no_invalidation)):
        result=unittest.TestResult();test_debugger.ReplayMemoryAcceptance("test_retraction_propagation_restore_history_and_unrelated_preservation").run(result)
        controls.append({"mutation":"erase correction propagation","killed":bool(result.failures or result.errors),"failures":len(result.failures),"errors":len(result.errors)})
    return {"scope":"Three specific in-process fault injections; not exhaustive mutation adequacy","controls":controls}


def main():
    parser=argparse.ArgumentParser();parser.add_argument("control",choices=["shift","mutations"]);parser.add_argument("--source",type=Path);parser.add_argument("--output",type=Path,required=True);args=parser.parse_args()
    value=shift(args.source) if args.control=="shift" else mutations()
    value["reproduction_driver_sha256"]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with args.output.open("x") as f:json.dump(value,f,indent=2);f.write("\n")
    if args.control=="mutations" and not all(c["killed"] for c in value["controls"]):return 1
    return 0


if __name__=="__main__":raise SystemExit(main())
