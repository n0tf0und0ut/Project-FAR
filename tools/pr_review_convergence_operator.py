#!/usr/bin/env python3
"""Read-only, exact-head review evidence. Never triggers reviews or modifies a PR."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SHA = re.compile(r"[a-f0-9]{40}\Z")
REPO = re.compile(r"(?!\.{1,2}/)[A-Za-z0-9_.-]+/(?!(?:\.{1,2})\Z)[A-Za-z0-9_.-]+\Z")
QUERY = """query($owner:String!,$name:String!,$number:Int!,$cursor:String) {
 repository(owner:$owner,name:$name) {
  pullRequest(number:$number) {
   reviewThreads(first:50,after:$cursor) {
    pageInfo { hasNextPage endCursor }
    nodes { id isResolved isOutdated comments(first:1) { nodes { databaseId } } }
   }
  }
 }
}"""


class EvidenceError(ValueError):
    pass


def api(url, token, data=None):
    payload = None if data is None else json.dumps(data).encode("utf-8")
    request = urllib.request.Request(url, data=payload,
        headers={"Authorization": "Bearer " + token,
                 "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json",
                 "X-GitHub-Api-Version": "2022-11-28"},
        method="POST" if payload is not None else "GET")
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)


def paginate(url, token):
    records = []
    for page in range(1, 41):
        batch = api(url + ("&" if "?" in url else "?") +
                    "per_page=100&page=" + str(page), token)
        if not isinstance(batch, list) or any(not isinstance(x, dict) for x in batch):
            raise EvidenceError("malformed REST collection")
        records.extend(batch)
        if len(batch) < 100:
            return records
    raise EvidenceError("incomplete REST pagination")


def threads_for(owner, name, number, token):
    items, cursor, seen = [], None, set()
    for _ in range(40):
        response = api("https://api.github.com/graphql", token, {
            "query": QUERY, "variables": {
                "owner": owner, "name": name, "number": number, "cursor": cursor
            }})
        if response.get("errors"):
            raise EvidenceError("GraphQL returned errors")
        try:
            data = response["data"]["repository"]["pullRequest"]["reviewThreads"]
            for item in data["nodes"]:
                roots = item["comments"]["nodes"]
                if not roots or item["id"] in seen:
                    raise EvidenceError("missing or duplicate thread identity")
                if type(item["isResolved"]) is not bool or type(item["isOutdated"]) is not bool:
                    raise EvidenceError("invalid thread state")
                seen.add(item["id"])
                items.append({"id": item["id"], "resolved": item["isResolved"],
                              "outdated": item["isOutdated"],
                              "root_comment_id": roots[0]["databaseId"]})
            if not data["pageInfo"]["hasNextPage"]:
                return items
            next_cursor = data["pageInfo"]["endCursor"]
            if not isinstance(next_cursor, str) or not next_cursor or next_cursor == cursor:
                raise EvidenceError("invalid review-thread cursor")
            cursor = next_cursor
        except (KeyError, TypeError, IndexError) as exc:
            raise EvidenceError("incomplete review-thread API response") from exc
    raise EvidenceError("incomplete GraphQL pagination")


def person(value):
    user = value.get("user") or {}
    return user.get("login", "") if isinstance(user, dict) else ""


def codex_origin(comment):
    user = comment.get("user") or {}
    app = comment.get("performed_via_github_app") or {}
    if not isinstance(user, dict) or not isinstance(app, dict):
        raise EvidenceError("malformed issue comment origin")
    return (user.get("login") == "chatgpt-codex-connector[bot]"
            and user.get("type") == "Bot"
            and app.get("slug") == "chatgpt-codex-connector"
            and type(app.get("id")) is int and app["id"] == 1144995)


def timestamp(value):
    if not isinstance(value, str):
        raise EvidenceError("invalid Codex source timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError("invalid Codex source timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise EvidenceError("Codex source timestamp must be UTC")
    return parsed


def source_identity(comment):
    cid, updated = comment.get("id"), comment.get("updated_at")
    if type(cid) is not int or cid < 1:
        raise EvidenceError("Codex comment missing source ID")
    return cid, updated, timestamp(updated)


RECEIPT_MARKER = "<!-- codex-review-receipt:v1 -->"
RECEIPT = re.compile(
    r"\A<!-- codex-review-receipt:v1 -->\s*"
    r"Codex Review: Didn't find any major issues\."
    r"(?: (?:Chef's kiss\.|Keep them coming!|Nice work!))?\n\s*"
    r"\*\*Reviewed commit:\*\* `([a-f0-9]{10,40})`\s*"
    r"(?:<details>.*</details>\s*)?\Z", re.DOTALL)


def codex_receipts(issue_comments):
    receipts = []
    for comment in issue_comments:
        if not isinstance(comment, dict):
            raise EvidenceError("malformed issue comment record")
        if not codex_origin(comment):
            continue
        body = comment.get("body")
        if not isinstance(body, str):
            raise EvidenceError("authenticated Codex comment has invalid body")
        if RECEIPT_MARKER not in body:
            continue
        match = RECEIPT.fullmatch(body)
        if (not match or body.count(RECEIPT_MARKER) != 1
                or body.count("**Reviewed commit:**") != 1):
            raise EvidenceError("ambiguous or unrecognized authenticated Codex receipt")
        cid, updated, moment = source_identity(comment)
        created = comment.get("created_at")
        if timestamp(created) != moment:
            raise EvidenceError("edited Codex completion receipt")
        receipts.append({"comment_id": cid, "created_at": created,
                         "updated_at": updated, "commit_prefix": match[1],
                         "verdict": "no_major_issues"})
    return receipts


def unique_json(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate machine-state key")
        result[key] = value
    return result


def codex_summary_candidates(issue_comments, expected_head):
    """Authenticate exact-head machine states independently of receipt prose."""
    candidates = []
    prefix = "<!-- codex-review-state:v1 "
    for comment in issue_comments:
        if not isinstance(comment, dict):
            raise EvidenceError("malformed issue comment record")
        if not codex_origin(comment):
            continue
        body = comment.get("body")
        if not isinstance(body, str):
            raise EvidenceError("authenticated Codex comment has invalid body")
        if prefix not in body:
            continue
        # The bot's review prose can quote untrusted input. Two machine markers
        # are ambiguous even if the first one parses as a successful review.
        if body.count(prefix) != 1:
            raise EvidenceError("ambiguous authenticated Codex review delimiters")
        suffix = body.split(prefix, 1)[1]
        if " -->" not in suffix:
            raise EvidenceError("unterminated authenticated Codex review state")
        try:
            state = json.loads(suffix.split(" -->", 1)[0], object_pairs_hook=unique_json)
            code = state["code_review"]
            if not isinstance(code, dict):
                raise ValueError("code_review must be an object")
        except (ValueError, KeyError, TypeError) as exc:
            raise EvidenceError("malformed authenticated Codex review summary") from exc
        if code.get("commit_sha") != expected_head:
            continue
        if (code.get("status") not in ("running", "completed", "failed")
                or "has_unresolved_findings" not in code
                or type(code.get("has_unresolved_findings")) not in (bool, type(None))
                or type(code.get("has_any_findings")) not in (bool, type(None))
                or (code.get("has_any_findings") is False
                    and code.get("has_unresolved_findings") is True)):
            raise EvidenceError("unrecognized or incomplete authenticated Codex state")
        cid, updated, _ = source_identity(comment)
        candidates.append((updated, cid, code))
    candidates.sort(key=lambda x: (timestamp(x[0]), x[1]))
    return candidates


def codex_status(issue_comments, expected_head, commit_resolutions=None):
    """Only authenticated, unambiguous, exact-head Codex state; never human approval."""
    candidates = codex_summary_candidates(issue_comments, expected_head)
    if not candidates:
        return {"status": "missing", "unresolved": None, "passed": False,
                "source_comment_id": None, "updated_at": None,
                "review_state_sources": [], "completion_basis": None,
                "receipt_source": None}
    updated, cid, code = candidates[-1]
    # A pending rerun never clears a previously known unresolved result. Nor
    # may a human approval bypass the incomplete rerun on the same head.
    outstanding = False
    for _, _, observed in candidates:
        if observed["has_unresolved_findings"] is True:
            outstanding = True
        elif (observed["status"] == "completed"
              and observed["has_unresolved_findings"] is False):
            # Only an explicit completed clean result clears known findings,
            # including those reported while a prior review was running/failed.
            outstanding = False
    passed = code["status"] == "completed" and code["has_unresolved_findings"] is False
    basis = "explicit_finding_state" if passed else None
    receipt_source = None
    if code["status"] == "completed" and code["has_unresolved_findings"] is None:
        # A separate, narrowly recognized receipt can attest completion with no
        # major issues. It does NOT turn unknown finding flags into false and
        # cannot clear a known unresolved result from another authenticated state.
        matching = []
        for receipt in codex_receipts(issue_comments):
            prefix = receipt["commit_prefix"]
            if not expected_head.startswith(prefix):
                continue
            elapsed = (timestamp(updated) - timestamp(receipt["created_at"])).total_seconds()
            if not 0 <= elapsed <= 5:
                continue
            if (commit_resolutions or {}).get(prefix) != expected_head:
                raise EvidenceError("Codex receipt commit prefix is not API-resolved to exact head")
            matching.append(receipt)
        if len(matching) != 1:
            raise EvidenceError("completed Codex state lacks one contemporaneous exact-head receipt")
        receipt_source = dict(matching[0], resolved_commit_sha=expected_head)
        passed = not outstanding
        basis = "authenticated_no_major_issues_receipt" if passed else None
    return {"status": code["status"],
            "unresolved": True if outstanding else code["has_unresolved_findings"],
            "passed": passed,
            "completion_basis": basis,
            "receipt_source": receipt_source,
            "source_comment_id": cid,
            "updated_at": updated,
            "review_state_sources": [
                {"comment_id": n, "updated_at": t, "status": c["status"],
                 "has_unresolved_findings": c["has_unresolved_findings"]}
                for t, n, c in candidates]}

def evaluate(pr, reviews, threads, comments, expected_head, issue_comments=None,
             commit_resolutions=None):
    """Only metadata closure; no claim of independent substantive correctness."""
    if not isinstance(pr, dict) or not SHA.fullmatch(expected_head):
        raise EvidenceError("invalid expected head or PR data")
    if (pr.get("head") or {}).get("sha") != expected_head:
        raise EvidenceError("review evidence is not for exact current PR head")
    author = person(pr)
    if not author or type(pr.get("number")) is not int:
        raise EvidenceError("incomplete PR identity")
    active = {}
    for review in sorted(reviews, key=lambda r: (r.get("submitted_at") or "", r.get("id") or 0)):
        state = review.get("state")
        if state not in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED", "COMMENTED", "PENDING"):
            raise EvidenceError("unknown review state")
        reviewer = person(review)
        if not reviewer:
            raise EvidenceError("review lacks user")
        # A COMMENTED review is not an approval or a dismissal.
        if state in ("APPROVED", "CHANGES_REQUESTED", "DISMISSED"):
            active[reviewer] = review
    current, stale, changes = [], [], []
    active_review_sources = []
    for reviewer, review in sorted(active.items()):
        active_review_sources.append({
            "login": reviewer, "review_id": review.get("id"),
            "state": review["state"], "commit_id": review.get("commit_id"),
            "submitted_at": review.get("submitted_at")})
        if review["state"] == "CHANGES_REQUESTED":
            changes.append(reviewer)
        elif review["state"] == "APPROVED":
            user = review["user"]
            if (user.get("type") == "User" and reviewer != author
                    and review.get("commit_id") == expected_head):
                current.append(reviewer)
            else:
                stale.append(reviewer)
    unresolved = []
    for item in threads:
        if not isinstance(item, dict) or type(item.get("resolved")) is not bool:
            raise EvidenceError("malformed review thread")
        if not item["resolved"]:
            unresolved.append(item)
    # Exact identical text only: this is NOT automatic causal deduplication.
    groups = defaultdict(list)
    for comment in comments:
        if (not isinstance(comment, dict) or type(comment.get("id")) is not int
                or not isinstance(comment.get("body"), str)):
            raise EvidenceError("malformed inline review comment")
        digest = hashlib.sha256(" ".join(comment["body"].split()).casefold().encode()).hexdigest()
        groups[(comment.get("path") or "", digest)].append(comment["id"])
    duplicates = [{"path": path, "normalized_sha256": digest, "comment_ids": sorted(ids)}
                  for (path, digest), ids in sorted(groups.items()) if len(ids) > 1]
    automated = codex_status([] if issue_comments is None else issue_comments,
                             expected_head, commit_resolutions)
    blockers = []
    if not current and not automated["passed"]:
        blockers.append("missing exact-head independent human approval or completed trusted Codex review")
    if automated["unresolved"] is True:
        blockers.append("authenticated exact-head Codex review reports unresolved findings")
    if automated["status"] in ("running", "failed"):
        blockers.append("authenticated exact-head Codex review is incomplete")
    if changes:
        blockers.append("active CHANGES_REQUESTED")
    if unresolved:
        blockers.append("unresolved review threads")
    return {
        "schema": "far-pr-review-convergence/2",
        "policy_version": "1.1",
        "pr_number": pr["number"],
        "exact_head_sha": expected_head,
        "base_sha": (pr.get("base") or {}).get("sha"),
        "author": author,
        "draft": pr.get("draft") is True,
        "review_count": len(reviews),
        "inline_comment_count": len(comments),
        "thread_count": len(threads),
        "all_thread_states": threads,
        "active_review_sources": active_review_sources,
        "human_approvals_on_exact_head": current,
        "trusted_codex_review_on_exact_head": automated,
        "stale_or_nonhuman_approvals": stale,
        "active_changes_requested": changes,
        "unresolved_threads": unresolved,
        "exact_text_duplicate_candidates": duplicates,
        "review_metadata_converged": not blockers and pr.get("draft") is False,
        "blockers": blockers,
        "substantive_review_verified": False,
        "software_correctness_proven": False,
        "merge_authorization_verified": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("report", "enforce"), default="enforce")
    args = parser.parse_args(argv)
    if not REPO.fullmatch(args.repository) or args.pr < 1 or not SHA.fullmatch(args.expected_head):
        parser.error("malformed immutable repository, PR or head identity")
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("missing read-only GH_TOKEN")
    owner, name = args.repository.split("/", 1)
    root = "https://api.github.com/repos/" + args.repository
    suffix = "/pulls/" + str(args.pr)
    try:
        pr = api(root + suffix, token)
        reviews = paginate(root + suffix + "/reviews", token)
        comments = paginate(root + suffix + "/comments", token)
        issue_comments = paginate(root + "/issues/" + str(args.pr) + "/comments", token)
        resolutions = {}
        candidates = codex_summary_candidates(issue_comments, args.expected_head)
        # The authenticated explicit completed-clean state requires no prose
        # receipt. Only the legacy completed/null path needs a provenance-bound
        # no-major-issues receipt and a GitHub-resolved exact commit prefix.
        if (candidates and candidates[-1][2]["status"] == "completed"
                and candidates[-1][2]["has_unresolved_findings"] is None):
            for receipt in codex_receipts(issue_comments):
                prefix = receipt["commit_prefix"]
                if args.expected_head.startswith(prefix) and prefix not in resolutions:
                    resolved = api(root + "/commits/" + prefix, token)
                    if not isinstance(resolved, dict) or not SHA.fullmatch(resolved.get("sha", "")):
                        raise EvidenceError("incomplete receipt commit resolution")
                    resolutions[prefix] = resolved["sha"]
        threads = threads_for(owner, name, args.pr, token)
        final = api(root + suffix, token)
        if not isinstance(final, dict) or (final.get("head") or {}).get("sha") != args.expected_head:
            raise EvidenceError("PR head advanced during evidence retrieval")
        record = evaluate(pr, reviews, threads, comments, args.expected_head,
                          issue_comments, resolutions)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        report = "\n".join([
            "## PR review convergence (metadata only)",
            "Exact head: " + args.expected_head,
            "Qualifying human approvals: " + str(len(record["human_approvals_on_exact_head"])),
            "Trusted Codex completed on exact head: " + str(record["trusted_codex_review_on_exact_head"]["passed"]),
            "Outstanding threads: " + str(len(record["unresolved_threads"])),
            "Active changes requested: " + str(len(record["active_changes_requested"])),
            "Result: " + ("METADATA CONVERGED" if record["review_metadata_converged"]
                          else "REVIEW REQUIRED"),
            "This is not proof of substantive review, correctness or merge authorization.",
        ]) + "\n"
        print(report)
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as output:
                output.write(report)
        return int(args.mode == "enforce" and not record["draft"]
                   and not record["review_metadata_converged"])
    except (EvidenceError, OSError, KeyError, TypeError, ValueError) as exc:
        print("INCOMPLETE_REVIEW_EVIDENCE: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
