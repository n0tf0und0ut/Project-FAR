# Project FAR — Current-Head PR Convergence Audit

Snapshot finalized (UTC): 2026-11-07T14:02:12.843Z

Repository: https://github.com/n0tf0und0ut/Project-FAR

Machine-readable source: https://github.com/n0tf0und0ut/Project-FAR/blob/audit/current-head-convergence-20261107/docs/audits/pr-current-head-convergence-2026-11-07.json

Authority: current root AGENTS.md (blob ccd372ade932266b03eea0615a40bea4a8c34262), docs/governance/research-execution-charter.md, docs/governance/pr-review-convergence.md, docs/CANONICAL_MAP.md.

## Scope and verdict

All 20 open PRs were enumerated and re-fetched at their live GitHub heads. All 20 recorded head/base/draft/state tuples passed final revalidation; a subsequent open-PR query returned the same 20 numbers. The protected-main base reported for 19 PRs is c7456b469f9dfe88b92d0fc7a211e5c9ed64de61. The permanent living-repository inbox #490 reports another base.

ZERO PRs are VERIFIED_MERGE_READY. The connected GitHub interface exposed pull-request workflow runs and named jobs but did not expose full live branch-protection requirements or direct latest Check Runs for the dedicated signed protected-repin App. Governing required contexts are merge-authority, protected-repin-gate, and pr-review-convergence-observation. The first two remain independently UNVERIFIED in the manifest. Neither an automated Codex completion nor a successful native review job demonstrates substantive correctness or authorization.

## Live inventory

| PR | Live head (prefix) | Description candidate | Codex exact-head status | Open threads | Native review job | Classification |
| --- | --- | --- | --- | ---: | --- | --- |
| [#623](https://github.com/n0tf0und0ut/Project-FAR/pull/623) | 9dbc11a0c940 | STALE | none | 0 | success | DRAFT |
| [#622](https://github.com/n0tf0und0ut/Project-FAR/pull/622) | 52ef171bcf0a | STALE | completed | 0 | success | PROTECTED GATES UNVERIFIED |
| [#621](https://github.com/n0tf0und0ut/Project-FAR/pull/621) | 4769f0fcea38 | STALE | failed | 1 | failure | OPEN FINDINGS |
| [#620](https://github.com/n0tf0und0ut/Project-FAR/pull/620) | 769ab788275b | STALE | completed | 0 | success | PROTECTED GATES UNVERIFIED |
| [#619](https://github.com/n0tf0und0ut/Project-FAR/pull/619) | d888fc27ab24 | no explicit candidate | completed | 0 | success | PROTECTED GATES UNVERIFIED |
| [#618](https://github.com/n0tf0und0ut/Project-FAR/pull/618) | 354811a6f7d1 | STALE | completed | 0 | success | PROTECTED GATES UNVERIFIED |
| [#617](https://github.com/n0tf0und0ut/Project-FAR/pull/617) | 89f72221ad6d | no explicit candidate | completed | 0 | success | DRAFT |
| [#616](https://github.com/n0tf0und0ut/Project-FAR/pull/616) | a12f711d2f51 | STALE | completed | 0 | success | PROTECTED GATES UNVERIFIED |
| [#615](https://github.com/n0tf0und0ut/Project-FAR/pull/615) | db0c95f6568d | STALE | completed | 0 | success | PROTECTED GATES UNVERIFIED |
| [#614](https://github.com/n0tf0und0ut/Project-FAR/pull/614) | 0d26eca3e2fd | matches live | completed | 0 | success | PROTECTED GATES UNVERIFIED |
| [#612](https://github.com/n0tf0und0ut/Project-FAR/pull/612) | ada9f99c2f12 | STALE | completed | 0 | success | PROTECTED GATES UNVERIFIED |
| [#611](https://github.com/n0tf0und0ut/Project-FAR/pull/611) | e48f6dc29302 | STALE | completed | 0 | success | PROTECTED GATES UNVERIFIED |
| [#608](https://github.com/n0tf0und0ut/Project-FAR/pull/608) | 6f59f8a53971 | matches live | completed | 0 | success | PROTECTED GATES UNVERIFIED |
| [#607](https://github.com/n0tf0und0ut/Project-FAR/pull/607) | df3b55a70780 | STALE | completed | 0 | success | PROTECTED GATES UNVERIFIED |
| [#606](https://github.com/n0tf0und0ut/Project-FAR/pull/606) | cec9386fd6d5 | STALE | completed | 0 | success | PROTECTED GATES UNVERIFIED |
| [#601](https://github.com/n0tf0und0ut/Project-FAR/pull/601) | 71cd19f348a6 | STALE | completed | 0 | success | PROTECTED GATES UNVERIFIED |
| [#600](https://github.com/n0tf0und0ut/Project-FAR/pull/600) | 58ef77dac335 | STALE | completed | 0 | success | PROTECTED GATES UNVERIFIED |
| [#599](https://github.com/n0tf0und0ut/Project-FAR/pull/599) | abf71a30a590 | STALE | completed | 0 | success | PROTECTED GATES UNVERIFIED |
| [#597](https://github.com/n0tf0und0ut/Project-FAR/pull/597) | ababafde8888 | STALE | failed | 3 | failure | OPEN FINDINGS |
| [#490](https://github.com/n0tf0und0ut/Project-FAR/pull/490) | c2178063902e | no explicit candidate | completed | 0 | action_required | PERMANENT DO NOT MERGE |

## Directly observed substantive blockers

- PR #597: three unresolved threads at current head ababafde8888b897cdf5312c0fd40385b974a6b3; quantified-pronoun negation, >450 KB snapshot resume with individually valid captures, and cross-investigation occurrence-scoped lineage. Current Codex and native review states are failed. [Finding 1](https://github.com/n0tf0und0ut/Project-FAR/pull/597#discussion_r4495176866), [finding 2](https://github.com/n0tf0und0ut/Project-FAR/pull/597#discussion_r4495176875), [finding 3](https://github.com/n0tf0und0ut/Project-FAR/pull/597#discussion_r4495176881). The historical evidence-ledger link resolves but its blob differs from current head; current ledger records corrective implementation with verification and independent review pending.
- PR #621: one unresolved review thread about the interpreter-dependent JSON nesting-limit regression, current Codex and native review states failed. [Finding](https://github.com/n0tf0und0ut/Project-FAR/pull/621#discussion_r4495142869). Its #616 combined integration has not been verified.
- PR #490: explicitly designated permanent noncanonical living research inbox, DO NOT MERGE OR CLOSE; draft, reported nonmergeable, native review workflow action_required. Changed-file listing returned 3,000 filenames versus 3,718 changed files reported by GitHub, so related overlap is incomplete.
- PRs #617 and #623: draft, irrespective of passing observed native review jobs.
- PR #614: dependent on PR #608. Verified Git comparison: #614 is 24 commits ahead of #608, zero behind, with #608's live head as merge base; all 20 #608 changed paths also occur in #614. Integrate and govern predecessor first.
- All PRs: the protected App repin status, complete live required check-run status, and owner merge authorization remain unverified or absent. This audit authorized no merge, auto-merge, or protected-main modification.

## Mechanical evidence reconciliation

- Fifteen descriptions state old candidate SHAs: #623, #622, #621, #620, #618, #616, #615, #612, #611, #607, #606, #601, #600, #599, #597. Every 40-character SHA found in each PR description is captured with context and a role; live head SHA is controlling.
- 35 PR-body evidence URLs are captured and classified. Fourteen referenced source blobs resolve byte-identically at the cited historical ref and live head. One (#597 review ledger) differs. Workflow links are classified as current-head observations only if their run IDs appear in the retrieved current-head workflow list; otherwise their historical nature is explicit.
- The latest native review workflow was resolved to named jobs for each eligible PR. Latest native job fails for #597 and #621; #490's latest workflow is action_required with no qualifying job; other observed jobs report success. This is process evidence, not proof of other protected checks.
- The manifest retains review submissions, the full bodies/IDs of four unresolved threads, all resolved-thread identifiers, current bot state with exact SHA comparison, exact workflow run/job IDs, status observations, explicit and conditional dependency references, full changed-path inventories except #490, and cross-PR overlap paths.
- A source path overlap is recorded only as possible integration conflict, not a hard dependency. The #608 → #614 ancestry and governing PR-description requirement are independently verified. Shared paths #621/#616 remain an integration test obligation.

## Reproduction and validity

All 20 live PR head/base/state/draft tuples were re-fetched; live open-PR count and identity were rechecked; snapshot validation required 20 rows, exactly four unresolved threads, and failing native review jobs #621 and #597. Full raw observation and mismatch/unknown classifications are in the linked JSON manifest.

This is a point-in-time Research-status audit. Any changes to PR heads, target bases, thread/review state, required checks, signatures or protection rules invalidate affected readiness classifications. No PR was merged, auto-merged, closed, retargeted, or otherwise modified by this work.
