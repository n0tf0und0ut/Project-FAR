#!/usr/bin/env python3
"""Prospectively registered secondary comparator of actual executable FAR mechanism.

FAR-MECH-COMP-001. Reuses original frozen W4/W6 records without modifying
them. NO MODEL CALLS, no independent investigators, no agent loop.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib
import json
import platform
import random
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from generic_collision import classify as generic_classify  # noqa: E402
from tools.check_pca_w6_empirical_audit_utility import (  # noqa: E402
    EXPECTED_DOMAINS, _record_groups, inject_registered_collision,
)
from mechanization.far_mechanization.contract_v2_strict_v11 import (
    validate_contract as strict_far_validate,
)

SEED = 20261112
WARMUP_ROUNDS = 2
MEASURED_ROUNDS = 21
VALID_LABELS = {"NO_LOSS", "LOSS"}
SCHEMA = ROOT / "schemas/far-contract-v2.schema.json"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def to_json(data: object) -> bytes:
    return json.dumps(
        data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def reference_truth(document: dict) -> str:
    """Independently derive the finite contract's ground truth using O(n²) pairs.

    This uses no FAR validator, report labels, or generic checker.
    The source/target TABLES are nevertheless Project-FAR-authored, not external.
    """
    contract = document["contract"]
    ids = [str(x["id"]) for x in contract["source_domain"]["cases"]]
    assert len(ids) == len(set(ids))
    reps = {row["case_id"]: to_json(row["value"]) for row in contract["representation"]["table"]}
    targets = {row["case_id"]: to_json(row["value"]) for row in contract["required_behavior"]["table"]}
    assert len(reps) == len(ids) and len(targets) == len(ids)
    assert set(ids) == set(reps) == set(targets)
    for i, left in enumerate(ids):
        for right in ids[i + 1:]:
            if reps[left] == reps[right] and targets[left] != targets[right]:
                return "LOSS"
    return "NO_LOSS"


def prepare_corpus() -> tuple[list[dict], list[dict]]:
    groups = _record_groups()  # Existing frozen corpus manifest and SHA-256 gates.
    cases = []
    for domain in EXPECTED_DOMAINS:
        for variant in ("repaired", "lossy"):
            path = groups[domain][variant]
            raw = path.read_bytes()
            obj = json.loads(raw)
            assert obj["format_version"] == "far-ir/2.0"
            assert obj["contract"]["source_domain"]["status"] == "EXPLICIT"
            label = "NO_LOSS" if variant == "repaired" else "LOSS"
            assert reference_truth(obj) == label
            if variant == "repaired":
                cases.append({
                    "id": domain + ".clean", "kind": "clean",
                    "domain": domain, "label": label,
                    "source_path": path.relative_to(ROOT).as_posix(),
                    "source_sha256": digest(raw),
                    "document": obj,
                })
                mutant = inject_registered_collision(obj)
                assert reference_truth(mutant) == "LOSS"
                cases.append({
                    "id": domain + ".mutant", "kind": "mutant",
                    "domain": domain, "label": "LOSS",
                    "source_path": path.relative_to(ROOT).as_posix(),
                    "source_sha256": digest(raw),
                    "document": mutant,
                })
            else:
                cases.append({
                    "id": domain + ".lossy", "kind": "lossy",
                    "domain": domain, "label": "LOSS",
                    "source_path": path.relative_to(ROOT).as_posix(),
                    "source_sha256": digest(raw),
                    "document": obj,
                })
    assert len(cases) == 18 and len(set(x["id"] for x in cases)) == 18
    assert Counter(x["label"] for x in cases) == {"LOSS": 12, "NO_LOSS": 6}

    # Preregistered integrity-only controls: first three registered domains, one each.
    clean_by_domain = {x["domain"]: x for x in cases if x["kind"] == "clean"}
    integrity = []
    for idx, domain in enumerate(EXPECTED_DOMAINS[:3]):
        src = clean_by_domain[domain]
        item = copy.deepcopy(src["document"])
        if idx == 0:
            name = "wrong-freeze-hash"
            item["freeze"]["contract_sha256"] = "0" * 64
        elif idx == 1:
            name = "falsified-refuted-outcome"
            item["report"]["outcome"] = "REFUTED"
        else:
            name = "unchecked-proof-status"
            item["report"]["evidence"]["status"] = "DECLARED_UNCHECKED"
        assert reference_truth(item) == "NO_LOSS"
        integrity.append({
            "id": domain + "." + name,
            "kind": "integrity-only",
            "domain": domain,
            "expected": "INVALID",
            "document": item,
            "base_source_sha256": src["source_sha256"],
        })
    assert len(integrity) == 3
    return cases, integrity


def make_validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def classify_schema_only(doc: dict, validator: Draft202012Validator) -> str:
    # The schema lane is an intentionally nonsemantic ablation.
    return "NO_LOSS" if validator.is_valid(doc) else "INVALID"


def classify_far(doc: dict) -> tuple[str, list[str]]:
    result = strict_far_validate(doc)  # Actual FAR executable contract verifier.
    codes = sorted({str(x.code) for x in result.diagnostics})
    outcome = doc.get("report", {}).get("outcome")
    evidence = doc.get("report", {}).get("evidence", {})
    kind = evidence.get("kind") if isinstance(evidence, dict) else None
    status = evidence.get("status") if isinstance(evidence, dict) else None
    if result.success:
        if (outcome, kind, status) == ("PROVED", "factorization", "CHECKED_FINITE_EXPLICIT"):
            return "NO_LOSS", codes
        if (outcome, kind, status) == ("REFUTED", "collision", "CHECKED_FINITE_EXPLICIT"):
            return "LOSS", codes
        return "INVALID", codes
    # This is a checked semantic refutation, distinct from unrelated invalid metadata.
    if "FACTORIZATION_FAILURE" in codes:
        return "LOSS", codes
    return "INVALID", codes


def _call(name: str, obj: dict, validator: Draft202012Validator) -> tuple[str, list[str]]:
    if name == "schema":
        return classify_schema_only(obj, validator), []
    if name == "generic":
        return generic_classify(obj, validator), []
    if name == "far":
        return classify_far(obj)
    raise ValueError("unregistered lane")


def _percentile_ns(values: list[int], percentile: int) -> int:
    assert values and 0 <= percentile <= 100
    # Conservative nearest-rank upper tail; integer order statistics only.
    ordered = sorted(values)
    return ordered[max(0, (len(ordered) * percentile + 99) // 100 - 1)]


def score(matrix: list[dict], lane: str) -> dict:
    tp = fn = tn = fp = invalid = 0
    for row in matrix:
        expected, observed = row["truth"], row["predictions"][lane]["class"]
        if expected not in VALID_LABELS:
            raise ValueError("bad truth class")
        if observed == "INVALID":
            invalid += 1
        if expected == "LOSS":
            if observed == "LOSS":
                tp += 1
            else:
                fn += 1
        else:
            if observed == "NO_LOSS":
                tn += 1
            else:
                fp += 1
    return {
        "tp": tp, "fn": fn, "tn": tn, "fp": fp, "invalid": invalid,
        "correct": tp + tn, "total": len(matrix),
    }


def execute() -> dict:
    cases, integrity = prepare_corpus()
    validator = make_validator()
    lanes = ("schema", "generic", "far")
    item_ids = [x["id"] for x in cases]
    original = {
        x["id"]: {
            "id": x["id"], "kind": x["kind"], "domain": x["domain"],
            "truth": x["label"],
            "source_path": x["source_path"],
            "source_sha256": x["source_sha256"],
            "document_sha256": digest(to_json(x["document"])),
            "predictions": {},
        }
        for x in cases
    }

    # Frozen initial classifications; do not learn from measured timings.
    for item in cases:
        for lane in lanes:
            verdict, diagnostics = _call(lane, item["document"], validator)
            original[item["id"]]["predictions"][lane] = {
                "class": verdict,
                "diagnostics": diagnostics,
            }
    matrix = [original[key] for key in sorted(original)]
    counts = {lane: score(matrix, lane) for lane in lanes}

    challenges = []
    for item in integrity:
        results = {}
        for lane in lanes:
            verdict, codes = _call(lane, item["document"], validator)
            results[lane] = {"class": verdict, "diagnostics": codes}
        challenges.append({
            "id": item["id"], "expected": item["expected"],
            "base_source_sha256": item["base_source_sha256"],
            "document_sha256": digest(to_json(item["document"])),
            "predictions": results,
        })

    # Operational cost measurements: all lanes alternate on same process/runner.
    per_lane: dict[str, list[int]] = {lane: [] for lane in lanes}
    observations = []
    for round_idx in range(WARMUP_ROUNDS + MEASURED_ROUNDS):
        rng = random.Random(SEED + round_idx)
        pairs = list(cases)
        rng.shuffle(pairs)
        for item in pairs:
            order = list(lanes)
            rng.shuffle(order)
            for lane in order:
                started = time.perf_counter_ns()
                result, diagnostics = _call(lane, item["document"], validator)
                elapsed = time.perf_counter_ns() - started
                expected = original[item["id"]]["predictions"][lane]
                assert (result, diagnostics) == (expected["class"], expected["diagnostics"]), (
                    "nondeterministic lane output", lane, item["id"])
                if round_idx >= WARMUP_ROUNDS:
                    per_lane[lane].append(elapsed)
                    observations.append({
                        "pass": round_idx - WARMUP_ROUNDS,
                        "case": item["id"],
                        "lane": lane,
                        "elapsed_ns": elapsed,
                        "class": result,
                    })
    assert len(observations) == MEASURED_ROUNDS * len(cases) * len(lanes)
    latency = {}
    for lane in lanes:
        durations = per_lane[lane]
        latency[lane] = {
            "samples": len(durations),
            "mean_ns": statistics.mean(durations),
            "median_ns": statistics.median(durations),
            "p95_nearest_rank_ns": _percentile_ns(durations, 95),
            "sum_ns": sum(durations),
            "mean_ns_per_correct_item_in_measured_cohort": (
                sum(durations) / MEASURED_ROUNDS / counts[lane]["correct"]
                if counts[lane]["correct"] else None
            ),
        }
    assert sum(len(v) for v in per_lane.values()) == len(observations)
    expected_ids = {x["id"] for x in cases}
    assert len(expected_ids) == 18

    result = {
        "schema": "far-mech-comp-001/1",
        "status": "RESEARCH_BOUNDED_INTERNAL_COMPARISON",
        "research_base_sha": "f3c04e423df798960f64599ff638994aaaae981c",
        "preregistration_path": "research/mechanism-comparator/00-preregistration.md",
        "sample": {
            "case_count": len(cases),
            "clean": 6,
            "registered_mutants": 6,
            "native_lossy": 6,
            "external_investigator_independent": False,
            "agent_model_calls": 0,
            "is_agent_reliability_trial": False,
        },
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "processor": platform.processor(),
            "jsonschema_version": importlib.metadata.version("jsonschema"),
            "source_sha256": digest(Path(__file__).read_bytes()),
            "generic_source_sha256": digest((HERE / "generic_collision.py").read_bytes()),
            "frozen_manifest_sha256": digest(
                (ROOT / "research/results/pca-w4-domain-contracts/manifest.json").read_bytes()),
        },
        "lane_scores": counts,
        "paired_matrix": matrix,
        "secondary_integrity_challenges": challenges,
        "timing": {
            "method": "time.perf_counter_ns on same process, warmed, fixed host",
            "seed": SEED,
            "warmup_rounds": WARMUP_ROUNDS,
            "measured_rounds": MEASURED_ROUNDS,
            "per_lane": latency,
            "observations": observations,
        },
        "limits": [
            "All tasks, mutations and behavior tables are Project-FAR-authored.",
            "Previously exposed finite W4/W6 examples; no blinded held-out task.",
            "Generic checker and FAR do not implement equal provenance/evidence-integrity contracts.",
            "Timing is on one hosted runner, cannot infer cross-machine cost or model API cost.",
            "No autonomous agent, repair or model execution; general-purpose causal reliability remains untested.",
            "A generic checker that tests the same collision equivalence is mathematically expected to match FAR.",
        ],
    }
    return result


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    result = execute()
    text = json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print("FAR_MECH_COMP_SUMMARY " + json.dumps({
        "scores": result["lane_scores"],
        "integrity": result["secondary_integrity_challenges"],
        "latency_ns": result["timing"]["per_lane"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
