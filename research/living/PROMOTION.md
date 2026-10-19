# Governed living-research promotion

Status: **Research infrastructure; fail closed; no scientific authority is delegated to automation**

`FAR-LIVING-PROMOTION-001` consumes the permanent draft PR #490 only as untrusted Research data. It may package already-governed state into a separate protected PR. It may not decide scientific acceptance, promote metadata into evidence, or bypass the lifecycle.

## Immutable source and execution boundary

The only source inbox is open draft PR #490, `automation/living-research-inbox` into `main`. A transaction freezes the exact source head and exact protected-main base, fetches those refs explicitly, and executes only tools/configuration from protected `main`. Source-branch code is never executed.

A promotion branch is keyed by both exact commits:

`automation/living-promotion-<40-hex-source>-<40-hex-base>`

If either PR #490 or `main` moves before publication, the attempt fails. A new base produces a new branch rather than rewriting a stale promotion attempt.

## Research snapshots: review is not authorization

`review-dispositions-v1.0.json` is durable review/queue memory. Membership there is **not** snapshot authority.

A reviewed candidate is mechanically snapshot-eligible only when protected `snapshot-authorizations-v1.0.json` contains one exact authorization with:

- `candidate_id`;
- exact `candidate_sha256`;
- exact `source_key` and allowed review `disposition`;
- exact `review_basis` path and `review_basis_sha256`;
- `review_record_sha256`, the canonical hash of the complete protected review row;
- `authorization_status: ACCEPTED_FOR_MECHANICAL_SNAPSHOT`.

If that authorization is absent, the candidate remains unpromoted. Existing historical review rows are not retroactively upgraded merely by hashing their current candidate bytes.

A Research snapshot preserves `authority: Research` and lifecycle stage `DISCOVERED`; it changes no claim, theorem, novelty, EFR, external-validity, utility, or independence status.

## Canonical edit proposals

A canonical edit is stronger. The source proposal must be at `PROMOTION_PROPOSED`, and protected `promotion-authorizations-v1.0.json` must bind the exact:

- proposal SHA-256;
- candidate SHA-256;
- canonical operation-set SHA-256;
- Question, Execution, Observation, Discovery, Replication, and Acceptance artifact SHA-256 values;
- `authorization_status: ACCEPTED_FOR_MECHANICAL_PROMOTION`.

Proposal provenance uses exact path/hash pairs:

```json
{
  "provenance": {
    "question": {"path": "...", "sha256": "..."},
    "execution": {"path": "...", "sha256": "..."},
    "observation": {"path": "...", "sha256": "..."},
    "discovery": {"path": "...", "sha256": "..."},
    "replication": {"path": "...", "sha256": "..."},
    "acceptance": {"path": "...", "sha256": "..."}
  }
}
```

Each `write_file` operation binds the exact current-main preimage (`ABSENT` for a new file), exact payload hash, target path, and payload source path. Duplicate targets, cross-proposal collisions, unsafe paths, symlink paths, protected/control-plane paths, disallowed extensions, stale preimages, or payload hash mismatches fail closed.

## Project-changing studies

`PROJECT_CHANGE_REQUIRED` is a governed review disposition, not an automated relevance score. It may be recorded only after the ordinary research lifecycle has established that the accepted result requires a Project FAR correction.

A row with that disposition is incomplete unless it binds one exact scientific `proposal_id`, leaves the metadata-only review queue, and has both an exact snapshot authorization and an exact `PROMOTION_PROPOSED` canonical-edit authorization. The permanent inbox must contain the bound candidate, the exact proposal, at least one `write_file` operation, and every referenced payload. `tools/check_living_project_change_obligations.py` fails closed on any missing component before promotion runs.

The same governed review must also declare whether repository implementation is required. If `implementation_required` is false, `implementation_proposal_id` is null. If it is true, the review must bind one exact `IMPLEMENTATION_PROPOSED` package plus an exact protected authorization in `implementation-authorizations-v1.0.json`. That package is handled by `FAR-LIVING-IMPLEMENTATION-001`, not by the scientific promoter.

A successful explicit validation of the rolling inbox triggers the protected-main routing workflows. Changes to the protected acceptance/authorization surfaces on `main` also trigger them. Scheduled passes remain recovery paths. The scientific promotion transaction independently revalidates hashes, provenance, preimages, targets, and the frozen source/base before opening the scientific correction PR. When implementation is required, the implementation transaction independently freezes the same trust boundary, validates exact authorization/preimage/payload hashes, and opens a separate implementation PR.

Automatic PR creation is required once the accepted package is complete. Automatic merge is not permitted; protected review and merge authority remain controlling.

## Write boundary

Automatic scientific/canonical targets are limited by `promotion-policy-v1.0.json`. `.github/`, `tools/`, `tests/`, validation/bootstrap code, `docs/governance/`, all `research/living/` governance/control files, and `research/living/inbox/.rolling-pr-anchor.json` are never scientific-promotion payload targets.

If accepted information also requires executable or control-plane changes, those changes use the separate `FAR-LIVING-IMPLEMENTATION-001` path defined in `implementation-policy-v1.0.json` and `IMPLEMENTATION.md`. PR #490 may carry the proposed implementation bytes as untrusted data, but protected `main` must first authorize the exact candidate, review row, proposal, operation set, preimages, and payload hashes. The implementation materializer executes only protected-main code; it copies and seals the exact authorized bytes without executing them, then opens a separate implementation PR.

If that implementation PR changes merge-authority's own declared assurance-sensitive surface, automation may create the PR but may not use the modified assurance surface to certify itself. Independent protected validation is required for that self-change.

This separation prevents the research inbox from becoming an unreviewed software supply chain while still ensuring that a project-changing study automatically surfaces all necessary scientific and implementation changes as reviewable PRs.

The only non-plan files permitted to change during scientific promotion are the explicitly declared deterministic reconciliation outputs in `trusted_generated_paths`: living status/state and the dependent corpus synthesis/current frontier. The runner rebuilds the corpus views after living reconciliation and before canonical validation. The independent head verifier reconstructs both stages from the frozen base plus planned payloads and rejects a rehashed forged view.

## Transaction seal

Materialization installs a fail-closed pre-commit hook. The runner stages only planned targets plus actually changed trusted-generated paths—never `git add -A`. Immediately before commit the seal independently requires:

1. the source head still equals the frozen source SHA;
2. current protected `main` still equals the frozen base SHA;
3. every planned file is staged and byte-identical to its approved result;
4. no unplanned staged, deleted, unstaged, or untracked repository file remains;
5. all preimages still match the frozen base;
6. the rolling anchor is absent;
7. one manifest records the exact SHA-256 and authority class of every promoted file.

The promotion commit must be exactly one commit whose parent is the frozen base.

## Independent protected verification

`tools/check_living_promotion_head.py` is independent of the promoter. Canonical tests run it inside `merge-authority`. For pull-request events GitHub checks out a synthetic merge commit, so the verifier resolves and checks the exact `GITHUB_HEAD_REF` promotion commit instead of trusting synthetic `HEAD`.

The verifier is read-only: it does not fetch or mutate `.git`. It re-derives the promotion from the protected base and rejects stale bases, forged/missing manifests, extra files, multiple commits, unsealed bytes, unauthorized snapshots, altered review/review-basis bytes, unauthorized proposal operations, provenance drift, stale preimages, and governance/self-modifying targets.

Strict branch protection requires the `merge-authority` check to be current with `main`. A base advance therefore invalidates the promotion and requires a new source+base transaction.

## Publication boundary

The scheduled workflow calls `tools/run_living_research_promotion_ci.py`, the native-token adapter around `tools/run_living_research_promotion.py`. The runner may create/recover the separate promotion PR. It never merges, approves itself, changes branch protection, writes directly to `main`, or uses the permanent inbox PR as the merge vehicle.

The separate implementation runner follows the same publication rule: it may create/recover the exact implementation PR, but it never merges or writes directly to `main`. Its full contract is in `IMPLEMENTATION.md`.

If GitHub Actions lacks permission to create a PR, the exact branch is preserved and the run fails. No broader token or protection bypass is substituted.

### Promotion PR credential

GitHub starts no `pull_request` workflow for a PR opened with `GITHUB_TOKEN`. The CI adapter therefore uses the ephemeral job token for bounded GitHub operations and explicitly dispatches `validator-assurance.yml` on the exact promotion branch when `merge-authority` is absent.

- Checkout uses `persist-credentials: false`. The adapter removes the real token from its ambient environment before materialization or validation, and injects it only into bounded GitHub API and push calls.
- The workflow requests `contents: write`, `pull-requests: write`, and `actions: write`. GitHub must allow Actions to create pull requests; a permission failure preserves the branch and stops the transaction.
- Before dispatch, the adapter verifies the open PR's base, branch, and exact remote head. A pending check or dispatched workflow on that head suppresses duplicate dispatch, including the interval before GitHub creates check runs.
- Failed exact-head authority or a failed dispatched workflow stops automation; the adapter never automatically retries it. A newly dispatched run must appear with the exact expected head.
- Validator Assurance still performs its protected validation. Its result and the separate `protected-repin-gate` remain required; dispatch itself grants no merge authority.

This workflow does not require the former promotion App installation, private key, or `living-promotion` environment. The independent repin-gate App and its owner-signature requirements are unchanged. The standalone core runner retains its legacy credential interface; scheduled operation uses the CI adapter.

## Core rule

No bytes become canonical merely because the automation considers them relevant. Promotion requires the exact bytes, exact protected authorization, exact provenance, exact base state, exact sealed diff, and exact protected validation to agree. Any uncertainty or mismatch produces **no promotion**.
