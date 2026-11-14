"""Fail-closed candidate preregistration and raw-receipt structural checks.

No model/tool runner, task unblinder, external signature trust anchor, or launch grant.
A structurally bound receipt is NOT an authenticated mechanism execution.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROTOCOL = ROOT / "protocol-v0.1.json"
LAUNCH = ROOT / "launch-state-v0.1.json"
EXPECTED_PROTOCOL_BLOB = "f0dd47f81b00ee38168175c6679fcfde69f99c29"
EXPECTED_LAUNCH_BLOB = "954bc82bb84b5feb19e29b28f8c5d2bf1b425e32"
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
TASK = re.compile(r"TASK-[0-9]{6}\Z")
RUN = re.compile(r"[a-zA-Z0-9_.:-]{1,128}\Z")
ARMS = ("generic_checker", "far")
TOOLS = {
    "generic_checker": "generic_checker",
    "far": "far_strict_verifier",
}
DIGEST_FIELDS = (
    "raw_request_sha256", "raw_response_sha256", "raw_continuation_sha256",
    "pre_state_sha256", "post_state_sha256",
)


def reject_duplicates(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON key: " + key)
        out[key] = value
    return out


def bad_constant(value):
    raise ValueError("non-finite JSON constant: " + value)


def exact_json(data: bytes):
    def finite_float(raw: str) -> float:
        value = float(raw)
        if not math.isfinite(value):
            raise ValueError("non-finite JSON number")
        return value

    return json.loads(data.decode("utf-8"), object_pairs_hook=reject_duplicates,
                      parse_constant=bad_constant, parse_float=finite_float)


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def same_keys(obj, fields, label):
    require(type(obj) is dict and set(obj) == set(fields), label + " unexpected/missing keys")


def hash256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def check_candidate(protocol_bytes: bytes, launch_bytes: bytes) -> dict:
    require(git_blob(protocol_bytes) == EXPECTED_PROTOCOL_BLOB,
            "preregistration changed since author candidate was pinned")
    require(git_blob(launch_bytes) == EXPECTED_LAUNCH_BLOB,
            "launch state changed since author candidate was pinned")
    p, gate = exact_json(protocol_bytes), exact_json(launch_bytes)
    # Verify authoritative upstream code and v3 governance from raw checkout bytes.
    repo_root = ROOT.parents[2]
    sources = (
        ("research/external-validation/swe-agent-v3/preregistration-v1.0.json",
         "governed_v3_preregistration_blob"),
        ("research/external-validation/swe-agent-v3/execution-gate-v1.0.json",
         "governed_v3_gate_blob"),
        ("tools/efr_generic_collision_checker.py", "generic_checker_blob"),
        ("mechanization/far_mechanization/contract_v2_strict_v11.py",
         "far_strict_verifier_blob"),
    )
    for source_path, source_key in sources:
        expected = p["prior_evidence"][source_key]
        require(type(expected) is str and re.fullmatch(r"[0-9a-f]{40}", expected),
                "invalid pinned source identity: " + source_key)
        require(git_blob((repo_root / source_path).read_bytes()) == expected,
                "pinned source drift: " + source_path)
    v3p = exact_json((repo_root / sources[0][0]).read_bytes())
    v3g = exact_json((repo_root / sources[1][0]).read_bytes())
    require([arm["id"] for arm in v3p["arms"]] == ["baseline", "placebo", "far"] and
            v3p["primary_contrast"] == "far_minus_placebo",
            "governed v3 design no longer matches baseline")
    require(all(value is False for value in v3g["pilot_gates"].values()) and
            all(value is False for value in v3g["gates"].values()) and
            all(v3g[key] is False for key in (
                "execution_authorized", "model_calls_authorized",
                "benchmark_execution_authorized", "pilot_execution_authorized",
                "confirmatory_execution_authorized")),
            "governed v3 launch state changed; independent reassessment required")
    require(p["program_id"] == gate["program_id"] == "FAR-AGENT-GENERIC-CAUSAL-001",
            "program identity mismatch")
    require(p["status"] == "RESEARCH_CANDIDATE_NOT_FROZEN", "status promoted without review")
    require(p["primary_contrast"] == "far_minus_generic_checker", "wrong causal contrast")
    require([a["id"] for a in p["arms"]] == list(ARMS), "active checker arms changed")
    require(p["arms"][0]["checker"] == "tools/efr_generic_collision_checker.py",
            "generic source changed")
    require(p["arms"][1]["checker"] ==
            "mechanization/far_mechanization/contract_v2_strict_v11.py",
            "FAR source changed")
    require(p["design"]["paired"] is True and
            type(p["design"]["repetitions_per_task_per_arm"]) is int and
            p["design"]["repetitions_per_task_per_arm"] == 2 and
            p["design"]["fixed_confirmatory_tasks"] == 24 and
            p["design"]["fixed_distinct_repositories"] == 6 and
            p["design"]["maximum_tasks_per_repository"] == 4 and
            p["design"]["maximum_fraction_per_repository"] == "1/6" and
            p["primary_endpoint"]["denominator"].startswith("The exactly 24 frozen tasks"),
            "design or denominator changed")
    require(p["statistics"]["minimum_practically_important_absolute_effect"] == "1/10" and
            p["statistics"]["no_posthoc_changes"] is True and
            p["statistics"]["no_pseudoreplication"] is True,
            "statistical commitment changed")
    require(p["mechanism_receipts"]["required_for_every_run"] is True and
            p["mechanism_receipts"]["include_nonactivation_and_errors"] is True and
            p["mechanism_receipts"]["no_posttreatment_activation_filter_for_primary"] is True and
            p["mechanism_receipts"]["expected_tool_ids"] == TOOLS,
            "receipt obligations changed")
    require(p["prior_evidence"]["no_inheritance_of_launch_authorization"] is True and
            p["prior_evidence"]["prior_v3_design_unchanged"] is True,
            "incompatible v3 authority claim")
    require(gate["status"] == "NOT_AUTHORIZED" and
            gate["launch_authorization"] is False,
            "candidate cannot grant execution")
    required_external = (
        "independent_custodian_id", "external_task_seal_manifest_sha256",
        "sealed_identity_ledger_git_blob_sha1", "independent_task_audit_sha256",
        "protocol_reviewed_protected_main_commit", "protocol_hash_sha256",
        "model_endpoint_and_digests_sha256", "agent_and_checker_mounts_sha256",
        "execution_environment_and_budgets_sha256",
        "randomization_seed_commitment_sha256", "sealed_grader_contract_sha256",
        "mechanism_receipt_observer_attestation_sha256",
        "evidence_store_restoration_receipt_sha256",
        "excluded_sacrificial_pilot_completion_sha256",
        "independent_exact_head_review_sha256", "authorized_manual_launch_record_sha256",
    )
    require(all(key in gate and gate[key] is None for key in required_external),
            "external evidence fabricated or changed without review")
    require(len(gate["current_prohibitions"]) >= 5, "launch prohibitions weakened")
    return {
        "status": "RESEARCH_CANDIDATE_VERIFIED_LAUNCH_BLOCKED",
        "program_id": p["program_id"],
        "protocol_git_blob_sha1": git_blob(protocol_bytes),
        "launch_state_git_blob_sha1": git_blob(launch_bytes),
        "external_prerequisites_supplied": 0,
        "external_prerequisites_required": len(required_external),
        "model_calls_authorized": False,
        "independent_review_established": False,
        "task_set_sealed": False,
        "experiment_executed": False,
    }


def _decode_nonempty(value, label) -> bytes:
    require(type(value) is str and bool(value), label + " empty or not text")
    try:
        raw = base64.b64decode(value, validate=True)
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError(label + " invalid base64") from exc
    require(bool(raw) and base64.b64encode(raw).decode("ascii") == value,
            label + " empty or noncanonical base64")
    return raw


def check_receipt(receipt: dict, raw_event_log: bytes) -> str:
    """Validate linkage, never identity authenticity or semantic correctness."""
    fields = (
        "schema", "run_id", "arm", "blind_task_id", "repetition",
        "configuration_root_sha256", "raw_event_log_sha256", "tool_event_index",
        "raw_request_sha256", "raw_response_sha256", "raw_continuation_sha256",
        "pre_state_sha256", "post_state_sha256", "mechanism_status",
        "runtime_attestation_root_sha256",
    )
    same_keys(receipt, fields, "receipt")
    require(receipt["schema"] == "far-agent-mechanism-receipt/1", "receipt schema")
    require(type(receipt["run_id"]) is str and RUN.fullmatch(receipt["run_id"]),
            "invalid run ID")
    require(receipt["arm"] in ARMS, "unknown treatment arm")
    require(type(receipt["blind_task_id"]) is str and TASK.fullmatch(receipt["blind_task_id"]),
            "invalid blind task ID")
    require(type(receipt["repetition"]) is int and receipt["repetition"] in (1, 2),
            "invalid repetition")
    for key in ("configuration_root_sha256", "raw_event_log_sha256",
                "runtime_attestation_root_sha256"):
        require(type(receipt[key]) is str and SHA256.fullmatch(receipt[key]),
                "invalid digest " + key)
    require(hash256(raw_event_log) == receipt["raw_event_log_sha256"],
            "raw observer log digest mismatch")
    log = exact_json(raw_event_log)
    same_keys(log, (
        "schema", "run_id", "arm", "blind_task_id", "repetition",
        "configuration_root_sha256", "events",
    ), "raw log")
    require(log["schema"] == "far-agent-tool-log/1", "raw log schema")
    for key in ("run_id", "arm", "blind_task_id", "repetition", "configuration_root_sha256"):
        require(log[key] == receipt[key] and type(log[key]) is type(receipt[key]),
                "run identity mismatch: " + key)
    require(type(log["events"]) is list, "events must be an array")
    for i, event in enumerate(log["events"]):
        same_keys(event, ("index", "tool_id", "raw_request_b64", "raw_response_b64",
                          "raw_continuation_b64", "pre_state_b64", "post_state_b64"), "event")
        require(type(event["index"]) is int and event["index"] == i,
                "event ordering/duplication")
        require(type(event["tool_id"]) is str and bool(event["tool_id"]),
                "tool event identity missing")
    status = receipt["mechanism_status"]
    require(status in ("activated", "not_triggered", "tool_failed"), "unknown mechanism status")
    matching = [e for e in log["events"] if e["tool_id"] == TOOLS[receipt["arm"]]]
    if status == "not_triggered":
        require(receipt["tool_event_index"] is None and
                all(receipt[k] is None for k in DIGEST_FIELDS),
                "nonactivation fabricated tool hashes")
        require(not matching, "nonactivation conceals checker invocation")
        return "STRUCTURALLY_BOUND_UNATTESTED_NO_TRIGGER"
    require(type(receipt["tool_event_index"]) is int and
            0 <= receipt["tool_event_index"] < len(log["events"]),
            "missing actual tool event")
    event = log["events"][receipt["tool_event_index"]]
    require(event["tool_id"] == TOOLS[receipt["arm"]], "wrong tool or arm")
    for field, payload in zip(DIGEST_FIELDS, (
        "raw_request_b64", "raw_response_b64", "raw_continuation_b64",
        "pre_state_b64", "post_state_b64",
    )):
        data = _decode_nonempty(event[payload], payload)
        require(type(receipt[field]) is str and
                receipt[field] == hash256(data), "tool evidence digest mismatch: " + field)
    return "STRUCTURALLY_BOUND_UNATTESTED_REQUIRES_INDEPENDENT_REPLAY"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-launch", action="store_true",
                        help="Fail closed; this candidate cannot authorize external launches.")
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--raw-log", type=Path)
    args = parser.parse_args()
    try:
        state = check_candidate(PROTOCOL.read_bytes(), LAUNCH.read_bytes())
        if (args.receipt is None) != (args.raw_log is None):
            raise ValueError("--receipt and --raw-log must both be supplied")
        if args.receipt is not None:
            receipt = exact_json(args.receipt.read_bytes())
            state["receipt_validation"] = check_receipt(receipt, args.raw_log.read_bytes())
        print(json.dumps(state, sort_keys=True))
        if args.require_launch:
            print("DENIED: independent sealing and prospective authorization absent")
            return 3
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print("INVALID_RESEARCH_CANDIDATE: " + str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
