#!/usr/bin/env python3
"""Check the factory protocol source-registration record against GitHub.

Research provenance only. No agents, evidence signing, result publication,
PR approval, budget changes, trial execution, or superiority assertion.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.factory_evaluation_contract import validate as validate_protocol  # noqa: E402

SCHEMA = "far-factory-protocol-registration/1"
STUDY = "FAR-FACTORY-SELF-EVAL-001"
STATUS = "Research-protocol-source-identified-trial-not-executed"
REPO = "n0tf0und0ut/Project-FAR"
PROTOCOL_PATH = "research/factory-evaluation/protocol-v1.json"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")
FIELDS = {"schema", "status", "study_id", "repository", "protocol", "trial", "limitations"}
PROTOCOL_FIELDS = {"path", "merged_pr", "protected_source_commit", "git_blob_sha1", "file_sha256"}
TRIAL_FIELDS = {
    "cohort_admitted", "execution_manifest_frozen", "trial_executed",
    "verified_results_available", "superiority_claim_allowed",
}


class RegistrationError(ValueError):
    """Registration or independently queried source did not verify."""


def _pairs(entries: list[tuple[str, object]]) -> dict:
    out: dict = {}
    for key, value in entries:
        if key in out:
            raise RegistrationError("duplicate JSON key: " + key)
        out[key] = value
    return out


def _reject_nonfinite(token: str) -> object:
    raise RegistrationError("nonstandard JSON number: " + token)


def strict_json(data: bytes) -> object:
    if not data or len(data) > 262144:
        raise RegistrationError("empty or oversized JSON")
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_reject_nonfinite)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise RegistrationError("invalid UTF-8 JSON") from exc


def _shape(obj: object, fields: set[str], label: str) -> dict:
    if type(obj) is not dict or set(obj) != fields:
        raise RegistrationError("invalid " + label + " fields")
    return obj


def validate_registration(value: object) -> dict:
    obj = _shape(value, FIELDS, "registration")
    if (obj["schema"], obj["status"], obj["study_id"], obj["repository"]) != (SCHEMA, STATUS, STUDY, REPO):
        raise RegistrationError("incorrect research registration identity/status")
    protocol = _shape(obj["protocol"], PROTOCOL_FIELDS, "protocol")
    if protocol["path"] != PROTOCOL_PATH or type(protocol["merged_pr"]) is not int or protocol["merged_pr"] != 633:
        raise RegistrationError("incorrect protocol path or protected PR")
    if type(protocol["protected_source_commit"]) is not str or not SHA40.fullmatch(protocol["protected_source_commit"]):
        raise RegistrationError("missing immutable protected source commit")
    if type(protocol["git_blob_sha1"]) is not str or not SHA40.fullmatch(protocol["git_blob_sha1"]):
        raise RegistrationError("invalid Git blob SHA-1")
    if type(protocol["file_sha256"]) is not str or not SHA64.fullmatch(protocol["file_sha256"]):
        raise RegistrationError("invalid protocol SHA-256")
    trial = _shape(obj["trial"], TRIAL_FIELDS, "trial")
    if any(type(v) is not bool or v is not False for v in trial.values()):
        raise RegistrationError("registration must not claim a trial or scientific result")
    if type(obj["limitations"]) is not list or not obj["limitations"] or any(
        type(item) is not str or not item.strip() for item in obj["limitations"]
    ):
        raise RegistrationError("missing research limitations")
    return obj


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\x00" + data).hexdigest()


def verify_bytes(registration: dict, content: bytes) -> None:
    p = registration["protocol"]
    if hashlib.sha256(content).hexdigest() != p["file_sha256"]:
        raise RegistrationError("protocol SHA-256 mismatch")
    if git_blob_sha1(content) != p["git_blob_sha1"]:
        raise RegistrationError("Git blob SHA-1 mismatch")
    protocol = strict_json(content)
    try:
        validate_protocol(protocol)
    except ValueError as exc:
        raise RegistrationError("source protocol validation failed") from exc
    if protocol["study_id"] != registration["study_id"] or protocol["reference_repo"] != registration["repository"]:
        raise RegistrationError("registration and source protocol refer to different research")


def get_github_json(url: str) -> dict:
    if not url.startswith("https://api.github.com/repos/n0tf0und0ut/Project-FAR/"):
        raise RegistrationError("unexpected GitHub API origin or repository")
    request = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "Project-FAR-registration-source-check",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            data = response.read(262145)
    except (OSError, urllib.error.URLError) as exc:
        raise RegistrationError("trusted GitHub API query unavailable") from exc
    obj = strict_json(data)
    if type(obj) is not dict:
        raise RegistrationError("GitHub API response must be an object")
    return obj


def verify_live(registration: dict, fetch_json=get_github_json) -> str:
    """Verify immutable PR source, source bytes and current protected-main ancestry.

    This validates GitHub's hosted observation. It is not a signature, nor
    proof that the planned cohort and control/treatment runtime exist.
    """
    p = registration["protocol"]
    root = "https://api.github.com/repos/" + REPO + "/"
    pr = fetch_json(root + "pulls/633")
    if pr.get("merged") is not True or pr.get("merge_commit_sha") != p["protected_source_commit"]:
        raise RegistrationError("PR 633 was not observed merged at registered protected source SHA")
    branch = fetch_json(root + "branches/main")
    main = branch.get("commit")
    if branch.get("protected") is not True or type(main) is not dict or not SHA40.fullmatch(str(main.get("sha", ""))):
        raise RegistrationError("current protected main identity not verified")
    current_main = main["sha"]
    compare = fetch_json(root + "compare/" + p["protected_source_commit"] + "...main")
    if (compare.get("status") not in ("identical", "ahead")
        or type(compare.get("behind_by")) is not int or compare["behind_by"] != 0
        or type(compare.get("merge_base_commit")) is not dict
        or compare["merge_base_commit"].get("sha") != p["protected_source_commit"]
        or type(compare.get("head_commit")) is not dict
        or compare["head_commit"].get("sha") != current_main):
        raise RegistrationError("registered source is not verified ancestor of current protected main")
    source = fetch_json(root + "contents/" + PROTOCOL_PATH + "?ref=" + p["protected_source_commit"])
    if source.get("type") != "file" or source.get("sha") != p["git_blob_sha1"] or source.get("encoding") != "base64":
        raise RegistrationError("GitHub source file/blob identity mismatch")
    encoded = source.get("content")
    if type(encoded) is not str:
        raise RegistrationError("missing GitHub file content")
    try:
        raw = base64.b64decode("".join(encoded.split()), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise RegistrationError("malformed source base64 content") from exc
    if type(source.get("size")) is not int or source["size"] != len(raw):
        raise RegistrationError("GitHub-reported byte size mismatch")
    verify_bytes(registration, raw)
    return current_main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registration", type=Path)
    parser.add_argument("protocol", type=Path)
    parser.add_argument("--verify-live", action="store_true",
                        help="Independently query public GitHub API for merge/ancestry and exact source bytes")
    args = parser.parse_args(argv)
    try:
        reg = validate_registration(strict_json(args.registration.read_bytes()))
        verify_bytes(reg, args.protocol.read_bytes())
        if args.verify_live:
            main_sha = verify_live(reg)
            print("SOURCE_BOUND to live protected-main ancestry " + main_sha)
        else:
            print("BYTES_MATCH only; external GitHub source and protected-main ancestry NOT VERIFIED")
    except (RegistrationError, OSError) as exc:
        print("INVALID: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
