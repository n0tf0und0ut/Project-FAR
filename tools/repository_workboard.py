#!/usr/bin/env python3
"""Read-only, non-authoritative live GitHub workboard for Project FAR.

This displays operational discovery data only. In particular, no output produced
by this script is a protected-branch merge decision or scientific status claim.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

DEFAULT_REPO = "n0tf0und0ut/Project-FAR"
API = "https://api.github.com"
PAGE_SIZE = 100


class WorkboardError(Exception):
    """A complete, coherent workboard could not be retrieved."""


class GitHubAPI:
    def __init__(self, token: str | None = None):
        self.token = token

    def get(self, path: str):
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "project-far-readonly-workboard",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = Request(API + path, headers=headers)
        try:
            with urlopen(request, timeout=20) as response:
                return json.load(response)
        except HTTPError as error:
            # Do not print token, request headers, or error response bodies.
            raise WorkboardError(f"GitHub API returned HTTP {error.code} for {path}") from None
        except (URLError, TimeoutError, ValueError) as error:
            raise WorkboardError(f"GitHub API request failed for {path}: {type(error).__name__}") from None


def pages(api, path: str) -> list[dict]:
    """Exhaust paginated REST results instead of silently truncating at 100."""
    results = []
    page = 1
    while True:
        data = api.get(f"{path}?state=open&per_page={PAGE_SIZE}&page={page}")
        if not isinstance(data, list):
            raise WorkboardError(f"Expected a list from {path} page {page}")
        if any(not isinstance(item, dict) for item in data):
            raise WorkboardError(f"Malformed item from {path} page {page}")
        results.extend(data)
        if len(data) < PAGE_SIZE:
            return results
        page += 1
        if page > 1000:
            raise WorkboardError(f"Unbounded pagination for {path}")


def _head_sha(api, root: str, branch: str) -> str:
    doc = api.get(f"{root}/branches/{quote(branch, safe='')}")
    sha = doc.get("commit", {}).get("sha") if isinstance(doc, dict) else None
    if not isinstance(sha, str) or len(sha) != 40:
        raise WorkboardError("Cannot establish exact default branch SHA")
    return sha


def _labels(item: dict) -> list[str]:
    return sorted(str(x.get("name")) for x in item.get("labels", []) if isinstance(x, dict) and x.get("name"))


def _assignees(item: dict) -> list[str]:
    return sorted(str(x.get("login")) for x in item.get("assignees", []) if isinstance(x, dict) and x.get("login"))


def _pr(row: dict, repo: str) -> dict:
    number = row["number"]
    protected_inbox = repo == DEFAULT_REPO and number == 490
    state = "PERMANENT INBOX — DO NOT MERGE" if protected_inbox else ("DRAFT" if row.get("draft") else "OPEN")
    return {
        "number": number,
        "title": row["title"],
        "url": row["html_url"],
        "state": state,
        "head_sha": row["head"]["sha"],
        "base": row["base"]["ref"],
        "updated_at": row["updated_at"],
        "assignees": _assignees(row),
        "labels": _labels(row),
        "merge_readiness": "NOT_EVALUATED",
    }


def _issue(row: dict) -> dict:
    return {
        "number": row["number"],
        "title": row["title"],
        "url": row["html_url"],
        "updated_at": row["updated_at"],
        "assignees": _assignees(row),
        "labels": _labels(row),
    }


def collect(api, repo: str = DEFAULT_REPO, now: datetime | None = None) -> dict:
    if repo.count("/") != 1 or any(not segment for segment in repo.split("/")):
        raise WorkboardError("Repository must have owner/name form")
    root = f"/repos/{quote(repo, safe='/')}"
    meta = api.get(root)
    if not isinstance(meta, dict) or not isinstance(meta.get("default_branch"), str):
        raise WorkboardError("Cannot determine default branch")
    branch = meta["default_branch"]
    before = _head_sha(api, root, branch)
    pulls = pages(api, root + "/pulls")
    issues = [row for row in pages(api, root + "/issues") if "pull_request" not in row]
    after = _head_sha(api, root, branch)
    if before != after:
        raise WorkboardError("Default branch advanced during retrieval; rerun for coherent snapshot")
    prs = sorted((_pr(row, repo) for row in pulls), key=lambda x: x["number"], reverse=True)
    tasks = sorted((_issue(row) for row in issues), key=lambda x: x["number"], reverse=True)
    actionable = sum(row["state"] != "PERMANENT INBOX — DO NOT MERGE" for row in prs)
    timestamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    return {
        "schema": "far-repository-workboard/1",
        "authority": "ADVISORY_ONLY",
        "repo": repo,
        "fetched_at_utc": timestamp,
        "default_branch": branch,
        "default_branch_sha": before,
        "scope": "Live open PR and issue metadata; merge readiness and scientific claims not evaluated",
        "counts": {
            "open_prs": len(prs),
            "actionable_prs": actionable,
            "permanent_inbox_prs": len(prs) - actionable,
            "open_issues": len(tasks),
            "unassigned_issues": sum(not item["assignees"] for item in tasks),
            "unlabeled_issues": sum(not item["labels"] for item in tasks),
        },
        "prs": prs,
        "issues": tasks,
    }


def _cell(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def markdown(snapshot: dict) -> str:
    c = snapshot["counts"]
    lines = [
        "# FAR live repository workboard", "",
        f"Repository: `{_cell(snapshot['repo'])}` · default `{_cell(snapshot['default_branch'])}` at `{_cell(snapshot['default_branch_sha'])}`",
        f"Retrieved: `{_cell(snapshot['fetched_at_utc'])}`", "",
        "**Scope:** read-only GitHub operational metadata; this is not scientific authority, an independent review, or protected merge authorization. GitHub lists are collected sequentially, not transactionally. The default branch is checked before and after retrieval.", "",
        f"Open PRs: **{c['open_prs']}** ({c['actionable_prs']} actionable, {c['permanent_inbox_prs']} permanent inbox). Open issues: **{c['open_issues']}** ({c['unassigned_issues']} unassigned, {c['unlabeled_issues']} unlabeled).", "",
        "## Pull requests", "",
        "| PR | Operational state | Head SHA | Updated (UTC) | Assignees |", "|---|---|---|---|---|",
    ]
    for row in snapshot["prs"]:
        title = _cell(row["title"])
        assignees = ", ".join(row["assignees"]) or "—"
        lines.append(f"| [#{row['number']} — {title}]({row['url']}) | {_cell(row['state'])} | `{row['head_sha']}` | `{row['updated_at']}` | {_cell(assignees)} |")
    if not snapshot["prs"]:
        lines.append("| — | None | — | — | — |")
    lines += ["", "## Issues", "", "| Issue | Last updated (UTC) | Assignees | Labels |", "|---|---|---|---|"]
    for row in snapshot["issues"]:
        title = _cell(row["title"])
        lines.append(f"| [#{row['number']} — {title}]({row['url']}) | `{row['updated_at']}` | {_cell(', '.join(row['assignees']) or '—')} | {_cell(', '.join(row['labels']) or '—')} |")
    if not snapshot["issues"]:
        lines.append("| — | — | — | — |")
    lines += ["", "For actual merge readiness, reconstruct the PR's exact-head evidence and apply `docs/governance/pr-review-convergence.md` and the protected gates. This workboard intentionally reports `NOT_EVALUATED` for merge readiness.", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_REPO, help="GitHub owner/repository (default: Project FAR)")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args(argv)
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    try:
        doc = collect(GitHubAPI(token), args.repo)
    except (WorkboardError, KeyError, TypeError) as error:
        print(f"Workboard failed closed: {error}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(doc, indent=2, sort_keys=True))
    else:
        print(markdown(doc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
