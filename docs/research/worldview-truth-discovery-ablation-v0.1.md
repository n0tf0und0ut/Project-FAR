# FAR-WORLD-EVAL/0.1 — Truth-Discovery Advantage Ablation

**Registration status:** Design frozen as Research in this commit before collecting any independent prospective outcome labels. The included eight-case dataset is `synthetic`, created solely to exercise the scorer. It is **not evidence of external-world predictive performance**. This protocol neither changes nor repairs the governed FAR Core v1.1 mathematical theory.

## Claim under test

`H`: An Eastern Orthodox Christological metaphysical commitment improves FAR's **out-of-sample empirical truth discovery** beyond the identical FAR inference engine without this commitment, when factual evidence, available actions and causal equations are held constant.

The confessional commitment itself is fixed inside the Orthodox profile and not experimentally retracted. The **effect of selecting this framework on externally checkable forecasts** is the experimental treatment. Outcome comparisons cannot prove or refute the existence of God, only determine whether this implementation adds predictive discrimination under tested conditions.

### Matched arms

- **Neutral:** the same FAR empirical/mechanism representation with no Christological profile.
- **Orthodox:** the same empirical/mechanism representation with the selected Christological grounding profile.
- **Placebo:** the same representation with comparably structured but inert non-predictive worldview metadata.

All three must receive identical input evidence, information time, causal equations, prediction opportunity, compute/time budget, interface, and scoring. Only the profile-specific configuration may differ. The record binds shared evidence/mechanism SHA-256 values per case; **the scoring tool verifies digest equality and syntax, not the actual referenced input bytes**. Independent replay must verify commitments and eliminate hidden leakage.

### Experimental outcome

A case is a binary empirical event, independently adjudicated after all forecasts are locked: `y in {0,1}`. Models report `p in [0,1]`, as a canonical decimal string. The scoring script calculates mean Brier loss `mean((p-y)^2)`. **Lower is better**. Primary paired differences are:

`Delta_N = Brier(Orthodox) - Brier(Neutral)`

`Delta_P = Brier(Orthodox) - Brier(Placebo)`.

A negative difference is better *on these data*. The script also records how many case-level forecasts actually differ. If every forecast is identical, both deltas must be zero for every possible independent outcome vector; it is then impossible to infer an accuracy gain from that predictive behavior.

### Evidence standard

A result merits a conditional **candidate empirical advantage** only after all of the following are satisfied:

1. The evaluation cohort contains at least **200 independent, post-registration, externally adjudicated cases** selected without access to arm forecasts. A proposed allocation is 100 mechanism/intervention outcomes and 100 sourced factual events, preregistered before collection.
2. Forecasts are locked *before* outcomes become knowable, with no outcome leakage; hashes, model versions and training/checkpoint provenance are independently replay-verified. The scoring script's timestamp checks alone cannot prove this.
3. The same model and tools are used across arms; a cross-over or equivalent randomized order design controls compute and placement effects. Results are evaluated blinded to arm labels.
4. Mean paired Brier improvement is at least **0.02 absolute loss points** versus **both** controls, with a prespecified block-bootstrap 95% confidence interval entirely below zero against both, using cluster-resampling if events share sources.
5. There is no material regression in corrections after new evidence, abstention when evidence is absent, false-certainty, or misleading citations. Those endpoints require separately preregistered rubrics and cannot be substituted for the primary score.
6. Results reproduce on a second hidden set not chosen after observing the pilot.

`0.02` is a declared screening threshold, not a known minimal clinically or commercially important difference. Sample size is an initial minimum; adequacy of power must be computed from actual outcome variance and clustering before attempting confirmatory inference. No p-value, interval or success claim is computed by the current scoring implementation; it is not a confirmatory statistical engine.

The scoring tool marks every case set either `SYNTHETIC_TEST_ONLY`, `INSUFFICIENT_PROSPECTIVE_CASES`, or `PROSPECTIVE_UNVERIFIED_REQUIRES_INDEPENDENT_AUDIT`. No output status means verified advantage.

### Crucial identification barrier

In the current FAR-WORLD/0.1 implementation, the Boolean SCM simulator reads causal models, exogenous contexts and interventions. It does **not** consume theological assertions, ontological grounding, or the selected worldview profile as predictors. Thus, for a matched causal graph and the same context/intervention, there is no mechanism by which mere profile metadata changes the simulated result. The current code provides no independent automatically learned forecasts or independently identified mechanisms. This architecture cannot yield a worldview-specific empirical uplift from **metadata alone**.

To obtain testable empirical differentiation, researchers must posit and register a novel hypothesis or constraint that (a) changes a prediction and (b) can be tested with independently observed outcomes, without violating FAR's domain separation or smuggling untestable theology into empirical results. If no discriminative prediction exists, an empirical benchmark cannot identify the metaphysical grounding claim.

### Separate normative evaluation

Framework-consistency can be measured on held-out Orthodox doctrinal problems against independent ecclesial/patristic reference review, with blinded provenance, passage-context controls, and disagreement handling. But scoring agreement with a framework's own labels is not evidence of *universal objective morality* or improved empirical truth detection. Do not mix denominational preference adherence with external factual accuracy.

### Assurance and current results

The eight-case fixture in `evaluation/fixtures/worldview-ablation-synthetic-v0.1.json` stipulates equal probabilities `0.75` for positive outcomes and `0.25` for negative outcomes in all three arms. The paired scorer's correct expected report is `n=8`, all arm Brier losses `0.0625`, zero prediction changes, zero score difference, and `SYNTHETIC_TEST_ONLY`. This exercise tests scoring and failure isolation; it is **not evidence** for or against Christian metaphysics.

Implementation: `evaluation/worldview_truth_discovery_ablation.py`. Test: `tests/test_worldview_truth_ablation.py`. Run from repository root:

```bash
python -m evaluation.worldview_truth_discovery_ablation evaluation/fixtures/worldview-ablation-synthetic-v0.1.json
python -m unittest discover -s tests -p test_worldview_truth_ablation.py -v
```

### External evaluation relevance

A 2026 peer-reviewed study of sycophancy found that model agreement with users can appear attractive while worsening judgment, so agreement with a starting commitment must not substitute for evidence-sensitive accuracy (Cheng et al., `Science`, DOI 10.1126/science.aec8352). Stanford's 2026 AI Index describes KaBLE, a 13,000-item epistemic reliability benchmark distinguishing belief from fact. NIST's 2026 agentic AI evaluation project likewise emphasizes grounding outputs against trusted documents. These are methodological reasons for independent scoring, not validation of FAR or its theology.

Sources:
- https://doi.org/10.1126/science.aec8352
- https://hai.stanford.edu/assets/files/ai_index_report_2026_chapter_3_responsible_ai.pdf
- https://www.nist.gov/programs-projects/building-evaluation-probes-agentic-ai

## Decision rule for the existing theory

- No result here contradicts FAR-CORE-001 or -004. Factorization remains contract-relative; a fixed worldview does not grant contract-free minimality.
- No change to FAR-CORE-010 is implied: worldview must be indexed in interpretations or background frames according to exact contract semantics, not arbitrary inference.
- Without a prespecified differential observable, there is no empirical test of the metaphysical axiom. The status is **underdetermined outside the declared theological profile**.
- The strongest **current factual result** is that the existing world model contains no worldview-dependent empirical prediction function. No truth-discovery uplift is established.
