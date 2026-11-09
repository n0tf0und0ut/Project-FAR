# FAR-MAS-EXTERNAL-003 — completed experiment and negative finding

**Status: Research / 96 of 96 registered neural runs completed / preregistered primary screen FAILED. No promotion to Accepted theory or FAR production capability.**

## Why this study was conducted

FAR's v0.1 synthetic architecture-search pilot initially appeared to favor two attention blocks. The registered v0.2 matched-capacity follow-up failed its primary advantage screen. The next distinct falsifier was transfer from self-authored bit tasks to fixed, externally collected classification data, with stronger simple alternatives and explicit parameter/MAC-proxy controls.

**Not official CLRS/NAS-Bench-360:** Those official data and reference evaluation environments were unavailable, and the local runtime could not fetch their official downloads. This study must not be represented as their evaluation or an independent scientific adjudication. It uses external UCI datasets *bundled* into scikit-learn, but all train/validation/test splits and architectures are FAR-authored.

## Registration and immutable identities

- Study: `FAR-MAS-EXTERNAL-003`, protocol `far-mas-external/0.3`.
- Original protocol prospectively committed to research branch in GitHub commit `7bba2ef291b90be178e72ab680fc84f7bb1fd62a`, **before** any scored model inference. Full protocol SHA-256: `73281ff83c57a7893220b21245e45c43a57ecca2089bfd03d2bb391188abf05b`.
- Original source SHA-256 `83cd655603557bd62b95119216aaf674938c698f915eff65fab7f1bd5523202f` was fixed and referenced in that public protocol **before** inference. The corresponding frozen source bytes were committed to the same research branch *during* execution, and subsequently verified to match this prospectively frozen hash. These two timestamp claims are distinct; code publication did not precede the very first model inference.
- Data SHA-256: UCI digits `f6d9e39f37dc45d327f6db33428ee58970ccceabb2535a5c179de35886b70443`; UCI Wisconsin diagnostic `25e2eb7b7a8745b1bde5ba18bc4969983d2e2f403291ecd5bde4a29ef30c3859`.
- Dataset split SHA-256: digits `52aa6260697bb7fd91a1b48cb3b07ab3f6a8a21fa969894fd53aa4fc82d05b9b`; Wisconsin `18d62d14ccb655953ad1c7ecb861511f16c77344109dca9d1a769fbe52277d99`.
- Original report SHA-256 (excluding the self-field): `0e316abb4119d10281cec2c4b0d233fe4cbfca8353db23f22eadf770e415e808`; original journal SHA-256: `5045e99348c372ac7a210c87ed539625998c036ca0fc92a8106a137cd8b10941`.
- Recorded environment: Python 3.13.5, PyTorch 2.10.0+cpu, scikit-learn 1.8.0, NumPy 2.3.5, one CPU thread, deterministic PyTorch algorithms.

No scored run was replaced, tuned or omitted after test data became available. Frozen original data, training code, protocol and outcome records remain unchanged. New replay and integrity checkers are explicitly post-execution software.

## Executed design

Two external datasets, four models (two attention blocks, one wider attention block, GRU, causal-ish depthwise convolution), widths 48 and 72 for the two-block reference, 80 and 160 gradient-update steps, and three paired training seeds: **96 neural trials**. Model-family widths were selected before fitting to match parameter count and estimated forward multiply-accumulate count (MAC proxy). Maximum absolute differences across the 96 trials were **8.31% in parameters** and **8.43% in estimated forward MACs**, below the prespecified 11% caps.

These are analytic MAC approximations and do **not** establish equal actual FLOPs, training energy, hardware efficiency, elapsed time or optimization difficulty. The test data were never used for architecture selection: every group generated its validation-only `selection_locked` journal event before any held-out predictions in that group. Additional fixed non-neural references were logistic regression, RBF-SVM and 5-NN, **not** parameter-/compute-matched to the neural systems.

## Original result: failure of primary registered screen

The predeclared 72-width/160-step screen required a mean held-out advantage **at least +2 percentage points** for the validation-selected neural model versus the validation-selected strongest conventional reference, on both external datasets, with no more than 2 points' selection regret. The score for the two datasets is:

| Dataset | Neural model selected using validation | Neural held-out accuracy, 3-seed mean | Strong simple model selected using validation | Simple held-out accuracy | Neural minus simple |
| --- | --- | ---: | --- | ---: | ---: |
| UCI 8×8 handwritten digits (360 test examples) | Depthwise convolution | 97.41% | RBF-SVM | 98.06% | **−0.65 pp** |
| UCI Wisconsin Diagnostic measurements (114 test examples) | Depthwise convolution | 97.08% | Logistic regression | 98.25% | **−1.17 pp** |

**Primary verdict: FAIL on both datasets.** Selection regret was zero for the selected neural family in both primary groups, but that condition alone cannot rescue the failure. No stable advantage or useful neural architecture superiority has been established.

Actual held-out accuracies for all four neural conditions and both model scales/training budgets (mean across three seeds):

| Dataset / width / steps | Two attention blocks | One attention block | GRU | Convolution | Validation-selected model |
| --- | ---: | ---: | ---: | ---: | --- |
| Digits / 48 / 80 | 84.81% | 80.74% | 93.15% | 92.13% | GRU |
| Digits / 48 / 160 | 89.72% | 91.76% | 97.22% | 97.41% | GRU |
| Digits / 72 / 80 | 83.89% | 80.19% | 94.44% | 94.35% | GRU |
| Digits / 72 / 160 | 88.70% | 89.81% | 97.22% | 97.41% | Convolution |
| Wisconsin / 48 / 80 | 97.08% | 94.74% | 94.15% | 95.32% | Two attention blocks |
| Wisconsin / 48 / 160 | 95.91% | 96.20% | 95.03% | 96.20% | Convolution |
| Wisconsin / 72 / 80 | 93.27% | 92.69% | 94.15% | 93.86% | GRU |
| Wisconsin / 72 / 160 | 92.98% | 94.44% | 93.27% | 97.08% | Convolution |

The top performer varied with dataset, width, and optimization budget. The original stacked-attention candidate was not the reliable winner. On the simple digit and Wisconsin data, fixed conventional models remained more efficient than the selected neural models: the selected neural models took about 1.72 and 5.32 seconds to train per seed, respectively, versus 0.039 and 0.028 seconds for the chosen SVM and logistic reference. These times are hardware- and implementation-dependent and not a universal efficiency comparison. Class-level metrics, exact predictions and all durations remain in the original report.

## Data and outcome verification

- All **96/96** original score records present; all **96/96** have source-bound parameter counts, estimated MACs, validation and test predictions, per-class scores, training budgets, seeds, and model-state SHA-256 digests.
- The frozen raw dataset arrays, stratified split indices and train-only normalization were recomputed. Test scores, reference model predictions and validation-only selection analysis can be independently regraded from the saved output records. The append-only journal includes every training started/completed, eight selection locks, 96 held-out test completions, two reference-model completions, and the terminal complete event.
- The post-execution deterministic replay attempted all 96 original models under the recorded environment and restored one-thread CPU configuration: **96/96 model state fingerprints and both validation/test predictions matched**, with all six conventional baseline prediction series matching. This is same-environment mechanical replay, **not independent scientific replication**.
- The first replay invocation failed before recording a receipt because its script was invoked directly without the repo root on Python's import path. This failure is retained. The replay wrapper was corrected without altering original source or trials. The one-slot preflight and then full 96-slot replay passed. Original failures and successful receipts are retained separately.
- The independently authored archive auditor checks member digests, source and protocol binding, full event stage coverage, selection-lock ordering and training-to-test record correspondence; mutation tests reject substituted grades, missing slots and archive alteration. None of these software checks establishes an externally trusted execution environment or scientifically independent adjudication.

The immutable compressed archive `archive-v0.3.zip.b64` contains the full original report, journal, protocol, model source and tests, replay scripts, all successful and failed preflight evidence, CLI stdout and an internal SHA-256 manifest. Its decoded ZIP checksum is recorded separately after assembly, never retroactively edited into the frozen experiment.

## Decision and remaining blockers

- **Reject** a claim that FAR currently produces a superior neural architecture, or has achieved general autonomous AI self-improvement.
- **Retain** the implemented search/benchmark tooling as Research and the negative results as part of the permanent audit trail. Do not change FAR's production pipeline or accepted theory on this evidence.
- Official CLRS-30 or NAS-Bench-360 results remain **NOT EXECUTED** because the official data/reference environments are unavailable. The available UCI datasets remain small, externally collected but internally administered; there is no independent evaluator.
- Actual-accelerator FLOPs/energy/time-equated training, substantially larger model scales, external tasks beyond fixed tabular/digit datasets, modern NAS comparators, and exact-head substantive GitHub review/merge authorization remain outstanding. A source-integrity or local CI green check does not satisfy these.

Reproduction commands from repo root (with optional `torch`, `numpy` and `scikit-learn` installed):

```bash
python tools/model_architecture_external.py check --protocol research/model-architecture-search/protocol-v0.3.json
python -m unittest discover -s tests -p 'test_model_architecture*.py' -v
base64 --decode research/model-architecture-search/archive-v0.3.zip.b64 > /tmp/far-mas-v0.3.zip
python tools/check_model_architecture_external_archive.py --archive research/model-architecture-search/archive-v0.3.zip.b64
```

A fresh rerun of the original scored trial under the same ID would not be a new independent replication and must not replace the retained negative result. The standalone model replay documented above only verifies the original registered observations.
