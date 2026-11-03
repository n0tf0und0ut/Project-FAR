# Model-directed semantic augmentation: verification record

Status: **Research-only implementation; no live external model execution**.

- Source: optional hosted FAR Demo application, separate from FAR Core theory.
- Model provider integration: HTTPS or loopback Chat Completions compatible;
  source text carried as JSON user data under a separate fixed system prompt.
- Authentication: operator-configured access token is required for the generation
  endpoint; the provider secret is never returned to the browser.
- Findings: only strictly validated report fields and exact quoted user input
  spans; unknown/missing output fails closed with no synthetic substitute.
- Recorded provenance: source-session snapshot SHA, revision prefix length,
  model identifier, prompt version, model output digest, report digest.
- Local checks: `python -m unittest discover -s commercial/far-demo/tests -p 'test_*.py'`
  and `node --check` against the page script; browser smoke tests exercise
  actual handlers under Chromium with a *scripted model service*.
- Model quality: **NOT MEASURED**. Model execution on a real provider: **NOT RUN**.
- Independent human reasoning gains: **NOT TESTED**.

**Interpretation limit:** A source-anchored generated critique is not
necessarily logically correct or causally identifying. Anchor validation guards
misquotation but cannot prove the author's claim, the inference, source truth,
completeness, or calibrated model judgment. No commercial or cognitive benefit
can be inferred from successful interface tests.

## November 3 exact-head review corrections

Original reviewed head: `fcf6860ea24e04252d4f7124ce00c6a6391cfa8f`.
No live-model effectiveness is inferred from these software corrections.

| Root cause / review source | Reproducer and before result | Correction and regression |
| --- | --- | --- |
| AUG-SEM-007 / 4458762716, PRRT_kwDOTH_vCM6zRVAx | Actual page script accepted a 21st report although import/restoration permit at most 20; Node regression failed. | Reject before calling the provider and recheck before appending. `test_report_limit_prevents_unrestorable_twenty_first_analysis` verifies no provider request or extra report. |
| AUG-SEM-008 / 4458762734, PRRT_kwDOTH_vCM6zRVA- | A pending session A model response was appended/persisted after replacing the workspace with B; Node regression failed. | Capture originating snapshot and report collection; discard responses after replacement. A separate regression preserves valid responses across append-only revision. |
| AUG-SEM-009 / 4458762747, PRRT_kwDOTH_vCM6zRVBJ | Revisions with opposing counterevidence answers and confidence 20 versus 95 produced identical `_refs`; semantic regression failed. | Include every revision's confidence and question answers as addressable source strings; exact new-answer quotations pass verification. |
| AUG-SEM-010 / 4458762770, PRRT_kwDOTH_vCM6zRVBW | Core-only semantic test import failed without HTTPX, reproduced in the clean base runtime. | Match the augmentation suite's explicit optional FastAPI/HTTPX dependency guard. Dependency-equipped tests still execute. |

The shipped browser script is executed under Node with DOM and asynchronous
provider test doubles, covering both failures and the append-only revision
control. Python provider replies remain scripted. Final-head hosted checks and
independent substantive review remain separate obligations.
