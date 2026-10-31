# FAR-MECH — Exact finite-evidence adjudication (31 October 2026)

**Status:** Research; frozen adverse-result adjudication, *not* an unconditional claim about all neural networks, future FAR versions or competing products.

## Evidence authority

Experiment: real pretrained `HuggingFaceTB/SmolLM2-135M-Instruct`, pinned revision `12fd25f77366fa6b3b4b768ec3050bf629380bac`, actual loaded tensor hash `f628c8c925c895e0c3380249695793e6e6a7e2d1031afa4ae84e485664f69594`.

Frozen full-vocabulary run: [GitHub Actions 41223761759](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41223761759), artifact 13051320299, ZIP SHA-256 `ee8a60502f6735f71d07018fb16f4c0e3c4f5608844247514da594a7d8291281`. The full trace SHA-256 is `45c94257672bb9051922526769dcf690e8b9714799d51c2a7fa2192b0fdd9392`; measured result JSON SHA-256 is `2486737cf3cc4c24b890ff3c13f15d7c8164cb455ccae04cc665dcbef8992682`. This report does not silently replace the original or independently attest the model execution; it relies on the authenticated repository workflow and stored artifacts.

The experimental target was one pre-down-projection coordinate in the first transformer MLP. The proposed explanation predicted its activation using **only prompt token count** fitted on 24 training cases. The comparator was training-mean replacement. There were 12 ordinary heldout, 12 adversarial-framing, and 8 identity-control cases. The metric was D_KL of the *entire model next-token vocabulary distribution* under activation replacement relative to the original.

## Exactly refuted finite claims

1. **Uniform superiority of the proposed explanation over the training mean on the adversarial cohort: REFUTED.** For each of the twelve distinct recorded adversarial prompts, `KL_probe > KL_mean`. Mean probe KL = `0.00003674138675424202`; mean baseline KL = `0.000003166602047474787`. Ratio about 11.60. The minimum recorded individual probe-minus-baseline KL is approximately `0.00000951536` (strictly positive).
2. **Selective-accuracy gain from the frozen FAR gate `two_token_KL <= 0.02`: REFUTED ON THIS COHORT.** The gate admitted all 32/32 cases; acceptance is identical to no filter. This is an exact logical identity on these outcomes, not an estimated significance effect.
3. **Differential logical-entailment accuracy gain from this explanation relative to training-mean replacement: NOT SUPPORTED.** Among the 24 noncontrol cases, original answers correct 13; probe 14; mean replacement 14. The only original error corrected by the probe (heldout-06) was also corrected by the mean replacement. No case distinguishes the two methods on correctness.
4. **Control fidelity:** the eight identity replacements produced KL zero; this proves deterministic consistency of the tested hook path within these cases, not semantic comprehension.

On the ordinary heldout split, probe mean full-vocabulary KL `0.00000083982139923604` beats mean replacement `0.000002351485579804554`. This positive *cohort-specific* result must be preserved alongside the adverse failures. Selective presentation of only the favorable split would be misleading.

## Not adjudicable from these data

- **Universal internal understanding:** the experiment lacks a reference causal circuit/semantic explanation. A one-dimensional token-length fit is not a discovery of what the neuron means.
- **Strong-tool superiority:** no matched MIB, activation-patching/attribution, DAS, SAE, or circuit-localization algorithm was evaluated with the same task/model/budget. FAR-MECH is primarily an **auditor**, not itself a published mechanism-discovery/featurization algorithm. Calling a verifier an outperforming circuit-discovery method is a category error unless it actually produces circuits.
- **General reasoning reliability:** 24 small programmatically authored syllogisms, one 135M-parameter model, and no benefit from the original gate cannot demonstrate broad accuracy, calibration, robustness, or out-of-distribution reliability.

## Exact finite-observation non-identifiability

For any finite probed set `S` drawn from an unbounded input domain, choose `x* not in S`. Let `f(x)=0` for all `x`; let `g(x)=0` for `x != x*`, and `g(x*)=1`. Then `f` and `g` agree *on every measured point in S* but disagree outside S. Therefore **no finite input-only observation record uniquely establishes a global input/output mechanism without restrictions on the hypothesis class**. Even a finite intervention set has the same limitation unless the intervention domain/causal class is fully and verifiably covered. This is a countermodel to any unqualified leap from finite fidelity to universal explanation, not a countermodel to Christological metaphysics or to FAR Core v1.1.

A deterministic complete model's actual stored weights and semantics can be inspected more extensively, but proving a universal high-level semantic claim additionally requires a precise interpretation/observation contract, an identified target, and sufficient verification.

## Research prior art and competitive status

- [MIB, ICML 2025](https://mib-bench.github.io/) already supplies circuit-localization and causal-variable localization tasks with standardized metrics. FAR has **no MIB leaderboard score**.
- [Certified Interventional Fidelity, UAI 2026](https://proceedings.mlr.press/v337/asiaee26d.html) already supplies anytime-valid confidence sequences and distribution-aware intervention certification; FAR's present point-estimate scoring **does not exceed that assurance level**. Statistical certification here would need a bounded estimand, sampling design and correct adaptive/importance-weighting controls.
- [AgenticInterpBench/HyVE, EMNLP 2026](https://aclanthology.org/2026.findings-emnlp.725/) provides a direct method/benchmark for generating and validating circuit explanations. FAR has **not** run that 84-circuit reference suite.

Consequently, **superior mechanistic explanation, competitive dominance, and general reasoning uplift are not established**. The actual demonstrated FAR benefit is rigorous, source-traceable **rejection of inadequate submitted mechanism claims** on a narrow but real pretrained-LM experiment. Auditing alone is not a demonstrated commercial moat.

## Binding verdict

**Falsified in this study:** universal superiority of the tested token-count probe on the adversarial cohort, improvement from the specified full-coverage fidelity gate, and a claimed advantage in task correctness over the mean-activation baseline.

**Not falsified generally:** the possibility that a future improved FAR mechanism-discovery algorithm could outperform strong baselines under a different registered benchmark. No finite study can settle that unrestricted hypothesis.

**Governance:** Preserve all counterexamples and both favorable/adverse cohorts; keep FAR Core v1.1 unchanged. No upgrade of Research findings to validated theoretical claims or product superiority.
