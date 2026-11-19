# Follow-up: matched text interface, upstream inference indexing, and native-run gate

**Status:** Research; executed CPU follow-up. **Date:** 2026-11-19.
**Parent record:** `README.md` (frozen 364-fact/108-question synthetic proxy experiment). **This document does not alter its frozen manifest, source corpus, results, or inference boundaries.**

## Objective and result

The original four-arm experiment had a known query-plan confound: the graph arm received typed case fields, while flat and hierarchical retrieval received natural-language questions. This exploratory follow-up tests whether a deterministic *text-only parser* can retrieve the declared graph path, with the same eight-record evidence cap. The parser was authored **after exposure to the existing question templates** and the follow-up is therefore **post-hoc**, not preregistered or independent.

The separately inspected AtlasKV native source also shows two index-space mismatches in the hierarchical inference path. `source_pruning_witness.py` transcribes the original `prune_key` operation and reproduces those local/global errors using CPU PyTorch. These are isolated tensor-level reproductions. We did **not** execute the complete pretrained AtlasKV model or establish a real model-answer failure.

## Follow-up comparison

All three text retrieval methods and the graph traversal parser receive exactly the same raw question string and same frozen facts. The graph arm derives `anchor`, relation path, source, and time from the question using three hardcoded regex templates, then executes deterministic traversal. It never inspects the case's expected answer or proof IDs. Flat and proxy arms continue using the original benchmark's gold typed fields in the **answerer**, which can only favor those baselines relative to the graph arm. The graph arm uses its parsed fields for both retrieval and answering. The original evidence corpus and results are preserved.

| Evidence cap | Flat TF-IDF metadata correct /108 | Hierarchical proxy correct /108 | Text-parsed graph correct /108 |
|---:|---:|---:|---:|
| 1 | 65 | 57 | 72 |
| 2 | 72 | 62 | 72 |
| 3 | 72 | 63 | 108 |
| 8 | 72 | 70 | 108 |
| 16 | 72 | 72 | 108 |

The bare-triple arm remained at 24/108 at every cap. All methods return `UNKNOWN` on the same 24 unknown cases, which is abstention rather than proof of absence. No LLM generated answers. Graph parser coverage was 108/108 **on the known template corpus only**; independent natural-language query planning is untested. Budget values refer to returned evidence records, *not* total graph traversal work; no speed or memory superiority is inferred. The graph arm's performance is still a domain-specific upper bound.

## AtlasKV inference-source witness

Upstream repository: `https://github.com/HKUST-KnowComp/AtlasKV`, commit `61e3abc1fb09fbfb426cfc847c4c26c5e94bcaeb`, source `src/atlaskv/models/llama3_model.py` (line 193–217 and 511–566 in the inspected revision).

- **Intermediate mismatch:** selected intermediate keys are `inter_kb_keys[:,:,select_inter_local_key_idx,:]`, but the subsequent `prune_key` receives the *entire* `inter_kb_indices` array. A winning local position 1 within global IDs `[30,40]` is mapped to the global ID at position 1 within `[10,20,30,40]`, namely `20` instead of `40`. The numerical witness returns **20 instead of 40**. A contract-preserving remedy would pass `inter_kb_indices[select_inter_local_key_idx]`, with dimensionality/scalar guards verified in the integrated model.
- **Leaf mismatch:** leaf attention operates over `leaf_kb_keys[:,:,select_leaf_local_key_idx,:]`, then `top_idx` from the pruned leaf group is used against the **entire** global `kb_values` array. If selected global leaf positions are `[3,7]`, the winning local position 1 selects global `kb_values[1]` instead of `kb_values[7]`. Numerical witness returns **1 instead of 7**. A suitable candidate repair would remap local `top_idx` through `select_leaf_local_key_idx` before gathering `kb_values`.

Both witnesses have positive controls with globally aligned indices. Reproduction does not require GPUs or checkpoints. Neither witness measures the frequency or downstream impact of these errors in the published model. The same independent exact-head / correctness review requirement applies before any upstream fix proposal. We have not modified AtlasKV source or published a defect report upstream.

## Native model preflight and blocked state

The original AtlasKV README requires a Llama backbone, both the trained model and encoder checkpoints, test dataset and precomputed key/value/cluster assets. Its native evaluation script runs via CUDA and depends on its own model/environment packages. The upstream repository's README specifies separate CC- and Wiki-trained checkpoint links (SharePoint). This session has **no CUDA device, no model/encoder/dataset assets, and no network access in the local Python container**. `full_model_preflight.py` checks required paths, GPU and import dependencies and writes a machine-readable blocked verdict; it does **not** attempt inference. Missing credentials or model resources must not be represented as a failed model score.

A genuine *matched AtlasKV-vs-graph* evaluation still needs a versioned KG2KV exporter preserving source/time, shared 108 question strings, suitable trained checkpoints, an equivalent LLM-based graph query planner, explicit generation/scoring and safety abstention controls, independent labels, and both inference and offline encoding resource measurement. Running the upstream out-of-domain benchmark alone would not answer FAR's source/time contract question.

## Reproduction and tests

Requires Python 3.10+, `numpy`, `scikit-learn`, `pytest`, and CPU PyTorch.

```bash
python -m pytest -q
python matched_language_followup.py
python source_pruning_witness.py
python full_model_preflight.py --output native_preflight.json
# Exit 2 = BLOCKED (expected without GPU and all input assets).
```

**Observed locally:** 15/15 tests passed; 108/108 template parses; source witness returned intermediate index `20` rather than `40`, and leaf value `1` rather than `7`. The native preflight returned `BLOCKED` (no CUDA or trained model resources). The original frozen input hashes remain `7c11af94668e1fe3d0d765711119d565cdc0f13b12b754e1e14b12d782d80626` (fixture) and `ece0befdb80fea324e3a94820686e95242e17ecbc0a333e68c7a5d67c55f0a43` (manifest).

**Disposition:** The only verified new defect is the upstream selection-index inconsistency at isolated tensor scope. The matched follow-up is a bounded, authored, synthetic comparison. General model effectiveness, AtlasKV trained correctness, GPU utilization, real multi-hop accuracy, empirical FAR advantage, and commercial value remain unresolved. No claim promotion or protected main merge is authorized by these results.
