# Prospective keyless internal coding-agent pilot v0.2

Status: Research / NOT EXECUTED. This is an independently scoped synthetic pilot. It is **not** the immutable 30 historical-FAR-PR candidate study from PR #603, is not SWE-agent v3, and carries no external/independent claim.

## Frozen design before first request

- 30 synthetic task identities FWE-001 through FWE-030: 10 different algorithm categories with 3 behavior variants each. A deterministic generator provides 2 public tests and 4 hidden tests per task; the hidden tests never enter the agent workspace.
- Two arms: exact historical pre-#602 Codex AGENTS.md at SHA 38e6c8e8b3b1f0a7c75795c9eac8c1c6189cf7ab, or post-#602 AGENTS.md plus shared workflow guide at SHA dc290674b755977378d6170a0128c1540f0a2b6a.
- The same OpenCode CLI 1.19.3 and free-model alias opencode/big-pickle, same per-run tool configuration, time ceiling 240 seconds, agent build 10-step ceiling, code workspace structure, task prompts, and isolated HOME/XDG contexts. 15 cases control-first and 15 treatment-first, deterministically assigned by task SHA ordering.
- No external API key or payment method is supplied. The repository owner triggers an excluded provider smoke via the exact comment /far-workflow-free-probe on merged PR #603, then the 60-run campaign via /far-workflow-free-60 on the same PR. The workflow exists only on protected main after substantive review and required checks, and checks immutable owner user ID 344016609.
- Task baselines are not derived from FAR commits; they are independently authored toy code problems. Therefore this pilot cannot establish effectiveness on real FAR repository work.
- Per-task evidence contains completed model-step counts, input/output tokens reported by OpenCode, declared $0 cost, source hashes, instruction hashes, grader evidence hashes, elapsed time and outcome. No evidence means no scored completion. Unauthorized edits to non-solution files disqualify success. Hidden tests are executed in a network-disabled Docker grader outside the model workspace.
- Free provider identity is an alias, not an immutable model build. Drift remains a limitation; no causal claim requiring a pinned model snapshot follows even from 60 successful calls. Rate limits/retirement could prevent a full sample and must be reported, never replaced with fabricated runs or a paid model.
- Source and analysis code are pinned by the reviewed merge commit at launch. The exact launched commit and GitHub Action run IDs must be preserved in the final report; the result artifacts are not merged back into theory registers.

## Pre-launch validation

Run in the exact source checkout:
- python -m unittest tests.test_workflow_efficacy_internal_fixtures tests.test_workflow_efficacy_free_agent tests.test_workflow_efficacy_free_agent_analysis -v
- python tools/workflow_efficacy_free_agent.py contract
- python tools/workflow_efficacy_free_agent.py schedule

Only the model-execution GitHub Actions workflow may generate actual observations. The unit tests and the provider smoke are not part of the 60 paired agent runs. An empty/partial report must remain INCOMPLETE_OR_INVALID.
