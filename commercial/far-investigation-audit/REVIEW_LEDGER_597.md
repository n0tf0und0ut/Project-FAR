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
