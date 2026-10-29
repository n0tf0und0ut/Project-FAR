# FAR-WORLD/0.1 — Eastern Orthodox indexed epistemic world model

Status: **Research prototype, bounded deterministic engine. Not an answer generator, a trained world model, a biblical commentary engine, or a validated representation of the world.** It is an additive application-layer experiment. It does not revise FAR Core v1.1, far-ir/2.x, `far-epistemic/1.0`, FAR-COG/0.1, or EFR benchmarks.

Implementation: `mechanization/far_mechanization/world_model.py`. Contract: `schemas/far-world-model-v0.1.schema.json`. Fixture: `examples/world-model/orthodox-example.json`. Tests: `tests/test_world_model.py`.

## Purpose

Represent a scoped world state with propositions, positive and negative observations, durable source commitments, declared finite logical implications, historical corrections, and deterministic causal models. Track Eastern Orthodox theological assumptions **as framework-indexed source premises**. Ordinary empirical model queries use empirical propositions only; normative projections can use Orthodox premises without requiring an overt biblical wrapper. Full provenance is always inspectable. This is a *model API*, not text-generation policy.

This component must not be confused with the FAR-COG answer-routing work previously proposed in PR #600. It replaces that approach. It has no user prompt classifier, LLM policy, answer formatting, chat integration, or output-text suppression mechanism.

## Worldview contract

`worldview_profile = eastern-orthodox/0.1` indicates that theological and normative propositions are interpreted within an Orthodox Christian profile: Scripture read in Holy Tradition with attention to the Church's liturgical experience, Fathers and councils. No particular rule becomes Church doctrine merely because it is in this document. In the provisional model, **every theological/normative asserted proposition and rule must cite a declared scriptural or traditional source**, carry the Orthodox framework ID, and remain inspectable. An Orthodox interpretation is an explicitly *adopted* normative/theological assumption, not a premise-free proof of truth.

The example quotes the public-domain KJV form of Exodus 20:16 only as a conveniently reproducible byte-anchored biblical source. This is **not** an Orthodox translation standard, a complete patristic reading, or an independently approved interpretation. A production source set requires a specified Orthodox canon, translation policy, canonical reference, textual variant handling, patristic interpretive source review, and precise claim-level doctrinal provenance. These remain unimplemented.

The model separates:

- **Empirical** propositions and implications: sources of type `observation` or `research`, without theological predicates in the premises or framework IDs. These remain *asserted* and model-relative; their provenance hashes do not verify truth.
- **Theological** propositions and rules: framework-indexed, source-justified readings of doctrine; a theological conclusion cannot be derived solely from empirical or moral claims.
- **Normative** propositions and rules: framework-indexed values/obligations; a moral obligation cannot be derived from empirical observations alone. Some normative rules can depend on empirical circumstances, but must also include at least one normative/theological premise.

This enforces a limited form of the is/ought boundary and prevents scriptural assumptions from being silently introduced as empirical evidence. It does **not** automatically establish the validity of a human-supplied implication in natural language. That remains a semantic/formalization obligation. No conditional probability, model evidence weighting, learned transition function, or exhaustive biblical entailment is provided.

## State and consequence semantics

Every source has an exact UTF-8 text and SHA-256 hash (byte integrity only). Assertions include `valid_at` (time of described state) and `recorded_at` (when the claim entered the model), a polarity and optional `supersedes` relation. Revision chains require the same proposition and increasing recording times. Historical records are not erased. Queries use both time cutoffs to prevent hindsight leakage. A recorded successor replaces its directly superseded observation, not independent observations by other sources.

The rule language is finite *ground Horn-style literal implication*: a rule fires when **all** declared positive/negative literal premises have support. Rules are explicitly justified and type checked, but their substantive truth is not automatically proven. Consequences are computed by fixed-point iteration; a cycle without a supporting assertion cannot manufacture truth.

Status is a *four-valued record of support*:

| Status | Meaning |
|---|---|
| `SUPPORTED` | Positive support only |
| `REFUTED` | Negative support only |
| `BOTH` | Positive and negative support coexist |
| `UNKNOWN` | Neither polarity has support |

This is evidence bookkeeping in a designated model, not a binary oracle about external reality. In particular `BOTH` does not entail unrelated conclusions, and `UNKNOWN` is not negation. The proof record combines assertion, rule and source identifiers; it may coalesce distinct proof paths and therefore is **not a minimal proof certificate**. `inspect()` preserves both sides and their contributing IDs.

## Causal model semantics

`causal_models` provides finite Boolean *structural causal models* with named exogenous variables (null table) and endogenous variables (a complete truth table indexed by parent assignments). The graph must be acyclic, parents unique, every relevant source referenced, and the model fully enumerated. `simulate()` evaluates a stipulated state. `counterfactual()` evaluates an intervention with the **same exogenous context**, giving changed variables and both states.

These are deterministic **on-model counterfactuals**, not recovered causal effects from observations. A `causal_model` source may be an explicitly hypothetical or toy specification. The fact that the simulator correctly executes the given equations provides no evidence that the equations represent reality or that a causal effect is identified. No open-world prediction, causal discovery, statistical estimation, latent-state identification, or model competition is yet implemented.

## Visibility and provenance

- `state.project('empirical')` returns empirical proposition states, no theological/normative material.
- `state.project('moral')` returns normative proposition states with **no routine framework/source fields**.
- `state.project('biblical')` exposes theological and normative propositions and their framework/source IDs.
- `state.project('all')` exposes all domains and their bases.
- `state.inspect(proposition_id)` always returns the full framework and source lineage. `expose_basis=True` also exposes it in an ordinary projection.

No material is deleted from audit storage. The no-default-exposure rule is a query projection convention, not a guarantee about downstream output, nor permission to misrepresent theological commitments as universal empirical facts. Consumers must retain full provenance and reveal the framework when its source is relevant or requested.

## Minimal executable demonstration

```python
from mechanization.far_mechanization.world_model import WorldModel

model = WorldModel.load('examples/world-model/orthodox-example.json')
early = model.derive(known_at='2026-10-28T23:00:00Z')
assert early.status('lamp-on') == 'BOTH'
later = model.derive(known_at='2026-10-29T23:00:00Z')
assert later.status('lamp-on') == 'SUPPORTED'  # later correction supersedes the negative report
assert later.project('moral')[0]['status'] == 'SUPPORTED'
assert later.inspect('false-witness-wrong')['proposition']['framework_id'] == 'eastern-orthodox/0.1'
assert model.simulate('rain-to-wet-ground', context={'rain': True})['wet_ground'] is True
assert model.counterfactual('rain-to-wet-ground', context={'rain': False},
                            interventions={'rain': True})['changed_variables'] == ['rain', 'wet_ground']
```

Run `PYTHONPATH=. python -m unittest discover -s tests -p 'test_world_model.py' -v` from the repository root. All model input is untrusted even when accompanied by source URLs. Input is bounded by the JSON Schema and semantic cross-reference checks; it is not a network fetcher.

## Assurance and integration boundary

This implementation is specifically a **world-state substrate**, not the general world model the broader research program ultimately seeks. It can be embedded into `far-epistemic/1.0` investigations by mapping source IDs and revision events to the governed evidence and belief contracts, but no such bidirectional validated adapter is claimed here. Automatic source extraction, doctrinal adjudication, semantic validation, learned causal dynamics, Bayesian posterior updates, calibration, independent evaluation, and actual time-series forecasting remain open tasks.

There is no claim of model novelty, complete biblical deduction, empirical validation, scientific truth, or superior commercial value. The schema and tests establish only bounded software behavior. Tests must not be relabeled as a customer-facing or externally validated result.
