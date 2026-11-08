# Project FAR — Open PR exact-head convergence manifest

**Observed:** 2026-11-07 UTC; sequential GitHub connector reads, not an atomic transaction.
**Protected main SHA:** `eff47bc4fc9e272e87d71ecfc8d559cd1176753e`.
**Inventory:** 20 open PRs, 19 merge candidates and one perpetual draft inbox (#490).

## Required gates

| Context | Required source App ID |
|---|---|
| `merge-authority` | `15368` |
| `protected-repin-gate` | `5073230` |
| `pr-review-convergence-observation` | `15368` |

Notation: ✓ = completed success; ✕ = completed failure; … = in progress; — = no check observed. A green machine gate is not an independent code review or merge authorization.

## All currently open PRs

| PR | Exact live head | Declared head | M / P / R | Unresolved threads | Disposition |
|---|---|---|---|---:|---|
| [#625](https://github.com/n0tf0und0ut/Project-FAR/pull/625) | [`fbb7a5be0bc1`](https://github.com/n0tf0und0ut/Project-FAR/commit/fbb7a5be0bc1185d868a09cb51bfaddcb1b24cd7) | match | … / ✓ / ✓ | 0 | BLOCKED_NO_MERGE |
| [#597](https://github.com/n0tf0und0ut/Project-FAR/pull/597) | [`94603603fd6c`](https://github.com/n0tf0und0ut/Project-FAR/commit/94603603fd6c863cf3895496af64cf2f003db480) | stale `ababafde88` | … / ✓ / ✕ | 0 | BLOCKED_NO_MERGE |
| [#490](https://github.com/n0tf0und0ut/Project-FAR/pull/490) | [`495cc99f9c8a`](https://github.com/n0tf0und0ut/Project-FAR/commit/495cc99f9c8a189968a9835a591550215726fa0d) | absent | — / ✓ / — | 0 | KEEP_OPEN_DRAFT_NEVER_MERGE |
| [#617](https://github.com/n0tf0und0ut/Project-FAR/pull/617) | [`4651fa065b18`](https://github.com/n0tf0und0ut/Project-FAR/commit/4651fa065b1847901871d3903b9ebcdc57e787aa) | stale `89f72221ad` | ✕ / ✕ / ✓ | 0 | BLOCKED_NO_MERGE |
| [#621](https://github.com/n0tf0und0ut/Project-FAR/pull/621) | [`03e19ac40424`](https://github.com/n0tf0und0ut/Project-FAR/commit/03e19ac40424636c47e9370d1fb72f85d51246e9) | stale `22af7f59a5` | … / ✓ / ✕ | 0 | BLOCKED_NO_MERGE |
| [#623](https://github.com/n0tf0und0ut/Project-FAR/pull/623) | [`3a62632658a1`](https://github.com/n0tf0und0ut/Project-FAR/commit/3a62632658a12938caac75f5d6921a7b9dadd425) | stale `87cec59af8` | ✓ / ✓ / ✕ | 2 | BLOCKED_NO_MERGE |
| [#601](https://github.com/n0tf0und0ut/Project-FAR/pull/601) | [`eb58ea4dcc5e`](https://github.com/n0tf0und0ut/Project-FAR/commit/eb58ea4dcc5e5d590c55002d17e047d4cf74b907) | stale `a75d6b1fa2` | … / ✓ / ✕ | 0 | BLOCKED_NO_MERGE |
| [#599](https://github.com/n0tf0und0ut/Project-FAR/pull/599) | [`7b5b6febf1f2`](https://github.com/n0tf0und0ut/Project-FAR/commit/7b5b6febf1f2b7725c2b4d2523ebab225c5ab223) | stale `5e521f93f2` | ✓ / ✓ / ✕ | 0 | BLOCKED_NO_MERGE |
| [#606](https://github.com/n0tf0und0ut/Project-FAR/pull/606) | [`130c69035624`](https://github.com/n0tf0und0ut/Project-FAR/commit/130c69035624c133954d96f5b6a5d063e2e82d97) | stale `dd00a19507` | ✓ / ✓ / ✕ | 0 | BLOCKED_NO_MERGE |
| [#600](https://github.com/n0tf0und0ut/Project-FAR/pull/600) | [`a8079e4e6d4b`](https://github.com/n0tf0und0ut/Project-FAR/commit/a8079e4e6d4b3f5caccab969756c910ab3b91d5b) | stale `ee62193370` | ✓ / ✓ / ✕ | 0 | BLOCKED_NO_MERGE |
| [#607](https://github.com/n0tf0und0ut/Project-FAR/pull/607) | [`c934d21ff5e5`](https://github.com/n0tf0und0ut/Project-FAR/commit/c934d21ff5e598403caa27e0c436f4e23737bfaf) | stale `e959c755bf` | ✓ / ✓ / ✕ | 0 | BLOCKED_NO_MERGE |
| [#611](https://github.com/n0tf0und0ut/Project-FAR/pull/611) | [`d217afa409fd`](https://github.com/n0tf0und0ut/Project-FAR/commit/d217afa409fd58798b32d8d2afbf06151b40e6d7) | stale `0e8364466d` | ✓ / ✓ / ✕ | 0 | BLOCKED_NO_MERGE |
| [#608](https://github.com/n0tf0und0ut/Project-FAR/pull/608) | [`054a7e691cb8`](https://github.com/n0tf0und0ut/Project-FAR/commit/054a7e691cb83237eef308b9455855bbc102a67c) | stale `6f59f8a539` | … / ✓ / ✕ | 0 | BLOCKED_NO_MERGE |
| [#614](https://github.com/n0tf0und0ut/Project-FAR/pull/614) | [`d91d86893c1b`](https://github.com/n0tf0und0ut/Project-FAR/commit/d91d86893c1be9a15eae6d63dc178bcfc8471a6f) | stale `0d26eca3e2` | … / ✓ / ✕ | 0 | BLOCKED_NO_MERGE |
| [#619](https://github.com/n0tf0und0ut/Project-FAR/pull/619) | [`1f173c990c69`](https://github.com/n0tf0und0ut/Project-FAR/commit/1f173c990c695ff5bd0244a9cc3015073a06a89f) | absent | ✓ / ✓ / ✕ | 0 | BLOCKED_NO_MERGE |
| [#615](https://github.com/n0tf0und0ut/Project-FAR/pull/615) | [`b360aab81ad1`](https://github.com/n0tf0und0ut/Project-FAR/commit/b360aab81ad14e0289d87f4acd67d84d20ae0116) | stale `87315d1402` | … / ✓ / ✕ | 0 | BLOCKED_NO_MERGE |
| [#618](https://github.com/n0tf0und0ut/Project-FAR/pull/618) | [`9f3bdd0a7dcf`](https://github.com/n0tf0und0ut/Project-FAR/commit/9f3bdd0a7dcf9890e87006cda2812a547c24e42e) | stale `8ab8c9d13d` | ✓ / ✓ / ✕ | 0 | BLOCKED_NO_MERGE |
| [#616](https://github.com/n0tf0und0ut/Project-FAR/pull/616) | [`8261c05a8578`](https://github.com/n0tf0und0ut/Project-FAR/commit/8261c05a85784b40de0e4d0148fd3920670ac25e) | stale `01632e92a9` | ✓ / ✓ / ✕ | 0 | BLOCKED_NO_MERGE |
| [#620](https://github.com/n0tf0und0ut/Project-FAR/pull/620) | [`8f7af32b4d8f`](https://github.com/n0tf0und0ut/Project-FAR/commit/8f7af32b4d8f9c9557cbf2adba18d12568a4a865) | stale `8ca6d68fe2` | ✓ / ✓ / ✕ | 0 | BLOCKED_NO_MERGE |
| [#622](https://github.com/n0tf0und0ut/Project-FAR/pull/622) | [`61d049311618`](https://github.com/n0tf0und0ut/Project-FAR/commit/61d0493116184e48606ac1360746e5c99d5b49da) | stale `0762cfca95` | ✓ / ✓ / ✕ | 0 | BLOCKED_NO_MERGE |

## Findings and root causes

**#623 remains substantively blocked.** The two unresolved, current, non-outdated threads are:

- `PRRT_kwDOTH_vCM607BpC`, `tools/check_governance_register_integrity.py:100`: shared leading conditions incorrectly discarded across coordinated status claims.
- `PRRT_kwDOTH_vCM607BpE`, `tools/check_governance_register_integrity.py:114`: Markdown emphasis breaks condition-cell recognition.

All other PRs returned zero unresolved review threads in the queried GraphQL state. This only describes thread state, not correctness. No nonauthor human `APPROVED` review was observed.

**#617** remains draft and `BLOCKED_GOVERNANCE` by absent owner signatures for the protected repin request. Its merge-authority, App repin and exact-head assurance checks failed. Draft review success is not merge readiness.

**#625** has completed current-head Codex `completed/false/false` review, successful protected-repin and review-convergence gates; merge-authority and exact-head assurance remained in progress at the last check snapshot.

**#490** is the permanent research inbox. Its workflow intentionally keeps it draft and nonmergeable; snapshot/promotion PRs must exclude `.rolling-pr-anchor.json`.

## Dependency and integration ordering

`#608 → #614` is an explicit predecessor requirement: integrate #608 before #614. `#625 → #597` is documented ordering for conflicting README and W4/W6 living digests, not a requirement for #625 to wait for #597. The combined README requires recalculating both living digests and repeating tests and reviews. #617 is a conditional protected-cache-runtime prerequisite when its trusted path prevents other candidates from passing.

Additional overlaps needing integration tests include `#597 ↔ #599` (investigation audit), `#616 ↔ #621` (commercial demo), and shared living-promotion regression and scheduled-research test files across many branches. File-path overlap alone does not prove textual conflict.

## Exact evidence identity

Each row below is a Content API lookup at the **current live candidate SHA**. Historical linked evidence is separately read where available; matching blob SHA proves byte identity for that file only.

| PR | Verified evidence path | Current Git blob | Historical pointer identity |
|---|---|---|---|
| #625 | [`docs/maintenance/beginner-comprehension-check.md`](https://github.com/n0tf0und0ut/Project-FAR/blob/fbb7a5be0bc1185d868a09cb51bfaddcb1b24cd7/docs/maintenance/beginner-comprehension-check.md) | `f77cf4b71c12` | not_compared |
| #597 | [`commercial/far-investigation-audit/REVIEW_LEDGER_597.md`](https://github.com/n0tf0und0ut/Project-FAR/blob/94603603fd6c863cf3895496af64cf2f003db480/commercial/far-investigation-audit/REVIEW_LEDGER_597.md) | `43c8f8b082d0` | changed |
| #490 | [`research/living/inbox/.rolling-pr-anchor.json`](https://github.com/n0tf0und0ut/Project-FAR/blob/495cc99f9c8a189968a9835a591550215726fa0d/research/living/inbox/.rolling-pr-anchor.json) | `42203bd35466` | not_compared |
| #617 | [`docs/audits/signed-cache-python-patch-mismatch-2026-11-03.md`](https://github.com/n0tf0und0ut/Project-FAR/blob/4651fa065b1847901871d3903b9ebcdc57e787aa/docs/audits/signed-cache-python-patch-mismatch-2026-11-03.md) | `066ffc3804bf` | unchanged |
| #621 | [`commercial/far-decision-integrity/PILOT_VALIDATION.md`](https://github.com/n0tf0und0ut/Project-FAR/blob/03e19ac40424636c47e9370d1fb72f85d51246e9/commercial/far-decision-integrity/PILOT_VALIDATION.md) | `686c45d674f0` | not_compared |
| #623 | [`docs/architecture/validator-assurance-hardening.md`](https://github.com/n0tf0und0ut/Project-FAR/blob/3a62632658a12938caac75f5d6921a7b9dadd425/docs/architecture/validator-assurance-hardening.md) | `0f37b534060e` | not_compared |
| #601 | [`docs/research/far-mech-convergence-20261103.md`](https://github.com/n0tf0und0ut/Project-FAR/blob/eb58ea4dcc5e5d590c55002d17e047d4cf74b907/docs/research/far-mech-convergence-20261103.md) | `d128b4f209e6` | unchanged |
| #599 | [`commercial/far-investigation-audit/evaluation/live-001/README.md`](https://github.com/n0tf0und0ut/Project-FAR/blob/7b5b6febf1f2b7725c2b4d2523ebab225c5ab223/commercial/far-investigation-audit/evaluation/live-001/README.md) | `3dbc5808db36` | not_compared |
| #606 | [`research/architecture-routing/finding-ledger.md`](https://github.com/n0tf0und0ut/Project-FAR/blob/130c69035624c133954d96f5b6a5d063e2e82d97/research/architecture-routing/finding-ledger.md) | `af87488c4c30` | unchanged |
| #600 | [`docs/research/orthodox-forecast-factual-experiment-execution-v0.1.md`](https://github.com/n0tf0und0ut/Project-FAR/blob/a8079e4e6d4b3f5caccab969756c910ab3b91d5b/docs/research/orthodox-forecast-factual-experiment-execution-v0.1.md) | `7d5763e4c11e` | unchanged |
| #607 | [`research/workflow-efficacy/LOCAL-QWEN-VALIDATION-V0.2.md`](https://github.com/n0tf0und0ut/Project-FAR/blob/c934d21ff5e598403caa27e0c436f4e23737bfaf/research/workflow-efficacy/LOCAL-QWEN-VALIDATION-V0.2.md) | `defe7c8de9d7` | unchanged |
| #611 | [`research/weight_space_programming/README.md`](https://github.com/n0tf0und0ut/Project-FAR/blob/d217afa409fd58798b32d8d2afbf06151b40e6d7/research/weight_space_programming/README.md) | `487dc9dc0012` | unchanged |
| #608 | [`research/uncertain-routing/finding-ledger.md`](https://github.com/n0tf0und0ut/Project-FAR/blob/054a7e691cb83237eef308b9455855bbc102a67c/research/uncertain-routing/finding-ledger.md) | `061a3ea2fb5c` | unchanged |
| #614 | [`research/investigation-engine/finding-ledger.md`](https://github.com/n0tf0und0ut/Project-FAR/blob/d91d86893c1be9a15eae6d63dc178bcfc8471a6f/research/investigation-engine/finding-ledger.md) | `c32448d272a5` | unchanged |
| #619 | [`research/good-view-jepa/README.md`](https://github.com/n0tf0und0ut/Project-FAR/blob/1f173c990c695ff5bd0244a9cc3015073a06a89f/research/good-view-jepa/README.md) | `0fabeca59966` | not_compared |
| #615 | [`research/model-architecture-search/CONVERGENCE-2026-11-03.md`](https://github.com/n0tf0und0ut/Project-FAR/blob/b360aab81ad14e0289d87f4acd67d84d20ae0116/research/model-architecture-search/CONVERGENCE-2026-11-03.md) | `60df8b191017` | unchanged |
| #618 | [`research/repository-convergence/2026-11-03/README.md`](https://github.com/n0tf0und0ut/Project-FAR/blob/9f3bdd0a7dcf9890e87006cda2812a547c24e42e/research/repository-convergence/2026-11-03/README.md) | `3f0a2e1f8ca9` | unchanged |
| #616 | [`commercial/far-demo/evaluation/semantic-live-smoke-20261103.md`](https://github.com/n0tf0und0ut/Project-FAR/blob/8261c05a85784b40de0e4d0148fd3920670ac25e/commercial/far-demo/evaluation/semantic-live-smoke-20261103.md) | `d28c31a84f8d` | unchanged |
| #620 | [`research/numeric-grounding/RESULTS-LIVE-V0.1.md`](https://github.com/n0tf0und0ut/Project-FAR/blob/8f7af32b4d8f9c9557cbf2adba18d12568a4a865/research/numeric-grounding/RESULTS-LIVE-V0.1.md) | `0a1cc10a540c` | unchanged |
| #622 | [`research/tool-agent-reliability/FAULT-CAMPAIGN-V0.1.md`](https://github.com/n0tf0und0ut/Project-FAR/blob/61d0493116184e48606ac1360746e5c99d5b49da/research/tool-agent-reliability/FAULT-CAMPAIGN-V0.1.md) | `f9ff1227afe6` | not_compared |

For #597, the historical linked finding ledger had a **different** Git blob SHA from the current-head ledger. It must not be cited as an unchanged current-head verdict. Most other historically linked principal evidence files retained identical bytes, but do not certify the changed code.

## Authorization and claim boundaries

No PR was merge-authorized here; no branch-protection bypass, signature substitution, protected-main edit, merge or auto-merge was performed. The legal path is to fix current-head findings, stabilize integration, re-run all source-bound checks, obtain substantive independent current-head review, and apply owner authorization last.

**Scientific boundary:** #620 failed its preregistered primary numeric-release improvement gate (zero incorrect releases in each arm); #616 had a local model output rejected with HTTP 502; #614 retained agent 0/8 vs deterministic/declarative 7/8. These are negative or bounded observations, not improvements to general agent reliability.

## Audit method and limitations

GitHub sources: `GET /repos/n0tf0und0ut/Project-FAR/pulls?state=open&per_page=100`, individual PR metadata, `GET /git/ref/heads/main`, `GET /branches/main`, check-runs on each exact SHA, pull-request review submissions, GraphQL review-thread state, machine summaries from issue comments, changed-file inventories and evidence-file Contents lookups.

The collection was **sequential** and source state may move. Unfinished workflows may settle later. A stable manifest requires re-querying main, PR list and heads both before and after collection, rejecting a changed head or inventory. The accompanying validator detects internal contradictions but does not itself consult GitHub. Source check provenance was observed as App IDs 15368/5073230/15368; the dedicated full protection endpoint returned HTTP 403.

Every attached evidence path was verified at its stated current candidate; the manifest does **not** claim exhaustive verification of all linked job logs, archived ZIP contents, historical run URLs, reviewer output semantics, or direct scientific truth.

## Exhaustive PR-body GitHub URL index

The machine-readable JSON carries every explicit `https://github.com/n0tf0und0ut/Project-FAR/…` URL extracted from the 20 PR descriptions in the collected REST responses. Historical run URLs are catalogued but not re-certified as current-head results.

| PR | Literal URL references | Current-head verified execution refs |
|---|---:|---:|
| #625 | 5 | 1 |
| #597 | 9 | 0 |
| #490 | 0 | 0 |
| #617 | 2 | 0 |
| #621 | 13 | 0 |
| #623 | 14 | 0 |
| #601 | 1 | 0 |
| #599 | 1 | 0 |
| #606 | 1 | 0 |
| #600 | 1 | 0 |
| #607 | 2 | 0 |
| #611 | 1 | 0 |
| #608 | 3 | 0 |
| #614 | 2 | 0 |
| #619 | 5 | 0 |
| #615 | 1 | 0 |
| #618 | 1 | 0 |
| #616 | 1 | 0 |
| #620 | 3 | 0 |
| #622 | 2 | 0 |

No URL-count claim is made for inline PR numbers, comment IDs without URLs, or references stored only inside linked artifacts.

---

# Project FAR — Five-advisor council review of the exact-head convergence manifest

## 1. The Contrarian

The largest defect is not a failing unit test. It is the repository's temptation to treat historical success as transferable authority. Eighteen ordinary PR descriptions fail to identify their actual head SHA, while seventeen exact-head review-convergence gates fail. A clean review on a prior commit is irrelevant to new changed bytes unless a fresh, authorized evaluation establishes coverage. Closing review threads also does not prove their associated fixes work. PR #623 demonstrates why: its two current, non-outdated findings concern conditional claim parsing, precisely where false acceptance could make the assurance machinery report misleading success. Fix those before advertising checker reliability.

The manifest is itself a point-in-time observation. Workflows were completing during collection; even the dedicated App check on #625 changed from absent to passing. The entire inventory is sequential, not a database transaction. A file containing twenty correct heads at one instant can be stale minutes later. Moreover, the full branch-protection endpoint returned HTTP 403; only branch metadata provided the three check bindings. Never transform incomplete policy visibility into an authoritative merge verdict. Preserve negative research results and human authorization boundaries.

## 2. The First Principles Thinker

The object being evaluated is a proposed transition from a particular source tree to protected main. Its identity is the full candidate commit, not the PR number, title, or narrated result. The transition can be allowed only if separately testable predicates hold: candidate head unchanged, protected base and dependency integration valid, required checks produced by their specified Apps on that head, independent substantive review applies to those bytes, no unresolved blocking findings remain, and the proper owner authorizes any protected operation. These predicates are conjunctive. Failure or uncertainty in one makes the merge-eligible claim false or unproven.

Evidence needs its own type. A Git blob digest proves file-byte identity; it does not prove experimental truth. A successful historical workflow proves only what ran at its recorded commit and configuration. A review-thread resolution records a workflow action; it is not equivalent to testing a repaired invariant. The manifest therefore stores actual and claimed SHAs, machine-state review identities, current and historical evidence blobs, checked sources, and distinct scientific caveats. Treat this as a reproducible state assertion with expiring inputs. The next phase should enforce the predicates, not merely improve the dashboard.

## 3. The Expansionist

The manifest can become a reusable repository intelligence layer rather than a manually written report. Each PR, candidate commit, evidence artifact, review finding, check run, owner approval and dependency can be represented as an edge in a provenance graph. Then stale evidence becomes a computed property, integration ordering becomes a directed graph, and an updated head invalidates exactly the attestations whose scope no longer matches. The permanent #490 research inbox should become a discovery input to that system, while separate snapshot PRs remain the only promotion mechanism. This preserves the distinction between research leads and canonical authority.

Extend the system with a signed, machine-readable observation record and two-pass race detection: collect, then recheck all heads and the protected main before publishing. Track exact required check App identities; build a changed-file overlap graph so high-collision branches are integrated coherently. Publish a read-only triage view showing blockers first, without implying green checks equal scientific success. This could reduce repeated manual forensic work across future PR waves, but the investment is justified only if the underlying collector and authorization logic are independently tested. The current JSON and validator supply a narrow starting substrate.

## 4. The Outsider

A newcomer sees twenty open pull requests and asks a simple question: which ones are ready? The answer is none, but the reason changes by PR. #490 is supposed to remain open and draft forever; it is an intake lane, not failed work. #617 is a draft technical repair blocked by an owner's missing cryptographic authorization. #623 has two real unresolved review findings. #625 has a clean review on its current source head and two passing required checks, but other checks were still running when examined. Seventeen ordinary review-convergence checks were failing, often because their clean Codex machine summaries referenced earlier commits.

This distinction must be visible without requiring a reader to decode GitHub workflows. A SHA names exact bytes. A check is a test or gate result bound to a commit. A review thread is a discussion of a suspected defect. A signature is a separate authorization, not evidence that the code is correct. The report succeeds where it names each blocker and links to its source. It would fail if it substituted a single readiness score that concealed the different reasons or implied external research validity.

## 5. The Executor

Freeze this snapshot as an auditable baseline and use the accompanying verifier before any decision about a PR. The validator checks all twenty records for contradictory identities, missing required App bindings, stale review coverage and suppressed unresolved findings. Its optional authenticated live mode reads GitHub without writes and refuses a passing verdict when heads, check states, threads, evidence blobs or the open PR inventory differ. The local tests cover fifteen positive and adversarial cases. The full authenticated live mode could not be executed in this container because GitHub DNS resolution failed; that limitation is recorded, not concealed.

Then converge in dependency order. Repair the two executable #623 counterexamples, obtain a fresh review on the corrected head and re-run protected checks. Separately resolve #617's protected-repin requirements through the authorized owner; no agent-generated signature is a substitute. Let #625's remaining exact-head checks finish, then refresh its review and integration state. Respect the documented #608-before-#614 relationship, and combine #625's README changes with #597 only after reconciling both W4/W6 living digests. Re-run cross-PR regressions on the actual combined tree. Never merge, alter protected main or turn #490 into a promotion vehicle without explicit authorization.

## Peer review

**Strongest response:** The First Principles Thinker defines the exact predicates required for a defensible transition. Those predicates expose why a complete inventory cannot itself certify merge readiness. The Contrarian offers the strongest near-term falsification pressure by centering #623 and stale reviews.

**Largest blind spot:** The Expansionist can overinvest in a provenance graph before the existing collector and protected checks are demonstrably sound. A richer graph built atop ambiguous review or signature predicates multiplies bad confidence. The Executor must also avoid treating the owner's protected signature as a routine implementation step; it is a distinct authorization boundary.

**What all responses missed:** The live observation is not atomic, and its findings can change as checks complete even when no branch moves. Check app provenance and duplicate check-run selection must be handled precisely. High-fan-in shared test files amplify integration risk; identical evidence blobs across history do not establish current software behavior. A user-facing manifest must expose these limits, not merely state them in fine print.

## Chairman's Verdict

### WHERE THE COUNCIL AGREES

A current candidate SHA is the governing identity. Review and check evidence must bind to it. No ordinary open PR is presently fully release-authorized, and #490 is intentionally nonmergeable. #623's unresolved findings and #617's protected owner-signature requirement are real blockers, while stale descriptions and reviews are widespread.

### WHERE THE COUNCIL CLASHES

The Expansionist favors immediately turning this into a provenance service. The Executor favors first using the narrow verifier and fixing present blockers. The latter wins sequencing: additional automation should follow demonstrably correct source collection and protected gating. The Contrarian gives the highest priority to #623, while the Executor allows independent #617 owner coordination and #625 check completion in parallel.

### BLIND SPOTS CAUGHT

A snapshot can be internally consistent yet stale; current branch protection was only partly accessible through the connection; work-item path collisions are not proven source conflicts; and authentic historical file content is not authentic current-head execution evidence. These are explicit fail-closed categories in the deliverables.

### THE RECOMMENDATION

Adopt this manifest as a dated, read-only convergence baseline, not as permission to merge. Require the authenticated live verifier and fresh exact-head independent review after every source change. Prioritize the two #623 semantic-checker findings, the owner-controlled #617 signature boundary, and the documented integration order; preserve negative research evidence unchanged. Automate periodic refresh only after independent tests of collection, head movement and check-origin selection.

### THE ONE THING TO DO FIRST

Reproduce and repair both unresolved #623 review counterexamples on its exact current branch, with adversarial regression tests that fail before the fix and pass afterward.
