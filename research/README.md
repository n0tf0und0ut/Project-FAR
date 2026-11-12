# Research Index

Status: Research navigation; non-canonical

## Purpose

This file is the navigation entry point for exploratory and provisional work under `research/`.

## Authority boundary

The Repository Domain Registry defines `research/` as non-canonical exploratory/provisional material. Nothing indexed here becomes accepted theory, current governance, or claim authority merely by appearing in this directory or this index.

Use [`../docs/CANONICAL_MAP.md`](../docs/CANONICAL_MAP.md) to locate current canonical sources and [`../docs/governance/research-execution-charter.md`](../docs/governance/research-execution-charter.md) for research status and promotion rules.

## Browse the research by question

These are **research records**, including negative and bounded results. The short descriptions are navigation aids; open each linked study for the exact protocol, evidence hashes, execution conditions, and limitations. Use your browser's **Find in page** to locate a topic.

| Research question | Observed boundary | Evidence and reproduction |
|---|---|---|
| **Do additional agent workflow instructions improve one-shot repairs?** | The completed 60-run scripted pilot found control **11/30**, FAR **10/30**. No treatment advantage demonstrated. A separate historical-PR study remains unexecuted. | [Pilot result](workflow-efficacy/KEYLESS-PILOT-RESULTS-V0.4.md) · [study and verification guide](workflow-efficacy/README.md) |
| **Does a model improve tool routing over deterministic dispatch?** | In the registered bounded architecture-routing study, deterministic and declarative arms were **12/12** each; small-model routing was **9/12**. No general agent advantage follows. | [Protocol and execution instructions](architecture-routing/README.md) · [distinct-prompt v0.3 observations](architecture-routing/execution-observation-v0.3.md) |
| **Can a small tool-using agent reliably complete bounded tasks?** | The v0.3 authored simulation recorded **72/72** scored successes with zero unsafe writes. It is not a FAR-versus-control result or an external-world reliability estimate. | [Results v0.3](tool-agent-reliability/RESULTS-V0.3.md) · [protocol and replay route](tool-agent-reliability/README.md) |
| **Can numeric grounding prevent unsupported number releases?** | The live-pilot primary wrong-number-reduction gate failed; both arms had zero wrong numeric releases. Correct final outcomes were **8/16** control versus **12/16** treatment on a bounded source metric. | [Live pilot result](numeric-grounding/RESULTS-LIVE-V0.1.md) · [implementation and tests](numeric-grounding/README.md) |
| **Can an agent select justified actions when the input is underspecified?** | The initial small-model pilot produced **11/12** admissible suggestions, tying the constant `ASK_SCOPE` baseline. The later bounded investigation required controller intervention; general autonomy is unestablished. | [Dispatch and investigations](uncertain-routing/README.md) · [initial execution](uncertain-routing/execution-v0.1.md) |
| **Do bounded weight-space edits improve model reliability?** | The completed 432-generation pilot reported no improvement over simpler prompting. It did not qualify for production adoption. | [Experiment results](weight-space/RESULTS-V0.1.md) · [implementation, sources, and replay](weight-space/README.md) |

| **Does adding Graphify to ripgrep improve code-navigation answers for a small local model?** | On 12 frozen syntactic Python call-site questions (36 local-model runs), exact answers were **10/12** ripgrep, **6/12** Graphify, **11/12** combined. Combined model tokens were 5,754 vs 6,069 ripgrep; only one question improved and 11 tied. No end-to-end coding-agent advantage is established. | [Research-only report, raw receipts and limits](comparisons/ripgrep-graphify-retrieval-2026-11-12/README.md) |

### Other research areas

- `axiomatization/` — exploratory axiom and ontology research.
- `bibliography/` and `literature/` — source records.
- `comparisons/` — exploratory comparison studies.
- `discovery/` — discovery records.
- `foundations/` — research concerning foundations; not the accepted `../foundations/` domain.
- `methodology/` — research-stage methods, not governing methodology.
- `notes/`, `open-problems/`, and `proofs/` — notes, unresolved questions, and draft proofs.
- `validation/` — investigations and execution evidence.
- [Repository convergence and bounded commercial comparison](repository-convergence/2026-11-03/README.md) — a Research-only inventory with unresolved human/customer validation.

### Interpret a research record

Read **question → frozen protocol → executed inputs and outputs → verdict → counterexamples and limitations**. Before treating a statement as established, cross-check [canonical project status](../docs/project-status.md), the [canonical map](../docs/CANONICAL_MAP.md), and the relevant acceptance record. A locally reproduced result is not independent replication.

## Preservation rule

Research records may preserve superseded, failed, incomplete, or contradictory work for provenance. Their presence is evidence of research history, not evidence that their claims are accepted or current. Current status and authority must be read from the canonical map and applicable governance/status registers.
