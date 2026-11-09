# Live Repository Workboard

Status: **Provisional**. Authority: advisory operations only; no governance or claim-promotion authority.

Project FAR maintains separate authoritative sources for project state, scientific findings, repository architecture, and protected merges. This workboard provides a short, current view of **open GitHub pull requests and issues** without copying those authorities or maintaining a manually edited PR-status register.

## Run

From the repository root:

```bash
python tools/repository_workboard.py
python tools/repository_workboard.py --format json
python -m unittest tests.test_repository_workboard
```

The script uses Python's standard library and read-only GitHub REST endpoints. It reads `GH_TOKEN` or `GITHUB_TOKEN` if present; public-repository access may work without authentication but has stricter rate limits. No token is written to the report. The command prints to stdout and does not commit, label, assign, request reviews, modify branches, or merge.

The report records the retrieved time, default branch SHA, each open PR's exact head SHA, draft/open state, last update, assignees, and the open issues with their labels/assignees. It removes GitHub's PR entries from the issue list and identifies **PR #490** as the permanent unmergeable research inbox. It counts unlabeled and unassigned issues for triage. JSON output uses `far-repository-workboard/1`, with `authority: ADVISORY_ONLY`.

## Read it correctly

- **OPEN/DRAFT** are GitHub operational metadata, not READY or approved.
- Every PR has `merge_readiness: NOT_EVALUATED`. Required check contexts, thread resolution, independent exact-head review, dependencies, and protected owner authorization require the normal source-bound evaluation.
- The default branch is checked before and after the API reads. If it changes, the command fails rather than presenting a coherent-main snapshot that was not observed. Issues and PRs are still fetched sequentially, so this is not a transactional snapshot of every item.
- A clean list is not evidence of repository health, research completeness, external validation, or scientific status.
- For any PR merging into `main`, apply [PR review convergence](../governance/pr-review-convergence.md) and the actual branch-protection gates. The workboard does **not** replace a current-head convergence manifest or merge-authority evidence.
- For meaning, scope, and authority, follow [project status](../project-status.md), [canonical map](../CANONICAL_MAP.md), and the [repository domain registry](../architecture/repository-domain-registry.md). The [generated file index](../planning/repository-index.md) is for file discovery; it is not a live issue/PR tracker.

## Operating routine

Use the live workboard to find open work and missing assignment/labels. Open the individual GitHub item for its actual scope, blockers, owner, dependencies, and source evidence. Track substantive review findings and corrective work in the PR's required root-cause ledger; do not promote a concise workboard row into a gate decision. Prioritize the existing bounded WIP policy recorded in [fix-register program issue #364](https://github.com/n0tf0und0ut/Project-FAR/issues/364): one P0 research slot, one P0 commercial slot, and one maintenance slot. Do not create additional competing status spreadsheets or edit canonical scientific state from the workboard.

## Verification boundary

The unit tests check complete pagination, PR-versus-issue filtering, the #490 exception, exact default-branch SHA drift detection, and fail-closed handling of malformed GitHub responses. Live GitHub retrieval must be run in an environment with network access; unit tests alone do not certify remote availability or all governance gates.

This tool is additive operational discovery tooling. It changes no frozen research input, accepted theory, workflow, branch protection, review policy, or merge procedure.
