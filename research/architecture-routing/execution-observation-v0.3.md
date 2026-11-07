# Architecture routing — executed v0.3 case-specific model comparison

**Status: Research / internally executed / bounded result, not accepted theory or externally validated general utility.**

## Frozen identity and preserved evidence

- Repository PR: [#606](https://github.com/n0tf0und0ut/Project-FAR/pull/606); executed head `7ecaf0c454413f2adab68af961cd27062529600d`.
- Successful no-secret, CPU-only GitHub Actions run: [41503257398](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41503257398), archive [13170780390](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41503257398/artifacts/13170780390).
- ZIP SHA-256: `1fb533502a20c860c28b2a6a8d4a4d8a1b43b133b93c0d376bdb6bc9350e7f6f`.
- `results.json` SHA-256: `17b92856c59e077c3dfb4dfec08fb19ae7ae6d9d0be84439a65eaf1f73622922`.
- Model: Qwen2.5-0.5B-Instruct Q4_K_M, GGUF SHA-256 `6eb923e7d26e9cea28811e1a8e852009b21242fb157b26149d3b188f3a8c8653`; llama.cpp b12023 archive SHA-256 `ae1311cdc0f67bd78e01e7b20bc5ed403814a621c290dd0ee29b8c67c0feece0`. CPU runner, two inference threads, temperature zero.
- The frozen v0.3 protocol was loaded without modification. Source cases were checked against original Git blob hashes. All twelve model prompt requests had **different SHA-256 hashes**. Raw local-model request bodies and base64-encoded response bytes were retained. All twelve preserved request/response SHA-256 pairs were independently recomputed and matched.

## Actual measured observations

| Routing arm | Correct versus project-authored frozen labels | Median end-to-end wall time / case | Model tokens |
|---|---:|---:|---:|
| Direct deterministic | 12/12 | 1.759336 ms | 0 |
| Declarative workflow | 12/12 | 1.723461 ms | 0 |
| Local model-directed | 9/12 | 1,694.4227915 ms | 4,064 |

**Ratio of model and deterministic arm medians: 963.1036×.** Every one of the twelve model-directed observations took longer than its matched deterministic observation. Median paired excess time was 1,692.3688 ms. The 12 model calls consumed an observed total of 21,861.7798 ms of wall time within the case-level timing envelopes.

The language model selected `RUN_VERIFIER` on nine cases. On A01, A04 and A05, it instead returned `ABSTAIN`, producing the correctly counted `NO_VERDICT` and no semantic verification. All three were admissible `far-ir/2.0` verification inputs with registered determinate expected outcomes. Deterministic and declarative routing both invoked the trusted current verifier and matched all twelve reference labels.

The model did not itself adjudicate truth, logic, or evidence. Its only permitted choice was whether to invoke the same verifier. Three lost outcomes therefore represent **routing decisions that suppressed a needed verification**, not wrong arithmetic or wrong theorem proving by the model.

## Per-case action and latency

| Case | Model action | Model result correct? | Model time (ms) |
|---|---|---|---:|
| A01 | ABSTAIN | No | 1,371.840 |
| A02 | RUN_VERIFIER | Yes | 1,265.453 |
| A03 | RUN_VERIFIER | Yes | 2,291.774 |
| A04 | ABSTAIN | No | 544.661 |
| A05 | ABSTAIN | No | 1,599.725 |
| A06 | RUN_VERIFIER | Yes | 1,858.780 |
| A07 | RUN_VERIFIER | Yes | 1,624.060 |
| A08 | RUN_VERIFIER | Yes | 2,346.200 |
| A09 | RUN_VERIFIER | Yes | 1,764.785 |
| A10 | RUN_VERIFIER | Yes | 3,080.879 |
| A11 | RUN_VERIFIER | Yes | 1,621.477 |
| A12 | RUN_VERIFIER | Yes | 2,492.146 |

Rounded per-case values are explanatory; use the archived `results.json` for exact calculations. The raw model responses were `ABSTAIN` on exactly those three cases and `RUN_VERIFIER` on all others.

## Inference and limits

The deterministic policy wins on observed time and categorical correctness for these twelve already-explicit verification submissions. The declarative policy also ties maximum correctness and had practically the same measured latency as deterministic dispatch. Their ~0.036 ms difference **does not establish** a reliable preference between those fixed implementations.

This result is not a test of actual ambiguous routing among multiple verified tools. The model was small (0.5 billion parameters), quantized, CPU-only, and tested once on a public, project-authored corpus with no external held-out oracle. There is no independent reviewer assessing semantic truth of the labels, no population-level uncertainty estimate, no enterprise value claim, and no demonstration that a frontier agent would behave similarly. Two previous execution-stage limitations remain preserved: [the repeated single-prompt v0.1 experiment](execution-observation-v0.1.md) and [v0.2's missing submitted-witness collision](preflight-failure-v0.2.md).

**Bounded decision:** For a fully specified contract with a known applicable verifier, do not pay a language-model routing cost without a demonstrated additional obligation that requires it. Use deterministic or declarative routing; reserve adaptive model routing as a research candidate for genuinely ambiguous or open-world tasks. This finding does not authorize a FAR architectural rewrite or a core-theory status change.
