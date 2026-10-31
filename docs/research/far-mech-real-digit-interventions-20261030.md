# FAR-MECH: first real-trained-model intervention run (2026-10-30)

**Status:** Research experiment, executed on an actual trained PyTorch MLP. **Not:** a pretrained or frontier language-model experiment, semantic neuron explanation, verified general mechanistic discovery, or comparative commercial benchmark.

## Reproducible experiment

- Data: `sklearn.datasets.load_digits` (1,797 actual handwritten digits represented as 64-pixel images). Dataset raw-float32 SHA-256: `a627aed550b0b29bf76a981bc1ecbab5ef775aac454c94154f20ec9f61a04c83`.
- Model: 64-input / 24-ReLU / 10-class PyTorch classifier, 60 full-batch Adam epochs, LR `0.01`, seed `1729`, CPU deterministic algorithms enabled, 1,257 training and 540 test images.
- Observed test accuracy: **520 / 540 = 96.2963%** (this is a model accuracy measurement, not an interpretation score).
- Target: hidden ReLU unit `fc1.relu.4`, selected from training activations by output-weight influence and maximal single-pixel correlation. One-pixel explanation `ReLU(alpha * image[42] + beta)`, fit on training only; baseline replaces with that unit's mean training activation.
- Real intervention: during inference replace only that unit with the explanation-predicted activation (and separately with the mean-activation baseline). Keep all other state and model parameters fixed. Score the 10-dimensional output distribution.
- Output probability reporting: softmax(logits / 2) mixed with 0.5% uniform, then fixed to six decimal places with exact total 1. This smoothing is a declared **scoring transformation**, not a property of the network's raw logits.
- Three distinct test cohorts: 16 initially selected held-out test inputs, eight adversarial cases selected as worst downstream loss deltas from a disjoint candidate pool of 154 test samples, and eight disjoint exact-activation controls.

## Observed results

| Split | n | Explanation activation MAE | Mean KL(original, predicted replacement) | Mean KL(original, mean baseline) | Cases worse than baseline |
|---|---:|---:|---:|---:|---:|
| Held-out | 16 | 0.6033775 | 0.0074025297 | 0.0181143239 | 1 |
| Adversarial selected | 8 | 1.841576875 | 0.0745697345 | 0.0298452063 | 8 |
| Exact-activation control | 8 | 0 | 0 | 0.0170841532 | 0 |

The simple explanation outperformed the baseline on mean held-out KL, but counterexample search revealed a distinct subset where it underperformed. Because that subset was **deliberately selected by its outcome KL**, comparing the cohort means does not estimate an unbiased generalization gap or a statistically confirmatory effect.

This result establishes a real network intervention that is sensitive to imperfect activation reconstruction. It does not show that the explanation represents the neuron's conceptual function: it is deliberately a weak one-pixel proxy.

## Exact provenance and independent replay of saved state

The actual locally recorded, full **32-case** source-bound FAR-MECH trace is retained as the conversation artifact `digits-mech-traces.json` and the model's full trained tensor values and all 32 input vectors as `digits-checkpoint.json`.

- Model checkpoint commitment `sha256:79bbe2c2808c93011cb8af35f33c7fa3b751fd35d34c09b9e9262273f950b8ad`, over FAR canonical compact JSON bytes of the checkpoint object (not the pretty-printed file bytes).
- Original run source-text commitment `sha256:cd8a38ebe88ea3b1e6f8be9564bcb1bca6887754cc22e06babd2cfea7d680c70`.
- Train reference-population commitment `sha256:ee5b020695965c5dbd5d7604f438bdd29f6bd046c854754911c5bc8b837f3bb8`.
- Independent *code-path* replay reconstructs the checkpoint, hashes every individual input, and intervenes by a PyTorch **forward hook on `fc1` pre-ReLU**, rather than using the recording script's hidden-state replacement branch. It checked all 32 original/replacement/baseline probability vectors with tolerance `2e-6`, and four tamper/replay tests passed.
- **Independence boundary:** this is a separate replay implementation from the original recording, **not** an independent research lab, independent acquisition of the dataset, review of human choices, or blind evaluation of explanations.

A three-case real-measurement extract with a self-attested source note is committed at `evaluation/fixtures/real-digits-three-case-extract-v0.1.json`, and the measured cohort summary is committed at `evaluation/results/real-digits-mechanistic-fidelity-20261030.json`. The extract can be re-audited by FAR-MECH using only the canonical lightweight test environment. The full 32-case recording and saved full-precision checkpoint accompany this conversation as downloadable artifacts; reproducing the experiment from scratch is also supported by the source scripts.

## Reproduction commands

Optional scientific dependencies are **not required** for FAR's ordinary canonical test suite:

```bash
python -m pip install numpy torch scikit-learn
python -m evaluation.run_real_digits_mechanism --output /tmp/far-real-digits
python -m mechanization.far_mechanization.mechanistic_fidelity /tmp/far-real-digits/digits_mechanism_traces.json
python -m evaluation.replay_real_digits_mechanism /tmp/far-real-digits/digits_checkpoint.json /tmp/far-real-digits/digits_mechanism_traces.json
python -m unittest discover -s tests -p 'test_mechanistic_real_digits_extract.py' -v
```

Re-training uses fixed seed and specified deterministic CPU settings, but exact weights may still depend on torch/BLAS/platform versions. **Do not claim byte-identical checkpoint reproduction without matching its digest.** The bundled checkpoint allows direct re-execution of the actual recorded interventions independently of training version drift.

## FAR theory and commercialization limits

The experiment is a bounded example of **representation failure under a specified task contract**: a simple one-pixel activation description can be useful for some cases and insufficient on others. It neither changes FAR Core v1.1 nor proves a universal circuit ontology. Causality is bounded to a **controlled computational intervention in the recorded checkpoint**; causal claims about the external world, alignment, and model intentions do not follow.

The next experimental scope is a pre-registered real **language-model** intervention with a pinned checkpoint/tokenizer, fixed activations/hooks, exact-context controls, held-out prompts and meaningful task outcomes, matched neuron/SAE/baseline explanations, and independent replication. This run only demonstrates that the FAR-MECH audit pipeline can operate on a real trained network.

There is no demonstrated competitive superiority over MIB, TransformerLens, pyvene, or existing circuit-tracing systems from the present evidence.
