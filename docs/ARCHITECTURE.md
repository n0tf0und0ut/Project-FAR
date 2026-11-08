# Project FAR Architecture

## Purpose

This document defines the architectural organization of Project FAR.

Its purpose is to describe the relationships among the major subsystems of the project.

Unless explicitly stated otherwise, every subsystem shall conform to the architectural principles established herein.

---

# Architectural Principles

Project FAR is organized as an acyclic dependency graph.

Foundations and shared theory provide prerequisites for framework-specific material.

Frameworks may specialize shared theory, but they shall not contradict it.

Methodology, validation, examples, and research may depend on canonical theory and frameworks, but canonical theory shall not depend on exploratory research.

Circular dependencies are prohibited.

---

# Canonical Dependency Layers

## Layer 1 — Foundations

Foundations establish motivation, assumptions, scope, and scoped representation/contract investigations.

Canonical theory may depend on foundations.

---

## Layer 2 — Shared Theory

Shared theory is governed by [Project FAR Core Theory v1.1](../theory/theorems/Project-FAR-Theory-Closure-v1.1.md) (`PROJECT-FAR-CORE-THEORY-1.1`): declared comparison contracts induce behavior maps, factorization tests, observational equivalence and quotients, and scoped invariance/common-theory results. It supplies no contract-free primitive inventory. The v1.0 theory is preserved as historical provenance, not current authority.


Shared theory contains canonical definitions, axioms, semantics, operators, notation, theorems, proofs, and consistency material.

Shared theory depends only on foundations and earlier shared-theory prerequisites.

---

## Layer 3 — FARA

FARA defines Project FAR's selected finite explicit auditable representation target. Its schema roles and accepted kernel are engineering commitments, not a universal source ontology.

FARA depends on foundations and shared theory.

---

## Layer 4 — FAR

FAR defines contract freezing, mapping, factorization/collision testing, relative minimization, and loss-reporting methodology using FARA where selected.

FAR depends on foundations, shared theory, and FARA.

---

## Layer 5 — FARO

FARO defines downstream operations for executing, materializing, comparing, auditing, transforming, and reporting reasoning representations and contract-relative results.

FARO depends on foundations, shared theory, FARA, and FAR.

---

## Layer 6 — Methodology, Examples, Research, and Papers

Methodology documents define project procedures and validation standards.

Examples illustrate use of the framework.

Research records exploratory work and shall not be treated as canonical until promoted to the appropriate canonical location.

Papers present publication-oriented syntheses of mature material.

---

# Dependency Graph

```text
foundations/
  ↓
theory/
  ↓
frameworks/FARA/
  ↓
frameworks/FAR/
  ↓
frameworks/FARO/
  ↓
methodology/, examples/, research/, papers/
```

This is a conceptual dependency graph. It does not assert that all downstream framework operations are production-ready. Consult [current project status](project-status.md) and [canonical framework boundaries](governance/framework-boundaries.md) for accepted scopes and implementation limits.

---

# Repository Organization

Project-FAR/

docs/

foundations/

theory/

frameworks/

methodology/

examples/

research/

tests/

papers/

archive/

.github/

---

# Design Goals

The architecture shall satisfy:

- modularity;
- extensibility;
- minimal coupling;
- explicit dependencies;
- formal rigor.

Future subsystems shall integrate within this architecture rather than modifying its foundational layers.

---

# Version 1.0 Repository Architecture

Project FAR now uses a permanent Version 1.0 repository architecture with one canonical location for each class of document.

## Structural Decisions

- Project governance and navigation documents are canonical under `docs/`.
- Foundational motivation, assumptions, primitives, representations, and foundational investigations are canonical under `foundations/`.
- Shared formal theory is canonical under `theory/`.
- FAR, FARA, and FARO are framework-specific and are canonical under `frameworks/`.
- Proof, validation, falsification, and comparison methods are canonical under `methodology/`.
- Exploratory material is maintained under `research/` and is not canonical until promoted to the appropriate canonical location.
- Meaningful superseded material is retained under `archive/`.
- Exact duplicate empty placeholders were removed.

## File Move Plan Executed

- Root project documents moved into `docs/`: architecture, roadmap, project status, changelog, and decision log.
- Former top-level FAR, FARA, and FARO directories moved into `frameworks/FAR/`, `frameworks/FARA/`, and `frameworks/FARO/`.
- Former top-level validation material moved into `methodology/validation/`.
- Former canonical methodology material moved into `methodology/proof-standard/`.
- Former root-theory foundation material moved into `foundations/primitives/` and `foundations/investigations/`.
- Former meta-theory content was merged into canonical `theory/`, `foundations/`, `methodology/`, and `research/` areas.
- Superseded meta-theory orientation and dependency-principle documents were archived under `archive/meta-theory/`.
- Research files were organized into `research/notes/`, `research/bibliography/`, and `research/open-problems/`.
- Flat theory files were organized into the canonical `theory/definitions/`, `theory/axioms/`, `theory/semantics/`, `theory/operators/`, `theory/notation/`, `theory/theorems/`, `theory/proofs/`, and `theory/consistency/` hierarchy.

## Simplification Review

A follow-up self-review simplified the refactor without changing the architecture:

- Removed unnecessary `core-` prefixes from canonical theory filenames while keeping the same canonical theory hierarchy.
- Archived the older general proof-standards document under `archive/superseded/methodology/` because the more specific Canonical Proof Standard is the active methodology document.
- Removed empty duplicate validation placeholders that did not contain meaningful content.
- Kept `.gitkeep` files only where they preserve required empty architecture directories.
