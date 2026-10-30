# FAR-MECH/0.1 — bounded mechanistic-explanation fidelity auditor

**Status:** Research-only executable evidence auditor. **Does not** establish that any neuron, circuit, language model, or causal mechanism is actually understood. No FAR Core theorem, frozen contract, MIB result, alignment assurance, epistemic probability semantics, or Christian metaphysical premise is changed.

## Research result and prior art

Nick Cammarata, [*Neural Networks Are Already Clean*](https://already-clean.goodfire.com/) (Goodfire, 15 Oct 2026), proposes beginning with native neurons and circuits rather than assuming polysemanticity makes them opaque. That is a productive *hypothesis*, not a certified explanation of all LLM computations.

Leo Gao, [*Neural networks are not already clean*](https://www.lesswrong.com/posts/Dkh7pXKjoNWkkxQDz/neural-networks-are-not-already-clean) (17 Oct 2026), identifies a critical logical failure: the fact that many activating examples fit a label does **not** mean that all instances satisfying that label activate the neuron. He proposes measuring how explanations behave when their predicted activations substitute for the actual neuron, observing downstream distributional effects using KL divergence. A low local error alone does not imply causally faithful model behavior.

The established [Mechanistic Interpretability Benchmark (MIB)](https://proceedings.mlr.press/v267/mueller25a.html) (Mueller et al., ICML 2025) evaluates causal localization and interchange intervention under multiple models and tasks. FAR does not claim to replace or outperform MIB. The intended product difference is *contract- and provenance-aware verification of submitted claims about mechanisms*, not the generation of model circuits.

## Evaluation contract

Files:
- `schemas/far-mechanistic-fidelity-v0.1.schema.json`: closed intake contract.
- `mechanization/far_mechanization/mechanistic_fidelity.py`: deterministic bounded auditor and CLI.
- `examples/mechanistic-fidelity/synthetic-neuron-replacement.json`: six deliberately synthetic traces.
- `tests/test_mechanistic_fidelity.py`: adversarial validation and counterexample tests.
- `mechanization/far_mechanization/mechanistic_toy_reference.py`: separate explicit deterministic toy network used to replay the synthetic probabilities.

The intake declares:
- a **deterministic, fixed nonintervened state, exact output distribution** execution contract, so equality checks have valid meaning;
- exact model artifact and reference population SHA-256 *claims*;
- the target component and intervention type (single-component activation replacement);
- an explanation with precise source identities and source-byte commitments;
- registration time and a split for each measured case: **heldout, adversarial, control**;
- source-bound observed and explanation-predicted component activations, with a named baseline;
- original output probability vector, replacement output vector, and baseline output vector.

Data is submitted by an operator. The auditor validates shape, referenced sources, exact source digests, chronological ordering, finite fixed-scale decimals, strictly positive normalized probability vectors, population output dimension, uniqueness, and all mandatory splits. **This is not verification that the cited model was run or that the evidence data were collected honestly.**

### Metrics

For each split, compute:

`MAE_local = mean(abs(observed_activation - explanation_activation))`.

`KL_replacement = mean(D_KL(P_original || P_replacement))`.

`KL_baseline = mean(D_KL(P_original || P_baseline_replacement))`.

`Delta_KL = KL_replacement - KL_baseline`.

Smaller downstream KL means the replacement better preserves the original model's *reported output distribution* under the declared experiment. This is **not** a direct measure of correctness, morality, safety, or original-world truth. The measure does not imply that a component is unique, a circuit complete, or an explanation semantically accurate. The normalizer must use original model probabilities before replacing the component, and the same model/input distribution must be used for comparisons.

A specific case with `KL_replacement > KL_baseline` becomes a retained `DOWNSTREAM_WORSE_THAN_BASELINE` counterexample with source references. A positive heldout average cannot mask a negative adversarial cohort: results are split and per-case, not collapsed into a single claimed certificate. All measured KL values and the source-committed document digest are supplied.

### Six-case synthetic falsification

The heldout cases have a 0.0001 activation prediction error and a replacement distribution much closer to the original than the baseline. Adversarial cases have a 0.01 activation error, yet this small error crosses a steep downstream nonlinearity; replacement output distributions differ sharply from the original and are worse than baseline. Every one of the six source-output pairs is independently recalculated by the deterministic toy reference in `mechanization/far_mechanization/mechanistic_toy_reference.py`. The adversarial regression suite compares these exact calculations against the submitted traces. This exhibits the failure mode:

`local activation fit does not imply downstream mechanism fidelity`.

Controls preserve the declared original output distributions exactly. The tiny reference network is `P0(z)=0.8 - 60 * clip(z-0.99, 0, 0.01)` and `P1(z)=1-P0(z)`. It exhibits steep but bounded probability sensitivity. A guard rejects a substituted or baseline activation equal to the observed activation if downstream probabilities differ; that scenario is impossible under the declared deterministic, fixed-context single-component replacement contract. The fixture demonstrates toy-model causal sensitivity and that the *auditor* detects its consequences; it is not a measured frontier-model neuron or circuit.

Run:

```bash
python -m mechanization.far_mechanization.mechanistic_fidelity examples/mechanistic-fidelity/synthetic-neuron-replacement.json
python -m unittest discover -s tests -p 'test_mechanistic_fidelity.py' -v
```

Every report is labeled `SYNTHETIC_DEMONSTRATION_ONLY` or `SUBMITTED_INTERVENTIONS_NOT_INDEPENDENTLY_REPLAYED`. Neither is a proof of a real mechanism. Provenance hashes protect submitted bytes only, not the asserted provenance origin.

## FAR integration and theory boundaries

This is a proposed measurement adapter to existing FAR evidence/claim investigations. It is deliberately **not** a second knowledge engine, a theory change, or an unauthorized assumption introduced into FAR-CORE-001–014.

- **FAR-CORE-001:** A proposed explanatory representation must preserve the task's specified behavior under a declared contract. A readable neuron label does not prove exact factorization of full downstream behavior.
- **FAR-CORE-004:** No finite demonstration implies a universal minimal circuit or universally least-informative explanation.
- **FAR-CORE-010:** The model, activation substitution semantics, intervention context, input family and target behavior belong in the **fixed interpretation/observation contract**. Frame changes are not a license to assert altered exact common theory.
- **FAR-CORE-011/012:** Any omitted intervention context or insufficient coverage must produce bounded/unknown status, not unwarranted mechanism certification.
- **FAR-CORE-014:** Its bounded theorem on linear-logic successor sets is unaffected.

To integrate into `far-epistemic/1.0`, keep source identities, experiment timestamps, counterexample IDs, calibrated predictions, outcomes and revision history in a separately validated adapter with no competing probability semantics. A regression cannot upgrade theoretical assurance without an applicable checked proof.

## Required independent experimental next step

Compare original-neuron, native explanation, sparse autoencoder, and matched trivial/ablated baselines on the **same checkpoint and preregistered sample**. Execute actual activation substitution with hooks, collect heldout/adversarial/negative-control cohorts blind to hypothesis construction, enforce exact model/precision/checkpoint/replay environment and seeds, and store independently reproducible logits. Evaluate downstream KL, intervention-induced distribution shift, local activation error, non-triviality (versus unchanged activations), and subset failure rates. The chosen effect threshold, sampling and power calculation must be registered **before** examining results.

The current artifact **does not perform neural model inference**. Without real intervention traces, it cannot claim to discover a new neural circuit or settle the disagreement between Cammarata and Gao. It can already reject submitted evidence that is internally inconsistent and identify a specific causal-fidelity counterexample.

## Verdict

**Implemented:** bounded, replayable, source-committed numerical audit of purported replacement experiments, plus adversarial failure discovery and contract-relative reporting.

**Not demonstrated:** model-neuron interpretation quality, correct source coding, empirical causal sufficiency, representation minimality, counterfactual correspondence, generalization to frontier models, improved external reasoning accuracy, or product/commercial advantage.
