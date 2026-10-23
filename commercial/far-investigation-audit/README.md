# FAR Investigations: bounded auditable evidence and inference checks (Research prototype)

**Status:** experimental downstream commercial/research component. It does **not** modify or claim Accepted FARA/FAR/FARO authority, the frozen FAR-CORE theory, the EFR campaign or the 60-case confirmatory benchmark. **It does not independently establish real-world truth.** Version 0.4 includes bounded text, caption, local-document, and optional media/URL intake; it does not establish open-domain ingestion reliability or independently correct semantic adjudication.

Current engine and local-service revision: **0.4.4**. Generated heuristic readings
are capped at 12, with omitted candidates disclosed in the report. Structured
quantities must cover a complete numeric literal in the original source, including
its sign and decimal digits; clipping the claim quotation cannot strip those
characters. Grouped, scientific, fractional, ratio and identifier spellings cannot
be checked by selecting a supported substring. Generated sentence candidates over
1,000 characters are omitted and disclosed, preserving the original offsets of
retained claims and evidence. A source with no eligible sentence candidates
requires explicitly supplied bounded excerpts. Source numbers beyond the Decimal
parser's range yield explicit structured unavailability. Replay requires the
originating engine revision; these repairs do not upgrade factual assurance.
The separate checker derives numerical-result membership from input evidence,
and truncated discovery HTTP responses remain redacted workflow failures. Numeric
terms separated only by punctuation, symbols or whitespace are conservatively
treated as one unsupported group: this rejects ambiguous mixed fractions,
space grouping and arithmetic fragments without interpreting their semantics.
Adjacent numeric lists can therefore require an explicitly disambiguated input.
The audit producer and replay share duplicate-rejecting JSON parsing, malformed
enums yield bounded input errors, and the separate checker rejects undeclared
report fields at report, claim and evidence levels.

This implements a concrete, independently replayable *formal* audit of two distinct steps:

1. **Evidence → premise.** Validate an exact quoted span of a content-addressed source and, **when the auditor is supplied a reviewed/inspectable propositional formalization of that source content**, decide whether the *formalized evidence* entails or contradicts the *formalized premise*.
2. **Premises → conclusion.** Exhaustively check entailment across all valuations of the supplied propositional atoms and return a countermodel when entailment fails. Inconsistent premises never receive a vacuously favorable result.

Different possible interpretations are checked separately; source provenance, asserted evidence relationships, uncertainty, source-origin grouping, and time cutoffs remain visible. No composite True/False verdict is produced. An assessor's label does not override the formal relation.

## Run

Python 3.11+, no third-party dependencies:

```sh
python commercial/far-investigation-audit/cli.py commercial/far-investigation-audit/examples/causal_jump.json --output /tmp/far-audit.json
python -m unittest discover -s commercial/far-investigation-audit/tests -p 'test_*.py' -v
```

The input (`far-investigation-audit/0.1`) is a JSON file containing:

- `investigation_id`, an ISO 8601 UTC `as_of` cutoff and a dictionary of named propositional `atoms` with human-readable definitions;
- `sources`: `id`, UTF-8 `text`, its SHA-256 hash, `published_at`, `captured_at`, and a **reported, not authenticated** `origin_id` (nullable when unknown);
- `claims`: source-anchored exact quote spans (`start` inclusive, `end` exclusive), natural-language `text`, propositional `formula`, and `mapping_status` (`unreviewed` or `review_recorded`);
- `evidence`: exact quote spans, target `claim_id`, author-proposed relation and optional propositional `formula`. Without the formula, the evidence's semantic relation is explicitly untested;
- `interpretations`: each named candidate has `premises`, `conclusion`, and `mapping_status`. Distinct readings cannot be merged into a majority vote;
- `unknowns`: open questions retained verbatim in output.

Formula operators are JSON `{"atom":"P"}`, `{"not": EXPR}`, `{"and":[EXPR,EXPR]}`, `{"or":[EXPR,EXPR]}`, and `{"implies":[EXPR,EXPR]}`. Variables must be declared. This finite propositional subset cannot establish causal identification, quantifiers, open-world generalizations, statistical evidence quality, social/normative inference, or natural-language intent. It rejects unverifiable or malformed source spans/hashes, limits source size and graph complexity, and returns `NOT_CHECKED_ATOM_LIMIT` for more than 12 distinct variables rather than silently asserting validity.

**Temporal discipline:** only source snapshots *both published and captured* by `as_of` are eligible for evidence→premise formal support. Missing dates remain `UNKNOWN_TEMPORAL_ELIGIBILITY` and cannot satisfy that gate. A claim cannot corroborate itself by citing its exact same source span. Later archives or unknown historical editions require separate version-specific substantiation; the conservative exclusion avoids hindsight leakage. The cutoff does **not** prove that the language model developing a formalization lacked future parametric knowledge.

**Replay:** input hash, method version, per-reading checked assignment count, returned countermodel and deterministic report hash are included. A changed bundle produces a changed input hash; hashes prove consistency of supplied bytes, **not** identity/authenticity or independence of the real source, semantic correctness of atom mappings, or correctness of a third-party assessor. `mapping_status=review_recorded` is an *unauthenticated claim of review*, not independent review evidence. Fail-closed `InvalidBundle` errors are not silently turned into a "verified" result.

## Assurance boundary

For a reading with status `ENTAILS_CONDITIONALLY`, the **formal formulas** have been checked to entail the formalized conclusion, conditional on the mappings, premises, interpretation and bounded propositional semantics. It does *not* follow that the natural-language argument is deductively valid or its conclusion true. `FORMALLY_SUPPORTS_IF_MAPPINGS_CORRECT` likewise establishes only formal entailment between **supplied** formalizations, not that the cited words mean those formulas, represent reliable facts, or are independently corroborated.

Before any commercial truth-oriented claim, FAR additionally needs (1) real media/source capture and authentic historical versions, (2) independently checked quote-to-proposition mapping, (3) retrieval and adversarial evidence assessment, (4) source dependence/copying analysis, (5) causal/statistical/nonmonotonic validators, (6) authenticated reviewer records, (7) head-to-head blind evaluation against strong matched systems, and (8) reliable operational delivery and buyer proof. Those capabilities are not simulated here.

## Existing research used; no novelty claim

- W3C [PROV-O](https://www.w3.org/TR/prov-o/): entity/activity/agent provenance and derivation chain. This implementation adopts content-addressed source snapshots and inspectable transform boundaries, but does *not* claim PROV-O compliance.
- [Argument Interchange Format](https://doi.org/10.1017/S0269888906001044) and [Argument Web](https://pmc.ncbi.nlm.nih.gov/articles/PMC6979725/): premise, inference-scheme, conclusion and conflict separation. JSON `interpretations` is only a bounded typed application, **not** an AIF serializer.
- [AVeriTeC](https://aclanthology.org/2024.fever-1.1/): fact-verification evaluations must measure evidence as well as verdict correctness. This prototype contains no automated AVeriTeC run.
- [No Hindsight for LLM Fact-Checkers](https://arxiv.org/abs/2610.04888): explicit point-in-time source eligibility to prevent post-claim evidence from silently establishing claims.
- [Rethinking Inline Citation Verification](https://arxiv.org/abs/2610.05355): do not equate citation existence with citation support; expose review and intent boundaries.
- [Auditable Claims about AI Agents](https://arxiv.org/abs/2610.07459): source claims must declare scope, evidential records and explicit decision checks before verdict, including coverage versus integrity.
- [Same Claim, Different Interpretations](https://arxiv.org/abs/2610.20457): alternative interpretations require outcome-sensitivity testing; recording interpretations alone is not an accuracy guarantee.
- [Argument Graph Uncertainty](https://arxiv.org/abs/2610.20328): structured argument uncertainty can complement but not substitute for verified entailment or source authenticity.
- Project FAR [Saturation Baseline v0.5](../../docs/architecture/saturation-baseline-v0.5.md): provisional capability classes, no implicit collapse of claim/evidence/inference status. This implementation uses existing extension points rather than changing the baseline or canonical core.

The next independent test is a blinded real-cases comparison assessing attribution fidelity, evidence-to-premise judgments, inference validity, abstention, false certainty, cost and latency. The registered #518 and EFR experiments remain unchanged and unexecuted by this component.

## 0.2 bounded structured-evidence extension

This Research-only extension adds a **second, independently typed computation lane** for numeric facts in frozen JSON snapshots. It complements—not substitutes for—the propositional evidence/inference checks above. The existing `far-investigation-audit/0.1` input envelope is backward-compatible: old files without structured checks are still checked as before. The engine identifies itself as `far-investigation-audit/0.2.0`. No canonical FAR IR or Accepted-theory schema was changed.

Use `data_check` on an `evidence` record **instead of** `formula`, paired with a `quantity` record on its target `claim`. An example is [examples/structured_tally.json](examples/structured_tally.json):

```json
{
  "quantity": {"value":"2", "number_span":{"start":0,"end":1}, "unit":"experiments"},
  "data_check": {"operation":"count_where", "pointer":"/experiments", "where":{"field":"passed", "equals":true}}
}
```

The snippet shows two fields belonging to **different** records. The `number_span` must point to the exact literal number in the claim's source quotation. `data_check` reads the already-hashed JSON evidence source, follows an RFC 6901 JSON Pointer (with bounds), and computes:

- `count_rows`: exact length of a selected array;
- `count_where`: exact type-safe equality count over a required field in every selected object (boolean `true` is not number `1`);
- `sum_field`: exact decimal sum over required JSON numeric fields, with finite digit/exponent bounds and a controlled precision context.

Ambiguous duplicate JSON keys, absent fields, non-numeric sums, invalid JSON pointers and unsupported forms fail closed or report `STRUCTURED_UNVERIFIABLE`. Inputs are limited to 2 MB, each source to 200 KB, selected arrays to 10,000 rows, and bounded finite decimals. Missing values are *not* quietly treated as zero. A mismatch produces an actual counter-result from the supplied dataset, rather than a model verdict.

Every audit also has a total budget of 8,000,000 worst-case propositional node visits across evidence and interpretation checks. The estimate multiplies formula-node count by valuation count; repeated identical inference pairs are computed once per audit. Exceeding the aggregate budget rejects the investigation without asserting a logical result. File entry points check regular-file sizes before allocation and read at most their limit plus one byte to detect growth. PDF and media extraction and raw hashing use the same bounded snapshot. The separate checker recomputes structured failure reasons and temporal chronology and compares formal results with exact JSON types.

The new per-claim `structured_value_checks` report is **separate** from the propositional `status`. It may show `STRUCTURED_VALUE_MATCH_CONDITIONALLY`, `STRUCTURED_VALUE_MISMATCH_CONDITIONALLY`, `CONFLICTING_STRUCTURED_VALUES`, or `NOT_ESTABLISHED`. Even a numeric match means only that the disclosed operation on the supplied frozen JSON produces the number recorded in the claim quotation. It **does not** verify the dataset's completeness, representativeness, origin, semantics of its columns, proper choice of statistic, associated source's authenticity, or real-world truth. The checker does not infer that a policy caused an observed change or that a reported study generalizes beyond its observed population. The original inference report separately tests whether the formal *premises* entail the formal *conclusion*.

To inspect the structured demonstration and replay the output:

```sh
python commercial/far-investigation-audit/cli.py commercial/far-investigation-audit/examples/structured_tally.json --output /tmp/far-structured-report.json
python commercial/far-investigation-audit/verify.py commercial/far-investigation-audit/examples/structured_tally.json /tmp/far-structured-report.json
```

The verifier independently **re-runs the deterministic code path**, checking the entire output against an independently provided bundle; it rejects even a report whose attacker has recalculated its own hash. This is reproducible computation, **not** independently authored verification software, proof of independent source provenance, or trusted third-party attestation.

### Exact local source capture

The optional offline importer constructs a SHA-256-bound source snapshot and, where specified, a unique exact quotation anchor:

```sh
python commercial/far-investigation-audit/capture.py document.txt --id source_1 --quote 'The observed quantity increased.'
```

The importer never fetches remote URLs or executes content; input must be UTF-8 text or JSON. The `captured_at` field records the time the command ran. Its `published_at` remains `null` unless a publication date is **explicitly supplied** with `--published-at` (the resulting date is marked unverified). The importer cannot authenticate historic availability, source lineage, or publisher identity. Unknown historical publication dates cause the existing point-in-time evidence gate to abstain rather than count the source as admissible. Ambiguous repeated quotations require `--start` to specify the exact character offset.

### Prior methods incorporated

- [FEVEROUS](https://fever.ai/dataset/feverous.html) explicitly represents factual verification evidence as sentences **and cells in tables**, with annotated numerical reasoning cases. FAR's bounded numerical path is an original *implementation of standard structured-data arithmetic*, not a novel verification algorithm or an evaluated FEVEROUS system.
- [TabVer: Tabular Fact Verification with Natural Logic](https://doi.org/10.1162/tacl_a_00722) demonstrates that table verification requires controlled operators and inference procedures; its reported performance does not transfer to this module without evaluation.
- [W3C PROV-O](https://www.w3.org/TR/prov-o/) motivates distinguishing a recorded computation and its input snapshot from the external authenticity and acquisition chain. This module does not claim PROV compliance or independently authenticated evidence.
- [AVeriTeC](https://aclanthology.org/2024.fever-1.1/) motivates separating evidence sufficiency, claim interpretation and downstream verdict quality in future independent evaluations. No performance claim is made here.

**Remaining work:** reliably retrieved and permissioned documents/media, automatic but challengeable natural-language claim mapping, authenticated reviewer attestations, independent source and temporal provenance, causal/statistical identification checks, external blind evaluations and user/customer validation. `0.2` adds only the bounded mechanical check described above, not all of these prerequisites.

---

## 0.3 end-to-end research integration (NOT a validated consumer fact-checker)

Version 0.3 extends the previously bounded core with a locally runnable complete
**source-to-reviewable-report transaction**. It is a comprehensive experimental
implementation path, not a claim that all supplied meanings or conclusions are
verified. All new behavior remains outside FAR Core's Accepted theory and is
unmerged Research until ordinary repository review and validation succeeds.

### Quick start (Python 3.11+)

From this repository's root:

```sh
python -m pip install -r commercial/far-investigation-audit/requirements-dev.txt
python commercial/far-investigation-audit/full_cli.py \
  commercial/far-investigation-audit/examples/full_speech.json \
  --output /tmp/far-case-1
python commercial/far-investigation-audit/full_cli.py --verify /tmp/far-case-1
python commercial/far-investigation-audit/evaluate.py \
  commercial/far-investigation-audit/examples/diagnostic_cases.json
python commercial/far-investigation-audit/webapp.py
```

The web UI is available at `http://127.0.0.1:8765/` only. It has no
multi-user authentication, production governance or durable storage. Never
expose it publicly or send regulated/private content without appropriate
independent security controls.

### Input modes

The `full_cli.py` request is JSON and specifies `source` and optional
`evidence_sources`. Use `kind`: `text`, `html`, `srt`, `vtt`, `url`, `youtube`,
`pdf_file` or `media_file` (CLI-only local file paths). For example:

```json
{
  "investigation_id": "hypothetical_case",
  "source": {"kind": "text", "text": "The sample was small. Therefore the treatment always works."},
  "evidence_sources": [{"kind": "text", "text": "A study recorded ten observations."}]
}
```

- Text, HTML and SRT/WebVTT are accepted without external accounts. Exact text
  spans or cue time ranges are preserved, while extraction/translation fidelity
  remains unverified. HTML extraction excludes scripts/styles/forms/nav.
- HTTPS article fetching is off by default and requires `--allow-network`.
  It allows only credential-free public DNS HTTPS on port 443, explicitly
  validates and pins resolved public addresses through TLS, caps response
  bytes, checks media type, and independently revalidates redirects. It does
  **not** process arbitrary private network URLs, PDFs fetched remotely,
  redirects to private addresses, or images. A live fetch is a present-time
  capture, not an authenticated historical snapshot.
- YouTube requires `--allow-network`, an optional installed `yt-dlp`, and a
  usable public English VTT caption track. No download of full copyrighted
  videos, DRM bypass, guaranteed diarization, or arbitrary platform promise.
  If captions are absent, processing fails explicitly; it does not invent a
  transcript.
- Local PDFs (`pdf_file`) use `pypdf` text extraction (max 30 pages / 8MB)
  and explicitly abstain on image-only PDFs; visual/table fidelity is not
  established. Audio/video local files (`media_file`) require ffmpeg and an
  explicitly authorized speech-to-text provider (`--allow-model`); the model
  output is unverified transcription. No speaker attribution is inferred.
- The local web UI accepts text/HTML/captions, public HTTPS article/YouTube
  URL (if network enabled at the server), or bounded local file uploads.
  External transcription in the UI additionally requires explicit user
  consent and the operator-set `FAR_LAB_MODEL=I_ACCEPT_EXTERNAL_TRANSCRIPTION`.

Remote acquisition is deliberately off until explicitly authorized. CLI use
of `--allow-network` can send queries/URL requests to third-party services;
`--allow-model` can send provided texts and audio to the model provider. These
are **operational/financial/privacy decisions**, not proof obligations.

### Three candidate-interpretation paths

`proposal_mode=heuristic` (default) extracts sentence candidates and marks
lexical evidence matches **unknown**, never supported or refuted. It notes
possible discourse markers like "therefore" but a propositional countermodel
cannot by itself certify an actual invalid natural-language argument.

`proposal_mode=supplied` permits structured human-authored claim spans, explicit
formulas, evidence relations and structured data checks. It rejects invented
quotes, undeclared atoms, invalid formula trees, ambiguous repeated quotations
without offsets and missing argument references. The bundled
`examples/complete_evidence_case.json` demonstrates a deterministic
`count_where` over a frozen JSON table and a separately checked inference.
An explicit `quantity` and `data_check` are *claims about that snapshot and
chosen computation*, not verified facts about the world.

`proposal_mode=openai` is optional CLI-only, requires `--allow-model`, the
operator's separately configured OpenAI SDK API credentials, and uses a
constrained JSON proposal prompt. The proposed claim and evidence spans must
match actual retained input text byte-for-byte after UTF-8 decoding. Model
claims and ratings do not acquire authority from the provider. The UI cannot
silently spend money or send text to a model for claim extraction.

For open-web **discovery**, set `discovery=tavily`, plus `--allow-network` and
operator-managed `TAVILY_API_KEY`. Searches are limited to three queries and
three results each, and snippets remain unverified leads. Setting
`expand_discovery=true` explicitly fetches at most four permitted public HTTPS
links into immutable source snapshots, which an optional proposing model can
read. Search retrieval does not provide exhaustive recall, publication-time
proof, source independence, faithful formalization, or reliable truth labels.

### Interpretation and assurance dimensions

- Claim, evidence and inference judgments are distinct. Formal inference is
  checked by exhaustive finite Boolean assignments (at most 12 atoms), and
  countermodels are returned, while semantic mapping fidelity remains **not
  independently verified**.
- A second, differently implemented finite truth-set/bitmask checker verifies
  propositions and returned countermodels on replay. That is design-diverse
  **internal** software cross-validation, not external independent review.
- A proposed interpretation card can separately retain subject, population,
  time, geography, quantifier, measurement, comparison, threshold and
  assumptions, each marked stated/inferred/default/unknown. Differences in
  cards do not automatically imply different truth values.
- Numerical records can be recomputed against a supplied JSON snapshot even
  when the source's historical eligibility is unknown. These become
  `SNAPSHOT_ONLY_VALUE_CHECK_TEMPORALLY_INADMISSIBLE`, not evidence support.
- Every source carries an exact hash and acquisition/normalization method.
  Captured-at is observed for live acquisition, but `published_at`, author,
  provenance and source independence are **not cryptographically verified**.
  Historical/as-of constraints prevent using future or undated evidence as
  proof of historical claims. As-of overrides on live remote capture are refused.
- A separate Ed25519 review attestation can be signed with a reviewer-owned
  private key and checked against the exact input/report hash. The signature
  proves key possession and that the recorded decision is unchanged. It does
  **not** prove reviewer identity, independence, competence or correctness.

### Reproducible bundle and review

`full_cli.py` writes into a **new directory** only: `input.json`, `audit.json`, `proposal.json`, `acquisition.json`,
`critical_questions.json`, `report.md`, optional `discovery.json`,
optional signed `review.json`/`review_verification.json`, and a `manifest.json`
binding every file's SHA-256. `--verify` checks all files, recomputes the full
report, separately checks bounded formal entailment/countermodels and validates
any signed review. It rejects omitted/extra files, symlinks, source tampering
and changed decision/status fields. It cannot prevent a malicious actor from
creating an entirely new internally self-consistent package; key-authenticated
publisher or custodian provenance would be needed for that stronger guarantee.

To add an independently produced reviewer record, prepare `review.json` with
`schema: "far-review-attestation/1.0"`, `input_sha256`, `report_sha256`,
`reviewer`, and bounded `decisions` (each with an audit object ID and one of
`agree`, `disagree`, `not_reviewed`, `requires_more_evidence`). Then use your own
Ed25519 PEM private key:

```sh
python commercial/far-investigation-audit/review.py unsigned_review.json \
  --private-key reviewer_private.pem --output signed_review.json
python commercial/far-investigation-audit/full_cli.py request.json \
  --output /tmp/far-reviewed --review signed_review.json
python commercial/far-investigation-audit/full_cli.py --verify /tmp/far-reviewed
```

Review binding includes the report's exact bytes and therefore the clock,
method/version and input hash. Do not commit reviewer private keys.

### Validation / benchmark status

Run the exact component suite:

```sh
python -m unittest discover -s commercial/far-investigation-audit/tests -p 'test_*.py' -v
python -m compileall -q commercial/far-investigation-audit
```

`evaluate.py` runs three **project-authored synthetic conformance cases**. It
is a software diagnostic only, not a claim-verification benchmark or a
measure of external accuracy. It reports no external-accuracy value. The
registered #518 60-case benchmark and EFR-001 are separate, still subject to
their frozen controls and independent adjudication gates. No benchmark result
is manufactured by this PR.

### Research incorporated, with implementation-status boundaries

- [AVeriTeC 2024/2025](https://aclanthology.org/2025.fever-1.15/) explicitly
  couples verdict and evidence adequacy and emphasizes open-weights,
  reproducible, time/cost-limited evaluation; this implementation does **not**
  reproduce the shared-task performance.
- [No Hindsight for LLM Fact-Checkers (Oct 4, 2026)](https://arxiv.org/abs/2610.04888):
  separate claims knowable when made from later retrieved evidence. Current
  code excludes temporally ineligible evidence; model pretraining leakage is
  still outside its ability to audit.
- [Same Claim, Different Interpretations (Oct 14, 2026)](https://arxiv.org/abs/2610.20457):
  interpretation-card sensitivity deserves typed records, but the study
  did not demonstrate improved expert agreement from cards alone. Our card
  support is an engineering mechanism, not a performance result.
- [Rethinking Inline Citation Verification (Oct 4, 2026)](https://arxiv.org/abs/2610.05355):
  different citation uses and reviewer approaches motivate source-intent
  and independent human-review stages, not automatic citation-validity claims.
- [Argument Graph Uncertainty (Oct 14, 2026)](https://arxiv.org/abs/2610.20328):
  post-hoc NLI graph uncertainty is promising on bounded multiple-choice
  evaluations; it does not authenticate evidence or certify general validity.
  We do not misapply its uncertainty as a scalar truth probability.
- [Reason and Verify (2026)](https://proceedings.mlr.press/v318/khan26a.html):
  emphasizes checking intermediate rationales grounded in evidence spans.
  Current code checks exact spans and bounded formal inference but does not
  reproduce its cross-encoder, NLI or experimental results.
- [TabVer](https://doi.org/10.1162/tacl_a_00722) and
  [FEVEROUS](https://fever.ai/dataset/feverous.html) motivate programmatic
  table arithmetic instead of relying exclusively on linguistic inference.
- [W3C PROV-O](https://www.w3.org/TR/prov-o/) and [AIF](https://doi.org/10.1017/S0269888906001044)
  inform inspectable provenance, claim/evidence/argument separation. This
  prototype does not assert conformance to those interchange standards.
- Open-source competitors [deepcheck](https://github.com/jaytrivediSF25/deepcheck),
  [truth-in-stream](https://github.com/verovec/truth-in-stream), and
  [Minerval](https://github.com/minerval-ai/minerval) already implement
  overlapping link ingestion, cite-grounded research and persistent claim
  graphs. FAR cannot claim ordinary source-citing media fact checking is
  novel, occupied by nobody else, or independently superior.

**Remaining mandatory external gates:** independently checked semantic/source
mapping, adversarial search quality, verified factual source provenance and
lineage, complete multimedia/visual fidelity, multiple inference families
beyond bounded propositional logic, hosted exact-head CI and substantive
independent review, operational hardening, external blinded outcome comparison,
and user/payments/retention validation. None can be inferred from this
internally complete pipeline's integration tests.

### Advisory argument-scheme checks

`diagnostics.py` returns typed, **unadjudicated critical questions** for
causal claims, universal generalizations, numeric denominators, absence
claims, and normative transitions. These are explicitly questions to test,
not evidence that a source is mistaken. They are stored independently in
`critical_questions.json`, included in `report.md`, and hash-checked and
recomputed on full package replay. They do not change any formal inference
result or factual evidence verdict. Existing AIF-style argumentation-scheme
research motivates their separation from deductive proof.

`far-investigation-report/0.2` adds the bounded interpretation-card and
structured-snapshot-only distinctions; the `far-investigation-audit/0.1`
input envelope remains supported. This 0.3 implementation does not promise
that arbitrary earlier report bytes can be re-created by a newer engine: to
replay a historic record, run the exact engine version identified by its
report or pinned repository commit.

See [ACCEPTANCE.md](ACCEPTANCE.md) for the exact tested acceptance contract and outstanding external gates.

## Version 0.4 adversarial verification corrections (2026-10-17)

The original 0.3 package verifier had a concrete integrity defect: changing
`report.md`, recomputing the **unsigned** manifest hashes, and presenting a false
certification still passed `--verify`. The attack was reproduced before the fix.
Version 0.4 now recomputes the report from the original input, recorded proposal,
acquisition data and generated questions; it validates the proposal-to-bundle
reconstruction, source identities and manifest identities as well as hashes.
A tampered report fails even when the attacker recalculates every reported
SHA-256. This remains a **replay check**, not an authenticated external assertion:
an attacker able to replace all inputs and unsigned artifacts self-consistently
can still manufacture an entirely different case. Signed review attestations
bind reviewer-held keys to an exact input and audit, not to reviewer expertise or
external truth.

Source acquisition now retains the original UTF-8 bytes for text, HTML, and
caption modes as `raw_snapshot_utf8`, and the verifier deterministically
reconstructs their extracted text and cue offsets. The verification result
separates `extraction_replayed` from `extraction_not_replayable`. PDF/audio
extraction and provider-supplied model transcripts cannot be reconstructed from
the extracted text alone, and those gaps remain explicit; source hashes are not
publisher authenticity certificates.

**Critical inference correction:** heuristically detected sentences get synthetic
propositional atom labels only for identity. These labels cannot meaningfully
test whether two natural-language propositions entail each other. Previously,
an innocuous valid argument such as `P; therefore P` could be displayed as
`DOES_NOT_ENTAIL` because its two quoted sentences received different atom
names. All readings missing explicitly authored formulas now produce
`NOT_CHECKED_UNFORMALIZED`; no countermodel or invalidity claim is invented.
Explicitly supplied formulas continue to receive independently cross-checked
bounded Boolean inference judgments; source-to-formula semantic fidelity remains
unverified even when those formulas happen to be correct.

**Critical temporal correction:** a direct audit input that omits the
`publication_date_verified` field cannot pass the historical evidence gate.
The field must be a Boolean and only explicit `true` with a valid historical
publication and capture date can be admitted, and that asserted verification
flag still does not authenticate an outside source. A known capture after
`as_of` is reported as outside the cutoff even if the publication date is
unknown. As required by [No Hindsight for LLM Fact-Checkers](https://arxiv.org/abs/2610.04888),
a model's learned knowledge of future outcomes remains a separate unresolved
hindsight channel.

Optional API calls use `gpt-4.1` for untrusted interpretation
proposals (Chat Completions in JSON mode without `reasoning_effort`) and
`gpt-4o-transcribe` for operator-authorized audio transcription.
Offline regression tests assert the actual model names and request arguments,
but do not claim a successful live provider call. No account credentials are
needed for the default offline heuristic path.

Tests: a bounded local regression suite including a seeded 220-case differential
comparison with the independently implemented SymPy SAT solver, cross-snapshot
source extraction replay, signed-record tampering, quotation offsets, malformed
and hindsight dates, and the full CLI/web/package transaction. The 3-case
bundled diagnostic corpus is an **internal synthetic test**, not a consumer
accuracy benchmark. Neither these tests nor a green local CI suite could
establish independent source truth, semantic fidelity, general causal or
statistical inference, external benchmark superiority, or product-market fit.
Those outcomes require outside, blinded adjudication and field testing.

Package writers and verifiers enforce the same limits: only the nine defined
artifact names, at most 6 MB per tracked artifact and 36 MB in aggregate, plus
a separate 6 MB manifest cap. Verification hashes and parses each captured
artifact snapshot rather than reopening mutable paths. Replay preserves JSON
Boolean, integer and floating-point types. Identical inference queries are
cached separately in both checking algorithms; cached query keys reuse bounded
formula metadata, avoiding repeated serialization of entire premise families.

Package replay rejects ambiguous duplicate JSON keys, manifests over 6 MB and
unexpected directory entries without collecting an unbounded directory listing.
Accepted UTC timestamps have at most microsecond precision; finer precision is
rejected before comparison. HTTP receive quotas count actual bytes before JSON
or multipart parsing (450 KB investigation, 16 MB upload), including chunked or
understated-length traffic. These are per-input limits, with no claim of global
concurrency admission control or production readiness.
