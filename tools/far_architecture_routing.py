"""FAR routing pilot: real verifier, fixed/declarative arms, scripted agent rehearsal.

Never interpret scripted policy input as evidence of a language-model run.
"""
import argparse
import hashlib
import json
import math
import sys
import time
from itertools import permutations
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Direct `python tools/...py` and `python -m tools...` must resolve the same pinned verifier.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mechanization.far_mechanization.contract_v2_strict_v11 import validate_contract as _validate_contract

SOURCE = ROOT / "research/architecture-routing/protocol-v0.1.json"
ARMS = ("deterministic", "declarative", "agent")


class PilotError(ValueError):
    pass


def blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def load(path=SOURCE):
    p = json.loads(Path(path).read_text(encoding="utf-8"))
    if (p.get("schema") != "far-architecture-routing/0.1"
            or p.get("status") != "RESEARCH_NOT_EXECUTED"
            or p.get("source_commit") != "4e71c7de4457001fd35a65f9b4804d60aac1c4f2"
            or p.get("arms") != list(ARMS)
            or p.get("workflow") != {"far-ir/2.0": ["verify_current"]}
            or p.get("model_runner") != "UNAVAILABLE"):
        raise PilotError("protocol changed")
    cases = p["cases"]
    if len(cases) != 12 or len({c["id"] for c in cases}) != 12 or len({c["path"] for c in cases}) != 12:
        raise PilotError("case population changed")
    for c in cases:
        path = c["path"]
        if (not isinstance(path, str) or path.startswith("/") or ".." in Path(path).parts
                or not path.endswith(".json") or not path.startswith(
                    ("conformance/far-ir-2.0/", "research/results/pca-w4-domain-contracts/"))):
            raise PilotError("unapproved source")
        if (len(c["blob_sha"]) != 40
                or any(ch not in "0123456789abcdef" for ch in c["blob_sha"])
                or c["expected"] not in ("PROVED", "REFUTED", "INVALID")):
            raise PilotError("unfrozen case identity/outcome")
    return p


def plan(p):
    tasks = sorted(p["cases"], key=lambda c: hashlib.sha256(
        ("far-routing-v0.1|" + c["id"]).encode()).hexdigest())
    orders = list(permutations(ARMS))
    return [{"case_id": c["id"], "arm": arm}
            for i, c in enumerate(tasks) for arm in orders[i % len(orders)]]


def source_document(case):
    path = (ROOT / case["path"]).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise PilotError("source escapes repository")
    raw = path.read_bytes()
    if blob_sha(raw) != case["blob_sha"]:
        raise PilotError("frozen source mismatch: " + case["id"])
    doc = json.loads(raw.decode("utf-8"))
    if not isinstance(doc, dict) or doc.get("format_version") != "far-ir/2.0":
        raise PilotError("source format mismatch")
    return doc


def verify(doc):
    result = _validate_contract(doc)
    if not result.success:
        return "INVALID"
    outcome = doc.get("report", {}).get("outcome")
    return outcome if outcome in ("PROVED", "REFUTED") else "INVALID"


def execute(case, arm, p, decision=None):
    doc = source_document(case)
    before = time.perf_counter_ns()
    if arm == "deterministic":
        action, outcome = "verify_current", verify(doc)
    elif arm == "declarative":
        steps = p["workflow"][doc["format_version"]]
        if steps != ["verify_current"]:
            raise PilotError("unapproved declarative workflow")
        action, outcome = steps[0], verify(doc)
    elif arm == "agent":
        if decision not in ("verify", "abstain"):
            raise PilotError("agent decision must be verified externally")
        action = decision
        outcome = verify(doc) if decision == "verify" else "NO_VERDICT"
    else:
        raise PilotError("unknown arm")
    return {"case_id": case["id"], "arm": arm, "source_blob_sha": case["blob_sha"],
            "action": action, "outcome": outcome, "correct": outcome == case["expected"],
            "elapsed_ms": (time.perf_counter_ns() - before) / 1_000_000,
            "provenance": "SCRIPTED_REPLAY" if arm == "agent" else "LOCAL_DETERMINISTIC"}


def smoke(p):
    cases = {c["id"]: c for c in p["cases"]}
    rows = [execute(cases[cell["case_id"]], cell["arm"], p)
            for cell in plan(p) if cell["arm"] != "agent"]
    wrong = [r for r in rows if not r["correct"]]
    return {"status": "LOCAL_SMOKE_ONLY", "runs": len(rows), "correct": len(rows) - len(wrong),
            "failures": wrong, "model_runs": 0, "claim": "NOT_ESTABLISHED"}


def replay(p, decisions):
    if type(decisions) is not dict or set(decisions) != {c["id"] for c in p["cases"]}:
        raise PilotError("agent decision case set mismatch")
    cases = {c["id"]: c for c in p["cases"]}
    rows = [execute(cases[cell["case_id"]], cell["arm"], p,
                    decisions[cell["case_id"]] if cell["arm"] == "agent" else None)
            for cell in plan(p)]
    return {"status": "SCRIPTED_REPLAY_ONLY", "records": rows,
            "model_runs": 0, "claim": "NOT_ESTABLISHED"}


def analyze(p, rows):
    if not isinstance(rows, list) or len(rows) != 36:
        raise PilotError("36 records required")
    cases = {c["id"]: c for c in p["cases"]}
    expected = {(c["id"], a) for c in p["cases"] for a in ARMS}
    got, agent_types = {}, set()
    for r in rows:
        if not isinstance(r, dict):
            raise PilotError("record not an object")
        identity = (r.get("case_id"), r.get("arm"))
        if identity not in expected or identity in got:
            raise PilotError("duplicate or unexpected run")
        c = cases[identity[0]]
        if r.get("source_blob_sha") != c["blob_sha"]:
            raise PilotError("source mismatch")
        if r.get("outcome") not in ("PROVED", "REFUTED", "INVALID", "NO_VERDICT"):
            raise PilotError("invalid outcome")
        # Independently recompute what the pinned, shared verifier would output.
        # A record claiming abstention cannot also claim a successful verdict.
        action = r.get("action")
        if identity[1] == "agent":
            if action not in ("verify", "abstain"):
                raise PilotError("unrecognized agent action")
            expected_outcome = "NO_VERDICT" if action == "abstain" else verify(source_document(c))
        else:
            if action != "verify_current":
                raise PilotError("fixed-policy action mismatch")
            expected_outcome = verify(source_document(c))
        if r["outcome"] != expected_outcome:
            raise PilotError("action-outcome mismatch")
        if type(r.get("correct")) is not bool or r["correct"] != (r["outcome"] == c["expected"]):
            raise PilotError("correctness tampering")
        ms = r.get("elapsed_ms")
        if type(ms) not in (float, int) or not math.isfinite(ms) or ms < 0:
            raise PilotError("invalid runtime")
        if identity[1] == "agent":
            origin = r.get("provenance")
            if origin not in ("SCRIPTED_REPLAY", "MODEL_REPORTED"):
                raise PilotError("unrecognized agent provenance")
            agent_types.add(origin)
            if origin == "MODEL_REPORTED" and (
                    not isinstance(r.get("model_id"), str) or not r["model_id"].strip()
                    or not isinstance(r.get("model_response_sha256"), str)
                    or len(r["model_response_sha256"]) != 64
                    or type(r.get("total_tokens")) is not int or r["total_tokens"] <= 0):
                raise PilotError("missing model-report metadata")
        elif r.get("provenance") != "LOCAL_DETERMINISTIC":
            raise PilotError("mismatched fixed-policy provenance")
        got[identity] = r
    if len(agent_types) != 1:
        raise PilotError("mixed agent evidence classes")
    metrics = {a: {"correct": sum(got[(c["id"], a)]["correct"] for c in p["cases"]),
                   "total": 12,
                   "mean_elapsed_ms": sum(got[(c["id"], a)]["elapsed_ms"] for c in p["cases"]) / 12}
               for a in ARMS}
    return {"status": "SCRIPTED_REPLAY_ONLY" if "SCRIPTED_REPLAY" in agent_types
            else "UNVERIFIED_MODEL_REPORTS",
            "metrics": metrics, "claim": "NOT_ESTABLISHED"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("schedule", "smoke", "replay", "analyze"))
    parser.add_argument("--decisions", type=Path)
    parser.add_argument("--records", type=Path)
    args = parser.parse_args(argv)
    try:
        p = load()
        if args.command == "schedule":
            result = {"status": "FROZEN_PLAN", "plan": plan(p)}
        elif args.command == "smoke":
            result = smoke(p)
        elif args.command == "replay":
            if args.decisions is None:
                raise PilotError("--decisions is required")
            result = replay(p, json.loads(args.decisions.read_text(encoding="utf-8")))
        else:
            if args.records is None:
                raise PilotError("--records is required")
            result = analyze(p, json.loads(args.records.read_text(encoding="utf-8")))
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1 if args.command == "smoke" and result["failures"] else 0
    except (PilotError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc),
                          "claim": "NOT_ESTABLISHED"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
