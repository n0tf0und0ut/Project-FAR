#!/usr/bin/env python3
"""Fail-closed *structural* replay of FAR-REPLAN-001 candidate run receipts.

Does not establish independent oracle provenance, model identity or causal effect.
Those require a separately authenticated, frozen independent evaluator.
"""
from __future__ import annotations

import argparse
import base64
import json
import math
from pathlib import Path

from tools import replanning_study_gate as gate
from tools import replanning_study_runner as runner


class EvidenceError(ValueError):
    pass


def _bytes64(raw: str, declared: str, label: str) -> bytes:
    if type(raw) is not str or type(declared) is not str or gate.HEX64.fullmatch(declared) is None:
        raise EvidenceError("invalid base64/hash in " + label)
    try:
        out = base64.b64decode(raw, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise EvidenceError("invalid base64 in " + label) from exc
    if base64.b64encode(out).decode() != raw or gate.digest(out) != declared:
        raise EvidenceError("digest mismatch in " + label)
    return out


def verify_arm(row: dict, expected_task: dict, expected_arm: str) -> dict:
    if type(row) is not dict or set(row) != {
        "schema", "task_id", "arm", "provenance", "model", "status", "trace_status",
        "initial_file_sha256", "final_file_sha256", "fault_injected", "fault_required",
        "orchestration_result_sha256", "model_requests", "tool_execution_receipts",
        "grade", "usage", "not_scored_reason",
    }:
        raise EvidenceError("arm record schema mismatch")
    if row["schema"] != "far-replan-candidate-arm/1" or row["task_id"] != expected_task["task_id"] or row["arm"] != expected_arm:
        raise EvidenceError("task/arm binding mismatch")
    if row["status"] != "DIAGNOSTIC_ONLY_NOT_INDEPENDENTLY_ATTESTED":
        raise EvidenceError("attempt to promote candidate to attested outcome")
    if row["model"] != runner.MODEL:
        raise EvidenceError("model manifest mismatch")
    if row["provenance"] not in ("LOCAL_OLLAMA", "SYNTHETIC_TEST"):
        raise EvidenceError("unrecognized provider provenance")
    if type(row["fault_injected"]) is not bool or type(row["fault_required"]) is not bool:
        raise EvidenceError("fault flags must be boolean")
    if row["fault_required"] != expected_task["interrupted"]:
        raise EvidenceError("frozen interruption changed")
    if row["initial_file_sha256"] != expected_task["source_sha256"]:
        raise EvidenceError("different baseline source")
    if type(row["final_file_sha256"]) is not str or gate.HEX64.fullmatch(row["final_file_sha256"]) is None:
        raise EvidenceError("final file SHA not preserved")
    hs = row["orchestration_result_sha256"]
    if type(hs) is not list or not 1 <= len(hs) <= (13 if expected_arm == "replanning" else 1) or any(type(h) is not str or gate.HEX64.fullmatch(h) is None for h in hs):
        raise EvidenceError("orchestration result binding invalid")
    if type(row["model_requests"]) is not list or type(row["tool_execution_receipts"]) is not list:
        raise EvidenceError("raw request/receipt collections missing")
    if len(row["model_requests"]) > 70 or len(row["tool_execution_receipts"]) > 60:
        raise EvidenceError("unbounded trace")
    # Reconstruct the starting task source from the frozen fixture identity,
    # not from a mutable model claim. Synthetic unit fixtures supply source.
    if "fixture_index" in expected_task:
        index = expected_task["fixture_index"]
        if type(index) is not int or not 0 <= index < 30:
            raise EvidenceError("invalid frozen fixture index")
        fixture = gate.fixtures.task(index)
        if fixture["task_id"] != expected_task["task_id"]:
            raise EvidenceError("fixture/task identity drift")
        source = fixture["source"]
        workspace = {"solution.py": source,
                     "README.md": fixture["spec"] + "\nImplement transform(payload) in solution.py. Do not alter other files.\n",
                     "test_public.py": gate.fixtures.public_test_code(fixture)}
    else:
        source = expected_task.get("source")
        if type(source) is not str:
            raise EvidenceError("source bytes unavailable for structural replay")
        workspace = {"solution.py": source}
    if gate.digest(source.encode("utf-8")) != expected_task["source_sha256"]:
        raise EvidenceError("source snapshot does not match frozen digest")
    observed_model_tokens = 0
    requested_worker_actions = []
    for i, e in enumerate(row["model_requests"]):
        if type(e) is not dict or set(e) != {"kind", "purpose", "request_base64", "request_sha256", "response_base64", "response_sha256", "http_status", "error"}:
            raise EvidenceError("model event schema mismatch")
        if e["kind"] != ("genuine_provider_request" if row["provenance"] == "LOCAL_OLLAMA" else "synthetic_provider_test"):
            raise EvidenceError("provider evidence confusion")
        req = _bytes64(e["request_base64"], e["request_sha256"], "model request")
        try:
            data = json.loads(req, object_pairs_hook=gate.unique_pairs,
                              parse_constant=lambda x: (_ for _ in ()).throw(EvidenceError("nonfinite model request")))
        except (ValueError, UnicodeError, TypeError, RecursionError) as exc:
            raise EvidenceError("malformed model request") from exc
        if type(data) is not dict:
            raise EvidenceError("model request must be a JSON object")
        if data.get("model") != runner.MODEL["name"]:
            raise EvidenceError("request provider identity drift")
        if e["response_base64"] is None:
            if e["response_sha256"] is not None:
                raise EvidenceError("unobserved response has a digest")
        else:
            resp = _bytes64(e["response_base64"], e["response_sha256"], "model response")
            try:
                body = json.loads(resp, object_pairs_hook=gate.unique_pairs,
                                  parse_constant=lambda x: (_ for _ in ()).throw(EvidenceError("nonfinite response")))
            except (ValueError, UnicodeError, TypeError, RecursionError) as exc:
                raise EvidenceError("malformed raw model response") from exc
            if type(body) is not dict or body.get("model") != runner.MODEL["name"]:
                raise EvidenceError("response model drift")
            if e["http_status"] == 200 and body.get("done") is True:
                a, b = body.get("prompt_eval_count"), body.get("eval_count")
                if type(a) is not int or type(b) is not int or a < 0 or b < 0:
                    raise EvidenceError("missing trustworthy provider counters")
                observed_model_tokens += a + b
                if e["error"] is None and e["purpose"] == "worker":
                    message = body.get("message")
                    if type(message) is not dict or type(message.get("content")) is not str:
                        raise EvidenceError("missing worker action content")
                    try:
                        action = runner.tar.strict_json(message["content"])
                    except (ValueError, UnicodeError, TypeError, RecursionError) as exc:
                        raise EvidenceError("malformed decoded worker action") from exc
                    if type(action) is not dict:
                        raise EvidenceError("decoded worker action must be an object")
                    requested_worker_actions.append(action)
        if e["purpose"] not in ("planner", "worker"):
            raise EvidenceError("unregistered model request")
    if len(requested_worker_actions) < len(row["tool_execution_receipts"]):
        raise EvidenceError("tool receipt has no corresponding model action")
    if len(requested_worker_actions) - len(row["tool_execution_receipts"]) > 1:
        raise EvidenceError("worker action missing intermediate tool receipt")
    fault_events = 0
    first_write_seen = False
    worker_finished = False
    for i, e in enumerate(row["tool_execution_receipts"]):
        if type(e) is not dict or set(e) != {"action", "tool_number", "result", "receipt_sha256"}:
            raise EvidenceError("tool receipt shape mismatch")
        if type(e["tool_number"]) is not int or e["tool_number"] != i + 1:
            raise EvidenceError("tool sequence break")
        if type(e["action"]) is not dict or e["action"].get("action") not in runner.ALLOWED_TOOLS:
            raise EvidenceError("unapproved tool receipt")
        action = e["action"]
        if worker_finished:
            raise EvidenceError("worker action recorded after finish")
        if requested_worker_actions[i] != action:
            raise EvidenceError("tool action differs from decoded worker response")
        if action["action"] in ("read_file", "write_file"):
            if action.get("path") not in (runner.ALLOWED_READS if action["action"] == "read_file" else {"solution.py"}):
                raise EvidenceError("unapproved tool path")
        expected_keys = {"list_files": {"action"}, "read_file": {"action", "path"},
                         "write_file": {"action", "path", "content"},
                         "finish": {"action"}}[action["action"]]
        if set(action) != expected_keys:
            raise EvidenceError("unexpected tool action arguments")
        result = e["result"]
        if type(result) is not dict:
            raise EvidenceError("tool result must be a dictionary")
        if action["action"] == "write_file":
            if type(action["content"]) is not str or len(action["content"].encode("utf-8")) > 32768:
                raise EvidenceError("invalid solution write content")
            first_write = not first_write_seen
            first_write_seen = True
            if first_write and row["fault_required"] and result != {"error": "INJECTED_TRANSIENT_WRITE_FAILURE", "executed": False}:
                raise EvidenceError("scheduled first-write fault is missing")
            if result == {"error": "INJECTED_TRANSIENT_WRITE_FAILURE", "executed": False}:
                fault_events += 1
                if not row["fault_required"] or not first_write or fault_events > 1:
                    raise EvidenceError("unscheduled or repeated injected fault")
            else:
                expected_result = {"written": "solution.py", "sha256": gate.digest(action["content"].encode("utf-8"))}
                if result != expected_result:
                    raise EvidenceError("inconsistent successful write receipt")
                workspace["solution.py"] = action["content"]
        elif action["action"] == "read_file":
            if action["path"] not in workspace or result != {"content": workspace[action["path"]]}:
                raise EvidenceError("file read receipt does not match replayed workspace")
        elif action["action"] == "list_files":
            if result != {"files": sorted(workspace)}:
                raise EvidenceError("list_files receipt does not match workspace")
        elif action["action"] == "finish":
            if result != {"finished": True}:
                raise EvidenceError("invalid finish receipt")
            worker_finished = True
        actual = gate.digest(gate.canonical({"action": e["action"], "result": e["result"], "tool_number": i+1}))
        if actual != e["receipt_sha256"]:
            raise EvidenceError("tool execution receipt modified")
    if row["fault_injected"] is not (fault_events == 1):
        raise EvidenceError("fault flag disagrees with executed receipt sequence")
    if gate.digest(workspace["solution.py"].encode("utf-8")) != row["final_file_sha256"]:
        raise EvidenceError("final source digest contradicts replayed tool writes")
    g = row["grade"]
    if type(g) is not dict or set(g) != {"source", "executed", "success", "exit_status", "trace_sha256", "trace"}:
        raise EvidenceError("oracle grade shape mismatch")
    if g["source"] != "trusted-host-docker-grader" or type(g["executed"]) is not bool or type(g["success"]) is not bool:
        raise EvidenceError("untrusted grading description")
    if type(g["trace"]) is not str or gate.digest(g["trace"].encode()) != g["trace_sha256"]:
        raise EvidenceError("grader trace hash mismatch")
    try:
        trace = json.loads(g["trace"], object_pairs_hook=gate.unique_pairs)
    except (ValueError, TypeError, RecursionError) as exc:
        raise EvidenceError("invalid grader trace") from exc
    if type(trace) is not dict or set(trace) != {"schema", "comparisons", "executed", "success"} or trace["schema"] != "far-isolated-output-grade/1":
        raise EvidenceError("unrecognized grader trace")
    comps = trace["comparisons"]
    if type(comps) is not list or len(comps) != 6 or any(type(x) is not dict for x in comps):
        raise EvidenceError("incomplete grader comparison inventory")
    if [(x.get("group"),x.get("index")) for x in comps] != [
        ("public",0),("public",1),("hidden",0),("hidden",1),("hidden",2),("hidden",3)]:
        raise EvidenceError("grader slot identity mismatch")
    statuses = {"PASS", "FAILURE", "OUTPUT_LIMIT", "RESOURCE_LIMIT", "INFRA_FAILURE"}
    if any(x.get("status") not in statuses or type(x.get("status")) is not str for x in comps):
        raise EvidenceError("unknown or missing grader comparison status")
    for comp in comps:
        if comp["status"] == "PASS":
            # The Docker grader can emit PASS only after a started candidate
            # exits 0 without timeout/output limits. Host receipt assertions
            # still need an independent source of authenticity.
            if (type(comp.get("exit_code")) is not int or comp["exit_code"] != 0
                    or comp.get("timed_out") is not False
                    or comp.get("output_limited") is not False
                    or type(comp.get("stdout")) is not str
                    or not comp["stdout"].startswith(runner.free.CANDIDATE_STARTED + "\n")):
                raise EvidenceError("contradictory PASS process receipt")
    executed = all(x["status"] != "INFRA_FAILURE" for x in comps)
    success = executed and all(x.get("status") == "PASS" for x in comps)
    if (trace["executed"] is not executed or trace["success"] is not success
            or g["executed"] is not executed or g["success"] is not success
            or g["exit_status"] != ((0 if success else 1) if executed else None)):
        raise EvidenceError("self-contradicting grade")
    # Authenticity still requires independent replay; this is only a structural
    # sanity check on the bytes the candidate runner claims it preserved.
    u = row["usage"]
    if type(u) is not dict or set(u) != {"model_tokens", "tool_calls", "wall_seconds"}:
        raise EvidenceError("budget evidence missing")
    if type(u["tool_calls"]) is not int or u["tool_calls"] != len(row["tool_execution_receipts"]) or u["tool_calls"] > 60:
        raise EvidenceError("tool budget/trace inconsistent")
    if type(u["model_tokens"]) is not int or not 0 <= u["model_tokens"] <= 15000:
        raise EvidenceError("model token budget exceeded")
    if u["model_tokens"] < observed_model_tokens:
        raise EvidenceError("raw model counters exceed recorded total")
    if type(u["wall_seconds"]) not in (int,float) or not math.isfinite(u["wall_seconds"]) or not 0 <= u["wall_seconds"] <= 2700:
        raise EvidenceError("wall budget exceeded")
    return {"task_id": row["task_id"], "arm": row["arm"],
            "structurally_consistent": True, "provider_declared": row["provenance"],
            "grader_claimed_success": g["success"], "independently_attested_success": None}


def analyze(candidate: dict, receipts: dict[str, dict], schedule: list[dict]) -> dict:
    """Retain complete denominator; missing receipts are NOT imputed successes."""
    expected = {(r["task_id"], arm) for r in candidate["task_rows"] for arm in gate.ARMS}
    if len(schedule) != 24 or {(r["task_id"],r["arm"]) for r in schedule} != expected:
        raise EvidenceError("allocation schedule invalid")
    if len({r["slot"] for r in schedule}) != 24 or [r["slot"] for r in schedule] != list(range(1,25)):
        raise EvidenceError("allocation slot order invalid")
    unknown = set(receipts) - {f"slot-{i:02d}" for i in range(1,25)}
    if unknown:
        raise EvidenceError("unregistered extra receipt slots")
    lookup = {x["task_id"]: x for x in candidate["task_rows"]}
    records = []
    for slot in schedule:
        key = f"slot-{slot['slot']:02d}"
        row = receipts.get(key)
        if row is None:
            records.append({"slot": slot["slot"], "task_id": slot["task_id"], "arm": slot["arm"], "status": "UNSTARTED_OR_MISSING"})
            continue
        if isinstance(row, EvidenceError):
            records.append({"slot": slot["slot"], "task_id": slot["task_id"], "arm": slot["arm"],
                            "status": "INVALID_PRESERVED", "error": str(row)[:180]})
            continue
        try:
            audit = verify_arm(row, lookup[slot["task_id"]], slot["arm"])
            records.append({"slot": slot["slot"], **audit, "status": "STRUCTURALLY_REPLAYED_NOT_AUTHENTICATED"})
        except (EvidenceError, TypeError, ValueError) as exc:
            records.append({"slot": slot["slot"], "task_id": slot["task_id"], "arm": slot["arm"],
                            "status": "INVALID_PRESERVED", "error": str(exc)[:180]})
    complete = all(r["status"] == "STRUCTURALLY_REPLAYED_NOT_AUTHENTICATED" for r in records)
    return {"study_id": "FAR-REPLAN-001", "status": "NOT_ESTABLISHED_NO_INDEPENDENT_RECEIPT_ATTESTATION",
            "denominator_pairs": 12, "expected_arms": 24,
            "records_structurally_replayed": sum(r["status"] == "STRUCTURALLY_REPLAYED_NOT_AUTHENTICATED" for r in records),
            "records_missing": sum(r["status"] == "UNSTARTED_OR_MISSING" for r in records),
            "records_invalid": sum(r["status"] == "INVALID_PRESERVED" for r in records),
            "complete_structural_census": complete,
            "paired_verified_completion_difference": None,
            "peer_independent_oracle_review": "NOT_ESTABLISHED",
            "records": records}


def read_receipts(directory: Path) -> dict[str, dict | EvidenceError]:
    """Preserve malformed source records as invalid slots, never drop the pair."""
    receipts: dict[str, dict | EvidenceError] = {}
    for path in directory.glob("slot-*.json"):
        if path.stem in receipts:
            raise EvidenceError("duplicate evidence file")
        try:
            row, _ = gate.read_json(path, max_size=4_000_000)
        except (gate.GateError, UnicodeError, ValueError, OSError, RecursionError) as exc:
            receipts[path.stem] = EvidenceError("malformed slot evidence: " + type(exc).__name__)
        else:
            receipts[path.stem] = row
    return receipts


def main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--evidence-dir",type=Path,required=True)
    p.add_argument("--manifest",type=Path,required=True)
    a=p.parse_args(argv)
    try:
        candidate=gate.check_candidate()
        approved=gate.require_launch_manifest(candidate,a.manifest)
        receipts={}
        receipts = read_receipts(a.evidence_dir)
        result=analyze(candidate,receipts,approved["schedule"])
    except (gate.GateError,EvidenceError,ValueError,OSError) as exc:
        print("INVALID/NOT ESTABLISHED: "+str(exc),file=__import__("sys").stderr)
        return 2
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
