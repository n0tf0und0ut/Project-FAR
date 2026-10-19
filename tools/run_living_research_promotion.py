#!/usr/bin/env python3
"""Transactional runner for governed living-research promotion from permanent PR #490."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from tools import check_living_project_change_obligations as project_changes
from tools import check_living_promotion_head as integrity
from tools import promote_living_research as promoter

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PR = 490
SOURCE_BRANCH = "automation/living-research-inbox"
BASE_BRANCH = "main"
SNAPSHOT_AUTHS = Path("research/living/snapshot-authorizations-v1.0.json")
SNAPSHOT_STATUS = "ACCEPTED_FOR_MECHANICAL_SNAPSHOT"
# Installation token of the dedicated promotion App (pull requests: write, this repository only).
# GitHub starts no pull_request workflow for a PR opened with GITHUB_TOKEN, so only a PR opened
# with this credential gets the required merge-authority check from a pull_request run.
PR_TOKEN_ENV = "FAR_PROMOTION_PR_TOKEN"


class RunnerError(RuntimeError):
    pass


def run(*args: str, check: bool = True, capture: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(list(args), cwd=ROOT, text=True, capture_output=capture, env=env)
    if check and result.returncode:
        detail = (result.stderr or result.stdout or "").strip()
        raise RunnerError(f"{' '.join(args)} failed: {detail}")
    return result


def git(*args: str) -> str:
    return run("git", *args).stdout.strip()


def gh(*args: str, check: bool = True) -> str:
    return run("gh", *args, check=check).stdout.strip()


def source_snapshot() -> dict[str, Any]:
    raw = gh(
        "pr", "view", str(SOURCE_PR), "--repo", os.environ["GITHUB_REPOSITORY"],
        "--json", "state,isDraft,baseRefName,headRefName,headRefOid",
    )
    value = json.loads(raw)
    expected = {"state": "OPEN", "isDraft": True, "baseRefName": BASE_BRANCH, "headRefName": SOURCE_BRANCH}
    for key, wanted in expected.items():
        if value.get(key) != wanted:
            raise RunnerError(f"PR #490 identity invariant failed: {key}={value.get(key)!r}, expected {wanted!r}")
    head = value.get("headRefOid")
    if not isinstance(head, str) or promoter.HEX40_RE.fullmatch(head) is None:
        raise RunnerError("PR #490 returned no exact lowercase 40-hex head")
    return value


def fetch_inputs() -> None:
    git(
        "fetch", "--no-tags", "origin",
        "+refs/heads/main:refs/remotes/origin/main",
        f"+refs/heads/{SOURCE_BRANCH}:refs/remotes/origin/{SOURCE_BRANCH}",
    )


def project_change_obligation_gate(source_ref: str, plan: dict[str, Any]) -> None:
    """Bind every accepted project change to this runner's exact frozen source."""
    errors = project_changes.check(ROOT, source_ref)
    if errors:
        raise RunnerError("project-change obligation failed: " + "; ".join(errors))
    obligations = project_changes.local_obligations(ROOT)
    if not obligations or not plan.get("already_promoted"):
        return
    manifest_path = ROOT / plan["manifest_path"]
    if not manifest_path.is_file():
        raise RunnerError("already-promoted plan lacks its canonical manifest")
    manifest = promoter.load(manifest_path)
    represented = {
        row.get("proposal_id")
        for row in manifest.get("canonical_proposals", [])
        if isinstance(row, dict) and isinstance(row.get("proposal_id"), str)
    }
    missing = sorted(
        obligation["proposal_id"]
        for obligation in obligations
        if obligation["proposal_id"] not in represented
    )
    if missing:
        raise RunnerError(
            "this inbox head was promoted before newly required project-change proposals were authorized; "
            "refresh the permanent inbox on current protected main before promotion: " + ", ".join(missing)
        )


def exact_snapshot_authorization_gate(plan: dict[str, Any]) -> list[dict[str, str]]:
    """Require an explicit protected authorization for each exact Research snapshot."""
    review_data = promoter.load(ROOT / promoter.REVIEWS)
    review_rows = review_data.get("reviewed_candidates", [])
    if not isinstance(review_rows, list):
        raise RunnerError("review registry is malformed")
    reviews = {
        row.get("candidate_id"): row
        for row in review_rows
        if isinstance(row, dict) and isinstance(row.get("candidate_id"), str)
    }
    if len(reviews) != len(review_rows):
        raise RunnerError("review registry contains malformed or duplicate candidate rows")

    auth_data = promoter.load(ROOT / SNAPSHOT_AUTHS)
    auth_rows = auth_data.get("authorizations", [])
    if (
        auth_data.get("schema_version") != "1.1"
        or auth_data.get("program_id") != "FAR-LIVING-SNAPSHOT-AUTHORIZATIONS-001"
        or auth_data.get("authority") != "Research"
        or not isinstance(auth_rows, list)
    ):
        raise RunnerError("snapshot authorization registry identity/version drift")
    auths = {
        row.get("candidate_id"): row
        for row in auth_rows
        if isinstance(row, dict) and isinstance(row.get("candidate_id"), str)
    }
    if len(auths) != len(auth_rows):
        raise RunnerError("snapshot authorization registry contains malformed or duplicate candidate rows")

    blocked: list[dict[str, str]] = []
    retained: list[dict[str, Any]] = []
    for item in plan.get("snapshot_candidates", []):
        cid = item["candidate_id"]
        review = reviews.get(cid)
        auth = auths.get(cid)
        if not isinstance(review, dict):
            raise RunnerError(f"{cid}: protected review row disappeared")
        if auth is None:
            blocked.append({"candidate_id": cid, "reason": "exact snapshot authorization absent"})
            continue
        required = {
            "candidate_id", "candidate_sha256", "source_key", "disposition",
            "review_basis", "review_basis_sha256", "review_record_sha256", "authorization_status",
        }
        if set(auth) != required:
            raise RunnerError(f"{cid}: snapshot authorization fields are malformed")
        for field in ("candidate_sha256", "review_basis_sha256", "review_record_sha256"):
            if not isinstance(auth[field], str) or promoter.HEX64_RE.fullmatch(auth[field]) is None:
                raise RunnerError(f"{cid}: snapshot authorization {field} is malformed")
        if auth["authorization_status"] != SNAPSHOT_STATUS:
            raise RunnerError(f"{cid}: snapshot authorization status drift")
        if auth["source_key"] != item["source_key"] or auth["disposition"] != item["disposition"] or auth["review_basis"] != item["review_basis"]:
            raise RunnerError(f"{cid}: snapshot authorization does not match reviewed identity/disposition")
        if auth["candidate_sha256"] != item["source_sha256"]:
            raise RunnerError(f"{cid}: snapshot authorization does not match exact candidate bytes")
        if auth["review_record_sha256"] != promoter.canonical_json_sha(review):
            raise RunnerError(f"{cid}: snapshot authorization does not match exact protected review row")
        basis_path = promoter.safe(review["review_basis"])
        basis = promoter.mainbytes(ROOT, basis_path)
        if basis is None or promoter.h(basis) != auth["review_basis_sha256"]:
            raise RunnerError(f"{cid}: snapshot authorization review-basis hash mismatch")
        retained.append(item)
    plan["snapshot_candidates"] = retained
    plan["snapshot_authorization_required"] = blocked
    plan["actionable"] = bool(retained or plan.get("canonical_proposals")) and not plan.get("fatal")
    return blocked


def forbidden_target_gate(plan: dict[str, Any]) -> None:
    policy = promoter.load(ROOT / promoter.POLICY)
    prefixes = policy.get("canonical_forbidden_prefixes", [])
    if not isinstance(prefixes, list) or any(not isinstance(x, str) or not x for x in prefixes):
        raise RunnerError("canonical_forbidden_prefixes policy is malformed")
    for proposal in plan.get("canonical_proposals", []):
        for operation in proposal.get("operations", []):
            path = promoter.safe(operation["path"])
            if any(path.startswith(prefix) for prefix in prefixes):
                raise RunnerError(f"canonical proposal targets forbidden prefix: {path}")


def branch_name(source_sha: str, base_sha: str) -> str:
    return f"automation/living-promotion-{source_sha}-{base_sha}"


def remote_branch_exists(branch: str) -> bool:
    return run("git", "ls-remote", "--exit-code", "--heads", "origin", branch, check=False).returncode == 0


def changed_paths() -> set[str]:
    modified = {x for x in git("diff", "--name-only", "--").splitlines() if x}
    untracked = {x for x in git("ls-files", "--others", "--exclude-standard").splitlines() if x}
    return modified | untracked


def stage_authorized(plan: dict[str, Any]) -> None:
    policy = promoter.load(ROOT / promoter.POLICY)
    planned = promoter.planned_paths(plan)
    generated = set(policy["trusted_generated_paths"])
    observed = changed_paths()
    allowed = planned | generated
    unexpected = observed - allowed
    if unexpected:
        raise RunnerError("materialization/validation produced unauthorized paths: " + ", ".join(sorted(unexpected)))
    missing = planned - observed
    if missing:
        raise RunnerError("planned paths were not materialized: " + ", ".join(sorted(missing)))
    to_stage = sorted(observed & allowed)
    if not to_stage:
        raise RunnerError("actionable plan produced no authorized repository changes")
    git("add", "--", *to_stage)


def run_validations() -> None:
    commands = [
        (
            sys.executable,
            "-m",
            "unittest",
            "tests.test_living_research_promotion",
            "tests.test_living_research_promotion_workflow",
            "tests.test_living_project_change_obligations",
            "-v",
        ),
        (sys.executable, "tools/reconcile_living_repo.py"),
        (sys.executable, "tools/reconcile_research_corpus.py", "--write"),
        (sys.executable, "tools/reconcile_research_corpus.py"),
        (sys.executable, "tools/check_living_research.py"),
        (sys.executable, "tools/check_research_gates.py"),
        (sys.executable, "tools/repo_health_check.py", "--fast"),
    ]
    for command in commands:
        run(*command, capture=False)


def verify_existing_branch(branch: str, base_sha: str, source_sha: str) -> str:
    git("fetch", "--no-tags", "origin", f"+refs/heads/{branch}:refs/remotes/origin/{branch}")
    head = git("rev-parse", f"origin/{branch}^{{commit}}")
    if git("rev-parse", f"{head}^") != base_sha:
        raise RunnerError("existing promotion branch parent does not equal its frozen base")
    manifest = f"{promoter.MANIFESTS}{source_sha}.json"
    if run("git", "cat-file", "-e", f"{head}:{manifest}", check=False).returncode:
        raise RunnerError("existing promotion branch lacks its exact source manifest")
    old_ref = os.environ.get("GITHUB_REF_NAME")
    old_head = os.environ.get("GITHUB_HEAD_REF")
    os.environ["GITHUB_REF_NAME"] = branch
    os.environ["GITHUB_HEAD_REF"] = branch
    try:
        errors = integrity.verify(ROOT)
    finally:
        if old_ref is None: os.environ.pop("GITHUB_REF_NAME", None)
        else: os.environ["GITHUB_REF_NAME"] = old_ref
        if old_head is None: os.environ.pop("GITHUB_HEAD_REF", None)
        else: os.environ["GITHUB_HEAD_REF"] = old_head
    if errors:
        raise RunnerError("existing promotion branch integrity failed: " + "; ".join(errors))
    return head


def create_or_recover_pr(branch: str, plan_path: Path, pr_token: str) -> tuple[int, bool]:
    """Open the promotion PR with the promotion App's token, never with GITHUB_TOKEN.

    The PR event then starts the ordinary pull_request workflows, including the required
    merge-authority, on the exact promotion head; nothing is dispatched on the PR's behalf.
    """
    repo = os.environ["GITHUB_REPOSITORY"]
    pr_env = {**os.environ, "GH_TOKEN": pr_token}
    existing = run(
        "gh", "pr", "list", "--repo", repo, "--head", branch, "--base", BASE_BRANCH,
        "--state", "open", "--json", "number", "--jq", ".[0].number // empty", env=pr_env,
    ).stdout.strip()
    if existing:
        return int(existing), False
    body_path = plan_path.with_suffix(".md")
    run(sys.executable, "tools/promote_living_research.py", "pr-body", "--plan", str(plan_path), "--output", str(body_path))
    result = run(
        "gh", "pr", "create", "--repo", repo, "--base", BASE_BRANCH, "--head", branch,
        "--title", f"Research: governed living-research promotion {plan_path.stem}",
        "--body-file", str(body_path), check=False, env=pr_env,
    )
    if result.returncode:
        raise RunnerError(
            "promotion branch was preserved but the promotion App could not create the PR; no main write or protection bypass was attempted: "
            + result.stderr.strip()
        )
    created = result.stdout.strip()
    number = int(run("gh", "pr", "view", created, "--repo", repo, "--json", "number", "--jq", ".number", env=pr_env).stdout.strip())
    return number, True


def main() -> int:
    # Taken out of the environment before any subprocess runs: only the PR calls receive it.
    pr_token = os.environ.pop(PR_TOKEN_ENV, "")
    if not os.environ.get("GITHUB_REPOSITORY") or not os.environ.get("GH_TOKEN"):
        raise RunnerError("GITHUB_REPOSITORY and GH_TOKEN are required")
    if not pr_token:
        raise RunnerError(
            f"{PR_TOKEN_ENV} is required: a promotion PR opened with GITHUB_TOKEN starts no pull_request "
            "workflow and can never satisfy merge-authority; configure the promotion App and retry"
        )
    first = source_snapshot()
    fetch_inputs()
    source_ref = f"origin/{SOURCE_BRANCH}"
    if git("rev-parse", f"{source_ref}^{{commit}}") != first["headRefOid"]:
        raise RunnerError("PR #490 head differs from fetched source branch")
    git("switch", "--detach", "origin/main")
    base_sha = git("rev-parse", "HEAD^{commit}")
    source_sha = first["headRefOid"]

    with tempfile.TemporaryDirectory(prefix="far-living-promotion-") as tmp:
        plan_path = Path(tmp) / f"{source_sha}.json"
        plan = promoter.build(ROOT, promoter.GitSource(ROOT, source_ref), source_sha, base_sha)
        project_change_obligation_gate(source_ref, plan)
        blocked = exact_snapshot_authorization_gate(plan)
        forbidden_target_gate(plan)
        promoter.dump(plan_path, plan)
        print(json.dumps({
            "source_head": source_sha,
            "base_main": base_sha,
            "actionable": plan["actionable"],
            "snapshot_candidates": len(plan.get("snapshot_candidates", [])),
            "snapshot_authorization_required": len(blocked),
            "canonical_proposals": len(plan.get("canonical_proposals", [])),
            "review_required": len(plan.get("review_required", [])),
        }, sort_keys=True))
        if plan.get("fatal"):
            raise RunnerError("promotion analysis has fatal blocks: " + "; ".join(plan.get("fatal_blocks", [])))
        if plan.get("already_promoted") or not plan.get("actionable"):
            return 0

        branch = branch_name(source_sha, base_sha)
        new_materialization = not remote_branch_exists(branch)
        if new_materialization:
            git("switch", "-c", branch, base_sha)
            promoter.materialize(ROOT, promoter.GitSource(ROOT, source_ref), plan)
            promoter.install_precommit_hook(ROOT, plan_path)
            run_validations()
            stage_authorized(plan)

            second = source_snapshot()
            fetch_inputs()
            if second["headRefOid"] != source_sha or git("rev-parse", f"origin/{SOURCE_BRANCH}^{{commit}}") != source_sha:
                raise RunnerError("PR #490 advanced during promotion; discard this attempt")
            if git("rev-parse", "origin/main^{commit}") != base_sha:
                raise RunnerError("main advanced during promotion; discard this attempt")

            git("config", "user.name", "project-far-promotion-bot")
            git("config", "user.email", "project-far-promotion-bot@users.noreply.github.com")
            git("commit", "-m", f"research: promote reviewed living-research state {source_sha} from {base_sha}")
            head_sha = git("rev-parse", "HEAD^{commit}")
            if git("rev-parse", "HEAD^") != base_sha:
                raise RunnerError("promotion commit parent drifted from frozen base")
            git("push", "origin", f"HEAD:refs/heads/{branch}")
        else:
            head_sha = verify_existing_branch(branch, base_sha, source_sha)

        pr_number, _created = create_or_recover_pr(branch, plan_path, pr_token)
        print(f"Promotion PR #{pr_number} is open for exact head {head_sha}; protected merge-authority remains controlling.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RunnerError, promoter.PromotionError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"living-research promotion runner failed closed: {exc}", file=sys.stderr)
        raise SystemExit(2)
