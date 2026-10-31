# FAR-WORLD/0.1 — Live Forecasting and Independent Fact Investigation

**Status:** Research implementation. Model prompts, scoring and validation are committed. **No external-world forecasting advantage is currently established.** This protocol does not modify or certify FAR Core v1.1.

## 1. Forecasting first: ForecastBench

**Data source:** Forecasting Research Institute, [ForecastBench datasets](https://www.forecastbench.org/datasets/) ([public repository](https://github.com/forecastingresearch/forecastbench-datasets)). New binary forecasting question sets are published every two weeks. Official instructions use `forecast_due_date-llm.json` and a 24-hour window. The next expected round following 2026-10-25 is **2026-11-08**; verify this date against the actual published release. As of 2026-10-30 the next question set is not yet available and the preceding 2026-10-25 submission deadline has passed.

ForecastBench **registration and approved GCP upload access** are separate requirements for official leaderboard participation: [official instructions](https://github.com/forecastingresearch/forecastbench/wiki/How-to-submit-to-ForecastBench). A local FAR forecast file **is not** a ForecastBench submission. The official benchmark demands at least 95% coverage separately for market and dataset questions; production generation must be externally locked and uploaded before the official deadline. This study will also retain a *separate*, internally preregistered and independently resolved cohort, not misrepresent partial pilots as official benchmark submissions.

### Inputs and same-engine treatment

`evaluation/prospective_forecast_runner.py` consumes the exact public question-set JSON. It validates the question-set name and due date, source classes, unique source-scoped question IDs, resolution criteria, and post-deadline dataset horizons. Each forecast unit is (source, ID, resolution date). It invokes the **same OpenAI-compatible chat-completions backend and the same model ID** separately under three declared prompt arms:

- `neutral`: secular epistemic standards with evidence, counterexamples and uncertainty;
- `orthodox`: identical shared evidence and reasoning instruction plus the Christological Logos/false-witness commitment;
- `placebo`: a comparably structured non-predictive invented research identity.

The prompt profiles are declared; they are **not guaranteed token- or style-matched**. The study must independently verify comparable token budgets and randomized execution, and must not attribute differences solely to metaphysics. `temperature=0` is requested but not an isolation guarantee across model providers. Order rotates by question identity, each invocation has fresh messages, source material is treated as untrusted, and each prediction records a hashed prompt, original response, question data and model identity. Inference services, model credentials and real responses are **not** bundled in the repository; they must be supplied separately. The runner does not claim the file's local timestamp is externally trusted.

### Runbook

From the repository root, using a model with an explicitly configured OpenAI-compatible inference endpoint and credential:

```bash
export FAR_MODEL_ENDPOINT='https://YOUR_MODEL_PROVIDER/v1/chat/completions'
export FAR_MODEL_API_KEY='YOUR_SECRET_VALUE'
# On or immediately after official question-set publication, verify date and URL:
curl -fL https://raw.githubusercontent.com/forecastingresearch/forecastbench-datasets/main/datasets/question_sets/2026-11-08-llm.json -o /tmp/2026-11-08-llm.json

# Small, explicitly non-prospective rehearsal; does not qualify for official submission:
python -m evaluation.prospective_forecast_runner /tmp/2026-11-08-llm.json /tmp/far-forecast-rehearsal.json --model EXACT_MODEL_ID --rehearsal --limit 4

# Full future round, run during official forecast due date and before deadline:
python -m evaluation.prospective_forecast_runner /tmp/2026-11-08-llm.json /tmp/far-forecast-2026-11-08.json --model EXACT_MODEL_ID
```

Before full execution, verify model costs, question count, output coverage, budget, tokens and available time. The repository does not expose model credentials or automatically run this costly full round. Full output is labeled `PRE_SUBMISSION_REQUIRES_EXTERNAL_LOCK`, not `SUBMITTED` or `VERIFIED`; partial outputs are non-submittable. Preserve raw bytes and commit/hash the generated artifact in an independently timestamped location before resolution.

**Record original external registration time** and a SHA-256 of the locked protocol separately. Having `registered_at` as a string is not proof that it was preregistered.

### Delayed independent outcome join

When official outcome data become known, use `evaluation/forecast_resolution_join.py` to pair forecast IDs with separately obtained, sourced resolution values. Each resolution event is:

```json
{
  "source": "metaculus",
  "id": "actual-question-id",
  "resolution_date": null,
  "value": true,
  "observed_at": "2026-11-16T00:00:00Z",
  "source_uri": "https://example.org/official-resolution"
}
```

Wrap an `events` array in an object containing `version: "FAR-WORLD-RESOLVE/0.1"` and the forecast's `question_set_sha256`. Source URI and resolution timestamp must be genuine; the example above is illustrative, not an actual outcome. The join rejects resolutions predating the locked forecast, missing arms, mismatched dataset hashes and duplicate records. Unresolved events remain excluded until resolution, not assigned false.

```bash
python -m evaluation.forecast_resolution_join /tmp/far-forecast-2026-11-08.json /tmp/verified-resolutions.json /tmp/far-resolved-study.json --registered-at '2026-11-07T12:00:00Z' --protocol-sha256 ACTUAL_64_HEX_SHA256 --data-class prospective
python -m evaluation.worldview_truth_discovery_ablation /tmp/far-resolved-study.json
python -m evaluation.worldview_confirmatory /tmp/far-resolved-study.json /tmp/independently-verified-cluster-map.json
```

The `registered_at` example is not a real registration claim. Outcome adjudication and genuine independent source clustering must be externally audited. The score returns **unverified prospective evidence** even if the result looks favorable. Confirmation requires the prespecified effect threshold versus both controls, blocked confidence intervals, and independent hidden replication. A retrospective or synthetic score is not prospective evidence.

### Scoring and causal interpretation

Primary outcome: per-event Brier score, paired arm differences, and source-blocked confidence bounds for the prespecified 0.02 effect, using the existing `FAR-WORLD-EVAL/0.1` scorer and `worldview_confirmatory`. ForecastBench's own leaderboard uses a **difficulty-adjusted Brier Index**, so raw FAR Brier scores must **not** be presented as official ForecastBench rankings. Track unresolved/censored events, arm completion, costs, answer-parsing failures, calibration and abstention. Do not silently remove difficult questions.

The current 200-case minimum is not a powered confirmatory sample. The repository's normal-approximation estimates vary from 535 to 1,486 independent clusters for a 0.02 effect at assumed paired SD 0.15–0.25, under familywise type-I error control and 80% power. An actual pilot must establish variance and dependence assumptions before setting the confirmatory cohort size.

## 2. Independent factual investigation — separate experimental endpoint

**Different construct:** evidence-supported factual interpretation, not forecasting of unknowable future outcomes. This part must be blinded to the forecasting results and separately adjudicated.

`evaluation/factual_investigation_runner.py` takes a **model-visible packet** containing only source IDs, source text, claims and the source subsets. It cannot accept an answer key embedded in the packet. Each arm evaluates exactly the same evidence and returns `SUPPORTED`, `REFUTED` or `INSUFFICIENT`, cited source IDs and a rationale. Synthetic smoke-test packet and **separate** key:

- `evaluation/fixtures/factual-packet-synthetic-v0.1.json`
- `evaluation/fixtures/factual-answer-key-synthetic-v0.1.json`

These fictional examples exist solely to validate code; they do not measure real reliability. To collect credible evidence, have independent subject-matter annotators prepare and separately adjudicate a held-out set from source material that none of the model arms received in training or through feedback. Audit source authenticity, contextual completeness, and whether the gold label follows from the source. Keep gold labels/keys inaccessible to the model and investigator until every output is committed. Randomize question order and label positions; source texts may contain malicious instructions.

```bash
python -m evaluation.factual_investigation_runner evaluation/fixtures/factual-packet-synthetic-v0.1.json /tmp/far-factual-smoke.json --model EXACT_MODEL_ID --endpoint "$FAR_MODEL_ENDPOINT"
python -m evaluation.score_factual_investigation evaluation/fixtures/factual-packet-synthetic-v0.1.json /tmp/far-factual-smoke.json evaluation/fixtures/factual-answer-key-synthetic-v0.1.json
```

This provides an end-to-end **synthetic rehearsal only**. In production the key must be held off the inference machine and the packet must come from independently prepared evidence, not these published examples. The scorer reports classification accuracy, citation-ID subset correctness and incorrect confident assertions on `INSUFFICIENT` examples; **citation ID matching is not an independent semantic validation**. Blind human and/or independently reviewed evidence probes must determine faithfulness, completeness and sufficiency separately. Relevant evidence rubric: [NIST Agentic AI Evaluation Probes](https://www.nist.gov/programs-projects/building-evaluation-probes-agentic-ai).

## 3. Acceptance, reproducibility, and nonclaims

**Required controls:** same frozen underlying model and evidence, isolated calls, equal research tools/compute budget, explicit prompt identities, separate placebo, no hidden outcomes, independently audited source commitments, no repeated-source pseudo-replication, matched timestamped forecasts, and honest uncertainty handling.

**Success:** an independently verified, replicated and powered paired improvement for Orthodox versus **both** secular-rigor and placebo on the specified factual outcome, with no material regression in citation honesty or abstention. A simple advantage over an instruction-free baseline is insufficient.

**Failure / null:** equal accuracy, lower accuracy, only synthetic improvement, failure to outperform secular rigor, no differential forecasts, loss of source trust or partial data. Such a result limits the *implemented method* without deciding the truth of Orthodox theology.

**Assurance ceiling:** This infrastructure validates input structure, regression behavior and arithmetic. It does not by itself provide independent model inference access, third-party outcome verification, a blinded human review service, official ForecastBench registration, independent data custody or proof of the metaphysical axiom. None of these missing external obligations may be silently marked completed.
