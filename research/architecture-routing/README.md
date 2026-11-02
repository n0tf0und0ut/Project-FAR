# FAR architecture routing — bounded research pilot

**Status: Research.** An initial bounded local-model execution was observed and preserved in [the v0.1 evidence record](execution-observation-v0.1.md). Its model requests were identical; the [v0.2 preregistered attempt](cpu-protocol-v0.2.json) failed its distinct-prompt preflight, as [recorded here](preflight-failure-v0.2.md). The independently frozen [v0.3 successor](cpu-protocol-v0.3.json) includes the submitted decoder evidence without exposing the reported verdict. Neither record changes FAR's accepted theory or establishes general model superiority.

## Question and scope

For a fully explicit `far-ir/2.0` contract, does language-model-controlled tool selection produce more correct outcomes or lower verified cost than direct deterministic routing or a declarative workflow? This is a routing experiment, separate from PR #603's coding-agent *instruction* experiment. It does not evaluate natural-language claim extraction or open-ended epistemic investigation, and it alters no FAR Core, accepted methodology, or canonical verifier.

Twelve fixed inputs from existing conformance fixtures and four W4 domain pairs are recorded in [protocol-v0.1.json](protocol-v0.1.json), with original Git blob SHAs as of `4e71c7de4457001fd35a65f9b4804d60aac1c4f2`. The source validator checks byte identity before parsing or execution. The reference labels (`PROVED`, `REFUTED`, `INVALID`) are project-authored and publicly visible: they are **not** independently held-out scoring data.

The three arms share `mechanization.far_mechanization.contract_v2_strict_v11.validate_contract`: direct routing, a declared single-step workflow, and a bounded external choice between `verify` and `abstain`. The protocol registers 36 case-arm cells and all six permutations of arm order twice. In smoke and replay the cells execute in that registered order (smoke skips only agent cells). `NO_VERDICT` is counted as incorrect, not removed from the denominator. Source text cannot grant authority to select arbitrary tools.

## Execute and inspect

From the repository root:

```bash
python tools/far_architecture_routing.py schedule
python tools/far_architecture_routing.py smoke
python -m unittest tests.test_far_architecture_routing -v
```

For package-module invocation, `python -m tools.far_architecture_routing smoke` is also supported. The smoke run executes 24 verifications across the two fixed arms and reports the exact count and failures, with `LOCAL_SMOKE_ONLY` and `model_runs: 0`. The tests exercise actual current-verifier results, direct-script invocation, arm-order counterbalancing, hash mismatch, output falsification, missing/duplicate runs and abstentions. Green CI demonstrates internal conformance only.

The external decision interface can be **rehearsed** by putting all twelve case IDs (`A01`–`A12`) into a JSON object with values `"verify"` or `"abstain"`, then running:

```bash
python tools/far_architecture_routing.py replay --decisions decisions.json
```

Extract the JSON `records` array into `records.json` and analyze it with:

```bash
python tools/far_architecture_routing.py analyze --records records.json
```

Scripted runs are labeled `SCRIPTED_REPLAY_ONLY`; records that merely **claim** to have come from a model are labeled `UNVERIFIED_MODEL_REPORTS` even if every metadata field is filled. Neither can produce a scientific efficacy verdict. `elapsed_ms` times the local action invocation, with the verifier imported before timing; it excludes input file loading, external model reasoning, network transit, and end-to-end orchestration. Such timings cannot establish a model-related efficiency advantage.

## Actual local model measurement and its limit

The first GitHub-hosted CPU execution performed 12 genuine Qwen2.5-0.5B-Instruct inference calls plus 24 fixed-verifier executions: 12/12 correctness in every arm on existing project-authored labels. Median action times were 1.80917 ms (deterministic), 1.75031 ms (declarative), and 74.44462 ms (model-directed). The model arm was 41.1485 times slower by the ratio of medians and used 1,728 model tokens. Raw outputs, exact hashes, run IDs and limitations are recorded in [execution observation v0.1](execution-observation-v0.1.md).

Substantive limitation: all twelve model requests in that first trial had the **same prompt SHA**, so the observed difference demonstrates overhead for repeatedly asking a model to make the same known routing decision. It does not demonstrate task-sensitive tool choice. The [v0.2 CPU protocol](cpu-protocol-v0.2.json) failed preflight: the valid and invalid factorization records share an entire contract but have different submitted decoder witnesses. The frozen [v0.3 successor](cpu-protocol-v0.3.json) additionally projects the submitted witness as untrusted data while withholding the reported outcome. Distinct prompts and exact raw request/response preservation are enforced before any v0.3 execution result is recorded.

The offline model smoke workflow runs without provider keys or remote model-inference API. Its executable entry point is:

```bash
python -m unittest tests.test_far_architecture_cpu_experiment -v
# Runtime study is launched by .github/workflows/far-architecture-offline-model.yml
# Evidence: GitHub Actions run-artifacts, with raw request/response data
```

## External model and empirical validity limits



A real model-backed trial still requires a frozen model build, independent executor, stable tool-access policy, isolatable prompt and tool traces, verified model outputs, retained raw evidence, identical source visibility, independently held-out evaluation, token/time/cost ceilings, and a bounded cost authorization. These are unresolved. No endpoint is invoked and no tokens are spent in this package. A full three-arm outcome is therefore **NOT ESTABLISHED**. This small deterministic corpus cannot support claims about agent usefulness on unfamiliar or ambiguous reasoning tasks even if a future model run is completed.

The [Research Execution Charter](../../docs/governance/research-execution-charter.md), [canonical FAR workflow](../../frameworks/FAR/workflow.md), [current verifier](../../docs/specification/far-ir-2.0-current-verification.md) and [hostile-source boundary](../../methodology/hostile-source-boundary.md) remain authoritative. The experiment does not promote a finding, claim novelty or justify an architectural replacement.
