#!/usr/bin/env python3
"""Validate and identify a Research-stage factory self-evaluation preregistration.

This file validates *declarations*, not trial results or GitHub provenance.
It does not run agents, sign evidence, approve PRs, or claim superiority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

KIND = "far-factory-self-evaluation/1"
SHA = re.compile(r"^[0-9a-f]{40}$")
STUDY_ID = re.compile(r"^FAR-FACTORY-SELF-EVAL-[0-9]{3}$")
METRICS = {
    "wall_minutes", "provider_usd", "human_interventions", "attempts",
    "regressions_detected", "escaped_regressions", "evidence_completeness",
    "recovery_after_interruption",
}
RECEIPT_FIELDS = {
    "study_id", "protocol_sha256", "task_id", "arm_id", "task_base_sha",
    "candidate_sha", "executor_identity", "model_version", "runner_identity",
    "task_oracle_digest", "started_at", "ended_at", "raw_log_digest",
    "cost_usd", "human_interventions", "outcome", "check_run_ids",
    "review_reference", "merge_sha", "observed_main_sha",
}
CHECKS = {"merge-authority", "protected-repin-gate", "pr-review-convergence-observation"}
ALLOCATION_ALGORITHM = "sha256-utf8-colon-sort-v1"
SCHEDULE_ALGORITHM = "sha256-utf8-colon-start-interleave-v1"
SEED = re.compile(r"^[0-9a-f]{64}$")
TASK_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


def allocation_schedule(seed: str, task_ids: list[str]) -> list[dict[str, object]]:
    """Pure reference assignment for a *pre-registered* cohort (not admission).

    No seed or tasks are generated here. The independent evaluator must first
    freeze eligibility and identities, then generate and retain a random seed.
    The test vector is illustrative; this function is not a trusted witness.
    """
    if type(seed) is not str or SEED.fullmatch(seed) is None:
        raise ContractError("seed must be exactly 64 lowercase hexadecimal characters")
    if type(task_ids) is not list or len(task_ids) != 8:
        raise ContractError("expected eight preregistered task IDs")
    if any(type(t) is not str or TASK_ID.fullmatch(t) is None for t in task_ids):
        raise ContractError("invalid canonical task ID")
    if len(set(task_ids)) != len(task_ids):
        raise ContractError("duplicate task ID")

    def digest(text: str) -> bytes:
        return hashlib.sha256(text.encode("utf-8")).digest()

    ranked = sorted(task_ids, key=lambda task: (digest(seed + ":" + task), task))
    tasks = {"control": ranked[:4], "factory": ranked[4:]}
    first = "factory" if digest(seed + ":start")[-1] & 1 else "control"
    second = "control" if first == "factory" else "factory"
    rows: list[dict[str, object]] = []
    for i in range(4):
        for arm in (first, second):
            rows.append({"slot": len(rows) + 1, "arm": arm, "task_id": tasks[arm][i]})
    return rows


class ContractError(ValueError):
    """A declaration is malformed or fails an essential comparison invariant."""


def _pairs(entries: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in entries:
        if key in result:
            raise ContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _shape(value: object, keys: set[str], label: str) -> dict:
    if type(value) is not dict:
        raise ContractError(f"{label} must be an object")
    missing = keys - value.keys()
    extra = value.keys() - keys
    if missing or extra:
        raise ContractError(f"{label} keys: missing={sorted(missing)}, unexpected={sorted(extra)}")
    return value


def _text(value: object, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise ContractError(f"{label} must be a nonempty string")
    return value


def _string_list(value: object, label: str) -> list[str]:
    if type(value) is not list or not value:
        raise ContractError(f"{label} must be a nonempty list")
    for item in value:
        _text(item, label)
    if len(set(value)) != len(value):
        raise ContractError(f"{label} contains duplicates")
    return value


def _bool(value: object, label: str, expected: bool) -> None:
    if type(value) is not bool or value != expected:
        raise ContractError(f"{label} must be {expected}")


def validate(record: object) -> dict:
    doc = _shape(record, {
        "schema", "study_id", "status", "reference_repo", "registration_base_sha",
        "question", "arms", "sampling", "controls", "primary_metric",
        "secondary_metrics", "verification", "decision", "limitations", "execution_manifest",
    }, "protocol")
    if doc["schema"] != KIND:
        raise ContractError("unknown schema")
    if not STUDY_ID.fullmatch(_text(doc["study_id"], "study_id")):
        raise ContractError("invalid study_id")
    if doc["status"] != "Research-preregistered-not-executed":
        raise ContractError("unverified protocol cannot claim execution or promotion")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", _text(doc["reference_repo"], "reference_repo")):
        raise ContractError("invalid reference repository")
    if not SHA.fullmatch(_text(doc["registration_base_sha"], "registration_base_sha")):
        raise ContractError("unbound registration base SHA")
    _text(doc["question"], "question")
    arms = doc["arms"]
    if type(arms) is not list or len(arms) != 2:
        raise ContractError("must have exactly two arms")
    for arm in arms:
        a = _shape(arm, {"id", "description"}, "arm")
        _text(a["description"], "arm.description")
    if {a["id"] for a in arms if type(a["id"]) is str} != {"control", "factory"}:
        raise ContractError("arms must be control and factory")
    s = _shape(doc["sampling"], {
        "design", "target_distinct_tasks", "source", "included_classes", "exclusions",
        "allocation", "allocation_algorithm", "tasks_frozen", "post_allocation_violation_policy",
    }, "sampling")
    if s["design"] != "prospective-randomized-parallel-pilot":
        raise ContractError("invalid pilot design")
    if type(s["target_distinct_tasks"]) is not int or s["target_distinct_tasks"] != 8:
        raise ContractError("invalid task target")
    _text(s["source"], "sampling.source")
    _text(s["allocation"], "sampling.allocation")
    if s["allocation_algorithm"] != ALLOCATION_ALGORITHM:
        raise ContractError("allocation algorithm must match executable reference")
    if set(_string_list(s["included_classes"], "included_classes")) != {"defect-repair", "maintenance"}:
        raise ContractError("invalid eligible classes")
    _string_list(s["exclusions"], "sampling.exclusions")
    _bool(s["tasks_frozen"], "sampling.tasks_frozen", False)
    if s["post_allocation_violation_policy"] != "Retain every allocated task in its original arm and denominator even if the contestant tampers with tests or oracles; record FAILURE or UNKNOWN and stop affected execution for a safety/provenance violation; never admit a replacement":
        raise ContractError("post-allocation outcomes must remain in the denominator")
    c = _shape(doc["controls"], {
        "task_base_sha_pinned_before_allocation", "task_specifications_frozen_before_allocation", "test_oracles_frozen_before_allocation",
        "same_model_version_when_possible", "same_runner_hardware_when_possible",
        "balanced_interleaved_schedule", "execution_order_algorithm", "cross_arm_knowledge_isolation",
        "cross_arm_exposure_policy", "max_wall_minutes_per_arm_task",
        "max_paid_provider_usd_per_arm_task", "max_agent_attempts_per_arm_task",
        "human_intervention_definition", "deviation_policy",
    }, "controls")
    for key in ("task_base_sha_pinned_before_allocation", "task_specifications_frozen_before_allocation", "test_oracles_frozen_before_allocation",
                "same_model_version_when_possible", "same_runner_hardware_when_possible",
                "cross_arm_knowledge_isolation"):
        _bool(c[key], f"controls.{key}", True)
    if c["execution_order_algorithm"] != SCHEDULE_ALGORITHM:
        raise ContractError("execution order algorithm must match executable reference")
    if "strictly alternate" not in _text(c["balanced_interleaved_schedule"], "controls.balanced_interleaved_schedule"):
        raise ContractError("unbalanced task scheduling")
    if "forbid sharing" not in _text(c["cross_arm_exposure_policy"], "controls.cross_arm_exposure_policy"):
        raise ContractError("missing cross-arm information-isolation policy")
    if type(c["max_wall_minutes_per_arm_task"]) is not int or not 1 <= c["max_wall_minutes_per_arm_task"] <= 1440:
        raise ContractError("invalid wall time budget")
    if type(c["max_paid_provider_usd_per_arm_task"]) not in (int, float) or c["max_paid_provider_usd_per_arm_task"] != 0:
        raise ContractError("paid provider usage requires a separately reviewed protocol")
    if type(c["max_agent_attempts_per_arm_task"]) is not int or not 1 <= c["max_agent_attempts_per_arm_task"] <= 5:
        raise ContractError("invalid attempt limit")
    _text(c["human_intervention_definition"], "controls.human_intervention_definition")
    _text(c["deviation_policy"], "controls.deviation_policy")
    e = _shape(doc["execution_manifest"], {
        "required_before_task_execution", "independent_review_required", "required_fields", "change_policy",
    }, "execution_manifest")
    _bool(e["required_before_task_execution"], "execution_manifest.required_before_task_execution", True)
    _bool(e["independent_review_required"], "execution_manifest.independent_review_required", True)
    required = {"study_id", "protocol_sha256", "cohort_manifest_sha256", "control_implementation_revision", "factory_implementation_revision", "control_configuration_digest", "factory_configuration_digest", "provider_model_versions", "prompts_and_tools_digest", "runner_image_digest", "allowed_adaptations", "approved_midtrial_change_policy", "independent_reviewer", "immutable_registration_reference"}
    if set(_string_list(e["required_fields"], "execution_manifest.required_fields")) != required:
        raise ContractError("incomplete execution manifest requirements")
    if "no unregistered" not in _text(e["change_policy"], "execution_manifest.change_policy"):
        raise ContractError("missing implementation freeze policy")
    p = _shape(doc["primary_metric"], {"id", "numerator", "denominator", "measurement_unit"}, "primary_metric")
    if p["id"] != "verified_protected_delivery_rate":
        raise ContractError("primary metric must be verified protected delivery")
    for k in ("numerator", "denominator", "measurement_unit"):
        _text(p[k], "primary_metric." + k)
    if set(_string_list(doc["secondary_metrics"], "secondary_metrics")) != METRICS:
        raise ContractError("secondary metrics differ from the registered set")
    v = _shape(doc["verification"], {
        "independent_from_candidate_worker", "required_check_contexts",
        "required_receipt_fields", "unknown_or_missing_is_not_success",
        "worker_declarations_are_untrusted", "frozen_task_oracle_required",
    }, "verification")
    for k in ("independent_from_candidate_worker", "unknown_or_missing_is_not_success",
              "worker_declarations_are_untrusted", "frozen_task_oracle_required"):
        _bool(v[k], "verification." + k, True)
    if set(_string_list(v["required_check_contexts"], "required_check_contexts")) != CHECKS:
        raise ContractError("protected checks mismatch current policy")
    if set(_string_list(v["required_receipt_fields"], "required_receipt_fields")) != RECEIPT_FIELDS:
        raise ContractError("evidence receipt schema changed")
    d = _shape(doc["decision"], {
        "study_type", "superiority_claim_allowed", "major_security_or_provenance_failure",
        "missing_or_incomparable_evidence", "success_condition", "followup",
    }, "decision")
    if d["study_type"] != "diagnostic-pilot-not-confirmatory":
        raise ContractError("pilot cannot claim a confirmatory study")
    _bool(d["superiority_claim_allowed"], "decision.superiority_claim_allowed", False)
    if d["major_security_or_provenance_failure"] != "STOP_AND_REPORT":
        raise ContractError("safety stop cannot be disabled")
    if d["missing_or_incomparable_evidence"] != "UNKNOWN_OR_INCOMPARABLE":
        raise ContractError("missing evidence must stay unknown")
    _text(d["success_condition"], "decision.success_condition")
    _text(d["followup"], "decision.followup")
    _string_list(doc["limitations"], "limitations")
    return doc


def load(path: Path) -> tuple[dict, str]:
    data = path.read_bytes()
    if not data or len(data) > 262144:
        raise ContractError("empty or oversized protocol")
    try:
        parsed = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs,
                            parse_constant=lambda val: (_ for _ in ()).throw(ContractError("nonfinite number " + val)))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"invalid UTF-8 JSON: {exc}") from exc
    validate(parsed)
    return parsed, hashlib.sha256(data).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("protocol", type=Path)
    parser.add_argument("--expected-sha256", help="Expected exact byte digest; use the protected-main copy when an experiment begins")
    args = parser.parse_args(argv)
    try:
        doc, digest = load(args.protocol)
        if args.expected_sha256 is not None and args.expected_sha256 != digest:
            raise ContractError("protocol digest mismatch: protocol bytes changed")
    except (ContractError, OSError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2
    print(f"VALID (structural only) {doc['study_id']} sha256={digest} status={doc['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
