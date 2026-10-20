# Review-convergence branch-protection cutover and recovery

Status: **three contexts observed live; eligible-event correction awaiting deployment**. Repository files and green advisory publications do not establish operational enforcement.

## Observed blocker

On 2026-10-20, `branches/main` exposed these source bindings:

| Required context | App ID |
|---|---|
| `merge-authority` | GitHub Actions `15368` |
| `protected-repin-gate` | Dedicated FAR gate `5073230` |
| `pr-review-convergence-observation` | GitHub Actions `15368` |

PR #588 at `42b51215418448d10f50a1153cb302da4bcfcb29` had all three visible checks successful, a clean exact-head Codex review, and zero unresolved threads. Its normal merge request still failed with HTTP 405 because the review-convergence context was expected. The [incident record](../audits/pr-review-convergence-event-eligibility-2026-10-20.md) preserves exact check IDs and the event-eligibility cause.

The corrected workflow supplies the required context through a native, read-only `pull_request_target` job that executes protected-main collector code. Scheduled/manual publications have a different advisory name and cannot authorize a merge. A candidate cannot deploy this trusted-main job by changing only its own workflow file.

## Owner bootstrap (only after the fix is reviewed)

1. Verify the workflow correction, its regression tests, independent review, hosted validations, `merge-authority`, and the dedicated `protected-repin-gate`. Keep their exact head SHA and App identities.
2. As the repository owner, open `n0tf0und0ut/Project-FAR → Settings → Branches → main protection rule → Edit`.
3. Temporarily remove only `pr-review-convergence-observation`. Keep `merge-authority` bound to App `15368`, `protected-repin-gate` bound to App `5073230`, strict/up-to-date checks, administrator enforcement, conversation resolution, stale review dismissal, and every other setting. This restores the previously documented two-context contract; it does not authorize bypassing either retained gate.
4. Merge only the independently reviewed correction after the two retained gates and all substantive review/validation obligations pass.
5. Restore `pr-review-convergence-observation` as required with **GitHub Actions App `15368`**, never “Any source.” Keep both retained checks and all unrelated settings unchanged.
6. On each waiting PR, trigger an eligible `pull_request_target` event through a legitimate metadata edit, or rerun its latest eligible required job. Require the exact current head, event-head guard, trusted-main checkout, and native job conclusion. A manually dispatched or scheduled advisory check is insufficient.
7. Verify a negative review state fails the native required job and blocks normal merge. Then complete the substantive review on the same head, rerun that eligible job, require success, and verify the normal merge API/UI permits merging. Record the final merge and main SHAs. Never label rollout complete based only on an advisory check or documentation edit.

## Readback and limits

The connected GitHub integrations cannot read or write the full administrative protection endpoint (HTTP 403). The ordinary branch endpoint reveals context/App bindings but not every protection invariant. The owner must retain the complete settings above and use the separate owner's gate repository protection audit for authenticated full readback. Keep agents out of that repository and never expose its App key.

The native GitHub Actions check is a process gate, not an adversarial security authority. Candidate-authored workflows under the same Actions App can shadow names; a stronger future design would move this decision into the independently controlled gate App. That is a separately reviewed deployment, not a reason to weaken the existing dedicated gate.

After rollout, the existing read-only verifier's `--require-review-convergence` option checks the three-context profile. Its default two-context profile remains historical and must not be cited as evidence of the live three-context configuration. If native publication fails during bootstrap, keep the reviewed fix and recovery state explicit; do not declare success or post counterfeit required results.
