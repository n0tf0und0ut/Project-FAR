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
# For OpenAI, create a project API key via the Platform setup flow.
# Store secrets only in a local process environment or approved secret store,
# never in GitHub repository files, logs, prompts or public issues.
export OPENAI_API_KEY='YOUR_SECRET_VALUE'
# Other OpenAI-compatible providers can instead supply these variables:
# export FAR_MODEL_ENDPOINT='https://YOUR_MODEL_PROVIDER/v1/chat/completions'
# export FAR_MODEL_API_KEY='YOUR_PROVIDER_SECRET'
# On or immediately after official question-set publication, verify date and URL:
curl -fL https://raw.githubusercontent.com/forecastingresearch/forecastbench-datasets/main/datasets/question_sets/2026-11-08-llm.json -o /tmp/2026-11-08-llm.json

# Small, explicitly non-prospective rehearsal; does not qualify for official submission:
python -m evaluation.prospective_forecast_runner /tmp/2026-11-08-llm.json /tmp/far-forecast-rehearsal.json --model EXACT_MODEL_ID --rehearsal --limit 4

# Full future round, run during official forecast due date and before deadline:
python -m evaluation.prospective_forecast_runner /tmp/2026-11-08-llm.json /tmp/far-forecast-2026-11-08.json --model EXACT_MODEL_ID
```

Before full execution, verify model costs, question count, output coverage, budget, tokens and available time. **A 500-question set expands into more than 500 forecast units when dataset questions require multiple resolution horizons; the three arms require three separate model calls per unit. The cost must be calculated from the verified real-data audit before execution**; this is not a free built-in ChatGPT inference capability. The official due-date restriction is strictly enforced in UTC. The default endpoint is `https://api.openai.com/v1/chat/completions` and the runner accepts `FAR_MODEL_API_KEY` or `OPENAI_API_KEY`; explicitly select an authorized, billable `--model`. The repository does not expose model credentials or automatically run this costly full round. Full output is labeled `PRE_SUBMISSION_REQUIRES_EXTERNAL_LOCK`, not `SUBMITTED` or `VERIFIED`; partial outputs are non-submittable. Preserve raw bytes and commit/hash the generated artifact in an independently timestamped location before resolution.

**Record original external registration time** and a SHA-256 of the locked protocol separately. Having `registered_at` as a string is not proof that it was preregistered.

### Prepare official ForecastBench files (no upload)

`evaluation/forecastbench_export.py` transforms a complete locked three-arm
FAR output into **exactly three separate ForecastBench-shaped JSON files**.
It rejects partial and rehearsal outputs, duplicate/missing forecasts,
out-of-range probabilities and unsafe organization names. It uses the real
underlying model ID with an arm-specific prompt suffix; verify that every
declared model and organization field is accurate before submission.

```bash
python -m evaluation.forecastbench_export /tmp/far-forecast-2026-11-08.json /tmp/forecastbench-submissions --organization YOUR_REGISTERED_TEAM --model-organization REAL_MODEL_CREATOR
```

The exporter does not submit anything, certify the model or validate official
participation. Use the [ForecastBench submission instructions](https://github.com/forecastingresearch/forecastbench/wiki/How-to-submit-to-ForecastBench)
and approved upload destination to submit files before the due deadline. The
actual forecast records and hashes must also be retained independently. Do not
submit an archived or late output by overriding a status field.

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

The current 200-case minimum is not a powered confirmatory sample. The historical 535–1,486 normal-approximation estimates (paired SD 0.15–0.25, expected improvement 0.02) plan 80% per-contrast detection power **against zero**, not power to meet the registered 0.02 confirmation margin. Use `recommended_minimum(delta=<expected true improvement>, confirmation_margin=0.02, paired_sd=<pilot estimate>)`; the expected improvement must exceed the confirmation margin. Expected improvement 0.04 with margin 0.02 yields those same sizes. At true improvement 0.02, increasing sample size cannot achieve 80% power to place the upper bound below -0.02. An actual pilot and prospective freeze must establish effect, variance, dependence and joint-power assumptions before confirmation.

### Verified October 31, 2026 intake checkpoint

Source audit: `evaluation/intake/forecastbench-2026-10-31-source-audit.json`.
The official previous `2026-10-25-llm.json` question set is present
in the organizer's public repository at Git blob
`d2f8e23707fd0859bf78d77fefbf1b74cbc8aabb` (1,473,008 bytes),
but is **past its authorized October 25 due date**. The expected
`2026-11-08-llm.json` URL returned **HTTP 404** on October 31.
The next official round therefore cannot yet be executed, scored or
submitted. Registration/approved upload destination are not verified;
no model API credential is available to this work session. A connected
OpenAI Platform key-setup UI has been surfaced for user-controlled
credential creation; no secret is obtained by the FAR code without
the user placing it into their chosen secure runtime environment.

The earlier prompting design had an unfair differential: only the
Orthodox arm explicitly repeated honesty and no-overclaiming guidance.
This was corrected **before any live forecasts**: every arm now receives
identical evidence-integrity and correction obligations; the prompt
treatment is confined to a declared interpretation profile. The
resulting prompts are not exactly token-balanced and should be
subjected to a blinded length/style-matched placebo robustness test.

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

## November 3 source-linked review corrections

Reviewed head: `837a6a1b36642f84fd193c2271ff407ff99240be`.
These are pre-execution software/planning repairs; real prospective forecasts
and independent future outcome adjudications remain zero.

| Finding / original source | Reproducer and before result | Correction and verification |
| --- | --- | --- |
| WORLD-RESPONSE-001 / comment 4458887679, thread PRRT_kwDOTH_vCM6zRnpQ | An output with leading whitespace, changed key order, `5e-1` and Unicode retained parsed fields and a hash but discarded the text needed to verify that hash. The new preservation regression failed. | Retain the exact completion message text and its UTF-8 SHA-256 in every prediction. Before export or resolution joining, replay its hash, parsed probability and reasoning; missing, modified and misgraded originals are rejected. The scored `artifact_sha256` refers to the retained original forecast record, which must accompany a scored study. It does not authenticate execution or the HTTP transport envelope. |
| WORLD-POWER-001 / comment 4458887688, thread PRRT_kwDOTH_vCM6zRnpV | The documented 951-case calculation sized a 0.02 effect against zero while acceptance required upper bounds below -0.02. A new boundary test failed before correction. | Preserve the acceptance rule and historical zero-null figures, add an explicit confirmation margin to planning, reject expected effects at/below it, and document detection versus confirmation and per-contrast versus joint power. Expected 0.04, margin 0.02 reproduces the former 951 calculation. |
| WORLD-RESPONSE-002 / follow-up CLI reproducer | A malformed second completion discarded both its raw text and the preceding valid response. An existing result path still caused all model calls before overwrite refusal. Both new regressions failed. | The CLI reserves a new `.responses.jsonl` sidecar exclusively and appends/flushed exact response receipts before parsing. Failed partial runs keep their receipts and cannot be silently retried under the same identity. Existing result or receipt paths refuse before model construction/execution. |
| WORLD-FACT-001 / actual CLI reproduction | `python -m evaluation.factual_investigation_runner --help` raised `UnboundLocalError` because `os.getenv` preceded a local `import os`; the factual CLI could not start. | Move the import to module scope. The regression executes actual help and a full scripted CLI run; existing output is rejected before backend construction. |
| WORLD-FACT-002 / corresponding raw-evidence/scorer audit | Factual responses also discarded original text; the scorer accepted status/citation/rationale edits without replaying their response hash. Invalid later completions discarded earlier outputs. | Retain exact factual completion text, replay its hash and parsed fields before scoring, and preserve CLI response receipts before parsing. Inconsistent grade edits are refused; genuinely unsupported provider responses remain scored as errors. |

Original negative observations and the October source-intake failure are retained.
The runner's exact completion text is preserved without JSON reserialization;
the envelope returned by an external HTTP service is a distinct provenance
surface. No previously frozen forecast file or study result is rewritten.
Retain the `.responses.jsonl` receipt sidecar with every successful or failed CLI
run; a missing final result is a failed/incomplete attempt, not a scored forecast.
All 115 focused worldview/forecast/factual contract tests pass after these repairs.

**Failure / null:** equal accuracy, lower accuracy, only synthetic improvement, failure to outperform secular rigor, no differential forecasts, loss of source trust or partial data. Such a result limits the *implemented method* without deciding the truth of Orthodox theology.

**Assurance ceiling:** This infrastructure validates input structure, regression behavior and arithmetic. It does not by itself provide independent model inference access, third-party outcome verification, a blinded human review service, official ForecastBench registration, independent data custody or proof of the metaphysical axiom. None of these missing external obligations may be silently marked completed.

## November 6 intake convergence

Reviewed starting head: `a34680d52dbeb861e60d8c4e2b3a4d275fda7451`;
protected-main base: `c7456b469f9dfe88b92d0fc7a211e5c9ed64de61`.
These are software corrections before live prospective execution. No frozen
observations, prompt arms, acceptance rules or scientific outcomes change.

| Root cause | Reproducer and before result | Correction and evidence |
| --- | --- | --- |
| WORLD-JSON-001 | Conflicting repeated `probability`, `status`, citation or rationale keys selected the last value; nested duplicate backend content and repeated file keys also passed. Exponent overflow and lone Unicode surrogates bypassed the existing strict loader; excessive nesting raised an unhandled `RecursionError`. | Reuse the existing scorer `loads` across model completions, backend envelopes, question/packet files, export, resolution joining, factual scoring, source audit and confirmation. Reject duplicate keys at every nesting level, recursively require finite JSON and valid UTF-8, and normalize decoder recursion failure to the existing typed error. Raw receipt preservation remains in place before completion parsing. |
| WORLD-COHORT-001 | A dataset horizon `[null]` created an undated unit, duplicate horizons created repeated identities, and an all-excluded combination set became a complete empty run. | Require distinct date strings for dataset horizons and at least one eligible unit. Every malformed cohort is rejected before any model invocation. Valid mixed market/dataset and combination-exclusion behavior remains covered. |

The seven original adversarial tests produced **15 failed subcases and one
uncaught error** on the starting head: [original log](../../evaluation/evidence/worldview-intake-convergence-20261106/before.log).
The corrected successor passes **8/8 intake tests**, including a separate
compatibility regression for both direct-script and module forecast CLI forms:
[corrected log](../../evaluation/evidence/worldview-intake-convergence-20261106/after.log).
The complete focused worldview/forecast/factual suite passes **123/123 tests**.
All scripted model responses are synthetic software controls. This provides no
live forecasting, factual reliability, theological, commercial or causal result.
Final-head independent substantive review and protected checks remain separate.

### Preregistration boundary correction

WORLD-REGISTRATION-001 / source review comment `4494358588`, thread
`PRRT_kwDOTH_vCM60k0OP`, reviewed head
`658f160fb22b04897f9139e7347a9d323324aba5`: joining resolutions accepted
registration at 10:00:59 during collection from 10:00:00 to 10:01:00.
Already-flushed arm responses could be inspected before that declaration.
The protocol requires registration before collection, not merely before its end.

The join now checks aware timestamps with the declared ordering
`registered_at < forecast_generated_at <= completed_at`. Missing/naive starts
and reversed collection intervals fail. This checks declared chronology only;
authentic independent preregistration and timestamp custody remain unverified.

Two root-cause regressions produced **five failed subcases before correction**
([before](../../evaluation/evidence/worldview-intake-convergence-20261106/registration-before.log))
and pass afterward
([after](../../evaluation/evidence/worldview-intake-convergence-20261106/registration-after.log)).
The complete focused suite now passes **125/125 tests**. No live forecast or
frozen study is rewritten. This material correction requires fresh exact-head
independent review and ordinary protected checks.

## November 8 factual prompt-attribution correction

**WORLD-FACT-PROMPT-001** — review comment
[`4507123882`](https://github.com/n0tf0und0ut/Project-FAR/pull/600#discussion_r4507123882),
thread `PRRT_kwDOTH_vCM61CysV`, reviewed head
`3500adc6e4cc578e503e99b8fd3ee78ab812024e`.
The factual scorer replayed original response bytes but did not check their
retained prompt commitment before assigning the response to a treatment arm.
Swapping only the `neutral` and `orthodox` labels in a scripted fixture therefore
moved correct-answer totals from `{neutral: 0, orthodox: 3, placebo: 0}` to the
wrong arms while all original response hashes remained valid.

The scorer now reconstructs each case/arm prompt from the validated supplied
packet and checks `prompt_sha256` before attributing any score to that row.
Two regression methods failed with **64 assertions and zero errors** before the
source repair: the original arm-label swap and all nine rows with missing,
malformed, wrong-arm or wrong-case prompt commitments. They pass after repair;
unchanged predictions and reordered valid rows retain their scores. All **127**
focused factual/worldview/forecast tests pass, including the original raw-response
and intake regressions.

This verifies local record consistency only. A coordinated rewrite of labels and
commitments is not authenticated execution, and the check establishes no external
model, source, annotation or treatment provenance. Prompt construction, frozen
protocols, fixture bytes and historical results are unchanged; no new model call
or experiment was performed. Fresh substantive review and required protected
checks must cover the corrective head.

### Forecast attribution and export use the same prompt-binding gate

**WORLD-FORECAST-PROMPT-001** — review comment
[`4507161039`](https://github.com/n0tf0und0ut/Project-FAR/pull/600#discussion_r4507161039),
thread `PRRT_kwDOTH_vCM61C4RW`, reviewed head
`4cc2046fbe9b65e07a43281ae5868d88cb147f28`.
Forecast resolution joining and ForecastBench export checked response bytes but
never verified the retained question/prompt commitments. In a scripted two-unit
run, swapping only `neutral`/`orthodox` labels changed Brier scores from
`{neutral: 0.81, orthodox: 0.01, placebo: 0.81}` to the wrong treatment attribution;
export also accepted the relabeled responses. The earlier factual-path repair
did not cover this separate forecast path.

Newly produced forecast records explicitly declare the additive integrity profile
`FAR-WORLD-PROSP-PROMPT-BINDING/1` in `record_contract` and retain
`question_set_snapshot`. The runner takes a detached canonical-JSON copy before
the first backend call and binds the snapshot with the existing
`question_set_sha256` semantics. This is an additive record-integrity correction,
not a change to the three prompt arms, outcome rules or experimental protocol.
Historical records without that profile and snapshot fail closed at current
scoring/export; the software does not invent their missing source data or rewrite
their bytes.

One shared validator now checks the snapshot commitment, dataset/due metadata,
declared counts, exact complete unit-by-arm coverage, per-unit question hashes
and reconstructed per-arm prompt hashes before either consumer attributes
responses. Both consumers retain the existing original-response replay checks.
The six new regression methods produced **96 failed assertions and zero errors**
before repair, including the original scorer/export arm swap, and pass afterward.
Controls cover absent/malformed/changed snapshots, recomputed snapshot hashes
that contradict retained units, every row's wrong prompt/unit/arm commitment,
coverage/metadata edits, input mutation after collection starts, valid reordering
and actual collection/export/resolution CLI execution. All **133** focused
factual/worldview/forecast tests pass without skips. The earlier no-outcome test
is corrected to inspect JSON field names recursively: retained resolution-criteria
prose legitimately contains the word "outcome" and is not a resolved-outcome field.

These checks establish local consistency under the current source-defined prompt
profile only. Coherently rewriting the entire record is not authenticated external
execution; independent source truth, prior registration, model identity and
custody still require separate evidence. Frozen protocols, fixtures and results
retain their original bytes. No model call or new scientific experiment was run.
The final corrective head still requires independent substantive review and all
protected checks.
