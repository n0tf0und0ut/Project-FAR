#!/usr/bin/env python3
"""Read-only Cloudflare audit -> FAR PR finding-ledger handoff.

This converter does not run an audit, confirm findings, publish evidence,
assign FAR dispositions, or substitute for upstream validator/independent review.
It intentionally omits exploit payloads from its output.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / ".agents/skills/security-audit/report-schema.json"
MAX_INPUT = 5 * 1024 * 1024
MAX_FIELDS = 1000
MAX_DEPTH = 64
MAX_SOURCE_BYTES = 8 * 1024 * 1024
UPSTREAM_FINDINGS_VALIDATOR = ROOT / ".agents/skills/security-audit/validate-findings.cjs"
UPSTREAM_COVERAGE_VALIDATOR = ROOT / ".agents/skills/security-audit/validate-coverage-ledger.cjs"
SHA = re.compile(r"^[a-f0-9]{40}$")
FINGERPRINT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$")


class HandoffError(ValueError):
    """Input has not met the minimum safe advisory handoff conditions."""


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise HandoffError(f"duplicate JSON field: {key[:60]}")
        result[key] = value
    return result


def bound_tree(root: Any):
    stack = [(root, 0)]
    visited = 0
    while stack:
        value, depth = stack.pop()
        visited += 1
        if visited > 200_000:
            raise HandoffError("audit JSON node budget exceeded")
        if depth > MAX_DEPTH:
            raise HandoffError("audit JSON depth budget exceeded")
        if isinstance(value, dict):
            if len(value) > MAX_FIELDS:
                raise HandoffError("audit JSON object field budget exceeded")
            stack.extend((entry, depth + 1) for entry in value.values())
        elif isinstance(value, list):
            if len(value) > MAX_FIELDS:
                raise HandoffError("audit JSON array item budget exceeded")
            stack.extend((entry, depth + 1) for entry in value)


def safe_load_json(path: Path):
    """Read one bounded, regular, unlinked file and reject ambiguous JSON."""
    if path.is_symlink():
        raise HandoffError(f"symlinked input rejected: {path.name}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise HandoffError(f"not a singly linked regular input: {path.name}")
        if before.st_size > MAX_INPUT:
            raise HandoffError(f"input exceeds byte limit: {path.name}")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(MAX_INPUT + 1)
        after = os.fstat(fd)
        if (len(raw) > MAX_INPUT or before.st_size != len(raw)
                or (before.st_dev, before.st_ino, before.st_size)
                != (after.st_dev, after.st_ino, after.st_size)):
            raise HandoffError(f"input changed or exceeded limit: {path.name}")
    finally:
        os.close(fd)
    def invalid_constant(value):
        raise HandoffError(f"nonstandard JSON constant: {value}")
    try:
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicate_keys,
                          parse_constant=invalid_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise HandoffError(f"invalid JSON in {path.name}: {exc}") from exc
    bound_tree(data)
    return data


def current_head(root: Path):
    value = subprocess.run(
        ["git", "--no-replace-objects", "rev-parse", "--verify", "HEAD^{commit}"],
        cwd=root, capture_output=True, text=True, check=True, timeout=10
    ).stdout.strip()
    if not SHA.fullmatch(value):
        raise HandoffError("cannot resolve an exact local source commit")
    return value


def source_is_clean_and_tracked(root: Path):
    """Require an unmodified checkout and real Git-tracked evidence paths."""
    status = subprocess.run(
        ["git", "--no-replace-objects", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=root, capture_output=True, text=True, check=True, timeout=15,
    ).stdout
    if status:
        raise HandoffError("checkout is dirty; SHA alone cannot bind source evidence")
    tracked = subprocess.run(
        ["git", "--no-replace-objects", "ls-files", "--cached", "-z"],
        cwd=root, capture_output=True, check=True, timeout=15,
    ).stdout
    return {
        value.decode("utf-8", errors="surrogateescape")
        for value in tracked.split(b"\0") if value
    }


def clean_source_path(relative: str, source_root: Path):
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise HandoffError("invalid source evidence path")
    name = Path(relative)
    if name.is_absolute() or any(part in ("", ".", "..") for part in name.parts):
        raise HandoffError(f"unsafe source evidence path: {relative[:100]}")
    path = source_root / name
    if path.is_symlink() or not path.is_file():
        raise HandoffError(f"source evidence file missing or symlinked: {relative[:100]}")
    if not path.resolve().is_relative_to(source_root.resolve()):
        raise HandoffError("source evidence path escapes checkout")
    return path


def exact_committed_source(root: Path, relative: str, expected_head: str) -> bytes:
    """Read evidence from the immutable requested commit, never mutable HEAD."""
    if not SHA.fullmatch(expected_head):
        raise HandoffError("expected source commit must be a full SHA")
    spec = expected_head + ":" + relative
    try:
        measured = subprocess.run(
            ["git", "--no-replace-objects", "cat-file", "-s", spec], cwd=root, capture_output=True,
            check=True, timeout=15,
        ).stdout.strip()
        if not measured.isdigit() or int(measured) > MAX_SOURCE_BYTES:
            raise HandoffError("source evidence blob exceeds bounded validation")
        contents = subprocess.run(
            ["git", "--no-replace-objects", "cat-file", "blob", spec], cwd=root, capture_output=True,
            check=True, timeout=15,
        ).stdout
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise HandoffError("source evidence Git blob cannot be verified") from exc
    if len(contents) != int(measured):
        raise HandoffError("source Git blob changed while reading")
    return contents


def inspect_source_references(records: list, source_root: Path, expected_head: str):
    if not SHA.fullmatch(expected_head):
        raise HandoffError("expected source commit must be a full SHA")
    tracked = source_is_clean_and_tracked(source_root)
    verified: dict[str, bytes] = {}
    for item in records:
        for section in ("trace", "evidence"):
            for entry in item[section]:
                relative = entry["file"]
                path = clean_source_path(relative, source_root)
                if relative not in tracked:
                    raise HandoffError("source evidence path is not tracked by Git")
                line = entry["line"]
                if type(line) is not int or not 1 <= line <= 2_000_000:
                    raise HandoffError("invalid source evidence line")
                if relative not in verified:
                    committed = exact_committed_source(source_root, relative, expected_head)
                    if path.stat().st_size > MAX_SOURCE_BYTES:
                        raise HandoffError("source evidence file exceeds bounded validation")
                    with path.open("rb") as stream:
                        observed = stream.read(MAX_SOURCE_BYTES + 1)
                    if observed != committed:
                        raise HandoffError(
                            "source evidence bytes do not match requested commit Git blob"
                        )
                    verified[relative] = committed
                committed = verified[relative]
                count = committed.count(b"\n") + int(
                    bool(committed) and not committed.endswith(b"\n")
                )
                if line > count:
                    raise HandoffError(f"source line does not exist: {relative}:{line}")


def schema_compatible_with_far(source):
    """Remove only Cloudflare's nonstandard visibleContent assertion in memory.

    FAR's intentionally constrained local jsonschema package rejects custom
    keywords. We enforce that assertion separately below; the upstream Node
    validator remains the authoritative full-format check during the audit.
    The pinned vendor schema file is never changed.
    """
    if isinstance(source, dict):
        return {key: schema_compatible_with_far(value)
                for key, value in source.items() if key != "visibleContent"}
    if isinstance(source, list):
        return [schema_compatible_with_far(value) for value in source]
    return source


def validate_with_pinned_cloudflare(records: list, validator: Path = UPSTREAM_FINDINGS_VALIDATOR,
                                   label: str = "findings"):
    """Run the vendored authoritative validator on a private, immutable snapshot.

    The local JSON-Schema compatibility pass omits Cloudflare's nonstandard
    visibleContent assertion; this pinned Node tool enforces that constraint,
    Unicode scalar validity and the upstream semantic rules in full.
    """
    try:
        with tempfile.TemporaryDirectory(prefix="far-cloudflare-findings-") as tmp:
            snapshot = Path(tmp) / (label + ".json")
            snapshot.write_text(
                json.dumps(records, ensure_ascii=False, allow_nan=False,
                           separators=(",", ":")),
                encoding="utf-8",
            )
            result = subprocess.run(
                ["node", str(validator), str(snapshot)],
                cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True,
                timeout=30, check=False,
            )
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise HandoffError("pinned Cloudflare validator unavailable or invalid input") from exc
    if result.returncode:
        raise HandoffError("pinned Cloudflare validator rejected " + label)


def clean_text(value: str, max_chars=200):
    if not isinstance(value, str):
        raise HandoffError("invalid text field")
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise HandoffError("rendered metadata contains invalid Unicode scalar values") from exc
    safe = "".join(char for char in value if char == " " or ord(char) >= 32).strip()
    safe = safe.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for mark in ("|", "[", "]", "*", "_", "\u0060"):
        safe = safe.replace(mark, "\\" + mark)
    return safe[:max_chars]


def build_report(run_dir: Path, expected_head: str, source_root: Path = ROOT):
    if not SHA.fullmatch(expected_head):
        raise HandoffError("expected head must be a full 40-hex SHA")
    if current_head(source_root) != expected_head:
        raise HandoffError("checkout HEAD does not match requested exact head")
    if run_dir.is_symlink() or not run_dir.is_dir():
        raise HandoffError("audit output must be a real directory")

    meta = safe_load_json(run_dir / "run-metadata.json")
    coverage = safe_load_json(run_dir / "coverage-ledger.json")
    findings = safe_load_json(run_dir / "findings.json")
    if not isinstance(meta, dict) or not isinstance(coverage, list):
        raise HandoffError("invalid audit metadata or coverage ledger container")
    if meta.get("source_ref") != expected_head:
        raise HandoffError("audit source SHA does not match checkout")
    if meta.get("execution_policy") != "sandboxed-source-and-local-only":
        raise HandoffError("audit execution policy not verified from metadata")
    if meta.get("run_status") not in {"complete", "incomplete"}:
        raise HandoffError("audit has not reached a terminal state")
    if not isinstance(meta.get("run_id"), str) or not meta["run_id"]:
        raise HandoffError("audit run identifier missing")
    if meta.get("repo") not in {"Project-FAR", "n0tf0und0ut/Project-FAR"}:
        raise HandoffError("audit repository identity mismatch")

    if not isinstance(findings, list):
        raise HandoffError("audit findings must be an array")
    # Run pinned, bounded upstream validation before local jsonschema's
    # potentially quadratic unique-items comparison on hostile nested data.
    validate_with_pinned_cloudflare(coverage, UPSTREAM_COVERAGE_VALIDATOR, "coverage")
    validate_with_pinned_cloudflare(findings)
    schema = safe_load_json(SCHEMA)
    validator = Draft202012Validator(schema_compatible_with_far(schema))
    problems = list(validator.iter_errors(findings))
    if problems:
        raise HandoffError(f"findings schema rejected data: {problems[0].message[:160]}")
    fingerprints = [r["fingerprint"] for r in findings]
    if len(fingerprints) != len(set(fingerprints)):
        raise HandoffError("duplicate vulnerability fingerprints")
    if any(not FINGERPRINT.fullmatch(p) for p in fingerprints):
        raise HandoffError("invalid vulnerability fingerprint")
    inspect_source_references(findings, source_root, expected_head)

    status = meta["run_status"]
    rows = [
        "# Project FAR — advisory security-audit handoff",
        "",
        "**Not a FAR finding adjudication, independent external approval, or security clearance.**",
        "",
        f"- Source HEAD: {expected_head}",
        f"- Cloudflare run: {clean_text(meta['run_id'])}",
        f"- Audit run status: {status}",
        f"- Findings records: {len(findings)}",
        "- Upstream validators and independent record verification must be checked separately.",
        "- This handoff excludes exploit payloads, credentials, and reproduction commands.",
    ]
    if status == "incomplete":
        rows.append("- Audit incomplete: never interpret omitted candidates or deferred coverage as clear.")
    rows += [
        "",
        "| Fingerprint | Cloudflare verdict | Source | FAR disposition |",
        "|---|---|---|---|",
    ]
    for item in sorted(findings, key=lambda row: row["fingerprint"]):
        fingerprint = item["fingerprint"]
        locations = ", ".join(
            f"{clean_text(ref['file'], 160)}:{ref['line']}"
            for ref in item["trace"][:3]
        )
        rows.append(
            f"| {clean_text(fingerprint)} | {item['verdict']} | "
            f"{locations} | OPEN — FAR adjudication required |"
        )
    for item in sorted(findings, key=lambda row: row["fingerprint"]):
        rows += [
            "",
            f"## CF/{item['fingerprint']}: {clean_text(item['title'], 180)}",
            "",
            f"- Cloudflare verdict: **{item['verdict']}** (source assertion only)",
            "- FAR root-cause disposition: **OPEN / NOT ADJUDICATED**",
            f"- Source-reviewed SHA: {expected_head}",
            "- Required FAR evidence: independently inspect trace and root cause, "
            "verify safe reproducer, link review/thread IDs, and test regression before disposition.",
        ]
        if item["verdict"] == "confirmed":
            rows.append(
                f"- Cloudflare-reported severity (not FAR-verified): "
                f"{item['severity']['overall_severity']}"
            )
            rows.append("- Source-reported root cause: " +
                        clean_text(item["root_cause"], 400))
        else:
            rows.append("- Source-reported claim: " +
                        clean_text(item["claimed_root_cause"], 400))
            if item["verdict"] == "needs_validation":
                rows.append("- Blockers: " +
                            "; ".join(clean_text(v, 200)
                                      for v in item["blockers"][:5]))
    rows += [
        "",
        "This report was generated from source-bound, schema-checked records. "
        "It cannot establish their factual truth or an accepted FAR disposition.",
        "",
    ]
    return "\n".join(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        destination = args.output.resolve()
        if destination.is_relative_to(ROOT.resolve()):
            raise HandoffError("handoff output must be outside the source repository")
        if not destination.parent.is_dir() or args.output.is_symlink():
            raise HandoffError("output parent must already exist and output cannot be a symlink")
        report = build_report(args.run_dir, args.expected_head)
        # Exclusive create: preserve previously generated evidence.
        fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(report)
        print(f"Created advisory FAR handoff: {destination}")
        return 0
    except (HandoffError, OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f"FAIL Cloudflare handoff: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
