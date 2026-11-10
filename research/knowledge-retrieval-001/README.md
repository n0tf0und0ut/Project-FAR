# Cross-investigation retrieval baseline 001

**Status:** Research; internally authored retrospective diagnostic. No Accepted theory, external assurance, autonomous agent capability, or production claim.

## Question and objective

Can a minimal, unaugmented lexical retriever recover the relevant records already present in FAR's governed corpus, and avoid presenting unrelated records as answers where there is no admissible primary evidence?

The preexisting governed corpus identifies an unresolved question about whether retained epistemic state improves later work. This task first establishes a reproducible retrieval diagnostic without introducing a second authoritative knowledge system.

## Authority and freeze

The 14 questions and exact record IDs were frozen in commit `a1fd66ae8982e5cf11de183fa5732fe40355badc`, then source-verification metadata was bound to the canonical corpus in `ae54443bb10d8949e7d032409323605956452615`, **before scoring**. The cases and gold IDs were not altered in that correction. The scoring implementation was recorded before the first score.

The fixture derives 28 observations, 5 conclusions, 11 mechanisms and 22 source references from the exact `main` snapshot `efd855db687215368fe8f466e40d2e5cc7a7a863`. It records the Git blob identities of the source corpus and generated synthesis. It retains the original source review flags but does not independently verify the source texts' truth or scientific independence.

Only active observations from sources whose records are both usable and primary-verified are indexed. Mechanisms and conclusions are read-only derived Research records, never separate evidence origins. The inaccessible scheduled-task observation remains inactive.

The question/answer golds are internal author judgements directly informed by the same data used in retrieval. They are **not held out**, externally adjudicated, or a valid measure of generalization.

## Frozen comparison and metric

The baseline scores overlapping non-stopword tokens with IDF weighting divided by the square root of document term count. It does not use embeddings, LLMs, synonym expansion, agent histories, or learned weights. Ranking is deterministic and ties break by ID. Index contents are record statements plus uncertainty or counterevidence text. Top-k is fixed at 5.

- **Positive cases (n=13):** macro record recall@5 and reciprocal rank@5 (MRR).
- **Unavailable-source negative control (n=1):** whether the retriever correctly returns no documents at all.
- **Integrity controls:** reject inactive/unverified observations, duplicated gold identifiers, altered source bytes, or source-ID/hash mismatches.

No optimization on the question set is permitted after observing the first result. The first result and all subsequent findings must remain visible; any genuinely prospective experiment requires a new independently frozen and adjudicated case set.

## Reproduction

From the repository root:

```sh
python research/knowledge-retrieval-001/run_baseline.py \
  --verify-source research/corpus/synthesis-v1.0.json \
  --verify-corpus research/corpus/corpus-v1.0.json \
  --output /tmp/far-cross-investigation-retrieval-result.json

python -m unittest tests.test_cross_investigation_retrieval -v
```

For an archival replay on a later changed `main`, use the exact pinned source blobs or the frozen projection without `--verify-source`/`--verify-corpus`. Omitting the switches **does not** verify contemporary source bytes.

## First bounded result

An independently coded JavaScript implementation of the specified lexical scoring formula directly evaluated the frozen records and wrote `results-js-crosscheck-v0.1.json`. It verified the Git-connector source/corpus blob identities and source-verification fields against the pinned source versions.

| Measure | Observed |
| --- | ---: |
| Admissible indexed records | 43 |
| Positive cases | 13 |
| Positive macro recall@5 | 13/13 complete = 1.000 |
| Positive MRR@5 | 0.961538 |
| Unavailable-source control abstention | 0/1 |
| Evidence of Zettelkasten advantage | None; no experimental variant |

These are **in-sample, near-paraphrase retrieval results**, not evidence of semantic understanding, correctness of source assertions, agent reliability, longitudinal learning, or a FAR advantage. The negative control demonstrates an observed weakness of this *lexical comparator*, not of FAR's canonical audit/reconciliation mechanism.

The JavaScript cross-check is not evidence that the Python CLI ran. The Python CLI and its unit tests must be executed separately; no unexecuted suite is called passed.

## Interpretation and bounded next decision

The initially proposed knowledge explorer is **not justified by this small ceiling-level positive retrieval set**. The comparator's failure on the unanswerable case motivates a distinct question about answerability and provenance-aware abstention, but a single internally authored case is insufficient to justify a new architecture.

Before proposing semantic links, graph storage, or agent-memory changes, the next authorized research step would be a prospectively frozen and independently judged set of paraphrases, conflicting scopes, missing sources, and repeated investigations. Compare an unaugmented lexical baseline with any candidate only under matched resources and the existing FAR governance and replication controls.

## Nonclaims

- No independent primary-source verification or external evaluator was used.
- No claim about general recall, precision, failure rates, statistical significance, or performance on unseen questions.
- No benchmark row is Accepted theory or a new evidence source for the governed corpus.
- No native FAR agent search API has been benchmarked. The diagnostic is a minimal direct ranker over FAR records.
- The case count is too small to support a commercial or engineering ROI estimate.
