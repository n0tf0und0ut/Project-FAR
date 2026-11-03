# Agent Workflow Orchestration

Status: operational guidance only. This document does not establish or change FAR theory, research authorization, evidence, governance, claim status, or merge authority.

This supplements the runtime-specific instructions in [`AGENTS.md`](../../AGENTS.md) (Codex) and [`CLAUDE.md`](../../CLAUDE.md) (Claude). The [Research Execution Charter](../governance/research-execution-charter.md), current canonical state, tool capabilities, protected-branch rules, and [PR review convergence policy](../governance/pr-review-convergence.md) control in case of conflict. A workflow aid never grants permission to perform a governed investigation or promote a result.

## 1. Plan mode by default for non-trivial work

- For tasks with at least three meaningful steps, significant uncertainty, or architectural choices, make a concrete plan before editing. Use a native plan mode if the runtime supplies one; otherwise keep a short, explicit checklist.
- Define the goal, governing sources, affected files, dependencies, assumptions, acceptance conditions, validation, and stopping conditions. Specify research freeze/preregistration obligations when applicable.
- Plan the verification, independent review, and final diff inspection as carefully as the construction steps.
- When an assumption fails, evidence conflicts, tests fail, or scope changes, stop the affected action, investigate the cause, revise the plan, and then continue from verified state.
- Simple, obvious changes do not require a separate formal plan. Planning is not an automatic request for user approval when authorization already exists.

## 2. Focused subagent strategy

- When actual subagent tools are available, delegate bounded research, source discovery, exploration, adversarial analysis, or independent code inspection to focused workers; use up to five concurrent workers when that improves coverage and isolation.
- Give each worker one precise task, explicit inputs and output requirements, and a known read/write boundary. Keep conflicting writes sequential; the coordinator integrates findings and validates the combined result.
- Prefer parallel independent reads to duplicated reasoning. Do not create subagents solely because the task is complex or claim a subagent ran when no tool executed.
- Treat subagent agreement as internal evidence only. The existing [subagent execution architecture](../architecture/far-subagent-execution.md) and isolation rules govern any FAR-specific research or claimed independence.

## 3. Self-improvement from corrections

- After user correction or a discovered failure, capture what failed, why it failed, and the smallest preventive step in the active task record.
- Add a durable lesson to `tasks/lessons.md` only when a demonstrated root cause recurs or a sufficiently serious single failure justifies a persistent control. Check for existing coverage first; prefer a regression test or deterministic validator for deterministic failures.
- State the trigger, reproducer or evidence, preventive rule, and how effectiveness will be checked. Do not turn every disagreement or one-off fix into a permanent instruction.
- Review relevant existing lessons at the start of comparable work and revise or remove proven stale or duplicative guidance through the appropriate repository process. No lesson overrides FAR authority or frozen evidence.

## 4. Verification before done

- Do not declare success merely because edits were made, a command exited zero, or CI metadata is green. Demonstrate the behavior or bounded claim that the change was meant to support.
- Inspect the complete final diff against the target branch and check for accidental changes, generated-file drift, policy conflicts, and unintended effects.
- Run relevant tests, lint/static checks, document links, semantic checks, and workflow logs where the environment allows. Reproduce defects before fixing and retain defect-detecting tests where appropriate.
- Distinguish what was executed and observed from what remains inferred, unverified, or externally blocked. Do not call bounded testing a universal proof.
- For PRs, satisfy exact-head review, independent substantive review, required checks, and protected merge authorization separately.

## 5. Balanced demand for elegance

- For non-trivial changes, ask whether a simpler, more maintainable solution satisfies the same verified requirements with fewer moving parts.
- If a fix is an ad hoc workaround, investigate the root cause and prefer a complete correction when the evidence supports one.
- Challenge the proposed implementation with counterexamples and integration risks before presenting it.
- Do not over-engineer simple fixes, expand to unrelated refactors, or trade correctness for fewer lines. Minimal impact means changing only what the task requires.

## 6. Autonomous bug fixing

- Given a concrete bug report, locate the relevant code, logs, failing tests, and observed symptoms; reproduce the defect; isolate the root cause; fix it; and re-run appropriate validation.
- Resolve repository-fixable CI failures without waiting for step-by-step user direction. Re-plan if failure reveals an incorrect assumption or a wider underlying defect.
- Report genuine missing permissions, unavailable external resources, or governance blockers precisely. Never evade a gate by weakening checks or inventing a successful run.

## Task management

1. **Plan first:** For sustained multi-step work, maintain a checkable plan in `tasks/todo.md` (or an equivalent runtime-supported task record). Identify the base ref, task scope, success criteria, and verification commands. Create this file only when useful for an auditable handoff; avoid committing disposable session notes.
2. **Verify the plan:** Check the plan against current repository authority and available tools before implementation. Seek a user decision only when an actual authorization or ambiguity requires it.
3. **Track progress:** Mark completed and blocked tasks accurately as evidence accumulates. Distinguish planned work from verified results.
4. **Explain changes:** At significant milestones, summarize the behavior changed, the evidence observed, and the next dependency or blocker.
5. **Document results:** Before completion, record the final diff scope, verification, review state, limitations, and remaining work in the task record or PR description.
6. **Capture lessons:** Apply the evidence threshold above before persisting `tasks/lessons.md`; do not manufacture lessons merely to populate a file.

## Core principles

- **Simplicity first:** Make each change as simple as the verified requirements permit.
- **No laziness:** Find the root cause; avoid temporary patches when a durable remedy is warranted and authorized.
- **Minimal impact:** Modify only necessary surfaces, preserve existing content and provenance, and avoid introducing defects.
- **Honest completion:** Stop at verified completion or an explicit external blocker; never substitute a plan, task checkbox, or confident statement for observed results.
