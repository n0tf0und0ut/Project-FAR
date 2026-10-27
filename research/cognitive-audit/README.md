# Cognitive and philosophical audit — internal Research

The [FAR-COG/0.1 proposal](../../docs/specification/far-cognitive-audit-v0.1.md)
extends the existing learning and assurance contracts. It verifies submitted,
source-anchored coding; automatic interpretation and external effectiveness are
OPEN. The [source reconciliation](../scheduled-task-reconciliation/reconciliation-2026-10-27.md)
records primary-source scope and outstanding access limits.

The [frozen protocol](frozen-v1/protocol.md) and [71 synthetic inputs and exposed
reference labels](frozen-v1/cases.json) were published before predictions in
commit `19424b98f5d42660d3f44eaa90c82236f9280679`. The [first manifest](freeze-v1.json)
and [first complete run](internal-001-results.json) preserve that experiment.
References were authored by the implementer and are not unseen or independent.

## Results and hostile interpretation

First-run status results on this finite, constructed corpus:

| Internal arm | TP | FP | FN | TN | Abstentions on 49 binary cases | Correct disposition on 22 unresolved cases |
|---|---:|---:|---:|---:|---:|---:|
| FAR-COG submitted-coding verifier | 25 | 0 | 0 | 24 | 0 | 22 |
| Generic lexical argument control | 1 | 0 | 0 | 0 | 48 | 21 |
| Structured evidence control | 4 | 0 | 4 | 3 | 38 | 21 |

Abstentions are separate from binary negatives. Each rule's denominators and
every prediction are in the machine-readable run. The candidate emitted 25
SUPPORTED, 24 CONTRADICTED, 21 UNKNOWN and one ABSTAIN. The single controlled
stance paraphrase pair was status-stable for all three arms; this is **not**
raw-language paraphrase robustness. Exact Fraction arithmetic separately checked
the three stipulated binary updates and a finite truth table supplied an
inconsistency-without-intent countermodel. Other labels remain operator coding.

The hostile pass found a defect despite all status labels matching: `observation`
contained the rule's failure predicate even on negative/unknown cases. That
could misleadingly assert a failure in explanatory prose. The correction stores
the supplied coding as the observation and separately labels the scoped
predicate. The first output is retained, not rewritten. The [successor source
manifest](freeze-v2.json) and [corrected follow-up run](internal-001-r2-results.json)
record an implementation-exposed replay on the same frozen cases, not another
unseen success. `test_cognitive_source_obligations.py` checks that boundary across
every case and independently exercises open versus closed scheme vocabularies.

The controls are intentionally small internal implementations, not representative
commercial tools or strong state-of-the-art baselines. Their narrow coverage
explains much of the difference. The structured checker ties on the covered
citation and lineage binary cases; the candidate adds no observed advantage
there. Its four false negatives on warrant cases reflect premise support alone
being insufficient to check the declared inference warrant. No claim of market
superiority follows from this comparison.

## What this does and does not demonstrate

- Demonstrated: deterministic rule replay, byte-bound inputs, strict references,
  explicit uncertainty, no clinical certainty or ontological attribution, and
  distinction between valid form, factual premise support and intent evidence.
- Major limitation: a dishonest or mistaken operator can code `intent_evidence`,
  source support, equivalence or a detection contract incorrectly while preserving
  perfect byte anchors. The audit does not certify these codings. This is a
  usable, bounded audit interchange and verifier, not an autonomous psychologist.
- Model traces are synthetic. No study of sycophancy prevalence, confidence
  updating, memory, attention, human trust, deliberation or actual causal
  mechanisms was run. Existing epistemic Brier scores concern two selected toy
  weather outcomes, not diagnostic calibration or population reliability.
- Motives, subjective understanding, consciousness, personhood and moral status
  remain UNKNOWN or framework-indexed. The absence of evidence is not proof of
  absence. Rhetoric alone is not manipulation; changed evidence is not a
  cross-turn inconsistency; justified disagreement is not sycophancy.
- EFR, human participants, independent adjudication, paid model calls, commercial
  benchmarks, retained-history benefit and customer utility remain unexecuted or
  OPEN. The user deferred external scientific verification and recruitment.

## Replay

```bash
python -m unittest discover -s tests -p 'test_cognitive*.py'
python tools/evaluate_cognitive_audit.py --check
python -m mechanization.far_mechanization.cli cognitive audit examples/cognitive/inconsistency-is-not-intent.json
```

To reproduce the original run, use its source commit plus the preserved v1
manifest and run the original evaluator. The default evaluator checks the
corrected v2 source commitment and refuses to overwrite a different saved run.
No accepted scientific result or application-status promotion is asserted here.
