# FAR architecture routing — bounded research pilot

**Status: Research / fixed-policy execution available / model experiment NOT EXECUTED.**

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

## Blocked empirical study

A real model-backed trial still requires a frozen model build, independent executor, stable tool-access policy, isolatable prompt and tool traces, verified model outputs, retained raw evidence, identical source visibility, independently held-out evaluation, token/time/cost ceilings, and a bounded cost authorization. These are unresolved. No endpoint is invoked and no tokens are spent in this package. A full three-arm outcome is therefore **NOT ESTABLISHED**. This small deterministic corpus cannot support claims about agent usefulness on unfamiliar or ambiguous reasoning tasks even if a future model run is completed.

The [Research Execution Charter](../../docs/governance/research-execution-charter.md), [canonical FAR workflow](../../frameworks/FAR/workflow.md), [current verifier](../../docs/specification/far-ir-2.0-current-verification.md) and [hostile-source boundary](../../methodology/hostile-source-boundary.md) remain authoritative. The experiment does not promote a finding, claim novelty or justify an architectural replacement.
