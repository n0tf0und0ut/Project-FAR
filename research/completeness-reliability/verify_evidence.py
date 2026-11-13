#!/usr/bin/env python3
"""Research-only raw evidence replay and causal-claim calibration.

This is a SECONDARY, outcome-exposed audit of the November 2026 frozen
30-pair one-shot synthetic-repair campaign. No trial or protocol is silently
registered or executed. The script deliberately cannot promote to a general
agent reliability claim.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import random
import re
import statistics
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "research/workflow-efficacy/result/campaign-41556392256.json"
RECORD_GIT_BLOB = "90b3a56bb43d772a9e891766a578a93e73928aa8"
EXECUTED_SHA = "a750c5523183f64a20ff644846c4fcd91c887824"
CAMPAIGN = 41556392256
MODEL = "ollama/qwen2.5-coder:1.5b"
MODEL_DIGEST = "d7372fd828518a4d38b1eb196c673c31a85f2ed302b3d1e406c4c2d1b64a0668"
REPORT_NAME = "far-completeness-reliability-retrospective/1"


def strict_json(raw: bytes) -> Any:
    def unique(pairs):
        output = {}
        for k, v in pairs:
            if k in output:
                raise ValueError("duplicate JSON key: " + k)
            output[k] = v
        return output
    def no_nonfinite(value):
        raise ValueError("nonfinite JSON constant: " + value)
    return json.loads(raw, object_pairs_hook=unique, parse_constant=no_nonfinite)


def blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def reject(condition: bool, why: str) -> None:
    if not condition:
        raise ValueError(why)


def read_source_record(path: Path = RECORD) -> dict:
    raw = path.read_bytes()
    reject(blob_sha(raw) == RECORD_GIT_BLOB, "original machine record identity drift")
    item = strict_json(raw)
    reject(isinstance(item, dict), "invalid report type")
    a, p = item["analysis"], item["provenance"]
    reject(p["execution_sha"] == EXECUTED_SHA, "source commit mismatch")
    reject(a["execution_commit"] == EXECUTED_SHA, "analyzer commit mismatch")
    reject(p["campaign_run_id"] == CAMPAIGN and p["campaign_run_attempt"] == 1, "original campaign mismatch")
    reject(a["model_alias"] == MODEL and a["model_digest"] == MODEL_DIGEST, "model mismatch")
    reject(a["observed_records"] == 60 and a["unique_slots"] == 60 and a["expected_runs"] == 60, "incomplete source cohort")
    reject(a["errors"] == [] and a["status"] == "COMPLETE_60_EXPLORATORY_SCRIPTED_REPAIR_RUNS", "non-complete source status")
    reject(item["status"] == "Research", "invalid research status")
    return item


def exact_discordant_p(far_wins: int, control_wins: int) -> float:
    n = far_wins + control_wins
    if n == 0:
        return 1.0
    # Exact two-sided conditional binomial/McNemar test under equal discordant odds.
    return min(1.0, 2.0 * sum(math.comb(n, k) for k in range(min(far_wins, control_wins) + 1)) / 2 ** n)


def descriptive_analysis(record: dict) -> dict:
    pairs = record["paired_outcomes"]
    reject(type(pairs) is list and len(pairs) == 30, "not 30 pairs")
    keys = [p["task_id"] for p in pairs]
    reject(set(keys) == {f"FWE-{i:03d}" for i in range(1, 31)}, "task identity not exactly 30")
    reject(len(keys) == len(set(keys)), "duplicate task IDs")
    d, times, inputs, outputs = [], [], [], []
    per_family = {}
    for p in pairs:
        for arm in ("control", "treatment"):
            reject(p[f"{arm}_outcome"] in ("SUCCESS", "FAILURE"), "unknown outcome")
            for metric in ("generation_seconds", "input_tokens", "output_tokens"):
                v = p[f"{arm}_{metric}"]
                reject(type(v) in (int, float) and math.isfinite(v) and v >= 0, "invalid metric: " + metric)
        c = int(p["control_outcome"] == "SUCCESS")
        f = int(p["treatment_outcome"] == "SUCCESS")
        dif = f - c
        d.append(dif)
        times.append(p["treatment_generation_seconds"] - p["control_generation_seconds"])
        inputs.append(p["treatment_input_tokens"] - p["control_input_tokens"])
        outputs.append(p["treatment_output_tokens"] - p["control_output_tokens"])
        group = (int(p["task_id"].split("-")[1]) - 1) // 3
        per_family.setdefault(group, []).append(dif)
    a = record["analysis"]
    control = sum(p["control_outcome"] == "SUCCESS" for p in pairs)
    far = sum(p["treatment_outcome"] == "SUCCESS" for p in pairs)
    pos, neg = d.count(1), d.count(-1)
    reject((control, far, pos, neg) == (11, 10, 1, 2), "aggregate effect disagreeing with source")
    reject(a["control_success"] == control and a["treatment_success"] == far, "published count drift")
    reject(abs(a["paired_success_delta"] - statistics.mean(d)) < 1e-12, "published paired delta drift")
    reject(abs(a["mean_generation_elapsed_delta_seconds"] - statistics.mean(times)) < 1e-9, "published time effect drift")
    reject(abs(a["mean_input_token_delta"] - statistics.mean(inputs)) < 1e-9, "published token effect drift")
    reject(abs(a["mean_output_token_delta"] - statistics.mean(outputs)) < 1e-9, "published output drift")
    reject(abs(a["exploratory_exact_sign_test_two_sided_p"] - exact_discordant_p(pos, neg)) < 1e-12, "published McNemar mismatch")
    reject(len(per_family) == 10 and all(len(v) == 3 for v in per_family.values()), "uncontrolled family dependence")
    rng = random.Random(60520261102)
    boot = sorted(statistics.mean(rng.choice(d) for _ in range(30)) for _ in range(10000))
    boot_ci = [boot[249], boot[9749]]
    reject(boot_ci == a["exploratory_paired_bootstrap_interval_95pct"], "published task bootstrap drift")

    # New, clearly post-hoc sensitivity: resample TEN clusters instead of 30 tasks.
    rng2 = random.Random(12062026)
    family_rows = [per_family[i] for i in range(10)]
    fam_boot = sorted(statistics.mean(sum((rng2.choice(family_rows) for _ in range(10)), []))
                      for _ in range(10000))
    clustered_ci = [fam_boot[249], fam_boot[9749]]
    control_elapsed = statistics.mean(p["control_generation_seconds"] for p in pairs)
    far_elapsed = statistics.mean(p["treatment_generation_seconds"] for p in pairs)
    reject(control_elapsed > 0 and far_elapsed > 0, "missing timing")
    artifacts = record["artifact_manifest"]
    reject(type(artifacts) is list and len(artifacts) == 31, "missing original artifact inventory")
    all_names = {x["name"] for x in artifacts}
    reject(all_names == {"fwe-free-aggregate-report"} |
           {f"fwe-free-pair-{i}" for i in range(30)}, "artifact names not complete")
    for x in artifacts:
        reject(type(x["id"]) is int and x["id"] > 0, "invalid artifact id")
        reject(re.fullmatch(r"sha256:[0-9a-f]{64}", x["digest"]) is not None, "invalid artifact digest")
    return {
        "schema": REPORT_NAME,
        "status": "VALID_SECONDARY_ANALYSIS_OF_REGISTERED_FINITE_CORPUS",
        "source_record_git_blob": RECORD_GIT_BLOB,
        "source_execution_sha": EXECUTED_SHA,
        "source_run": CAMPAIGN,
        "primary_corpus": {"n_pairs": 30, "n_related_families": 10,
                           "n_model_runs": 60, "first_attempts_per_arm": 30,
                           "model": MODEL, "model_digest": MODEL_DIGEST},
        "success": {
            "control": control, "far": far,
            "control_fraction": control / 30, "far_fraction": far / 30,
            "far_minus_control": statistics.mean(d),
            "both_succeeded": sum(p["control_outcome"] == "SUCCESS" and p["treatment_outcome"] == "SUCCESS" for p in pairs),
            "both_failed": sum(p["control_outcome"] == "FAILURE" and p["treatment_outcome"] == "FAILURE" for p in pairs),
            "far_only": pos, "control_only": neg,
            "exact_discordant_two_sided_p_exploratory": exact_discordant_p(pos, neg),
            "task_bootstrap_95pct_exploratory": boot_ci,
            "family_cluster_bootstrap_95pct_post_hoc": clustered_ci,
        },
        "generation": {
            "control_mean_seconds": control_elapsed, "far_mean_seconds": far_elapsed,
            "far_minus_control_seconds": statistics.mean(times),
            "far_over_control_ratio": far_elapsed / control_elapsed,
            "mean_additional_input_tokens": statistics.mean(inputs),
            "mean_additional_output_tokens": statistics.mean(outputs),
        },
        "audit": {
            "all_31_original_artifact_identifiers_available": True,
            "original_raw_replay_in_this_pass": False,
            "frozen_source_replay": "REQUIRES_VERIFY_RAW_AND_REPLAY",
            "far_specific_causal_effect_identified": False,
            "generic_matched_active_comparator_present": False,
            "general_purpose_agent_reliability_established": False,
            "external_independent_replication": False,
        },
        "verdict": "NO_IMPROVEMENT_ESTABLISHED; GENERAL_EFFECT_INCONCLUSIVE",
        "nonclaims": [
            "The retrospective bootstrap is not a population confidence interval.",
            "The model ran one-shot toy repair, not general-purpose autonomous agents.",
            "Treatment bundled more instruction/context; the FAR-specific mechanism is not isolated.",
            "No active generic reasoning arm or FAR mechanism ablation was executed.",
            "No external evaluator independently selected this corpus.",
            "This source does not determine efficacy on unbounded tasks or other models.",
        ],
    }


def github_download(url: str, token: str) -> bytes:
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "far-research-raw-evidence-replay",
    })
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = resp.read(10_000_001)
    reject(len(data) <= 10_000_000, "oversized artifact response")
    return data


def verify_archived_raw(record: dict, token: str, destination: Path) -> dict:
    reject(bool(token), "GitHub read-only token needed for raw artifact access")
    destination.mkdir(parents=True, exist_ok=True)
    expected = {x["name"]: x for x in record["artifact_manifest"]}
    url = f"https://api.github.com/repos/n0tf0und0ut/Project-FAR/actions/runs/{CAMPAIGN}/artifacts?per_page=100"
    page = strict_json(github_download(url, token))
    listed = {x["name"]: x for x in page["artifacts"]}
    reject(set(listed) == set(expected), "hosted campaign artifacts missing or unexpected")
    nfiles, total = 0, 0
    for name in sorted(expected):
        meta = listed[name]
        x = expected[name]
        reject(meta["id"] == x["id"] and meta["digest"] == x["digest"], "hosted archive metadata drift")
        reject(not meta["expired"], "original raw evidence expired")
        blob = github_download(
            f"https://api.github.com/repos/n0tf0und0ut/Project-FAR/actions/artifacts/{x['id']}/zip", token)
        reject("sha256:" + hashlib.sha256(blob).hexdigest() == x["digest"], "original zip hash mismatch: " + name)
        reject(zipfile.is_zipfile(io.BytesIO(blob)), "non-ZIP artifact")
        if name == "fwe-free-aggregate-report":
            continue
        expected_index = int(name.removeprefix("fwe-free-pair-"))
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            infos = zf.infolist()
            reject(0 < len(infos) <= 100, "unexpected ZIP member count")
            reject(sum(f.file_size for f in infos) <= 5_000_000, "ZIP expanded size budget exceeded")
            found_pair = False
            for info in infos:
                if info.is_dir():
                    continue
                p = Path(info.filename)
                reject(not p.is_absolute() and ".." not in p.parts and p.parts, "unsafe ZIP path")
                reject(info.file_size <= 1_000_000, "ZIP member budget exceeded")
                if p.name == f"pair-{expected_index}.json":
                    found_pair = True
                tgt = destination / p
                reject(not tgt.exists(), "duplicate evidence member: " + str(p))
                tgt.parent.mkdir(parents=True, exist_ok=True)
                raw = zf.read(info)
                reject(len(raw) == info.file_size, "ZIP byte-count mismatch")
                tgt.write_bytes(raw)
                nfiles += 1
                total += len(raw)
            reject(found_pair, "missing pair observation in original archive")
    pairs = list(destination.glob("pair-*.json"))
    reject(len(pairs) == 30, "raw pair count incomplete")
    return {
        "raw_artifact_zip_count_verified": 31,
        "original_pair_archives_extracted": 30,
        "raw_file_count": nfiles,
        "uncompressed_evidence_bytes": total,
        "archive_run": CAMPAIGN,
        "all_artifact_hashes_match_original_manifest": True,
        "frozen_analyzer_replay_still_required": True,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path)
    p.add_argument("--verify-raw", action="store_true")
    p.add_argument("--raw-destination", type=Path)
    args = p.parse_args()
    record = read_source_record()
    report = descriptive_analysis(record)
    if args.verify_raw:
        reject(args.raw_destination is not None, "--raw-destination required")
        report["raw_artifact_audit"] = verify_archived_raw(
            record, os.environ.get("GITHUB_TOKEN", ""), args.raw_destination)
        report["audit"]["original_raw_replay_in_this_pass"] = True
        report["audit"]["frozen_source_replay"] = "RAW_ARCHIVES_VERIFIED; RUN_FROZEN_ANALYZER_SEPARATELY"
    data = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(data)
    print(data)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, urllib.error.URLError) as exc:
        print("FAIL_CLOSED: " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        raise SystemExit(2)
