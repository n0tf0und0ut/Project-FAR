# Weight-space intervention research (FAR-WSP-001)

**Status: Research — infrastructure only; 0 model-backed FAR-WSP observations.** This is a bounded extension of the empirical research program. It does not change FAR Core, the production reasoning pipeline, accepted mechanisms, or the existing tool-agent-reliability study. The completed 60-run scripted-repair result in PR #605 and the completed bounded tool-agent study in merged PR #610 remain distinct evidence sources.

## Question and necessity

Can a direct edit to a fixed open-weight model reproducibly remove a measured behavioral failure, more effectively and efficiently than a prompt change, decoding/budget change or a sham checkpoint rewrite, without unacceptable regressions? The immediate impetus is the November 2, 2026 [MIT CSAIL research report](https://rikiyat.github.io/blog/weight-space-programming/). The authors report that GPT-6 Astra removed a repetition-associated direction from 131,072 weights of Qwen3.5-0.8B and changed MATH-500 accuracy from 7.9% to 48.1% while reducing token-limit hits from 93.0% to 33.1%. They also report a negative comparison on Gemma 3 270M, whose failures were not principally loops. These are **author-reported observations**, not evidence of independent reproduction or generic self-improvement.

FAR needs a narrower testable claim: **repair of an independently observable failure mode**. A model can show higher benchmark accuracy by finally returning answers it could already compute; this does not show acquisition of a new mathematical capability. Separately report completion rate and accuracy among completed responses.

## Components

- `tools/weight_space_research.py audit-checkpoint` compares safetensors checkpoints with a bounded memory footprint. It checks model artifacts, tensor names/shape/dtype/metadata, finite floating values, changed element count, allowed tensor names and a prospective change-fraction cap. It produces checkpoint tree digests for provenance. This is an **auditor**, not a patch optimizer, trainer, checkpoint signer or inference engine. No production checkpoint is modified.
- `tools/weight_space_research.py analyze` validates a full five-arm, paired evidence manifest. It binds base/sham/edited checkpoint identities, per-slot traces, original grade files, SHA-256s and the fixed source/suite identities, rejects missing, substituted, forged-success-field, conflicting and duplicated entries, and calculates descriptive paired and family-level results. It does **not** check the semantic truth of a supplied grade, prove prospective freezing, or evaluate a live model.
- `tests/test_weight_space_research.py` exercises complete fixtures, attacks on evidence and sparse checkpoint mutations. All toy outputs and tests are engineering fixtures, not research observations.

## Commands

From the repository root:

```sh
python -m unittest tests.test_weight_space_research -v
python -m tools.weight_space_research audit-checkpoint BASE_DIR EDITED_DIR --allowed-tensor 'model.layers.15.mlp.down_proj.weight' --max-fraction 0.001
python -m tools.weight_space_research analyze FROZEN_MANIFEST.json EVIDENCE_DIR
```

Checkpoint auditing requires optional `torch` and `safetensors`. Evidence analysis uses only the standard library. A checksum is a file identity, not proof of true execution or independent grading.

## Registration and execution status

The experiment is **NOT RUN**. Before touching model weights, freeze the identities of a legitimately accessible open-weight model, original checkpoint, candidate algorithm, controlled frozen task selection, independently withheld task oracles, seed/decoding/token settings, baseline fixes, safety controls, negative-control cohorts, model host, grading code and acceptance thresholds. Select the mechanism only after examining baseline traces, and do not tune on the held-out scored tasks. Changes after exposure require a successor protocol; preserve original observations. No favorable reruns or model substitutions count as part of the frozen sample. See [protocol-v0.1](protocol-v0.1.md).

The internal result screen cannot independently establish causality, general reasoning reliability, safety or customer value. Advancement requires a blinded held-out test, counterfactual intervention/ablation, independent exact-source replay, at least one independent model/failure-family replication, and strong evidence that a simpler solution is not better. A negative result or failure to run is an accepted Research outcome.

## Current-main convergence (2026-11-03)

This five-arm evidence-auditor design is distinct from the completed eight-arm
pilot in [merged PR #613](https://github.com/n0tf0und0ut/Project-FAR/pull/613).
Protected main `c7456b469f9dfe88b92d0fc7a211e5c9ed64de61` already contains
`research/weight-space/`, its actual 432-generation negative result, declarative
array-edit controls and frozen-source replay. That implementation is the existing
execution lane; this PR does not create a second inference runner or claim to
have completed its unregistered five-arm design. The completed pilot found no
advantage over prompting and no eligible production intervention. Its evidence
is neither imported as five-arm observations nor rerun here.

The remaining additive capabilities here are whole-safetensors checkpoint
inventory/allowlist auditing and a strict supplied-evidence five-arm descriptor.
No duplicate memory, agent architecture or production path is introduced.
Future execution must reconcile its question with the existing pilot and satisfy
prospective registration before collecting any scored evidence.

Convergence root cause `WSP-EVID-001`: the grade JSON parser silently accepted
repeated conflicting keys (`"correct": true, "correct": false`), and Python's
boolean/integer key equivalence allowed observation seed `false` to alias 0.
Both were reproduced against the original branch and now fail closed through
unique-key parsing and exact integer observation typing. Checkpoint digest keys
are closed to the three declared identities. Regression controls are in
`tests/test_weight_space_research.py`. All such records remain synthetic
engineering tests. This adds zero experimental observations.

`WSP-TENSOR-001`: an actual safetensors checkpoint containing a scalar tensor
raised `IndexError` because a zero-dimensional slice cannot be indexed with
`[:]`. Scalar values now use the safetensors scalar accessor; larger tensors
retain bounded row slicing. The regression serializes real safetensors files
and verifies exactly one change among ten parameters. This is a software test,
not a model-backed behavioral intervention.

## Exact-head review corrections

All three findings below were reviewed at `afd1f26de828cddda06a8f059b00d59a14448e4a`. Each is **fixed by the commit introducing this section**; the original counterexamples were run before correction and retained as regression tests in `tests/test_weight_space_research.py`.

| Root cause and invariant | Source | Reproduction and correction |
| --- | --- | --- |
| `WSP-FLOAT8-001`: valid finite sparse checkpoints must remain auditable under the declared change budget. | [4459114273](https://github.com/n0tf0und0ut/Project-FAR/pull/611#discussion_r4459114273), thread `PRRT_kwDOTH_vCM6zSJZp` | A real E4M3 safetensors checkpoint with one change among 100 coordinates raised CPU `isfinite` `NotImplementedError` under PyTorch 2.9.0. The current bounded chunk is widened to float64 before finiteness testing. Real E4M3/E5M2 fixtures pass for finite edits, reject NaN/infinity in either checkpoint, and reject an excessive changed fraction. A separate finite `1e300` float64 control prevents a float32 conversion from introducing false overflow failures. |
| `WSP-SHAM-001`: recording a sham identity must permit byte-identical unchanged-weight serialization while the edited identity differs from both controls. | [4459114284](https://github.com/n0tf0und0ut/Project-FAR/pull/611#discussion_r4459114284), thread `PRRT_kwDOTH_vCM6zSJZu` | An actual safetensors save/load/save round trip has identical bytes and file-tree digests. The original gate rejected the complete ten-observation campaign. It now allows base/sham equality; the real-roundtrip campaign passes, and edited/base or edited/sham equality still fails closed. |
| `WSP-ASSET-001`: auxiliary checkpoint files must not cause allocation proportional to file size. | [4459114292](https://github.com/n0tf0und0ut/Project-FAR/pull/611#discussion_r4459114292), thread `PRRT_kwDOTH_vCM6zSJZy` | An unchanged 32 MiB `pytorch_model.bin` produced 33,562,919 bytes of peak traced Python allocation before repair. Auxiliary comparison now reuses the per-file streaming hashes already calculated for tree identity. The same regression observed 2,108,844 bytes after repair, enforces an 8 MiB ceiling, and detects a changed final asset byte. A separate reader guard rejects whole-file or greater-than-1-MiB reads. |

Verification in the shared local environment: **25 supplied-evidence/checkpoint tests and 69 combined weight-space tests pass**, with PyTorch 2.9.0 CPU and safetensors 0.8.0 installed. The existing read-only offline workflow runs the checkpoint suite with those optional dependencies, so these regressions execute instead of being skipped. The frozen schedule validator and retained negative-result reconstruction also pass. No scored model inference ran; the prospective protocol and previously published negative experiment remain byte-identical. Exact-head independent review, hosted checks and merge authority are separate obligations.

## Clean CI dependency correction

`WSP-CI-DEPS-001`: checkpoint job `126233278065` failed on published head `5c6143ec6dea2fce74a1b3785df22aec24695839` with **10 errors among 25 tests**, each reporting `ModuleNotFoundError: No module named 'numpy'` from `safetensors.torch.save_file`. The shared local environment already contained NumPy, masking the missing workflow dependency. This failed hosted outcome is retained; it was not a passing checkpoint run.

The workflow now explicitly installs `numpy==1.26.4` alongside `safetensors==0.8.0`. A fresh Python 3.12 virtual environment with system-site packages disabled reproduced the same ten errors with only the original Torch/safetensors installations. After adding the pinned NumPy dependency, all **69 combined tests pass without skips**, and `pip check` reports no broken requirements. Installed versions are NumPy 1.26.4, PyTorch 2.9.0 CPU and safetensors 0.8.0. The hosted Python 3.11 job still requires verification on the corrected head. No checkpoint-auditor semantics, protocol or model observations changed.

## Empty-tensor metadata correction (2026-11-06)

`WSP-EMPTY-DTYPE-001`: at reviewed head `05985bbff09d424696bde517f9d21864c8d83774`, tensor dtype identity was checked only while comparing value chunks. A tensor with a zero-length first axis yields no row chunks. Actual safetensors files with a protected `empty` tensor changing from float32 to float64 at shape `(0, 2)` and an otherwise allowed one-coordinate edit among 100 parameters therefore passed the audit, violating its identical-dtype contract. The original 69-test suite passed despite this counterexample.

The retained regression `test_empty_tensor_dtype_is_checked_without_value_chunks` failed before correction for shapes `(0, 2)`, `(0, 0)` and `(0, 2, 3)`. Dtype identity is now checked from the lazy slice metadata before value iteration, without loading checkpoint tensors. The test also covers `(2, 0)` and `(0,)`, accepts unchanged empty tensors, and rejects dtype changes for every shape. All **70 combined weight-space tests pass without skips** under Python 3.12, PyTorch 2.9.0 CPU, safetensors 0.8.0 and NumPy 1.26.4; `pip check` passes. The preserved 432-slot schedule and 462-member publication reconstruction remain valid, with zero new model observations. Final-head hosted checks and renewed substantive review remain separate requirements.
