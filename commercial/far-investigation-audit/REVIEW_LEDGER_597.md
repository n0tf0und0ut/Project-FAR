# PR 597 software review ledger

Status: Research implementation review; no independent scientific assurance.

Initial reviewed head: `ef88af8cf2696004db90224c055d2b3a53288706`.
Base: `8f0e8e330d8f11a629447e23f3d00e6a5f81c1e6`.
Review submission: `5670073956` by the authenticated Codex review service.
Software review does not provide external scientific independence.

Every finding below was accepted and reproduced before correction. The six
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
