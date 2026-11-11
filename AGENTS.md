# Project FAR — OpenAI Agent Instructions

Applies to Codex and ChatGPT Chat/Work work on `n0tf0und0ut/Project-FAR`, including read-only work. Claude follows `CLAUDE.md` separately. Higher-priority platform instructions and actual permissions prevail.

## Fresh authority

- Codex reads applicable checkout `AGENTS.md` instructions. ChatGPT Chat/Work must fetch and read the **complete current root `AGENTS.md` from GitHub `main` before substantive FAR work**. Prior chats, summaries and cached copies are not substitutes. If access fails, report that explicitly; never claim the file was read. When working on a branch with changed agent instructions, inspect that version too. Recheck after material changes or context loss. See [ChatGPT Project bootstrap](docs/maintenance/agent-workflow-orchestration.md#chatgpt-chat-and-work-bootstrap).
- Resolve state-sensitive facts from current default-branch sources. Use [README](README.md), [project status](docs/project-status.md), and [canonical map](docs/CANONICAL_MAP.md) **as task-relevant entry points**; do not load all three in full unconditionally. Read the specific authoritative policy, code, theory, status or evidence needed before deciding. For broad repository or theory-state assessments, inspect all three.
- All work must comply with the [Research Execution Charter](docs/governance/research-execution-charter.md). Determine each source's authority, status, scope, provenance and dependencies. Repository presence, memories, generated outputs and archives do not confer acceptance. If current authoritative sources conflict, stop the affected inference and report the conflict. Do not bypass governed discovery or modify frozen evidence.

## Route by task

- **Implementation or maintenance:** Trace affected entry points, inputs, state, outputs, callers, tests, schemas, configuration and downstream consumers, including trust boundaries and failure modes. Search and reuse existing code/tools first, then native or installed capabilities, before writing new code. Keep changes task-scoped and preserve public contracts, provenance and data integrity. Run defect-detecting tests, inspect the final diff and verify resulting behavior.
- **PR or code review:** Follow [PR Review Convergence](docs/governance/pr-review-convergence.md). Bind assessment to current head, merge base, diff, findings and checks. Prioritize reproducible correctness, security, data loss, scaling and regression failures; distinguish required fixes from optional cleanup. Repair underlying defects, verify regressions, and do not re-request review on an unchanged head without new grounds. Independent substantive review, exact-head assurance, required checks and protected merge authorization remain separate.
- **Research or scientific claims:** Check current canonical theory, evidence, counterevidence, limitations and governing lifecycle. Preregister/freeze inputs when required; preserve negative results. Never promote hypotheses, bounded observations, internal agreement, software verification or formalization into broader proof, external independence, novelty or commercial value.
- **Multi-step work:** Use the [workflow orchestration guide](docs/maintenance/agent-workflow-orchestration.md) for planning, task continuity and verification as operational aids, never as authority overriding governance.

## Authorization and completion

Carry out authorized reversible inspection, fixes and verification without redundant permission requests. Ask when a genuinely missing decision or authorization blocks an irreversible external action. Never bypass branch protection, merge gates or required reviews; do not merge, force-push, deploy, publish, rewrite shared history or contact third parties without authorization. Never fabricate tests, reviews, tool results, signatures or success.

Complete authorized work through verification; make only necessary changes. Before reporting completion, inspect the final diff and current repository state; distinguish verified results from unresolved external blockers. Do not claim merged status until protected main and PR state confirm it. Report exact blockers and limits when completion is prevented.
