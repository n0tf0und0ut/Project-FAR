# AtlasKV × Project FAR: local retrieval and representation stress test

**Status:** Exploratory internal Research. **Date:** 2026-11-19.
**Scope:** A self-contained CPU experiment inspired by the *hierarchical search shape* in the AtlasKV source code. **Not an execution of AtlasKV**, **not a FAR EFR study**, and **not evidence of external replication or product benefit**.

## What ran

A synthetic corpus of 364 facts and 108 questions was sealed before any evaluation run. The corpus contains 36 three-hop entity chains, 24 contradictory source-specific claims, 24 effective-date ownership changes, and 24 negative/unknown questions. There are 160 unrelated distractor facts. All entities are fictional.

The four arms were preregistered in `frozen_manifest.json` with an eight-evidence-record output budget:

1. **Flat TF-IDF, full metadata:** one-shot lexical/vector retrieval, keeping source and time.
2. **Flat TF-IDF, bare triples:** identical one-shot retrieval mechanism with `source`/`valid_from` removed from both indexed evidence and returned evidence.
3. **Hierarchical proxy, full metadata:** a two-level deterministic KMeans hierarchy over TF-IDF/SVD embeddings, with root → intermediate → leaf selection and final top-eight output. This is **not** the model, learned encoder, or GPU pruning of AtlasKV.
4. **Structured graph traversal:** executes the supplied relation chain, source constraint, and as-of cutoff over the full fact set, returning up to eight supporting facts. It does **not** inspect expected answers or gold supporting IDs. This arm receives an oracle typed query plan and therefore is only an upper-bound comparator for retrieval, not an equivalent natural-language interface.

A **deterministic answerer** interprets the predeclared query semantics on *only the selected records*, returning `UNKNOWN` if evidence is incomplete or ambiguous. No LLM answered the queries. For unknown cases, `UNKNOWN` is a conservative abstention, **not proof of absence** in an open or incomplete evidence corpus. Repeated runs can have small CPU timing differences.

## Predeclared metrics and results

| Arm | Correct /108 | Known cases with complete supporting evidence /84 | Unknown abstentions /24 | Median retrieval ms* |
| --- | ---: | ---: | ---: | ---: |
| Flat TF-IDF, full metadata | 72 | 48 | 24 | 0.409 |
| Flat TF-IDF, bare triples | 24 | 0 | 24 | 0.370 |
| Hierarchical proxy, full metadata | 70 | 34 | 24 | 0.496 |
| Structured graph traversal | 108 | 84 | 24 | 0.016 |

\* Per-query retrieval code only, CPU, 364 facts; excludes vectorization, clustering, model training, LLM inference, and GPU memory. Do not extrapolate to billion-scale costs. Timing values are illustrative from the included results file.

All 36 three-hop queries failed in both one-shot retrieval arms (flat full and hierarchical proxy). All 36 passed the structured graph walk with the supplied typed plan. On the 84 positive-answer cases, answer accuracy was 48/84 flat full, 0/84 bare triples, 46/84 hierarchy proxy, and 84/84 structured graph walk.

The experiment constructed and machine-verified 48 counterfactual pairs (24 source swaps, 24 timestamp swaps): the exact `(subject, relation, object)` projection was identical in each pair, but the contract-required answer changed. Therefore a deterministic decoder using **only** that projection cannot be correct in both worlds. This is a **representation-theoretic** witness about the *chosen bare-triple projection*, **not a demonstration that AtlasKV necessarily loses source/time**. A KG2KV encoding could preserve these distinctions if its input and evaluation contract explicitly include them.

## Input integrity and provenance

- Fixture SHA-256: `7c11af94668e1fe3d0d765711119d565cdc0f13b12b754e1e14b12d782d80626`
- Manifest SHA-256: `ece0befdb80fea324e3a94820686e95242e17ecbc0a333e68c7a5d67c55f0a43`
- Fixed seed: `20261119`.
- The evaluator checks the frozen fixture hash and rejects changes.
- Source inspected: [AtlasKV](https://github.com/HKUST-KnowComp/AtlasKV); [`llama3_model.py`](https://github.com/HKUST-KnowComp/AtlasKV/blob/main/src/atlaskv/models/llama3_model.py), root/intermediate/leaf pruning and softmax top-k; [`experiments/eval.py`](https://github.com/HKUST-KnowComp/AtlasKV/blob/main/experiments/eval.py), CUDA-specific evaluation; source retrieved from GitHub main 2026-11-19.
- Project FAR governance inspected from `n0tf0und0ut/Project-FAR` protected `main`: root `AGENTS.md` (blob `0c21bb208e2f624742fde13715326882b178dcc7`), research charter, project status, canonical map, README, and EFR protocol. This experiment does **not** modify the FAR repository or count as EFR evidence.

## Reproduction

Requires Python 3.10+ and `numpy`, `scikit-learn`, `pytest`. The run used Python 3.13.5, NumPy 2.3.5, scikit-learn 1.8.0, and CPU-only execution.

```bash
cd atlaskv_far_experiment
python -m pytest -q
python evaluate.py
```

Expected: nine passing tests, 108 cases, 48 valid collision witnesses; verified outputs in `case_results.csv`, `results_summary.json`, and `collision_witnesses.json`.

`build_fixture.py` documents how the corpus was constructed. **Do not rerun it during reproduction**; replacing a fixture would constitute a new input freeze.

## Conclusions, boundaries, and next test

- **Verified here:** Exact bare triples cannot answer contracts that distinguish source attribution or effective time when those distinctions are omitted. One-shot text retrieval is vulnerable to multi-hop evidence loss on this deliberately constructed corpus. A typed graph traversal can retrieve the specific chain when the correct plan is supplied.
- **Not verified:** AtlasKV's actual trained accuracy, learned hierarchy behavior, GPU VRAM budget, multi-hop model outputs, source/time encoding capabilities, or superiority/inferiority against graph RAG. This proxy does not use original AtlasKV weights, the sentence transformer, a Llama model, or an external dataset.
- **Not a controlled model comparison:** The graph arm gets structured query plans. The flat and hierarchical arms receive only natural-language query strings. The oracle advantage cannot be separated from query planning.
- **Not generalizable:** The corpus, contracts, and questions were constructed in-session. There is no external custodian, held-out sample, blind adjudication, or representative population.

A future true model comparison would require authorized access to AtlasKV model and encoder checkpoints, compatible GPUs, shared frozen facts and questions, an equivalent language-to-query-plan component for the graph baseline, equal evidence/latency constraints, and source/time-aware output scoring. No FAR scientific status should be promoted from this result.
