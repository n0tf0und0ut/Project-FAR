#!/usr/bin/env python3
"""Read-only, one-candidate living-research -> software-factory proposal bridge.

No queue submission, model invocation, branch mutation, or research adjudication.
The existing factory work-order shape is validated but remains ADVISORY_ONLY.
This adapter reads the permanent rolling inbox as untrusted Research data.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import math
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable

if __package__:
    from .software_factory import SCHEMA, canonical, validate_order
else:
    from software_factory import SCHEMA, canonical, validate_order

BRIDGE_SCHEMA = "far-software-factory/living-bridge-proposal/1"
REPOSITORY = "n0tf0und0ut/Project-FAR"
SOURCE_BRANCH = "automation/living-research-inbox"
SOURCE_BASE = "main"
CANDIDATE = re.compile(r"FAR-LIT-[0-9A-F]{16}\Z")
RQ = re.compile(r"FAR-RQ-[0-9]{3}\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
MAX_CANDIDATE_BYTES = 128 * 1024
MAX_API_BYTES = 512 * 1024
API_ROOT = "https://api.github.com/repos/" + REPOSITORY
# Bound discovery to exactly the owner's rolling branch and protected base.
# A closed/recreated PR cannot be reopened after GitHub rewrites its source ref.
INBOX_PRS_URL = (
    API_ROOT + "/pulls?state=open&head=" +
    urllib.parse.quote(REPOSITORY.split("/")[0] + ":" + SOURCE_BRANCH, safe="") +
    "&base=main&per_page=2"
)


class BridgeError(ValueError):
    """Input or provenance does not satisfy the pilot's fail-closed contract."""


def strict_json(raw: bytes, *, limit: int = MAX_API_BYTES) -> object:
    if not isinstance(raw, bytes) or len(raw) > limit:
        raise BridgeError("JSON bytes missing or above the configured bound")

    def unique(pairs):
        output = {}
        for key, value in pairs:
            if key in output:
                raise BridgeError("duplicate JSON member: " + key)
            output[key] = value
        return output

    def reject_constant(value):
        raise BridgeError("non-finite JSON token: " + value)

    def finite_float(value):
        parsed = float(value)
        if not math.isfinite(parsed):
            raise BridgeError("non-finite JSON number")
        return parsed

    try:
        document = json.loads(raw.decode("utf-8", errors="strict"),
                              object_pairs_hook=unique, parse_constant=reject_constant,
                              parse_float=finite_float)
    except BridgeError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise BridgeError("invalid UTF-8 JSON input or excessive JSON nesting") from exc

    # JSON escapes can encode lone UTF-16 surrogates even though the transport is
    # UTF-8. Do not accept bytes that later fail provenance serialization. Limit
    # nested structures independently of the interpreter-specific parser limit.
    stack = [(document, 0)]
    while stack:
        value, depth = stack.pop()
        if depth > 128:
            raise BridgeError("JSON nesting exceeds permitted depth")
        if isinstance(value, str):
            try:
                value.encode("utf-8", errors="strict")
            except UnicodeEncodeError as exc:
                raise BridgeError("JSON contains invalid Unicode surrogate") from exc
        elif isinstance(value, dict):
            for key, item in value.items():
                stack.append((key, depth + 1))
                stack.append((item, depth + 1))
        elif isinstance(value, list):
            stack.extend((item, depth + 1) for item in value)
    return document


def git_blob_sha1(raw: bytes) -> str:
    """Hash a regular Git blob, not a document assertion or a signature."""
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def candidate_path(candidate_id: str) -> str:
    if not isinstance(candidate_id, str) or not CANDIDATE.fullmatch(candidate_id):
        raise BridgeError("candidate ID must match FAR-LIT-[0-9A-F]{16}")
    return "research/living/inbox/candidates/" + candidate_id + ".json"


def _require_sha(value: object, what: str) -> str:
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise BridgeError("invalid 40-character SHA for " + what)
    return value


def _require_mapping(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise BridgeError(label + " must be an object")
    return value


def validate_candidate(raw: bytes, candidate_id: str) -> tuple[dict, list[str]]:
    """Validate identity/status/routing, never interpret candidate prose as commands."""
    if len(raw) > MAX_CANDIDATE_BYTES:
        raise BridgeError("candidate exceeds maximum permitted size")
    candidate = _require_mapping(strict_json(raw, limit=MAX_CANDIDATE_BYTES), "candidate")
    if candidate.get("candidate_id") != candidate_id:
        raise BridgeError("candidate ID and requested filename disagree")
    for key, expected in (("record_type", "CANDIDATE_LITERATURE"),
                          ("schema_version", "1.0"), ("authority", "Research")):
        if candidate.get(key) != expected:
            raise BridgeError("unexpected candidate " + key)
    lifecycle = _require_mapping(candidate.get("lifecycle"), "lifecycle")
    if lifecycle.get("stage") != "DISCOVERED" or any(
        lifecycle.get(flag) is not False for flag in
        ("may_change_claim_status", "may_count_as_external_independence",
         "may_establish_novelty", "may_execute_efr")
    ):
        raise BridgeError("candidate lifecycle exceeds Research discovery authority")
    triage = _require_mapping(candidate.get("triage"), "triage")
    if triage.get("status") != "UNREVIEWED_CANDIDATE":
        raise BridgeError("pilot only accepts unreviewed research candidates")
    source_key = candidate.get("source_key")
    if not isinstance(source_key, str) or not source_key or len(source_key) > 512:
        raise BridgeError("missing or invalid source identity")
    sources = candidate.get("sources")
    if not isinstance(sources, list) or not sources or any(not isinstance(s, dict) for s in sources):
        raise BridgeError("candidate lacks structured source provenance")
    discovery = _require_mapping(candidate.get("discovery"), "discovery")
    bindings = discovery.get("query_bindings")
    if not isinstance(bindings, list) or not bindings:
        raise BridgeError("candidate lacks declared governed-question routing")
    targets = set()
    for binding in bindings:
        binding = _require_mapping(binding, "query binding")
        ids = binding.get("target_ids")
        selected = binding.get("target_id")
        if not isinstance(ids, list) or not ids or any(not isinstance(x, str) or not RQ.fullmatch(x) for x in ids):
            raise BridgeError("invalid governed question IDs")
        if selected not in ids or len(ids) != len(set(ids)):
            raise BridgeError("inconsistent governed question binding")
        targets.update(ids)
    return candidate, sorted(targets)


def build_proposal(*, raw: bytes, candidate_id: str, source_ref_sha: str,
                   recorded_blob_sha: str, base_sha: str, source_pr_number: int,
                   repository: str = REPOSITORY) -> dict:
    """Pure, deterministic proposal; cannot start or authorize a factory task."""
    candidate_path(candidate_id)
    if type(source_pr_number) is not int or source_pr_number < 1:
        raise BridgeError("source PR must be a positive GitHub PR number")
    source_ref_sha = _require_sha(source_ref_sha, "source inbox commit")
    recorded_blob_sha = _require_sha(recorded_blob_sha, "GitHub candidate blob")
    base_sha = _require_sha(base_sha, "target main")
    if not isinstance(repository, str) or repository.casefold() != REPOSITORY.casefold():
        raise BridgeError("source and proposed factory repository must be Project FAR")
    if not isinstance(raw, bytes) or git_blob_sha1(raw) != recorded_blob_sha:
        raise BridgeError("candidate bytes do not match pinned Git blob identity")
    record, targets = validate_candidate(raw, candidate_id)
    path = candidate_path(candidate_id)
    source_sha256 = hashlib.sha256(raw).hexdigest()
    namespace = {"candidate_id": candidate_id, "source_pr": source_pr_number,
                 "source_ref": source_ref_sha,
                 "source_blob": recorded_blob_sha, "base_sha": base_sha,
                 "repository": REPOSITORY.casefold()}
    key = hashlib.sha256(canonical(namespace).encode("utf-8")).hexdigest()[:24]
    order = {
        "schema": SCHEMA,
        "id": "living-" + key,
        "repository": REPOSITORY.casefold(),
        "base_sha": base_sha,
        "tasks": [{
            "id": "investigate",
            "objective": ("Prepare a non-authoritative, evidence-preserving relevance assessment "
                          "of Research candidate " + candidate_id + " against declared questions "
                          + ", ".join(targets) + "."),
            "acceptance": [
                "Record source commit " + source_ref_sha + ", Git blob " + recorded_blob_sha
                + ", source SHA-256 " + source_sha256 + " and path " + path + ".",
                "Trace the candidate's declared governed-question IDs: " + ", ".join(targets) + ".",
                "Record independently checked supporting and counterevidence, or explicitly mark them unavailable.",
                "Deliver an advisory investigation report only; do not assert novelty, "
                "theorem contradiction, external independence, or scientific promotion.",
            ],
            "depends_on": [],
        }],
    }
    validate_order(order)
    proposal = {
        "schema": BRIDGE_SCHEMA,
        "status": "ADVISORY_REQUIRES_INDEPENDENT_TRIAGE_AND_AUTHORIZATION",
        "execution_authorized": False,
        "submit_to_queue": False,
        "source": {
            "repository": REPOSITORY,
            "pull_request": source_pr_number,
            "branch": SOURCE_BRANCH,
            "commit_sha": source_ref_sha,
            "path": path,
            "blob_sha1": recorded_blob_sha,
            "content_sha256": source_sha256,
            "candidate_id": candidate_id,
            "authority": "Research",
            "triage_status": "UNREVIEWED_CANDIDATE",
            "governed_question_ids": targets,
        },
        "untrusted_display": {
            "source_key": record["source_key"],
            "source_titles": [s.get("title") for s in record["sources"] if isinstance(s.get("title"), str)],
        },
        "proposed_work_order": order,
    }
    proposal["proposal_sha256"] = hashlib.sha256(canonical(proposal).encode("utf-8")).hexdigest()
    return proposal


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise BridgeError("GitHub redirect rejected")


def read_github_json(url: str) -> object:
    """Bounded, unauthenticated GET against a fixed GitHub API prefix."""
    if not url.startswith(API_ROOT + "/") or any(c in url for c in "\r\n#"):
        raise BridgeError("unexpected GitHub API URL")
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "project-far-living-factory-bridge/1",
    }, method="GET")
    opener = urllib.request.build_opener(_NoRedirect())
    try:
        with opener.open(req, timeout=12) as response:
            if response.status != 200:
                raise BridgeError("unexpected GitHub HTTP status")
            raw = response.read(MAX_API_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise BridgeError("GitHub read failed") from exc
    return strict_json(raw)


def fetch_live_proposal(candidate_id: str, getter: Callable[[str], object] = read_github_json) -> dict:
    """Discover one open draft inbox, then pin candidate bytes to that exact head."""
    path = candidate_path(candidate_id)
    candidates = getter(INBOX_PRS_URL)
    if type(candidates) is not list or len(candidates) != 1:
        raise BridgeError("expected exactly one open draft permanent rolling inbox")
    pr = _require_mapping(candidates[0], "rolling inbox PR metadata")
    source_pr_number = pr.get("number")
    if type(source_pr_number) is not int or source_pr_number < 1:
        raise BridgeError("invalid permanent inbox PR number")
    head = _require_mapping(pr.get("head"), "rolling inbox head")
    base = _require_mapping(pr.get("base"), "rolling inbox base")
    head_repo = _require_mapping(head.get("repo"), "rolling inbox repository")
    if (pr.get("state") != "open"
            or pr.get("draft") is not True or head.get("ref") != SOURCE_BRANCH
            or base.get("ref") != SOURCE_BASE
            or str(head_repo.get("full_name", "")).casefold() != REPOSITORY.casefold()):
        raise BridgeError("source is not the permanent, open draft research inbox")
    source_ref_sha = _require_sha(head.get("sha"), "current rolling inbox head")
    main = _require_mapping(getter(API_ROOT + "/branches/main"), "main branch")
    if main.get("name") != "main" or main.get("protected") is not True:
        raise BridgeError("main is not identified as a protected branch")
    base_sha = _require_sha(_require_mapping(main.get("commit"), "main commit").get("sha"), "main")
    file = _require_mapping(getter(API_ROOT + "/contents/" + path + "?ref=" + source_ref_sha),
                            "candidate GitHub contents")
    if (file.get("path") != path or file.get("type") != "file" or file.get("encoding") != "base64"):
        raise BridgeError("unexpected candidate GitHub contents identity")
    blob_sha = _require_sha(file.get("sha"), "GitHub blob")
    content = file.get("content")
    if not isinstance(content, str) or len(content) > MAX_CANDIDATE_BYTES * 2:
        raise BridgeError("invalid or oversized candidate base64 contents")
    try:
        raw = base64.b64decode("".join(content.splitlines()), validate=True)  # GitHub inserts line breaks
    except (binascii.Error, ValueError) as exc:
        raise BridgeError("malformed candidate base64") from exc
    size = file.get("size")
    if type(size) is not int or size != len(raw):
        raise BridgeError("GitHub candidate content size mismatch")
    return build_proposal(raw=raw, candidate_id=candidate_id, source_ref_sha=source_ref_sha,
                          recorded_blob_sha=blob_sha, base_sha=base_sha,
                          source_pr_number=source_pr_number)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-id", required=True, help="One FAR-LIT-[0-9A-F]{16} candidate in the single open draft living inbox")
    args = parser.parse_args(argv)
    try:
        output = fetch_live_proposal(args.candidate_id)
    except BridgeError as exc:
        print("living-factory-bridge: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(output, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
