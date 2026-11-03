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
