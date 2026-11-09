# Architecture routing — execution observation v0.1

Status: **Research / bounded internal execution only / no FAR core or utility promotion**.

## Verified machine observation

GitHub Actions run [41500632052](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41500632052) executed the three arms on PR head `4a60e21c8270b19d9d7cd1dccf495836c40ad7c8`. The immutable evidence artifact is [13166884946](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41500632052/artifacts/13166884946), ZIP SHA-256 `8ab600ba9326d3a761253f2434ac265cb60c4dcbd4b6bbfd2bfa6894c3b30aad`. Within the artifact: `results.json` SHA-256 `3684fdd97c62af7117fc321996be2885c4da1db4e979c38924de09f81268db56` and `server.log` SHA-256 `14681da8c694ba37a3e02b8204f513148e5c8b005e813f8b89014602bd18cf38`. The artifact expires January 31, 2027 unless preserved elsewhere.

Model: Qwen2.5-0.5B-Instruct Q4_K_M GGUF SHA-256 `6eb923e7d26e9cea28811e1a8e852009b21242fb157b26149d3b188f3a8c8653`; llama.cpp b12023 CPU archive SHA-256 `ae1311cdc0f67bd78e01e7b20bc5ed403814a621c290dd0ee29b8c67c0feece0`. Source cases were constrained to their registered Git blob SHA values. Linux GitHub runner, CPU-only, 2 threads, 12 model completions with no paid API calls.

| Arm | Correct, internal frozen labels | Median end-to-end per case | Model tokens |
|---|---:|---:|---:|
| Deterministic | 12/12 | 1.80917 ms | 0 |
| Declarative | 12/12 | 1.7503135 ms | 0 |
| Model-directed | 12/12 | 74.4446215 ms | 1,728 |

Observed model/deterministic ratio of separate arm medians: **41.1485×**. On all 12 matched cases the model arm was slower than the deterministic arm. The median within-case excess latency was **72.7230 ms**. One model request, the first scheduled one, took 635.7562 ms (cold inference); the other eleven measured between 74.1083 and 74.8535 ms. The model returned `RUN_VERIFIER` on each of 12 queries. Between the fixed approaches, their median times differ by only 0.059 ms; this does not demonstrate reliable micro-latency superiority.

## Identified limitation and successor correction

**V0.1 used an identical prompt across all twelve cases**, confirmed by the identical request SHA-256 in each raw response record (prefix `227cea84a734`). All the projected metadata was shared; this was effectively twelve executions of **one** routing decision, not twelve distinct contextual decisions. The 12 correct final outcomes came from the shared deterministic FAR verifier. The data prove additional measured inference overhead for redundant model routing on this CPU/model/task, not model competence at choosing among distinct verification strategies.

The separately frozen [v0.2 CPU protocol](cpu-protocol-v0.2.json) attempted contract-specific non-oracle fields but [failed the distinct-prompt preflight](preflight-failure-v0.2.md): A01/A04 have identical contracts and different submitted decoder witnesses. The [v0.3 successor](cpu-protocol-v0.3.json) includes that submitted evidence without exposing the reported verdict. It remains an internal bounded study: all cases still have the same safe verifier, so an adaptive-routing superiority claim is not identified.

## Decision and nonclaims

For an explicit, validated `far-ir/2.0` contract with the correct verifier already known, direct dispatch is preferable **on the measured latency and model-token dimensions**. There is no correctness loss on this internal corpus. The deterministic policy's available result is already maximal at 12/12; delegating a binary `verify`/ `abstain` action cannot improve this corpus's correctness.

No external validity, frontier-model comparison, general FAR reasoning superiority, customer value, independent correctness oracle, or architectural replacement is established. The historic v0.1 preregistration is retained unchanged. This outcome is recorded as Research and cannot enter the accepted claims ledger without separately governed evidence.
