#!/usr/bin/env python3
"""Read back canonical-branch protection and fail closed on any mismatch."""
from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request

REQUIRED_CHECK = "merge-authority"
GATE_CHECK = "protected-repin-gate"
REVIEW_CHECK = "pr-review-convergence-observation"
# GitHub Actions posts merge-authority; the owner's dedicated App posts protected-repin-gate.
GITHUB_ACTIONS_APP_ID = 15368


def request(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"GitHub API {exc.code}: {detail}") from exc


def protection_errors(actual: object, gate_app_id: int, *, require_review_convergence: bool = False) -> list[str]:
    if not isinstance(actual, dict):
        return ["branch-protection response is not an object"]
    errors: list[str] = []
    checks = actual.get("required_status_checks")
    contexts = checks.get("contexts", []) if isinstance(checks, dict) else []
    if not isinstance(checks, dict) or checks.get("strict") is not True:
        errors.append("required status checks are not strict/up-to-date")
    expected_contexts = {REQUIRED_CHECK, GATE_CHECK}
    if require_review_convergence:
        expected_contexts.add(REVIEW_CHECK)
    if len(contexts) != len(expected_contexts) or set(contexts) != expected_contexts:
        errors.append(f"required status-check contexts must be exactly {sorted(expected_contexts)}; found {contexts}")
    # A context bound to the wrong App (or to any App) can be satisfied by that App's check runs.
    bindings = sorted((check.get("context"), check.get("app_id"))
                      for check in (checks.get("checks") or [] if isinstance(checks, dict) else []))
    expected = sorted([(REQUIRED_CHECK, GITHUB_ACTIONS_APP_ID), (GATE_CHECK, gate_app_id)]
                      + ([(REVIEW_CHECK, GITHUB_ACTIONS_APP_ID)] if require_review_convergence else []))
    if bindings != expected:
        errors.append(f"required checks must be bound exactly to {expected}; found {bindings}")
    admins = actual.get("enforce_admins")
    if not isinstance(admins, dict) or admins.get("enabled") is not True:
        errors.append("administrator enforcement is not enabled")
    reviews = actual.get("required_pull_request_reviews")
    if not isinstance(reviews, dict):
        errors.append("pull requests are not required")
    else:
        for field, expected in {
            "dismiss_stale_reviews": True, "require_code_owner_reviews": False,
            "required_approving_review_count": 0, "require_last_push_approval": False,
        }.items():
            if reviews.get(field) != expected:
                errors.append(f"pull-request control {field} must be {expected!r}")
    for field, expected in {
        "required_conversation_resolution": True, "required_linear_history": False,
        "allow_force_pushes": False, "allow_deletions": False, "block_creations": False,
        "required_signatures": False, "lock_branch": False, "allow_fork_syncing": False,
    }.items():
        value = actual.get(field)
        enabled = value.get("enabled") if isinstance(value, dict) else None
        if enabled is not expected:
            errors.append(f"branch-protection control {field} must be {expected!r}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Project FAR canonical-branch protection")
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", "notfoundout/Project-FAR"))
    parser.add_argument("--branch", default="main")
    parser.add_argument("--token-env", default="FAR_GITHUB_ADMIN_TOKEN")
    parser.add_argument("--gate-app-id", type=int, required=True,
                        help="App ID of the owner's protected-repin-gate App")
    parser.add_argument("--require-review-convergence", action="store_true",
                        help="verify prospective three-check profile after owner cutover (never mutate protection)")
    args = parser.parse_args()
    token = os.environ.get(args.token_env)
    if not token:
        raise SystemExit(f"missing admin token in {args.token_env}")
    api = f"https://api.github.com/repos/{args.repository}"
    repository = request(api, token)
    branch = urllib.parse.quote(args.branch, safe="")
    actual = request(f"{api}/branches/{branch}/protection", token)
    errors = protection_errors(actual, args.gate_app_id,
                               require_review_convergence=args.require_review_convergence)
    print(json.dumps({
        "repository": args.repository, "branch": args.branch,
        "control_plane_enforced": not errors, "required_check": REQUIRED_CHECK,
        "review_convergence_required_profile": args.require_review_convergence,
        "owner_type": repository.get("owner", {}).get("type"),
        "visibility": repository.get("visibility"), "errors": errors,
    }, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
