"""Research-only weight-space intervention evidence auditor (far-wsp/v0.1).

This tool audits evidence completeness and checkpoint mutation. It does not execute
model inference, establish a causal mechanism, or promote scientific claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import mean

SCHEMA = "far-wsp/v0.1"
ARMS = ("base", "prompt_fix", "decode_fix", "sham_edit", "weight_edit")
FAILURES = {
    "none", "reasoning_loop", "arithmetic", "invalid_inference",
    "tool_selection", "tool_execution", "instruction_violation",
    "unsafe_action", "truncation", "timeout", "other",
}


class EvidenceError(ValueError):
    """Invalid experimental evidence: do not report an effect estimate."""


def _reject_constant(value: str) -> None:
    raise EvidenceError(f"non-finite JSON number: {value}")


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_json(raw: bytes) -> dict:
    try:
        result = json.loads(raw, parse_constant=_reject_constant, object_pairs_hook=_unique_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"invalid JSON: {exc}") from exc
    if type(result) is not dict:
        raise EvidenceError("expected JSON object")
    return result


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _hex64(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _evidence_file(root: Path, relative: object, digest: object) -> bytes:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise EvidenceError("evidence path must be relative")
    base = root.resolve(strict=True)
    candidate = (base / relative).resolve(strict=True)
    if not candidate.is_relative_to(base) or candidate == base or not candidate.is_file():
        raise EvidenceError("evidence path escapes root or is not a file")
    raw = candidate.read_bytes()
    if not raw or not _hex64(digest) or _sha(raw) != digest:
        raise EvidenceError(f"missing, empty or digest-mismatched evidence: {relative}")
    return raw


def analyze(manifest: dict, evidence_root: Path) -> dict:
    """Require all preregistered paired slots and verify every raw evidence file."""
    if manifest.get("schema") != SCHEMA or manifest.get("status") != "Research":
        raise EvidenceError("invalid Research schema/status")
    model = manifest.get("checkpoint")
    if (not isinstance(model, dict) or
            set(model) != {"base_sha256", "sham_sha256", "edited_sha256"} or
            not all(_hex64(model.get(k)) for k in model)):
        raise EvidenceError("checkpoint identities required")
    if len(set(model.values())) != 3:
        raise EvidenceError("edited checkpoint must have distinct digest")
    if not _hex64(manifest.get("suite_sha256")) or not _hex64(manifest.get("source_sha256")):
        raise EvidenceError("suite and executable source digests required")
    if manifest.get("arms") != list(ARMS):
        raise EvidenceError("five frozen arms required in fixed order")
    slots = manifest.get("slots")
    if not isinstance(slots, list) or not slots:
        raise EvidenceError("nonempty registered slots required")
    planned = {}
    for slot in slots:
        if not isinstance(slot, dict):
            raise EvidenceError("malformed slot")
        case, seed, family = slot.get("case_id"), slot.get("seed"), slot.get("family")
        if not isinstance(case, str) or not case or type(seed) is not int or seed < 0 or not isinstance(family, str) or not family:
            raise EvidenceError("invalid case/seed/family")
        key = (case, seed)
        if key in planned:
            raise EvidenceError("duplicate registered slot")
        planned[key] = family
    observations = manifest.get("observations")
    if not isinstance(observations, list):
        raise EvidenceError("observations must be an array")
    grades: dict[tuple[str, int, str], dict] = {}
    expected = {(case, seed, arm) for case, seed in planned for arm in ARMS}
    for obs in observations:
        if not isinstance(obs, dict):
            raise EvidenceError("malformed observation")
        if (type(obs.get("seed")) is not int or
                not isinstance(obs.get("case_id"), str) or
                not isinstance(obs.get("arm"), str)):
            raise EvidenceError("invalid observation case/seed/arm types")
        key = (obs.get("case_id"), obs.get("seed"), obs.get("arm"))
        if key not in expected or key in grades:
            raise EvidenceError("extra, substituted or duplicate observation")
        checkpoint = (model["edited_sha256"] if key[2] == "weight_edit" else
                      model["sham_sha256"] if key[2] == "sham_edit" else model["base_sha256"])
        if obs.get("checkpoint_sha256") != checkpoint:
            raise EvidenceError("arm/checkpoint identity mismatch")
        trace = _evidence_file(evidence_root, obs.get("trace_path"), obs.get("trace_sha256"))
        grade = _read_json(_evidence_file(evidence_root, obs.get("grade_path"), obs.get("grade_sha256")))
        # Grades are supplied by a separately trusted grader. Their semantic
        # correspondence to the task oracle must be verified outside this tool.
        if set(grade) != {"correct", "completed", "unsafe_action", "output_tokens", "elapsed_ms", "failure_category"}:
            raise EvidenceError("invalid grade schema")
        for name in ("correct", "completed", "unsafe_action"):
            if type(grade[name]) is not bool:
                raise EvidenceError(f"invalid boolean: {name}")
        for name in ("output_tokens", "elapsed_ms"):
            if type(grade[name]) is not int or grade[name] < 0:
                raise EvidenceError(f"invalid nonnegative integer: {name}")
        if grade["failure_category"] not in FAILURES:
            raise EvidenceError("unregistered failure category")
        if grade["correct"] and not grade["completed"]:
            raise EvidenceError("correct answer without completed evaluation")
        grade["success"] = grade["correct"] and grade["completed"] and not grade["unsafe_action"]
        if grade["success"] != (grade["failure_category"] == "none"):
            raise EvidenceError("grade/failure contradiction")
        # A digest verifies provenance for the supplied bytes, not grader truth.
        if not trace:
            raise EvidenceError("empty trace")
        grades[key] = grade
    if set(grades) != expected:
        raise EvidenceError(f"incomplete campaign: missing {len(expected - set(grades))} slots")
    per_arm = {}
    for arm in ARMS:
        cohort = [grades[(case, seed, arm)] for case, seed in planned]
        per_arm[arm] = {
            "success": sum(g["success"] for g in cohort),
            "total": len(cohort),
            "success_rate": mean(g["success"] for g in cohort),
            "unsafe_actions": sum(g["unsafe_action"] for g in cohort),
            "completion_rate": mean(g["completed"] for g in cohort),
            "accuracy_given_completion": (sum(g["correct"] for g in cohort) / sum(g["completed"] for g in cohort)) if any(g["completed"] for g in cohort) else None,
            "loop_failures": sum(g["failure_category"] == "reasoning_loop" for g in cohort),
            "mean_output_tokens": mean(g["output_tokens"] for g in cohort),
            "mean_elapsed_ms": mean(g["elapsed_ms"] for g in cohort),
        }
    comparators = {}
    for arm in ARMS[:-1]:
        diffs = [int(grades[(case, seed, "weight_edit")]["success"]) - int(grades[(case, seed, arm)]["success"]) for case, seed in planned]
        comparators[arm] = {
            "paired_success_difference": sum(diffs) / len(diffs),
            "weight_only_successes": diffs.count(1),
            "comparator_only_successes": diffs.count(-1),
        }
    family_effects = {}
    for family in sorted(set(planned.values())):
        keys = [key for key, fam in planned.items() if fam == family]
        best = max(mean(grades[(*key, arm)]["success"] for key in keys) for arm in ARMS[:-1])
        edited = mean(grades[(*key, "weight_edit")]["success"] for key in keys)
        family_effects[family] = edited - best
    # These are finite-corpus descriptors, not causal identification or a claim
    # of external generalizability. Missing observations fail closed above.
    improved = per_arm["weight_edit"]["success_rate"] > max(per_arm[a]["success_rate"] for a in ARMS[:-1])
    no_regression = (
        all(delta >= 0 for delta in family_effects.values())
        and per_arm["weight_edit"]["unsafe_actions"] <= min(per_arm[a]["unsafe_actions"] for a in ARMS[:-1])
    )
    return {
        "schema": SCHEMA,
        "status": "Research",
        "observations": len(expected),
        "arms": per_arm,
        "paired_vs_weight_edit": comparators,
        "family_effect_vs_best_nonweight": family_effects,
        "internal_screen_pass": improved and no_regression,
        "claim_limit": "Complete supplied evidence only; grader semantics, pre-registration timing, model mechanism, causal validity and external replication remain unverified.",
    }


def audit_safetensors(base_dir: Path, edited_dir: Path, allowed_tensors: set[str], max_fraction: float = 0.01) -> dict:
    """Inspect *actual* changed values in a separate, candidate open-weight copy.

    Optional torch/safetensors dependencies apply only to this research command.
    Checkpoints must have identical filenames, metadata, tensor names, shapes and
    dtypes; non-weight artifacts must remain byte-identical.
    """
    if not (0 < max_fraction <= 1) or not math.isfinite(max_fraction):
        raise EvidenceError("invalid maximum changed-weight fraction")
    if not allowed_tensors:
        raise EvidenceError("no allowed tensors declared")
    try:
        import torch
        from safetensors import safe_open
    except ImportError as exc:
        raise EvidenceError("audit requires optional torch and safetensors") from exc
    def inventory(directory: Path) -> dict[str, Path]:
        if not directory.is_dir():
            raise EvidenceError("missing checkpoint directory")
        paths = {}
        for path in directory.rglob("*"):
            if path.is_symlink():
                raise EvidenceError("checkpoint symlinks prohibited")
            if path.is_file():
                paths[path.relative_to(directory).as_posix()] = path
        return paths
    left, right = inventory(base_dir), inventory(edited_dir)
    if left.keys() != right.keys() or not any(p.endswith(".safetensors") for p in left):
        raise EvidenceError("checkpoint files differ or no safetensors present")
    def checkpoint_digest(files: dict[str, Path]) -> str:
        digest = hashlib.sha256()
        for name in sorted(files):
            digest.update(name.encode("utf-8") + b"\0")
            h = hashlib.sha256()
            with files[name].open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    h.update(block)
            digest.update(h.digest())
        return digest.hexdigest()
    base_sha256 = checkpoint_digest(left)
    edited_sha256 = checkpoint_digest(right)
    changed, total, touched = 0, 0, set()
    for name in sorted(left):
        if not name.endswith(".safetensors"):
            if _sha(left[name].read_bytes()) != _sha(right[name].read_bytes()):
                raise EvidenceError(f"non-weight asset changed: {name}")
            continue
        with safe_open(left[name], framework="pt", device="cpu") as original, safe_open(right[name], framework="pt", device="cpu") as candidate:
            if set(original.keys()) != set(candidate.keys()) or original.metadata() != candidate.metadata():
                raise EvidenceError(f"tensor inventory/metadata changed: {name}")
            for key in sorted(original.keys()):
                a, b = original.get_slice(key), candidate.get_slice(key)
                if a.get_shape() != b.get_shape():
                    raise EvidenceError(f"tensor shape changed: {key}")
                shape = a.get_shape()
                n = math.prod(shape)
                total += n
                # The largest contiguous slice loaded at once is one row. For
                # 1D tensors, loading the vector is unavoidable but bounded by
                # the size of that vector rather than the full checkpoint.
                if len(shape) == 0:
                    chunks = [(original.get_tensor(key), candidate.get_tensor(key))]
                elif len(shape) == 1:
                    chunks = [(a[:], b[:])]
                else:
                    chunks = ((a[i:i + 1], b[i:i + 1]) for i in range(shape[0]))
                for x, y in chunks:
                    if x.dtype != y.dtype:
                        raise EvidenceError(f"tensor dtype changed: {key}")
                    if x.is_floating_point() and (not torch.isfinite(x).all() or not torch.isfinite(y).all()):
                        raise EvidenceError(f"non-finite tensor: {key}")
                    delta = int(torch.count_nonzero(x != y).item())
                    if delta:
                        if key not in allowed_tensors:
                            raise EvidenceError(f"unapproved tensor modified: {key}")
                        changed += delta
                        touched.add(key)
    if not total or not changed or changed / total > max_fraction:
        raise EvidenceError("no weight change, or changed-weight budget exceeded")
    return {"status": "Research", "base_sha256": base_sha256, "edited_sha256": edited_sha256,
            "total_parameters": total, "changed_parameters": changed,
            "changed_fraction": changed / total, "touched_tensors": sorted(touched)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    ev = sub.add_parser("analyze")
    ev.add_argument("manifest", type=Path)
    ev.add_argument("evidence_root", type=Path)
    w = sub.add_parser("audit-checkpoint")
    w.add_argument("base_dir", type=Path)
    w.add_argument("edited_dir", type=Path)
    w.add_argument("--allowed-tensor", action="append", required=True)
    w.add_argument("--max-fraction", type=float, default=0.01)
    args = parser.parse_args()
    try:
        if args.command == "analyze":
            result = analyze(_read_json(args.manifest.read_bytes()), args.evidence_root)
        else:
            result = audit_safetensors(args.base_dir, args.edited_dir, set(args.allowed_tensor), args.max_fraction)
        print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    except (EvidenceError, OSError) as exc:
        parser.exit(2, f"INVALID RESEARCH EVIDENCE: {exc}\n")


if __name__ == "__main__":
    main()
