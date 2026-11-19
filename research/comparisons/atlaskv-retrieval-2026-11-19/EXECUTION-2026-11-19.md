# Actual execution receipt — 2026-11-19

**Status: Research; CPU scopes executed; trained AtlasKV model remains unexecuted.**

Pinned AtlasKV reference: `HKUST-KnowComp/AtlasKV@61e3abc1fb09fbfb426cfc847c4c26c5e94bcaeb`.

Execution in isolated fresh copy of the frozen benchmark:

- `python -m pytest -q`: **17/17 passed** before adding the new exhaustive regression.
- `python evaluate.py`: four-arm synthetic 108-case benchmark ran; exact answers **72** (flat metadata), **24** (bare triples), **70** (hierarchical proxy), **108** (typed graph oracle). All match archived results.
- `python matched_language_followup.py`: text-only graph parser **108/108** on its previously seen question templates; flat metadata **72/108**, hierarchy proxy **70/108** at eight selected records.
- `python source_pruning_witness.py`: isolated reproductions **20 vs expected 40** for an intermediate ID; **1 vs expected 7** for a leaf value.
- `python exhaustive_index_audit.py`: synthetic local/global index comparisons. Intermediate top-1 mismatch **124/180**; intermediate top-100 mismatch **180/180**; leaf top-1 mismatch **124/180**; leaf top-100 mismatch **166/180**. These are *constructed index patterns*, not real-world error rates or full model behavior.
- `python full_model_preflight.py`: **exit 2, `BLOCKED`**, 18 recorded blockers including absent CUDA, downloaded trained model and encoder, required graph index/test assets, dependencies, and exact pinned upstream checkout.

Frozen input files were byte-identical before and after execution. Fixture SHA-256: `7c11af94668e1fe3d0d765711119d565cdc0f13b12b754e1e14b12d782d80626`; manifest SHA-256: `ece0befdb80fea324e3a94820686e95242e17ecbc0a333e68c7a5d67c55f0a43`.

Reproduce all CPU checks from this directory with `python -m pytest -q` (18 tests after including `test_exhaustive_index.py`), `python evaluate.py`, `python matched_language_followup.py`, `python source_pruning_witness.py`, and `python exhaustive_index_audit.py`. The native preflight returning exit 2 is expected only where its prerequisites are absent.

The upstream checkpoint collection is https://huggingface.co/collections/HaoyuHuang2/atlaskv. Neither checkpoint release nor the bounded CPU checks establish native accuracy. There is no GPU memory, trained Llama inference, real AtlasKV attention integration, external corpus, independent held-out test, or equitable LLM query-planning comparison in this execution. The repository's accepted theory and preregistered EFR evidence are unchanged.
