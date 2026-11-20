# FAR-REPLAN-001: adaptive replanning comparison (Research)

**Status: Research proposal, not executed, not independently registered on protected main.** This comparison is additive to the existing [factory self-evaluation](../factory-evaluation/protocol-v1.json), which remains unchanged. It does not promote accepted FAR theory or grant new tool permissions.

## Why this experiment exists

The bounded Qwen2.5-Coder 1.5B scripted-repair pilot resolved 10/30 FAR-treatment tasks versus 11/30 control tasks. The 7B tool-agent screen passed 72/72 authored executions with restricted virtual tools; neither result tests whether an event-driven controller increases completion in changing, long-horizon environments. The current `tools/subagent_orchestration.py::orchestrate` executes a predeclared directed acyclic plan and blocks dependent agents after failures; it does not dynamically add new intents from verified worker observations. This mismatch justifies a prospective **Research** comparison, not a presumption that replanning works.

## Exact proposed contrast

Canonical candidate protocol: [`replanning-protocol-v1.json`](replanning-protocol-v1.json). The baseline executes `orchestrate` with an independently frozen plan. The candidate uses the **same** agent runtime, model, tool permissions and task objective, plus a bounded event-driven planner capable of adding work after a verified novel observation or failed prerequisite. No ARTEX code is copied. The candidate implementation is **not yet written or frozen**; its code and the control adapter require separate review and registration before any scored run. The study measures task completion, not protected GitHub merge throughput.

The independently authored task cohort will contain twelve local engineering cases, each run once in each arm in separate credential-free, network-restricted workspaces. The evaluator must prefreeze exact source bytes, task descriptions, independent oracle bytes, permissions, model/provider manifest, and the placement of deterministic injected interruptions. The same holdout oracle grades each arm after execution. The model must never read its own holdout oracle. Arm order within a task and pair order are assigned by `tools/replanning_evaluation_contract.py::assignment_schedule` using a fresh unpredictable seed generated **after** all twelve tasks are frozen. Never use the deterministic test seed from unit tests for actual allocation.

## Outcomes and stopping

The primary descriptive contrast is `(verified_replanning_successes - verified_control_successes) / 12`, with the complete paired 2x2 contingency table. Every allocated arm remains in the denominator, including no starts, failures, timeouts and safety stops. A task is successful only if an independent oracle confirms the intended result and the run is not disqualified by an authorization or provenance failure. Retain raw model requests and responses, real tool execution receipts, oracle receipts, timing, budgets, and every negative finding. An external/independent witness must check execution provenance; a model's own completion statement cannot certify success.

A security or evidence-integrity violation stops affected execution and preserves records. Cross-arm leakage, oracle exposure, source changes, model drift, privilege changes or unmatched budgets make the affected paired causal comparison `INCOMPARABLE`, without deleting either outcome. Budget exhaustion and stalling are legitimate terminal results. Twelve related tasks cannot establish general autonomy, superiority or commercial value.

## Registration and next gate

Validate the exact source candidate with:

```bash
python tools/replanning_evaluation_contract.py research/workflow-efficacy/replanning-protocol-v1.json
python -m unittest discover -s tests -p test_replanning_evaluation_contract.py -v
```

Only after independent review, protected merge, and retention of the exact protocol hash and main SHA may an independent evaluator register the execution manifest. That manifest must lock **both executable adapters**, the model/tool/environment identities, an isolated scorer, a sealed cohort and a fresh allocation seed before the first scored agent invocation. Neither this registration candidate nor passing deterministic tests is an agent performance result. No external system or target is in scope. If isolation, model access, or an independent oracle is unavailable, record `BLOCKED` rather than inventing observations.
