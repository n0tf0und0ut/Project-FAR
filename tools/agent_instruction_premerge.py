#!/usr/bin/env python3
"""Prospectively locked 40-slot AGENTS.md screen; no claim of model execution.

Setup/schedule and scoring are deterministic. Live calls require an installed,
operator-configured Codex CLI; candidate source is graded only in pinned Docker.
The tool never changes frozen protocol files and never merges pull requests.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid

from tools.workflow_efficacy_free_agent import (
    capture_candidate_process, execute_agent_process,
    unauthorized_file_changes, GRADER_IMAGE, CANDIDATE_STARTED,
    MAX_CANDIDATE_OUTPUT_BYTES,
)

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "research/agent-instruction-evaluation/ponytail-premerge-001"
PROTOCOL = REG / "protocol.json"
TASKS = REG / "tasks.json"
SCHEDULE = REG / "schedule.json"
ARMS = ("control", "treatment")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
ID = re.compile(r"[A-Z][A-Z0-9]*-[0-9]{2}\Z")
START = "FAR_CANDIDATE_STARTED_V1"
FINISH = "FAR_CANDIDATE_COMPLETED_V1"
IMAGE = GRADER_IMAGE
ENTRYPOINT = (
    "import json,runpy,sys\n"
    "sys.path.insert(0,'/app')\n"
    "d=json.load(sys.stdin)\n"
    "sys.stdout.write('" + START + "\\n');sys.stdout.flush()\n"
    "candidate=runpy.run_path('/app/solution.py')\n"
    "answer=candidate['transform'](d)\n"
    "sys.stdout.write(json.dumps(answer,sort_keys=True,allow_nan=False,separators=(',',':')))\n"
    "sys.stdout.write('\\n" + FINISH + "\\n');sys.stdout.flush()\n"
)


class ContractError(ValueError):
    pass


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def pairs_unique(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ContractError("duplicate JSON key: " + k)
        out[k] = v
    return out


def strict_load(raw):
    def bad(value):
        raise ContractError("non-finite JSON value: " + value)
    return json.loads(raw, object_pairs_hook=pairs_unique, parse_constant=bad)


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False,
                      ensure_ascii=False).encode("utf-8")


def safe_path(value):
    if not isinstance(value,str) or not value or "\\" in value or "\x00" in value:
        raise ContractError("unsafe path")
    p = PurePosixPath(value)
    if p.is_absolute() or ".." in p.parts or "." in p.parts or str(p) != value:
        raise ContractError("non-canonical path")
    return p


def load_contract():
    proto = strict_load(PROTOCOL.read_bytes())
    if proto.get("schema") != "far-agent-instruction-premerge/1" or proto.get("experiment_id") != "FAR-PONYTAIL-PREMERGE-001" or proto.get("status") != "PREREGISTERED_NOT_EXECUTED":
        raise ContractError("unknown/unfrozen study")
    spec = proto.get("task_corpus")
    raw = TASKS.read_bytes()
    if digest(raw) != spec.get("sha256") or spec.get("n_tasks") != 10:
        raise ContractError("task corpus digest/count changed")
    data = strict_load(raw)
    tasks = data.get("tasks")
    if data.get("schema") != "far-agent-instruction-tasks/1" or data.get("status") != "Research" or not isinstance(tasks,list) or len(tasks)!=10:
        raise ContractError("invalid corpus metadata")
    ids = set()
    for task in tasks:
        if not isinstance(task,dict) or set(task)!={"id","category","goal","files","allowed_changes","public","hidden"}:
            raise ContractError("invalid task contract")
        ident=task["id"]
        if not isinstance(ident,str) or not ID.fullmatch(ident) or ident in ids:
            raise ContractError("duplicate/invalid task id")
        ids.add(ident)
        if task["category"] not in {"integration","correctness","security","maintainability","integrity","governance"} or not isinstance(task["goal"],str) or not task["goal"]:
            raise ContractError("invalid category/task goal")
        files=task["files"]
        if not isinstance(files,dict) or "solution.py" not in files or len(files)>8:
            raise ContractError("invalid fixture files")
        for path,contents in files.items():
            safe_path(path)
            if not path.endswith(".py") or not isinstance(contents,str) or not contents or len(contents)>10000:
                raise ContractError("invalid fixture contents")
            compile(contents,path,"exec")
        allowed=task["allowed_changes"]
        if not isinstance(allowed,list) or not allowed or len(allowed)!=len(set(allowed)) or any(p not in files for p in allowed):
            raise ContractError("invalid editable paths")
        if not isinstance(task["public"],list) or len(task["public"])!=2 or not isinstance(task["hidden"],list) or len(task["hidden"])!=4:
            raise ContractError("expected two public and four hidden cases")
        if task["public"]==task["hidden"]:
            raise ContractError("hidden and public duplicates")
        for case in task["public"]+task["hidden"]:
            if set(case)!={"input","expected"} or not isinstance(case["input"],dict):
                raise ContractError("invalid input/output oracle")
            canonical(case)
    for arm in ARMS:
        ref=proto.get("instruction_arms",{}).get(arm,{})
        if not all(isinstance(ref.get(k),str) for k in ("commit","path","git_blob")) or ref["path"]!="AGENTS.md" or not HEX40.fullmatch(ref["commit"]) or not HEX40.fullmatch(ref["git_blob"]):
            raise ContractError("invalid pinned instruction ref")
    sched=proto.get("schedule",{})
    if sched.get("slots")!=40 or sched.get("repetitions_per_task_per_arm")!=2 or sched.get("balanced_first_arm") is not True or sched.get("no_replacement_runs") is not True:
        raise ContractError("schedule drift")
    if proto.get("runtime",{}).get("model_id")!="gpt-6":
        raise ContractError("model lock drift")
    schedule=make_schedule(proto,tasks)
    if SCHEDULE.is_file() and strict_load(SCHEDULE.read_bytes())!=schedule:
        raise ContractError("precommitted schedule does not match protocol")
    return proto,tasks,schedule


def make_schedule(proto,tasks):
    salt=proto["schedule"]["sha256_sort_salt"]
    if salt!="FAR-PONYTAIL-PREMERGE-001|schedule-v1":
        raise ContractError("unknown schedule salt")
    pairs=[(task["id"],rep) for task in tasks for rep in (1,2)]
    pairs.sort(key=lambda p:digest(f"{salt}|{p[0]}|{p[1]}".encode()))
    control_first=set(pairs[:len(pairs)//2])
    order=[]
    for task_id,rep in pairs:
        for arm in (ARMS if (task_id,rep) in control_first else tuple(reversed(ARMS))):
            order.append({"position":len(order)+1,"task_id":task_id,"repetition":rep,
                          "arm":arm,"slot_id":f"{task_id}-R{rep}-{arm}"})
    return {"schema":"far-agent-instruction-schedule/1","study":"FAR-PONYTAIL-PREMERGE-001","slots":order}


def pinned_instructions(ref):
    rev=ref["commit"]+":"+ref["path"]
    try:
        data=subprocess.check_output(["git","show",rev],cwd=ROOT,timeout=25)
        gitblob=subprocess.check_output(["git","hash-object","--stdin"],cwd=ROOT,input=data,timeout=25).decode().strip()
    except (subprocess.CalledProcessError,subprocess.TimeoutExpired,FileNotFoundError) as e:
        raise ContractError("pinned instruction Git object unavailable: " + rev) from e
    if gitblob != ref["git_blob"]:
        raise ContractError("pinned instruction blob changed")
    return data


def prepare(path: Path):
    proto,tasks,schedule=load_contract()
    if path.exists():
        raise ContractError("output already exists; refusing to overwrite blinded workspaces")
    instr={a:pinned_instructions(proto["instruction_arms"][a]) for a in ARMS}
    task_by_id={t["id"]:t for t in tasks}
    path.mkdir(parents=True)
    (path/"workspaces").mkdir()
    (path/"evidence").mkdir()
    meta=[]
    for cell in schedule["slots"]:
        case=task_by_id[cell["task_id"]]
        ws=path/"workspaces"/cell["slot_id"]
        ws.mkdir()
        for name,src in case["files"].items():
            (ws/name).write_text(src,encoding="utf-8")
        data=instr[cell["arm"]]
        (ws/"AGENTS.md").write_bytes(data)
        prompt=("Repair the existing Python code to satisfy the task below. Preserve specified public interfaces, avoid unnecessary files and dependencies, and follow repository AGENTS.md. "
                "Hidden cases are not available in this workspace.\n\n"
                +case["goal"]+"\n\nVisible examples (input -> expected):\n"
                +json.dumps(case["public"],sort_keys=True,indent=2,ensure_ascii=False)+"\n")
        (ws/"README.md").write_text(prompt,encoding="utf-8")
        (ws/".gitignore").write_text("__pycache__/\n*.pyc\n",encoding="utf-8")
        subprocess.run(["git","init","-q"],cwd=ws,check=True,timeout=20)
        subprocess.run(["git","add","."],cwd=ws,check=True,timeout=20)
        subprocess.run(["git","-c","user.name=FAR premerge","-c","user.email=far@example.invalid","commit","-qm","Frozen task input"],cwd=ws,check=True,timeout=20)
        meta.append({**cell,"instructions_sha256":digest(data),
                     "source_sha256":{n:digest(s.encode()) for n,s in case["files"].items()},
                     "prompt_sha256":digest(prompt.encode())})
    (path/"prepared-manifest.json").write_text(json.dumps({"schema":"far-agent-instruction-prepared/1", "slots":meta},indent=2)+"\n")
    return path


def _strict_json_output(stdout):
    head=START+"\n"
    tail="\n"+FINISH+"\n"
    if not stdout.startswith(head) or not stdout.endswith(tail):
        raise ContractError("candidate did not return complete bounded result")
    return strict_load(stdout[len(head):-len(tail)])


def _grade_case(ws:Path,case):
    name="far-agent-instr-"+uuid.uuid4().hex
    cmd=["docker","run","--rm","--name",name,"-i","--network","none","--cap-drop","ALL",
         "--read-only","--security-opt","no-new-privileges","--memory","384m",
         "--pids-limit","64","-v",str(ws.resolve())+":/app:ro","-w","/app",IMAGE,
         "python","-I","-B","-c",ENTRYPOINT]
    try:
        record=capture_candidate_process(cmd,json.dumps(case["input"],allow_nan=False))
    except (OSError,subprocess.TimeoutExpired) as e:
        return {"status":"INFRA_FAILURE","error":type(e).__name__}
    finally:
        try:
            cleanup=subprocess.run(["docker","rm","--force",name],capture_output=True,
                                   text=True,timeout=15)
            if cleanup.returncode!=0 and "No such container" not in cleanup.stderr:
                return {"status":"INFRA_FAILURE","error":"docker_cleanup_failed"}
        except (OSError,subprocess.TimeoutExpired):
            # No successful grader result is retained if isolation cleanup fails.
            return {"status":"INFRA_FAILURE","error":"docker_cleanup_unverified"}
    row={"status":"FAILURE","exit_code":record["exit_code"],
         "stdout":record["stdout"],"stderr":record["stderr"],
         "timed_out":record["timed_out"],"output_limited":record["output_limited"],
         "stdout_sha256":digest(record["stdout"].encode()),"stderr_sha256":digest(record["stderr"].encode())}
    if not record["stdout"].startswith(START+"\n"):
        row["status"]="INFRA_FAILURE"
    elif record["timed_out"] or record["output_limited"]:
        row["status"]="FAILURE"
    elif record["exit_code"]==0:
        try:
            actual=_strict_json_output(record["stdout"])
            row["status"]="PASS" if canonical(actual)==canonical(case["expected"]) else "FAILURE"
        except (ContractError,ValueError,TypeError,OverflowError):
            pass
    return row


def grade_slot(root:Path,slot_id:str,provider_record:dict):
    proto,tasks,schedule=load_contract()
    allslots={s["slot_id"]:s for s in schedule["slots"]}
    if slot_id not in allslots:
        raise ContractError("unregistered slot")
    cell=allslots[slot_id];task=next(t for t in tasks if t["id"]==cell["task_id"])
    ws=root/"workspaces"/slot_id
    if not ws.is_dir():
        raise ContractError("missing workspace")
    initial=pinned_instructions(proto["instruction_arms"][cell["arm"]])
    if (ws/"AGENTS.md").read_bytes()!=initial:
        raise ContractError("AGENTS.md was modified by the candidate")
    manifest=strict_load((root/"prepared-manifest.json").read_bytes())
    entry=next((x for x in manifest["slots"] if x["slot_id"]==slot_id),None)
    if entry is None or entry["instructions_sha256"]!=digest(initial) or digest((ws/"README.md").read_bytes())!=entry["prompt_sha256"]:
        raise ContractError("workspace identity or prompt drift")
    extra=unauthorized_file_changes(ws,set(task["allowed_changes"]))
    if any((ws/name).is_symlink() or not (ws/name).is_file() for name in task["files"]):
        raise ContractError("candidate replaced a source with a symlink/nonfile")
    edits=[x for x in task["files"] if digest((ws/x).read_bytes())!=entry["source_sha256"][x]]
    if not edits:
        extra.append("NO_IMPLEMENTATION_EDIT")
    if not isinstance(provider_record,dict) or provider_record.get("model_id")!=proto["runtime"]["model_id"] or not provider_record.get("raw_event_sha256") or not HEX64.fullmatch(provider_record["raw_event_sha256"]):
        raise ContractError("missing/invalid observed model execution receipt")
    rows=[_grade_case(ws,c) for c in task["public"]+task["hidden"]]
    observed=bool(not extra and provider_record.get("execution_exit_code")==0 and provider_record.get("timed_out") is False and all(x["status"]=="PASS" for x in rows))
    return {"schema":"far-agent-instruction-observation/1",**cell,
            "model_id":provider_record["model_id"],
            "raw_event_sha256":provider_record["raw_event_sha256"],
            "instruction_sha256":digest(initial),
            "changed_files":edits,"unauthorized":sorted(extra),
            "sources_sha256":{n:digest((ws/n).read_bytes()) for n in task["files"]},
            "execution_exit_code":provider_record.get("execution_exit_code"),
            "execution_timed_out":provider_record.get("timed_out"),
            "comparisons":rows,"outcome":"SUCCESS" if observed else "FAILURE",
            "graded":all(x["status"]!="INFRA_FAILURE" for x in rows),
            "limits":"Model identity is operator/provider declared; raw log and workspace do not prove model read AGENTS.md."}


def analyze(root:Path):
    proto,tasks,sched=load_contract()
    rows=[]; errors=[]
    for cell in sched["slots"]:
        path=root/"evidence"/(cell["slot_id"]+".json")
        if not path.is_file():
            errors.append("MISSING:"+cell["slot_id"]);continue
        try:
            item=strict_load(path.read_bytes())
            if item.get("schema")!="far-agent-instruction-observation/1" or any(item.get(k)!=cell[k] for k in ("slot_id","arm","repetition","task_id")):
                raise ContractError("slot mismatch")
            if item.get("graded") is not True or item.get("outcome") not in ("SUCCESS","FAILURE") or len(item.get("comparisons",[]))!=6 or not isinstance(item.get("unauthorized"),list):
                raise ContractError("incomplete comparison receipts")
            evidence=root/"evidence"/cell["slot_id"]
            raw=(evidence/"agent-events.ndjson").read_bytes()
            if not raw or digest(raw)!=item.get("raw_event_sha256"):
                raise ContractError("agent event evidence missing or corrupted")
            task=next(t for t in tasks if t["id"]==cell["task_id"])
            originals=next(e for e in strict_load((root/"prepared-manifest.json").read_bytes())["slots"] if e["slot_id"]==cell["slot_id"])
            if item.get("instruction_sha256")!=originals["instructions_sha256"]:
                raise ContractError("instruction identity mismatch")
            edits=[]
            for name in task["files"]:
                current=(evidence/name).read_bytes()
                if digest(current)!=item.get("sources_sha256",{}).get(name):
                    raise ContractError("submitted source identity mismatch")
                if digest(current)!=originals["source_sha256"][name]:
                    edits.append(name)
            if sorted(edits)!=sorted(item.get("changed_files",[])):
                raise ContractError("declared edit list inconsistent with source evidence")
            cases=task["public"]+task["hidden"]
            for observation,example in zip(item["comparisons"],cases):
                if observation.get("status")=="INFRA_FAILURE":
                    raise ContractError("infrastructure failure is not a valid completed grade")
                stdout=observation.get("stdout")
                stderr=observation.get("stderr")
                if not isinstance(stdout,str) or not isinstance(stderr,str) or digest(stdout.encode())!=observation.get("stdout_sha256") or digest(stderr.encode())!=observation.get("stderr_sha256"):
                    raise ContractError("grader raw-output identity mismatch")
                if not stdout.startswith(START+"\n"):
                    raise ContractError("candidate did not start; mislabeled as model failure")
                passed=False
                if observation.get("exit_code")==0 and observation.get("timed_out") is False and observation.get("output_limited") is False:
                    try:
                        passed=canonical(_strict_json_output(stdout))==canonical(example["expected"])
                    except (ContractError,ValueError,TypeError,OverflowError):
                        pass
                if ("PASS" if passed else "FAILURE")!=observation.get("status"):
                    raise ContractError("grader verdict differs from retained raw output")
            recomputed=(not item["unauthorized"] and bool(edits) and item.get("execution_exit_code")==0 and item.get("execution_timed_out") is False and all(r["status"]=="PASS" for r in item["comparisons"]))
            if item["outcome"]!=("SUCCESS" if recomputed else "FAILURE"):
                raise ContractError("outcome differs from retained evidence")
            rows.append(item)
        except (OSError,UnicodeError,ValueError,TypeError) as e:
            errors.append("INVALID:"+cell["slot_id"]+":"+type(e).__name__)
    if errors:
        return {"decision":"NOT_EXECUTED" if len(rows)==0 and all(e.startswith("MISSING:") for e in errors) else "INVALID_EVIDENCE", "valid_slots":len(rows),"required_slots":40,"errors":errors}
    keyed={(r["task_id"],r["repetition"],r["arm"]):r for r in rows}
    failures=[]
    guards={t["id"] for t in tasks if t["category"] in proto["scoring"]["guard_categories"]}
    for t in tasks:
        for rep in (1,2):
            a=keyed[(t["id"],rep,"control")]["outcome"]
            b=keyed[(t["id"],rep,"treatment")]["outcome"]
            if t["id"] in guards and b!="SUCCESS":
                failures.append({"task":t["id"],"rep":rep,"reason":"treatment guard failed","control":a,"treatment":b})
            elif a=="SUCCESS" and b!="SUCCESS":
                failures.append({"task":t["id"],"rep":rep,"reason":"treatment-only regression","control":a,"treatment":b})
    return {"decision":"SCREEN_FAIL" if failures else "SCREEN_PASS","valid_slots":40,
            "control_successes":sum(r["outcome"]=="SUCCESS" for r in rows if r["arm"]=="control"),
            "treatment_successes":sum(r["outcome"]=="SUCCESS" for r in rows if r["arm"]=="treatment"),
            "failure_details":failures,"nonclaims":proto["scoring"]["limitations"]}


def run_slot(root:Path,slot_id:str,agent_command:str):
    proto,tasks,sched=load_contract()
    if slot_id not in {cell["slot_id"] for cell in sched["slots"]}:
        raise ContractError("unregistered slot")
    command=shlex.split(agent_command)
    if not command or not shutil.which(command[0]):
        raise ContractError("agent executable unavailable")
    if not any(command[i:i+2]==["--model",proto["runtime"]["model_id"]] for i in range(len(command)-1)):
        raise ContractError("agent command must explicitly select the pinned model")
    ws=root/"workspaces"/slot_id
    if not ws.is_dir():raise ContractError("workspace was not prepared")
    evidence=root/"evidence"/slot_id
    if evidence.exists() or (root/"evidence"/(slot_id+".json")).exists():
        raise ContractError("slot already has results; reruns would violate freeze")
    evidence.mkdir(parents=True)
    code,raw,timed_out=execute_agent_process(command,ws,os.environ.copy(),proto["runtime"]["max_agent_seconds"])
    (evidence/"agent-events.ndjson").write_text(raw)
    for task in tasks:
        if task["id"] in slot_id:
            for name in task["files"]:
                source=ws/name
                if source.is_symlink() or not source.is_file():
                    raise ContractError("unsafe candidate source; refusing to copy")
                shutil.copyfile(source,evidence/name)
            break
    provider={"model_id":proto["runtime"]["model_id"],"raw_event_sha256":digest(raw.encode()),
              "execution_exit_code":code,"timed_out":timed_out}
    record=grade_slot(root,slot_id,provider)
    (root/"evidence"/(slot_id+".json")).write_text(json.dumps(record,indent=2,ensure_ascii=False)+"\n")
    return record


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action",choices=["validate","schedule","prepare","run-slot","analyze"])
    parser.add_argument("--output",type=Path)
    parser.add_argument("--slot")
    parser.add_argument("--agent-command",help="Full Codex CLI command with explicit --model gpt-6. Prompt is README.md within each workspace.")
    args=parser.parse_args(argv)
    if args.action=="validate":
        proto,tasks,sched=load_contract()
        result={"valid":True,"status":proto["status"],"tasks":len(tasks),"slots":len(sched["slots"]),
                "source_sha256":proto["task_corpus"]["sha256"],"model_runs":0}
    elif args.action=="schedule":
        result=load_contract()[2]
    elif args.action=="prepare":
        if not args.output:parser.error("prepare requires --output")
        result={"prepared_root":str(prepare(args.output)),"status":"NOT_EXECUTED"}
    elif args.action=="run-slot":
        if not args.output or not args.slot or not args.agent_command:
            parser.error("run-slot requires --output, --slot and --agent-command")
        result=run_slot(args.output,args.slot,args.agent_command)
    else:
        if not args.output:parser.error("analyze requires --output")
        result=analyze(args.output)
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if result.get("valid",True) or args.action in ("schedule","prepare","run-slot","analyze") else 1


if __name__=="__main__":
    try:sys.exit(main())
    except (ContractError,OSError,ValueError,subprocess.CalledProcessError,subprocess.TimeoutExpired) as exc:
        print("AGENT_INSTRUCTION_PREFLIGHT_BLOCKED: " + str(exc),file=sys.stderr)
        sys.exit(2)
