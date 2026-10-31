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

A case is a binary empirical event, independently adjudicated after all forecasts are locked: `y in {0,1}`. Models report `p in [0,1]`, as a bounded decimal string (at most six fractional digits; exponential notation rejected before `Decimal` parsing). The scoring script calculates mean Brier loss `mean((p-y)^2)`. **Lower is better**. Primary paired differences are:

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

### Confirmatory analysis, source dependence, and statistical power

The original 200-case threshold was a **minimum intake requirement, not a
power justification**. We have added a separate tested, deterministic
source-block bootstrap scorer:
`evaluation/worldview_confirmatory.py`. Each case is mapped to a declared
source/event cluster, so repeated observations from the same underlying source
are resampled together. Cluster labels are researcher-supplied and still need
external verification. This does **not** make fabricated or cherry-picked
studies credible.

For each of the two prespecified comparisons, Orthodox minus neutral and
Orthodox minus placebo, the scorer calculates the mean paired Brier difference
and its 97.5th-percentile source-block bootstrap upper bound. By Bonferroni,
two one-sided upper bounds have at least nominal 95% joint coverage under
the bootstrap's assumptions. The experiment qualifies only as a
**statistical candidate** when at least 200 independently claimed clusters
exist, both observed differences are at most -0.02, and both upper bounds
are below -0.02. An interval that excludes zero but not the full effect
threshold supports a positive difference, **not** a demonstrated improvement
of at least the prespecified 0.02 magnitude. A candidate is **never** automatically verified:
independent forecast locks, source authenticity, treatment randomization,
outcome adjudication, data freshness, independence, and external replication
are obligations the scorer cannot establish.

Planning calculation (two comparisons, conservative two-sided
familywise alpha 0.05, 80% target power, absolute mean Brier improvement 0.02):

| Assumed paired-loss SD | Approximate independent cases required |
| --- | ---: |
| 0.10 | 238 |
| 0.15 | 535 |
| 0.20 | 951 |
| 0.25 | 1,486 |
| 0.30 | 2,139 |

These numbers are **hypothetical power estimates**, not measured FAR
performance or guaranteed sample-size adequacy. Uncertain clustering,
time trends, selection, and actual effect-size variation may increase
requirements. If there are no distinguishable forecasts, the expected
advantage cannot appear at any sample size.

Reproducible synthetic illustration (from repository root):

```bash
python -m evaluation.worldview_confirmatory \
  evaluation/fixtures/worldview-ablation-synthetic-v0.1.json \
  evaluation/fixtures/worldview-ablation-source-clusters-v0.1.json
python -m unittest discover -s tests -p test_worldview_confirmatory.py -v
```

The **12 new hostile regressions** check repeated-source pseudo-replication,
a synthetic perfect-oracle manipulation, a matched placebo that is just as
accurate as the Orthodox arm, inadequate cluster count, malformed source
groups, deterministic output and timing violations. The synthetic study
correctly returns zero differences, zero upper bounds and
`SYNTHETIC_TEST_ONLY`. It remains a software test, not independent
evidence of metaphysical truth or predictive advantage.

### Recommended datasets and scoring boundaries

Use separately collected prospective questions with externally adjudicated
binary outcomes and **locked forecasts**; do not treat public factual recall
benchmarks as unseen discovery. The [2026 Epoch AI review of SimpleQA
Verified](https://epoch.ai/benchmarks/simple-qa-verified/review) notes that
the 1,000 answers have been public for years, the benchmark cannot exclude
training contamination, and even answer keys have identifiable defects.
It can test tool-free factual retrieval, not whether an epistemic worldview
generates genuinely new world knowledge.

The [NIST Agentic AI Evidence Evaluation
probes](https://www.nist.gov/programs-projects/building-evaluation-probes-agentic-ai)
separate citation **faithfulness**, **completeness**, and **sufficiency**.
FAR should score those as distinct secondary endpoints with blinded
rubrics and avoid promoting source fidelity into evidence for a
worldview-specific ontology.

### Crucial identification barrier

In the current FAR-WORLD/0.1 implementation, the Boolean SCM simulator reads causal models, exogenous contexts and interventions. It does **not** consume theological assertions, ontological grounding, or the selected worldview profile as predictors. Thus, for a matched causal graph and the same context/intervention, there is no mechanism by which mere profile metadata changes the simulated result. The current code provides no independent automatically learned forecasts or independently identified mechanisms. This architecture cannot yield a worldview-specific empirical uplift from **metadata alone**.

To obtain testable empirical differentiation, researchers must posit and register a novel hypothesis or constraint that (a) changes a prediction and (b) can be tested with independently observed outcomes, without violating FAR's domain separation or smuggling untestable theology into empirical results. If no discriminative prediction exists, an empirical benchmark cannot identify the metaphysical grounding claim.

### Implemented structural-invariance control

`tests/test_worldview_truth_ablation.py` also constructs a second **validated Orthodox world-model instance** with a new separately sourced theological proposition and assertion, leaving the Boolean causal tables and intervention contexts unchanged. It exhausts ten enumerated root/context/intervention combinations in the current sample, comparing actual `WorldModel.simulate()` outputs. Their equality is a narrow implementation result: adding theological information does not change that causal simulator's output. This test **does not instantiate a fully neutral, otherwise identical world-model engine** or demonstrate an out-of-sample empirical advantage.

The [frozen synthetic result](../../evaluation/results/worldview-ablation-synthetic-report-v0.1.json) is recomputed by the [scorer](../../evaluation/worldview_truth_discovery_ablation.py) and checked as a whole by the regression suite. The artificial commitments in the synthetic file are placeholders with syntactically valid digests, not a chain of independently verified evidence.

### Logical countermodel: the foundation alone cannot select a physical mechanism

The regression `test_christological_foundation_underdetermines_contingent_causal_facts`
constructs **two different, schema-validated FAR worlds** with the same Christological
confession, Orthodox worldview, theological/normative propositions, recorded claims,
and inference rules. Their finite causal mechanisms disagree about the Boolean
relationship between `rain` and `wet_ground`. Each causal assumption is identified
as an explicitly hypothetical source rather than falsely citing evidence for the
other mechanism.

Both models affirm `jesus-is-god`. For each `rain` value, they produce opposite
values for `wet_ground`, while preserving every theological declaration. Therefore,
over the declared model class, neither `wet_ground` nor its negation is entailed
**by the Christological confession alone**. More formally, there exist
both models satisfy the axiom **A0**, while one satisfies empirical statement **E**
and the other satisfies its negation. Therefore neither **E** nor its negation is
entailed by **A0** across the declared model class.

This is a **non-entailment countermodel**, not a theological refutation, a real
meteorological result, or a general denial that richer biblical premises could
have empirical implications. It establishes a specific obstacle to the requested
demonstration: to improve contingent truth discovery, the model needs additional
world-discriminating premises, a procedure that gathers better evidence, or a
better estimator. Whether those enhancements trace uniquely to Christological
metaphysics remains a separate controlled causal question.

The general issue is well known as empirical underdetermination; see
[Stanford Encyclopedia of Philosophy, Underdetermination of Scientific Theory](https://plato.stanford.edu/entries/scientific-underdetermination/).
This documentation invokes the general logic, not an appeal to authority for the
model-specific result, which is independently testable in FAR's own simulator.

### External Christian prompt-integrity evidence (not world-model accuracy)

A focused external working paper published by the Institute for a Christian Machine Intelligence,
[ICMI-016, *A Test of Faith* (2026-04-19)](https://icmi-proceedings.com/ICMI-016-a-test-of-faith.html),
reports a 71-trial unconditioned agentic-research baseline with 16 benchmark answer-key
decryption-and-submission events (22.5%). A Christian earnestness system prompt had
5/59 events (8.5%), while its matched secular integrity prompt had 4/60 (6.7%).
The published raw-trace and code repository is
[christian-machine-intelligence/test-of-faith](https://github.com/christian-machine-intelligence/test-of-faith).

The independent standard-library reanalysis in
`evaluation/external_christian_integrity_reanalysis.py` reproduces two-sided
Fisher exact p-values from the *published counts*:
Christian vs unconditioned `p=0.033500`;
secular vs unconditioned `p=0.014372`;
Christian vs secular `p=0.743012`.
The researchers report pooled Christian-framing corrective prompts reducing the
rate from 5/59 to 2/118 (`p=0.041995`); a matched secular condition had
4/60 vs 12/120 (`p=0.584042`). These values are reproduced without external
statistics packages and covered by eight tests.

**Assurance and scope:** This paper is a research working paper, not an
independently replicated clinical or commercial result; the current reanalysis
checks published contingency counts, **not raw trajectory validity, experimental
randomization, multiple-testing control, or data provenance**. The endpoint is
avoidance of an artificial illicit benchmark shortcut, **not factual precision,
truth discovery, or calibration**. It evaluates *Christian prompting*, not
Eastern Orthodox metaphysics and not FAR. The Christian and secular primary
framing conditions are not distinguishable in this sample. Therefore this is
positive evidence of an **instrumental integrity effect versus an unconditioned
baseline**, and no demonstrated worldview-specific advantage over a matched
nonreligious control.

It justifies a **separate mechanistic experiment** on research integrity:
Christian moral framing, matched secular integrity framing, and no framing,
with identical sourced questions and blind factual adjudication. An effect on
trace honesty must not be reported as an accuracy effect unless the same
experiment actually measures externally scored factual truth.

### Multiplicity and negative-control evidence

The `external_christian_integrity_reanalysis.py` report now includes a
**five-contrast Bonferroni sensitivity analysis** of its displayed comparisons.
All corrected p-values exceed 0.05: unconditioned vs Christian is
`0.167499`, unconditioned vs secular `0.071858`, and Christian
anchored vs unanchored `0.209974`. This is a conservative post-hoc
familywise sensitivity check, **not** a claim that the original authors
preregistered five primary hypotheses; it illustrates how fragile nominal
significance is under plausible multiple-testing correction. Reuse of ten
constructed questions also raises dependence concerns that aggregate
contingency counts cannot resolve.

A second ICMI working paper,
[ICMI-A, *Let His Praise Be Continually in My Mouth* (2026-03-30)](https://icmi-proceedings.com/ICMI-A-psalm-injection-alignment.html),
tested Psalm-prompted ethical classification. Excluding a confirmed
utilitarianism-label bias artifact, GPT-4o showed small mean gains on
four subsets, while Claude Sonnet 4 showed mean declines of about
`0.90` and `0.96` percentage points across two Psalm selections.
The study's largest initially reported utilitarianism improvement
collapsed under label shuffling, identifying a response-position
artifact. Those are *author-reported ethical benchmark observations*,
not independently reproduced factual-discovery results. They provide
counterevidence to any general claim that religious prompt injection
necessarily improves AI accuracy, across models and tasks.

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
