# Documentation Index

Project-level documentation lives here. This directory provides orientation, governance, status, audit evidence, and navigation. Current canonical theory lives in `../theory/`; foundations live in `../foundations/`; exploratory work lives in `../research/` and is non-canonical unless separately promoted.

## Find what you need

Six routes lead to existing sources. Pick the question you are trying to answer; the linked documents retain their own status, scope, and authority.

| Reader goal | Start here | Follow through |
|---|---|---|
| **Understand FAR** | [Five-minute introduction](START_HERE.md) | [Plain-language overview](OVERVIEW.md); the example explains an idea, not experimental validation. |
| **Discover research** | [Research index by question](../research/README.md) | Open each study's protocol, recorded outcome, and reproduction instructions; Research placement grants no acceptance. |
| **Reproduce an experiment or check** | [Mechanization guide](../mechanization/README.md) | Follow a registered fixture or a study-specific README; record input, source version, execution, outcome, and limits. |
| **Assess results and evidence** | [Canonical project status](project-status.md) | [W1–W6 claim/evidence matrix](governance/w1-w6-claim-evidence-matrix-v1.0.md) and [limitations register](governance/limitations-register.md). |
| **Explore formal theory** | [Theory index by question](../theory/README.md) | [Core theory v1.1](../theory/theorems/Project-FAR-Theory-Closure-v1.1.md) and its assurance/formalization ledgers. |
| **Build or contribute** | [Contribution guide](../CONTRIBUTING.md) | [Mechanization guide](../mechanization/README.md), [architecture](ARCHITECTURE.md), and [repository health checks](maintenance/repository-health-checks.md). |

For **authority or ownership**, use the [canonical map](CANONICAL_MAP.md) and [domain registry](architecture/repository-domain-registry.md). For **an exact filename**, use the [generated repository index](planning/repository-index.md), which is a locator rather than an authority source. To check whether a beginner can navigate these routes, use the [reader-comprehension procedure](maintenance/beginner-comprehension-check.md). For **live PR and issue triage**, use the [read-only repository workboard](maintenance/repository-workboard.md), an advisory inventory rather than a merge gate or scientific status source.

### Follow an example through to evidence

A short route through a concrete verifier case:

1. Read the [receipt illustration and finite software example](START_HERE.md#see-an-actual-far-software-check); distinguish the fictional explanation from the registered case.
2. Inspect the [collision record](../conformance/far-ir-2.0/valid-collision.json) and the [current conformance manifest](../conformance/far-ir-2.0-current/manifest.json).
3. Use the [bounded contract-check instructions](../mechanization/README.md#run-a-bounded-contract-check) and inspect the [strict conformance tests](../tests/test_far_contract_v2_strict.py).
4. Interpret the observed result under the [W3 status](governance/pca-w3-contract-schema-status-v1.0.md) and [current project limits](project-status.md). A passing software check establishes neither source truth nor external effectiveness.

For a **negative empirical result**, go directly to the [workflow-efficacy pilot](../research/workflow-efficacy/KEYLESS-PILOT-RESULTS-V0.4.md), then follow its frozen protocol and verification references. Do not conflate that experiment with the separate, unexecuted historical-PR workflow study.

The root [README command center](../README.md) remains the repository entry point. This page and the research/theory indexes are navigation only; they do not duplicate or promote canonical scientific claims.

## Current authority and status

- [Canonical map](CANONICAL_MAP.md) — canonical location map for major concepts and the controlling navigation surface for authority.
- [Project status](project-status.md) — current project-level governance and milestone status.
- [Central research program](governance/central-research-program.md) — terminal central-research answer and evidence discipline.
- [Core theory v1.1](../theory/theorems/Project-FAR-Theory-Closure-v1.1.md) — current corrected Project FAR Core Theory v1.1.
- [Historical core theory v1.0](../theory/theorems/Project-FAR-Theory-Closure-v1.0.md) — immutable historical base; preserved for provenance and superseded as current authority.
- [W1–W6 claim/evidence matrix](governance/w1-w6-claim-evidence-matrix-v1.0.md) — canonical W1–W6 claims, evidence, scopes, and prohibited promotions.
- [External falsification and replication program](governance/external-falsification-and-replication-program-v1.0.md) — separate post-W1–W6 program; external work is not established by internal repository validation.
- [Limitations register](governance/limitations-register.md) — current limitations.
- [Unresolved questions register](governance/unresolved-questions-register.md) — unresolved questions.

## Core documentation

- [`maintenance/agent-workflow-orchestration.md`](maintenance/agent-workflow-orchestration.md) — operational planning, subagent use, correction learning, task tracking, and verification guidance for repository assistants; not FAR authority.

- [Architecture](ARCHITECTURE.md) — repository architecture and structural decisions.
- [`architecture/far-subagent-execution.md`](architecture/far-subagent-execution.md) — provisional provider-neutral subagent execution architecture; no claim-promotion authority.
- `ROADMAP.md` — gated future work.
- `CHANGELOG.md` — chronological change history.
- `DECISION_LOG.md` — canonical project decision log.
- [Five-minute explanation](START_HERE.md) — first-time, nontechnical learning route; illustrative and non-authoritative.
- [Beginner comprehension check](maintenance/beginner-comprehension-check.md) — practical human-reader usability procedure, not research evidence.
- [Overview](OVERVIEW.md) — project overview.
- [`planning/repository-index.md`](planning/repository-index.md) — generated repository-wide artifact navigation; an index, not an authority source.
- `STYLE_GUIDE.md` — documentation style standards.
- `SEMANTIC_AUDIT.md` — repository-wide semantic consistency audit and dependency graph.
- `governance/repository-certification-standard.md` — frozen canonical Repository Certification Standard.
- `reports/foundation-health-verification.md` — bounded Foundation health-verification report.

## Related entry points

- [Repository entry point](../README.md) — repository-level command center.
- [Foundations](../foundations/README.md) — foundations index.
- [Shared theory](../theory/README.md) — theory index.
- [Frameworks](../frameworks/README.md) — FAR-family framework material.
- [Methodology](../methodology/README.md) — supporting proof, validation, falsification, and comparison methodology.
- [Research](../research/README.md) — non-canonical exploratory research index.
- [Central Research Program](governance/central-research-program.md) — terminal core answer and standards for post-closure assurance/application.

## Repository Certification navigation

- [Repository Certification Standard](governance/repository-certification-standard.md) — governing certification criteria and completion rule.
- [Repository Certification Inventory Audit](audits/repository-certification-inventory-audit.md) — inventory baseline, classifications, metrics, findings, and architecture map.
- [Canonical Vocabulary Index](glossary/canonical-vocabulary-index.md) — vocabulary navigation by reference to canonical definitions.
- [Semantic Certification Report](audits/semantic-certification-report.md) — semantic, terminology, glossary, reachability, and canonical-home audit report.
- [Repository Architecture Certification Report](audits/repository-architecture-certification-report.md) — architecture policy and discoverability audit.
- [Documentation Standardization Report](audits/documentation-standardization-report.md) — documentation structure and consistency audit.
- [Repository Certification Index](certification/README.md) — certification artifact navigation hub.
- [Repository Domain Registry](architecture/repository-domain-registry.md) — frozen authoritative registry of repository domains, responsibilities, roots, owners, and allowed artifact classes.
- [Repository Compliance Enforcement Report](audits/repository-compliance-enforcement-report.md) — compliance automation coverage and findings.
- [Independent Repository Certification Audit](audits/independent-repository-certification-audit.md) — preserved certification audit evidence; consult the current certification status before relying on its conclusion.
- [Root-of-Trust Audit 2026-09](audits/root-of-trust-audit-2026-09.md) — independent-oracle audit of the validators, reference verifiers, CI gates, and formalization claims, with repairs and residual limits (non-authoritative Research record).
- [Repository Certification Status](certification/repository-certification-status.md) — current repository-level certification decision. This status fails closed against unresolved merged-review reconciliation findings.

## Evaluation methodology navigation

These are bounded methodology/evidence surfaces. Their presence does not establish external validity.

- Preliminary external-validation methodology: `../theory/evaluation/external-validation-methodology.md`.
- Comparative-representation protocol: `../theory/evaluation/comparative-representation/protocol-v1.0.md`.
- Comparative-experiment registry: `../theory/evaluation/comparative-representation/experiment-registry.json`.

## Release navigation

- Current release record: [`releases/project-far-v1.0.0.md`](releases/project-far-v1.0.0.md).
- Previous maintenance release: [`releases/project-far-v0.3.1.md`](releases/project-far-v0.3.1.md).
- Internal-validation baseline: [`releases/project-far-v0.3.0.md`](releases/project-far-v0.3.0.md).

Release records are historical/version records; they do not override the current canonical theory, governance, claim/evidence matrix, limitations, or certification status.

## Supporting documentation

The following records are supporting or scoped surfaces. They do not replace the canonical map or current governance/status registers.

- Architecture records: [repository convergence](architecture/repository-convergence-2026-07-23.md), [terminology status](architecture/terminology-status-2026-07-23.md), [validation architecture](architecture/unified-validation-architecture.md), and [validator assurance](architecture/validator-assurance-hardening.md).
- Governance and operations: [CI responsibility matrix](ci/responsibility-matrix.md), [anti-self-validation clarification](governance/anti-self-validation-deduction-clarification.md), [fix-register control](governance/fix-register-control.md), and [repository-truth revalidation scope](governance/repository-truth-revalidation-scope.md).
- Interfaces and mechanization: [compare/adjudicate contract](interfaces/compare-adjudicate-v1.md), [scope boundary](interfaces/compare-adjudicate-v1-scope.md), and [mechanization capability statement](mechanization/capability-statement.md).
- Supporting methodology: [boundary discovery](methodology/boundary-discovery-program-v1.0.md), [comparative cost](methodology/comparative-cost-model-v1.0.md), [external observation](methodology/external-observation-contract-v1.0.md), [primitive necessity](methodology/primitive-necessity-and-reintroduction-protocol-v1.0.md), and the [proof-assurance taxonomy](proof-assurance-taxonomy.md).
- Planning records: [anti-self-validation implementation](planning/anti-self-validation-implementation-plan.md), [deduction-first roadmap](planning/deduction-first-proof-roadmap.md), and [external-validation convergence](planning/external-validation-convergence-plan-2026-07-23.md).
- Review and reusable controls: [S-core review package](review/s-core-w5-independent-proof-review-package-v1.0.md), [pipeline threat model](security/swe-agent-v2-pipeline-threat-model.md), [claim-ledger template](templates/claim-ledger-entry.md), and [S-core review form](templates/s-core-w5-independent-proof-review-form-v1.0.md).
- Registered comparative packages: [CRE-002-EXT-001-REP-001 preregistration](../theory/evaluation/comparative-representation/experiments/CRE-002-EXT-001-REP-001/preregistration.md) and [CRE-004-RUN-001](../theory/evaluation/comparative-representation/experiments/CRE-004/runs/CRE-004-RUN-001/README.md).

For any authority conflict, use `CANONICAL_MAP.md` and the applicable canonical governance/status register rather than this index.
