# FAR-MECH/0.2 — pretrained language-model mechanism and reliability pilot

**Status: executable experimental protocol; numerical model findings require a completed, artifact-bearing run.** Adds no FAR Core theorem or commercial superiority claim.

## Fixed target

- Model: [HuggingFaceTB/SmolLM2-135M-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct).
- Immutable model revision: `12fd25f77366fa6b3b4b768ec3050bf629380bac` (HF model metadata confirmed October 31, 2026).
- Transformer experiment: PyTorch `float32`, CPU, deterministic kernels where possible; inference from actual pretrained safetensors, **no random initialization fallback**.
- Target: first decoder block's MLP `down_proj` input, one real internal activation coordinate at the final prompt token. Coordinate chosen *from training prompts only* by train-activation standard deviation multiplied by output-projection column norm.
- Explanation hypothesis: a one-variable training-only linear regression predicting that activation from token count. This is a deliberately weak scalar proxy; **it is not a semantic description of the neuron's learned function**.
- Baseline: replace that same coordinate with its training-set mean. Identity replacement is the positive control.
- Each sample: calculate normal model forward, intervene through `register_forward_pre_hook`, compute two-way, answer-token-conditioned distribution, and submit source-committed results to `FAR-MECH/0.1`.

## Three independent research questions

### 1. Can FAR correctly explain pretrained-LM computation?

**Necessary evidence:** A candidate explanation must predict held-out activations; explain why the component is involved in the model's computation; survive causal replacement and adversarial probes with lower downstream KL than a matched baseline.

**Pilot actually tests:** Whether a train-derived scalar proxy predicts one internal activation sufficiently well to preserve a defined **binary answer-token projection** under replacement. The full model vocabulary distribution and circuit-level explanations are *not* reconstructed. A low KL on the two selected tokens is not full-model sufficiency. Any statement of full interpretability is unsupported.

### 2. Does FAR beat interpretability tools?

**Relevant external baselines:** [MIB (Mueller et al., ICML 2025)](https://proceedings.mlr.press/v267/mueller25a.html), [TransformerLens](https://transformerlensorg.github.io/TransformerLens/) for hooks/patching, [Goodfire parameter decomposition](https://www.goodfire.com/research/interpreting-lm-parameters), and causal-variable interventions through DAS/SAEs.

The pilot only compares the chosen probe to a mean-activation baseline **on the exact same model/input/target**. There is no published MIB score for FAR and no direct SAE, DAS, or attribution/optimization method running on these same tasks. Consequently **outperforming existing interpretability systems is untested**, even if this baseline is beaten. MIB tasks, model/test splits, budgets and quality metrics must be matched in a distinct confirmatory trial.

### 3. Does mechanistic auditing improve general reasoning reliability?

Evaluation consists of logically labeled **syllogistic entailment** questions of the form:
- Valid: Every A is B; Every B is C; therefore every A is C.
- Invalid: Every A is B; Every C is B; therefore every A is C.

Tasks are generated deterministically with distinct wording for training, heldout and adversarial cohorts. They are **not GSM8K or a comprehensive reasoning benchmark**. Report correctness for the original LM, explanation-activation intervention, and mean-activation intervention. An interpretation audit does not automatically change the LM's output policy.

For abstention, a predetermined `KL <= 0.02` gate accepts a subset of cases *without seeing ground truth*. Report accuracy on accepted cases and compare to (a) lowest answer-token entropy and (b) deterministic hash-order acceptance at the **same number of accepted cases**. If the gate does not improve accuracy at matched coverage, reliability enhancement is unsupported. If it improves only selective accuracy, do **not** call it an improvement in full-coverage model correctness. All claims need independent tasks and adequate sample sizes.

## Data collection and controls

- `evaluation/run_pretrained_lm_fidelity.py` contains the fixed model id/revision, case generator, hooks, metrics, checkpoint-weight-byte fingerprint, source commitments, and reporting.
- `tests/test_mechanistic_pretrained_protocol.py` validates model pin, disjoint task identities, split labels and implementation entry points *without requiring downloads*. Such tests are **not neural-model runs**.
- `.github/workflows/far-pretrained-lm-mechanism.yml` installs pinned dependencies, fetches the exact model revision on a read-only GitHub runner, runs the real pilot and uploads two JSON artifacts. If model download fails, CI should **fail and report the network blocker**, not substitute generated values.
- Every case is measured after the run registration timestamp; registration timestamp alone is not independent proof of preregistration. Code and split construction predate the experiment as a Git commit.
- Source hash of actual loaded model tensor bytes is recorded; a repository ID by itself is not a checkpoint-integrity proof.
- The candidate's `adversarial` split is a harder instruction/framing perturbation that is predeclared by the generator, **not** cherry-picked post hoc based on KL.
- The `control` split uses identity replacement at the target coordinate. It checks fidelity of this intervention path, not invariance to every model hook or full-vocabulary output.
- All comparisons are descriptive pilot estimates. No preregistered significance threshold, benchmark dominance or extrapolation to frontier-scale LMs is established.

## Commands

```bash
python -m unittest discover -s tests -p 'test_mechanistic_pretrained_protocol.py' -v
python -m pip install 'torch==2.5.1' 'transformers==4.49.0' 'huggingface_hub==0.29.3' 'safetensors==0.5.3'
python -m evaluation.run_pretrained_lm_fidelity --output artifacts/pretrained-lm-mechanism --per-split 12
```

The output files are `far_mech_pretrained_trace.json` (accepted FAR-MECH submitted-data audit) and `far_mech_pretrained_result.json` (paired causal fidelity and reasoning task outcomes).

## Decision rules

| Claim | Evidence required | Acceptable pilot decision |
|---|---|---|
| Actual pretrained-LM mechanism experiment executed | Exact checkpoint loaded; hook measurements; FAR-MECH audit; output artifacts; no synthetic fallback | Executed / failed / unavailable |
| Faithful explanation of internal computation | Held-out and adversarial intervention tests; matched baselines; semantic and circuit review | Bounded local-fidelity result only |
| Better than published competing interpretability methods | Reproduced MIB tasks under matched budgets, at least relevant strong baselines | `NOT_TESTED` until run |
| Improves general reasoning reliability | Independent broad reasoning tasks, equal coverage/latency and matched controls, calibrated risk | `NOT_ESTABLISHED` from this pilot |

No theological worldview premise changes this computational evaluation, and no output may infer Christian metaphysical truth from the measured model behavior. No FAR-CORE-001–014 theorem or closure assurance is modified.
