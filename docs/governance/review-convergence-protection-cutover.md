# Review-convergence branch-protection deployment and verification

Status: **three contexts observed live; eligible-event correction awaiting deployment**. Green advisory publications do not establish operational enforcement.

## Observed blocker

On 2026-10-20, `branches/main` exposed these source bindings:

| Required context | App ID |
|---|---|
| `merge-authority` | GitHub Actions `15368` |
| `protected-repin-gate` | Dedicated FAR gate `5073230` |
| `pr-review-convergence-observation` | GitHub Actions `15368` |

PR #588 at `42b51215418448d10f50a1153cb302da4bcfcb29` had all three visible checks successful, a clean exact-head Codex review, and zero unresolved threads. Its normal merge request failed with HTTP 405 because the review context was expected. The [incident record](../audits/pr-review-convergence-event-eligibility-2026-10-20.md) preserves exact check IDs and the event-eligibility cause.

## Deploy through the existing protected path

The native required job lives in `.github/workflows/required-pr-review-convergence.yml`, whose events are main-targeting `pull_request` and `pull_request_review` submission/edit/dismissal. This eligible event can load the reviewed candidate workflow before it reaches main. It therefore permits ordinary protected deployment without removing a requirement or changing settings. The collector code is checked out from protected `main`, never the candidate; the token has read permissions only and no persistent secret is used.

1. Freeze the correction head, protected-main base and complete diff. Run the regression tests, workflow validator, full hosted assurance and dedicated gate App. Obtain a substantive independent review covering the exact final head.
2. Observe that the native `pr-review-convergence-observation` job fails while exact-head review evidence is incomplete. Verify the source App, event, associated head and collector artifact; no skipped job counts as enforcement.
3. After the independent review is clean and all threads are resolved, rerun the latest eligible native job on that unchanged head. Require the event/current-head comparison, protected-main checkout, enforce-mode collector and post-check head comparison to succeed.
4. Require all three original context/App bindings and all other substantive checks. Use the normal expected-head merge API/UI for the correction. Record the final merge/main SHAs and verify that the original protection settings remain intact.
5. Refresh waiting PRs onto the resulting main without rewriting history, obtain exact-head review and assurance, and require their native eligible job. Review submissions, edits and dismissals automatically execute the required collector. For comment-only machine-state or thread changes, inspect fresh API evidence and rerun the current eligible job before merge; no atomic merge-time freshness guarantee is claimed.
6. Merge only through the ordinary protected path and verify final PR/main state. Do not label deployment complete based on a YAML test, scheduled advisory pass or metadata edit alone.

## Skipped-success boundary

The required job has no job-level condition, dependency or matrix. Its dedicated workflow has no comment/schedule/manual event; both eligible PR and review event families execute the same job unconditionally. Independent review discussion 4330779437 showed that co-locating it with `pull_request_review` could emit an eligible skipped success without enforcing the collector. Discussion 4330890559 requires unconditionally enforcing eligible review events to invalidate changed approval/submitted-findings state. Regression mutations reject an event condition that skips review enforcement, ineligible comment/schedule events, write permissions, candidate checkout, missing head binding and dependency-skipped success. Discussion 4330890566 adds the required workflow to both contract-validator path lists, with a regression binding both. Scheduled/manual publications use the distinct advisory context `pr-review-convergence-scheduled-observation`.

## Trust and readback limits

The native GitHub Actions check is a process gate, not an adversarial security authority. Candidate workflow configuration and other candidate-authored Actions workflows share App `15368` and can shadow names; the protected-main collector checkout does not eliminate that existing limitation. A stronger future authority could be deployed in an independently controlled App, as a separately reviewed owner operation. This change does not claim that guarantee or modify the dedicated gate.

Managed integrations cannot read or write the full administrative protection endpoint (HTTP 403). The ordinary branch endpoint reveals context/App bindings but not every protection invariant. No administrative mutation is needed or attempted. Keep agents out of the owner's separate gate repository and never expose its key.

The existing read-only protection verifier's `--require-review-convergence` option checks the three-context profile. Its default two-context profile remains historical and is not evidence of the live configuration. If the eligible native job cannot satisfy the normal merge path, retain the failed result and report the actual blocker; never manufacture a green result or remove a required check.
