# FAR-CORE v1.1 proof-assistant formalization

Status: **Generated W2 assurance view; not governing theory authority**

Sources: [`theory/evaluation/far-core-formalization-ledger-v1.0.json`](../../theory/evaluation/far-core-formalization-ledger-v1.0.json)
and [`artifacts/mechanization/lean-inventory-v1.0.json`](../../artifacts/mechanization/lean-inventory-v1.0.json).
Edit the machine ledger or Lean sources and regenerate this view.

Lean proves machine-checked derivations relative to the encoded premises. It does not establish
novelty, empirical validity, or universal architecture. The W1 truth verdicts, historical
provenance labels, and proof-assistant status remain separate dimensions.

The W2 workflow captures every `#print axioms` result and rejects missing declarations,
unexpected transitive assumptions, or any mismatch with the declaration-level and claim-level
assumption contracts. Merely printing the audit is not accepted as assurance.

## Outcome matrix

| Claim | W2 outcome | Kernel | Kernel assumptions | Declarations | Obstruction |
|---|---|---|---|---|---|
| `FAR-CORE-001` | `FORMALIZED` | `PASS` | `Classical.choice` | `FARCoreV11.exact_factorization_criterion`<br>`FARCoreV11.collision_refutes_sufficiency` | — |
| `FAR-CORE-002` | `FORMALIZED` | `PASS` | `Classical.choice`<br>`Quot.sound` | `FARCoreV11.quotient_is_sufficient`<br>`FARCoreV11.observational_quotient_universal`<br>`FARCoreV11.factorToQuotient_surjective`<br>`FARCoreV11.leastInformativeImageEquiv`<br>`FARCoreV11.leastInformativeSufficient_iff_kernelEqual`<br>`FARCoreV11.quotient_is_least_informative_sufficient` | — |
| `FAR-CORE-003` | `FORMALIZED` | `PASS` | `Quot.sound` | `FARCoreV11.action_preserves_observational_equivalence`<br>`FARCoreV11.descendAction` | — |
| `FAR-CORE-004` | `FORMALIZED` | `PASS` | `Classical.choice`<br>`Quot.sound` | `FARCoreV11.no_contract_free_simultaneous_minimum`<br>`FARCoreV11.identity_is_universally_sufficient`<br>`FARCoreV11.no_simultaneous_least_informative_sufficient` | — |
| `FAR-CORE-005` | `FORMALIZED` | `PASS` | `none` | `FARCoreV11.invariants_antitone` | — |
| `FAR-CORE-006` | `FORMALIZED` | `PASS` | `Classical.choice`<br>`Quot.sound`<br>`propext` | `FARCoreV11.embeddingRangeEquiv`<br>`FARCoreV11.transport_operation_commutes`<br>`FARCoreV11.transport_relation_commutes` | — |
| `FAR-CORE-007` | `FORMALIZED` | `PASS` | `none` | `FARCoreV11.reification_recovers_relation`<br>`FARCoreV11.primitive_vocabulary_count_noninvariant` | — |
| `FAR-CORE-008` | `FORMALIZED` | `PASS` | `Quot.sound` | `FARCoreV11.combine_split_operator_family`<br>`FARCoreV11.split_combine_operator`<br>`FARCoreV11.finite_operator_count_noninvariant` | — |
| `FAR-CORE-009` | `FORMALIZED` | `PASS` | `none` | `FARCoreV11.finite_panel_two_completions` | — |
| `FAR-CORE-010` | `FORMALIZED` | `PASS` | `Quot.sound`<br>`propext` | `FARCoreV11.commonTheory_frame_independent`<br>`FARCoreV11.commonTheory_invariant_under_truth_equivalence`<br>`FARCoreV11.residue_can_change_with_frame` | — |
| `FAR-CORE-011` | `FORMALIZED` | `PASS` | `none` | `FARCoreV11.omitted_parameter_refutes_sufficiency` | — |
| `FAR-CORE-012` | `FORMALIZED` | `PASS` | `none` | `FARCoreV11.absent_unknown_must_separate` | — |
| `FAR-CORE-013` | `FORMALIZED` | `PASS` | `none` | `FARCoreV11.Omega.omega_elimination`<br>`FARCoreV11.Omega.resolve_is_composition` | — |
| `FAR-CORE-014` | `FORMALIZED` | `PASS` | `Quot.sound`<br>`propext` | `FARCoreV11.SSS.four_monotone_decoders`<br>`FARCoreV11.SSS.projected_successor_decoder_failure`<br>`FARCoreV11.SSS.hyperedge_factorization`<br>`FARCoreV11.SSS.frontier_factorization`<br>`FARCoreV11.SSS.MLL.derivable_atom_balance`<br>`FARCoreV11.SSS.MLL.sOr_witness_certified`<br>`FARCoreV11.SSS.MLL.sAnd_witness_certified`<br>`FARCoreV11.SSS.MLL.bounded_projected_decoder_failure`<br>`FARCoreV11.SSS.MLL.summaries_match_mll_witnesses`<br>`FARCoreV11.SSS.MLL.mll_projected_decoder_failure` | — |

## FAR-CORE-014 bounded application bridge

The governed MLL syntax, cut-free unit-free derivability rules, atom-balance invariant, both named
witness sequents, their mixed projected-successor truth profiles, and the uniform-decoder failure
are now kernel-checked in `FARCoreV11SSS.lean`. The positive hyperedge and frontier statements
remain explicitly conditional on their stated rule-characterization/recursion premises. This
formalization does not enlarge FAR-CORE-014 into a universal architecture claim.

## W2 module inventory

| File | SHA-256 | Lines | Imports |
|---|---|---:|---|
| `mechanization/lean/FARCoreV11AxiomAudit.lean` | `cd6e88e642ac0d397eacde46201b552f6c2ed1a7c02607181b57bbb7e70c55fa` | 44 | `FARCoreV11Claims001To012`, `FARCoreV11Omega`, `FARCoreV11SSS` |
| `mechanization/lean/FARCoreV11Claims001To012.lean` | `52dbd255de8cd64cbcac5a437bd8827d20e9fe4c0fbd3fb318e01b5be22e04a7` | 388 | `FARCoreV11Substrate` |
| `mechanization/lean/FARCoreV11Mutations.lean` | `e129549526c8f13078c3ae5d8897926700c5cef340f5b56387dd2212c603bdf7` | 182 | `FARCoreV11Claims001To012`, `FARCoreV11Omega`, `FARCoreV11SSS` |
| `mechanization/lean/FARCoreV11Omega.lean` | `52570fe1ed0c7a76b850162d584d47e759098b054a8cd147161891d663a7044c` | 51 | `FARCoreV11Substrate` |
| `mechanization/lean/FARCoreV11SSS.lean` | `c58a9b55385fb1ce0a6555ef827ebec0d5c38a63130eb07f8003f6821c73ad53` | 412 | `FARCoreV11Substrate` |
| `mechanization/lean/FARCoreV11Substrate.lean` | `65cda881f620c02611e86e00e9f7bd8d6a9e7ed89740de81b7f95c2ab4b35504` | 293 | `Std` |

The inventory also records every pre-existing Lean file as `LEGACY_OR_OTHER_SCOPE`. Those files
were searched and retained; they do not silently count as coverage of FAR-CORE-001--014.
