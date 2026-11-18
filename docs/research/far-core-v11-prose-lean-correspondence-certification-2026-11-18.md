# FAR-CORE v1.1: prose-to-Lean correspondence certification obligations

**Status: Research — proposal and gap register, NOT independent certification.**  
**Baseline protected main:** `a9eb83eee705ba3e242b3f329712f6352761c6c1` (checked 2026-11-18).  
**Theory:** `PROJECT-FAR-CORE-THEORY-1.1`.  
**Historical source:** `theory/theorems/Project-FAR-Theory-Closure-v1.0.md` (preserved SHA-256 `b7cbd28d54686da33773a66edf9af9480044ffaabfeb83cfa4bfc1a12fe862a5`).  
**Corrections:** v1.1 §1 (FAR-CORE-004), §2 (FAR-CORE-010).  
**Current baseline:** `LIM-035`, `LIM-052`, `LIM-053` remain open at their recorded assurance scopes.  
**Existing external protocol:** EFR-001 / `EFR-R1` is preregistered and **not executed**. Its immutable experimental design is NOT amended by this Research document.

## Why name locks and kernel compilation are insufficient

There are three distinct propositions:

1. **Source stability:** a given declaration has not changed textually or elaboratively from a pinned baseline.
2. **Formal equivalence:** separately formulated formal propositions `P` and `Q` express mutually derivable consequences under exactly the same declared scope and assumptions. A Lean theorem `P ↔ Q`, or two implication proofs with transparent premise mapping, can certify this formal fact.
3. **Prose fidelity:** `P` faithfully expresses the *governing natural-language theorem*. This cannot be deduced from the Lean kernel; it requires independent, source-grounded mathematical interpretation and adjudication.

A successful check of (1) is **not** a check of (2) or (3). A check of (2) that reconstructs `P` by copying `Q` is circular as independent translation evidence. `#print axioms` establishes axiom dependencies, not the completeness of a prose translation.

A formal equivalence claim must fail closed if the intended prose theorem is ambiguous, under-specified, nonformalized, stronger than the Lean proposition, or only supported by an added bridge premise. Do not edit the original theorem or silently move its quantifier domain to obtain a passing check.

## Independence and execution order

This is a **potential correspondence adjunct**, not a substitute for or alteration of the frozen `EFR-R1` test. The existing EFR intake issues #476, #477, and #478 remain the operational entry points. Only an independently controlled custodian may prepare and seal a permitted R1 input and approve eligible teams. Public repository issue or PR links must not be sent as first contact to prospective clean-room evaluators.

A correspondence-certification study requires this sequence:

1. **Identity and exposure screen.** Two technically qualified teams from distinct external organizations; neither controlled by FAR or an author of the target artifacts. A custodian logs exposure, conflicts, tools, compensation, and restrictions. An already-exposed team cannot claim I3 merely by beginning a new chat or repository checkout.
2. **Blind statement reconstruction.** The custodian distributes only v1.1-governed theorem statements, definitions, assumptions, and exact scopes. Do **not** include v1.0/v1.1 proofs, W1 verdicts/reasoning, W2 Lean sources, the formalization ledger, this claim-to-Lean mapping, or the prior internal correspondence audit. Each team independently authors an explicit formal proposition for **all 14** claims, with quantifiers, carriers, assumptions, and claimed conclusion. They also record ambiguities and potential countermodels. The outputs are signed, hashed, timestamped, and sealed before comparison with FAR's Lean.
3. **Deductive replication.** Carry out `EFR-R1` exactly as preregistered; do not replace its accepted endpoints with correspondence measurements. Any new correspondence phase has its own separate preregistration and authorization before execution.
4. **Post-seal formal comparison.** Only after authorized unblinding, compare each independently authored proposition `P_i` with the pinned existing Lean proposition bundle `Q_i`. Bind *actual elaborated theorem types and transitive dependencies*, not symbol names or source headers. Prove both `P_i → Q_i` and `Q_i → P_i` under explicit shared premises, or exhibit the smallest countermodel / missing hypothesis. Test replacement by `True`, narrowed types, vacuous antecedents, changed definitions, extra axioms, deleted witness cases, and swapped quantifiers.
5. **Adjudication.** An independent mathematical adjudicator checks that the sealed `P_i` actually follows the governing prose and that no formal bridge smuggles in a stronger premise. Adjudication must not substitute new definitions for governing definitions to make an equivalence pass. Preserve disagreements and negative findings.
6. **Certification.** Publish exact source SHA, reviewer and organization independence disclosures, packet manifest, sealed independent `P_i` expressions, fully elaborated `Q_i` types, explicit universe/choice/extensionality map, Lean 4.19.0 build logs, two-way formal bridges, test/countermodel evidence, and claim-specific verdicts. No aggregate `14/14` certification unless **every** exact-scope claim passes all three layers. A proof of a weaker version remains a useful partial result, not an equivalence certificate.

**Prohibited shortcuts:** asking the same model twice, showing the W2 Lean declarations in stage one, reusing FAR's formalization ledger as the independent specification, treating Codex comments or source-lock tests as I3 certification, self-signing as an external custodian, or retrospectively changing a frozen EFR endpoint.

## Claim-specific verification obligations

The **source** column points to the governing proof-bearing monograph for adjudicator access; a blinded reviewer must receive a custodian-extracted **statement-only** packet, not this table or the proof-containing file. Classifications below are research risk assessments, not external verdicts.

| Claim | Governing theorem location | Minimum exact correspondence obligation | Current blocker / adversarial question |
|---|---|---|---|
| 001 | v1.0 Theorem 1 | For every fixed total `C=(X,T,V,obs)`, prove equivalence of reachable-image decoder factorization, kernel refinement, and pointwise test agreement. | Confirm that `beta:X→V^T` and decoder on `rho[X]` preserve all typed observations; choice use explicit. |
| 002 | v1.0 Theorem 2 | Prove quotient sufficiency; existence **and uniqueness** of factor from any sufficient image; minimality iff kernel equality; isomorphism; finite image cardinal lower bound. | Existing Lean universe bounds (`Type u`) and cardinal corollary must match the actual prose quantifiers; a surjection is not an automatic statement about arbitrary finite/universe classes. |
| 003 | v1.0 Theorem 3 | Formalize semantic test closure under every admitted action and proof of observational compatibility and descended quotient action. | Test absence of closure with a concrete countermodel; do not silently replace `∀ action` by one named action. |
| 004 | **v1.1 §1** | On any domain with two distinct cases, no single representation is least-informative sufficient for **all** contracts. Separately prove the identity map is universally sufficient. | The false stronger assertion 'no representation is sufficient for all contracts' must be rejected. |
| 005 | v1.0 Theorem 5 | For arbitrary admitted `G₁ ⊆ G₂` and arbitrary properties, show invariant-family antitonicity. | Verify transformation composition or bijectivity is not an undeclared extra premise. |
| 006 | v1.0 Theorem 6 | Prove transport of arbitrary named finitary operations **and relations**, injective encoding, image restriction, inverse recovery, and isomorphism. | The further claim 'encoding does not establish *native* common structure' is a non-entailment; define 'native' and give an independent countermodel or mark **NOT FORMALIZED AS STATED**. |
| 007 | v1.0 Theorem 7 | Derive both direct and reified primitive signatures from an explicit counted presentation grammar, and prove a faithful decoder back to the original relation. | Lean currently compares **stipulated** count profiles. Merely declaring 1 versus 3 is not a syntax-derived invariance refutation. |
| 008 | v1.0 Theorem 8 | State the admitted finite family, tagged dependent argument domain, split/combination inverse, and syntax-derived primitive operator counts. | Lean currently stipulates 2 versus 1; the general finite-family claim and heterogeneous-arity encoding need exact scope reconstruction. |
| 009 | v1.0 Theorem 9 | For every proper finite panel **and every observed on-panel predicate**, exhibit two compatible total completions that differ outside it. | The main-branch Lean declaration lacks a parameter for actual observed truth; separate unmerged PR #679 has an additive lemma, not yet accepted main authority. |
| 010 | **v1.1 §2** | Formulate `Th_L(M_i)` using first-order model semantics and `Cn_L(Γ)` using the declared consequence relation. Prove exact theory independent of `Γ` when `L,J,I,M_i` stay fixed; test residue dependence. | Current Lean abstracts both truth and consequence relations; frame-independence is definitional and residue change requires witness hypotheses. No full first-order correspondence certificate exists. |
| 011 | v1.0 Theorem 11 | Prove that omission of a realizable consequence-affecting context `c` creates a representation collision that refutes exact sufficiency. | Require an actual declared differing behavior, not merely differing metadata. |
| 012 | v1.0 Theorem 12 | For **any** declared test on which determinate absence and epistemic Unknown differ, show a sufficient representation distinguishes the cases. | Current Lean proves a single typed outcome-function instance; a quantified test-family bridge is not independently certified. |
| 013 | v1.0 Theorem 13 | Under the explicit *canonical* definition `Ω(z)=Rep(Class_κ(z))`, prove elimination for every declared downstream rule `r`. | Correctly classify this as **definitional**, not an independently established fact that all conceivable Ω state is reducible. |
| 014 | v1.0 Theorem 14 | Recover precise SSS-1/2/3 state, transition and decoder classes, certify the concrete MLL witnesses, prove restricted projected-decoder failure and conditional hyperedge/frontier factorization. | Do not promote a bounded restricted-decoder counterexample into a universal statement against binary relations or all decoders. |

## Mechanically checkable acceptance matrix

For every `FAR-CORE-NNN`, independently record:

- `source_identity`: governing statement and correction hashes, line/section locator.
- `independent_statement`: sealed explicit mathematical statement, exact quantifiers and types, author/organization, pre-unblind timestamp and signature.
- `encoded_assumptions`: all extra/nondefinitional hypotheses, including empty domains, accessible universe levels, choice, classical axioms, propositional/function extensionality.
- `lean_formulation`: fully elaborated proposition `Q`, dependent definition closures, and target commit.
- `bridge_forward`: independently checked `P → Q` proof receipt, or a concrete witness of failure.
- `bridge_backward`: independently checked `Q → P` proof receipt, or a concrete witness of failure.
- `definition_fidelity`: independent review of every imported semantic definition and correspondence to the governing definitions; a `True ↔ True` bridge does not pass when the prose claim is nontrivial.
- `failure_modes`: counterexamples for dropped hypotheses, changed quantifier domains, invalid theorem identities, and weak/trivial statements.
- `review_disposition`: one of `CERTIFIED_EXACT`, `CERTIFIED_CONDITIONAL`, `STRICTLY_WEAKER`, `STRICTLY_STRONGER`, `INCOMPARABLE`, `UNFORMALIZABLE_AS_STATED`, `INVALID_EVIDENCE`, `UNRESOLVED`. **Only** `CERTIFIED_EXACT` counts toward exact correspondence.

An exact claim counts as **certified** only with separate external semantic attestations, two-way Lean proof receipts under aligned assumptions, authenticated independence and intact seals. Unknown is not PASS. Proof-assistant kernel validity cannot upgrade an internal semantic mapping to I3.

## Present disposition (not simulated certification)

| Gate | Current result |
|---|---|
| 14 governing theorem statements available on protected main | YES |
| W2 Lean counterparts present | YES (governed mechanization claims, not complete prose equivalence) |
| Documented weaker/narrower counterparts | YES — see `LIM-052` |
| Source-level header lock in PR #679 | PROPOSED, not on protected main |
| Two independently qualified, eligible I3 teams with sealed stage-one `P_i` | **NO EVIDENCE / NOT EXECUTED** |
| Independent custodian seal and adjudication of semantic fidelity | **NO EVIDENCE / NOT EXECUTED** |
| Two-way formal bridges `P_i ↔ Q_i` for all 14 exact-scope claims | **NOT EXECUTED** |
| Independent exact prose–Lean equivalence certification | **NOT ESTABLISHED** |

This is a **Research proposal** for the missing correspondence question. It is not a new frozen EFR preregistration, not an amendment of `EFR-R1`, not a team assignment, and not permission to expose clean-room candidates to withheld material. Any independent experiment extending EFR's endpoints must be separately governed and prospectively approved. Until then, the only defensible claim is that the present Lean formalizations prove their **encoded** statements under disclosed premises.
