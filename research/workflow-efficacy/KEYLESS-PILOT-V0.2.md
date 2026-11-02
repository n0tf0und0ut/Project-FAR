# Prospective local scripted-repair pilot v0.4

Status: Research / NOT EXECUTED. The scored sample remains 0/60 until the protected-main campaign executes. This synthetic pilot is separate from the unexecuted historical-FAR-PR candidate study in PR #603 and from SWE-agent v3.

## Frozen design before scored execution

- Thirty authored tasks, FWE-001 through FWE-030: ten algorithm families with three variants each. Each has two public and four held-out deterministic input/output comparisons. Only public examples enter the model request; no hidden input or expected output enters model context.
- Control uses the exact pre-#602 Codex AGENTS.md at commit `38e6c8e8b3b1f0a7c75795c9eac8c1c6189cf7ab`. Treatment uses AGENTS.md plus the shared workflow guide from `dc290674b755977378d6170a0128c1540f0a2b6a`. The estimand is the bundled instruction change, including its added context length; no component-specific mechanism is identified.
- Each condition makes exactly one direct localhost Ollama request. There is no autonomous tool loop or OpenCode CLI execution. Both conditions use Qwen2.5-Coder 1.5B Q4_K_M, full model-manifest SHA-256 `d7372fd828518a4d38b1eb196c673c31a85f2ed302b3d1e406c4c2d1b64a0668`, pinned Ollama v0.34.0 archive, temperature 0, seed 0, context 16384 and output ceiling 512 tokens. Generation timeout is 420 seconds. Pinning weights does not prove identical inference across hardware.
- Fifteen tasks are control-first and fifteen treatment-first under the registered deterministic task-hash schedule. Each condition has a separate temporary workspace; the preceding workspace is removed before the next condition starts. Direct API requests carry explicit messages and no conversation history. A warm model process may persist within a pair; order is counterbalanced.
- A syntactically valid generated Python source defining transform is applied once, without repair retries. Invalid, truncated, unchanged, incorrect, or nonterminating submissions are measured failures if a complete model response and valid evaluation exist. Provider or evaluation infrastructure failures leave the study incomplete. Model output must return JSON-serializable results without extra stdout.
- Trusted host code compares all six registered expected answers with outputs from six separate network-disabled, read-only Docker candidate processes. Only candidate source and one input enter each container. Expected answers and assertion machinery stay outside the candidate process. The Python grader image is pinned to digest `b18b261e1b4974b4f321451ad5251ded85abb22c2b8b262da527dda1d031ab30`. Each comparison has a 10-second execution ceiling and a 100,000-byte limit per output stream; buffers are bounded and excessive output is a measured failure. A startup marker distinguishes a started submission exceeding its budget from a container that never began evaluation. Named containers are force-removed after each comparison, including timeouts. All six comparisons must execute; skips, monkeypatched unittest assertions, forged unittest text and non-JSON exits cannot count as passing.
- Retained evidence includes full provider responses, model-step/token metadata, generation-only elapsed seconds, instruction/corpus/source hashes, candidate source, per-comparison trusted grading trace, execution commit and GitHub run identifiers. The analyzer checks artifact hashes and independently reconciles recorded order, model identity, provider output, submitted patch, grading and outcome. Incomplete or inconsistent evidence yields no effect estimate.
- Workflow source and analysis are frozen by the reviewed protected-main merge commit at launch. The owner-only commands on PR #603 are `/far-workflow-free-probe` for an excluded model-access smoke and `/far-workflow-free-60` for the scored campaign. Both check immutable owner ID 344016609. All scored jobs and aggregation use the triggering event revision. Record the exact merge commit, campaign run IDs and artifact digests in the final report. No outcome-based reruns, model changes or task substitutions are permitted.

## Scope and analysis limits

This evaluates instruction effects on one-shot repair of these thirty authored toy specifications with this small model and fixed settings. It does not establish autonomous-agent efficacy, historical FAR repository development performance, external replication, general reasoning reliability or commercial/customer value. Generation timing excludes setup, grading and runner provisioning; it is not end-to-end delivery cost. Zero API charges do not mean zero compute cost.

Report both success counts, paired task outcomes, treatment-minus-control success fraction and generation/token differences. Sign-test and task-bootstrap output are exploratory diagnostics only. The tasks are not a probability sample; variants share ten families, and one deterministic generation per arm cannot estimate model stochastic variability. A bootstrap interval that collapses to zero or a nonsignificant sign test does not establish equivalence, population significance or absence of a practically important effect. Report family-level patterns and the exact finite-corpus result.

## Pre-launch validation

From the exact source checkout:

```bash
python -m unittest tests.test_workflow_efficacy_internal_fixtures tests.test_workflow_efficacy_free_agent tests.test_workflow_efficacy_free_agent_analysis -v
python -m tools.workflow_efficacy_free_agent contract
python -m tools.workflow_efficacy_free_agent schedule
```

Unit/mutation tests and excluded smoke/preflight runs are not scored observations. Only the protected-main execution workflow creates scored evidence. An empty, partial or contradictory campaign remains INCOMPLETE_OR_INVALID.

## Preserved protocol history

The original v0.2 OpenCode tool-agent preflight failed to complete useful interaction. The v0.3 direct-generation preflight completed two responses on FWE-001, but both copied the broken source and failed grading. Both were excluded; the scored sample was 0/60. Before any scored execution, v0.4 corrects the evaluator trust boundary, generated-code timeout handling, full model identity and analysis provenance checks. Earlier provider failures and preflight artifacts remain historical evidence, without relabeling them as scored results. The v0.4 prospective freeze does not retroactively establish the original autonomous-agent question.
