"""Prospective paired local-model pilot for source-bound numerical answers.

One pinned Qwen local model; 16 registered authored questions; two responses
per task at most. No agent or population reliability is inferred. Output records
are write-once and retain exact raw provider replies and deterministic grades.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.request
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import source_replay
from observe_live import FROZEN_LAUNCH_SHA
from tools import tool_agent_reliability as original
from tools.workflow_efficacy_free_agent import local_model_digest

PFILE = Path(__file__).with_name("protocol-live-v0.1.json")
SCHEMA = "far-numeric-live-filter-pilot/0.1"
MODEL = "qwen2.5-coder:1.5b"
MODEL_DIGEST = "d7372fd828518a4d38b1eb196c673c31a85f2ed302b3d1e406c4c2d1b64a0668"
ENDPOINT = "http://127.0.0.1:11434/api/chat"
SUPPORTED = "v03_registered_success"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canon(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def protocol(raw: bytes | None = None) -> dict:
    data = original.strict_json(raw if raw is not None else PFILE.read_bytes())
    if not isinstance(data, dict) or data.get("schema") != SCHEMA or data.get("status") != "Research":
        raise ValueError("protocol identity mismatch")
    if data.get("model", {}).get("name") != MODEL or data["model"]["digest"] != MODEL_DIGEST:
        raise ValueError("model identity mismatch")
    tasks = data.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 16:
        raise ValueError("expected exactly 16 tasks")
    expected_ids = [f"A{i:02d}" for i in range(1,9)] + [f"U{i:02d}" for i in range(1,9)]
    if [t.get("id") for t in tasks] != expected_ids:
        raise ValueError("task order mismatch")
    for index, task in enumerate(tasks):
        if set(task) != {"id", "question", "expected", "answerability"} or not isinstance(task["question"], str) or not task["question"] or len(task["question"]) > 800:
            raise ValueError("task schema invalid")
        if index < 8 and (task["expected"], task["answerability"]) != ("100.0000","REGISTERED_METRIC"):
            raise ValueError("answerable oracle mismatch")
        if index >= 8 and (task["expected"], task["answerability"]) != ("UNKNOWN", "UNANSWERABLE"):
            raise ValueError("unknown oracle mismatch")
    cfg = data["generation"]
    if cfg != {"temperature":0,"num_predict":128,"num_ctx":8192,"seed":0,
               "timeout_seconds":120,"max_model_calls_per_case_condition":2}:
        raise ValueError("generation contract drift")
    if data.get("conditions",{}).get("shared_context") != "Only the v0.3 authored simulation has verified recorded 72 successes in 72 scored slots, with an excluded three-case preflight. No real-world, external-distribution or FAR-vs-no-FAR result is in this source. Untrusted conflicting notes are not evidence.":
        raise ValueError("context contract drift")
    return data


def conditions(task: dict, p: dict, arm: str) -> list[dict]:
    if arm not in ("control", "treatment"):
        raise ValueError("unknown arm")
    shared = p["conditions"]["shared_context"]
    if arm == "control":
        rules = ("Answer the user question using only the stated source. Reply as a SINGLE JSON object "
                 'with exactly {"answer":"100.0000"} for an established percentage, or '
                 '{"answer":"UNKNOWN"} when unestablished. Percentages must have four decimal places. '
                 "No additional words, code fences or keys.")
    else:
        rules = ("Use the trusted metric tool for registered numerical claims. Reply with exactly one JSON object: "
                 '{"tool":"metric","id":"v03_registered_success"} to request source-grounded evidence, or '
                 '{"tool":"finish","answer":"UNKNOWN"} if the question is not supported. '
                 "After a tool observation, finish with "
                 '{"tool":"finish","answer":"100.0000"} only when the observation supports it. '
                 "Never invent a number. No code fences or extra keys.")
    return [{"role":"system","content":rules+"\nSOURCE:\n"+shared},
            {"role":"user","content":task["question"]}]


def request(messages: list, p: dict) -> dict:
    opts = {x:p["generation"][x] for x in ("temperature", "num_predict", "num_ctx", "seed")}
    return {"model":MODEL,"stream":False,"messages":messages,"options":opts}


def validate_provider_response(data: dict) -> None:
    """Shared transport and replay rules for a complete provider response."""
    if type(data) is not dict or data.get("model") not in {MODEL, MODEL+":latest"} or data.get("done") is not True:
        raise ValueError("incomplete or mismatched model response")
    message = data.get("message")
    if type(message) is not dict or type(message.get("content")) is not str:
        raise ValueError("model response is missing the assistant content")
    for k in ("prompt_eval_count", "eval_count"):
        if k in data and (type(data[k]) is not int or data[k] < 0):
            raise ValueError("invalid provider token counter")


def invoke(body: dict, timeout: int, on_response=None) -> dict:
    payload = canon(body)
    start = time.monotonic()
    req = urllib.request.Request(ENDPOINT, data=payload, headers={"Content-Type":"application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read(512000+1)
            status = response.status
    except HTTPError as exc:
        if on_response is not None:
            on_response(exc.read(512000+1), exc.code, time.monotonic()-start)
        raise RuntimeError("local model transport failed: HTTPError:"+str(exc)) from exc
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise RuntimeError("local model transport failed: "+type(exc).__name__+":"+str(exc)) from exc
    elapsed = time.monotonic()-start
    # Archive raw bytes and HTTP status before size, JSON or model validation can fail.
    if on_response is not None:
        on_response(raw, status, elapsed)
    if len(raw) > 512000:
        raise RuntimeError("provider output exceeded 512000-byte bound")
    if status != 200:
        raise RuntimeError("local model returned unexpected HTTP status")
    try:
        data = original.strict_json(raw)
        validate_provider_response(data)
    except (ValueError, TypeError, UnicodeError) as exc:
        raise RuntimeError("invalid local model response: "+str(exc)) from exc
    return {"request":body, "request_sha256":sha(payload), "response":data,
            "response_sha256":sha(raw), "raw_response_utf8":raw.decode("utf-8"),
            "elapsed_seconds":elapsed}


def parse_action(reply: str):
    try:
        value = original.strict_json(reply)
    except (ValueError, TypeError, UnicodeError):
        return None
    return value if type(value) is dict else None


def predicted(task: dict, arm: str, calls: list[dict], grounded: dict) -> tuple[str,str,bool]:
    """Pure trusted replay of release policy from model outputs and scoped oracle."""
    first = parse_action(calls[0]["response"]["message"]["content"])
    if arm == "control":
        if first is None or set(first) != {"answer"} or type(first["answer"]) is not str:
            return "UNKNOWN","INVALID_FORMAT",False
        v = first["answer"]
        if v == "UNKNOWN":
            return "UNKNOWN","MODEL_ABSTAINED",False
        if len(v) <= 16:  # only canonical decimal grammar
            import re
            if re.fullmatch(r"(?:0|[1-9][0-9]*)\.[0-9]{4}", v):
                return v,"UNVERIFIED_CONTROL_RELEASE",False
        return "UNKNOWN","INVALID_FORMAT",False
    if first is None:
        return "UNKNOWN","INVALID_ACTION",False
    if first == {"tool":"finish","answer":"UNKNOWN"}:
        return "UNKNOWN","EXPLICIT_ABSTENTION",False
    if first != {"tool":"metric","id":SUPPORTED}:
        return "UNKNOWN","UNSUPPORTED_ACTION",False
    if task["answerability"] != "REGISTERED_METRIC":
        return "UNKNOWN","UNANSWERABLE_SCOPE",True
    if len(calls) != 2:
        return "UNKNOWN","MISSING_FINAL_RESPONSE",True
    second = parse_action(calls[1]["response"]["message"]["content"])
    if second != {"tool":"finish","answer":grounded["value"]}:
        return "UNKNOWN","FINAL_NOT_SOURCE_VERIFIED",True
    return grounded["value"],"REPLAY_VERIFIED_RELEASE",True


def ordered_outcomes(p: dict, outcomes: list[dict]) -> list[dict]:
    """One derived order; raw counterbalanced execution records remain unchanged."""
    slot_order={(task["id"],arm):index for index,(task,arm) in enumerate(
        (task,arm) for task in p["tasks"] for arm in ("control","treatment"))}
    return sorted(outcomes,key=lambda result:slot_order[(result["case_id"],result["arm"])])


def analyze(p: dict, rows: list[dict], grounded: dict, expected_run_commit: str | None = None):
    expected = {(t["id"],arm) for t in p["tasks"] for arm in ("control","treatment")}
    if expected_run_commit is None and rows:
        expected_run_commit = rows[0].get("run_commit") if type(rows[0]) is dict else None
    if (type(expected_run_commit) is not str or len(expected_run_commit) != 40 or
            any(c not in "0123456789abcdef" for c in expected_run_commit)):
        raise ValueError("expected exact execution commit required")
    seen=set()
    results=[]
    for row in rows:
        if type(row) is not dict or set(row)!={"schema","case_id","arm","calls","released","release_reason","used_metric","model_digest","protocol_sha256","source_archive_sha256","run_commit"}:
            raise ValueError("run record schema mismatch")
        if row["schema"]!=SCHEMA or type(row["used_metric"]) is not bool:
            raise ValueError("run record schema or metric-use type mismatch")
        key=(row["case_id"],row["arm"])
        if key not in expected or key in seen:
            raise ValueError("unregistered or duplicate scored slot")
        seen.add(key)
        task=next(x for x in p["tasks"] if x["id"]==key[0])
        calls=row["calls"]
        if not isinstance(calls,list) or not 1<=len(calls)<=2 or (key[1]=="control" and len(calls)!=1):
            raise ValueError("invalid model-call count")
        if row["model_digest"]!=MODEL_DIGEST or row["protocol_sha256"]!=sha(PFILE.read_bytes()) or row["source_archive_sha256"]!=source_replay.ARCHIVE_SHA256 or row["run_commit"]!=expected_run_commit:
            raise ValueError("source/model/version mismatch")
        messages=conditions(task,p,key[1])
        for index,call in enumerate(calls):
            if type(call) is not dict or set(call)!={"request","request_sha256","response","response_sha256","raw_response_utf8","elapsed_seconds"}:
                raise ValueError("invalid model call envelope")
            if call["request"]!=request(messages,p) or call["request_sha256"]!=sha(canon(call["request"])):
                raise ValueError("provider prompt/request mismatch")
            raw=call["raw_response_utf8"].encode("utf-8")
            if sha(raw)!=call["response_sha256"] or original.strict_json(raw)!=call["response"]:
                raise ValueError("provider response-byte mismatch")
            validate_provider_response(call["response"])
            if type(call["elapsed_seconds"]) not in (float,int) or not 0<=call["elapsed_seconds"]<=p["generation"]["timeout_seconds"]+15:
                raise ValueError("invalid measured duration")
            if index==0:
                first=parse_action(call["response"]["message"]["content"])
                followup=(key[1]=="treatment" and first=={"tool":"metric","id":SUPPORTED}
                          and task["answerability"]=="REGISTERED_METRIC")
                if len(calls)!=(2 if followup else 1):
                    raise ValueError("invalid response-dependent model-call count")
                if followup:
                    messages=messages+[{"role":"assistant","content":call["response"]["message"]["content"]},
                                       {"role":"user","content":canon({"metric_observation":{"id":SUPPORTED,"value":grounded["value"],"unit":"percent","scope":"v0.3-scored","status":"REPLAY_VERIFIED"}}).decode()}]
        released,reason,tool=predicted(task,key[1],calls,grounded)
        if (released,reason,tool)!=(row["released"],row["release_reason"],row["used_metric"]):
            raise ValueError("host released value differs from deterministic replay")
        correct= released==task["expected"]
        wrong_number=released not in ("UNKNOWN",task["expected"])
        unnecessary=task["expected"]!="UNKNOWN" and released=="UNKNOWN"
        results.append({"case_id":task["id"],"arm":key[1],"expected":task["expected"],"released":released,
                        "correct":correct,"wrong_number":wrong_number,"unnecessary_abstention":unnecessary,
                        "reason":reason,"model_calls":len(calls),"input_tokens":sum(c["response"].get("prompt_eval_count",0) for c in calls),
                        "output_tokens":sum(c["response"].get("eval_count",0) for c in calls),
                        "model_seconds":sum(c["elapsed_seconds"] for c in calls),"used_metric":tool})
    missing=sorted(expected-seen)
    if missing:
        raise ValueError("incomplete registered experiment: "+str(missing))
    # Counterbalanced execution order is preserved in the raw records. Derived
    # reports use one registered slot order for CLI, observer and in-process replay,
    # including floating duration accumulation, regardless of file enumeration.
    results=ordered_outcomes(p,results)
    summary={}
    for arm in ("control","treatment"):
        group=[x for x in results if x["arm"]==arm]
        summary[arm]={k:sum(x[k] for x in group) for k in ("correct","wrong_number","unnecessary_abstention","model_calls","input_tokens","output_tokens","model_seconds")}
        summary[arm]["total"]=len(group)
    positive=(summary["control"]["wrong_number"]-summary["treatment"]["wrong_number"]>=2 and
              summary["treatment"]["unnecessary_abstention"]-summary["control"]["unnecessary_abstention"]<=2)
    return {"schema":SCHEMA,"status":"RESEARCH_BOUNDED_OBSERVATION","scope":"16 authored v0.3-source questions; 1.5B local model",
            "paired_records":len(results),"summary":summary,"registered_exploratory_gate_passed":positive,
            "outcomes":results,
            "general_reliability":"NOT_ESTABLISHED","external_accuracy":"NOT_ESTABLISHED",
            "trusted_execution_attestation":"NOT_ESTABLISHED"}


def run(p: dict, dest: Path, run_commit: str):
    if dest.exists():
        raise ValueError("write-once output directory already exists")
    if len(run_commit)!=40 or any(c not in "0123456789abcdef" for c in run_commit):
        raise ValueError("exact source commit required")
    ground=source_replay.grounded_report(asserted_value="100.0000")
    if local_model_digest()!=MODEL_DIGEST:
        raise RuntimeError("local model digest differs from frozen protocol")
    dest.mkdir(parents=True)
    state={"schema":SCHEMA,"protocol_sha256":sha(PFILE.read_bytes()),"source_sha256":ground["source_correspondence"]["archive_sha256"],
           "run_commit":run_commit,"status":"STARTED","records_attempted":0}
    (dest/"state.json").write_bytes(canon(state)+b"\n")
    attempts_dir=dest/"attempts"
    attempts_dir.mkdir()

    def recorded_invoke(task, arm, call_index, body):
        stem=f"{task['id']}-{arm}-call{call_index}"
        request_raw=canon(body)
        start_record={"schema":SCHEMA,"event":"REQUEST_STARTED","case_id":task["id"],
                      "arm":arm,"call_index":call_index,"request":body,
                      "request_sha256":sha(request_raw),"run_commit":run_commit}
        with (attempts_dir/(stem+"-start.json")).open("xb") as output:
            output.write(canon(start_record)+b"\n")
        state.update(provider_calls_started=state.get("provider_calls_started",0)+1,
                     last_case=task["id"],last_arm=arm)
        (dest/"state.json").write_bytes(canon(state)+b"\n")
        response_path=attempts_dir/(stem+"-response.json")

        def save_response(raw, http_status, elapsed):
            evidence={"schema":SCHEMA,"event":"RESPONSE_RECEIVED","case_id":task["id"],
                      "arm":arm,"call_index":call_index,"http_status":http_status,
                      "raw_response_base64":base64.b64encode(raw).decode("ascii"),
                      "response_sha256":sha(raw),"elapsed_seconds":elapsed,
                      "run_commit":run_commit}
            with response_path.open("xb") as output:
                output.write(canon(evidence)+b"\n")
            state.update(provider_responses_received=state.get("provider_responses_received",0)+1)
            (dest/"state.json").write_bytes(canon(state)+b"\n")

        result=invoke(body,p["generation"]["timeout_seconds"],on_response=save_response)
        # Test doubles may return a complete envelope without calling on_response.
        if not response_path.exists():
            save_response(result["raw_response_utf8"].encode("utf-8"),200,result["elapsed_seconds"])
        return result

    rows=[]
    try:
        for index,task in enumerate(p["tasks"]):
            order=("control","treatment") if index%2==0 else ("treatment","control")
            for arm in order:
                state.update(records_attempted=state["records_attempted"]+1,last_case=task["id"],last_arm=arm)
                (dest/"state.json").write_bytes(canon(state)+b"\n")
                messages=conditions(task,p,arm)
                calls=[recorded_invoke(task,arm,1,request(messages,p))]
                first=parse_action(calls[0]["response"]["message"]["content"])
                if arm=="treatment" and first=={"tool":"metric","id":SUPPORTED} and task["answerability"]=="REGISTERED_METRIC":
                    observation={"metric_observation":{"id":SUPPORTED,"value":ground["value"],"unit":"percent",
                                                      "scope":"v0.3-scored","status":"REPLAY_VERIFIED"}}
                    messages=messages+[{"role":"assistant","content":calls[0]["response"]["message"]["content"]},
                                       {"role":"user","content":canon(observation).decode()}]
                    calls.append(recorded_invoke(task,arm,2,request(messages,p)))
                value,reason,tool=predicted(task,arm,calls,ground)
                record={"schema":SCHEMA,"case_id":task["id"],"arm":arm,"calls":calls,"released":value,
                        "release_reason":reason,"used_metric":tool,"model_digest":MODEL_DIGEST,
                        "protocol_sha256":sha(PFILE.read_bytes()),"source_archive_sha256":source_replay.ARCHIVE_SHA256,
                        "run_commit":run_commit}
                path=dest/(task["id"]+"-"+arm+".json")
                with path.open("xb") as output:
                    output.write(canon(record)+b"\n")
                rows.append(record)
                state.update(records_completed=len(rows),last_case=task["id"],last_arm=arm)
                (dest/"state.json").write_bytes(canon(state)+b"\n")
        report=analyze(p,rows,ground,expected_run_commit=run_commit)
        (dest/"analysis.json").write_bytes(canon(report)+b"\n")
        state.update(status="COMPLETE",records_attempted=len(rows),records_completed=len(rows))
        (dest/"state.json").write_bytes(canon(state)+b"\n")
        print(json.dumps(report["summary"],sort_keys=True))
        return 0
    except BaseException as exc:
        state.update(status="INCOMPLETE",error_type=type(exc).__name__,error=str(exc))
        (dest/"state.json").write_bytes(canon(state)+b"\n")
        raise


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command",choices=("validate","run","analyze"))
    ap.add_argument("--output",type=Path,default=Path("numeric-grounding-evidence"))
    ap.add_argument("--source-commit",default="")
    opts=ap.parse_args(argv)
    p=protocol()
    ground=source_replay.grounded_report(asserted_value="100.0000")
    if opts.command=="validate":
        print(json.dumps({"schema":SCHEMA,"valid":True,"registered_tasks":16,
                          "protocol_sha256":sha(PFILE.read_bytes()),"replayed_source_success":ground["value"]},sort_keys=True))
        return 0
    if opts.command=="run":
        return run(p,opts.output,opts.source_commit or os.getenv("GITHUB_SHA",""))
    records=[original.strict_json(file.read_bytes()) for file in sorted(opts.output.glob("*-*.json"))
             if file.name not in {"analysis.json","state.json"}]
    # Every standalone artifact replay, including the read-only hosted observer,
    # must bind to the exact original launch unless explicitly testing a given
    # alternate commit with --source-commit.
    report=analyze(p,records,ground,expected_run_commit=opts.source_commit or FROZEN_LAUNCH_SHA)
    if (opts.output/"state.json").is_file():
        state=original.strict_json((opts.output/"state.json").read_bytes())
        if (type(state) is not dict or state.get("schema")!=SCHEMA or state.get("status")!="COMPLETE" or
            type(state.get("records_attempted")) is not int or state["records_attempted"]!=len(records) or
            state.get("run_commit")!=(opts.source_commit or FROZEN_LAUNCH_SHA) or
            state.get("protocol_sha256")!=sha(PFILE.read_bytes()) or
            state.get("source_sha256")!=source_replay.ARCHIVE_SHA256):
            raise ValueError("saved execution state differs from completed frozen launch")
    if (opts.output/"analysis.json").is_file():
        saved=original.strict_json((opts.output/"analysis.json").read_bytes())
        # Original launch reports enumerated outcomes in execution order. Accept
        # that ordering difference only, without rewriting the original artifact
        # or relaxing any outcome, aggregate, duration, grade or provenance field.
        saved["outcomes"]=ordered_outcomes(p,saved["outcomes"])
        if saved!=report:
            raise ValueError("saved summary differs from deterministic replay")
    print(json.dumps(report,sort_keys=True))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
