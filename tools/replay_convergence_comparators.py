#!/usr/bin/env python3
"""Relocate the frozen exposed-fixture probe without rewriting historical bytes.

The default only regrades retained outputs using the pinned source references.
--run-sdk additionally executes the original probe with its exact optional SDKs.
Neither mode is a new confirmatory experiment or external scientific replication.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import platform
import socket
import stat
import sys
import traceback
import uuid
import zipfile

ARCHIVE_SHA256 = "ef562ebb7adebf3c68159d25e8a32d9148e0b1f0b946060e1f0ae65456bf3c00"
MANIFEST_SHA256 = "c740b94b4f2945d3ff2bdb5ea96519d3d292751ebcc1651a1e38bfa61626ad07"
SCRIPT_SHA256 = "ca682340a90438f0126907daf8cdf8c3e5e37df148d5eee38e079bf7ef293c50"
PROTOCOL_SHA256 = "ea0e0102f73a3197cff2a9c0afb5d425055bbc04a27fdee14680c2c7377eb18d"
ORIGINAL_ROOT = "/workspace/scratch/e1c41a89d76e/Project-FAR"
EVIDENCE_RELATIVE = "research/repository-convergence/2026-11-03"
CASE_FILE = "commercial/far-investigation-audit/evaluation/internal-001/cases-v1.json"
SOURCE_HASHES = {
    CASE_FILE: "b280e084abc934569caf55021a375dcde9efc2e0e552d39d1b67bd6ce7dbc705",
    "commercial/far-investigation-audit/engine.py": "f51ca95b677586ae4a8063254c6b818da93777616ed937bcc02bfe084f26f0f0",
    "tools/run_internal_investigation_evaluation.py": "7f7e762dfcd3c5e5ae7067800b7ed84ed7dd52c960d46c997aabb5b623a0cb92",
}
# Imported by engine.py; supplementary launcher binding from the same source
# commit, not a retrospective edit to the original protocol.
STRUCTURED_FILE = "commercial/far-investigation-audit/structured.py"
STRUCTURED_SHA256 = "a1d89de211d933524a0f0d6568f7e6492cbd3d28a3d586e63e830b0a7fec7814"
VERSIONS = {"sympy": "1.14.0", "langsmith": "0.14.17", "arize-phoenix-evals": "3.9.5"}
SCOPE = "EXPOSED_EXISTING_FIXTURE_SOFTWARE_INTEROPERABILITY_ONLY"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def parse(raw):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            require(key not in out, "duplicate JSON key: " + key)
            out[key] = value
        return out
    def invalid(value):
        raise ValueError("nonfinite JSON: " + value)
    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def safe_path(value, *, exists=True):
    """Reject symlinks in every component, including dangling final links."""
    path = Path(os.path.abspath(value))
    for component in [*reversed(path.parents), path]:
        require(not component.is_symlink(), "symlink path forbidden: " + str(component))
    if exists:
        require(path.exists(), "missing path: " + str(path))
    return path


def member_name(name):
    require(isinstance(name, str) and name and "\\" not in name,
            "invalid evidence member name")
    require(PurePosixPath(name).name == name and name not in {".", ".."},
            "evidence member must be a flat file: " + name)


def verify_members(members):
    require("evidence-manifest.json" in members, "missing evidence manifest")
    require(digest(members["evidence-manifest.json"]) == MANIFEST_SHA256,
            "historical manifest identity mismatch")
    manifest = parse(members["evidence-manifest.json"])
    expected = {"evidence-manifest.json"}
    for item in manifest["files"]:
        name = item["path"]
        member_name(name)
        require(name not in expected, "duplicate manifest member: " + name)
        expected.add(name)
        require(name in members, "missing evidence member: " + name)
        raw = members[name]
        require(len(raw) == item["bytes"] and digest(raw) == item["sha256"],
                "evidence member identity mismatch: " + name)
    require(set(members) == expected, "unexpected evidence members")
    require(digest(members["local_sdk_probe.py"]) == SCRIPT_SHA256, "frozen script identity mismatch")
    require(digest(members["local-sdk-protocol.json"]) == PROTOCOL_SHA256, "frozen protocol identity mismatch")
    protocol = parse(members["local-sdk-protocol.json"])
    require(protocol["script_sha256"] == SCRIPT_SHA256 and protocol["inputs"] == SOURCE_HASHES
            and protocol["versions"] == VERSIONS and protocol["scope"] == SCOPE
            and protocol["scientific_independence"] is False
            and protocol["new_confirmatory_experiment"] is False, "unexpected protocol boundary")
    roots = [node.value for node in ast.parse(members["local_sdk_probe.py"]).body
             if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "ROOT" for t in node.targets)]
    require(len(roots) == 1 and isinstance(roots[0], ast.Call)
            and isinstance(roots[0].func, ast.Name) and roots[0].func.id == "Path"
            and len(roots[0].args) == 1 and ast.literal_eval(roots[0].args[0]) == ORIGINAL_ROOT,
            "unexpected frozen ROOT mapping")
    return protocol


def load_evidence(evidence):
    evidence = safe_path(evidence)
    if evidence.is_dir():
        members = {}
        for path in evidence.iterdir():
            member_name(path.name)
            path = safe_path(path)
            require(path.is_file(), "evidence must contain only regular files")
            members[path.name] = path.read_bytes()
        protected = evidence
    else:
        require(evidence.is_file(), "evidence is not a regular file")
        raw = evidence.read_bytes()
        require(digest(raw) == ARCHIVE_SHA256, "historical archive identity mismatch")
        members = {}
        with zipfile.ZipFile(evidence) as archive:
            for info in archive.infolist():
                member_name(info.filename)
                require(info.filename not in members, "duplicate archive member")
                require(not stat.S_ISLNK(info.external_attr >> 16), "archive symlink forbidden")
                members[info.filename] = archive.read(info)
        protected = evidence.parent
    verify_members(members)
    return members, protected


def verify_sources(checkout):
    checkout = safe_path(checkout)
    require(checkout.is_dir(), "checkout must be a directory")
    for name, expected in {**SOURCE_HASHES, STRUCTURED_FILE: STRUCTURED_SHA256}.items():
        path = safe_path(checkout / name)
        require(path.is_relative_to(checkout) and path.is_file(), "source escape: " + name)
        require(digest(path.read_bytes()) == expected, "source identity mismatch: " + name)
    cases = parse((checkout / CASE_FILE).read_bytes())["formal_comparison"]
    ids = [row["case_id"] for row in cases]
    require(len(cases) == 46 and len(set(ids)) == 46, "incomplete or duplicate source cases")
    return checkout, {row["case_id"]: row for row in cases}


def regrade(members, cases):
    """Recompute both SDKs' two metrics, bound to source case IDs/references."""
    require(len(cases) == 46, "expected 46 source cases")
    rows = {}
    arms = {}
    for arm in ("far", "sympy"):
        values = parse(members["langsmith-" + arm + ".json"])["rows"]
        arm_rows = []
        for row in values:
            key = (row["arm"], row["case_id"])
            require(row["arm"] == arm and row["case_id"] in cases, "unknown target case")
            require(key not in rows, "duplicate target trial")
            require(row["reference"] == cases[row["case_id"]]["reference_status"], "source reference mismatch")
            require(isinstance(row["status"], str) and row["error"] is None, "target error or malformed status")
            scores = {"status_match": int(row["status"] == row["reference"]),
                      "abstention": int(row["status"].startswith("NOT_CHECKED"))}
            require(row["sdk_scores"] == scores and all(type(v) in (int, float) for v in row["sdk_scores"].values()),
                    "incorrect LangSmith score")
            rows[key] = row
            arm_rows.append(row)
        require({r["case_id"] for r in arm_rows} == set(cases), "missing target trials")
        arms[arm] = {"n": len(arm_rows), "reference_match": sum(r["sdk_scores"]["status_match"] for r in arm_rows),
                     "abstentions": sum(r["sdk_scores"]["abstention"] for r in arm_rows), "target_errors": 0}
    phoenix = parse(members["phoenix-scores.json"])
    seen = set()
    for row in phoenix:
        key = (row["arm"], row["case_id"])
        require(key in rows and key not in seen, "unknown or duplicate Phoenix trial")
        seen.add(key)
        require(all(row[field] == rows[key][field] for field in ("status", "reference", "sdk_scores", "error")),
                "Phoenix target/reference mismatch")
        for metric, score in rows[key]["sdk_scores"].items():
            result = row[metric + "_score"]
            require(result["name"] == metric and result["score"] == score and type(result["score"]) in (int, float),
                    "incorrect Phoenix score")
            details = row[metric + "_execution_details"]
            require(details["status"] == "COMPLETED" and details["exceptions"] == [], "Phoenix evaluator failed")
    require(seen == set(rows), "missing Phoenix trials")
    expected_arms = {"far": {"n": 46, "reference_match": 40, "abstentions": 6, "target_errors": 0},
                     "sympy": {"n": 46, "reference_match": 46, "abstentions": 0, "target_errors": 0}}
    require(arms == expected_arms, "unexpected bounded outcome counts")
    summary = parse(members["local-sdk-results.json"])
    require(summary["arms"] == arms and summary["cases"] == 46 and summary["target_executions"] == 92
            and summary["phoenix_rows"] == 92 and summary["protocol_sha256"] == PROTOCOL_SHA256
            and summary["scope"] == SCOPE and summary["model_calls"] == 0
            and summary["network_connect_attempts"] == [], "summary mismatch")
    return {"cases": 46, "target_outputs_regraded": 92, "langsmith_scores_recomputed": 184,
            "phoenix_scores_recomputed": 184, "arms": arms}, rows


def reserve_output(output, protected):
    output = safe_path(output, exists=False)
    require(output.parent.is_dir(), "output parent must already exist")
    for root in protected:
        root = safe_path(root, exists=False)
        require(not output.is_relative_to(root) and not root.is_relative_to(output),
                "output overlaps original evidence: " + str(root))
    # mkdir is the exclusive reservation: never reuse even an empty directory.
    output.mkdir(mode=0o700)
    return output


def run_sdk(checkout, output, members, cases, expected_rows):
    versions = {name: importlib.metadata.version(name) for name in VERSIONS}
    require(versions == VERSIONS, "optional SDK version mismatch: " + str(versions))
    frozen = output / "frozen-inputs"
    frozen.mkdir(mode=0o700)
    script = frozen / "local_sdk_probe.py"
    script.write_bytes(members["local_sdk_probe.py"])
    script.chmod(0o400)
    frozen.chmod(0o500)
    sdk_output = output / "sdk-output"
    sdk_output.mkdir(mode=0o700)
    # run() reads its original prospective protocol from HERE. Retain exact bytes.
    protocol_path = sdk_output / "local-sdk-protocol.json"
    protocol_path.write_bytes(members["local-sdk-protocol.json"])
    protocol_path.chmod(0o400)
    for name in ("engine", "structured"):
        if name in sys.modules:
            require(Path(sys.modules[name].__file__).resolve() == checkout / ("commercial/far-investigation-audit/" + name + ".py"),
                    "preloaded module belongs to another checkout: " + name)
    spec = importlib.util.spec_from_file_location("frozen_convergence_probe", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(str(module.ROOT) == ORIGINAL_ROOT and digest(Path(module.__file__).read_bytes()) == SCRIPT_SHA256,
            "frozen module identity mismatch")
    module.ROOT, module.HERE = checkout, sdk_output
    old_path = sys.path[:]
    old_connect, old_create_connection = socket.socket.connect, socket.create_connection
    try:
        with (output / "sdk-run.log").open("w") as log, redirect_stdout(log), redirect_stderr(log):
            module.run()
    finally:
        socket.socket.connect, socket.create_connection = old_connect, old_create_connection
        sys.path[:] = old_path
    fresh = {name: (sdk_output / name).read_bytes() for name in (
        "langsmith-far.json", "langsmith-sympy.json", "phoenix-scores.json", "local-sdk-results.json")}
    report, fresh_rows = regrade(fresh, cases)
    require(fresh_rows == expected_rows, "SDK replay differs from original per-case outputs/scores")
    require(digest(script.read_bytes()) == SCRIPT_SHA256 and digest(protocol_path.read_bytes()) == PROTOCOL_SHA256,
            "frozen bytes changed during execution")
    return report


def replay(checkout, evidence, output, *, execute_sdk=False):
    members, evidence_root = load_evidence(evidence)
    checkout, cases = verify_sources(checkout)
    report, expected_rows = regrade(members, cases)
    output = reserve_output(output, [evidence_root, checkout / EVIDENCE_RELATIVE])
    freeze = {"schema": "far-convergence-comparator-replay/1", "status": "FROZEN_BEFORE_OPTIONAL_SDK_EXECUTION",
              "replay_id": "convergence-replay-" + uuid.uuid4().hex,
              "timestamp": datetime.now(timezone.utc).isoformat(), "scope": SCOPE,
              "new_confirmatory_experiment": False, "scientific_independence": False,
              "mode": "run-sdk" if execute_sdk else "retained-output-regrade",
              "original_archive_sha256": ARCHIVE_SHA256, "original_protocol_sha256": PROTOCOL_SHA256,
              "original_script_sha256": SCRIPT_SHA256, "original_root": ORIGINAL_ROOT,
              "checkout": str(checkout), "output": str(output), "source_sha256": SOURCE_HASHES,
              "supplementary_import_sha256": {STRUCTURED_FILE: STRUCTURED_SHA256},
              "launcher_sha256": digest(Path(__file__).read_bytes()), "python": platform.python_version(),
              "optional_sdk_versions_required": VERSIONS, "case_ids": sorted(cases),
              "nonclaims": parse(members["local-sdk-protocol.json"])["nonclaims"]}
    write(output / "replay-freeze.json", freeze)
    receipt = {"replay_id": freeze["replay_id"], "freeze_sha256": digest((output / "replay-freeze.json").read_bytes()),
               "retained_output_regrade": report, "sdk_executed": False}
    try:
        if execute_sdk:
            receipt["sdk_replay"] = run_sdk(checkout, output, members, cases, expected_rows)
            receipt["sdk_executed"] = True
        receipt["status"] = "COMPLETED"
    except BaseException as exc:
        receipt.update(status="FAILED", exception_type=type(exc).__name__, exception=str(exc))
        (output / "failure-traceback.txt").write_text(traceback.format_exc())
        raise
    finally:
        receipt["files"] = {str(p.relative_to(output)): digest(p.read_bytes())
                            for p in sorted(output.rglob("*")) if p.is_file()}
        write(output / "replay-receipt.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True, help="checkout with exact frozen source bytes")
    parser.add_argument("--evidence", type=Path, required=True, help="original ZIP or exact extracted evidence directory")
    parser.add_argument("--output", type=Path, required=True, help="new directory outside original evidence; parent must exist")
    parser.add_argument("--run-sdk", action="store_true", help="also rerun the exposed engineering probe using pinned SDKs")
    args = parser.parse_args()
    print(json.dumps(replay(args.checkout, args.evidence, args.output, execute_sdk=args.run_sdk), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
