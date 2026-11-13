"""Post-hoc research-only schema compilation cost / equivalence probe.

DO NOT DEPLOY THIS WRAPPER: the temporary module-global override is not
thread-safe and is used solely to falsify the hypothesis that per-call schema
meta-validation is necessary to preserve this finite verifier's outcomes.
Actual frozen FAR verifier code is never modified.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import platform
import random
import statistics
import time
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

import compare
from mechanization.far_mechanization import contract_v2, contract_v2_errata1


@lru_cache(maxsize=8)
def _compiled_validator(schema_text: str) -> Draft202012Validator:
    schema = json.loads(schema_text)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def cached_schema_errors(document: object) -> list:
    # No stale-content assumption: read the live schema every time. Different
    # contents => a different cache key => new validation and compiled validator.
    schema_text = contract_v2.SCHEMA_PATH.read_text(encoding="utf-8")
    validator = _compiled_validator(schema_text)
    return [
        contract_v2.ContractDiagnostic(
            "SCHEMA_CONSTRAINT_VIOLATION", item.message, tuple(item.path)
        )
        for item in sorted(
            validator.iter_errors(document), key=lambda e: (tuple(e.path), e.message)
        )
    ]


@contextlib.contextmanager
def research_only_override():
    original = contract_v2_errata1._schema_errors
    contract_v2_errata1._schema_errors = cached_schema_errors
    try:
        yield
    finally:
        contract_v2_errata1._schema_errors = original


def inspect(document: object) -> list[tuple]:
    result = contract_v2_errata1.ContractValidationResult  # dynamic type from original module
    from mechanization.far_mechanization.contract_v2_strict_v11 import (
        validate_contract as strict_validate
    )
    outcome = strict_validate(document)
    assert isinstance(outcome, result)
    return [
        (item.code, item.message, tuple(item.path))
        for item in outcome.diagnostics
    ]


def pct(values: list[int], p: int) -> int:
    data = sorted(values)
    return data[max(0, (len(data) * p + 99) // 100 - 1)]


def execute() -> dict:
    corpus, integrity = compare.prepare_corpus()
    all_cases = corpus + integrity
    # Additional syntactic/adversarial invalid inputs (not part of 18/3 data).
    invalid = [
        ("empty-document", {}),
        ("invalid-root", None),
        ("bad-format", {**corpus[0]["document"], "format_version": "not-a-format"}),
    ]
    def doc(item):
        return item["document"]
    equivalence = []
    for item in all_cases:
        original = inspect(doc(item))
        with research_only_override():
            cached = inspect(doc(item))
        if original != cached:
            raise AssertionError("cached validator changed diagnostic output: " + item["id"])
        equivalence.append(item["id"])
    for key, value in invalid:
        baseline = inspect(value)
        with research_only_override():
            candidate = inspect(value)
        if baseline != candidate:
            raise AssertionError("cached validator changed invalid input: " + key)
        equivalence.append(key)

    if len(equivalence) != 24:
        raise AssertionError("not all original/mutation challenges covered")
    original_fn = contract_v2_errata1._schema_errors
    assert original_fn is not cached_schema_errors

    # Post-hoc diagnostic, NOT the preregistered three-lane performance endpoint.
    WARMUP, REPEATS, SEED = 2, 21, 20261112
    measures = {"canonical": [], "cached_prototype": []}
    order_log = []
    for round_id in range(WARMUP + REPEATS):
        rng = random.Random(SEED + round_id + 100_000)
        shuffled = list(corpus)
        rng.shuffle(shuffled)
        for item in shuffled:
            lanes = list(measures)
            rng.shuffle(lanes)
            for lane in lanes:
                before = time.perf_counter_ns()
                if lane == "canonical":
                    outputs = inspect(doc(item))
                else:
                    with research_only_override():
                        outputs = inspect(doc(item))
                elapsed = time.perf_counter_ns() - before
                if round_id >= WARMUP:
                    measures[lane].append(elapsed)
                    order_log.append({
                        "round": round_id - WARMUP,
                        "case": item["id"],
                        "lane": lane,
                        "time_ns": elapsed,
                    })
    assert all(len(x) == 378 for x in measures.values())
    assert contract_v2_errata1._schema_errors is original_fn
    metrics = {}
    for lane, observations in measures.items():
        metrics[lane] = {
            "samples": len(observations),
            "mean_ns": statistics.mean(observations),
            "median_ns": statistics.median(observations),
            "p95_ns": pct(observations, 95),
            "sum_ns": sum(observations),
        }
    # Directly isolate mandatory JSON Schema meta-validation (same schema string).
    schema = json.loads(contract_v2.SCHEMA_PATH.read_text(encoding="utf-8"))
    samples_check_schema = []
    for _ in range(32):
        start = time.perf_counter_ns()
        Draft202012Validator.check_schema(schema)
        samples_check_schema.append(time.perf_counter_ns() - start)

    return {
        "schema": "far-schema-cache-research-probe/1",
        "status": "RESEARCH_POST_HOC_DIAGNOSTIC_NOT_PREREGISTERED_ENDPOINT",
        "original_frozen_verifier_mutated": False,
        "canonical_path": str(contract_v2.SCHEMA_PATH.relative_to(compare.ROOT)),
        "schema_sha256": hashlib.sha256(contract_v2.SCHEMA_PATH.read_bytes()).hexdigest(),
        "schema_changed_bytes_trigger_recompilation": True,
        "equivalent_complete_diagnostics_cases": equivalence,
        "n_equivalence_cases": len(equivalence),
        "timing": metrics,
        "schema_definition_meta_check_32": {
            "mean_ns": statistics.mean(samples_check_schema),
            "median_ns": statistics.median(samples_check_schema),
            "samples": len(samples_check_schema),
        },
        "cache_info": str(_compiled_validator.cache_info()),
        "measurements": order_log,
        "host": platform.platform(),
        "limitations": [
            "Post-hoc diagnostic after seeing original three-lane performance results.",
            "Uses sequential temporary global override; not concurrency-safe or deployable.",
            "Retains full on-disk schema read each call; compiles only when schema bytes change.",
            "Twenty-four fixed cases are not a general equivalence proof across all JSON inputs.",
            "No agent loop, no tool access, no impact on autonomous-agent reliability.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = execute()
    if args.output:
        args.output.parent.mkdir(exist_ok=True, parents=True)
        args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print("PASS_RESEARCH_SCHEMA_CACHE_PROBE " + json.dumps({
        "diagnostic_parity": result["n_equivalence_cases"],
        "timing": result["timing"],
        "schema_meta_check": result["schema_definition_meta_check_32"],
        "cache": result["cache_info"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
