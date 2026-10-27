# PR #596 — internal defect and convergence record

Status: Research implementation record, not an independent scientific review.
Independent exact-head software review and protected merge authority are separate
release obligations. [Scope and results](../../research/cognitive-audit/README.md).

| Violated invariant / root cause | Evidence and disposition | Regression / remaining scope |
|---|---|---|
| Observation must not assert a failure on a negative/unknown diagnosis; predicate text was reused as observation | First run preserved; correction separates submitted coding from scoped predicate without changing status decisions | All 71 outputs checked by the hostile source-obligation test; coding fidelity remains UNKNOWN |
| Navigation must preserve executed-byte provenance and corpus-source identity; three pages were changed without coupled byte records | Hosted PCA-W6/local corpus tests rejected d5b8550. Restore project-status to original SRC-STATUS bytes; update existing W4/W6 supplements only for README/canonical-map navigation | W4/W6 and corpus tests; frozen manifests, results and corpus unchanged |
| A current-navigation change must rebuild dependent living/corpus views; the living validator reconciles surface hashes before checking synthesis | Hosted living `validate` rejected 016d7f8's stale synthesis. Run the existing living reconciler to a fixed point, then the corpus generator | Idempotence verified. Only five synthesis hash fields change; semantic observations, conclusions, governed source inputs, candidate set and 2,068-lead count remain identical |

Source-only freeze: `19424b98f5d42660d3f44eaa90c82236f9280679`, before predictions.
Explanatory correction/reconciliation: `75556e1f2aeef68c73b7306639fb1c803ac8d499`.
The successor manifest records that the follow-up is exposed and already
exercised by regression tests, not a new confirmatory experiment. Existing
score/ELENCHUS meanings and accepted core theorem/assurance bytes are unchanged.

No external scientific seals, paper replication, customer validation or complete
historical-scheduler coverage are claimed.
