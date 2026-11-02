# Prospective locally executed scripted-repair pilot v0.3

Status: Research / NOT EXECUTED. This is an independently scoped synthetic pilot. It is **not** the immutable 30 historical-FAR-PR candidate study from PR #603, is not SWE-agent v3, and carries no external/independent claim.

## Frozen design before first request

- 30 synthetic task identities FWE-001 through FWE-030: 10 different algorithm categories with 3 behavior variants each. A deterministic generator provides 2 public tests and 4 hidden tests per task; the hidden tests never enter the agent workspace.
- Two arms: exact historical pre-#602 Codex AGENTS.md at SHA 38e6c8e8b3b1f0a7c75795c9eac8c1c6189cf7ab, or post-#602 AGENTS.md plus shared workflow guide at SHA dc290674b755977378d6170a0128c1540f0a2b6a.
- The same OpenCode CLI 1.19.3 and locally hosted digest-checked open-weight model ollama/qwen2.5-coder:1.5b, same generation configuration, time ceiling 240 seconds, one-shot generation, code workspace structure, task prompts, and isolated HOME/XDG contexts. 15 cases control-first and 15 treatment-first, deterministically assigned by task SHA ordering.
- No external API key or payment method is supplied. The repository runs Ollama locally from a pinned release archive (SHA-256 verified), pulls a Q4_K_M 1.5B coding model, and verifies the published digest prefix `d7372fd82851`. This removes the earlier Gemini/OpenCode external inference authentication dependency. The repository owner triggers an excluded provider smoke via the exact comment /far-workflow-free-probe on merged PR #603, then the 60-run campaign via /far-workflow-free-60 on the same PR. The workflow exists only on protected main after substantive review and required checks, and checks immutable owner user ID 344016609.
- Task baselines are not derived from FAR commits; they are independently authored toy code problems. Therefore this pilot cannot establish effectiveness on real FAR repository work.
- Per-task evidence contains completed model-step counts, input/output tokens reported by OpenCode, declared $0 cost, source hashes, instruction hashes, grader evidence hashes, elapsed time and outcome. No evidence means no scored completion. Unauthorized edits to non-solution files disqualify success. Hidden tests are executed in a network-disabled Docker grader outside the model workspace.
- The local model digest and Ollama release are verified against pinned identities before every run. Even 60 successful observations would be internally authored toy-task evidence, not external FAR development efficacy. A hardware/runner failure must be reported, never replaced with fabricated observations.
- Source and analysis code are pinned by the reviewed merge commit at launch. The exact launched commit and GitHub Action run IDs must be preserved in the final report; the result artifacts are not merged back into theory registers.

## Pre-launch validation

Run in the exact source checkout:
- python -m unittest tests.test_workflow_efficacy_internal_fixtures tests.test_workflow_efficacy_free_agent tests.test_workflow_efficacy_free_agent_analysis -v
- python tools/workflow_efficacy_free_agent.py contract
- python tools/workflow_efficacy_free_agent.py schedule

Only the model-execution GitHub Actions workflow may generate actual observations. The unit tests and the provider smoke are not part of the 60 paired agent runs. An empty/partial report must remain INCOMPLETE_OR_INVALID.


## Prospective protocol revision before the scored 60-run sample

Original v0.2 tool-using OpenCode preflight exposed a model capability failure: control completed only an off-task getcwd response and made no source edit; treatment timed out without any completed model step. Those two excluded preflight runs are not scored. The v0.3 protocol replaces the tool-agent loop with exactly one direct local Ollama code-repair request per condition; generated source is parsed and independently graded. Task corpus and 15/15 counterbalanced task order are unchanged, but the estimand is now **instruction effects on one-shot scripted repair**, not autonomous tool-using coding-agent efficacy. These observations cannot answer the original historical-FAR-PR question, which remains unexecuted. No v0.3 scored model run existed before the merged trial launch.
