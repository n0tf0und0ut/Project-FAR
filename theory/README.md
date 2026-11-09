# Theory Index

This directory contains Project FAR's canonical shared theory. Research notes remain under `../research/`; framework-specific commitments remain under `../frameworks/`.

## Governing theory

- [Project FAR Core Theory v1.1](theorems/Project-FAR-Theory-Closure-v1.1.md) — current governed correction of the contract-relative representation, sufficiency, observational-quotient, invariance, and terminal-boundary results.
- [Machine-readable v1.1 core ledger](terminal/project-far-core-theory-v1.1.json) — current claim IDs, corrected scopes, dispositions, and assurance.
- [Permanent v1.1 regressions](evaluation/project-far-core-theory-v1.1-regressions.json) — countermodels preventing reintroduction of the FAR-CORE-004 and FAR-CORE-010 defects.
- [FAR-CORE multidimensional assurance ledger](evaluation/far-core-assurance-v1.0.json) — separates truth, narrative proof, independent review, Lean, empirical, novelty, and governance status.
- [FAR-CORE formalization ledger](evaluation/far-core-formalization-ledger-v1.0.json) — exact W2 prose/type/premise/declaration mapping and the reproducible FAR-CORE-014 obstruction.
- [Historical Project FAR Core Theory v1.0](theorems/Project-FAR-Theory-Closure-v1.0.md) — immutable historical base, preserved byte-for-byte at its recorded SHA-256 and superseded only as current authority.
- [Shared definitions](definitions/definitions.md) — canonical vocabulary used by the core and frameworks.

## Find the theory by question

| Question | Authoritative starting point | Check the scope |
|---|---|---|
| When does a representation preserve required distinctions? | [Core theory v1.1](theorems/Project-FAR-Theory-Closure-v1.1.md) and [formal definitions](definitions/definitions.md) | [Core v1.1 claim ledger](terminal/project-far-core-theory-v1.1.json) |
| What is the least-informative representation for a fixed exact contract? | [Observational-quotient results in core v1.1](theorems/Project-FAR-Theory-Closure-v1.1.md) | [Multidimensional assurance ledger](evaluation/far-core-assurance-v1.0.json) |
| What changed in v1.1 and why? | [v1.1 correction audit](../docs/audits/project-far-core-theory-v1.1-correction-audit.md) | [Permanent countermodel regressions](evaluation/project-far-core-theory-v1.1-regressions.json) and [acceptance](../docs/governance/project-far-theory-closure-acceptance-v1.1.md) |
| What was actually checked in Lean? | [W2 formalization status](../docs/governance/pca-w2-formalization-status-v1.0.md) | [Formalization ledger](evaluation/far-core-formalization-ledger-v1.0.json): inspect each prose/type/premise/declaration mapping. |
| What remains unproven or externally untested? | [Canonical project status](../docs/project-status.md) | [Limitations](../docs/governance/limitations-register.md) and [claim/evidence matrix](../docs/governance/w1-w6-claim-evidence-matrix-v1.0.md). |

Use these links as a **lookup**, not a replacement for the current theorem, proof objects, or accepted status. A kernel-checked counterpart can be narrower than its informal prose; do not treat the number of formalized declarations as evidence of novelty or empirical usefulness.

## Supporting areas

- `axioms/` — legacy and scoped axiom records; none overrides the core theory.
- `theorems/`, `proofs/`, and `proof-objects/` — theorem and proof artifacts at their recorded assurance.
- `evaluation/` — bounded protocols, historical programs, regression fixtures, and the post-closure assurance program.
- `independence/` — historical primitive-independence criteria and research artifacts.

## Reading order

1. `theorems/Project-FAR-Theory-Closure-v1.1.md`
2. `../docs/governance/project-far-theory-closure-acceptance-v1.1.md`
3. `../docs/audits/project-far-core-theory-v1.1-correction-audit.md`
4. `definitions/definitions.md`
5. `../docs/governance/framework-boundaries.md`
6. FARA, FAR, then FARO.

For provenance, reviewers of v1.1 should also retain access to the immutable v1.0 monograph and ledger.

## Canonical boundary

Shared theory depends on foundations and precedes FARA. FARA is a selected representation target; FAR and FARO are downstream methodology and operations. Historical v1.0 and UPP artifacts remain evidence and history, not current theorem authority. The non-independent hostile correction audit remains distinct from the later sealed W1 review, which is complete. The [W2 formalization status](../docs/governance/pca-w2-formalization-status-v1.0.md) records 14/14 governed claims as `FORMALIZED` under its exact pinned Lean 4.19.0 scopes; this does not imply independent external replication or that every formalized counterpart is as strong as the prose.
