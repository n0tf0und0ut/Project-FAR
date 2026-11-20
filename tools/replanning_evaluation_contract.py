#!/usr/bin/env python3
"""Fail-closed structural checker and allocation reference for FAR-REPLAN-001.

Research declaration only: no agent execution, outcome grading, attestation or
permission to alter protected main. Never treat VALID as trial authorization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

SCHEMA = "far-replanning-comparison/1"
STUDY = "FAR-REPLAN-001"
SHA = re.compile(r"[0-9a-f]{40}\Z")
SEED = re.compile(r"[0-9a-f]{64}\Z")
IDENT = re.compile(r"[A-Za-z0-9._-]{1,128}\Z")
ARMS = {"control", "replanning"}
ALGORITHM = "sha256-utf8-task-and-order-v1"
SECONDARY = {
    "unauthorized_writes", "verified_interruption_recoveries",
    "duplicate_or_stale_intents", "model_tokens", "executed_tool_calls",
    "wall_seconds", "provider_cost_usd", "human_interventions",
    "evidence_binding_failures", "unresolved_failures",
}
MANIFEST = {
    "protocol_sha256", "protected_main_registration_sha",
    "cohort_manifest_sha256", "seed_and_origin", "source_sha_per_task",
    "oracle_sha256_per_task", "control_adapter_sha", "replanning_adapter_sha",
    "model_manifest_sha256", "prompt_and_tools_sha256", "container_image_digest",
    "isolation_and_permissions", "interruption_schedule_sha256",
    "independent_reviewer_identity",
}
RECEIPT = {
    "study_id", "protocol_sha256", "task_id", "arm_id", "task_source_sha",
    "oracle_sha256", "executor_identity", "model_manifest_sha256",
    "prompt_and_tools_sha256", "runner_image_digest", "started_at",
    "ended_at", "raw_request_response_digest", "tool_execution_receipts_digest",
    "oracle_execution_receipt_digest", "termination_reason", "outcome",
    "budget_usage", "human_interventions",
}


class ContractError(ValueError):
    """Protocol does not preserve its registered comparison obligations."""


def _pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("duplicate JSON key: " + key)
        result[key] = value
    return result


def _shape(value: object, keys: set[str], label: str) -> dict:
    if type(value) is not dict or set(value) != keys:
        raise ContractError(f"{label} keys differ from registered contract")
    return value


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise ContractError(f"{label} must be nonempty text")
    return value


def _exact(value: object, expected: object, label: str) -> None:
    if type(value) is not type(expected) or value != expected:
        raise ContractError(f"{label} must be {expected!r}")


def _unique_list(value: object, expected: set[str], label: str) -> None:
    if type(value) is not list or len(value) != len(expected) or any(type(x) is not str for x in value):
        raise ContractError(f"{label} must have the complete registered members")
    if set(value) != expected:
        raise ContractError(f"{label} members differ from the registered members")


def assignment_schedule(seed: str, task_ids: list[str]) -> list[dict[str, object]]:
    """Deterministically order frozen tasks and vary arm order within each pair.

    Must be called by an independent evaluator *after* task+oracle freeze; the
    function does not produce a seed or assert that an admission was independent.
    """
    if type(seed) is not str or SEED.fullmatch(seed) is None:
        raise ContractError("seed must be 64 lowercase hex characters")
    if type(task_ids) is not list or len(task_ids) != 12:
        raise ContractError("exactly twelve frozen task IDs required")
    if any(type(t) is not str or IDENT.fullmatch(t) is None for t in task_ids):
        raise ContractError("noncanonical task ID")
    if len(set(task_ids)) != 12:
        raise ContractError("duplicate task ID")

    def digest(s: str) -> bytes:
        return hashlib.sha256(s.encode("utf-8")).digest()

    tasks = sorted(task_ids, key=lambda t: (digest(seed + ":task:" + t), t))
    schedule: list[dict[str, object]] = []
    for task in tasks:
        first = "replanning" if digest(seed + ":order:" + task)[-1] & 1 else "control"
        second = "control" if first == "replanning" else "replanning"
        for arm in (first, second):
            schedule.append({"slot": len(schedule) + 1, "task_id": task, "arm": arm})
    return schedule


def validate(record: object) -> dict:
    p = _shape(record, {
        "schema", "study_id", "status", "reference_repository", "registration_base_sha",
        "question", "arms", "sampling", "controls", "execution_manifest",
        "primary_metric", "secondary_metrics", "receipt_fields", "decision", "limitations",
    }, "protocol")
    _exact(p["schema"], SCHEMA, "schema")
    _exact(p["study_id"], STUDY, "study_id")
    _exact(p["status"], "Research-proposed-not-executed", "status")
    _exact(p["reference_repository"], "n0tf0und0ut/Project-FAR", "reference_repository")
    if not isinstance(p["registration_base_sha"], str) or SHA.fullmatch(p["registration_base_sha"]) is None:
        raise ContractError("registration must pin an exact Git SHA")
    _text(p["question"], "question")
    arms = p["arms"]
    if type(arms) is not list or len(arms) != 2:
        raise ContractError("exactly two arms required")
    parsed_arms = [_shape(a, {"id", "implementation"}, "arm") for a in arms]
    _unique_list([a["id"] for a in parsed_arms], ARMS, "arms")
    for arm in parsed_arms:
        _text(arm["implementation"], "arm.implementation")
    s = _shape(p["sampling"], {
        "design", "distinct_task_count", "runs_per_task", "eligible_tasks",
        "exclusions", "freeze_before_seed", "task_ids_frozen",
        "task_base_sha_frozen", "oracles_frozen", "allocation_algorithm",
        "allocation", "post_allocation_policy",
    }, "sampling")
    _exact(s["design"], "prospective-paired-diagnostic-pilot", "sampling.design")
    _exact(s["distinct_task_count"], 12, "sampling.distinct_task_count")
    _exact(s["runs_per_task"], 2, "sampling.runs_per_task")
    for key, expected in (("freeze_before_seed", True), ("task_ids_frozen", False),
                          ("task_base_sha_frozen", False), ("oracles_frozen", False)):
        _exact(s[key], expected, "sampling." + key)
    _exact(s["allocation_algorithm"], ALGORITHM, "sampling.allocation_algorithm")
    _text(s["eligible_tasks"], "sampling.eligible_tasks")
    _text(s["allocation"], "sampling.allocation")
    if "never replace" not in _text(s["post_allocation_policy"], "post_allocation_policy"):
        raise ContractError("missing denominator preservation")
    if type(s["exclusions"]) is not list or len(s["exclusions"]) < 3:
        raise ContractError("insufficient exclusions")
    for item in s["exclusions"]:
        _text(item, "sampling.exclusions")
    c = _shape(p["controls"], {
        "same_base_source_and_task_per_pair", "same_model_manifest_and_generation_settings",
        "same_tools_permissions_oracle_and_runner", "fresh_isolated_context_and_workspace_per_arm",
        "no_cross_arm_feedback_until_pair_terminal", "same_task_budget", "max_wall_minutes_per_run",
        "max_model_tokens_per_run", "max_tool_calls_per_run", "max_model_replanning_rounds",
        "max_paid_provider_usd_per_run", "interruption_policy", "deviation_policy",
    }, "controls")
    for key in ("same_base_source_and_task_per_pair", "same_model_manifest_and_generation_settings",
                "same_tools_permissions_oracle_and_runner", "fresh_isolated_context_and_workspace_per_arm",
                "no_cross_arm_feedback_until_pair_terminal", "same_task_budget"):
        _exact(c[key], True, "controls." + key)
    for key, expected in (("max_wall_minutes_per_run", 45),
                          ("max_model_tokens_per_run", 15000),
                          ("max_tool_calls_per_run", 60),
                          ("max_model_replanning_rounds", 12),
                          ("max_paid_provider_usd_per_run", 0)):
        _exact(c[key], expected, "controls." + key)
    _text(c["interruption_policy"], "controls.interruption_policy")
    _text(c["deviation_policy"], "controls.deviation_policy")
    e = _shape(p["execution_manifest"], {
        "required_before_first_run", "independent_review_required", "required_fields",
        "implementations_frozen", "provider_verified", "tasks_enrolled",
    }, "execution_manifest")
    _exact(e["required_before_first_run"], True, "execution_manifest.required_before_first_run")
    _exact(e["independent_review_required"], True, "execution_manifest.independent_review_required")
    _unique_list(e["required_fields"], MANIFEST, "execution_manifest.required_fields")
    for key in ("implementations_frozen", "provider_verified"):
        _exact(e[key], False, "execution_manifest." + key)
    _exact(e["tasks_enrolled"], 0, "execution_manifest.tasks_enrolled")
    m = _shape(p["primary_metric"], {
        "id", "denominator", "definition", "independent_oracle_required",
        "worker_claim_not_evidence",
    }, "primary_metric")
    _exact(m["id"], "paired_verified_completion_difference", "primary_metric.id")
    _exact(m["denominator"], 12, "primary_metric.denominator")
    _exact(m["independent_oracle_required"], True, "primary_metric.independent_oracle_required")
    _exact(m["worker_claim_not_evidence"], True, "primary_metric.worker_claim_not_evidence")
    _text(m["definition"], "primary_metric.definition")
    _unique_list(p["secondary_metrics"], SECONDARY, "secondary_metrics")
    _unique_list(p["receipt_fields"], RECEIPT, "receipt_fields")
    d = _shape(p["decision"], {
        "study_type", "superiority_or_generalization_claim_allowed", "security_or_provenance_breach",
        "missing_or_incomparable", "success_condition", "followup",
    }, "decision")
    _exact(d["study_type"], "diagnostic-only", "decision.study_type")
    _exact(d["superiority_or_generalization_claim_allowed"], False, "decision.superiority")
    _exact(d["security_or_provenance_breach"], "STOP_AND_PRESERVE", "decision.security")
    _exact(d["missing_or_incomparable"], "UNKNOWN_OR_INCOMPARABLE", "decision.missing")
    _text(d["success_condition"], "decision.success_condition")
    _text(d["followup"], "decision.followup")
    if type(p["limitations"]) is not list or len(p["limitations"]) < 4:
        raise ContractError("limitations must be explicit")
    for item in p["limitations"]:
        _text(item, "limitations")
    return p


def load(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    if not raw or len(raw) > 131072:
        raise ContractError("empty or oversized protocol")
    try:
        parsed = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                            parse_constant=lambda x: (_ for _ in ()).throw(ContractError("nonfinite " + x)))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError("invalid UTF-8 JSON") from exc
    return validate(parsed), hashlib.sha256(raw).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("protocol", type=Path)
    parser.add_argument("--expected-sha256", help="Independent protected-main exact byte digest")
    args = parser.parse_args(argv)
    try:
        doc, digest = load(args.protocol)
        if args.expected_sha256 is not None and args.expected_sha256 != digest:
            raise ContractError("protocol digest mismatch")
    except (ContractError, OSError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2
    print(f"VALID DECLARATION ONLY: {doc['study_id']} sha256={digest} status={doc['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
