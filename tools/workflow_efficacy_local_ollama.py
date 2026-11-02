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
    task, fingerprint, public_test_code, hidden_test_code,
)

ROOT=Path(__file__).resolve().parents[1]
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
    root.mkdir(parents=True,exist_ok=True)
    (root/"solution.py").write_text(code)
    (root/"test_public.py").write_text(public_test_code(t))
    (root/"test_hidden.py").write_text(hidden_test_code(t))
    cmd=["docker","run","--rm","--network","none","--cap-drop","ALL",
      "--security-opt","no-new-privileges","--memory","384m","--pids-limit","64",
      "-e","PYTHONDONTWRITEBYTECODE=1","-v",str(root.resolve())+":/app:ro",
      "-w","/app","python:3.12-slim",
      "python","-B","-m","unittest","-q","test_public","test_hidden"]
    try:
        p=subprocess.run(cmd,text=True,capture_output=True,timeout=60)
        trace=(p.stdout+p.stderr)[:500000]
        ran=bool(re.search(r"Ran 2 tests? in ",trace))
        return (ran, p.returncode==0 and ran, p.returncode, trace)
    except (OSError,subprocess.TimeoutExpired) as exc:
        return (False,False,None,type(exc).__name__)

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
    raw="" if response is None else str(response.get("response") or "")
    code=extract(raw)
    (root/"model-output.txt").write_text(raw)
    (root/"solution.py").write_text(code)
    ran,passed,returncode,trace=grade(code,t,root/"grader")
    (root/"grade.txt").write_text(trace)
    valid=(response is not None and response.get("done") is True
        and response.get("model")==MODEL and not response.get("error")
        and isinstance(response.get("eval_count"),int)
        and response["eval_count"]>0 and error is None and ran)
    state="SUCCESS" if valid and passed else ("FAILURE" if valid else "INCOMPLETE")
    r={"task_id":t["task_id"],"arm":arm,"model":MODEL,"model_digest":identity,
       "options":OPTIONS,"corpus_sha":fingerprint(),
       "instructions_sha":sha(instructions(arm)),
       "prompt_sha":sha(text.encode()),"duration_s":elapsed,
       "provider_error_class":error,"done":response.get("done") if response else None,
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
    if a.index is None or a.output is None or not 0<=a.index<30:
        ap.error("run-pair requires --index 0..29 and --output")
    a.output.mkdir(parents=True,exist_ok=True)
    records=[run_one(a.index,arm,a.output) for arm in order(a.index)]
    (a.output/("pair-%02d.json"%a.index)).write_text(json.dumps(records,indent=2))
    print(json.dumps({"case":a.index,"outcomes":[x["outcome"] for x in records],
                      "model_digest":records[0]["model_digest"]}))
    return 0 if all(x["outcome"]!="INCOMPLETE" for x in records) else 2

if __name__=="__main__":
    sys.exit(main())
