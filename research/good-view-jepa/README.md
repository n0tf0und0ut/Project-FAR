# Good-view JEPA evidence retrieval — isolated research pilot

**Status: Research.** This executable optional-dependency experiment compares **synthetic numerical vectors**; it does not use actual images or text embeddings and is not part of FAR's reasoning or verification pipeline. Source: Balestriero & LeCun, [arXiv:2610.39302v1](https://arxiv.org/html/2610.39302v1), October 29, 2026. Their theorem requires a shared positive-pair kernel, injective renderings, population optima and uniqueness up to rotation. This small VICReg-style pilot neither satisfies those assumptions nor implements the complete SIGReg method.

## Frozen design and execution

The [protocol](PROTOCOL.md) was committed on the research branch at `b546d99d5b340ff7820f7d32f135ce9238de0405` before measured execution. The fixture uses **240 training, 96 calibration and 96 test items**, grouped into respectively 120, 48 and 48 *disjoint* synthetic proposition families. Each item has two simulated views in each of two independent numerical modalities. Each modality's representation is trained alone; a single orthogonal Procrustes map is fitted with *calibration pairs only*. No model sees image–text pairs during representation training.

The initial code blob `c3eb4d73372977fa9f6139c1e8f7fc255a0b1f68` mistakenly averaged both PCA views at inference while JEPA conditions saw one view. The [original results](results-initial-invalid-v0.1.json) are preserved and **invalid for a fair comparison with PCA**. Good-vs-bad values are unaffected. The repaired blob `3f84fdb8f66f7f015b673cbcd50f87855f6ccff9` enforces one retrieval view in every condition; the [corrected results](results-synthetic-v0.2.json) were recorded afterward. Because the correction followed initial outcome exposure, this remains exploratory and is not a blinded confirmatory trial.

## Corrected results (held-out Recall@1)

| Seed | Untrained | Bad view | Good view | One-view PCA | Good − bad | Good − PCA |
|---|---:|---:|---:|---:|---:|---:|
| 11 | 0.031250 | 0.041667 | 0.000000 | 0.156250 | -0.041667 | -0.156250 |
| 29 | 0.000000 | 0.041667 | 0.041667 | 0.156250 | 0.000000 | -0.114583 |
| 47 | 0.020833 | 0.031250 | 0.041667 | 0.156250 | +0.010417 | -0.114583 |

The good-view model's stance discrimination (own item ranked ahead of opposite-stance sibling) was **0.583333, 0.552083, 0.614583**, versus bad-view **0.593750, 0.677083, 0.656250**, and PCA **0.729167**. Full per-seed Recall@5, MRR, false-opposition top-1 rates, toolchain versions and timings appear in the raw result JSON. The preregistered exploratory signal gate **failed**: not every seed gained five points over bad views; no seed equaled PCA; and all seeds had worse-than-allowed stance discrimination relative to bad views.

These are the *same* 96 test queries assessed over three seeds, not 288 independent test items. The generated latent structure is linear and favors PCA; it is a falsification control, not a universal architecture ranking. No external evaluator or independently adjudicated evidence was used. No FAR-specific improvement in truth assessment, general agent reasoning, citation validity, real multimodal retrieval or commercial value has been shown.

## Reproduce and extend

Install NumPy and PyTorch in a **research-only** Python environment. Observed runtime: Python `3.13.5`, NumPy `2.3.5`, PyTorch `2.10.0+cpu`, CPU and no network access. From the repo root:

    python -m unittest discover -s research/good-view-jepa -p 'test_*.py' -v
    python research/good-view-jepa/pilot.py --synthetic --output /tmp/far-jepa-synthetic.json

Synthetic input digest: `3746f2216c40b768b72d8aad6c44b1857fb804c24bf7e32a2f55518888a0930c`. Corrected output SHA-256, including final newline: `027812d345412c501169cc0d5a16d3e420232a65bfe2abc4a2816bc2a72c8db3`. Runtime measurements can vary; compare semantic metrics independently of wall-clock seconds.

With separately registered and precomputed numerical features use `--input /path/to/registered-data.json` instead of `--synthetic`. The [protocol](PROTOCOL.md) describes input identity, split, provenance, finite-vector and label controls. This runner has **no raw image/text feature extraction**. A real multimodal experiment must independently freeze licensed sources, image/text encoder weights and provenance, time cutoffs, verified labels, split hygiene and a strong matched retriever baseline before looking at outcomes.

## Isolation and disposition

Retrieval can rank candidate items but cannot establish a claim's truth, source authority, entailment, citation validity, temporality, or evidence closure. FAR's source and claim checks retain independent authority. This branch changes no `mechanization/`, `frameworks/`, `theory/`, canonical claim ledger or protected-main files.

**Decision: NO OBSERVED GOOD-VIEW ADVANTAGE IN THIS SYNTHETIC PILOT.** Whether it helps real multimodal FAR investigations is **UNKNOWN**. No production adoption is authorized by these results.
