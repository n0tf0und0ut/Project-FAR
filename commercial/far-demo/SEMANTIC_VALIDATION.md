# Model-directed semantic augmentation: verification record

Status: **Research-only implementation; one failed local-model conformance smoke**.

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
- Model quality: **NOT MEASURED**. One real local-model access/conformance call
  **FAILED** output validation; preserved evidence appears below.
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

## Follow-up review: asynchronous replacement and lossless round trips

Original reviewed head: `70eab5ed003f11741bd66edbe98989b21e2e842a`
(tree `c6abf84f77e65b3df8d56843ba09d9e9d44dbe0d`).

| Root cause / review source | Reproducer and before result | Correction and regression |
| --- | --- | --- |
| AUG-SEM-011 / 4458859142, PRRT_kwDOTH_vCM6zRjY5 | A pending revision for A overwrote a replaced workspace B. The same actual-script stale-write failure was reproduced for pending creation, import and restoration. | A workspace epoch covers every replacement intent; revisions additionally bind the original session. Stale asynchronous completions cannot mutate or persist the new workspace. Model responses retain the compatible append-only revision control. |
| AUG-SEM-012 / 4458859162, PRRT_kwDOTH_vCM6zRjZD | Individually bounded provider reports accumulated beyond the 500,000-byte import cap before the 20-report count cap. The actual-script round-trip regression failed. | A bounded 8 MiB aggregate ceiling permits 20 individually server-verified reports to import/export above 500 KB. Storage and export use the same encoding. All mutations check size and complete storage before state assignment; quota/size failures preserve prior state. |
| AUG-SEM-013 / 4458859170, PRRT_kwDOTH_vCM6zRjZI | A rejected verification fetch during page restoration deleted the existing local-storage record. The actual-script exact-byte regression failed. | Failed restoration preserves the exact original bytes and leaves data unhydrated. Retry, unverified preserved-byte download and explicit New session removal are available. Retry success preserves original bytes. |
| AUG-SEM-014 / follow-up accepted-session boundary test | Actual HTTP revision 7 accepted a 499,970-byte request, returned a 500,180-byte session, then verification rejected that accepted session with HTTP 413. | Existing-history routes use a schema-derived bounded 8 MiB payload allowance; initial submissions retain 500 KB. Accepted Unicode history can verify, revise, generate and replay a semantic report. Over-8-MiB bodies and revision 21 remain rejected. |

The shipped-script suite now contains 14 tests, including exact export/storage
byte equality, import replay, offline preservation, successful retry, all four
pending replacement paths, report count/aggregate limits and append-only revision
compatibility. A separate test constructs and verifies all 20 reports through
the real server contracts before importing/re-exporting the >500-KB bundle in
the shipped script. All 46 dependency-equipped augmentation/semantic tests pass. These
are software-integrity observations with scripted provider replies; no live-model
quality or independent human benefit is established.

## Genuine live-model engineering smoke (November 3, 2026)

One prospectively frozen, separately identified access/conformance call used the
unchanged semantic route and strict validator with official
`Qwen/Qwen2.5-0.5B-Instruct` revision
`7ae557604adf67be50417f59c2c2f167def9a775`, BF16 CPU inference. The real model
generated 218 tokens from 525 input tokens in 25.259 seconds. The local provider
returned HTTP 200; FAR returned HTTP 502 because the actual output violated the
contract (Markdown-fenced JSON, missing `open_questions`, malformed anchors).
There was no outcome-based retry, scripted replacement or validator relaxation.

Thus live inference access is established for this engineering configuration,
while end-to-end output conformance **FAILED**. Semantic accuracy, strong-provider
performance, independent human improvement and commercial benefit remain
unestablished. This small model and single authored input cannot support a broad
quality verdict. External API charge was zero; total compute/human cost was not
measured. Setup time is separate from generation timing.

[Full preserved summary](evaluation/semantic-live-smoke-20261103.md) and
[immutable raw evidence ZIP](evaluation/semantic-live-smoke-20261103.zip), SHA-256
`0a6ca2e36226423498b7726e24f86eb10279d5d2217018a121f1e6291a737bf0`,
retain the pre-generation freeze, exact client/source hashes, official model and
weight identities, thin local transport source, raw request/output, token IDs,
HTTP/validation outcome, environment and deterministic byte/sequence verifier.
The ZIP contains an engineering receipt, not trusted execution attestation or an
externally independent study. No model checkpoint or production dependency was
added to FAR.

## November 6 input-boundary corrections

Reviewed source: `9ce45e13613c18d9b854ba01f8fc974cb6a3cc8f`. These are software
corrections after the recorded live smoke; its frozen source hashes and failure
remain historical evidence for that earlier implementation.

| Root cause | Before correction | Correction and bounded verification |
| --- | --- | --- |
| AUG-SEM-015 — decoder failures escaped invalid-input contracts | A 20,001-byte array nested 10,000 levels raised uncaught `RecursionError` at input and model-output boundaries. Provider envelopes also accepted non-finite numeric constants or overflow in ignored fields. | Shared package-local strict decoding rejects duplicate members, constants, overflow and unsupported nesting. Actual request tests require HTTP 400; malformed model output yields HTTP 502; mocked transport exercises malformed provider envelopes without model inference. |
| AUG-SEM-016 — non-ASCII values reached string-only HMAC comparison | Non-ASCII access headers or report digests raised `TypeError`, producing a server failure before an authorization/integrity verdict. | Tokens compare UTF-8 bytes; report digests must be 64 lowercase hex characters before constant-time comparison. Actual-route regressions require HTTP 401 and HTTP 422 respectively. |

The dependency-equipped demo suite passes **71 tests**, including the unchanged
browser round trips, persistence races and scripted-provider controls. No new
live experiment, semantic effectiveness or customer-value claim follows.
