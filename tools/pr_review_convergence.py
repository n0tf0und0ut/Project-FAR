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


def codex_status(issue_comments, expected_head):
    """Use only authenticated Codex App review summaries bound to the exact head.

    This is observable automated review metadata, NOT an independent human approval
    or a guarantee of the review's completeness.
    """
    candidate = None
    for comment in issue_comments:
        if not isinstance(comment, dict):
            raise EvidenceError("malformed issue comment record")
        user = comment.get("user") or {}
        app = comment.get("performed_via_github_app") or {}
        if user.get("login") != "chatgpt-codex-connector[bot]" or app.get("slug") != "chatgpt-codex-connector":
            continue
        body = comment.get("body")
        if not isinstance(body, str):
            raise EvidenceError("trusted Codex summary has invalid body")
        prefix = "<!-- codex-review-state:v1 "
        if prefix not in body or " -->" not in body.split(prefix, 1)[1]:
            continue
        try:
            details = json.loads(body.split(prefix, 1)[1].split(" -->", 1)[0])
            code = details["code_review"]
            if not isinstance(code, dict):
                raise TypeError("invalid code_review object")
        except (ValueError, TypeError, KeyError) as exc:
            raise EvidenceError("malformed signed-origin Codex review state") from exc
        if code.get("commit_sha") != expected_head:
            continue
        key = (comment.get("updated_at") or "", comment.get("id") or 0)
        if candidate is None or key > candidate[0]:
            candidate = (key, code)
    if candidate is None:
        return {"status": "missing", "unresolved": None, "passed": False}
    code = candidate[1]
    passed = code.get("status") == "completed" and code.get("has_unresolved_findings") is False
    return {"status": code.get("status"), "unresolved": code.get("has_unresolved_findings"),
            "passed": passed}


def evaluate(pr, reviews, threads, comments, expected_head, issue_comments=None):
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
    for reviewer, review in sorted(active.items()):
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
    automated = codex_status([] if issue_comments is None else issue_comments, expected_head)
    blockers = []
    if not current and not automated["passed"]:
        blockers.append("missing exact-head independent human approval or completed trusted Codex review")
    if automated["status"] == "completed" and automated["unresolved"] is True:
        blockers.append("authenticated exact-head Codex review reports unresolved findings")
    if changes:
        blockers.append("active CHANGES_REQUESTED")
    if unresolved:
        blockers.append("unresolved review threads")
    return {
        "schema": "far-pr-review-convergence/1",
        "pr_number": pr["number"],
        "exact_head_sha": expected_head,
        "base_sha": (pr.get("base") or {}).get("sha"),
        "author": author,
        "draft": pr.get("draft") is True,
        "review_count": len(reviews),
        "inline_comment_count": len(comments),
        "thread_count": len(threads),
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
        threads = threads_for(owner, name, args.pr, token)
        final = api(root + suffix, token)
        if (final.get("head") or {}).get("sha") != args.expected_head:
            raise EvidenceError("PR head advanced during evidence retrieval")
        record = evaluate(pr, reviews, threads, comments, args.expected_head, issue_comments)
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
