#!/usr/bin/env python3
"""FAR-REPLAN-001 candidate audit and scored-run launch gate.

Never convert a candidate source or a worker's claimed outcome into independent
scientific evidence. This module is an offline protocol guard and cannot itself
attest independent authorship, execution, provider identity, or reviewer intent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from tools import replanning_evaluation_contract as contract
from tools import workflow_efficacy_internal_fixtures as fixtures

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE = ROOT / "research/workflow-efficacy/replanning-candidate-cohort-v1.json"
DEFAULT_PROTOCOL = ROOT / "research/workflow-efficacy/replanning-protocol-v1.json"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
ARMS = ("control", "replanning")
CANDIDATE_KEYS = {
    "schema", "study_id", "status", "origin", "source_path", "source_git_blob_sha1",
    "selection_rule", "selected_indices", "interrupted_indices", "interruption",
    "reference_code", "model_candidate", "model_digest_candidate",
    "independent_oracle_approved", "independent_cohort_approved", "cohort_frozen",
    "provider_currently_attested", "scored_run_authorized", "scored_runs_executed",
    "limitations",
}
EXPECTED_SELECTION = "First 12 of 30 indices sorted by SHA256(UTF8('FAR-REPLAN-001|FWE-' + 3-digit one-based index)); compare raw digest bytes and break ties by index"
EXPECTED_INTERRUPTION = "On the first attempted solution.py write only, a host-declared, one-shot transient tool error aborts the current worker. Fault is identical across both arms, seeded before allocation; the replanning arm may recover through a distinct budgeted agent invocation."


class GateError(ValueError):
    """A prelaunch condition does not hold; do not start scored execution."""


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    out = {}
    for key, value in pairs:
        if key in out:
            raise GateError("duplicate JSON key: " + key)
        out[key] = value
    return out


def read_json(path: Path, *, max_size: int = 131072) -> tuple[dict, str]:
    raw = path.read_bytes()
    if not raw or len(raw) > max_size:
        raise GateError("missing or oversized manifest")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs,
                          parse_constant=lambda v: (_ for _ in ()).throw(GateError("nonfinite JSON: " + v)))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise GateError("invalid manifest JSON") from exc
    if type(data) is not dict:
        raise GateError("manifest must be an object")
    return data, digest(raw)


def task_selection() -> list[int]:
    def key(i: int):
        value = f"FAR-REPLAN-001|FWE-{i+1:03d}".encode("ascii")
        return hashlib.sha256(value).digest(), i
    return sorted(range(30), key=key)[:12]


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def check_candidate(path: Path = DEFAULT_CANDIDATE, *, repo_root: Path = ROOT) -> dict:
    data, manifest_sha = read_json(path)
    if set(data) != CANDIDATE_KEYS:
        raise GateError("candidate manifest keys differ from contract")
    for key, expected in {
        "schema": "far-replanning-candidate-cohort/1", "study_id": "FAR-REPLAN-001",
        "status": "Research-candidate-unsealed",
        "source_path": "tools/workflow_efficacy_internal_fixtures.py",
        "selection_rule": EXPECTED_SELECTION,
        "interruption": EXPECTED_INTERRUPTION,
        "reference_code": "tools/workflow_efficacy_free_agent.py::grade",
        "model_candidate": "qwen2.5-coder:7b",
        "model_digest_candidate": "dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364",
        "independent_oracle_approved": False,
        "independent_cohort_approved": False,
        "cohort_frozen": False,
        "provider_currently_attested": False,
        "scored_run_authorized": False,
        "scored_runs_executed": 0,
    }.items():
        if type(data.get(key)) is not type(expected) or data[key] != expected:
            raise GateError(f"candidate {key} drift")
    if type(data["origin"]) is not str or "prior different-model evaluation" not in data["origin"]:
        raise GateError("missing prior-study disclosure")
    limits = data["limitations"]
    if type(limits) is not list or len(limits) < 4 or any(type(x) is not str or not x.strip() for x in limits):
        raise GateError("candidate limitations missing")
    indices = data["selected_indices"]
    if type(indices) is not list or any(type(i) is not int or i < 0 or i >= 30 for i in indices):
        raise GateError("bad candidate indices")
    if indices != task_selection() or len(set(indices)) != 12:
        raise GateError("candidate selection is not deterministic or complete")
    if data["interrupted_indices"] != indices[::2] or any(type(i) is not int for i in data["interrupted_indices"]):
        raise GateError("interruption assignment drift")
    source = (repo_root / data["source_path"]).read_bytes()
    if type(data["source_git_blob_sha1"]) is not str or not HEX40.fullmatch(data["source_git_blob_sha1"]):
        raise GateError("invalid source blob SHA")
    if git_blob_sha(source) != data["source_git_blob_sha1"]:
        raise GateError("underlying fixture source changed")
    rows = []
    for i in indices:
        t = fixtures.task(i)
        row = {
            "task_id": t["task_id"], "fixture_index": i,
            "source_sha256": digest(t["source"].encode("utf-8")),
            "spec_sha256": digest(t["spec"].encode("utf-8")),
            "oracle_sha256": digest(canonical({"public": t["public"], "hidden": t["hidden"]})),
            "interrupted": i in data["interrupted_indices"],
        }
        rows.append(row)
    return {"status": "CANDIDATE_NOT_FROZEN", "study_id": data["study_id"],
            "candidate_sha256": manifest_sha, "source_blob_sha1": data["source_git_blob_sha1"],
            "source_sha256": digest(source), "task_rows": rows,
            "cohort_content_sha256": digest(canonical(rows)), "task_count": len(rows),
            "scored_execution_authorized": False, "independent_authority": "NOT_ESTABLISHED"}


def require_launch_manifest(candidate: dict, manifest_path: Path | None, *,
                            protocol_path: Path = DEFAULT_PROTOCOL) -> dict:
    """Refuse all scored invocations absent a separately sealed launch manifest.

    Even a structurally valid launch manifest does not cryptographically prove
    independence: external signed/approved evidence must be assessed separately.
    """
    if manifest_path is None:
        raise GateError("SCORING_BLOCKED: no independently sealed execution manifest")
    p, protocol_sha = contract.load(protocol_path)
    if p["study_id"] != candidate["study_id"]:
        raise GateError("protocol/candidate study mismatch")
    m, m_sha = read_json(manifest_path)
    fields = set(p["execution_manifest"]["required_fields"])
    required = fields | {"study_id", "schema", "status", "candidate_cohort_sha256",
                         "cohort_content_sha256", "task_ids_frozen_before_seed",
                         "oracles_frozen_before_seed", "frozen_protocol_digest_verified",
                         "protected_main_evidence", "external_launch_authorization_receipt"}
    if set(m) != required:
        raise GateError("execution manifest keys differ from preregistration")
    if m["schema"] != "far-replanning-launch/1" or m["study_id"] != candidate["study_id"]:
        raise GateError("wrong execution manifest")
    if m["status"] != "Research-external-review-required":
        raise GateError("manifest is not at a reviewable launch stage")
    if m["protocol_sha256"] != protocol_sha or m["candidate_cohort_sha256"] != candidate["candidate_sha256"]:
        raise GateError("protocol or candidate manifest unbound")
    if m["cohort_content_sha256"] != candidate["cohort_content_sha256"]:
        raise GateError("cohort content unbound")
    if m["cohort_manifest_sha256"] != candidate["candidate_sha256"]:
        raise GateError("cohort source SHA mismatch")
    for key in ("task_ids_frozen_before_seed", "oracles_frozen_before_seed", "frozen_protocol_digest_verified"):
        if m[key] is not True:
            raise GateError("frozen-input claim missing: " + key)
    if type(m["seed_and_origin"]) is not dict or set(m["seed_and_origin"]) != {"seed", "origin", "generated_after_freeze"}:
        raise GateError("allocation seed record malformed")
    seed = m["seed_and_origin"]["seed"]
    if type(seed) is not str or HEX64.fullmatch(seed) is None or m["seed_and_origin"]["generated_after_freeze"] is not True:
        raise GateError("allocation seed or freeze ordering invalid")
    if type(m["seed_and_origin"]["origin"]) is not str or not m["seed_and_origin"]["origin"].strip():
        raise GateError("allocation seed origin missing")
    task_map = {x["task_id"]: x["source_sha256"] for x in candidate["task_rows"]}
    oracle_map = {x["task_id"]: x["oracle_sha256"] for x in candidate["task_rows"]}
    if m["source_sha_per_task"] != task_map or m["oracle_sha256_per_task"] != oracle_map:
        raise GateError("task source/oracle hash drift")
    for key in ("control_adapter_sha", "replanning_adapter_sha", "model_manifest_sha256",
                "prompt_and_tools_sha256", "container_image_digest", "interruption_schedule_sha256"):
        if type(m[key]) is not str or HEX64.fullmatch(m[key]) is None:
            raise GateError("invalid SHA for " + key)
    for key in ("protected_main_registration_sha", "independent_reviewer_identity", "protected_main_evidence",
                "external_launch_authorization_receipt", "isolation_and_permissions"):
        v = m[key]
        if type(v) is not str or not v.strip():
            raise GateError("missing reviewer, protection or environment: " + key)
    if type(m["protected_main_registration_sha"]) is not str or HEX40.fullmatch(m["protected_main_registration_sha"]) is None:
        raise GateError("invalid protected-main SHA")
    schedule = contract.assignment_schedule(seed, list(task_map))
    # A manifest can claim review/authentication, but does not prove either.
    return {"status": "STRUCTURALLY_READY_EXTERNAL_ATTESTATION_UNVERIFIED",
            "study_id": p["study_id"], "execution_manifest_sha256": m_sha,
            "schedule": schedule, "launch_approved_by_this_validator": False}


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    cli.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    cli.add_argument("--manifest", type=Path)
    args = cli.parse_args(argv)
    try:
        c = check_candidate(args.candidate)
        if args.manifest is not None:
            result = require_launch_manifest(c, args.manifest, protocol_path=args.protocol)
        else:
            result = c
    except (GateError, contract.ContractError, OSError, ValueError) as exc:
        print("BLOCKED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
