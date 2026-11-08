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
