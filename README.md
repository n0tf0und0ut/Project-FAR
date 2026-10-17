# Project FAR

[![Release v1.0.0](https://img.shields.io/github/v/release/notfoundout/Project-FAR?include_prereleases&label=release)](https://github.com/notfoundout/Project-FAR/releases/latest)
[![Verify Theory](https://github.com/notfoundout/Project-FAR/actions/workflows/repo-health.yml/badge.svg)](https://github.com/notfoundout/Project-FAR/actions/workflows/repo-health.yml)

Project FAR is a framework for representing, analyzing, and comparing structured, explicit, auditable reasoning under declared contracts.

## Latest release: v1.0.0

The latest published GitHub repository release is [v1.0.0](https://github.com/notfoundout/Project-FAR/releases/tag/v1.0.0). The executable package metadata currently declares a separate installable version. These are separate version surfaces: the GitHub release records the published repository release, while package metadata governs the installable software version.

The current governing theory is `PROJECT-FAR-CORE-THEORY-1.1`.

> **NONTRIVIAL CONTRACT-FREE MINIMAL ARCHITECTURE IS IMPOSSIBLE; CONTRACT-RELATIVE SUFFICIENCY AND A UNIQUE MINIMAL OBSERVATIONAL QUOTIENT ARE PROVED.**

For a fixed exact comparison contract, a representation is sufficient exactly when declared behavior factors through it. The contract induces a unique least-informative observational quotient up to isomorphism. No single representation is simultaneously least-informative sufficient for every observation contract on a nontrivial domain, although identity can be sufficient for all such contracts on fixed `X`.

The v1.1 correction also separates exact common theory from frame-relative residue: `T_{L,J,I}` is indexed by language, interpretation profiles/models, and target class; `T_{L,J,I} \ Cn_L(Γ)` is additionally indexed by frame. `Γ` alone does not change exact `T` when the interpreted models are fixed.

Project FAR therefore closes as a **contract-relative audit discipline**, not as a universal inventory of reasoning primitives.

Mathematically, the proved core instantiates standard kernel-factorization and quotient results; several formalized claims (FAR-CORE-010 frame independence, FAR-CORE-013) hold definitionally and FAR-CORE-007/008 compare declared counts. See the [calibration audit](docs/audits/far-core-epistemic-calibration-v1.0.md) before reading the verdict above as a deep or novel result.

## Assurance state

The W1-labelled sealed review, performed by a single OpenAI Codex agent ([LIM-035](docs/governance/limitations-register.md)), returned 14 `PROVED`, 0 `REFUTED`, 0 `OPEN`, and 0 `UNDERDETERMINED` under its exact scopes; no theorem correction was required. Its evidence is I1 claimed isolation: repository access was prohibited by instruction but not technically prevented. External independent validation requires I3 evidence, which W1 does not supply. Novelty and priority were not established.

`PCA-W2-PROOF-ASSISTANT-FORMALIZATION` is complete: all 14 governed claims are `FORMALIZED` under pinned Lean 4.19.0, with zero partial obstructions and zero contradiction/reopen outcomes. FAR-CORE-014 includes the bounded unit-free MLL witness bridge, and exact transitive kernel assumptions are runtime-audited rather than inferred from CI success.

`PCA-W3-CONTRACT-SCHEMA` is complete: `far-ir/2.0` is a versioned comparison-contract successor with explicit contract/scope/provenance/failure fields, finite-explicit factorization/collision/quotient verification, loss-explicit migration from v1, and registered conformance fixtures. `far-ir/1.0` remains unchanged and is not silently reinterpreted.

`PCA-W4-DOMAIN-CONTRACTS` is complete at its recorded finite-explicit scopes: six independently motivated native comparison dimensions were frozen before controlled mapping; each domain has one checked lossy collision and one checked repaired factorization. The mappings and evaluations remain project-authored and do not establish external-investigator independence, novelty, minimal repair, or open-domain completeness.

`PCA-W5-APPROXIMATION-AND-COST` is complete at its frozen finite-explicit operational scope. The additive `far-ir/2.1` verifier checks exact-rational metric/loss/reference/tolerance semantics, randomized decoders, multidimensional product cost orders, Pareto minima versus least elements, and zero-loss recovery. It does not select a universal scalar cost or unique optimum.

`PCA-W6-EMPIRICAL-AUDIT-UTILITY` is complete at its preregistered bounded internal controlled-artifact scope. Across six W4 repaired controls and six deterministic representation-collision mutants, the schema-only baseline detected `0/6` mutants while the FAR semantic audit detected `6/6`, accepted `6/6` clean controls, and agreed with a separately implemented Project-FAR-authored table-only collision oracle on `12/12` primary records. The six frozen native W4 lossy controls were separately recomputed. The mutation was constructed to be exactly the collision the verifier checks, so this is a regression control rather than an estimate of detection power, and the baseline verifier recomputes only records that declare checked evidence ([LIM-047](docs/governance/limitations-register.md)). This is an exact all-items result for that finite corpus and defect class only: human disagreement reduction remains `UNDERDETERMINED` and external real-world utility remains `OPEN`.

These are separate assurance dimensions. Independent review does not imply novelty; Lean formalization does not imply empirical utility, efficiency, open-domain universality, or product readiness; schema/software conformance does not establish application correspondence; W6 machine controls do not establish human or external effectiveness.

For what these labels do and do not mean across claims, read the [FAR core epistemic calibration audit](docs/audits/far-core-epistemic-calibration-v1.0.md). It is a non-authoritative Research calibration that changes no claim status, and it records that much of the core mathematics instantiates standard patterns (Blackwell comparison, minimal sufficient statistics, Myhill-Nerode, coalgebraic minimization, abstract interpretation), that `14/14 FORMALIZED` is a mechanization-status label rather than fourteen deep or novel results, and that foundational mathematical novelty, external independence, empirical utility, and commercial value are all unestablished.

Project FAR also provides an additive [`far-epistemic/1.0` learning interchange](docs/specification/far-epistemic-learning-v1.md) for provenance-bound beliefs, predictions, decisions, canonical FAR-ELENCHUS-1.0 sessions, typed causal models, outcomes, deterministic scoring, and evidence-linked error-driven revision. It is an application-layer contract and does not alter FAR Core or reuse approximation/provenance cost as probability or utility.

Canonical links:

- [Corrected core theory v1.1](theory/theorems/Project-FAR-Theory-Closure-v1.1.md)
- [Machine-readable v1.1 claim ledger](theory/terminal/project-far-core-theory-v1.1.json)
- [v1.1 correction acceptance](docs/governance/project-far-theory-closure-acceptance-v1.1.md)
- [W1 independent-review promotion](docs/governance/pca-w1-independent-review-promotion-v1.0.md)
- [Machine assurance ledger](theory/evaluation/far-core-assurance-v1.0.json)
- [W2 formalization status](docs/governance/pca-w2-formalization-status-v1.0.md)
- [W3 contract-schema status](docs/governance/pca-w3-contract-schema-status-v1.0.md)
- [W4 domain-contract status](docs/governance/pca-w4-domain-contracts-status-v1.0.md)
- [W5 approximation/cost status](docs/governance/pca-w5-approximation-cost-status-v1.0.md)
- [W6 bounded audit-utility status](docs/governance/pca-w6-empirical-audit-utility-status-v1.0.md)
- [Epistemic assurance acceptance](docs/governance/far-epistemic-assurance-promotion-acceptance-v1.0.md), [specification](docs/specification/far-epistemic-assurance-1.0.md), and [hostile-source boundary](methodology/hostile-source-boundary.md)
- [Canonical W1–W6 claim/evidence matrix](docs/governance/w1-w6-claim-evidence-matrix-v1.0.md)
- [FAR core epistemic calibration audit](docs/audits/far-core-epistemic-calibration-v1.0.md) (non-authoritative Research calibration)
- [Governed research corpus](research/corpus/README.md) and [generated current research frontier](docs/research/current-research-frontier.md) (non-authoritative Research synthesis)
- [External Falsification and Replication program](docs/governance/external-falsification-and-replication-program-v1.0.md) and its [comparator amendment v2.0](docs/governance/external-falsification-and-replication-comparator-amendment-v2.0.md)
- [W6 execution and results](docs/research/pca-w6-empirical-audit-utility/02-execution-and-results.md)
- [`far-ir/2.1` approximation/cost specification](docs/specification/far-ir-2.1-approximation-cost.md)
- [W4 finite-explicit results](docs/research/pca-w4-domain-contracts/02-results.md)
- [`far-ir/2.0` contract specification](docs/specification/far-ir-2.0-contract.md)
- [Canonical project status](docs/project-status.md)
- [Roadmap](docs/ROADMAP.md)
- [Historical v1.0 core theory](theory/theorems/Project-FAR-Theory-Closure-v1.0.md), preserved byte-for-byte at SHA-256 `b7cbd28d54686da33773a66edf9af9480044ffaabfeb83cfa4bfc1a12fe862a5`

## Post-closure phase

`POST-CLOSURE-001` is complete at all six registered workstream scopes.

- `PCA-W0-REPOSITORY-CONFORMITY`: complete.
- `PCA-W1-INDEPENDENT-REVIEW`: complete.
- `PCA-W2-PROOF-ASSISTANT-FORMALIZATION`: complete, 14/14 formalized.
- `PCA-W3-CONTRACT-SCHEMA`: complete.
- `PCA-W4-DOMAIN-CONTRACTS`: complete at six finite-explicit domain scopes.
- `PCA-W5-APPROXIMATION-AND-COST`: complete at its finite-explicit operational scope.
- `PCA-W6-EMPIRICAL-AUDIT-UTILITY`: complete at its bounded internal controlled-artifact scope.

No W7 is registered by `POST-CLOSURE-001`. The separate successor `EXTERNAL-FALSIFICATION-AND-REPLICATION-001` is now preregistered, with no test executed. Its [comparator amendment v2.0](docs/governance/external-falsification-and-replication-comparator-amendment-v2.0.md) replaces the confounded human-disagreement, field-utility, and cost tests with three-arm versions whose primary contrast is FAR against a generic table-consistency checker; OP-28 remains open until its external/human evidence is actually collected and passes the frozen criteria.

Core theory reopens only for a reproducible contradiction to a stated premise, proof step, theorem, or derivation.

## W4–W6 result boundaries

`far-ir/2.0` explicitly represents contract identity/version, source/case domain, required behavior, representation, decoder/factorization or collision evidence, observation contexts, typed outcomes including `Unknown`, observational equivalence/quotient evidence, admitted transformations/equivalences, interpretation profile, target/model class, frame, provenance/freeze metadata, failure reporting, and optional approximation/loss/cost declarations.

For finite explicit records, checked factorization, collision, and exact beta-kernel quotient claims are recomputed by the semantic verifier. A migrated `far-ir/1.0` record preserves the legacy primitive payload but remains `Unknown` and unfrozen for comparison semantics that v1 never represented.

W4 froze native contracts for formal logic, Bayesian/causal reasoning, argumentation, model-based reasoning, type theory, and proof theory before mapping them into `far-ir/2.0`. Across the six domains, deliberately lossy representations expose six checked consequence-affecting collisions, while explicit scoped repairs supply six checked finite factorization witnesses. Domain-specific recomputation and mutation controls supplement the generic v2 verifier.

W5 separately established finite-explicit approximation and product-cost-preorder semantics under `far-ir/2.1`; W4 supplies none of those choices implicitly.

W6 then tested one preregistered defect class using the six W4 repaired records as negative controls, deterministic representation-collision mutants as positive cases, a schema-only syntactic baseline, and a separate table-only oracle. The result is exact for that project-authored finite corpus and does not estimate population performance or human reviewer benefit.

The existing Phase 3 `far-ir/1.0` mechanization remains a historical/current MVP for its stated reasoning-document interchange scope. It is not redefined by v2 or v2.1.

## Framework roles

The authoritative dependency order is **foundations → shared theory → FARA → FAR → FARO**.

- FARA: formal/schema representation layer. `FARA-FORMAL-KERNEL-001` remains the accepted bounded formal-kernel promotion at its stated scope; the former seven candidate primitives are schema/contract roles, not globally necessary primitives.
- FAR: contract-relative methodology and audit protocol.
- FARO: downstream execution, comparison, materialized views, audit, and reporting. This role definition is not implementation, product, external-validation, or deployment readiness.
- FARE: requirement-driven mathematical support.
- FARM: governance/change coordination.

Construct, Differentiate, and Restrict are workflow verbs. Resolve and Ω are derived. No global primitive count or operator basis is claimed.

## Historical boundaries

The historical UPP proposition remains not refuted, but its frozen derivation is defective and the theorem is not established. Its artifacts are preserved as history and are not current theorem authority.

Historical bounded-program status remains historical only. PR #453 remains a noncanonical Research record at its exact bounded scope. Preserved SWE-agent, REP, ADJ, W3.5, CRE, FARA-kernel, comparative-representation, and external-system records likewise retain only their original scopes. The frozen SWE-agent v2 comparison observed 0/2 resolved runs for v1.0.0 and 0/2 for v1.0.1 on one task; its recorded result is `no_observed_resolution_difference` and its bounded case decision is `REVIEW_REQUIRED`. That bounded observation does not establish equivalence, superiority, safety, readiness, or general performance. No finite execution establishes open-domain universality or commercial value.

## Certification and architecture navigation

- [Repository certification governance](docs/governance/repository-certification-standard.md)
- [Repository certification inventory baseline](docs/audits/repository-certification-inventory-audit.md)
- [Semantic certification baseline](docs/audits/semantic-certification-report.md)
- [Canonical vocabulary index](docs/glossary/canonical-vocabulary-index.md)
- [Repository architecture certification](docs/audits/repository-architecture-certification-report.md)
- [Documentation standardization report](docs/audits/documentation-standardization-report.md)
- [Repository domain registry](docs/architecture/repository-domain-registry.md)
- [Repository compliance enforcement report](docs/audits/repository-compliance-enforcement-report.md)
- [Independent repository certification audit](docs/audits/independent-repository-certification-audit.md)
- [Repository certification status](docs/certification/repository-certification-status.md)

## Validation

Theory-closure validation:

```bash
python tools/check_project_far_theory_closure.py
```

W2 formalization alignment:

```bash
python tools/check_far_core_v11_formalization.py
python -m unittest tests.test_far_core_v11_formalization
```

W3 contract-schema conformance and current `far-ir/2.0` verification ([current verification rule](docs/specification/far-ir-2.0-current-verification.md): `PROVED`/`REFUTED` require checked evidence):

```bash
python -m mechanization.far_mechanization.contract_conformance
python -m mechanization.far_mechanization.contract_conformance --manifest conformance/far-ir-2.0-current/manifest.json
python -m unittest tests.test_far_contract_v2 tests.test_far_contract_v2_strict tests.test_far_contract_v2_errata1 tests.test_contract_v2_verifier_authority
```

W4 domain-contract recomputation:

```bash
python tools/check_pca_w4_domain_contracts.py
python -m unittest tests.test_pca_w4_domain_contracts
```

W5 approximation/cost recomputation:

```bash
make pca-w5-check
```

W6 bounded audit-utility recomputation:

```bash
make pca-w6-check
```

Repository command center:

```bash
make research-check
make health-fast
make health
make docs-check
```

CI/repository consistency is assurance evidence for the encoded artifacts; it is not a substitute for mathematical proof or external empirical validation.

## Navigation

Start with [the canonical map](docs/CANONICAL_MAP.md), [project status](docs/project-status.md), [terminology authority](docs/glossary/canonical-terminology.md), [framework boundaries](docs/governance/framework-boundaries.md), [claim-status matrix](docs/governance/claim-status-matrix.md), [theorem/proof register](docs/governance/theorem-proof-status-register.md), [limitations](docs/governance/limitations-register.md), and [open problems](docs/governance/open-problems-register.md).

Repository navigation continues through the [documentation index](docs/README.md), [foundations](foundations/README.md), [shared theory](theory/README.md), [frameworks](frameworks/README.md), [methodology](methodology/README.md), and [papers](papers/README.md).
