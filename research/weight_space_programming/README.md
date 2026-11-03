# Weight-space intervention research (FAR-WSP-001)

**Status: Research — infrastructure only; 0 model-backed FAR-WSP observations.** This is a bounded extension of the empirical research program. It does not change FAR Core, the production reasoning pipeline, accepted mechanisms, or the existing tool-agent-reliability study. The completed 60-run scripted-repair result in PR #605 and the separate ongoing tool-agent study in PR #610 remain distinct evidence sources.

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
