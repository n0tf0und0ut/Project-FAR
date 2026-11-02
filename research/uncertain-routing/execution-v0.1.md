# FAR uncertain-routing pilot v0.1 — observed run and negative control

**Status: Research / bounded internal observation; no product or core promotion.**

## Source and execution identity

- PR: [#608](https://github.com/n0tf0und0ut/Project-FAR/pull/608), initial executed head `cd1741fc4d26df9dfc2a68810b105451f71aa059`.
- Actual GitHub Actions execution: [run 41529666605](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41529666605), [artifact 13182485174](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41529666605/artifacts/13182485174).
- Archived ZIP SHA-256 `185bdb929604b4acdc05092606015418292acc82cc5846515b1126cfd592eddb`.
- `results.json` SHA-256 `62af0ae9dc9322b740868014b771abaf25e3e35f02398ba236d5f11044e32c3d`.
- Frozen protocol input SHA-256 `e0e3ce46271f3c20b664f905af875e10c664630f06a170394b1f300d822d69b7`.
- Qwen2.5-0.5B-Instruct-Q4_K_M GGUF SHA-256 `6eb923e7d26e9cea28811e1a8e852009b21242fb157b26149d3b188f3a8c8653`; pinned llama.cpp b12023 CPU. Exactly 12 model completions; no paid model API calls.
- Independently replayed SHA-256 from all **12 raw request bodies and 12 raw response byte strings**: every hash matched its record. All twelve tasks had distinct prompt hashes. This is actual model inference, not a scripted agent replay.

## Observed actions versus frozen task-author admissible sets

| Quantity | Result |
|---|---:|
| Model action `ASK_SCOPE` | 12/12 |
| Model used any other action | 0/12 |
| Model choices admissible under task-author set | 11/12 |
| Fixed `DISCOVER_CONTRACT` policy admissible | 6/12 |
| Fixed `ASK_SCOPE` policy admissible | **11/12** |
| Unsafe attempt to `VERIFY_EXPLICIT` | 0/12 |
| Model tokens | 1,454 |
| Median model inference decision wall time | 173.1303 ms |

One task, U08, did not list `ASK_SCOPE` as admissible because the task-author rubric instead offered `GATHER_EVIDENCE`, `DISCOVER_CONTRACT` and `PRESERVE_UNKNOWN` for a secondary-source claim lacking primary material. **This is a contestable rubric decision**: asking the user for primary data may also be reasonable. No independent expert adjudication was conducted. The frozen labels are not changed post-result.

## Correct negative conclusion

The model's higher admissibility score than the one chosen fixed baseline (`DISCOVER_CONTRACT`) is **not evidence of adaptive tool routing**. All twelve model actions were exactly the same `ASK_SCOPE`; a trivial deterministic rule `always ASK_SCOPE` ties the model at **11/12**, avoids model inference entirely and uses zero model tokens. Because task labels are set-valued and task-author assigned, there is no ground truth for *the* unique best move and no demonstrated population benefit.

The successor code adds a mechanical comparison against **every** constant action and reports action diversity and `model_minus_best_constant`. Those refinements are analysis-only; the raw pilot responses and frozen task protocol remain unchanged. No claim of improved general reasoning reliability, cost benefit, cognitive insight, or discovered optimal routing is warranted.

## Implications for routing architecture

- Existing explicit FAR IR contracts: the current strict verifier is known; use direct or declarative dispatch, not model arbitration. This is enforced separately in `tools/far_routing_dispatch.py`, which returns intake-required on incomplete/invalid input.
- Under-specified investigations: preserve multiple plausible interpretations and record `Unknown` / intake obligations. Model suggestions can remain non-authoritative **research leads** until tested against competing executable tools, independently adjudicated admissibility and held-out cases.
- Avoid turning model refusal/clarification into a verified judgment or assigning a unique gold action where none is identifiable. The test intentionally did not execute evidence retrieval, intake search or semantic verification.

See [the frozen v0.1 task rubric](frozen-v0.1.json), [the research execution charter](../../docs/governance/research-execution-charter.md), and [the accepted contract discovery protocol](../../methodology/contract-discovery-protocol.md).
