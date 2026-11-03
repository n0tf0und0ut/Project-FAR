"""Credential-free, locally inferred, one-shot Qwen coding-repair experiment.

This is a synthetic instruction-effect test, not an autonomous agent or FAR PR replay.
Never execute model-written code outside the offline Docker grader.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from tools.workflow_efficacy_internal_fixtures import (
    task, fingerprint,
)

from tools.workflow_efficacy_free_agent import grade as isolated_grade

ROOT=Path(__file__).resolve().parents[1]
HARNESS_VERSION="local-qwen-validation-v0.2"
CONTROL="38e6c8e8b3b1f0a7c75795c9eac8c1c6189cf7ab"
TREATMENT="dc290674b755977378d6170a0128c1540f0a2b6a"
MODEL="qwen2.5-coder:1.5b"
URL="http://127.0.0.1:11434"
OPTIONS={"temperature":0,"seed":602,"num_ctx":4096,"num_predict":320,"num_thread":4}
ARMS=("control","treatment")

def sha(b):
    return hashlib.sha256(b).hexdigest()

def request(path,payload=None,timeout=20):
    data=None if payload is None else json.dumps(payload,sort_keys=True).encode()
    req=urllib.request.Request(URL+path,data=data,headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return json.loads(r.read(2000000))

def extract_section(document: bytes, heading: str) -> bytes:
    """Extract an exact source section without paraphrase or silent truncation."""
    text=document.decode("utf-8")
    m=re.search(r"^"+re.escape(heading)+r"\s*\n.*?(?=^## |\Z)",text,re.M|re.S)
    if m is None:
        raise ValueError("required canonical instruction heading absent: "+heading)
    return m.group(0).strip().encode("utf-8")

def instructions(arm):
    if arm not in ARMS: raise ValueError(arm)
    revision=CONTROL if arm=="control" else TREATMENT
    raw=subprocess.check_output(["git","show",revision+":AGENTS.md"],cwd=ROOT,timeout=20)
    selections=["## Rules for getting work done","## Completion standard"]
    if arm=="treatment":
        selections.insert(0,"## Workflow orchestration")
    content=b"\n\n".join(extract_section(raw,h) for h in selections)
    if arm=="treatment":
        guide=subprocess.check_output(
            ["git","show",revision+":docs/maintenance/agent-workflow-orchestration.md"],
            cwd=ROOT,timeout=20)
        content+=b"\n\n"+guide
    return content

def order(index):
    if not 0<=index<30: raise ValueError(index)
    ranking=sorted((sha(("far-ollama-v1|"+task(i)["task_id"]).encode()),i) for i in range(30))
    control_first={i for _,i in ranking[:15]}
    return ARMS if index in control_first else tuple(reversed(ARMS))

def model_sha():
    matches=[m for m in request("/api/tags")["models"] if m.get("name")==MODEL]
    if len(matches)!=1 or len(matches[0].get("digest",""))<60:
        raise ValueError("no uniquely resolved local model digest")
    return matches[0]["digest"]

def prompt(index,arm):
    t=task(index)
    return ("Follow the following software-development instructions while solving the task:\n"
        +instructions(arm).decode("utf-8")
        +"\n\nImplement Python function transform(payload) for this task:\n"+t["spec"]
        +"\n\nExisting buggy code:\n"+t["source"]
        +"\n\nPublic examples:\n"+json.dumps(t["public"])
        +"\n\nReturn ONLY the complete executable replacement Python source file. "
        +"Do not include explanations or hidden-test assumptions.")

def extract(raw):
    fence=chr(96)*3
    match=re.search(re.escape(fence)+r"(?:python)?\s*\n(.*?)"+re.escape(fence),raw,re.S|re.I)
    return (match.group(1) if match else raw).strip()+"\n"

def grade(code,t,root):
    """Reuse the hardened trusted-host scorer from completed pilot #605.

    Expected values never enter the submitted Python interpreter. Shared grader
    bounds output, explicitly removes every container and exposes raw comparisons.
    """
    root.mkdir(parents=True,exist_ok=True)
    source=root/"solution.py"
    source.write_text(code,encoding="utf-8")
    passed,returncode,_digest,trace,executed=isolated_grade(source,t,root)
    return executed,passed,returncode,trace


def run_one(index,arm,out):
    t=task(index)
    root=out/(t["task_id"]+"-"+arm)
    root.mkdir(parents=True,exist_ok=False)
    identity=model_sha()
    text=prompt(index,arm)
    start=time.monotonic()
    response=None
    error=None
    try:
        response=request("/api/generate",{"model":MODEL,"prompt":text,
          "stream":False,"options":OPTIONS,"keep_alive":"10m"},timeout=300)
    except Exception as exc:
        error=type(exc).__name__
    elapsed=round(time.monotonic()-start,3)
    if response is not None and not isinstance(response,dict):
        error="InvalidProviderEnvelope"
        response=None
    raw="" if response is None else str(response.get("response") or "")
    provider=json.dumps(response,sort_keys=True,allow_nan=False)+"\n"
    (root/"provider-response.json").write_text(provider,encoding="utf-8")
    code=extract(raw)
    (root/"model-output.txt").write_text(raw)
    (root/"solution.py").write_text(code)
    inference_valid=(response is not None and response.get("done") is True
        and response.get("done_reason")=="stop"
        and response.get("model")==MODEL and not response.get("error")
        and type(response.get("eval_count")) is int
        and response["eval_count"]>0 and error is None)
    if inference_valid:
        ran,passed,returncode,trace=grade(code,t,root/"grader")
    else:
        ran,passed,returncode,trace=False,False,None,"INCOMPLETE_INFERENCE: no submitted code executed"
    (root/"grade.txt").write_text(trace)
    valid=inference_valid and ran
    state="SUCCESS" if valid and passed else ("FAILURE" if valid else "INCOMPLETE")
    r={"harness_version":HARNESS_VERSION,"task_id":t["task_id"],"arm":arm,"model":MODEL,"model_digest":identity,
       "options":OPTIONS,"corpus_sha":fingerprint(),
       "instructions_sha":sha(instructions(arm)),
       "prompt_sha":sha(text.encode()),"duration_s":elapsed,
       "provider_error_class":error,"done":response.get("done") if response else None,
       "done_reason":response.get("done_reason") if response else None,
       "provider_response_sha":sha((root/"provider-response.json").read_bytes()),
       "input_tokens":response.get("prompt_eval_count") if response else None,
       "output_tokens":response.get("eval_count") if response else None,
       "grader_executed":ran,"grader_exit_code":returncode,"outcome":state,
       "model_output_sha":sha((root/"model-output.txt").read_bytes()),
       "solution_sha":sha((root/"solution.py").read_bytes()),
       "grade_sha":sha((root/"grade.txt").read_bytes())}
    (root/"record.json").write_text(json.dumps(r,indent=2,sort_keys=True))
    return r

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("action",choices=["contract","run-pair"])
    ap.add_argument("--index",type=int)
    ap.add_argument("--output",type=Path)
    a=ap.parse_args()
    if a.action=="contract":
        print(json.dumps({"model":MODEL,"options":OPTIONS,"pairs":30,"runs":60,
            "corpus_sha":fingerprint(),"control":CONTROL,"treatment":TREATMENT,
            "claims":"synthetic one-shot coding-repair only"},indent=2))
        return 0
    ap.error("Original v0.1 live entry point retired after failed preflight; "
             "a separately registered successor identity and output location are required.")

if __name__=="__main__":
    sys.exit(main())
