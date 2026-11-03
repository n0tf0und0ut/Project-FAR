# Weight-space programming execution and reliability evidence — 2026-11-03

Status: Research. **Completed 432/432 scored pretrained-model generations plus six development generations. No production intervention qualifies.** General agent reliability and FAR workflow improvement remain unestablished.

## Authoritative baseline and distinct studies

Protected-main baseline: `a3f5825ee74af723d660a55e6708ef96e305b156`. FAR Core v1.1 and canonical governance are unchanged. PR #605 implemented the completed 60-run one-shot scripted-repair study, with results published in merged #609: control 11/30 versus FAR 10/30, −3.33 percentage points. It was not repeated or relabeled as general reliability.

PR #610's frozen v0.3 source `6c382c798df0a95824b79e76263318865ee24c68`, publication `854c0431b7e9dce5a6b90d6dde39234f57449c25`: 72/72 scored tool episodes; 24/24 tasks pass all three repeats; zero unsafe writes. Three separate preflight episodes passed. All 14 original archive identities, 75 raw records, actual task oracles and frozen-source reports were independently rechecked. At temperature zero 23/24 tasks produced identical trajectories. Cost: 228 model calls, 88,013 input tokens, 3,581 output tokens, 1,517.215 aggregate episode seconds; median 18.990 seconds. Earlier 1.5B preflights remain 1/3 and 2/3 with one unauthorized write each, and their broader studies NOT RUN. These observations are not 72 independent population samples, do not compare FAR to a control, and do not establish real-world or general reliability.

PR #611 remains a DESIGN ONLY five-arm loop-repair contract plus supplied-evidence auditor. This separate eight-arm output-contract pilot does not complete that protocol. PR #601 remains a distinct activation-fidelity study with negative mechanistic findings. No results are pooled.

## MIT findings and exact reproduction boundary

See the [full verification](mit/VERIFICATION.md). The original Qwen study's MATH-500 counts reconstruct exactly as 158/2,000 → 962/2,000, 7.9% → 48.1%. Immutable base revision `2fc06364715b967f1860aea9cf38778875588b17`; layers 15/19 each edit 64 MLP output columns, using a layer-specific residual direction and subtraction scale 6. 131,072 coordinates are addressed; 130,188 BF16 values actually change. Locally fetched immutable source tensor bytes, applied the sparse arrays, and matched both author-evaluated tensor hashes and public edited-checkpoint tensors. Recomputed 46 benchmark-condition groups from 561 source files. **No original MIT benchmark generation was rerun locally.**

Most practice rescues were originally truncated (576/579); five regressions remain. The reported Gemma follow-up does not establish gain; its lenient versus boxed grading must be distinguished. The external edited-checkpoint rerun reports 51.0%, but its base comparator is only 25 problems. Strong optimized non-thinking, prompting, decoding, interruption and budget alternatives were absent from the released benchmark comparison. The loop-circuit interpretation is supported but incomplete; broad capability addition, reliable cross-model optimization and recursive self-improvement were not demonstrated.

## Registered experiment and actual results

Frozen public source: `bb48be7df44adf9d30f018f3528bbd9db49555e1`. [Protocol](protocol-v0.1.json), [checkpoint manifest](smol135m-checkpoint.json), [all raw evidence](results/smol135m-v01-evidence.zip), [analysis](results/smol135m-v01-analysis.json), [archive/member manifest](results/smol135m-v01-manifest.json).

Model: SmolLM2-135M-Instruct, revision `12fd25f77366fa6b3b4b768ec3050bf629380bac`, PyTorch 2.5.1 CPU float32, eager attention, two threads, Transformers 4.49.0, tokenizers 0.21.4. 12 authored heldout output tasks and six regression tasks, three stochastic seeds, eight randomized conditions. Six development tasks feed activation selection only; evaluation prompts/labels are withheld from the selector, not from the coordinator who authored the corpus. Separate trusted host graders agree; they are not externally blinded oracles.

Selection fixed column 1498 in `model.layers.29.mlp.down_proj.weight`; matched random column 778, norm ratio 0.983241. The in-memory ablation changes 576 parameter bit patterns, half ablation 576, random ablation 576; sham changes zero. Full parameter inventories were checked before every scored generation and restored at completion. Independent replay reconstructs the complete baseline inventory from pinned safetensors, the selector, exact tensor differences, raw tokenization, all slots and host grades.

| Condition | Heldout exact contracts | Regression exact contracts | Tasks passing all 3 trials | Generated tokens | Generation seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 0/36 | 0/18 | 0/18 | 1771 | 103.683 |
| sham | 0/36 | 0/18 | 0/18 | 1771 | 103.081 |
| ablate | 1/36 | 0/18 | 0/18 | 1783 | 103.992 |
| half_ablate | 0/36 | 0/18 | 0/18 | 1944 | 112.749 |
| random_ablate | 0/36 | 0/18 | 0/18 | 2439 | 141.235 |
| prompt | 1/36 | 0/18 | 0/18 | 1462 | 89.668 |
| decoding | 0/36 | 0/18 | 0/18 | 2996 | 172.412 |
| budget | 0/36 | 0/18 | 0/18 | 2427 | 141.292 |

Strongest **tested** simpler arm: `prompt`. Registered primary edited-minus-that-arm heldout difference: 0.000 percentage points. Task-cluster bootstrap diagnostic 95% interval: [-0.08333333333333333, 0.08333333333333333]; this is not a population interval or an independently randomized task sample. Registered screen: `{"minimum_gain_met": false, "positive_task_bootstrap_lower_bound": false, "regression_difference": 0.0, "regression_tolerance_met": true}`. Half-strength/random controls and all category failures are retained in the JSON analysis rather than selecting a favorable subgroup.

Development repetitions: 0/6. HLOOP disposition: **NOT_TESTABLE; fewer than two development repetition-proxy failures**. Wrong output format, an unfinished answer and a repetitive internal reasoning loop are distinct; these task labels do not diagnose a neural mechanism.

Primary grades are trimmed exact text or strict JSON-value equality, including exact expression strings. The separate post-registration semantic sensitivity receipt in the archive examines case-insensitive answer labels and equivalent calculator expressions. It changes no primary grade and adds zero model observations. The sensitivity admits three capitalization-only outputs (budget slot90, baseline91, sham95), and no calculator-expression-only failures. Baseline, sham, ablation, prompt and budget each then score 1/54 overall; half ablation, random ablation and decoding score 0/54. It still demonstrates no weight advantage. These are relaxed post-registration scores, not replacement primary results.

Actual total attempt wall time: 1,197.829 seconds. The table measures generation-only wall time, CPU and tokens; setup, checkpoint audit, activation selection, serialization and queueing are excluded from per-generation timing. Full attempt time includes those local overheads. Total scored generation CPU seconds: 1,891.907. Development generation/activation cost is distinct; FLOPs, energy and dollar costs were not measured. Supplemental installed-package/build metadata is included and labeled as captured after execution began. No paid provider API or model fallback was used.

**Floor limitation:** all arms scored 0/18 on the strict regression contracts. A zero edited-minus-baseline difference therefore provides no evidence that useful capability was preserved. Several baseline arithmetic outputs contain correct arithmetic but violate the requested answer-only format; exact-contract success is not a complete semantic reasoning measure. The primary score remains frozen. The present candidate failed the meaningful-gain screen and tied the prompt fix; it does not advance.

## Causal scope, failures and adoption

This tests the first frozen candidate, preserving negative outcomes and regressions. At fixed prompts, seeds and runtime, edited-arm parameter inventories differ only by the declared column; sham output IDs must exactly equal baseline IDs. This supports only the observed finite intervention comparison. It does not identify the column's semantic function, exclude every hidden runtime fault, establish an optimum prompt/decoding baseline, or generalize beyond this authored cohort. Cross-model transfer and external rerunning are **NOT RUN**.

No production promotion is justified. The present candidate must satisfy every prospective screen before even advancing; an internal screen never substitutes for independent preregistered replication, representative heldout tasks, stronger simpler baselines, transfer, tolerable regressions/costs and protected approval. The MIT Qwen loop repair warrants targeted replication against those simpler alternatives. General self-improvement or increased-intelligence claims remain unsupported.

## Software validation and review

32 targeted numeric/evidence tests passed. Independent final replay reproduced the full analysis byte-for-byte and rejected all 12 malicious mutations of copied actual traces; no new inference occurred in that replay. Canonical runner: 2,736 tests, zero failures, three skips. `make health-fast`: 125 repository checks, zero warnings/failures, followed by the remaining Makefile validators and 20 theory-dependency tests. PR-fast no-cache validation SUCCESS, including canonical tests, research/claim/authorization gates, health, hygiene and Markdown. Documentation, workflow, internal-link and final-newline validators passed. Unit fixtures are not model observations.

[Internal review ledger](REVIEW.md) records five pre-inference defects and permanent regressions: text/token false credit; untracked/fake source freeze; untested loop interpretation; trusted self-reported edit hashes; missing early-phase failure receipts. Separate internal review independently reconstructs actual tensor/trace evidence, with prior shared exposure disclosed. It is not external scientific independence or protected PR approval. Final exact-head CI, independent substantive review, signed assurance and protected merge authorization remain separate gates. No merge or production change is claimed.

Evidence archive SHA-256: `e687b9165b1a9ce5a77290711007de9389adc3aac536a321d61090b0843a8b35`, 2,391,819 bytes, 462 members. The archive binds every original evidence byte, final raw replay, semantic sensitivity and supplemental software verification. Checksums establish identity; they are not an external execution attestation.
