# Documentation Index

Project-level documentation lives here. This directory provides orientation, governance, status, audit evidence, and navigation. Current canonical theory lives in `../theory/`; foundations live in `../foundations/`; exploratory work lives in `../research/` and is non-canonical unless separately promoted.

## Find what you need

| Your task | Start here | Boundary |
|---|---|---|
| Understand FAR in context | [Overview](OVERVIEW.md) and [educational example](../examples/simple-investigation.md) | Examples illustrate methods; they do not establish empirical performance. |
| Find the current governing theory | [Project status](project-status.md), then [core theory v1.1](../theory/theorems/Project-FAR-Theory-Closure-v1.1.md) | Historical v1.0 remains preserved, not current theory authority. |
| Find code and run tests | [Mechanization guide](../mechanization/README.md), [contributor guide](../CONTRIBUTING.md), and [repository health checks](maintenance/repository-health-checks.md) | Verification applies only to the encoded test/contract scope. |
| Trace a research result to evidence | [W1–W6 matrix](governance/w1-w6-claim-evidence-matrix-v1.0.md), [research index](../research/README.md), and [limitations](governance/limitations-register.md) | Research records and generated views cannot promote claims. |
| Determine where a concept belongs | [Canonical map](CANONICAL_MAP.md) and [domain registry](architecture/repository-domain-registry.md) | The map identifies authority; the domain registry controls repository placement. |
| Locate a specific file | [Generated repository index](planning/repository-index.md) | A file index is a discovery aid, not a status or acceptance decision. |

For the full repository entry point use the [root README](../README.md). For a documentation change, prefer improving an existing route over creating another competing index.

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
