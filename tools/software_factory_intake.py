#!/usr/bin/env python3
"""Reviewable natural-language and GitHub-Issue intake for FAR's Research factory.

A requirement is *data*, not an instruction granting a coding agent permissions.
Only the explicit `submit` command creates queue state. This module never starts
workers, performs network writes, or bypasses protected GitHub controls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

try:
    from tools.software_factory import Factory, FactoryError, digest, validate_order
except ModuleNotFoundError:  # python tools/software_factory_intake.py
    from software_factory import Factory, FactoryError, digest, validate_order

INTAKE_SCHEMA = "far-software-factory/intake/1"
MAX_REQUEST_BYTES = 65536
MAX_ISSUE_BYTES = 131072
HEADING = re.compile(r"^\s*(?:#{1,5}\s*)?(?:acceptance(?:\s+criteria)?|done\s+when|definition\s+of\s+done|success\s+criteria)\s*:\s*$", re.I)
ANY_HEADING = re.compile(r"^\s*(?:#{1,5}\s+\S.*|[A-Z][\w /-]{2,48}:\s*)$")
BULLET = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)(?:\[[ xX]\]\s*)?(\S.*)$")
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")


class IntakeError(FactoryError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not follow GitHub API redirects with a bearer credential."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _ensure_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise IntakeError(f"{name} must be nonempty text")
    try:
        raw = value.encode("utf-8", "strict")
    except UnicodeError as exc:
        raise IntakeError(f"{name} is not valid UTF-8") from exc
    if len(raw) > MAX_REQUEST_BYTES or "\x00" in value:
        raise IntakeError(f"{name} is too large or contains NUL")
    return value


def _strict_json(raw: str) -> object:
    def unique(pairs):
        d = {}
        for k, v in pairs:
            if k in d:
                raise IntakeError(f"duplicate JSON key: {k}")
            d[k] = v
        return d

    def invalid(x):
        raise IntakeError(f"invalid JSON constant: {x}")

    try:
        return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)
    except json.JSONDecodeError as exc:
        raise IntakeError(f"invalid JSON: {exc.msg}") from exc


def _criteria(body: str) -> list[str]:
    """Copy *explicitly labeled* criteria verbatim; never invent test oracles."""
    result = []
    in_section = False
    for line in body.splitlines():
        if HEADING.fullmatch(line):
            in_section = True
            continue
        if not in_section:
            continue
        if ANY_HEADING.fullmatch(line) or (line.strip() and line.lstrip().startswith('```')):
            in_section = False
            continue
        m = BULLET.match(line)
        if m:
            value = m.group(1).strip()
            if not value or len(value) > 1000:
                raise IntakeError("acceptance criterion must have 1-1000 characters")
            result.append(value)
        elif line.strip():
            # A new prose paragraph ends the criteria section.
            in_section = False
    if len(result) > 32 or len(set(result)) != len(result):
        raise IntakeError("duplicate or excessive acceptance criteria")
    return result


def compile_request(*, repository: str, base_sha: str, title: str, body: str,
                    source_kind: str = "chat", source_ref: str = "manual") -> dict:
    """Compile only explicit requirements. Return blocked drafts for missing tests.

    Source strings are retained exactly and bound to the queue identity by SHA-256.
    This is deterministic extraction, NOT a language model's semantic analysis.
    """
    if not isinstance(repository, str) or not REPO.fullmatch(repository):
        raise IntakeError("invalid repository")
    if not isinstance(base_sha, str) or not SHA.fullmatch(base_sha):
        raise IntakeError("base_sha must be a full lowercase Git commit SHA")
    if source_kind not in {"chat", "github_issue", "api"}:
        raise IntakeError("invalid source kind")
    title = _ensure_text(title, "title")
    body = _ensure_text(body, "body")
    source_ref = _ensure_text(source_ref, "source reference")
    if len(title) > 500 or len(source_ref) > 500:
        raise IntakeError("title or reference exceeds limit")
    original = {"kind": source_kind, "ref": source_ref, "title": title, "body": body}
    source_hash = digest(original)
    order_id = f"intake-{source_hash[:24]}"
    acceptance = _criteria(body)
    if title.strip().endswith("?"):
        # Questions are not implementation authorizations.
        acceptance = []
    order = None
    if acceptance:
        order = {"schema": "far-software-factory/work-order/1", "id": order_id,
                 "repository": repository, "base_sha": base_sha,
                 "tasks": [{"id": "implementation", "objective": title.strip(),
                            "acceptance": acceptance, "depends_on": []}]}
        validate_order(order)
    draft = {"schema": INTAKE_SCHEMA, "source": original, "source_sha256": source_hash,
             "repository": repository, "base_sha": base_sha,
             "status": "ready_for_manual_submission" if order else "needs_clarification",
             "questions": [] if order else ["Provide observable, testable items under an 'Acceptance criteria:' heading."],
             "order": order, "authority": "ADVISORY_ONLY",
             "compiler": "deterministic-explicit-criteria-v1"}
    draft["fingerprint"] = digest(draft)
    return draft


def verify_draft(draft: object) -> dict:
    """Regenerate from preserved source, detecting accidental draft edits.

    Fingerprints provide integrity checks, NOT authentication or an approval.
    """
    if not isinstance(draft, dict) or set(draft) != {"schema", "source", "source_sha256", "repository", "base_sha",
                                                    "status", "questions", "order", "authority", "compiler", "fingerprint"}:
        raise IntakeError("invalid intake draft fields")
    if draft["schema"] != INTAKE_SCHEMA or not isinstance(draft["source"], dict):
        raise IntakeError("unsupported intake draft")
    src = draft["source"]
    if set(src) != {"kind", "ref", "title", "body"}:
        raise IntakeError("invalid source fields")
    expected = compile_request(repository=draft["repository"], base_sha=draft["base_sha"],
                               title=src["title"], body=src["body"],
                               source_kind=src["kind"], source_ref=src["ref"])
    if expected != draft:
        raise IntakeError("intake draft differs from deterministic source compilation")
    return draft


def _issue_from_payload(payload: object, repository: str, issue_number: int) -> tuple[str, str]:
    if not isinstance(payload, dict):
        raise IntakeError("invalid GitHub issue response")
    if payload.get("number") != issue_number or isinstance(payload.get("number"), bool):
        raise IntakeError("GitHub issue number mismatch")
    if "pull_request" in payload or payload.get("state") != "open":
        raise IntakeError("source must be an open GitHub issue, not a PR")
    repo_url = payload.get("repository_url")
    if not isinstance(repo_url, str) or repo_url.casefold() != f"https://api.github.com/repos/{repository}".casefold():
        raise IntakeError("GitHub issue repository mismatch")
    title = _ensure_text(payload.get("title"), "issue title")
    body = _ensure_text(payload.get("body"), "issue body")
    return title, body


def fetch_issue(repository: str, issue_number: int, *, token: str | None = None,
                fetcher=None) -> tuple[str, str]:
    """GET one fixed-host GitHub API issue. No arbitrary URL, redirects, or writes.

    The optional fetcher injects a test transport; the default uses HTTPS.
    """
    if not isinstance(repository, str) or not REPO.fullmatch(repository):
        raise IntakeError("invalid repository")
    if type(issue_number) is not int or not 1 <= issue_number <= 1_000_000_000:
        raise IntakeError("invalid issue number")
    url = f"https://api.github.com/repos/{repository}/issues/{issue_number}"
    if fetcher is None:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "far-factory-intake-v1",
                   "X-GitHub-Api-Version": "2022-11-28"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.build_opener(_NoRedirect).open(req, timeout=12) as response:
                if response.geturl() != url:  # prohibit redirected credentials / source swaps
                    raise IntakeError("redirected issue source is not trusted")
                raw = response.read(MAX_ISSUE_BYTES + 1)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            raise IntakeError(f"GitHub issue retrieval failed: {type(exc).__name__}") from exc
    else:
        raw = fetcher(url)
    if not isinstance(raw, bytes) or len(raw) > MAX_ISSUE_BYTES:
        raise IntakeError("issue response is not a bounded byte string")
    try:
        payload = _strict_json(raw.decode("utf-8", "strict"))
    except UnicodeError as exc:
        raise IntakeError("invalid issue response encoding") from exc
    return _issue_from_payload(payload, repository, issue_number)


def submit_draft(draft: object, db_path: str | Path) -> dict:
    validated = verify_draft(draft)
    if validated["status"] != "ready_for_manual_submission":
        raise IntakeError("draft requires clarification; queue unchanged")
    # No network actions, worker invocation, or permission inference.
    factory = Factory(db_path)
    try:
        receipt = factory.submit(validated["order"])
    finally:
        factory.db.close()
    return {"queue": receipt, "source_sha256": validated["source_sha256"],
            "draft_fingerprint": validated["fingerprint"], "authority": "ADVISORY_ONLY"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("draft-text", "draft-issue"):
        p = commands.add_parser(name)
        p.add_argument("--repo", required=True)
        p.add_argument("--base-sha", required=True)
        p.add_argument("--output", required=True)
        if name == "draft-text":
            p.add_argument("--text-file", required=True)
            p.add_argument("--source-ref", default="manual")
        else:
            p.add_argument("--issue", type=int, required=True)
    p = commands.add_parser("submit")
    p.add_argument("--draft-file", required=True)
    p.add_argument("--db", required=True)
    p.add_argument("--receipt-file")
    args = parser.parse_args(argv)
    try:
        if args.command == "draft-text":
            if Path(args.text_file).resolve() == Path(args.output).resolve():
                raise IntakeError("draft output must not overwrite original source")
            text = Path(args.text_file).read_text(encoding="utf-8")
            lines = text.splitlines()
            title = next((line.strip() for line in lines if line.strip()), "")
            if not title:
                raise IntakeError("request file must contain a nonempty title")
            draft = compile_request(repository=args.repo, base_sha=args.base_sha,
                                    title=title, body=text, source_kind="chat", source_ref=args.source_ref)
        elif args.command == "draft-issue":
            title, body = fetch_issue(args.repo, args.issue, token=os.getenv("GITHUB_TOKEN"))
            draft = compile_request(repository=args.repo, base_sha=args.base_sha, title=title,
                                    body=body, source_kind="github_issue",
                                    source_ref=f"{args.repo}#{args.issue}")
        else:
            if args.receipt_file and Path(args.receipt_file).resolve() == Path(args.draft_file).resolve():
                raise IntakeError("receipt must not overwrite intake draft")
            draft = _strict_json(Path(args.draft_file).read_text(encoding="utf-8"))
            receipt = submit_draft(draft, args.db)
            if args.receipt_file:
                Path(args.receipt_file).write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(receipt, sort_keys=True, indent=2))
            return 0
        Path(args.output).write_text(json.dumps(draft, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"status": draft["status"], "output": args.output,
                          "source_sha256": draft["source_sha256"], "questions": draft["questions"]}, indent=2))
        return 0 if draft["order"] else 3
    except (IntakeError, FactoryError, OSError, ValueError, UnicodeError) as exc:
        print(f"software-factory-intake: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
