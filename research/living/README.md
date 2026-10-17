# Project FAR living repository

Status: **Research infrastructure; never theory or evidence authority**

Research candidate only. Discovery or triage does not establish support, dispute, novelty, priority, external validity, utility, independence, theorem status, EFR result, or any other Project FAR claim/evidence disposition.

The permanent governed [research corpus and synthesis layer](../corpus/README.md) interoperates with this discovery/control plane. It content-addresses reviewed repository inputs and derives source → finding → mechanism → conclusion → frontier views without changing this lifecycle or gaining promotion authority.

Discovery candidates and frozen external bytes enter `corpus-reconciliation-v1.0.json` as non-evidentiary leads. They can enter corpus semantics only through a protected `../corpus/reviewed-inputs-v1.0.json` entry binding the exact candidate, independently verified primary evidence, exact review record, scope, and declared observations. The reconciler verifies all hashes and the `VERIFIED_FOR_CORPUS` review status. This bridge is a Research intake action, not scientific Acceptance or Promotion; discovery metadata, scheduled-task summaries, and AI output cannot self-authorize it.

`FAR-LIVING-RESEARCH-001` and `FAR-LIVING-REPOSITORY-001` make the repository continuously self-reconciling without giving automation authority to manufacture scientific acceptance.

## What runs unattended

Every 30 minutes the scheduled workflow:

1. reads current protected `main` as governance authority;
2. searches newly indexed Crossref metadata against governed FAR research questions;
3. advances a deterministic historical backfill through older publication windows;
4. runs the same historical query/window through OpenAlex as a second scholarly index;
5. periodically performs a low-volume Open Library book search for historical philosophical, metaphysical, and logic sources that may not have DOI metadata;
6. applies deterministic signal and mathematical-bridge gates;
7. deduplicates across providers by normalized DOI when possible;
8. maps candidates to exact governed research questions and any FAR-CORE identifiers explicitly present in those questions/dependencies;
9. records source failures rather than treating them as empty evidence;
10. reconciles canonical claim, assurance, research-question, limitation, open-problem, dependency, and program surfaces by content hash;
11. derives the FAR-CORE dependency/reverse-impact graph from the canonical assurance ledger;
12. builds a non-authoritative core-claim review queue for high-attention candidates;
13. updates generated living-research and living-repository status pages;
14. validates the result before writing only to `automation/living-research-inbox`;
15. refreshes one permanent draft rolling PR. It never writes directly to protected `main` and the rolling inbox PR is never the promotion PR.

## Execution boundary

The scheduled job builds its working tree from protected `main` and carries only accumulated *data* (`inbox/`, `runs/`, `state-v1.0.json`, `repository-state-v1.0.json`) across from `automation/living-research-inbox`. Tools and configuration always come from `main`. The job never checks out and executes code from the inbox branch, which is not protected; doing so would let anyone able to push there run code under a write-scoped token on a schedule.

The branch is rebuilt as a single commit on current `main` each run, so the rolling PR stays a readable one-commit diff and cannot conflict with its own base.

## Permanent rolling PR

Steady-state operation uses one permanent draft PR for `automation/living-research-inbox`. `research/living/inbox/.rolling-pr-anchor.json` exists on that branch solely so the PR remains non-empty immediately after canonical snapshot promotion. The anchor is not a candidate or evidence item and must never be copied into a promotion snapshot.

Because the PR already exists, the discovery scheduler only refreshes it. The permanent inbox PR must not be merged or closed during normal operation. If it disappears, the writer preserves research data on the branch and the governance step fails closed until a human bootstraps one replacement permanent PR. Broadening automation authority is not the recovery path.

## Governed promotion

Promotion is a separate transaction from discovery. `Living Research Promotion` executes code only from protected `main`, freezes the exact PR #490 head and exact current-main base, and may prepare/open a separate promotion PR. It never merges that PR.

Review-disposition membership alone is not promotion authority. A Research snapshot requires an explicit protected entry in `snapshot-authorizations-v1.0.json` binding the exact candidate bytes, exact review row, exact review-basis bytes, source identity, and disposition. Existing review rows that lack such an authorization remain unpromoted.

Canonical edits require the stronger `PROMOTION_PROPOSED` lifecycle stage and an explicit protected entry in `promotion-authorizations-v1.0.json` binding the exact proposal, candidate, operation set, and Question/Execution/Observation/Discovery/Replication/Acceptance hashes.

`PROJECT_CHANGE_REQUIRED` is the fail-closed bridge between discovery and repository correction. Governed review may record it only when the accepted result requires Project FAR to change and the review binds one exact nonempty scientific correction proposal. The exact candidate must also have snapshot authorization and the exact proposal must have canonical-promotion authorization. A project-changing result therefore cannot be accepted merely as a queue note.

The same review must declare `implementation_required`. If false, `implementation_proposal_id` is null. If true, it must bind one exact `IMPLEMENTATION_PROPOSED` package plus an exact protected entry in `implementation-authorizations-v1.0.json`.

When those protected acceptance/authorization records land on `main`, or when the permanent inbox completes explicit validation after an update, routing runs immediately. The scientific promotion workflow verifies the exact candidate, scientific proposal, nonempty operation set, provenance, preimages, and payload hashes and opens the separate scientific correction PR. When implementation is required, `Living Research Implementation` independently freezes the same source/base boundary, validates exact protected implementation authorization, target/preimage/payload hashes, copies the authorized bytes without executing them, seals the diff, and opens a separate implementation PR. Scheduled passes remain recovery paths.

Every scientific promotion branch and implementation branch is keyed by the complete source SHA and complete base SHA and must contain exactly one sealed commit on its frozen base. If PR #490 or `main` moves, the transaction fails and must be regenerated against the new exact state.

Merging a Research-only snapshot or merely opening either correction PR does not itself establish support, dispute, novelty, external validity, utility, independence, theorem status, or EFR results.

The scientific mechanical contract is in `PROMOTION.md`; the executable/control-plane contract is in `IMPLEMENTATION.md`.

## Attention terms are derived, never accumulated

Each provider's attention-term matches are stored on that provider's source entry and replaced whenever that provider is seen again; `triage.attention_terms` is recomputed as the union of those, filtered to the currently configured terms. A term removed from `attention_terms` in the configuration therefore clears on the next sighting instead of marking a candidate high-attention forever.

## Run-report validation

`tools/check_living_research.py` validates the newest 500 run reports. Reports are immutable and are validated when written, so every automatic path uses that bound; `--all-runs` (used by the pull-request job) still checks every one of them.

## PR-status boundary

Updates pushed to the permanent inbox by `GITHUB_TOKEN` do not manufacture protected PR status checks and never make PR #490 canonical. Promotion therefore uses distinct exact source+base branches and PRs, opened by the dedicated promotion App so that each PR's own `pull_request` run produces `merge-authority` (see `PROMOTION.md`). The transactions cannot forge or replace protected merge authority.

Canonical tests independently verify the final scientific promotion head. For pull-request CI, where GitHub checks out a synthetic merge commit, the verifier resolves `GITHUB_HEAD_REF` and checks the exact promotion commit. It is read-only and rejects stale bases, multiple commits, forged manifests, unauthorized or unsealed files, authorization/provenance drift, and protected/control-plane targets.

The implementation path separately rejects unprotected authorization, target escape, stale preimages, payload drift, colliding targets, source/base movement, unsealed paths, and source execution. If an implementation proposal changes merge-authority's own declared assurance-sensitive surface, automation still creates the PR but deliberately does not use that modified assurance workflow to certify itself.

## Historical, philosophical, and metaphysical coverage

Historical backfill starts at the present and walks backward in ten-year publication windows to 1600. The query set covers sufficiency/statistics, quotient minimization, automata/Myhill-Nerode, bisimulation/coalgebra, abstract interpretation, Blackwell/decision theory, invariance, scientific representation, underdetermination, measurement theory, formal identity, grounding/dependence, formal ontology, logic/semantics, probability/decision, and formal language.

Philosophy and metaphysics are not admitted merely because they mention a broad theme. Lenses that could otherwise become unconstrained require an explicit bridge to formal or mathematical content such as logic, identity, relation, structure, equivalence, model, semantics, modality, order, category, algebra, measurement, probability, decision, or information.

Open Library is intentionally low-volume and used only for historical book discovery. It is not treated as a bulk scholarly backend or as evidence authority.

## Claim-change behavior

The living repository **can detect that a core claim may need to change** and calculate the downstream FAR-CORE claims that depend on it. A metadata result never constitutes a contradiction.

Canonical correction path:

`candidate → source verification → exact claim reconstruction → attack → replication → acceptance → PROJECT_CHANGE_REQUIRED + exact authorizations → automatic scientific correction PR + automatic implementation PR when required → protected merge`

A reproducible contradiction satisfying the exact canonical premises may trigger the smallest affected reopening/correction path. The old claim remains recoverable through Git history.

The scientific correction PR carries every exact authorized target permitted by the scientific promotion policy. Executable and control-plane surfaces remain outside that write boundary. When such changes are required, the separately authorized implementation path automatically opens a second PR from protected `main`; inbox bytes remain untrusted data and are never executed by the write-scoped materializer.

The automation may enter only `DISCOVERED` by itself. Every later scientific lifecycle stage is governed. EFR remains separate and externally executed.

## Files

- `config-v1.0.json` — sources, governed questions, lenses, backfill, and triage.
- `state-v1.0.json` — incremental and historical cursors.
- `lifecycle-v1.0.json` — scientific stage-transition boundary.
- `review-dispositions-v1.0.json` — protected review/queue memory; not promotion authority.
- `project-change-policy-v1.0.json` — accepted project-change correction and implementation-obligation rule.
- `snapshot-authorizations-v1.0.json` — protected exact-byte Research snapshot authority.
- `promotion-authorizations-v1.0.json` — protected exact scientific/canonical-edit authority after `PROMOTION_PROPOSED`.
- `promotion-policy-v1.0.json` — scientific automatic-write and sealing boundary.
- `PROMOTION.md` — complete scientific promotion contract.
- `implementation-authorizations-v1.0.json` — protected exact implementation-package authority.
- `implementation-policy-v1.0.json` — executable/control-plane target, sealing, and self-validation boundary.
- `IMPLEMENTATION.md` — complete implementation-PR contract.
- `repository-surfaces-v1.0.json` — canonical surfaces monitored for drift.
- `repository-state-v1.0.json` — generated reconciliation/impact state.
- `inbox/candidates/` — deduplicated source candidates.
- `runs/` — per-run query/result/rejection/failure provenance.
- `../../docs/research/living-research-status.md` — discovery status.
- `../../docs/research/living-repository-status.md` — repository reconciliation status.

## Commands

```bash
python tools/run_living_research.py
python tools/reconcile_living_repo.py
python tools/check_living_research.py
python tools/check_living_project_change_obligations.py
python -m tools.run_living_research_promotion
python tools/living_implementation_contract.py --help
python -m tools.run_living_research_implementation
python -m tools.check_living_promotion_head
python -m unittest tests.test_living_research tests.test_living_research_workflow tests.test_living_research_promotion tests.test_living_research_promotion_runner tests.test_living_research_promotion_workflow tests.test_living_project_change_obligations tests.test_living_implementation_contract -v
```
