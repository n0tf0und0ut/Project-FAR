# Contributing to Project FAR

## Purpose

Thank you for your interest in contributing to Project FAR.

Project FAR is a contract-relative research and software project for representing, analyzing, and comparing structured, explicit, auditable reasoning under declared contracts. It does not claim a universal minimal reasoning representation.

Contributions should strengthen the framework while preserving its logical consistency, minimality, and formal rigor.

---

# Before You Contribute

Before proposing changes, contributors should become familiar with the project.

Recommended reading order:

1. [Repository introduction](README.md) and [overview](docs/OVERVIEW.md).
2. [Current project status](docs/project-status.md) and [canonical map](docs/CANONICAL_MAP.md).
3. [Documentation index](docs/README.md) and the README for the affected domain.
4. [Research execution charter](docs/governance/research-execution-charter.md) and [PR review convergence policy](docs/governance/pr-review-convergence.md) before changes.
5. [Decision log](docs/DECISION_LOG.md) for architecture and [limitations register](docs/governance/limitations-register.md) for scientific claims.

Automated contributors should follow their applicable runtime instructions: [Codex](AGENTS.md) or [Claude](CLAUDE.md). Those instructions do not override canonical governance.

---

# Guiding Principles

All contributions should follow these principles.

- Definitions precede conclusions.
- Simplicity is preferred over complexity.
- Reduction is preferred over expansion.
- Every concept has one canonical definition.
- New concepts require explicit justification.
- Formal claims should ultimately be supported by proof.
- Avoid circular dependencies.
- Preserve internal consistency.

---

# Repository Organization

| Directory | Purpose |
|-----------|---------|
| `docs/` | Project documentation |
| `theory/` | Formal theory |
| `frameworks/FARA/` | Architectural framework |
| `frameworks/FAR/` | Investigation methodology |
| `frameworks/FARO/` | Reasoning operations |
| `examples/` | Worked examples |
| `methodology/validation/` | Validation studies |
| `research/` | Active research |
| `papers/` | Publications |

---

# Canonical Definitions

Use [canonical terminology](docs/glossary/canonical-terminology.md) for names, meanings, ownership, and epistemic class. Consult [formal definitions](theory/definitions/definitions.md) for the corresponding formal treatment. Other documents should link to the canonical source rather than redefine a term. New concepts and changes in authority require the applicable governed process.

---

# Architectural Contributions

Architectural changes should satisfy all of the following:

- Address a demonstrated limitation.
- Preserve or increase expressive power.
- Minimize additional complexity.
- Avoid introducing circular dependencies.
- Remain consistent with existing definitions.

Whenever possible, derive existing concepts before introducing new primitive concepts.

---

# Formal Theory

Changes to the formal theory should identify dependencies where appropriate.

Examples include:

- Definitions
- Axioms
- Propositions
- Lemmas
- Theorems
- Proofs

The goal is to preserve the meaning, premises, scope, provenance, and stated limitations of each claim. Do not promote an illustrative example, passing test, or research artifact into accepted theory without the governed acceptance process.

## Verify a contribution

From the repository root, use the existing checkers appropriate to the changed files:

```bash
make docs-check
make health-fast
```

For a narrow documentation update, [repository health checks](docs/maintenance/repository-health-checks.md) explain the link, Markdown, orphan-document, and broader checks. Investigate failing checks; do not suppress them to make a PR pass.

Submit a task-scoped pull request with the reason for the change, affected canonical sources, validation evidence, and any unresolved limitations. Follow [PR review convergence](docs/governance/pr-review-convergence.md); independent review and protected-main merge authorization remain separate obligations.
