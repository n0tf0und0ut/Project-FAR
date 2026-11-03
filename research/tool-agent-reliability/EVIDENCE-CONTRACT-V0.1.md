# Agent reliability evidence audit profile v0.1

Status: **Research — additive post-execution audit profile.** No new performance
experiment, accepted schema, theory promotion, deployment assurance, or live
model run is introduced.

## Question and observed representational gap

Protected baseline: `c7456b469f9dfe88b92d0fc7a211e5c9ed64de61`.
The current root instructions, Research Execution Charter, review-convergence
policy, canonical map and status govern this work.

Search and inspection found three complementary existing contracts:

- [`far-evidence-package/1.0`](../../schemas/far-evidence-package-v1.schema.json)
  represents source-supported claims, assumptions and boundaries. Its metadata
  permits scalar values only; it cannot hold structured run, safety and exposure
  measurements. It is preserved unchanged and reused as this profile's evidence
  envelope.
- [`tool_agent_reliability.py`](../../tools/tool_agent_reliability.py) already
  recomputes raw provider messages, prompts, actual actions, tool observations,
  final state and grades, and checks registered task/seed coverage. Its current
  record identity and model selection are intentionally specific to the frozen
  tool-agent study.
- The [SWE-agent v3 evidence plan](../external-validation/swe-agent-v3/evidence-and-analysis-plan-v1.0.md)
  already requires extensive resource, regression, authorization, blinding and
  adjudication evidence. It is prospective, its execution gate remains closed,
  and it supplies no observed v3 runs. This audit neither executes nor replaces
  that study or its contracts.

The missing invariant is a common explicit measurement surface that distinguishes
known run exposure from incidents, missing measurements from zero cost, repeated
execution from independent behavior, and reconstructed outcomes from causal or
external assurance. The smallest addition here is a **sidecar projection**, not
a second agent runtime, scorer, memory store, or production schema revision.

## Contract and trust boundary

[`agent_reliability_evidence.py`](../../tools/agent_reliability_evidence.py)
defines the Research profile `far-agent-evidence/0.1`. Its outer evidence envelope
remains valid `far-evidence-package/1.0`; a scalar metadata field identifies the
profile. Existing frozen trace bytes are addressed by path, nested ZIP member
chain and SHA-256 rather than rewritten or copied into a replacement history.

| Measurement | Profile field | Historical adapter evidence or limit |
| --- | --- | --- |
| Task and environment identity | `task`, `identities.environment` | Exact authored task hash, phase, family, Python/platform record |
| Model, harness, tools, policy, configuration | `identities` | Full model digest; original source commit/tree/Git blobs and SHA-256s; policy and protocol hashes |
| Model actions and actual observations | `trace.model_actions`, `trace.artifact` | Every retained request/response is replayed by the existing verifier; actions/observations are reconstructed |
| Success, partial success, failure, abstention | `outcome` | Common grades include all five including `unknown`; historical binary grade does not invent separate partial or abstention scoring |
| Earliest consequential error and category | `failure.first_consequential_error`, `failure.first_observed_failure` | Causal earliest deviation stays `unknown`; observable policy violation/termination/check failure is separately recorded |
| Detection, recovery, retries, intervention | `failure` | Failed tool observations and later successful completion are observable; causal repair remains untested; source has no fallback-planner/intervention or retry path |
| Unauthorized actions and policy violations | `safety` | Reused trusted history/oracle grade retains transient writes and unsafe attempts |
| Severity and reversibility | `safety` | Severity unknown; only simulated state reconstruction is demonstrated |
| Ground truth and adjudicator independence | `ground_truth` | Frozen oracle hash, Project-FAR-authored grader, no external independence |
| Eligible exposure denominator | `exposure`, `summary` | Exact registered slots; no rate for incidents, missing slots or unknown outcomes |
| Resources, latency and billing | `resources` | Replayed token/call/action counts and measured elapsed/provider time; unavailable measurements are null with explicit reasons/evidence, never invented zero |
| Trace completeness and provenance | `trace`, original source manifest | Complete within recorded harness scope; source objects verified against original Git commit; no execution attestation |
| Generalization limits | `limitations`, `summary` | Authored simulation only; no IID sample claim, FAR benefit, external reliability or commercial inference |

`validate_profile` checks the common cross-model measurement surface and its
internal consistency, including every required nested measurement field. It
calls the existing `normalize_package` verifier for the reused evidence envelope.
**Shape validation does not verify arbitrary task grades.**
`verify_historical` rebuilds every projected field from retained frozen evidence
through the existing deterministic replay implementation, then requires exact
canonical equality. A new model/program may use the common representation, but
requires its own independently scrutinized adapter before any outcome is called
verified. The module never executes a model or adds a provider.

The historical v0.3 archive is pinned to its previously published SHA-256
`b4e1ccd17a46db8f91ccee29232853bdd6ba5881a1f6c747351d2dfc242a7809`.
V0.2 direct raw records are checked byte-for-byte against their immutable Git
objects on the baseline above. Protocol and source manifests are checked against
their original execution commits. Source mutation, fabricated profile grades,
changed eligible denominators, removed/duplicated slots, altered observations and
cost claims fail reconstruction even when an attacker recomputes a local hash.
Provider time cannot exceed total elapsed time by more than one microsecond;
UTC wall timestamps must agree with the recorded monotonic elapsed duration
within 0.1 seconds. These are audit serialization tolerances, not additional
experimental outcome thresholds. An incomplete trace can be represented only
with an invalid/unknown outcome and contributes no success/failure rate.
Known provider wall time must also fit within the observed UTC interval plus
0.1 seconds, including when the monotonic elapsed measurement is unknown.

Every numeric resource measurement may be null when unrecorded. The exact set of
null fields must appear in `resources.unknown_measurements`, each with a nonempty
`reason` and an `evidence` list (empty when no supporting artifact exists).
Unavailable telemetry alone does not invalidate an otherwise verified task
outcome or its registered exposure denominator. All non-null counters must be
nonnegative integers; all non-null durations must be finite nonnegative numbers;
booleans, NaN and infinity are rejected. `provider_seconds` means nonoverlapping
provider-occupied wall time, which equals summed call duration in the existing
sequential harness. A concurrent adapter must reconstruct occupied interval union
or report it unknown; summed parallel compute time is a different metric and is
not constrained by this wall-time inequality.

Unknown authorization counts similarly require explicit entries in
`safety.unknown_measurements`; an unknown safety count cannot satisfy a success
claim's observed-zero authorization requirement. A null retry count requires its
`provider_retry_basis`; null human-intervention counts retain their existing
`basis`. Observed or estimated billing requires an exact nonnegative decimal
string of at most 128 characters, a three-letter uppercase currency, and a
nonempty string evidence reference of at most 2,048 characters. Boolean or numeric
values cannot stand in for that reference. `cohort_id` and `adapter` are nonempty
strings of at most 256 characters. These type checks do not establish the truth
of an invoice, missingness explanation, or independence declaration; independent
evidence validation and deterministic historical reconstruction remain separate.

Every runtime identity uses exactly `id`, `version`, `details`, `provenance`,
and `unknown_fields`. IDs and versions are bounded nonempty strings, or explicit
null with a retained-artifact explanation. Placeholders such as `UNKNOWN` cannot
stand in for a release identity. Provenance is a nonempty list of typed artifact
references; provider-specific information stays in `details`. The historical
adapter retains the observed Python/platform but reports the immutable complete
environment version unknown because no image/package-lock identity was retained.
It does not invent a pin from the Python version alone.

Registered exposure requires a typed protocol reference plus a `slot_declaration`
whose source equals that protocol and whose digest binds the ordered eligible
slot list. Both profile validation and direct summary calculation reject a
missing protocol or mismatched declaration before producing fractions. Incident
collections cannot supply eligible slots or a slot declaration. Common-profile
fractions remain **conditional on supplied declarations**: self-consistently
rewriting a declaration is not proof of registration. Only an audited adapter,
including `verify_historical`, establishes correspondence to the actual frozen
protocol. Historical reconstruction rejects even self-consistent omitted slots.
Artifact references cannot name the current directory or a directory in place
of a regular file.

The existing replay verifies that recorded requests match the registered prompt
construction, including exclusion of oracle objects. This does not prove that
the unsealed investigators never disclosed an answer through an unobserved
channel. A fully fabricated coherent history and false runtime metadata require
external attestation to exclude; self-consistent hashes alone cannot do so.

## Executed reconstruction and negative outcomes

The generated [audit receipt](evidence-contract-validation-v0.1.json) records
canonical profile hashes, current audit-source hash and exact summary results.
It is a post-execution reconstruction, not another experiment or independent
replication.

| Retained cohort | Replayed outcomes | Exposure and behavior limits |
| --- | --- | --- |
| Frozen v0.3 scored | 72 successes / 72 registered slots, zero failures | 24 authored tasks, three attempts each; 25 distinct action/observation trajectories across the entire corpus; independence unestablished |
| Frozen v0.2 stopped preflight | 2 successes and 1 failure / 3 registered slots, one unauthorized simulated write | Separate earlier 1.5B condition; no pooling with v0.3 and no reinterpretation of its stopped gate |

Twenty-three of the 24 v0.3 tasks repeat the same trajectory across all seeds.
The 25 trajectory count is an exact deduplication count, **not** an independent
sample count or estimate of behavioral robustness. The earlier negative result
remains equally visible. The separate [scripted repair study](../workflow-efficacy/KEYLESS-PILOT-RESULTS-V0.4.md)
still reports control 11/30 and FAR 10/30; these tool-only cohorts do not establish
FAR-specific improvement or override that finding.

No real billing or full operational cost was retained. The profile deliberately
uses null/unknown rather than asserting free execution from absent invoices.
No external causal diagnosis, verified repair intervention, human decision
benefit or buyer outcome has been measured here.

## Reproduction and adversarial verification

From a repository checkout containing the original Git objects:

```bash
python -m tools.agent_reliability_evidence build --file /tmp/far-v03-evidence.json
python -m tools.agent_reliability_evidence verify --file /tmp/far-v03-evidence.json
python -m tools.agent_reliability_evidence build --cohort tool-agent-v02-preflight --file /tmp/far-v02-evidence.json
python -m tools.agent_reliability_evidence verify --file /tmp/far-v02-evidence.json
python -m tools.agent_reliability_evidence audit --file /tmp/far-evidence-audit.json
python -m unittest discover -s tests -p 'test_agent_reliability_evidence.py' -v
python -m unittest discover -s tests -p 'test_tool_agent_reliability.py' -v
```

Regression/mutation cases cover missing dimensions, missing and duplicated runs,
invented denominators and independence, false success, incorrect grades, changed
model identity, forged observations/actions with updated hashes, hidden oracle
objects in requests, changed source identities, invalid timestamps and costs,
unsafe paths, symlinks outside the evidence root, duplicate ZIP members and
missing trace completeness. All use deterministic fixtures or previously frozen
records; none is counted as new inference evidence.

Executed local validation: **29/29** profile tests and **51/51** existing runner
tests passed; the profile test includes per-key omission mutations throughout
task, runtime, trace, outcome, ground truth, diagnosis, intervention, safety,
resources and timestamp records. Documentation checks passed. Required hosted
checks, independent review and protected authorization remain separate gates.

## Finding ledger

| Root cause | Disposition and verification |
| --- | --- |
| RLY-EVID-001 — study-specific traces lack a common reliability measurement surface | Research sidecar adds missing exposure, provenance, safety, cost and assurance fields while reusing original envelope and replay; cross-model shape test distinguishes representation from verified grading |
| RLY-EVID-002 — incidents or repeated runs could be promoted into population rates | Exact eligible-slot enumeration, missingness handling and explicit unestablished independence; incident/missing/duplicate/denominator/independence mutation tests |
| RLY-EVID-003 — valid hashes alone could support fabricated grades, costs or trace claims | Historical reconstruction checks original archive/Git source, replays messages/tools/grades and compares the complete profile; raw/provider/grade/source/cost mutations fail |
| RLY-EVID-004 — explanatory labels could imply causal identification | Earliest causal error, attribution, repair and regressions remain unknown/untested; observable failure is recorded separately |
| RLY-EVID-005 — truthy non-string billing references and untyped profile identities | Independent review at `cc44f6fe` reproduced acceptance of boolean/integer source references; bounded string checks and exact type mutations reject them |
| RLY-EVID-006 — unavailable telemetry could require invented zero | Independent review identified missing null representation for resource/safety counts; explicit per-field missingness reasons preserve unknown without treating it as free execution or safe zero |
| RLY-EVID-007 — unknown monotonic duration could hide impossible provider wall time | Follow-up review reproduced acceptance of `elapsed_seconds=null` with `provider_seconds=1000000000` despite a short observed UTC interval; the UTC bound and exact counterexample now reject it |
| RLY-EVID-008 — a missing protocol still permitted declared-rate arithmetic | Exact published-head reproducer accepted `exposure.protocol=null`; typed protocol and source-bound slot declarations now reject this in both validation and direct summary, with missingness/corruption controls |
| RLY-EVID-009 — dictionary placeholders could omit runtime identities and versions | Published-head reproducer accepted `{unidentified: true}` for model/harness/policy/environment; all six generic identity envelopes now require typed IDs/versions/provenance or explicit reasoned unknowns; per-field and malformed-value mutations reject |
| RLY-EVID-010 — current-directory artifact reference passed syntax validation | `.` is now rejected and artifact loading requires a regular file; exact directory regressions pass |

These are bounded software/evidence-audit corrections. They do not promote the
profile to Accepted methodology or satisfy independent scientific review and
protected PR authorization.

## Interrupted unpublished implementation stage

The working directory expired before the later identity/exposure refinements and
comparator relocation launcher were pushed. Those unpublished local source and
SDK replay receipts are not treated as current verified artifacts. The published
original comparator ZIP, all primary model outputs, and all frozen historical
protocols/results remained intact. The identity/exposure/directory counterexamples
were reproduced against the published head and these corrections were rebuilt
and tested from that source; the receipt identifies the rebuilt validator bytes.
No lost local receipt is substituted for the current tests or original results.
