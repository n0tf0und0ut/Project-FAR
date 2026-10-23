# Review-convergence branch-protection deployment and verification

Status: **three contexts observed live; eligible-event and v1.1 receipt corrections awaiting protected deployment**. Green advisory publications do not establish operational enforcement.

## Observed blocker

On 2026-10-20, `branches/main` exposed these source bindings:

| Required context | App ID |
|---|---|
| `merge-authority` | GitHub Actions `15368` |
| `protected-repin-gate` | Dedicated FAR gate `5073230` |
| `pr-review-convergence-observation` | GitHub Actions `15368` |

PR #588 at `42b51215418448d10f50a1153cb302da4bcfcb29` had all three visible checks successful, a clean exact-head Codex review, and zero unresolved threads. Its normal merge request failed with HTTP 405 because the review context was expected. The [incident record](../audits/pr-review-convergence-event-eligibility-2026-10-20.md) preserves exact check IDs and the event-eligibility cause.

## Deploy through the existing protected path

The native required job lives in `.github/workflows/required-pr-review-convergence.yml`, whose events are main-targeting `pull_request` and `pull_request_review` submission/edit/dismissal. This eligible event can load the reviewed candidate workflow before it reaches main. It permits ordinary protected deployment without removing a requirement or changing settings. The token has read permissions only and no persistent secret is used. Normal collection uses protected `main`; the following explicitly authorized v1.1 exception is necessary because the old main collector cannot evaluate the new receipt policy.

### One-base, one-PR immutable collector deployment

Only when the checked-out protected-main commit is exactly `e4d936ca0ba9770be6f72e0435220987882f4146`, repository is `n0tf0und0ut/Project-FAR`, and PR is #578, the native job downloads the single collector file from a literal full commit pin and verifies its literal SHA-256 before execution. The source commit is an ancestor of the final integration candidate; independent review must cover that collector and the complete final workflow. No mutable PR ref, candidate checkout, arbitrary URL, write token, persistent key, manufactured review state or fabricated check publication is used. Failed download, digest mismatch, API ambiguity or missing review evidence fails the job.

Pinned collector commit: `a26d0aec9d1f82fb661c72cf06a0a3a72cc74b71`.
File: `tools/pr_review_convergence.py`.
SHA-256: `21fdbd425dcf9dbe00ee7c2798d25a92363d9b2ebe89f25e4dafa1cfb3aa9863`.

This is a deliberate, limited collector-source trust amendment authorized by the user's instruction to implement the policy repair. The pinned file is reviewed candidate code, not already protected-main code. It does not acquire more authority by being hashed. Required exact-head review, full hosted assurance, merge-authority and the owner-controlled gate remain mandatory. Once main moves from that exact base, the exception is inactive and the collector again runs from protected main; other PRs at the old base fail closed rather than inherit this exception. Remove the dormant loader in a separately reviewed cleanup after verified deployment. The final workflow and regression assertions record the exact pin and digest; do not edit either without new review and assurance.

1. Freeze the correction head, protected-main base and complete diff. Run the regression tests, workflow validator, full hosted assurance and dedicated gate App. Obtain a substantive independent review covering the exact final head.
2. Observe that the native `pr-review-convergence-observation` job fails while exact-head review evidence is incomplete. Verify the source App, event, associated head and collector artifact; no skipped job counts as enforcement.
3. After the independent review is clean and all threads are resolved, rerun the latest eligible native job on that unchanged head. Require the event/current-head comparison, protected-main checkout, policy-v1.1 collector source/digest verification where applicable, enforce-mode collector and post-check head comparison to succeed. Preserve both raw summary and receipt evidence; null flags must remain null.
4. Require all three original context/App bindings and all other substantive checks. Use the normal expected-head merge API/UI for the correction. Record the final merge/main SHAs and verify that the original protection settings remain intact.
5. Refresh waiting PRs onto the resulting main without rewriting history, obtain exact-head review and assurance, and require their native eligible job. Review submissions, edits and dismissals automatically execute the required collector. For comment-only machine-state or thread changes, inspect fresh API evidence and rerun the current eligible job before merge; no atomic merge-time freshness guarantee is claimed.
6. Merge only through the ordinary protected path and verify final PR/main state. Do not label deployment complete based on a YAML test, scheduled advisory pass or metadata edit alone.

## Skipped-success boundary

The required job has no job-level condition, dependency or matrix. Its dedicated workflow has no comment/schedule/manual event; both eligible PR and review event families execute the same job unconditionally. Independent review discussion 4330779437 showed that co-locating it with `pull_request_review` could emit an eligible skipped success without enforcing the collector. Discussion 4330890559 requires unconditionally enforcing eligible review events to invalidate changed approval/submitted-findings state. Regression mutations reject an event condition that skips review enforcement, ineligible comment/schedule events, write permissions, candidate checkout, missing head binding and dependency-skipped success. Discussion 4330890566 adds the required workflow to both contract-validator path lists, with a regression binding both. Scheduled/manual publications use the distinct advisory context `pr-review-convergence-scheduled-observation`.

## Trust and readback limits

The native GitHub Actions check is a process gate, not an adversarial security authority. Candidate workflow configuration and other candidate-authored Actions workflows share App `15368` and can shadow names; the protected-main collector checkout does not eliminate that existing limitation. A stronger future authority could be deployed in an independently controlled App, as a separately reviewed owner operation. This change does not claim that guarantee or modify the dedicated gate.

Managed integrations cannot read or write the full administrative protection endpoint (HTTP 403). The ordinary branch endpoint reveals context/App bindings but not every protection invariant. No administrative mutation is needed or attempted. Keep agents out of the owner's separate gate repository and never expose its key.

The existing read-only protection verifier's `--require-review-convergence` option checks the three-context profile. Its default two-context profile remains historical and is not evidence of the live configuration. If the eligible native job cannot satisfy the normal merge path, retain the failed result and report the actual blocker; never manufacture a green result or remove a required check.

## Proposed operator repair for legacy publication names (2026-10-23)

**Status: prepared for independent exact-source review; not executed.** This
operation lives on `repair/legacy-review-publications-20261023`, reviewed through
a separate PR targeting `feature/bounded-auditable-investigations-v01`. Do not
merge that operation PR into #578: doing so would move the already assured
integration head. Close it only after the metadata operation and protected
integration have been verified.

The normal expected-head merge of #578 at
`5cd1ff7a2d1847e2f6f91c1a99550b66efd96484` was rejected with HTTP 405,
`Required status check "pr-review-convergence-observation" is failing`, despite
eligible native job **120698569965** (run **40036918391**) succeeding. Exact-head
assurance **120688987537**, merge-authority **120689368917** and dedicated gate
**120689624927** also passed. Main remained
`e4d936ca0ba9770be6f72e0435220987882f4146`.

The old-main scheduled publisher emitted a distinct failing custom API check
**120690505476**, under the required name. Run **40034461117**, job
**120690436244**, contains its complete publication receipt and the old
collector's incomplete-state failure. Its name collision continues to block the
normal merge path. A later eligible native success does not retire that separate
legacy publication. Later scheduled instances must be discovered and proven too.

The proposed operation changes **only the name** of proven legacy scheduled
publications to `pr-review-convergence-scheduled-observation`. It preserves their
original success/failure conclusion, status, commit, timestamps, output, source
App and details URL. It neither creates a successful result nor changes branch
protection, native requirements, commits or merge authority. The [GitHub update
API](https://docs.github.com/en/rest/checks/runs#update-a-check-run) accepts a
name-only update. Whether the deployed token can perform this exact provider
operation remains unproven until the real operation/readback succeeds.

### Activation and source boundary

The first push runs a **read-only activation job**, which exits before loading
helpers. Its dependent writer is skipped and receives no token. After independent
substantive review and the native read-only contract test cover the operation's
exact immutable head, an authorized operator explicitly retries that activation
job. GitHub's [job retry API](https://docs.github.com/en/rest/actions/workflow-runs#re-run-a-job-from-a-workflow-run)
also retries dependent jobs. A direct manual dispatch on the same repair branch
with `pr_number=578` is an alternative. PR/review/comment events remain read-only.

The activation retry constructs a read-only plan. The dependent writer then
independently repeats every preflight before its name-only PATCH. Both jobs have
no checkout and load only these reviewed, immutable, digest-verified files:

| File | Source commit | SHA-256 |
|---|---|---|
| `tools/retire_legacy_review_publications.py` | `77662c7a4bea57c6f4a5f41df5a3f19a99474380` | `fe6c43cf8829d34c921e53d4b650265c8465799d0d6714c9b962f36640e13b9f` |
| `tools/pr_review_convergence.py` | `a26d0aec9d1f82fb661c72cf06a0a3a72cc74b71` | `21fdbd425dcf9dbe00ee7c2798d25a92363d9b2ebe89f25e4dafa1cfb3aa9863` |

This is an explicitly reviewed operator metadata-write exception for the user's
authorized integration repair. It deliberately trusts reviewed operation code
outside protected main. It does not claim an adversarial authority independent
of GitHub Actions, nor does hashing make candidate code protected. Only the
dependent operator job receives `checks: write`; it has contents/actions/issues/
pull-requests read permissions and no persistent secret, contents-write,
administration or owner-gate access. All original source/App bindings remain.

### Mandatory preflight and readback

The helper refuses a changed repository, target PR head, old-main SHA, protection
binding, draft or source-review branch. It requires exact-source review of the
operation itself, its exact-head native `convergence-contract` CI result, and
fresh v1.1 review closure of #578. The target's native review, exact-head
assurance, merge-authority and dedicated-App results must pass on the exact head;
custom API publications cannot stand in for eligible native jobs. The native
run/job IDs, event family, workflow path, App and head are checked through APIs.

Every candidate name change needs an exact matching JSON publication receipt in
a completed job of the old-main **scheduled** publisher. Native check URLs,
foreign Apps, other heads, unproven records and malformed/quoted receipts do not
qualify. Signed log-download URLs receive no API bearer token. All proofs must
exist before the first write. Each PATCH contains only the new advisory name;
readback must preserve the original result and evidence. The operation report
and both review records are uploaded even though they do not establish software
correctness or authorize a merge by themselves.

After a successful name repair, inspect current review evidence and the live
required bindings, refresh the eligible native job when needed, and use the
normal expected-head merge for #578. A new scheduled collision or head movement
must still block that merge. Record the actual main commit and component PR
dispositions only after verification. Once main moves from the exact old base,
the operation refuses to run. Keep #490 open and unmerged throughout.
