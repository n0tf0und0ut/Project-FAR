# Review-convergence event eligibility incident

Status: Research operational incident record. No theory, evidence or benchmark promotion.

## Evidence

- Protected main: `e4d936ca0ba9770be6f72e0435220987882f4146`.
- PR #588 head: `42b51215418448d10f50a1153cb302da4bcfcb29`; clean exact-head Codex review, no unresolved threads.
- Required source bindings from `branches/main`: `merge-authority` / `15368`, `protected-repin-gate` / `5073230`, `pr-review-convergence-observation` / `15368`.
- Successful exact-head check IDs: merge authority `118892628711`, dedicated gate `118893603687`, review observation `118900514585`, exact-head assurance `118892414588`.
- The review observation belongs to completed successful suite `107043036427`, is associated with PR #588, and reports the same head and App. The virtual merge commit had no checks.
- The normal expected-head merge API returned HTTP 405: `Required status check "pr-review-convergence-observation" is expected.` No merge or protection bypass was performed.

## Cause and correction

[GitHub's required-check troubleshooting documentation](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks?plain=1) excludes scheduled/manual workflow-job checks from required PR evaluation. The deployed publisher used those events; its green workflow-token publication therefore did not satisfy the rule. This explains the observed rejection; live positive/negative verification of the corrected deployment remains required.

The correction adds a native required job on the eligible `pull_request` event, retaining only read permissions and protected-main code. It freezes the event/current head, enforces the same metadata collector, checks head stability before success, and preserves evidence. Schedule/manual output uses a distinct advisory context. Regression mutations reject ineligible events, write permissions, candidate checkout, omitted head binding and dependency-skipped success.

The initially proposed trusted `pull_request_target` definition could not execute before reaching main. The final design uses an eligible read-only `pull_request` workflow and protected-main collector checkout, so it can deploy through all three existing protected requirements. No owner rollback or administrative mutation is necessary. The [deployment procedure](../governance/review-convergence-protection-cutover.md) requires an actual failed native check while review is incomplete, a successful rerun after exact-head convergence, and a successful normal protected merge. Candidate-controlled workflow configuration remains an explicit Actions-App process-gate limitation.

## Unproved claims

Local/YAML tests cannot prove GitHub's future deployed behavior. Hosted CI on a candidate cannot deploy protected-main workflow code. A native green metadata job does not prove correctness or independent scientific validity. Bootstrap and actual negative/positive merge-path evidence must be recorded before declaring this incident resolved.

The required-name job is isolated in `.github/workflows/required-pr-review-convergence.yml`, whose eligible events are `pull_request` and `pull_request_review`. It has no job-level condition. Every eligible event runs the required job without a condition. Discussion 4330779437 identified eligible skipped success; 4330890559 identified missing automatic review-state re-evaluation. Submission/edit/dismissal now re-executes enforcement. Discussion 4330890566 enrolled the new workflow in both PR/push contract filters. Three new assertions failed on abc0b250 and all 35 convergence tests pass after correction. Comment-only state/thread changes retain the existing non-atomic freshness limitation and require fresh inspection/re-evaluation before merge.
