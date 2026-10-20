# FAR PR Review Convergence Policy (v1.0)

Applies to all future pull requests targeting main, including bot-generated PRs. The same review rigor applies to changed trust boundaries without broadening the PR's feature scope.

## Requirements and raw inputs

Before requesting substantive review, pin the exact PR head, protected-main SHA, merge base, and complete diff. Inspect actual code, requirements, invariants, trust boundaries, original review submissions and threads, all relevant changed integration points, and full hosted logs. Prior status summaries and green checks are not independent proof.

Each PR records a finding ledger in its description or a linked immutable artifact. For each distinct root cause, retain:

- Stable root-cause ID and the violated invariant.
- Source review/thread/comment IDs, reviewed SHA and affected lines.
- Smallest reproducer/counterexample or an explicit inability to verify.
- Disposition: open, accepted, fixed, disproven, duplicate, stale, out-of-scope, or external blocker.
- Evidence for every disposition, including why duplicates share a proven mechanism.
- Fix commit, regression test and before/after defect-detection evidence where possible.
- Newer changes that invalidate prior verification or review.

A comment is not itself a defect. Equally, a passing test or dismissed thread does not refute a real defect. Reject unsupported findings with testable evidence; do not silently suppress findings to make a gate pass. Similar words are insufficient to establish a shared root cause.

## Stopping repeated reviews

- Resolve known substantive root causes and test their original counterexamples first; don't patch review comments as isolated symptoms.
- Execute whole-PR and relevant integration validation on the stabilized exact head, including adversarial and mutation checks where applicable.
- Request an independent substantive review once the candidate is stable. Request a subsequent review only after a material change invalidates the prior review, or new evidence justifies reassessment.
- Never request reviews repeatedly on an unchanged head simply to obtain a different answer.
- If the reviewer repeats a disproven finding, point to its root-cause ledger entry and counterexample. If it identifies a new reproducible defect, reopen the affected invariant without regard to how many reviews have already occurred.
- Investigate architecture, inconsistent specifications and inadequate test oracles when review cycles fail to converge.
- Stop when there are no unresolved reproducible actionable findings, critical obligations have an adequate verification argument, independent substantive review covers final head, and all required protected gates are green. This is a bounded process condition, not a guarantee that future defects cannot exist.

## Automation and limits

The review-evidence collector checks out protected `main`, never PR source. The required native job is named **pr-review-convergence-observation** and runs only on `pull_request_target` for main-targeting PRs. Its token has contents/pull-requests/issues read permissions only. It binds the event head to the current PR head, runs the collector in enforce mode, and checks the head again before completing. No dependency can turn a failed prerequisite into a skipped required job.

GitHub excludes checks produced by scheduled/manual workflow jobs from required PR-check evaluation. A successful Checks API publication made with a workflow token does not cure that event restriction. The scheduled/manual trusted-main publisher therefore uses the distinct **pr-review-convergence-scheduled-observation** name as advisory evidence only. It retains checks-write solely on trusted-main schedule/manual events; candidate-driven jobs remain read-only. See the [observed failure and bootstrap record](../audits/pr-review-convergence-event-eligibility-2026-10-20.md).

Review and comment events preserve read-only evidence artifacts. After a review completes or a thread changes without a new eligible PR event, rerun the current `pull_request_target` required job, or trigger a legitimate PR metadata edit. A scheduled advisory pass cannot replace the required native job. The workflow does not request reviews, push source commits or merge. Native required job completion and advisory check publication are process observations, not proofs of software correctness.
For non-draft PRs its metadata check passes only with at least one of (a) a nonauthor human APPROVED review recorded on the exact head or (b) a completed exact-head Codex review summary authenticated as originating from the ChatGPT Codex Connector GitHub App and explicitly reporting no unresolved findings; in either case there must be zero active CHANGES_REQUESTED reviews and zero unresolved review threads (including outdated ones). Codex completion is **automated review metadata**, not equivalent to human approval or independent proof of substantive correctness. A current authenticated Codex review explicitly reporting unresolved findings blocks metadata convergence even when a human approval exists; one reviewer cannot erase another reviewer's known unresolved defects. It recognizes identical normalized comment text only as a duplicate *candidate*, never a verified common root cause. Missing/incomplete API evidence fails closed. Drafts remain outside enforcement until ready.

An APPROVED flag is not a proof that the review was substantive. A newer authenticated Codex state of `running` never clears earlier unresolved findings; a later completed clean review may supersede them. Ambiguous duplicate machine-state markers fail closed. The artifact retains exact source review/comment identifiers, timestamps and thread-state inventory for reconstruction. The check cannot verify correctness, independent counterexamples, completed root-cause ledgers, other CI results, or merge authority. The exact-head assurance and owner-signed protected-repin gate remain separate.

## Required branch protection and rollout

The live branch endpoint observed on 2026-10-20 requires three contexts: merge-authority from GitHub Actions 15368, protected-repin-gate from the dedicated App 5073230, and pr-review-convergence-observation from GitHub Actions 15368. The earlier two-context/default-verifier profile is historical. A third context published only through ineligible schedule/manual events produced green visible checks but still blocked the normal merge API.

Deploying the corrected trusted-main workflow is a bootstrap dependency: its native job is unavailable until the change reaches protected main, while the broken required context blocks that merge. Only the owner can perform the documented temporary rollback to the previous two-context contract, preserving strictness, administrator enforcement, the dedicated App binding and every other setting; merge the independently reviewed fix through those retained gates; then restore the third context and verify actual eligible-event negative and positive behavior. See [cutover and recovery](review-convergence-protection-cutover.md). Do not alter the branch rule through retired admin tokens, manufacture a check or bypass the retained gates. No rollout is complete until the actual normal merge path succeeds with the native required job.
The Codex installation's own automatic review-trigger settings are external to this policy. This repository automation never requests Codex to review identical code; controlling Codex's own automatic trigger behavior may require adjusting that integration's settings.

## Final release record

Record final PR/main/merge SHAs, live review findings, resolved/disproven ledger dispositions, root-cause regressions, mutation results, final exact-head review outcome, hosted checks, protected App decision, and the merge result. If an external review or authorized protection change remains unavailable, stop with a named external blocker instead of forging a green signal or bypassing the gate. Keep research and empirical claims within demonstrated boundaries.
