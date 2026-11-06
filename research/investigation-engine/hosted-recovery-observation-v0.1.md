# Hosted investigation recovery: retained original observations

Status: Research / negative bounded execution result. No capability promotion.
The hosted recovery campaign completed from original head
`7ffb943386d4cc6450417ba472f45ab55b2b6823` between
`2026-11-03T16:14:48.718887Z` and `2026-11-03T16:47:11.668372Z`.

- [Original Actions run 41672008583](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41672008583).
- [Original artifact 13251236916](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41672008583/artifacts/13251236916).
- Exact downloaded ZIP retained as [`hosted-recovery-v0.1.zip`](hosted-recovery-v0.1.zip),
  6,081,384 bytes, SHA-256 `ac45229fda1e7a38fe23b5127cfd361fc938601bc5b6db94bd5d9a95268473e9`.
- Exact selection-v2 SHA-256 `c10854197fdff2f02785c66ab6ebe1795af1486525fe5885cd917ca939ac0f0a`.
- Model SHA-256 `9c9f56a391a3abbd5b89d0245bf6106081bcc3173119d4229235dd9d23253f94`;
  actual server executable SHA-256 `c4b03ddc2d99be837701030cdb72df72db5bd9d2ffece7783461cacdc83b384a`.

## Actual results

| Lane | Attempted tasks | Pipeline completed | Internally valid transcripts | Frozen/evaluated families | Model tokens | Rejected calls | Controller substitutions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Agent | 8 | 0 | 8 | 0 | 141,481 | 20 | 0 |
| Deterministic | 8 | 7 | 8 | 7 | 0 | 5 | 0 |
| Declarative | 8 | 7 | 8 | 7 | 0 | 5 | 0 |

The deterministic and declarative lanes execute the same algorithm through two
representations; they are not independent competing systems. These are exposure
counts for this purposive authored selection, not population reliability rates.
A valid transcript means internal consistency, not success on the question.
All semantic-success fields remain null. Billed dollars, energy, amortized
hardware cost and human-review time were not measured; 141,481 tokens are not a
cost estimate.

All eight agent attempts failed or remained incomplete. H201, H202, H203, H204,
H206, H207 and H208 end after a model HTTP timeout; H205 returned two function
calls despite the one-call contract and was rejected. The raw failure envelopes
and partial action histories survive. The agent retrieved no accepted source
receipts and performed no native candidate evaluations. This does not isolate
model quality from prompt growth, transport limits, hardware speed, task demands
or model-call policy; no intervention counterfactual was executed. A plausible
mechanism is not established causal attribution.

Both workflow lanes failed H204 after a retrieved source raised
`UnicodeDecodeError`, leaving discovery incomplete. Other workflow slots
completed a frozen `evidence_assessment` inventory with `Unknown`, not an
independent substantive answer. Mechanical inspection confirms that the numeric
H202, H203 and H208 slots did not execute the required earthquake calculation,
process-mean statistics or 400-year cycle enumeration. Their original question
obligations remain unsatisfied by these native traces. This is an objectively
checkable missing execution, not a semantic-accuracy score for all eight cases.
Source meaning, conclusion adequacy, false positives/negatives and independent
human decision benefit remain unadjudicated.

## Reproduction and adversarial validation

```bash
python tools/far_investigation_campaign.py audit research/investigation-engine
python -m unittest tests.test_far_investigation_campaign tests.test_far_investigation_audit -v
```

Replay verifies all 24 transcript hashes, internal histories and native results;
recomputes row metrics and the campaign summary; binds task identities, exposure
order, budgets and the external frozen selection; and checks the retained
original source identity. Every original implementation hash also matches the
corresponding file at the recorded Git commit. Duplicated/missing exposure,
mutated selection or source bindings, duplicate ZIP members, fabricated metrics,
invalid cost and forged summary mutations are rejected even when an attacker
updates the copied ZIP's manifest hash. The original ZIP is never modified.
Self-recorded manifests cannot establish authenticity against an author rewriting
the entire repository and all evidence.

The original bounded-response helper incorrectly labeled request start as
`received_at`. Those historical values remain unchanged and do not establish
body-receipt timing. This post-execution correction records separate start and
completion instants, including timeout; new timing-scope records are checked for
backwards chronology. Event timestamps and monotonic elapsed measurements remain
the original observations. The validator changes are maintenance work, not a
rerun under the old frozen condition.

The exact original hosted workflow is retained in
[`original-hosted-workflow-v0.1.yml`](original-hosted-workflow-v0.1.yml), SHA-256
`0940c5d5fbfd5deaff38106ebf07c61bd5881f24f86ccb59236a366f4a51bbda`.
Maintenance pushes replay evidence and run offline invariants. No live entry
point silently repeats or overwrites this condition; a separately registered
successor identity and output location are required for a new scored trial.

## Post-hoc deterministic adjudication preparation

The [source-bound arithmetic record](posthoc-numeric-recomputation-v0.1.json)
was actually executed by [its retained recipe](recompute-numeric-v0.1.py). It
recomputes the quoted USGS formulas (nearest integers: amplitude 794, empirical
energy 22,387), NIST raw sample statistics (mean 53.7; sample variance
3881/90; t approximately 1.782), and an independently cross-checked Gregorian
400-year cycle (97 leap days; 146,097 days; mean 365.2425 days). The conditional
NIST decision uses the source-reported critical value; that quantile is explicitly
not independently recomputed. Formula/quote coordinates, retained source hashes,
precision, assumptions and limitations are recorded. This post-hoc work prepares
bounded adjudication evidence; it is not a new original-lane success or an
independent human semantic score. Reproduce without network or model calls:

```bash
python research/investigation-engine/recompute-numeric-v0.1.py
```

## Remaining scientific gates

The pinned Open Deep Research graph comparison was registered, but its original
adapter was uncommitted and lost at the documented workspace interruption. No
recoverable adapter hash, exact adapter source or raw competitor observations
survive. Reconstructing code now cannot establish the missing original condition.
That original comparison is **BLOCKED_GOVERNANCE** on missing frozen source and
execution evidence, not a competitor failure or an external access excuse. A
source-bound successor adapter may reuse the existing graph after separate
registration; it cannot replace the absent original evidence.

Independent substantive source/answer adjudication is still required. The
mechanical checks above prepare exact input identities and identify unexecuted
calculations; they do not fabricate independent human judgments. General agent
reliability, FAR superiority, causal repair benefit, commercial value and human
augmentation remain **NOT ESTABLISHED**.
