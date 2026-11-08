# PR 597 software review ledger

Status: Research implementation review; no independent scientific assurance.

Initial reviewed head: `ef88af8cf2696004db90224c055d2b3a53288706`.
Base: `8f0e8e330d8f11a629447e23f3d00e6a5f81c1e6`.
Review submission: `5670073956` by the authenticated Codex review service.
Software review does not provide external scientific independence.

Every finding below was accepted and reproduced before correction. The initial six
root-cause regressions produced nine failed subcases and one error before the
fixes, then six passing tests afterward. Exact before/after logs are preserved
in the campaign directory. The successor commit containing this ledger carries
the fixes and tests together; the PR records its exact published commit.

| Root cause / source comment | Violated invariant and reproducer | Correction and regression | Disposition |
| --- | --- | --- | --- |
| ED-R1 / 4390863035 | Unsupported number words and plural descriptions fell through as singular subjects; negation of “exactly thirty blue” was accepted as “exactly thirty not blue” | Reject unrecognized count words and restrict the unquantified singular lane; `test_4390863035_unsupported_cardinal_cannot_be_singular` covers five forms | Fixed; original head and failure retained |
| ED-R2 / 4390863050 | Negating a universal moved negation across unresolved temporal scope | Universal negation now abstains for a temporal predicate; `test_4390863050_universal_negation_keeps_temporal_scope_unknown` | Fixed |
| ED-R3 / 4390863057 | Appending an individually valid event could cross the aggregate payload cap and make all future replay fail | Check current total plus new payload inside the transaction before insertion; reject and roll back; `test_4390863057_aggregate_limit_rejects_before_commit` | Fixed |
| ED-R4 / 4390863070 | Audit fidelity could pass while evidence fidelity was contradicted | Roll up all claim and evidence mappings, including missing/abstained mappings; `test_4390863070_failed_evidence_mapping_blocks_assurance_pass` | Fixed |
| ED-R5 / 4390863082 | Resume inserted an explicit clock, making authorized live URL acquisition fail the backdating guard | Leave the clock unset unless explicitly supplied; verify acquisition succeeds and explicit historical capture still fails; `test_4390863082_resume_live_url_assigns_capture_during_acquisition` | Fixed |
| ED-R6 / 4390863105 | Retained discovery sources acquired new `evN` names while inherited citations kept old names | Deep-copy and consistently remap inherited evidence/lineage references; `test_4390863105_discovery_source_refs_survive_resume` verifies both original and resumed packages | Fixed |

Additional construction/integration repairs are retained in the PR description:
explicit legacy opt-in, modal scope and unresolved count-equivalence abstention,
per-occurrence source provenance, future-valid correction handling, supported
local JSON-schema API, current documentation/corpus commitments, strict verifier
routing, bounded invalid-database CLI recovery, canonical cognitive dependency
composition, and deterministic source/version runtime identification.

Validation of a successor head must include the complete component suite,
the original frozen campaign, correction/mutation controls, changed coverage on
the public-source shift set, full repository validation, final-head substantive
review and the existing protected checks. Original findings are not cleared by
stale green CI or by marking threads resolved. No protected gate is weakened.

## Second material-head review

Reviewed head: `cf26c031609f4c3760fd2f76a38f8d90aa0fe691`. Two additional findings were accepted and reproduced as failing tests before correction; both now pass. Exact `review-round2-before.log` and `review-round2-after.log` preserve those outcomes. The complete integrated component suite passes 276 tests (50 debugger acceptance/property/review tests).

| Root cause / source comment | Violated invariant | Correction and regression |
| --- | --- | --- |
| ED-R7 / 4391124909 | Validated upstream source lineage was absent from correction adjacency | Add validated upstream-to-dependent source graph edges, including canonical cognitive source lineage; `test_4391124909_declared_lineage_propagates_retraction_and_restore` checks retraction and restoration |
| ED-R8 / 4391124913 | Equivalent quantified leaves became definitive contradictions inside conditionals | Recursively propagate unresolved leaf equivalence through matching logical contexts in fidelity and collision detection; `test_4391124913_nested_count_equivalence_abstains_and_never_collides` |

Protected-main integration reuses canonical FAR-COG/0.1 from merged PR #596. Its source records and validated lineage participate in the same memory graph; its auditor remains the sole implementation of that contract. Registrations v7–v9 preserve intermediate and corrected combined runtimes.

## Local user-interface integration finding

ED-I1: The same text sent through `/api/investigate` enabled the debugger, while `/api/upload` omitted it and emitted only the legacy report. A transport-level regression failed before correction (`ui-before.log`) and passes afterward (`ui-after.log`). Uploads now enable the same canonical debugger; no second reasoning implementation is added. `test_pasted_and_uploaded_text_share_debugger_report` checks both actual request paths and nonacceptance of unsupported formal readings. The complete component suite passes 277 tests, including 51 debugger tests. Registration/runtime v10 and run 010 retain the successor configuration; all earlier runs remain intact.

## Final-head review corrections (2026-11-03 convergence)

Reviewed head: `5667383fff19af0a370b24d6ba2940dc3543c1fb`.
These corrections extend the live implementation and tests; all numbered frozen
campaigns, inputs, runtime archives and original observations remain unchanged.
A successor head requires a new exact-head substantive review.

| Root cause / source | Reproducer and observed failure | Correction / verification | Disposition |
| --- | --- | --- | --- |
| ED-R9 / comment 4391545567, thread PRRT_kwDOTH_vCM6wyewB | `fidelity('Rain is not wet.', {'atom':'P'}, {'P':'Rain is wet.'})` returned `ABSTAIN`; the same-atom pair emitted no collision. The new regression failed against the reviewed source. | Limit unresolved count-equivalence abstention to two quantified predications. Singular polarity and nested conditional polarity now produce `CONTRADICTED`, and the pair emits a collision. `test_4391545567_singular_polarity_is_not_count_equivalence` passes; existing nested quantified-equivalence abstention remains tested. | Fixed in the commit containing this entry; final-head service review remains required. |
| ED-R10 / comment 4391545578, thread PRRT_kwDOTH_vCM6wyewK | Core-only discovery of `test_debugger_ui.py` failed with `ModuleNotFoundError: fastapi`, reproduced before correction. | Check optional FastAPI, HTTPX and multipart availability before UI imports. Core-only discovery cleanly skips; dependency-equipped UI test runs. | Fixed; no dependency or test assertion weakened. |

Verification on the corrected source: **278/278 complete component tests pass**,
including the actual pasted/uploaded-source HTTP UI integration, independent
SymPy/property controls and all prior review regressions. Core-only UI discovery
reports one explicit optional-dependency skip. Passing tests provide bounded
software evidence, not general semantic coverage or independent effectiveness.

## Resumed source-lineage coverage

ED-R11 / comment `4458895730`, thread `PRRT_kwDOTH_vCM6zRo3v`, reviewed
head `16573648e92baa8ef2f810c7957118ea08bab7ca` (also reproduced on its
derived-index-only successor): a verified package with declared primary-origin
lineage failed default resume after adding evidence, with `lineage must cover
actual sources`. The inherited declarations covered retained sources only.

`resume_request` now retains/remaps those declarations and appends explicitly
`unknown` lineage records for newly added `evN` sources. All unknown additions
share an unresolved-root placeholder; distinct independent origins are not
invented. Explicit replacement proposals remain caller-supplied contracts.
`test_4458895730_resume_extends_inherited_lineage_without_claiming_independence`
failed before correction and now verifies the original declarations, two added
unknowns, portable replay and a second resume. The complete dependency-equipped
component suite passes **279/279 tests**. Frozen campaign bytes remain unchanged;
this correction does not rerun or replace their observations.

## ED-JSON-001 — ambiguous web debugger request

Coordinator review on `94fd7e193b48979428624bc8a37f8e55d3e16003` reproduced
`{"debugger":true,"debugger":false}` reaching the investigation as `false`
and returning HTTP 200. The debugger added by this PR therefore inherited a
web decoder that could silently change the supplied mode or source text.
The same parser accepted nonfinite JSON constants. The new raw-request
regression failed three adversarial subcases before the correction.

The web route now reuses the existing bounded `parse_json_artifact` helper,
rejecting duplicate members and nonfinite constants with HTTP 422 before
investigation. A further raw `1e309` counterexample reached investigation as
infinity on the initial parser-reuse successor; the shared helper now rejects
exponent overflow during float conversion as well. That regression failed
before the additional correction. Tests retain an over-nested control and a subsequent
valid request proving the worker gate is released. The two new tests pass;
all 281 dependency-equipped component tests pass. This changes request intake
only; frozen protocols, source snapshots, campaign results and scientific
assurance are unchanged. A fresh substantive review on the successor head
and hosted protected checks remain separate obligations.

## November 6 current review corrections — pending verification

The following substantive Codex findings were reported on the preceding head. Each
has a distinct reproducer and root cause; commits below are implementation evidence
only. Exact-head hosted component/integration validation, a fresh independent
substantive review, and protected required checks are **pending**. Do not close
threads or assert merge readiness solely from these edits.

| ID / review evidence | Violated invariant and concrete counterexample | Branch correction and regression | Current disposition |
| --- | --- | --- | --- |
| ED-R12 / comment `4495176866`, thread `PRRT_kwDOTH_vCM60mvzA` | `Something is not blue` can be true even where `not (Something is blue)` is false; an existential pronoun cannot inherit fixed-referent singular negation. | `8ade9c75bef88ea9c2623584353f81e462ad8ca5` rejects ambiguous quantified/indefinite pronouns in the deliberately bounded grammar. `test_449514_quantified_pronouns_cannot_be_fixed_singular` covers 15 subjects and requires abstention. | Implemented, verification/review pending. |
| ED-R13 / comment `4495176881`, thread `PRRT_kwDOTH_vCM60mvzK` | Sharing source bytes across investigations incorrectly shared dependency edges; withdrawing Y from one derived X invalidated another independently sourced identical X. | `bcc445fbd641615bc22f4322ff385e9921d4123b` retains one content-addressed byte node but separates source-occurrence nodes and their declared lineage. `test_449514_lineage_does_not_cross_deduplicated_source_occurrences` requires derived-only invalidation, valid independent reading, and successful restoration. | Implemented, verification/review pending. |
| ED-R14 / comment `4495176875`, thread `PRRT_kwDOTH_vCM60mvzG` | Rebuilding a resume request by inlining three individually valid remote captures of roughly 160 KB exceeds the 450 KB raw-intake limit before verified-source continuation can begin. | Commits `1aabe11ddab71004a08bfa2d557da20f6f667881`, `e963ad46ae961a263f3be06aa28150e7d15e056a`, and `9002272115eacc449b7f2b1a0ab2ac2618c10c8b` introduce local `VerifiedSnapshotResume` references to replay-verified retained bytes; ordinary requests retain their original 450 KB cap and unbound references fail closed. `test_449514_resume_reuses_large_verified_snapshots_without_input_bypass` checks large resume, forged ordinary-dictionary rejection, and second-package replay. | Implemented, verification/review pending. |

The resume correction also required an acquisition-provenance follow-up:
`74fac5af238f07cc588e8f86a0628e8da928d235`,
`c5ff6c58f0c8d7f6e3191d5199464bd5f7993e07`,
`9c2a72adab4eac1be5a1f97b16c1567b14f2f8d2`, and
`b4ad19e49453276aa251397b9fdd79f8adc7c8b2`.
A verified continuation now retains the original acquisition record, URL
when present, and source capture timestamp; the manifest records remote
source use. The expanded large-snapshot regression asserts acquisition URLs,
capture timestamps, source hashes, and portable replay. The additional
failure mode was that converting remote acquisition into plain text would
misreport remote provenance despite retaining source bytes.

All updates are source/test amendments. Historical frozen experiment outputs,
registered scientific acceptance criteria, and protected-main theory remain unchanged.

## DOC-CROSS-597-625 — documentation integration (2026-11-08)

Integrated protected main `eff47bc4fc9e272e87d71ecfc8d559cd1176753e`
through PR #625's refreshed head `6ebc988553d4e6b20963cf9dc6fb3db9165bb1d1`.
PR #625 remains a merge dependency until its reviewed documentation reaches main.
The candidate is a normal merge successor of #597 head
`94603603fd6c863cf3895496af64cf2f003db480`; no shared history is rewritten.

The merge reproduced conflicts in README and both W4/W6 current-state supplements.
After preserving #625's newcomer/task routes and relocating #597's unchanged
scoped Research debugger paragraph below Framework roles, each actual campaign
checker rejected the retained predecessor digest independently with
`W4_SUPPLEMENT_CURRENT_DIGEST_DRIFT` / `W6_SUPPLEMENT_CURRENT_DIGEST_DRIFT`.
Both existing README entries now bind the combined living document at SHA-256
`6af9fc8762db5da3f2548343f56059daf954ddca2ddbacb29f62d95473aee484`.
The executed digests, frozen manifests, sources, protocol, results, and all
non-README supplement entries remain unchanged by this correction.

After correction the W4 campaign check, all 34 W4/W6 unit tests, and W6 campaign
recomputation pass. This is documentation-integrity and bounded replay evidence;
it introduces no new scientific result or empirical advantage claim. Final-head
hosted gates, substantive independent review and the #625 merge dependency remain
separate obligations.

### DOC-CROSS-597-625-DERIVED — downstream inventory invalidation

Hosted `validate` job `128648838021` on `48358a5f069bbd764cc4f57225961b0594cfa7d9`
passed 66 living/corpus tests, then failed `stale generated output:
research/corpus/synthesis-v1.0.json`. The exact command sequence reproduces the
failure: `reconcile_living_repo.py` first updates its canonical-entry README hash
from the predecessor value to the combined document; that declared mutable
repository-state dependency invalidates corpus inventory/synthesis identities.
A direct corpus check before living reconciliation misses this integration order.

The existing living reconciler was run to a stable state, then the existing
`reconcile_research_corpus.py --write` regenerated the derived synthesis and
frontier. Only the living README surface hash and five synthesis identity/input
fields changed; corpus semantic inputs, observations, conclusions, frontier
content, scientific statuses and all frozen evidence remain unchanged. The exact
66-test hosted validation subset passes locally; the same two-stage command
sequence then passes and produces stable output. Independent exact-head review
and hosted protected gates remain required after this successor correction.
