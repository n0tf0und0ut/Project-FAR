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

The review-evidence collector runs only protected-main code (never PR source) using a read-only GitHub API token. A separate, narrowly scoped workflow step has `checks: write` to publish the resulting **pr-review-convergence-observation** check directly onto the exact PR head SHA. Supported PR/review/comment events trigger updates, and a periodic scheduled reconciliation polls all open main PRs because review-thread resolution/reopening is not a native Actions trigger. Issue-comment-origin jobs alone are **not** reliably PR-associated required job checks; the explicit head-bound Checks API publication is the check consumers must inspect. Because GitHub scheduled workflows are best-effort, this is not an atomic merge-time attestation of thread state. Every run records an inspectable JSON artifact. The workflow does not comment, request reviews, push commits, merge, or execute untrusted code; its sole GitHub write is the scoped head-bound observation check.

For non-draft PRs its metadata check passes only with at least one of (a) a nonauthor human APPROVED review recorded on the exact head or (b) a completed exact-head Codex review summary authenticated as originating from the ChatGPT Codex Connector GitHub App and explicitly reporting no unresolved findings; in either case there must be zero active CHANGES_REQUESTED reviews and zero unresolved review threads (including outdated ones). Codex completion is **automated review metadata**, not equivalent to human approval or independent proof of substantive correctness. A current authenticated Codex review explicitly reporting unresolved findings blocks metadata convergence even when a human approval exists; one reviewer cannot erase another reviewer's known unresolved defects. It recognizes identical normalized comment text only as a duplicate *candidate*, never a verified common root cause. Missing/incomplete API evidence fails closed. Drafts remain outside enforcement until ready.

An APPROVED flag is not a proof that the review was substantive. A newer authenticated Codex state of `running` never clears earlier unresolved findings; a later completed clean review may supersede them. Ambiguous duplicate machine-state markers fail closed. The artifact retains exact source review/comment identifiers, timestamps and thread-state inventory for reconstruction. The check cannot verify correctness, independent counterexamples, completed root-cause ledgers, other CI results, or merge authority. The exact-head assurance and owner-signed protected-repin gate remain separate.

## Required branch protection and rollout

The repository's canonical protection currently requires only merge-authority and protected-repin-gate, binds them to specific Apps, and has zero required approving reviews. This newly introduced workflow is therefore NOT automatically a protected required check. Even when the head-bound observation check is red, the two existing protected contexts can permit a merge. Furthermore, interval polling does not guarantee zero latency between a thread-state change and a new observation; a future owner-signed merge requirement must explicitly address freshness before relying on it for authorization.

Only the owner can authorize a properly reviewed, signed repin of canonical branch protection and corresponding verifier expectations to include review convergence; do not execute retired admin-token protection tools, weaken the protected-repin App, or silently change the existing two-check contract. Until the owner-approved repin, protection-level enforcement is incomplete.

The Codex installation's own automatic review-trigger settings are external to this policy. This repository automation never requests Codex to review identical code; controlling Codex's own automatic trigger behavior may require adjusting that integration's settings.

## Final release record

Record final PR/main/merge SHAs, live review findings, resolved/disproven ledger dispositions, root-cause regressions, mutation results, final exact-head review outcome, hosted checks, protected App decision, and the merge result. If an external review or authorized protection change remains unavailable, stop with a named external blocker instead of forging a green signal or bypassing the gate. Keep research and empirical claims within demonstrated boundaries.
