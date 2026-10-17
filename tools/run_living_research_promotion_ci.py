#!/usr/bin/env python3
"""GitHub Actions adapter for the living-research promotion transaction.

The core transaction historically required a dedicated GitHub App token only so that
opening its PR emitted a ``pull_request`` event. GitHub's App installation for that
credential can be absent or stale even when repository configuration appears correct.
This adapter removes that external installation dependency without weakening merge
authority:

* the ephemeral ``GITHUB_TOKEN`` is removed from the process environment before any
  candidate materialization or validation subprocess executes;
* checkout credentials are not persisted by the workflow;
* the token is injected only into bounded fetch/push/PR/API subprocesses;
* the privileged push ignores global/system Git configuration, rejects local redirect,
  credential, HTTP, include, and hook configuration, disables hooks, and targets the
  canonical repository URL rather than a mutable remote name;
* after the exact promotion PR exists, Validator Assurance is explicitly dispatched on
  that exact branch only when ``merge-authority`` is absent for its exact head;
* an existing failed ``merge-authority`` is never papered over by an automatic rerun.

GitHub explicitly permits workflows created through ``workflow_dispatch`` by
``GITHUB_TOKEN``. Validator Assurance is a protected-main workflow and its
``merge-authority`` job validates the dispatched branch head. The independent external
``protected-repin-gate`` remains unchanged and still controls merge separately.
"""
from __future__ import annotations

import base64
import json
import os
import re
import time
from typing import Any, Callable

from tools import run_living_research_promotion as core

QUARANTINED = "__FAR_GITHUB_TOKEN_QUARANTINED__"
VALIDATOR_WORKFLOW = "validator-assurance.yml"
MERGE_AUTHORITY = "merge-authority"
PUSH_REF_RE = re.compile(r"^HEAD:refs/heads/automation/living-promotion-[0-9a-f]{40}-[0-9a-f]{40}$")
BANNED_LOCAL_GIT_PREFIXES = (
    "credential.",
    "http.",
    "include.",
    "includeif.",
    "url.",
)
BANNED_LOCAL_GIT_KEYS = {"core.hookspath", "core.sshcommand"}


class AdapterError(RuntimeError):
    pass


def _token_env(token: str) -> dict[str, str]:
    env = {**os.environ, "GH_TOKEN": token}
    env.pop(core.PR_TOKEN_ENV, None)
    return env


def _canonical_repo_url() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) is None:
        raise AdapterError(f"invalid GITHUB_REPOSITORY identity: {repo!r}")
    return f"https://github.com/{repo}"


def _assert_safe_local_push_config(original_git: Callable[..., str]) -> None:
    names = original_git("config", "--local", "--name-only", "--list").splitlines()
    normalized = [name.strip().lower() for name in names if name.strip()]
    forbidden = sorted(
        name
        for name in normalized
        if name in BANNED_LOCAL_GIT_KEYS or name.startswith(BANNED_LOCAL_GIT_PREFIXES)
    )
    if forbidden:
        raise AdapterError(f"unsafe local Git configuration before privileged push: {forbidden}")
    origins = [row.strip() for row in original_git("config", "--local", "--get-all", "remote.origin.url").splitlines() if row.strip()]
    if origins != [_canonical_repo_url()]:
        raise AdapterError(f"origin URL changed before privileged push: {origins!r}")


def _install_bounded_auth(token: str, captured: dict[str, Any]) -> None:
    """Patch the core's GitHub boundaries while keeping the real token out of ambient env."""
    original_git = core.git
    original_create = core.create_or_recover_pr

    def secure_gh(*args: str, check: bool = True) -> str:
        return core.run("gh", *args, check=check, env=_token_env(token)).stdout.strip()

    def secure_git(*args: str) -> str:
        if args and args[0] == "push":
            if len(args) != 3 or args[1] != "origin" or PUSH_REF_RE.fullmatch(args[2]) is None:
                raise AdapterError(f"unexpected privileged push shape: {args!r}")
            _assert_safe_local_push_config(original_git)
            encoded = base64.b64encode(f"x-access-token:{token}".encode("utf-8")).decode("ascii")
            env = {
                **os.environ,
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
                "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {encoded}",
            }
            return core.run(
                "git", "-c", "core.hooksPath=/dev/null", "push", _canonical_repo_url(), args[2], env=env
            ).stdout.strip()
        return original_git(*args)

    def tracked_create(branch: str, plan_path, pr_token: str) -> tuple[int, bool]:
        if pr_token != token:
            raise AdapterError("promotion PR credential diverged from the quarantined job token")
        number, created = original_create(branch, plan_path, pr_token)
        captured["branch"] = branch
        captured["pr_number"] = number
        captured["created"] = created
        return number, created

    core.gh = secure_gh
    core.git = secure_git
    core.create_or_recover_pr = tracked_create


def _remote_head(branch: str, token: str) -> str:
    repo = os.environ["GITHUB_REPOSITORY"]
    raw = core.run(
        "gh", "api", "-X", "GET", f"repos/{repo}/git/ref/heads/{branch}", env=_token_env(token)
    ).stdout
    payload = json.loads(raw)
    obj = payload.get("object")
    head_sha = obj.get("sha") if isinstance(obj, dict) else None
    if not isinstance(head_sha, str) or core.promoter.HEX40_RE.fullmatch(head_sha) is None:
        raise AdapterError(f"could not resolve exact remote head for {branch}")
    return head_sha


def _check_runs(repo: str, head_sha: str, token: str) -> list[dict[str, Any]]:
    raw = core.run(
        "gh", "api", "-X", "GET",
        f"repos/{repo}/commits/{head_sha}/check-runs?check_name={MERGE_AUTHORITY}&per_page=100",
        env=_token_env(token),
    ).stdout
    payload = json.loads(raw)
    runs = payload.get("check_runs")
    if not isinstance(runs, list):
        raise AdapterError("GitHub returned malformed merge-authority check-run data")
    return [row for row in runs if isinstance(row, dict) and row.get("name") == MERGE_AUTHORITY]


def _validator_runs(repo: str, branch: str, token: str) -> list[dict[str, Any]]:
    raw = core.run(
        "gh", "run", "list", "--repo", repo, "--workflow", VALIDATOR_WORKFLOW,
        "--branch", branch, "--event", "workflow_dispatch", "--limit", "30",
        "--json", "databaseId,headSha,status,conclusion",
        env=_token_env(token),
    ).stdout
    payload = json.loads(raw)
    if not isinstance(payload, list):
        raise AdapterError("GitHub returned malformed Validator Assurance run data")
    return [row for row in payload if isinstance(row, dict)]


def ensure_merge_authority(branch: str, pr_number: int, token: str) -> None:
    """Bind the exact PR/head and enqueue trusted Validator Assurance exactly when absent."""
    repo = os.environ["GITHUB_REPOSITORY"]
    head_sha = _remote_head(branch, token)
    pr_raw = core.run(
        "gh", "pr", "view", str(pr_number), "--repo", repo,
        "--json", "state,baseRefName,headRefName,headRefOid",
        env=_token_env(token),
    ).stdout
    pr = json.loads(pr_raw)
    expected = {
        "state": "OPEN",
        "baseRefName": core.BASE_BRANCH,
        "headRefName": branch,
        "headRefOid": head_sha,
    }
    for key, wanted in expected.items():
        if pr.get(key) != wanted:
            raise AdapterError(f"promotion PR exact-head invariant failed: {key}={pr.get(key)!r}, expected {wanted!r}")

    checks = _check_runs(repo, head_sha, token)
    if checks:
        active = [row for row in checks if row.get("status") != "completed"]
        successful = [row for row in checks if row.get("status") == "completed" and row.get("conclusion") == "success"]
        if active or successful:
            print(f"merge-authority already exists for exact promotion head {head_sha}; no duplicate dispatch")
            return
        conclusions = sorted({str(row.get("conclusion")) for row in checks})
        raise AdapterError(
            f"merge-authority already failed for exact promotion head {head_sha}: {conclusions}; refusing automatic rerun"
        )

    existing = [row for row in _validator_runs(repo, branch, token) if row.get("headSha") == head_sha]
    # A dispatched workflow may be queued before GitHub creates its job/check
    # runs. Absence of merge-authority alone does not justify another dispatch.
    if any(row.get("status") != "completed" for row in existing):
        print(f"Validator Assurance is already pending for exact promotion head {head_sha}; no duplicate dispatch")
        return
    failed = [row for row in existing if row.get("conclusion") != "success"]
    if failed:
        conclusions = sorted({str(row.get("conclusion")) for row in failed})
        raise AdapterError(
            f"Validator Assurance already failed for exact promotion head {head_sha}: {conclusions}; refusing automatic rerun"
        )
    before = {int(row["databaseId"]) for row in existing if isinstance(row.get("databaseId"), int)}
    core.run(
        "gh", "workflow", "run", VALIDATOR_WORKFLOW, "--repo", repo, "--ref", branch,
        env=_token_env(token),
    )

    for _ in range(20):
        time.sleep(2)
        for row in _validator_runs(repo, branch, token):
            run_id = row.get("databaseId")
            if row.get("headSha") == head_sha and isinstance(run_id, int) and run_id not in before:
                print(f"Validator Assurance dispatch #{run_id} is bound to exact promotion head {head_sha}")
                return
    raise AdapterError("Validator Assurance dispatch returned success but no new exact-head run appeared")


def main() -> int:
    token = os.environ.pop("GH_TOKEN", "")
    if not token:
        raise AdapterError("GH_TOKEN is required")
    if os.environ.get(core.PR_TOKEN_ENV):
        raise AdapterError(f"legacy {core.PR_TOKEN_ENV} must not be supplied by the workflow")

    # The legacy core checks for GH_TOKEN and consumes PR_TOKEN_ENV. Give it a non-secret
    # sentinel for the former and the real token only through the latter; main() immediately
    # pops PR_TOKEN_ENV before any materialization/validation subprocess can inherit it.
    os.environ["GH_TOKEN"] = QUARANTINED
    os.environ[core.PR_TOKEN_ENV] = token
    captured: dict[str, Any] = {}
    _install_bounded_auth(token, captured)
    try:
        result = core.main()
    finally:
        os.environ.pop("GH_TOKEN", None)
        os.environ.pop(core.PR_TOKEN_ENV, None)
    if result:
        return result
    if captured:
        ensure_merge_authority(str(captured["branch"]), int(captured["pr_number"]), token)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AdapterError, core.RunnerError, core.promoter.PromotionError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"living-research promotion CI adapter failed closed: {exc}", file=__import__("sys").stderr)
        raise SystemExit(2)
