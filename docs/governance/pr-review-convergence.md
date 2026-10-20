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

The read-only PR Review Convergence workflow runs from protected-main code after PR and review events, never checks out PR source into a privileged job and never publishes comments, review requests, or commits. It paginates review and inline-comment APIs, examines GraphQL review thread status, verifies the PR head both before and after evidence acquisition, and writes an inspectable JSON artifact.

For non-draft PRs its metadata check passes only with at least one nonauthor human APPROVED review recorded on the exact head, zero active CHANGES_REQUESTED reviews, and zero unresolved review threads (including outdated ones). It recognizes identical normalized comment text only as a duplicate *candidate*, never a verified common root cause. Missing/incomplete API evidence fails closed. Drafts remain outside enforcement until ready.

An APPROVED flag is not a proof that the review was substantive. The check cannot verify correctness, independent counterexamples, completed root-cause ledgers, other CI results, or merge authority. The exact-head assurance and owner-signed protected-repin gate remain separate.

## Required branch protection and rollout

The repository's canonical protection currently requires only merge-authority and protected-repin-gate, binds them to specific Apps, and has zero required approving reviews. This newly introduced workflow is therefore NOT automatically a protected required check. Its visible failure does not guarantee that a protected merge is blocked.

Only the owner can authorize a properly reviewed, signed repin of canonical branch protection and corresponding verifier expectations to include review convergence; do not execute retired admin-token protection tools, weaken the protected-repin App, or silently change the existing two-check contract. Until the owner-approved repin, protection-level enforcement is incomplete.

The Codex installation's own automatic review-trigger settings are external to this policy. This repository automation never requests Codex to review identical code; controlling Codex's own automatic trigger behavior may require adjusting that integration's settings.

## Final release record

Record final PR/main/merge SHAs, live review findings, resolved/disproven ledger dispositions, root-cause regressions, mutation results, final exact-head review outcome, hosted checks, protected App decision, and the merge result. If an external review or authorized protection change remains unavailable, stop with a named external blocker instead of forging a green signal or bypassing the gate. Keep research and empirical claims within demonstrated boundaries.
