# Weight-space programming and bounded reliability research

Status: Research. No production reasoning path imports these tools. Protected-main baseline: `a3f5825ee74af723d660a55e6708ef96e305b156`; governing theory remains PROJECT-FAR-CORE-THEORY-1.1.

The [completed execution report](RESULTS-V0.1.md) preserves 432 actual scored generations and their negative result: the selected edit tied prompting, showed no advantage, and did not qualify for adoption. The [integration audit](integration-audit-2026-11-03.md) records subsequent cold reconstruction, metadata-preservation repairs and reconciliation with merged PR #610.

The [MIT source/tensor verification](mit/VERIFICATION.md) reconstructs the original Qwen result and exact BF16 edit without new inference. Its [source manifest](mit/mit-source-manifest.json) and [tensor receipt](mit/tensor-replay/receipt.json) preserve immutable upstream identities. It does not show that FAR improved a model. Reproduce source arithmetic with a clone of `RikiyaT/lm_understand-logs` at `4d09ba6d6a7e891dd8063974dfe81b3d78e3494f` placed under `mit/lm_understand-logs`, then run `python research/weight-space/mit/verify_original_evidence.py`. The two `replay_*`/`verify_published_checkpoint.py` scripts perform actual immutable HTTP-range tensor verification, requiring NumPy and network; none execute author-provided code or model inference. Upstream benchmark material remains upstream; this repository preserves hashes and locally authored analysis.

## Existing evidence and reuse

The completed [60-run scripted-repair study](../workflow-efficacy/KEYLESS-PILOT-RESULTS-V0.4.md), implemented in merged PR #605 and published in merged PR #609, found control 11/30, FAR treatment 10/30, difference −3.33 percentage points. It does not measure multistep general agent reliability and is not repeated here.

[PR #610](https://github.com/n0tf0und0ut/Project-FAR/pull/610) is a separate operational tool-agent study. Frozen v0.3 execution source `6c382c798df0a95824b79e76263318865ee24c68`, publication `854c0431b7e9dce5a6b90d6dde39234f57449c25`, workflow `41620413774`: 72/72 scored episodes, 24/24 tasks passed all three repeats, zero unsafe writes; 3/3 separate preflight. Independent raw replay and task-oracle reconstruction agreed. Temperature zero produced identical trajectories for 23/24 tasks; the 72 episodes are not independent samples. No FAR treatment contrast or general reliability inference follows. The earlier 1.5B preflights failed 1/3 and 2/3 with one unsafe write each; their broader 72-slot studies were not run. Preserve all versions. Its protected review gates remain separate from experimental completion.

[PR #601](https://github.com/n0tf0und0ut/Project-FAR/pull/601) already audits activation replacement and exposes failed mechanistic/reliability hypotheses. This work reuses its pinned Smol135M checkpoint, float32 CPU provenance and MLP intervention boundary; its unmerged production modules are not imported. An activation-fidelity checker does not perform checkpoint differences or verify arbitrary task answers. These are complementary experiments with distinct records, not a combined performance result.

## Bounded experimental capability

`tools/weight_space_edits.py` accepts declarative identity, column-scale, directional-projection and sparse-replacement proposals under a separate trusted policy. It rejects unknown fields, executable content, forged base hashes, wrong shapes/dtypes, nonfinite values, duplicate coordinates, and parameter/column/norm-budget violations. The audit distinguishes addressed coordinates, actual byte changes after rounding, numerical changes, exact changed-coordinate commitment and tensor digests. NumPy float16/32/64 two-dimensional arrays are supported; the MIT BF16 receipt uses a separate raw-uint16 replay. No result is an approval or deployment authority.

`tools/weight_space_pilot.py` loads only hash-checked safetensors from one immutable open checkpoint with remote code disabled. A fixed algorithm chooses one last-layer MLP output column using six development prompt activations. It gets no evaluation labels or prompts. The coordinator authored all tasks and has seen them; this is algorithmic information separation, not externally blinded independence. The algorithm is a model-authored proposal procedure, not a demonstrated autonomous discovery of a semantic circuit.

The evaluator owns the policy, complete randomized schedule, seeds, source freeze, exact output-contract grading, per-episode full parameter inventory, restoration check, and write-once raw evidence. The proposer cannot execute generated Python or change the grader. Process-level isolation from a malicious host is not supplied. Tokenizer-bound independent replay checks raw IDs against text, actual sparse tensor edits against the checkpoint, selection inputs, exact commit bytes, slot accounting and recomputed grades. Trace validation does not prove a trustworthy remote execution occurred; independent rerunning remains necessary.

The [prospective protocol](protocol-v0.1.json) freezes 12 authored heldout output tasks and six regression tasks, three stochastic seeds and eight arms: baseline, sham, high-influence column ablation, half ablation, norm-matched random-column ablation, prompt correction, repetition penalty, and doubled token budget. Six development generations are excluded from the 432 scored generations. Failure categories cover repetition, completion, tool-action selection, unsupported inference and distraction, as operational output proxies. They do not diagnose internal reasoning causes or establish multistep tool execution. The loop hypothesis is untestable unless at least two development repetitions are observed; report that outcome rather than inventing loops.

All attempts, setup failures, negative findings, regressions and arm costs must be retained. No outcome-based retry, model search, prompt revision or pooling is permitted. Inference is actual pretrained-model generation; offline synthetic unit fixtures never count as observations. The pilot's fixed scalar output contract is narrow, public and author-curated. No benchmark-wide or general intelligence claim follows.

## Commands

```bash
python -m venv /tmp/far-weight-env
/tmp/far-weight-env/bin/pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu
/tmp/far-weight-env/bin/pip install -r research/weight-space/requirements.txt
/tmp/far-weight-env/bin/python -m unittest tests.test_weight_space_edits tests.test_weight_space_pilot -v
/tmp/far-weight-env/bin/python -m tools.weight_space_pilot validate
/tmp/far-weight-env/bin/python -m tools.weight_space_pilot fetch --model-dir /tmp/far-smol135m
# Commit experimental source before running. Use a new output path for every attempt.
/tmp/far-weight-env/bin/python -m tools.weight_space_pilot run --model-dir /tmp/far-smol135m --output /tmp/far-weight-attempt-01
/tmp/far-weight-env/bin/python -m tools.weight_space_pilot replay --model-dir /tmp/far-smol135m --output /tmp/far-weight-attempt-01
```

Replay uses the exact experimental source commit recorded in the output; check out that commit before replaying archived evidence. This recomputes traces, tokenization, sparse edits and grading without generating new answers. A full independent reproduction requires executing new model generations on an independently controlled machine with the same frozen source, weights and runtime. CPU, threads, attention implementation, primary numerical/tokenizer versions and checkpoint/file hashes are recorded; different numerical environments may diverge even with equal seeds.

`python -m tools.check_weight_space_publication` verifies all published ZIP members, the frozen-source bindings, complete slots, grades and analysis without downloads, extraction or inference. It runs in CI together with eight actual-archive mutation tests. It does not replace checkpoint/tokenizer replay or attest that a trusted machine generated the traces. Git history must contain the registered source commit; the dedicated workflow fetches full history. MIT verifiers now compare their published receipts read-only by default. Use `--source-dir /path/to/lm_understand-logs` for the source/tensor scripts, and `--output` or `--output-dir` only to create a new reconstruction; existing destinations are refused.

The primary score compares trimmed exact text and strict JSON values, including exact calculator-expression rendering. This is narrower than semantic task correctness: equivalent expression whitespace or answer-label capitalization can fail the primary contract. Any semantic sensitivity regrading must be labeled separately, preserve every primary grade, and never count as new model inference.

The separate five-arm loop-repair design in [PR #611](https://github.com/n0tf0und0ut/Project-FAR/pull/611) remains NOT RUN. This eight-arm output pilot does not complete that protocol. See [internal review and integration boundaries](REVIEW.md).

## Adoption decision

No pilot result automatically approves a production change. A candidate must beat the strongest applicable simpler method by a predeclared meaningful margin, show acceptable regression and cost tradeoffs, survive controls and dose ablations, transfer across independent tasks/checkpoints, and be independently reproduced under a new prospectively frozen protocol. The present software always reports `production_eligible: false`. No canonical methodology or theory is promoted.

A fixed small corpus can falsify a proposed edit's usefulness on that corpus. It cannot establish general reasoning reliability, commercial value, recursive self-improvement or that arbitrary future edits will fail. Preserve negative results rather than silently selecting a new neuron after seeing evaluation grades.
