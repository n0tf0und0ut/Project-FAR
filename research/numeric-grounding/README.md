# Numeric metric grounding — executable Research sidecar v0.1

**Status: Research.** This is a bounded software control over *declared* measurements, not an accepted FAR core theorem, certified business ontology, model-evaluation result, general agent-reliability result, or production answer service.

## Question and rationale

Can a registered metric vocabulary with fixed executable meanings, declared exposure, answerability checks, and source-bound output receipts reject numerical claims that an agent might otherwise invent or miscalculate?

NVIDIA's [Auto Ontology](https://github.com/NVIDIA/auto-ontology) resolves enterprise terms to columns, reviewed SQL measures and join relationships, checks answerability, and shows SQL/provenance. Its [paired evaluation harness](https://github.com/NVIDIA/auto-ontology-eval) compares ontology-grounded text-to-SQL to schema-only control with deterministic execution scoring. NVIDIA has not established a universal elimination of wrong numbers. FAR's actual use case here is narrower: quantitative claims about registered agent/task executions.

Existing FAR authority already separates observation, inference, scopes, source provenance and replay:

- [Research charter](../../docs/governance/research-execution-charter.md) and [canonical map](../../docs/CANONICAL_MAP.md) govern acceptance and authority.
- [far-epistemic/1.0](../../docs/specification/far-epistemic-learning-v1.md) already enforces exact-decimal scores and provenance for its own typed predictions and decisions.
- [FAR-TOOL-AGENT-001](../tool-agent-reliability/README.md) already replays model tools, outcomes and registered slots within its bounded simulation.
- Open PR #618 adds an evidence-profile sidecar with registered exposure/known missingness, and must be inspected at its actual head before any subsequent integration.

The representational gap for **general quantitative answers** is an explicit catalog saying which numerator, denominator, unit, reference population and comparison operator a submitted metric means, paired with an answerability decision before emitting numbers. This research implementation tests that limited mechanism; it does not replace any of the validators above.

## Implemented contract

The standard-library-only [metric_grounding.py](metric_grounding.py) supports:

1. An explicit Research catalog identifying each metric, executed operator, formula, unit and review status. A changed formula or false certification is rejected; descriptive prose is not treated as machine verification.
2. A study-scoped eligible-slot registry, arm/case identities, unique outcome observations and declared source references.
3. Two bounded semantic operators: registered success percentage, and treatment-minus-control success difference in **percentage points** on identical registered case sets.
4. Strict answerability: missing observations, unknown outcomes, unmatched comparisons, duplicate exposures, unauthorized metric IDs and malformed data result in **no numerical answer**. Failures and abstentions remain in the registered denominator; they are not silently excluded.
5. Exact rational arithmetic, explicit decimal precision and half-even rounding. Optional assertion checking rejects a proposed numerical answer that differs from the executed result.
6. Receipts containing selected metric, group counts, rational numerator/denominator, displayed value, declared scope, source IDs, source registry and SHA-256 of exact input bytes.

Input formats are far-metric-catalog/0.1 and far-metric-events/0.1. Successful receipts say DERIVED_FROM_DECLARED_EVENTS; source entries must explicitly say DECLARED_NOT_INDEPENDENTLY_VERIFIED. The hashes bind submitted bytes, **not** the truth, originality, external provenance or eligibility of those bytes. No remote URI is fetched or independently authenticated. An adversary who fabricates a self-consistent dataset can still obtain a deterministic answer to the fabricated dataset. A replaying source adapter and authorized metric review are prerequisites for stronger assurance.

This module does not generate SQL, use an LLM judge, connect to NVIDIA NIM, import NVIDIA's code or deploy Postgres. It isolates the semantically relevant acceptance control without adding a parallel agent runtime or claiming equivalent capability to NVIDIA's full product.

## Verification and recorded observation

Executed locally with Python 3.13.5:

    python -m unittest discover -s research/numeric-grounding -p 'test_*.py' -v

**16 of 16 focused tests passed** after correcting an uncontrolled type error in malformed slot input. The tests exercise successful arithmetic, bad numerator/denominator assertions, dropped or duplicated rows, unpaired cohorts, unknown outcomes, abstentions, false metric redefinition/certification, unknown source IDs, malformed input types, duplicate JSON keys, binary floats and receipt-hash mutation.

A CLI smoke used **synthetically authored 30-case control and treatment arms** with 11 and 10 simulated successes respectively. It returned control 36.6667%, treatment 33.3333%, and treatment-minus-control **−3.3333 percentage points** (exactly −10/3 percentage points). These counts intentionally resemble the separately reported one-shot workflow pilot, but **no original FAR provider trace or historical run was imported or reproduced**. This is arithmetic/guard testing, not another observation of that study and not an estimate of a treatment effect.

For a CLI use, supply JSON catalog and events with the stated formats:

    python research/numeric-grounding/metric_grounding.py --catalog catalog.json --events events.json --metric delta --assert-value=-3.3333

The example metric ID delta is part of the authored unit-test catalog, not a global authority. The CLI emits one JSON receipt and returns nonzero with status UNANSWERABLE on rejection. Use the tests' catalog() and events() constructors for a reproducible demonstration.

## Limitations and next verification gate

The observed software behavior is limited to rejecting structural/semantic misreporting **given the declared rows and catalog**. It does not detect fabricated outcome rows, wrong source classifications, false source digests, incorrect human definitions or a rigged initial eligible-slot registry. It also does not demonstrate a model choosing the right metric ID, applying the right reference class, improving answers against a control, or reducing real-world numerical errors. The strict pilot prefers abstention over fabricated certainty.

Before promoting this approach beyond Research, a separate governed adapter must rebuild eligible slots and outcomes from original replayed agent/tool traces or audited database queries; human/domain reviewers must approve metric meanings; then a prospective paired evaluation should compare the same agent and questions with and without metric grounding, independently score correct numbers **and** legitimate abstentions, and report error reductions, introduced false rejections, latency and cost. Keep the experiment separately registered and frozen before outcome exposure. Do not reinterpret this sidecar as an EFR result or general agent-reliability evidence.

The current PR is deliberately isolated from FAR Core, far-ir schemas, protected main, existing experimental results, CI policy and open workstreams.
