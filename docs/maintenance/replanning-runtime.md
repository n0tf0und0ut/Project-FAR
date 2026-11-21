# FAR-REPLAN-001: Research-only replanning runtime adapter

**Status: Research / implementation candidate / no scored model execution.** This code is an implementation of a *bounded orchestration mechanism* for the preregistered [FAR-REPLAN-001 comparison](../../research/workflow-efficacy/replanning-protocol-v1.json), not a validated experiment, a new accepted FAR mechanism, or evidence that replanning improves task completion.

## Exact reuse boundary

`tools/replanning_runtime.py::run_replanning` first runs the original `tools/subagent_orchestration.py::orchestrate` on the frozen input plan and objective. If and only if an external observer supplies a novel event declaration bound to that exact execution result, an external proposal callback can request a follow-up run by an **already authorized root specialist** from the same plan. The planner never gets to choose an arbitrary agent, skill, tool, privilege, scope, completion oracle or coordinator. A fresh one-specialist plan retains the original agent's complete `AgentSpec` and the original coordinator's complete `AgentSpec` except for the coordinator's per-round dependency. FAR's existing orchestrator continues to check capabilities, skill hashes, sandbox identities, report bindings, and evidence visibility on every round.

The original high-level objective and original content-addressed context remain intact. A bounded observer declaration and bounded planner proposal are appended as separately content-addressed **untrusted input data**, not new operator instructions. The adapter rejects unbound source-result hashes, forged observation hashes, duplicate observed event IDs/content, duplicate proposed actions, unauthorized agents, attempts to skip specialist prerequisites, context-ID collisions, and context overflow. Contradictory findings or a blocked coordinator terminate without replanning. A maximum of twelve extra planning rounds is enforced. A failed initial run with no verified event remains a failure; a completed coordinator report is **not** an independent task-success judgment.

## Explicit limits and remaining gates

1. **Observer authenticity is not established.** `VerifiedEvent.verified_by` is a string declaration only, not a signature. An independent host must inspect actual execution and tool receipts and bind an observation to the source execution hash. A model's statement is insufficient. The provided regression fixtures inject observer callbacks and do **not** count as independent evidence.
2. **Hard budgets must be implemented by the underlying runtime.** The adapter bounds planning rounds and context bytes but cannot interrupt an in-flight provider call or enforce the protocol's 45-minute, 15,000-token, or 60-tool-call limits. A trusted external runner must enforce these across the *entire arm execution*, including coordinator and planning calls. Missing or unverifiable meters block a scored run.
3. **Isolation and continuation are external contracts.** The complete arm must execute in a credential-free, network-restricted workspace that is distinct from the other arm, and every actual tool action must be captured. The existing FAR runtime checks claimed capabilities but is not, by itself, a sandbox or an authenticated provider.
4. **The implementation is deliberately restricted.** Only specialists with zero dependencies in the prospectively frozen plan can be selected for follow-up. Broader dynamically discovered toolchains, new skills, dependency rewrite, arbitrary goal changes, and runtime-generated specialist identities are not supported. If the frozen experiment tasks require them, this adapter is ineligible; register a new implementation/cohort before execution rather than silently weakening the rules.
5. **No oracle or trial runner is included.** The independent evaluator must author and seal 12 local tasks/oracles, freeze both implementation arms and the model/provider/container/prompt/tool identities, independently generate the allocation seed after cohort sealing, and retain 24 actual run receipts. `ReplanningTrace` contains orchestration hashes and terminal diagnostics, not an outcome grade.

The control arm remains the repository's unmodified `orchestrate(plan=..., objective=..., context=..., runtime=...)`. The candidate arm uses the same call for round zero and calls it again after verified new observations. This does not imply the cost of the two arms is identical: measure actual tokens, calls, time, and intervention burden instead of assuming parity.

## Verification

The targeted tests invoke **real** FAR `OrchestrationPlan`, `AgentSpec`, `CallableRuntime` and `orchestrate` code with deterministic callbacks; no model or external network executes. They check failure continuation, adapter compatibility, unchanged objective/permissions, unsupported workers, dependency violations, duplicate events/intents, forged hashes, conflicts, isolation failures and bounded execution.

```bash
python -m unittest discover -s tests -p test_replanning_runtime.py -v
python -m unittest discover -s tests -p test_replanning_evaluation_contract.py -v
```

Passing tests demonstrates only these bounded, synthetic software behavior claims. They cannot establish whether a real agent recovers from an unexpected prerequisite, whether the environment is secure, or whether the candidate improves the trial's independently graded completion metric. The original registered protocol and every past FAR result remain unchanged.
