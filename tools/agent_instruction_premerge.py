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
import selectors
import signal
import time
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid

# Support both `python -m tools.agent_instruction_premerge` and direct-script usage.
REPO_PARENT = str(Path(__file__).resolve().parents[1])
if REPO_PARENT not in sys.path:
    sys.path.insert(0, REPO_PARENT)

from tools.workflow_efficacy_free_agent import (
    capture_candidate_process, GRADER_IMAGE,
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
# Candidate source runs in Docker, but also shares a Python interpreter with
# the scoring wrapper. A module-global copy of the input can be rebound by
# sys._getframe(1).f_globals in candidate code, falsely certifying no mutation.
# Use a call-local baseline, reject known frame/native introspection paths, and
# keep the same input/output protocol for all three entrypoint variants.
# Python audit hooks are defense in depth, not isolation from hostile C code.
OBSERVER_SETUP = (
    "import copy,json,runpy,sys\n"
    "sys.path.insert(0,'/app')\n"
    "d=json.load(sys.stdin)\n"
    "def _deny_grader_introspection(event,args):\n"
    "    if event in ('sys._getframe','sys._current_frames','gc.get_objects',"
    "'gc.get_referrers','gc.get_referents','sys.settrace','sys.setprofile') "
    "or event.startswith('ctypes.'):\n"
    "        raise RuntimeError('candidate attempted grader introspection')\n"
    "sys.addaudithook(_deny_grader_introspection)\n"
    "def _checked(call,payload):\n"
    "    before=copy.deepcopy(payload)\n"
    "    answer=call(payload)\n"
    "    return answer,payload==before\n"
    "sys.stdout.write('" + START + "\\n');sys.stdout.flush()\n"
)
OBSERVER_EMIT = (
    "sys.stdout.write(json.dumps({'value':answer,'input_unchanged':input_unchanged},"
    "sort_keys=True,allow_nan=False,separators=(',',':')))\n"
    "sys.stdout.write('\\n" + FINISH + "\\n');sys.stdout.flush()\n"
)
ENTRYPOINT = (
    OBSERVER_SETUP
    + "candidate=runpy.run_path('/app/solution.py')\n"
    + "answer,input_unchanged=_checked(candidate['transform'],d)\n"
    + OBSERVER_EMIT
)

# The two extra integration/maintainability probes use the same call-local
# mutation observer as the primary adapter. No candidate can provide the
# comparison flag directly, and frame-introspection attempts fail closed.
INTERFACE_CALLERS = (
    OBSERVER_SETUP
    + "def _call(payload):\n"
    + "    from normalize import canonical,legacy\n"
    + "    return {'service':canonical(payload['name']),'legacy':legacy(payload['name'])}\n"
    + "answer,input_unchanged=_checked(_call,d)\n"
    + OBSERVER_EMIT
)
INTERFACE_REUSE = (
    OBSERVER_SETUP
    + "def _call(payload):\n"
    + "    import shared\n"
    + "    calls=[]\n"
    + "    def spy(value):\n"
    + "        calls.append(value)\n"
    + "        return 'FAR_HELPER_USED_V1'\n"
    + "    shared.slugify=spy\n"
    + "    from catalog import slugs\n"
    + "    return {'result':slugs(payload['items']),'calls':calls}\n"
    + "answer,input_unchanged=_checked(_call,d)\n"
    + OBSERVER_EMIT
)
INTERFACE_ENTRYPOINTS = {'CALLERS-01': INTERFACE_CALLERS,
                         'REUSE-06': INTERFACE_REUSE}

def _interface_probes(task:dict) -> list[tuple[dict,str]]:
    """Use the existing six frozen inputs to check declared public interfaces."""
    cases = task['public'] + task['hidden']
    if task['id'] == 'CALLERS-01':
        return [(case, INTERFACE_CALLERS) for case in cases]
    if task['id'] == 'REUSE-06':
        return [({'input':case['input'],
                  'expected':{'result':['FAR_HELPER_USED_V1'] * len(case['input']['items']),
                              'calls':case['input']['items']}}, INTERFACE_REUSE)
                for case in cases]
    return []


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
    if not SCHEDULE.is_file() or strict_load(SCHEDULE.read_bytes())!=schedule:
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


def freeze_identity():
    """Pin the actual candidate source and all controlling input bytes per campaign."""
    return {"protocol_sha256":digest(PROTOCOL.read_bytes()),
            "tasks_sha256":digest(TASKS.read_bytes()),
            "schedule_sha256":digest(SCHEDULE.read_bytes()),
            "runner_sha256":digest(Path(__file__).read_bytes()),
            "grader_helper_sha256":digest((ROOT/'tools/workflow_efficacy_free_agent.py').read_bytes())}


def validate_prepared(root:Path):
    manifest=strict_load((root/'prepared-manifest.json').read_bytes())
    if manifest.get('schema')!='far-agent-instruction-prepared/2' or manifest.get('freeze')!=freeze_identity():
        raise ContractError('prepared campaign freeze differs from scoring source')
    _,tasks,sched=load_contract()
    if manifest.get('schedule_sha256')!=digest(canonical(sched)):
        raise ContractError('prepared schedule drift')
    expected=sched['slots']
    if not isinstance(manifest.get('slots'),list) or len(manifest['slots'])!=len(expected):
        raise ContractError('incomplete prepared slot inventory')
    for i,(m,s) in enumerate(zip(manifest['slots'],expected)):
        if any(m.get(k)!=s[k] for k in s):
            raise ContractError(f'prepared slot {i} reordered or edited')
    return manifest


def prepare(path:Path):
    proto,tasks,schedule=load_contract()
    if path.exists():
        raise ContractError('output already exists; refusing to overwrite frozen campaign')
    instr={a:pinned_instructions(proto['instruction_arms'][a]) for a in ARMS}
    # Check all input references and helper source before creating outputs.
    freeze=freeze_identity()
    task_by_id={t['id']:t for t in tasks}
    path.mkdir(parents=True)
    (path/'workspaces').mkdir()
    (path/'evidence').mkdir()
    entries=[]
    for cell in schedule['slots']:
        task=task_by_id[cell['task_id']]
        ws=path/'workspaces'/cell['slot_id']
        ws.mkdir()
        for name,src in task['files'].items():
            (ws/name).write_text(src,encoding='utf-8')
        (ws/'AGENTS.md').write_bytes(instr[cell['arm']])
        prompt=('Repair the existing Python code to satisfy the task below. Preserve specified public interfaces, avoid unnecessary files and dependencies, and follow repository AGENTS.md. '
                'Hidden cases are not available in this workspace.\n\n'
                +task['goal']+'\n\nVisible examples (input -> expected):\n'
                +json.dumps(task['public'],sort_keys=True,indent=2,ensure_ascii=False)+'\n')
        (ws/'README.md').write_text(prompt,encoding='utf-8')
        (ws/'.gitignore').write_text('__pycache__/\n*.pyc\n',encoding='utf-8')
        subprocess.run(['git','init','-q'],cwd=ws,check=True,timeout=20)
        subprocess.run(['git','add','.'],cwd=ws,check=True,timeout=20)
        subprocess.run(['git','-c','user.name=FAR premerge','-c','user.email=far@example.invalid',
                        'commit','-qm','Frozen task input'],cwd=ws,check=True,timeout=20)
        file_hashes={name:digest((ws/name).read_bytes()) for name in [*task['files'],'AGENTS.md','README.md','.gitignore']}
        entries.append({**cell,'initial_files_sha256':file_hashes,
                        'source_sha256':{name:file_hashes[name] for name in task['files']},
                        'instructions_sha256':file_hashes['AGENTS.md'],
                        'prompt_sha256':file_hashes['README.md']})
    manifest={'schema':'far-agent-instruction-prepared/2','freeze':freeze,
              'schedule_sha256':digest(canonical(schedule)),'slots':entries}
    (path/'prepared-manifest.json').write_bytes(canonical(manifest))
    return path


def _strict_json_output(stdout):
    head=START+'\n'; tail='\n'+FINISH+'\n'
    if not stdout.startswith(head) or not stdout.endswith(tail):
        raise ContractError('candidate did not return complete bounded result')
    body=strict_load(stdout[len(head):-len(tail)])
    if not isinstance(body,dict) or set(body)!={'value','input_unchanged'} or type(body['input_unchanged']) is not bool:
        raise ContractError('candidate output missing independent mutation observation')
    return body


def _grade_case(snapshot:Path,case:dict,entrypoint:str=ENTRYPOINT):
    name='far-agent-instr-'+uuid.uuid4().hex
    cmd=['docker','run','--rm','--name',name,'-i','--network','none','--cap-drop','ALL',
         '--read-only','--security-opt','no-new-privileges','--memory','384m',
         '--pids-limit','64','-v',str(snapshot.resolve())+':/app:ro','-w','/app',IMAGE,
         'python','-I','-B','-c',entrypoint]
    result=None; transport_error=None
    try:
        result=capture_candidate_process(cmd,json.dumps(case['input'],allow_nan=False))
    except (OSError,subprocess.TimeoutExpired) as e:
        transport_error=type(e).__name__
    cleanup_error=None
    try:
        cleanup=subprocess.run(['docker','rm','--force',name],capture_output=True,text=True,timeout=15)
        if cleanup.returncode!=0 and 'No such container' not in cleanup.stderr:
            cleanup_error='docker_cleanup_failed:'+cleanup.stderr[:2000]
    except (OSError,subprocess.TimeoutExpired) as e:
        cleanup_error='docker_cleanup_unverified:'+type(e).__name__
    if result is None:
        return {'status':'INFRA_FAILURE','error':transport_error or 'transport_missing',
                'cleanup_error':cleanup_error}
    row={'status':'FAILURE','exit_code':result['exit_code'],'stdout':result['stdout'],
         'stderr':result['stderr'],'timed_out':result['timed_out'],
         'output_limited':result['output_limited'],
         'stdout_sha256':digest(result['stdout'].encode()),
         'stderr_sha256':digest(result['stderr'].encode()),
         'stdout_bytes_observed':result.get('stdout_bytes_observed'),
         'stderr_bytes_observed':result.get('stderr_bytes_observed'),
         'cleanup_error':cleanup_error}
    if cleanup_error or not result['stdout'].startswith(START+'\n'):
        row['status']='INFRA_FAILURE'
    elif result['timed_out'] or result['output_limited']:
        row['status']='FAILURE'
    elif result['exit_code']==0:
        try:
            output=_strict_json_output(result['stdout'])
            row['status']='PASS' if (output['input_unchanged'] and
                                    canonical(output['value'])==canonical(case['expected'])) else 'FAILURE'
        except (ContractError,ValueError,TypeError,OverflowError):
            pass
    return row


def _classify_sources(actual:dict,expected:dict,allowed:set):
    violations=[]
    for rel in sorted(set(actual)|set(expected)):
        if rel not in expected:
            violations.append('NEW_FILE:'+rel)
        elif rel not in actual:
            violations.append('MISSING_FILE:'+rel)
        elif digest(actual[rel])!=expected[rel] and rel not in allowed:
            violations.append('UNAUTHORIZED_EDIT:'+rel)
    edits=sorted(rel for rel in allowed if rel in expected and rel in actual
                 and digest(actual[rel])!=expected[rel])
    if not edits:violations.append('NO_IMPLEMENTATION_EDIT')
    return sorted(violations),edits


def _workspace_snapshot(ws:Path,entry:dict,task:dict):
    """Compare every retained file against trusted bytes, never against candidate Git HEAD."""
    actual={};unsafe=[]
    for folder,dirs,files in os.walk(ws,followlinks=False):
        relroot=Path(folder).relative_to(ws)
        dirs[:]=[d for d in dirs if not (str(relroot)=='.' and d=='.git')]
        for dirname in dirs:
            path=Path(folder)/dirname
            if path.is_symlink():unsafe.append('SYMLINK_DIRECTORY:'+path.relative_to(ws).as_posix())
        for filename in files:
            path=Path(folder)/filename
            rel=path.relative_to(ws).as_posix()
            if path.is_symlink() or not path.is_file():
                unsafe.append('UNSAFE_FILE:'+rel);continue
            if path.stat().st_size>200_000:
                unsafe.append('OVERSIZED_FILE:'+rel);continue
            actual[rel]=path.read_bytes()
    violations,edits=_classify_sources(actual,entry['initial_files_sha256'],
                                      set(task['allowed_changes']))
    return actual,sorted(set(violations+unsafe)),edits


def _parse_agent_trace(raw:bytes):
    """Validate documented Codex exec JSONL lifecycle, not arbitrary log hashes."""
    if not raw or len(raw)>2_000_000 or not raw.endswith(b'\n'):
        raise ContractError('incomplete or oversized Codex trace')
    lines=raw.splitlines()
    if len(lines)>20000:raise ContractError('oversized Codex event stream')
    events=[strict_load(x) for x in lines]
    if not all(isinstance(e,dict) and isinstance(e.get('type'),str) for e in events):
        raise ContractError('invalid Codex event JSON')
    if len(events)<3 or events[0].get('type')!='thread.started' or not isinstance(events[0].get('thread_id'),str) or not events[0]['thread_id']:
        raise ContractError('missing Codex thread identity')
    types=[e['type'] for e in events]
    if types.count('thread.started')!=1 or types.count('turn.started')!=1 or types.count('turn.completed')!=1 or types[-1]!='turn.completed' or any(x in types for x in ('turn.failed','error')):
        raise ContractError('Codex stream has missing, duplicated or failed lifecycle')
    usage=events[-1].get('usage')
    if not isinstance(usage,dict) or any(type(usage.get(k)) is not int or usage[k]<0 for k in ('input_tokens','output_tokens')):
        raise ContractError('Codex completion missing token usage')
    if usage['input_tokens']==0 or usage['output_tokens']==0:
        raise ContractError('Codex completion did not report model usage')
    return {'thread_id':events[0]['thread_id'],'input_tokens':usage['input_tokens'],
            'output_tokens':usage['output_tokens'],'events':len(events)}


def _command_identity(command:list[str],model_id:str):
    """Accept only a fixed Codex runner contract; do not execute arbitrary wrappers."""
    expect=['codex','exec','--json','--model',model_id,'--sandbox','workspace-write',
            '--ephemeral','--ignore-user-config','--ignore-rules',
            'Read README.md and AGENTS.md, then make the code changes needed to satisfy the task.']
    if command!=expect:
        raise ContractError('agent invocation differs from pinned Codex execution contract')
    exe=shutil.which('codex')
    if not exe:raise ContractError('Codex executable unavailable')
    real=Path(exe).resolve()
    if not real.is_file() or real.stat().st_size>300_000_000:
        raise ContractError('invalid executable')
    version=subprocess.run([str(real),'--version'],capture_output=True,text=True,timeout=20)
    if version.returncode or not version.stdout.strip().startswith('codex-cli '):
        raise ContractError('cannot identify Codex CLI release')
    return {'schema':'far-codex-runtime/1','executable_path':str(real),
            'executable_sha256':digest(real.read_bytes()),'version':version.stdout.strip(),
            'command':command,'requested_model':model_id,
            'model_identity_basis':'Codex CLI --model argument plus validated event trace; provider-selected backend not cryptographically attested'}


def _execute_traced_agent(command:list[str],ws:Path,env:dict,seconds:int,max_bytes:int):
    """Capture both streams with byte ceilings; reap process-group descendants always."""
    start=time.monotonic(); buff={'stdout':bytearray(),'stderr':bytearray()}; counts={'stdout':0,'stderr':0}
    timed_out=False;output_limited=False; code=None
    # The fixed prompt is the sole task context. Never inherit parent stdin:
    # Codex CLI treats piped bytes as additional, unregistered instructions.
    proc=subprocess.Popen(command,cwd=ws,env=env,stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                          start_new_session=True)
    try:
        with selectors.DefaultSelector() as sel:
            for key in ('stdout','stderr'):
                sel.register(getattr(proc,key),selectors.EVENT_READ,key)
            while sel.get_map():
                remaining=seconds-(time.monotonic()-start)
                if remaining<=0:
                    timed_out=True;break
                events=sel.select(min(remaining,0.2))
                for key,_ in events:
                    chunk=os.read(key.fileobj.fileno(),8192)
                    if not chunk:
                        sel.unregister(key.fileobj);continue
                    dest=key.data;counts[dest]+=len(chunk)
                    if len(buff[dest])<max_bytes:
                        buff[dest].extend(chunk[:max_bytes-len(buff[dest])])
                    if counts[dest]>max_bytes:
                        output_limited=True;break
                if output_limited:break
            if not timed_out and not output_limited:
                try:
                    code=proc.wait(timeout=max(0.001,seconds-(time.monotonic()-start)))
                except subprocess.TimeoutExpired:
                    timed_out=True
    finally:
        # A successfully exited parent can leave a child altering the source.
        # Kill the entire private process group before snapshotting any code.
        try:os.killpg(proc.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        proc.wait(timeout=10)
        for stream in (proc.stdout,proc.stderr):stream.close()
    return {'stdout':bytes(buff['stdout']),'stderr':bytes(buff['stderr']),
            'stdout_bytes_observed':counts['stdout'],
            'stderr_bytes_observed':counts['stderr'],
            'output_limited':output_limited,'timed_out':timed_out,
            'exit_code':code,'elapsed_seconds':time.monotonic()-start}


def _record_path(root:Path,slot_id:str):
    return root/'evidence'/(slot_id+'.json')


def grade_slot(root:Path,slot_id:str,provider_record:dict):
    proto,tasks,sched=load_contract()
    manifest=validate_prepared(root)
    cells={s['slot_id']:s for s in sched['slots']}
    if slot_id not in cells:raise ContractError('unregistered slot')
    cell=cells[slot_id];task=next(t for t in tasks if t['id']==cell['task_id'])
    entry=manifest['slots'][cell['position']-1]
    ws=root/'workspaces'/slot_id
    if not ws.is_dir():raise ContractError('missing candidate workspace')
    original=pinned_instructions(proto['instruction_arms'][cell['arm']])
    if digest(original)!=entry['instructions_sha256']:
        raise ContractError('workspace instruction baseline inconsistent with Git')
    source,unauthorized,edits=_workspace_snapshot(ws,entry,task)
    evidence=root/'evidence'/slot_id
    submitted=evidence/'submitted'
    submitted.mkdir(exist_ok=False)
    for name,contents in source.items():
        (submitted/name).parent.mkdir(parents=True,exist_ok=True)
        (submitted/name).write_bytes(contents)
    complete=all(n in source for n in task['files'])
    probes=_interface_probes(task)
    if complete:
        results=[_grade_case(submitted,c) for c in task['public']+task['hidden']]
        interface_checks=[_grade_case(submitted,c,entrypoint=script) for c,script in probes]
    else:
        results=[{'status':'INFRA_FAILURE','error':'source_missing_or_unsafe'} for _ in range(6)]
        interface_checks=[{'status':'INFRA_FAILURE','error':'source_missing_or_unsafe'} for _ in probes]
    trace=provider_record.get('validated_trace')
    valid=bool(complete and not unauthorized and provider_record.get('exit_code')==0 and
               provider_record.get('timed_out') is False and provider_record.get('output_limited') is False and
               isinstance(trace,dict) and len(results)==6 and
               all(row['status']=='PASS' for row in results+interface_checks))
    return {'schema':'far-agent-instruction-observation/2',**cell,
            'freeze':manifest['freeze'],'previous_observation_sha256':provider_record.get('previous_observation_sha256'),
            'model_id':proto['runtime']['model_id'],
            'runtime':provider_record['runtime'],'trace':trace,
            'stdout_sha256':provider_record['stdout_sha256'],
            'stderr_sha256':provider_record['stderr_sha256'],
            'stdout_bytes_observed':provider_record['stdout_bytes_observed'],
            'stderr_bytes_observed':provider_record['stderr_bytes_observed'],
            'exit_code':provider_record['exit_code'],
            'timed_out':provider_record['timed_out'],
            'output_limited':provider_record['output_limited'],
            'source_sha256':{n:digest(data) for n,data in source.items()},
            'changed_files':edits,'unauthorized':unauthorized,
            'comparisons':results,'interface_checks':interface_checks,
            'outcome':'SUCCESS' if valid else 'FAILURE',
            'graded':all(x['status']!='INFRA_FAILURE' for x in results+interface_checks),
            'limitations':'Trusted host/executable attestations and Codex stream parsing are not cryptographic proof of provider-side model selection or instruction ingestion.'}


def analyze(root:Path):
    proto,tasks,sched=load_contract()
    try:manifest=validate_prepared(root)
    except (OSError,ValueError) as e:
        if not root.exists() or not any(root.iterdir()):
            return {'decision':'NOT_EXECUTED','valid_slots':0,'required_slots':40,
                    'errors':['NO_PREPARED_CAMPAIGN']}
        return {'decision':'INVALID_EVIDENCE','valid_slots':0,'required_slots':40,
                'errors':['PREPARED_FREEZE_INVALID:'+type(e).__name__]}
    rows=[];errors=[];previous=None
    for cell in sched['slots']:
        sid=cell['slot_id'];path=_record_path(root,sid)
        if not path.is_file():
            if (root/'evidence'/sid).exists() or (root/'evidence'/(sid+'.attempt.json')).exists():
                errors.append('ATTEMPTED_BUT_INCOMPLETE:'+sid)
            else:errors.append('MISSING:'+sid)
            continue
        try:
            record=strict_load(path.read_bytes())
            if record.get('schema')!='far-agent-instruction-observation/2' or record.get('freeze')!=manifest['freeze']:
                raise ContractError('wrong observation schema or campaign freeze')
            if any(record.get(k)!=cell[k] for k in cell):
                raise ContractError('slot mismatch')
            if record.get('previous_observation_sha256')!=previous:
                raise ContractError('actual execution-order chain broken')
            previous=digest(path.read_bytes())
            entry=manifest['slots'][cell['position']-1]
            if record.get('model_id')!=proto['runtime']['model_id']:
                raise ContractError('declared model differs from protocol')
            runtime=record.get('runtime')
            if not isinstance(runtime,dict) or runtime.get('requested_model')!=proto['runtime']['model_id'] or runtime.get('schema')!='far-codex-runtime/1':
                raise ContractError('invalid runtime provenance')
            if runtime.get('command')!=_command_expected(proto['runtime']['model_id']):
                raise ContractError('execution command not the pinned CLI protocol')
            if not isinstance(runtime.get('version'),str) or not runtime['version'].startswith('codex-cli ') or not HEX64.fullmatch(runtime.get('executable_sha256','')):
                raise ContractError('incomplete executable attestation')
            slotdir=root/'evidence'/sid
            if strict_load((slotdir/'runtime.json').read_bytes())!=runtime:
                raise ContractError('retained execution environment differs from observation')
            attempt=strict_load((root/'evidence'/(sid+'.attempt.json')).read_bytes())
            if attempt.get('freeze')!=manifest['freeze'] or attempt.get('slot_id')!=sid or attempt.get('previous_observation_sha256')!=record['previous_observation_sha256'] or attempt.get('runtime')!=runtime:
                raise ContractError('pre-exposure attempt manifest mismatch')
            raw=(slotdir/'agent-events.ndjson').read_bytes();err=(slotdir/'agent-stderr.txt').read_bytes()
            if digest(raw)!=record.get('stdout_sha256') or digest(err)!=record.get('stderr_sha256'):
                raise ContractError('model transcript bytes differ')
            if len(raw)>proto['runtime']['max_agent_output_bytes'] or not record.get('trace') or record.get('output_limited') is not False or record.get('timed_out') is not False:
                raise ContractError('incomplete model trace')
            if _parse_agent_trace(raw)!=record['trace']:
                raise ContractError('model lifecycle not supported by preserved stream')
            if record.get('exit_code')!=0 or record.get('stdout_bytes_observed')!=len(raw) or record.get('stderr_bytes_observed')!=len(err):
                raise ContractError('model runner exit/byte-count mismatch')
            task=next(t for t in tasks if t['id']==cell['task_id'])
            submitted=slotdir/'submitted';stored={}
            if not submitted.is_dir():raise ContractError('missing snapshot directory')
            for file in submitted.rglob('*'):
                if file.is_symlink():raise ContractError('unsafe retained symlink')
                if not file.is_file():continue
                name=file.relative_to(submitted).as_posix()
                if file.stat().st_size>200_000:raise ContractError('oversized retained file')
                stored[name]=file.read_bytes()
            if {n:digest(c) for n,c in stored.items()}!=record.get('source_sha256'):
                raise ContractError('submitted source inventory digest mismatch')
            expected=entry['initial_files_sha256']
            unauthorized,edits=_classify_sources(stored,expected,set(task['allowed_changes']))
            if edits!=record.get('changed_files') or unauthorized!=record.get('unauthorized'):
                raise ContractError('source edits/permission facts not reproduced')
            if not all(n in stored for n in task['files']):
                raise ContractError('missing retained candidate sources')
            if not record.get('graded') or not isinstance(record.get('comparisons'),list) or len(record['comparisons'])!=6:
                raise ContractError('ungraded/absent comparison evidence')
            for item,case in zip(record['comparisons'],task['public']+task['hidden']):
                if item.get('status') not in ('PASS','FAILURE'):
                    raise ContractError('infrastructure error in supposedly completed results')
                stdout=item.get('stdout');stderr=item.get('stderr')
                if not isinstance(stdout,str) or not isinstance(stderr,str) or digest(stdout.encode())!=item.get('stdout_sha256') or digest(stderr.encode())!=item.get('stderr_sha256'):
                    raise ContractError('grader byte-digest mismatch')
                good=False
                if item.get('exit_code')==0 and item.get('timed_out') is False and item.get('output_limited') is False and item.get('cleanup_error') is None:
                    try:
                        parsed=_strict_json_output(stdout)
                        good=parsed['input_unchanged'] and canonical(parsed['value'])==canonical(case['expected'])
                    except (ContractError,ValueError,TypeError,OverflowError):pass
                if item['status']!=('PASS' if good else 'FAILURE'):
                    raise ContractError('grader output and verdict disagree')
            probes=_interface_probes(task)
            interface_checks=record.get('interface_checks')
            if not isinstance(interface_checks,list) or len(interface_checks)!=len(probes):
                raise ContractError('missing required public-interface verification')
            for item,(case,_) in zip(interface_checks,probes):
                if item.get('status') not in ('PASS','FAILURE'):
                    raise ContractError('infrastructure failure in required interface tests')
                stdout=item.get('stdout');stderr=item.get('stderr')
                if (not isinstance(stdout,str) or not isinstance(stderr,str)
                        or digest(stdout.encode())!=item.get('stdout_sha256')
                        or digest(stderr.encode())!=item.get('stderr_sha256')):
                    raise ContractError('interface test transcript digest mismatch')
                good=False
                if (item.get('exit_code')==0 and item.get('timed_out') is False
                        and item.get('output_limited') is False
                        and item.get('cleanup_error') is None):
                    try:
                        parsed=_strict_json_output(stdout)
                        good=(parsed['input_unchanged']
                              and canonical(parsed['value'])==canonical(case['expected']))
                    except (ContractError,ValueError,TypeError,OverflowError):pass
                if item['status']!=('PASS' if good else 'FAILURE'):
                    raise ContractError('interface result and verdict disagree')
            success=(not unauthorized and bool(edits) and
                     all(r['status']=='PASS' for r in record['comparisons']+interface_checks))
            if record.get('outcome')!=('SUCCESS' if success else 'FAILURE'):
                raise ContractError('record claimed a false outcome')
            rows.append(record)
        except (OSError,ValueError,TypeError,KeyError) as e:
            errors.append('INVALID:'+sid+':'+type(e).__name__)
    if errors:
        unstarted=len(rows)==0 and all(e.startswith('MISSING:') for e in errors)
        return {'decision':'NOT_EXECUTED' if unstarted else 'INVALID_EVIDENCE',
                'valid_slots':len(rows),'required_slots':40,'errors':errors}
    keyed={(r['task_id'],r['repetition'],r['arm']):r for r in rows}
    failures=[]
    guards={t['id'] for t in tasks if t['category'] in proto['scoring']['guard_categories']}
    for task in tasks:
        for rep in (1,2):
            a=keyed[(task['id'],rep,'control')]['outcome'];b=keyed[(task['id'],rep,'treatment')]['outcome']
            if task['id'] in guards and b!='SUCCESS':
                failures.append({'task':task['id'],'repetition':rep,'reason':'treatment guard failed'})
            elif a=='SUCCESS' and b!='SUCCESS':
                failures.append({'task':task['id'],'repetition':rep,'reason':'treatment-only regression'})
    return {'decision':'SCREEN_FAIL' if failures else 'SCREEN_PASS','valid_slots':40,
            'control_successes':sum(r['outcome']=='SUCCESS' for r in rows if r['arm']=='control'),
            'treatment_successes':sum(r['outcome']=='SUCCESS' for r in rows if r['arm']=='treatment'),
            'failure_details':failures,'nonclaims':proto['scoring']['limitations']}


def _command_expected(model):
    return ['codex','exec','--json','--model',model,'--sandbox','workspace-write',
            '--ephemeral','--ignore-user-config','--ignore-rules',
            'Read README.md and AGENTS.md, then make the code changes needed to satisfy the task.']


def run_slot(root:Path,slot_id:str,agent_command:str):
    proto,tasks,sched=load_contract()
    manifest=validate_prepared(root)
    if slot_id not in {s['slot_id'] for s in sched['slots']}:
        raise ContractError('unregistered slot')
    cell=next(x for x in sched['slots'] if x['slot_id']==slot_id)
    cmd=shlex.split(agent_command)
    if cmd!=_command_expected(proto['runtime']['model_id']):
        raise ContractError('not the preregistered Codex invocation')
    runtime=_command_identity(cmd,proto['runtime']['model_id'])
    ws=root/'workspaces'/slot_id
    if not ws.is_dir():raise ContractError('workspace missing')
    evidence=root/'evidence'/slot_id
    if evidence.exists() or _record_path(root,slot_id).exists():
        raise ContractError('attempt already exists; no selective reruns')
    previous=None
    for prior in sched['slots'][:cell['position']-1]:
        path=_record_path(root,prior['slot_id'])
        if not path.is_file():raise ContractError('previous registered slot was not completed; frozen order required')
        row=strict_load(path.read_bytes())
        if row.get('slot_id')!=prior['slot_id'] or row.get('position')!=prior['position'] or row.get('previous_observation_sha256')!=previous:
            raise ContractError('previous evidence chain is invalid')
        previous=digest(path.read_bytes())
    # The attempt marker is written *before* contacting the provider.
    evidence.mkdir(parents=True)
    attempt={'schema':'far-agent-instruction-attempt/1','slot_id':slot_id,
             'freeze':manifest['freeze'],'runtime':runtime,'previous_observation_sha256':previous}
    (root/'evidence'/(slot_id+'.attempt.json')).write_bytes(canonical(attempt))
    (evidence/'runtime.json').write_bytes(canonical(runtime))
    try:
        run=_execute_traced_agent(cmd,ws,os.environ.copy(),
                                  proto['runtime']['max_agent_seconds'],
                                  proto['runtime']['max_agent_output_bytes'])
        (evidence/'agent-events.ndjson').write_bytes(run['stdout'])
        (evidence/'agent-stderr.txt').write_bytes(run['stderr'])
        try:trace=_parse_agent_trace(run['stdout'])
        except (ValueError,UnicodeError):trace=None
        receipt={'runtime':runtime,'validated_trace':trace,
                 'previous_observation_sha256':previous,
                 'stdout_sha256':digest(run['stdout']),'stderr_sha256':digest(run['stderr']),
                 **{k:run[k] for k in ('exit_code','timed_out','output_limited','stdout_bytes_observed','stderr_bytes_observed')}}
        record=grade_slot(root,slot_id,receipt)
        _record_path(root,slot_id).write_bytes(canonical(record))
        return record
    except Exception as exc:
        # Preserve the attempted slot as a negative immutable trace even if
        # source integrity or Docker fails before a standard grade exists.
        failure={'schema':'far-agent-instruction-attempt-error/1','slot_id':slot_id,
                 'error_type':type(exc).__name__,'message':str(exc),
                 'runtime':runtime,'previous_observation_sha256':previous}
        (evidence/'negative-outcome.json').write_bytes(canonical(failure))
        raise


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['validate','schedule','prepare','run-slot','analyze'])
    parser.add_argument('--output',type=Path)
    parser.add_argument('--slot')
    parser.add_argument('--agent-command',help='Exact Codex CLI command; use fixed --model gpt-6 --json and full isolated flags')
    args=parser.parse_args(argv)
    if args.action=='validate':
        proto,tasks,sched=load_contract()
        result={'valid':True,'status':proto['status'],'tasks':len(tasks),
                'slots':len(sched['slots']),'source_sha256':proto['task_corpus']['sha256'],
                'model_runs':0}
    elif args.action=='schedule':result=load_contract()[2]
    elif args.action=='prepare':
        if not args.output:parser.error('prepare requires --output')
        result={'prepared_root':str(prepare(args.output)),'status':'NOT_EXECUTED'}
    elif args.action=='run-slot':
        if not args.output or not args.slot or not args.agent_command:
            parser.error('run-slot requires --output, --slot and --agent-command')
        result=run_slot(args.output,args.slot,args.agent_command)
    else:
        if not args.output:parser.error('analyze requires --output')
        result=analyze(args.output)
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0


if __name__=='__main__':
    try:sys.exit(main())
    except (ContractError,OSError,ValueError,subprocess.CalledProcessError,subprocess.TimeoutExpired) as exc:
        print('AGENT_INSTRUCTION_PREFLIGHT_BLOCKED: '+str(exc),file=sys.stderr)
        sys.exit(2)
