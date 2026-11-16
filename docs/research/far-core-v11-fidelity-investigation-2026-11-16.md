# FAR Core v1.1 theorem-fidelity investigation — 2026-11-16

**Status: Research — not an Acceptance or Promotion record.** This is a source-grounded
adversarial examination of formalization fidelity and the known `LIM-052`/`LIM-053`
assurance defects. It does not alter accepted theorems, W1 truth verdicts, the W2
historical formalization record, or the authority of frozen evidence.

## Pinned primary material

- Protected-main baseline: `a9eb83eee705ba3e242b3f329712f6352761c6c1`.
- Complete current root `AGENTS.md` read before repository analysis.
- Original v1.0 theorem source: `theory/theorems/Project-FAR-Theory-Closure-v1.0.md`;
  historical SHA-256 `b7cbd28d54686da33773a66edf9af9480044ffaabfeb83cfa4bfc1a12fe862a5`.
  Frozen original not modified.
- Corrected v1.1 governing source: `theory/theorems/Project-FAR-Theory-Closure-v1.1.md`;
  original lineages for FAR-CORE-004/010 superseded by v1.1.
- Primary executable statements: `mechanization/lean/FARCoreV11Substrate.lean`,
  `FARCoreV11Claims001To012.lean`, `FARCoreV11Omega.lean`,
  `FARCoreV11SSS.lean`, and `FARCoreV11Mutations.lean`.
- Cross-checking inputs: `theory/evaluation/far-core-formalization-ledger-v1.0.json`,
  `tools/check_far_core_v11_formalization.py`, and the governing
  `docs/governance/limitations-register.md`. The ledger is a locator and
  reported-status claim, **not** independent evidence of statement fidelity.

## Method and assurance classes

The investigator reconstructed the core mathematical argument from the original v1.0
theorem statements, applied the explicit v1.1 corrections, then compared them with
the actual Lean declaration headers and source proof structure. Where possible,
the proof obligation was reduced to a direct quotient, kernel, or countermodel
argument. Existing formalization assertions were not treated as independent proof.

The executed code guard pins the normalized *source headers* of all **40** mapped
Lean declarations. It fails on missing/duplicate declarations and changed
headers, including replacing the FAR-CORE-009 proposition with `True`, while
allowing proof-body-only edits. This protects against a specific silent weakening.
It does **not** check elaborated Lean type equivalence, whether changed definitions
silently alter unchanged theorem expressions, semantic correspondence to the
English theorem, or independence of the initially pinned headers.

Classification below is **this source inspection's scope-specific assessment**,
not an externally replicated verdict or a change to the governed claim ledger.

## Fourteen claim-to-proof dispositions

| Claim | Source-based mathematical reconstruction | Lean counterpart and observed limitation | Fidelity classification |
|---|---|---|---|
| 001 | For exact `beta`, a decoder on the reachable `rho`-image exists iff `ker(rho) ⊆ ker(beta)`; one separating collision refutes it. | `exact_factorization_criterion`, `collision_refutes_sufficiency`; representative choice is an explicit kernel dependency. | In-scope correspondence observed |
| 002 | `X/ker(beta)` is exactly sufficient; every sufficient image maps uniquely onto it; least-informative means kernel equality. | Quotient, unique factor, surjection, isomorphism, and minimality bridge are present. Comparison quantifies representations into `Type u`; not arbitrary larger universes or cost minimality. | In-scope correspondence with explicit universe limit |
| 003 | Precomposition closure of tests under an action makes observational equivalence action-compatible and lets the action descend to the quotient. | `ContextClosedFor`, `action_preserves_observational_equivalence`, `descendAction`; closure is a premise, not inferred. | Conditional correspondence observed |
| 004 | Constant versus injective behavior demand incompatible *least-informative* kernels on any domain with two distinct cases; identity remains universally sufficient. | `no_simultaneous_least_informative_sufficient` proves the corrected minimality claim using the derived minimum/kernel bridge. | In-scope correspondence observed |
| 005 | Invariance under a larger transformation class implies invariance under each subclass. | `invariants_antitone` directly formalizes the subset argument. | In-scope correspondence observed |
| 006 | Injection yields recovery and transport of named operations/relations onto the reachable image. It does not imply the host has the structure natively. | `embeddingRangeEquiv` and transport commutation are explicit. The extra philosophical/non-selection inference is not itself a Lean theorem. | Partial: transport established, non-selection requires separate semantic formulation |
| 007 | Typed relation occurrence reification can reconstruct the original binary relation, but a statement about primitive-count invariance requires a formal presentation and counting rule. | `reification_recovers_relation` is substantive; count difference is between hand-stipulated `directBinaryVocabulary` and `reifiedIncidenceVocabulary`. | Partial: stipulated counts, no syntax-derived count |
| 008 | A tagged dispatcher and family are mutually recoverable; a genuine primitive-count comparison requires the count to be derived from the admitted presentation syntax. | `combine_split_operator_family`, `split_combine_operator` verify recovery; 2-versus-1 count is stipulated. | Partial: stipulated counts, no syntax-derived count |
| 009 | A proper finite observed panel has at least two open-domain predicate extensions with identical on-panel behavior and differing off-panel behavior. | Original `finite_panel_two_completions` proves two completions agree on-panel but does not parameterize the observed predicate. The proposed additive `finite_panel_observation_extensions` explicitly carries `observed` and requires agreement with it on-panel. | Partial in baseline; additive strengthening compiled in Lean 4.19.0 on exact source at hosted run `43881439555` |
| 010 | Holding `L,J,I` and their models fixed, exact common theory is independent of `Gamma`; frame-subtracted residue may vary. | `CommonTheory` is an abstract truth intersection rather than first-order `Th_L`; `Residue` uses an abstract consequence operator; the frame independence is definitional and the residue witness premises are supplied. | Partial: full model/closure semantics unformalized |
| 011 | Any collision induced by omitting a consequence-changing parameter violates exact sufficiency. | `omitted_parameter_refutes_sufficiency` is a direct kernel/collision instantiation. | In-scope correspondence observed |
| 012 | Distinct outcomes such as determinate absence and unknown cannot be merged under any sufficient representation when the contract observes them. | `absent_unknown_must_separate` proves the typed one-test case; a general typed multi-test claim follows from 001 but is not explicitly quantified here. | Partial: one-test witness |
| 013 | If canonical `Omega` is defined as representation of calculus classifications, downstream resolution equals ordinary composition. | `omega_elimination` and `resolve_is_composition` unfold by definition; this does not independently establish that every possible admissibility structure is reducible. | Definitional, exactly scoped |
| 014 | On a bounded unit-free MLL witness surface, a restricted uniform monotone projected-successor decoder cannot distinguish the required derivability profiles; alternative representations factor under supplied rule premises. | `mll_projected_decoder_failure` now ties explicit sequents to the decoder failure; `hyperedge_factorization` and `frontier_factorization` require rule/recursion characterization premises. | Bounded and conditional; no universality claim |

## Reproduced defect mechanism and repairs

**LIM-053, original failure mode:** `alignment_errors()` checked for declaration
presence but not the proposition type. A weaker declaration with the same name could
survive the Python alignment gate, even if Lean itself compiled the weaker theorem.
This was verified directly from the original checker implementation.

**Additive mitigation:** a 40-entry source-level proposition-signature lock is checked
by `alignment_errors()`. The mutation tests verify rejection of a weakened `True`
statement and a duplicate declaration, and continued acceptance of harmless proof
comment changes. These are tests of the Python guard; the `True` mutation itself
is not represented as a successful Lean compilation.

**LIM-052, independently recoverable narrow case:** the v1.0 FAR-CORE-009 proof
depends on comparing completions compatible with *observed* finite-panel claims.
An additive Lean lemma explicitly quantifies an arbitrary observed predicate and
constructs two extensions that preserve that predicate on-panel and disagree
off-panel. It does not alter the original theorem statement or frozen evidence.

**Remaining known gaps:** source-level locking cannot prove prose-to-elaborated-type
equivalence. In particular 006–008, 010 and 012 require formal-language or
scope-explicit mathematical bridges if their broader prose is to receive stronger
mechanization assurance. FAR-CORE-013 is definitional by construction, not an
unproved metaphysical claim.

## Independent checks and failure boundaries

- Hosted FAR-CORE formalization run `43879761479` on initial patch head
  `f5c5c59b569e1ce549aeb33a2fdc8ae7d9326fc3`: **success**.
  The logged targeted Python run completed **12 tests**, including all four
  proposition-lock tests; Lean 4.19.0 compilation, declared transitive axiom
  checks and generated-report checks passed.
- Hosted general Lean mechanization run `43879761411` on that same initial
  head: **success**.
- The additive FAR-CORE-009 lemma and regenerated module inventory passed
  hosted FAR-CORE formalization run `43881439555` at commit
  `352c103b0c72e453116c3b0bd7dae5e5eca3d9e5`, including Lean 4.19.0
  compilation and 12 targeted Python tests. This is machine assurance for the
  encoded proposition, not an independent evaluation of the prose claim.
- No I2/I3 isolation or independent mathematical review has been obtained.
  A second reviewer must not be simulated by another prompted response.
- No complete raw elaborated-expression comparison to a separately authored
  theorem specification has been executed. Do not call `LIM-052` or `LIM-053`
  closed on the basis of the source lock.
- No claim of novel mathematics, cross-domain universality, objective contract
  correctness, real-world utility, or general autonomous-agent reliability follows.

## Governance disposition

All findings are **Research**, with unchanged governing theory and evidence
status. Negative and partial results remain explicit. The known proof-fidelity
work remains open beyond the source-lock mitigation. Preserve all historical
and frozen artifacts and complete normal exact-head review and protected
checks before any authorized merge.
