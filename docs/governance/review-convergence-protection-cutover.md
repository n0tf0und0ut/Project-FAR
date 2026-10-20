# Review-convergence branch-protection cutover

Status: **prepared, NOT activated**. Changing repository files does not change GitHub's live branch protection. This document must never be cited as evidence that the third check is required.

## Verified starting state and why no automated cutover

On 2026-10-20 the canonical branch-protection verifier expected these two strictly source-bound checks:

| Context | Required source |
| --- | --- |
| `merge-authority` | GitHub Actions, App ID `15368` |
| `protected-repin-gate` | FAR owner's dedicated gate App, App ID `5073230` |

The two connected GitHub integrations returned HTTP **403 Resource not accessible by integration** when reading the protected branch's administrative API. Consequently no agent-side Admin write or authenticated full-protection readback is available. The owner's secured, independent gate installation is not an administration token and must never be turned into one.

The newly deployed `pr-review-convergence-observation` check is generated only from a trusted-main scheduled or manual `PR Review Convergence` workflow; PR-origin events cannot publish this check. On the PR heads sampled before this document, the observation was absent. Enabling it as required without verifying publication first can fail-closed indefinitely.

## Intended target and source limits

**Add**, never replace:

| Context | Required source |
| --- | --- |
| `merge-authority` | GitHub Actions `15368` (unchanged) |
| `protected-repin-gate` | Dedicated FAR App `5073230` (unchanged) |
| `pr-review-convergence-observation` | GitHub Actions `15368` (additional process gate) |

Keep strict/up-to-date checks, administrator enforcement, no force pushes/deletions, required conversation resolution, stale review dismissal, and all other existing protection settings unchanged.

**Trust limitation:** `pr-review-convergence-observation` is a **process gate, not an adversarial security authority**. It is bound to GitHub Actions rather than a dedicated trusted App. GitHub Actions check names can be shadowed by candidate-authored workflows under the same App identity. Scheduled evaluation also cannot provide atomic freshness after a review-state change. It must not be represented as equivalent to the independent `protected-repin-gate` App. For an adversary-resistant hard gate, migrate this review decision into the owner-controlled App and bind the required context to that App after separately reviewed and owner-signed deployment. Never loosen `protected-repin-gate` to compensate.

## Required live preflight (before any setting is changed)

1. Identify one currently open, ready-for-review PR targeting `main`, its **exact current head SHA**, and its actual review state.
2. At the trusted protected-main workflow `Actions → PR Review Convergence → Run workflow`, provide that PR number. This is a *manual, authorized* main workflow dispatch; do not execute a PR-authored job with checks-write.
3. Require a completed `pr-review-convergence-observation` check on that **exact head**, posted by `github-actions` with App ID `15368`. Reject check name alone, a different App source, wrong head SHA, missing check, or a neutral/skipped run.
4. Verify that a pending or unresolved Codex review or an unresolved review thread produces a failure, and that a subsequent completed clean review produces success **on the same SHA**. The check publisher must re-evaluate rather than replay stale output.
5. Reopen a resolved review thread or submit a new finding and verify the next trusted dispatch produces failure, with source identities in the artifact. Document the observable delay. A queued scheduled job is not an atomic guarantee.
6. Check that the currently required `merge-authority` and `protected-repin-gate` remain successful and correctly source-bound. If any probe fails, **STOP**: do not edit branch protection.

## Owner-only protection setting (after preflight PASS)

On GitHub as the repository owner: `n0tf0und0ut/Project-FAR → Settings → Branches → main protection rule → Edit`.

Under **Require status checks to pass before merging**:

- Keep `Require branches to be up to date before merging`.
- Retain `merge-authority` from GitHub Actions (App `15368`).
- Retain `protected-repin-gate` from the dedicated FAR App (App `5073230`).
- **Add** `pr-review-convergence-observation`, selecting **GitHub Actions** as its source (App `15368`). Never select `Any source`.
- Preserve every other existing setting and save through the owner's authenticated UI.

This is an authorized administrative change **outside** Project-FAR's code-repin signature ledger. It does not call for inventing a user signature or bypassing the gate App.

## Required read-back and negative enforcement probe

1. In the owner's **separate gate repository**, run `protected-repin-gate` with mode `audit`. The App publishes an authenticated `protected-repin-audit` check on current main with the full live settings.
2. Require the audit to report strict enforcement and both existing App bindings unchanged. Separately compare the three required check contexts and their exact `app_id` fields against the table above. A two-check readback is a failure of cutover.
3. Run `python tools/check_validation_protection.py --gate-app-id 5073230 --require-review-convergence` in a **trusted owner-authorized context** possessing `Administration: read`. This command is read-only and exits nonzero on any mismatch. Do not restore the revoked `FAR_GITHUB_ADMIN_TOKEN` or expose an administration token to candidate CI.
4. Execute a negative probe on a disposable PR whose relevant review state is unresolved. The trusted manual dispatch must post `pr-review-convergence-observation: failure` and GitHub must block normal merge while both existing required checks remain green.
5. After completing and independently verifying review on that same head, rerun the trusted publisher and verify that GitHub now permits merging *only* when all required checks pass.
6. Record exact PR/head SHA, check-run IDs, App IDs, protection audit, GitHub mergeability, and read-back result. The change is **not completed** until both negative and positive live probes pass.

## Rollback

If a third check never appears, misbinds, or causes an unintended operational deadlock, the owner must restore the **previous two-check contract only**, retaining strictness, App binding and all unrelated settings. Run the owner's protection audit again and repeat the current-profile validation. Do not bypass branch protection, post counterfeit checks, or create privileged long-lived credentials to recover.

## Deployment state

The prospective three-check contract is available as an explicit **read-only preflight** using `--require-review-convergence`; without that option `tools/check_validation_protection.py` still checks the active historical two-check contract. This avoids silently declaring rollout complete or breaking existing protection audits during an unfinished cutover.
