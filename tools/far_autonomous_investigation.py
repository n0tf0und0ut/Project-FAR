"""Bounded live FAR investigation with real evidence, governed intake, and verifier calls.

This is not a general-purpose fact checker. It investigates a literal GitHub
release-tag claim under TWO preserved meanings of "latest". Current FAR
implementations validate the frozen intake and downstream finite contracts.
The optional local model chooses *proposed* actions, never verdicts or tool args.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mechanization.far_mechanization.intake_v1 import (
    aggregate_manifest, freeze_manifest, new_manifest, sha256_json, sha256_text, validate_manifest,
)
from mechanization.far_mechanization.contract_v2_strict_v11 import contract_sha256
from tools.far_routing_dispatch import _parse, route_text
from tools.far_uncertain_routing_pilot import MODEL_SHA256, sha256_file, persist as persist_json

REPO = "n0tf0und0ut/Project-FAR"
CLAIMED = "v1.0.0"
QUESTION = f"Is the latest release tag of {REPO} {CLAIMED}?"
URLS = {
    "latest": f"https://api.github.com/repos/{REPO}/releases/latest",
    "list": f"https://api.github.com/repos/{REPO}/releases?per_page=10",
}
ACTIONS = ("FETCH_LATEST", "FETCH_LIST", "REFETCH_ALL", "DISCOVER_CONTRACT",
           "FREEZE", "VERIFY_CONTRACT", "AGGREGATE")
SYSTEM = (
    "You are a bounded investigator choosing one safe next ACTION, not a truth verdict. "
    "Use exactly one of the allowed next actions supplied to you. "
    "Return only the uppercase action token. Never assume a source has been retrieved "
    "until the observed state says so."
)
MODEL_ENDPOINT = "http://127.0.0.1:8085/v1/chat/completions"
MAX_BYTES = 2_000_000


class InvestigationError(ValueError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def fetch(source: str) -> tuple[bytes, str]:
    """GET one of two fixed URLs. No network location comes from model/source text."""
    if source not in URLS:
        raise InvestigationError("source not allowlisted")
    url = URLS[source]
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "api.github.com":
        raise InvestigationError("network destination drift")
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *_args, **_kwargs):
            raise InvestigationError("redirect refused")
    opener = urllib.request.build_opener(NoRedirect())
    request = urllib.request.Request(
        url, headers={"Accept": "application/vnd.github+json",
                      "User-Agent": "Project-FAR-bounded-research/0.1",
                      "X-GitHub-Api-Version": "2022-11-28"},
        method="GET",
    )
    try:
        with opener.open(request, timeout=25) as response:
            if response.status != 200:
                raise InvestigationError("GitHub API non-200")
            data = response.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                raise InvestigationError("source exceeds size ceiling")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        raise InvestigationError("source fetch failed: " + type(exc).__name__) from exc
    if not data:
        raise InvestigationError("empty source")
    return data, now()


def parse_source(name: str, raw: bytes) -> dict:
    try:
        document = _parse(raw.decode("utf-8", errors="strict"))
    except (ValueError, UnicodeError) as exc:
        raise InvestigationError("source not strict JSON: " + type(exc).__name__) from exc
    if name == "latest":
        if not isinstance(document, dict):
            raise InvestigationError("latest release response not object")
        item = document
    elif name == "list":
        if not isinstance(document, list) or not document or len(document) > 10:
            raise InvestigationError("release listing response invalid")
        item = document[0]
    else:
        raise InvestigationError("unrecognized source")
    if (not isinstance(item, dict) or type(item.get("tag_name")) is not str
            or not item["tag_name"] or type(item.get("id")) is not int
            or item["id"] <= 0 or type(item.get("draft")) is not bool
            or type(item.get("prerelease")) is not bool):
        raise InvestigationError("release metadata incomplete")
    if item["draft"]:
        raise InvestigationError("draft release returned for public search")
    return {"id": item["id"], "tag_name": item["tag_name"],
            "draft": item["draft"], "prerelease": item["prerelease"]}


def pointer_leaves(value: object, path: str = "") -> list[tuple[str, object]]:
    if isinstance(value, dict) and value:
        return [pair for k, item in value.items()
                for pair in pointer_leaves(item, path + "/" + k.replace("~", "~0").replace("/", "~1"))]
    if isinstance(value, list) and value:
        return [pair for j, item in enumerate(value)
                for pair in pointer_leaves(item, path + "/" + str(j))]
    return [(path, value)]


def term(ident: str, surface: str, interpretation_ids: list[str]) -> dict:
    return {
        "id": ident, "surface": surface, "material": True,
        "interpretation_ids": interpretation_ids, "materiality_basis": "RAW_INPUT",
        "materiality_source_ids": [],
        "materiality_derivation": "Changing this term changes the exact release-tag comparison or the selected source API.",
        "effect_if_misclassified": "A conflicting release tag or source interpretation could be omitted.",
    }


def contract_core(source_id: str, tag: str) -> dict:
    """Build an exact FAR finite-contract CORE, without pre-freeze outcome evidence."""
    return {
        "id": "research.release." + source_id, "contract_version": "2.0", "mode": "exact",
        "source_domain": {
            "status": "EXPLICIT", "kind": "finite_explicit",
            "description": "Literal tag claim and one retrieved GitHub release metadata projection.",
            "cases": [
                {"id": "case.claim", "value": {"tag": CLAIMED, "origin": "preserved user question"}},
                {"id": "case.observed", "value": {"tag": tag, "origin": source_id}},
            ],
        },
        "required_behavior": {
            "status": "EXPLICIT", "description": "Exact equality of the two recorded release tag strings.",
            "table": [{"case_id": "case.claim", "value": CLAIMED},
                      {"case_id": "case.observed", "value": tag}],
        },
        "representation": {
            "status": "EXPLICIT", "description": "Test a common release-tag equivalence class.",
            "table": [{"case_id": "case.claim", "value": "same-release"},
                      {"case_id": "case.observed", "value": "same-release"}],
        },
        "observation_contexts": [
            {"id": "obs.tag", "description": "Literal GitHub API tag equality", "status": "EXPLICIT"}
        ],
        "admitted_transformations": [
            {"id": "eq.identity", "kind": "equivalence",
             "description": "Literal string identity; no normalization", "status": "EXPLICIT"}
        ],
        "interpretation_profile": {
            "id": "interp." + source_id, "description": "GitHub release " + source_id
            + " endpoint snapshot, not a global release history.", "status": "EXPLICIT"
        },
        "target_model_class": {
            "id": "target.two", "description": "These two values and only these two.",
            "status": "EXPLICIT"
        },
        "frame": {
            "id": "frame.empty", "description": "No external release assumptions.", "status": "EXPLICIT"
        },
    }


def build_intake(receipts: dict[str, dict], *, cutoff: str,
                 round1: str, round2: str) -> dict:
    if set(receipts) != set(URLS):
        raise InvestigationError("both evidence sources required before contract discovery")
    m = new_manifest(QUESTION, "FAR-LIVE-RELEASE-001")
    d = m["discovery"]
    d["claim_parses"] = [{
        "id": "parse.release", "statement": "The 'latest' repository release tag equals v1.0.0.",
        "term_ids": ["term.latest", "term.tag"], "origin": "SURFACE", "derivation": None,
    }]
    d["terms"] = [
        term("term.latest", "latest", ["interp.latest", "interp.list"]),
        term("term.tag", CLAIMED, ["interp.claimed"]),
    ]
    d["sources"] = [
        {"id": "src." + name, "locator": URLS[name], "sha256": receipt["sha256"],
         "source_type": "PRIMARY", "retrieved_at": receipt["retrieved_at"],
         "scope": "Public GitHub REST release metadata; first response item only for listing."}
        for name, receipt in sorted(receipts.items())
    ]
    d["interpretations"] = [
        {"id": "interp.latest", "term_id": "term.latest",
         "statement": "Latest release endpoint reports tag " + receipts["latest"]["parsed"]["tag_name"],
         "origin": "SOURCE_EXPLICIT", "source_ids": ["src.latest"],
         "derivation": None, "scope": "GitHub API latest endpoint"},
        {"id": "interp.list", "term_id": "term.latest",
         "statement": "First release-list item reports tag " + receipts["list"]["parsed"]["tag_name"],
         "origin": "SOURCE_EXPLICIT", "source_ids": ["src.list"],
         "derivation": None, "scope": "GitHub API first release-list item"},
        {"id": "interp.claimed", "term_id": "term.tag",
         "statement": "The literal user assertion is " + CLAIMED,
         "origin": "INFERENCE", "source_ids": [],
         "derivation": "Literal tag extracted from the preserved input without spelling normalization.",
         "scope": "Preserved user question"},
    ]
    d["assumptions"] = [
        {"id": "asm.scope", "statement": "This comparison is restricted to two GitHub public REST response projections.",
         "status": "EXPLICIT", "source_ids": ["src.latest", "src.list"],
         "effect_if_false": "Other sources or time periods may report different tags."},
        {"id": "asm.mapping", "statement": "FAR exact finite factorization is used only as an equality check, not external source authentication.",
         "status": "EXPLICIT", "source_ids": [],
         "effect_if_false": "A larger causal or provenance claim would require other evidence."},
    ]
    d["search_protocol"] = {
        "evidence_cutoff": cutoff,
        "queries": [
            {"id": "q.latest", "query": URLS["latest"], "target": "latest GitHub release tag",
             "source_scope": "GitHub public release metadata", "term_ids": ["term.latest", "term.tag"],
             "claim_parse_ids": ["parse.release"]},
            {"id": "q.list", "query": URLS["list"], "target": "first release-list entry tag",
             "source_scope": "GitHub public release metadata", "term_ids": ["term.latest", "term.tag"],
             "claim_parse_ids": ["parse.release"]},
        ],
        "stopping_rule": "Two exact registered GitHub endpoints re-fetched; stop only if both semantic projections match the first pass.",
        "saturation_observations": [
            {"round": 1, "observed_at": round1, "query_ids": ["q.latest", "q.list"],
             "source_ids": ["src.latest", "src.list"], "new_claim_parse_ids": [],
             "new_material_interpretation_ids": ["interp.latest", "interp.list"]},
            {"round": 2, "observed_at": round2, "query_ids": ["q.latest", "q.list"],
             "source_ids": ["src.latest", "src.list"], "new_claim_parse_ids": [],
             "new_material_interpretation_ids": []},
        ],
        "limitations": [
            "Two correlated GitHub publisher API surfaces, not independent witnesses.",
            "Bounded instant of retrieval, not global release history or maximum semantic-version claim.",
            "The first release-list element is not necessarily a stable latest-release definition.",
            "Zero-new means only that both recorded projections were unchanged on refetch.",
        ],
    }
    for name in ("latest", "list"):
        core = contract_core(name, receipts[name]["parsed"]["tag_name"])
        source = "src." + name
        provenance = []
        for path, value in pointer_leaves(core):
            if path in (
                "/required_behavior/table/1/value",
                "/source_domain/cases/1/value/tag",
            ):
                basis, src_ids, interp_ids = "SOURCE", [source], []
            elif path in (
                "/source_domain/cases/0/value/tag",
                "/required_behavior/table/0/value",
            ):
                basis, src_ids, interp_ids = "RAW_INPUT", [], []
            elif path.startswith("/interpretation_profile/"):
                basis, src_ids, interp_ids = "INTERPRETATION", [], ["interp." + name]
            else:
                basis, src_ids, interp_ids = "INFERENCE", [], []
            provenance.append({
                "path": path, "basis": basis, "source_ids": src_ids,
                "interpretation_ids": interp_ids, "assumption_ids": [],
                "derivation": "Finite equality-contract construction from preserved claim and named source, with declared bounded comparison semantics.",
            })
        d["contract_candidates"].append({
            "id": "contract." + name, "claim_parse_id": "parse.release",
            "assignments": {"term.latest": "interp." + name, "term.tag": "interp.claimed"},
            "contract": core, "sha256": sha256_json(core), "parameter_provenance": provenance,
        })
    errors = validate_manifest(m, require_complete=True)
    if errors:
        raise InvestigationError("governed discovery failed validation: " + "; ".join(errors))
    return m


def far_document(frozen: dict, candidate: dict, receipts: dict, timestamp: str) -> dict:
    """Only now, *after* intake freeze, synthesize the submitted finite witness."""
    if frozen["freeze"]["status"] != "FROZEN" or validate_manifest(frozen):
        raise InvestigationError("candidate cannot be evaluated before valid freeze")
    core = copy.deepcopy(candidate["contract"])
    if sha256_json(core) != candidate["sha256"]:
        raise InvestigationError("frozen candidate altered")
    observed = core["required_behavior"]["table"][1]["value"]
    same = CLAIMED == observed
    if same:
        outcome = "PROVED"
        evidence = {"kind": "factorization", "status": "CHECKED_FINITE_EXPLICIT",
                    "decoder_table": [{"representation_value": "same-release", "behavior_value": CLAIMED}]}
        failure = []
    else:
        outcome = "REFUTED"
        evidence = {"kind": "collision", "status": "CHECKED_FINITE_EXPLICIT",
                    "left_case_id": "case.claim", "right_case_id": "case.observed"}
        failure = ["The constant representation merges different literal release tag values."]
    return {
        "format_version": "far-ir/2.0",
        "id": core["id"] + ".evaluation",
        "contract": core,
        "report": {"outcome": outcome, "evidence": evidence, "failure_report": failure},
        "provenance": {
            "producer": "Project FAR bounded live GitHub release investigation",
            "created_at": timestamp,
            "sources": [URLS["latest"], URLS["list"]],
        },
        "freeze": {
            "status": "FROZEN", "frozen_at": frozen["freeze"]["frozen_at"],
            "contract_sha256": contract_sha256(core),
        },
    }


def _allowed(state: dict) -> list[str]:
    if not state["receipts"]:
        return ["FETCH_LATEST", "FETCH_LIST"]
    if len(state["receipts"]) < 2:
        return ["FETCH_LIST" if "latest" in state["receipts"] else "FETCH_LATEST"]
    if not state["rechecked"]:
        return ["REFETCH_ALL"]
    if state["intake"] is None:
        return ["DISCOVER_CONTRACT"]
    if state["frozen"] is None:
        return ["FREEZE"]
    if len(state["evaluations"]) < 2:
        return ["VERIFY_CONTRACT"]
    return ["AGGREGATE"]


def request_model_action(prompt: str) -> dict:
    """Independent tool-routing prompt, not the previous ASK_SCOPE-only pilot prompt."""
    data = {
        "model": "Qwen2.5-0.5B-Instruct-Q4_K_M",
        "temperature": 0, "stream": False, "max_tokens": 32,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": prompt}],
    }
    request_bytes = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(
        MODEL_ENDPOINT, request_bytes,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            if res.status != 200:
                raise InvestigationError("loopback model returned non-200")
            response_bytes = res.read(1024 * 1024 + 1)
            if len(response_bytes) > 1024 * 1024:
                raise InvestigationError("model response exceeds size ceiling")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        raise InvestigationError("loopback model unavailable: " + type(exc).__name__) from exc
    try:
        parsed = _parse(response_bytes.decode("utf-8"))
        answer = parsed["choices"][0]["message"]["content"]
        tokens = parsed["usage"]["total_tokens"]
        model_id = parsed["model"]
    except (IndexError, KeyError, ValueError, TypeError, UnicodeError) as exc:
        raise InvestigationError("malformed loopback model completion") from exc
    if not isinstance(answer, str) or type(tokens) is not int or tokens < 1 or not isinstance(model_id, str):
        raise InvestigationError("invalid loopback model telemetry")
    return {
        "action": answer.strip(), "raw_choice": answer,
        "total_tokens": tokens, "model": model_id,
        "request": data, "raw_response_base64": base64.b64encode(response_bytes).decode("ascii"),
        "request_sha256": sha(request_bytes), "response_sha256": sha(response_bytes),
    }


def choose_action(state: dict, mode: str, model: Callable[[str], dict] | None) -> tuple[str, dict]:
    allowed = _allowed(state)
    if mode == "deterministic":
        return allowed[0], {"mode": mode, "proposed": None, "override_reason": None, "tokens": 0}
    if mode != "model":
        raise InvestigationError("invalid investigator mode")
    if model is None:
        raise InvestigationError("model mode requires actual inference callable")
    prompt = (QUESTION + "\nTools available right now: " + ", ".join(allowed)
              + "\nRetrieved: " + ", ".join(sorted(state["receipts"]))
              + "\nFreeze: " + ("yes" if state["frozen"] else "no")
              + "\nCompleted verifications: " + str(len(state["evaluations"])))
    event = model(prompt)
    proposal = str(event.get("raw_choice", event.get("action", ""))).strip()
    if type(event.get("total_tokens")) is not int or event["total_tokens"] < 1:
        raise InvestigationError("invalid model usage metadata")
    actual = proposal if proposal in allowed else allowed[0]
    return actual, {
        "mode": mode, "proposed": proposal,
        "override_reason": None if proposal == actual else "NOT_AN_ELIGIBLE_ACTION",
        "tokens": event["total_tokens"],
        "request_sha256": event.get("request_sha256"),
        "response_sha256": event.get("response_sha256"),
        "raw_model_event": event,
    }


def execute(mode: str, fetcher: Callable[[str], tuple[bytes, str]] = fetch,
            model: Callable[[str], dict] | None = None, checkpoint=None) -> dict:
    """Sequential real-tool chain, with stage-level evidence and bounded model proposals."""
    if mode not in ("deterministic", "model"):
        raise InvestigationError("mode not recognized")
    state: dict = {
        "schema": "far-live-investigation/0.1", "mode": mode,
        "scope": QUESTION, "status": "INCOMPLETE",
        "receipts": {}, "rechecks": [], "rechecked": False,
        "intake": None, "frozen": None, "evaluations": [],
        "aggregate": None, "actions": [], "verifier_calls": 0,
        "model_proposals": 0, "controller_overrides": 0,
        "model_tokens": 0,
    }
    def save():
        if checkpoint is not None:
            checkpoint(copy.deepcopy(state))
    save()
    for _ in range(12):
        allowed_before = _allowed(state)
        action, choice = choose_action(state, mode, model)
        if action not in allowed_before:
            raise InvestigationError("invalid actual tool transition")
        state["model_tokens"] += choice["tokens"]
        if choice["proposed"] is not None:
            state["model_proposals"] += 1
        if choice["override_reason"]:
            state["controller_overrides"] += 1
        trace = {"step": len(state["actions"]) + 1, "available": allowed_before,
                 "actual": action, "choice": choice, "executed_at": now(),
                 "status": "STARTED"}
        state["actions"].append(trace)
        save()
        if action in ("FETCH_LATEST", "FETCH_LIST"):
            key = "latest" if action == "FETCH_LATEST" else "list"
            raw, stamp = fetcher(key)
            parsed = parse_source(key, raw)
            state["receipts"][key] = {
                "url": URLS[key], "raw_base64": base64.b64encode(raw).decode("ascii"),
                "sha256": sha(raw), "retrieved_at": stamp, "parsed": parsed,
            }
        elif action == "REFETCH_ALL":
            for key in ("latest", "list"):
                raw, stamp = fetcher(key)
                parsed = parse_source(key, raw)
                state["rechecks"].append({
                    "source": key, "url": URLS[key], "sha256": sha(raw),
                    "retrieved_at": stamp, "parsed": parsed,
                    "raw_base64": __import__("base64").b64encode(raw).decode("ascii"),
                })
                save()
                if parsed != state["receipts"][key]["parsed"]:
                    raise InvestigationError("source projection changed during bounded recheck: " + key)
            state["round1"] = max(x["retrieved_at"] for x in state["receipts"].values())
            state["round2"] = max(x["retrieved_at"] for x in state["rechecks"])
            state["cutoff"] = now()
            state["rechecked"] = True
        elif action == "DISCOVER_CONTRACT":
            state["intake"] = build_intake(state["receipts"], cutoff=state["cutoff"],
                                           round1=state["round1"], round2=state["round2"])
        elif action == "FREEZE":
            state["frozen"] = freeze_manifest(state["intake"])
            if validate_manifest(state["frozen"]):
                raise InvestigationError("governed freeze invalid after writing")
        elif action == "VERIFY_CONTRACT":
            c = state["frozen"]["discovery"]["contract_candidates"][len(state["evaluations"])]
            stamp = now()
            document = far_document(state["frozen"], c, state["receipts"], stamp)
            result = route_text(json.dumps(document, separators=(",", ":"), sort_keys=True))
            state["verifier_calls"] += 1
            if result["status"] != "VERIFIED_EXPLICIT_CONTRACT" or not result["verifier_success"]:
                raise InvestigationError("current FAR verifier rejected generated frozen contract: " + str(result))
            state["evaluations"].append({
                "contract_id": c["id"], "contract_sha256": c["sha256"],
                "freeze_sha256": state["frozen"]["freeze"]["freeze_sha256"],
                "outcome": result["outcome"], "evaluated_at": now(),
                "evidence_refs": ["urn:sha256:" + state["receipts"][
                    "latest" if c["id"] == "contract.latest" else "list"]["sha256"]],
                "verified_document": document, "verifier_result": result,
            })
        elif action == "AGGREGATE":
            final = copy.deepcopy(state["frozen"])
            final["evaluations"] = [
                {key: row[key] for key in
                 ("contract_id", "contract_sha256", "freeze_sha256",
                  "outcome", "evaluated_at", "evidence_refs")}
                for row in state["evaluations"]
            ]
            if validate_manifest(final):
                raise InvestigationError("post-verification manifest invalid")
            aggregate = aggregate_manifest(final)
            if aggregate["outcome"] not in (
                "INVARIANTLY_PROVED", "INVARIANTLY_REFUTED", "CONTRACT_SENSITIVE",
                "UNDERDETERMINED",
            ):
                raise InvestigationError("aggregate invalid or incomplete")
            state["frozen"] = final
            state["aggregate"] = aggregate
            state["status"] = "BOUNDED_INVESTIGATION_COMPLETED"
        trace["status"] = "COMPLETED"
        trace["finished_at"] = now()
        save()
        if action == "AGGREGATE":
            return state
    raise InvestigationError("bounded 12-step action budget exceeded")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run",))
    parser.add_argument("--mode", choices=("model", "deterministic"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", type=Path, help="exact SHA-256 pinned GGUF; required for model mode")
    args = parser.parse_args(argv)
    partial = args.output.with_name(args.output.stem + ".partial.json")
    try:
        if args.mode == "model":
            if args.model is None or sha256_file(args.model) != MODEL_SHA256:
                raise InvestigationError("model path missing or GGUF SHA-256 mismatch")
            model = request_model_action
        else:
            model = None
        output = execute(args.mode, model=model, checkpoint=lambda x: persist_json(partial, x))
        persist_json(args.output, output)
        partial.unlink(missing_ok=True)
        print(json.dumps({
            "status": output["status"], "mode": args.mode,
            "verifier_calls": output["verifier_calls"],
            "aggregate": output["aggregate"]["outcome"],
            "model_proposals": output["model_proposals"],
            "controller_overrides": output["controller_overrides"],
        }, sort_keys=True))
        return 0
    except (InvestigationError, ValueError, OSError, TypeError, KeyError) as exc:
        persist_json(args.output.with_name(args.output.stem + ".failure.json"), {
            "status": "FAILED_OR_INCOMPLETE", "error_class": type(exc).__name__,
            "reason": str(exc), "claim": "NOT_ESTABLISHED",
            "partial_exists": partial.exists(),
        })
        print(json.dumps({"status": "FAILED_OR_INCOMPLETE", "error_class": type(exc).__name__,
                          "reason": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
