# FAR Human Reasoning Augmentation Prototype 0.1

Status: **Research-only application prototype.** This product surface is not a new
FAR Core primitive, an accepted cognitive theory, an independently evaluated
reasoning agent, or a conforming FAR-ELENCHUS-1.0 session. It reuses the approved
*question-purpose vocabulary* but deliberately does not fabricate the
commitments, proof contexts, provenance, or intake freezes required by the
canonical Socratic contract.

## Objective and user flow

1. The user records an exact initial claim, inference, confidence (0–100),
   supporting observations with source labels, challenging observations,
   premises, alternative explanations, and a falsifier.
2. A deterministic, source-preserving field-completeness check produces typed
   elicitation questions. A missing field yields a targeted question; a filled
   field does **not** make the evidence true or the inference valid.
3. The user answers at least one question and records a versioned revised
   conclusion, confidence and rationale. Original content is retained without
   silent normalization. Further revisions append events.
4. The user can export/import a JSON session and verify its declared structure,
   ordered event chain and internal SHA-256 commitments. The server retains no
   session database; the browser stores the plain-text session locally.

## API and limits

- `GET /augment`: standalone, mobile-responsive reasoning workspace.
- `POST /api/augment/start`: accepts the eight structured user-supplied fields
  (`claim`, `reasoning`, `confidence`, `supporting_evidence`, `challenging_evidence`,
  `assumptions`, `alternatives`, `falsifier`). Evidence entries carry exactly
  `statement` and `source`. The result is an unverified initial record.
- `POST /api/augment/revise`: accepts an intact session, a revised claim,
  confidence, rationale, and nonempty answers keyed by declared question IDs.
  Returns a new hash-bound event sequence.
- `POST /api/augment/verify`: checks syntax, all fields, question derivation,
  initial-basis commitment, event linkage and event hashes. This proves only
  *internal structural integrity*, not authorship or historical truth.

Initial input is limited to 500 KB, with 12 elements per evidence/text list and
20 revisions per record. Existing-history verification, revision and semantic
requests are bounded at 8 MiB: an accepted sequence can grow past 500 KB even
when every preceding request fits the initial limit. A generated history's
20 revisions contain at most 440,000 text characters; the initial basis adds
at most 57,200. Worst-case JSON surrogate-pair escaping plus metadata and one
report fits 8 MiB. Model-output and per-field limits remain unchanged.
Browser aggregate import/export is also bounded at 8 MiB and 20 reports, with
transactional storage: a size/quota failure retains the prior live and saved
workspace. Failed restoration preserves the exact saved bytes without hydrating
unverified data; retry and unverified-data download are available before explicit
removal. Malformed duplicate-key/non-finite JSON is refused.
No arbitrary text is rendered as HTML; user values use DOM `textContent`.
The page exports session data without a server-side file write.

## Execute and test

From a checkout with Python 3.11+:

```bash
python -m pip install -e commercial/far-decision-integrity -e commercial/far-demo
python -m unittest discover -s commercial/far-demo/tests -p 'test_augmentation.py' -v
uvicorn far_demo.app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/augment`. The app's existing deployment entrypoint
`far_demo.validation_app:app` imports the same underlying FastAPI app, so the
research route is available there too without replacing validation feedback.

## Assurance and evaluation boundary

The tool checks recorded omissions, not semantic sufficiency. The existence of a
source label is not independent verification. Confidence is self-reported; the
system computes no calibration or correctness outcome. SHA-256 is unkeyed and
can be recomputed by a determined editor, so this is *not* a signed audit trail.
Local browser storage, web host request logs, and any backups are privacy
surfaces; do not enter secrets. No autonomous model, external retrieval,
independent experiment, or AI provider inference is executed by this prototype.

Its outcome is an inspectable and testable **human-operated reasoning loop**.
Empirical augmentation claims still require frozen, independently adjudicated
comparisons against both unaided reasoning and a strong generic AI comparator,
including retained unassisted performance on later tasks. Governed EFR studies
remain distinct and unexecuted; this prototype does not modify them.

## Model-directed semantic reasoning (Research extension v0.2)

The optional model lane interprets the *meaning* of the submitted claim,
reasoning, evidence labels, and existing revisions. It asks for a structured
critique including inferential gaps, alternative hypotheses, falsifiers, and
concrete follow-up questions. It calls a real, operator-configured Chat
Completions-compatible language model when credentials and a provider are
available. The original deterministic questionnaire remains functional with no
provider configured.

The model output is adversarially validated before it reaches the browser:

- Each finding must cite one to three **exact substring quotations** from an
  allowed, versioned input field. Invented quotations, paths, duplicate keys,
  unknown categories, oversized responses, missing fields, and malformed JSON
  are rejected with a failure response; the server never substitutes a canned
  finding as if inference succeeded.
- Interpretations, sources and quote references are not treated as verified
  facts. A quote match establishes only that a phrase exists in the submitted
  data, not that the proposed critique is sound. A model can still misunderstand
  even when every quote is accurate.
- Every report binds to the exact SHA-256 of the session snapshot and the
  original basis, names its model and prompt version, records a model-output
  digest, and preserves its own integrity digest. Later revisions can replay
  and validate reports associated with earlier revision prefixes.
- User reasoning remains untrusted input, never system instructions. Model
  findings cannot change canonical FAR assertions, user commitments, decision
  status, accepted theory or an existing revision. Any human decision remains
  recorded by the human.
- Model responses are read once, with redirects disabled, a 30-second timeout,
  64 KB response limit, up to five bounded findings, and no network tools.
  There is no guarantee that a configured model adheres to the prompt, and a
  rejected output is an observed failed run, not a verified inference.

### Configure a model provider

Run this on the machine hosting the FastAPI demo; never expose the provider API
key in the browser or bundle. The model/provider credentials are not included
in the source package.

```bash
export FAR_SEMANTIC_URL='https://api.openai.com/v1/chat/completions'
export FAR_SEMANTIC_MODEL='your-available-model-id'
export FAR_SEMANTIC_API_KEY='your-provider-key'
export FAR_SEMANTIC_ACCESS_TOKEN='a-new-random-secret-of-at-least-16-characters'
uvicorn far_demo.app:app --host 127.0.0.1 --port 8000
```

For an installed local Ollama model, instead point `FAR_SEMANTIC_URL` to
`http://127.0.0.1:11434/v1/chat/completions`, select the locally installed model
name, and omit `FAR_SEMANTIC_API_KEY` if the local provider does not require one.
A token is always required to authorize generation requests. Supply the
*workspace access token*, **not the provider key**, in the UI's masked token
field. The token stays in browser memory and is transmitted only to this app's
same-origin server, not forwarded to the model provider. Use transport security
and authorization at your hosting ingress; never expose the unprotected demo to
untrusted users. A long, random access token is recommended.

The only allowed provider URL schemes are HTTPS, or HTTP to the server's own
loopback host. URLs with embedded credentials, queries or redirects are not
accepted. When `FAR_SEMANTIC_URL` points to `api.openai.com`, the request uses
`max_completion_tokens`; other OpenAI-compatible services default to
`max_tokens`. Set `FAR_SEMANTIC_OUTPUT_TOKEN_FIELD` to one of those two values
when the selected provider requires the other spelling. JSON mode is requested
and the returned payload is validated independently.

### Semantic API

- `GET /api/augment/model/status` returns only configuration availability and
  model name; it does not probe model performance.
- `POST /api/augment/semantic` takes `{ "session": <valid session> }` and the
  `X-FAR-Augment-Token` header. It produces a source-bound semantic report or
  returns a non-success response if the provider or validator fails.
- `POST /api/augment/semantic/verify` takes `{ "session": <valid final session>,
  "report": <semantic report> }` and rechecks the report against its exact
  historic session prefix, including quoted source spans.
- Browser export v0.2 bundles the original session plus all model reports.
  Import performs both structural validation and bound-report validation.
  Legacy v0.1 session imports continue to work with no model reports.

`far-model-semantic-audit/0.1` is an additive Research reporting format. It is
not `FAR-ELENCHUS-1.0`, has no FAR Intake freeze, and does not claim that a
model interpretation is a canonical verifier result. The report status remains
`MODEL_INTERPRETATION_UNVERIFIED`; the verifier assurance level is
`MODEL_OUTPUT_STRUCTURALLY_BOUND_ONLY`.

### Evidence and tests

```bash
PYTHONPATH=commercial/far-demo/src python -m unittest discover \
  -s commercial/far-demo/tests -p 'test_*.py' -v
```

The current test suite covers the original workflow, model request formation,
provider authentication, deterministic test-double responses, source-binding,
revision-prefix replay, tampering, invalid JSON, endpoint rejection, and browser
presentation. Passing mocks do not show that a model actually ran. A live
provider call must be separately executed, logged, and checked before reporting
operational model-inference success.

### Human improvement is a distinct empirical question

A model-generated critique may improve assisted task performance while reducing
independent problem-solving ability. Test that separately: preregister independent
held-out tasks and answer rubrics; randomize participants among unaided, strong
conventional-AI, and FAR-augmented conditions; evaluate blind scored accuracy,
material error rate, calibration, burden/time, and delayed **unassisted** transfer.
Allow no post-hoc change to scoring or sample definitions. New human studies
must satisfy the current repository's governance and applicable ethics/consent
requirements; they do not silently execute or amend the existing frozen EFR
program. No empirical human-capability advantage has been demonstrated here.
