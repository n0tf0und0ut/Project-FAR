# Workflow-orchestration instruction efficacy — internal experiment package v0.1

> **Scope update — November 2, 2026 (America/New_York):** This page describes the unexecuted historical-PR agent study v0.1. The separate [local scripted-repair pilot v0.4](KEYLESS-PILOT-RESULTS-V0.4.md) completed 60/60 verified observations: control 11/30, treatment 10/30. That synthetic one-shot result does not execute or establish efficacy for this historical-PR study. The v0.4 [prelaunch protocol](KEYLESS-PILOT-V0.2.md) is retained as frozen history; its NOT EXECUTED label records the prelaunch state, not the completed pilot's current status.

**Status: Research / NOT EXECUTED. No demonstrated improvement.** This is a study of the *agent development workflow*, not a FAR reasoning-engine benchmark or theory-acceptance exercise. Do not merge or pool with `FAR-SWE-V3-001`: that study has its own closed execution gate, different treatment, and external-task constraints.

## Observed facts at intake (2026-11-02 UTC)

- Protected main at baseline: `38e6c8e8b3b1f0a7c75795c9eac8c1c6189cf7ab`. PR #602 merged at `2026-11-02T14:13:01Z` to `dc290674b755977378d6170a0128c1540f0a2b6a`.
- Its four changed files were `AGENTS.md`, `CLAUDE.md`, `docs/README.md`, and the new `docs/maintenance/agent-workflow-orchestration.md`. No FAR runtime/logic code changed.
- The exact PR head reported 20 successful CI checks and two skipped checks; no failed check. This is evidence of integration, **not** of reduced defects or improved agent ability.
- In the October 20–November 2 historical cohort, 14 other PRs were opened, 8 merged, 4 remained open, and 2 closed without merge. Median creation-to-merge time among the 8 merged was approximately **87.97 minutes**. These incomparable tasks and governance delays are **not** a causal control arm.
- No PR was created after the new instructions merged when intake was measured. Post-treatment agent-task sample size: **zero**.

## Testable causal question

For one pinned model build and unchanged tools/configuration/budgets, do these exact post-#602 instructions improve independent verified task success relative to their exact pre-#602 counterparts?

**Conditions:** `control` loads `AGENTS.md` and `CLAUDE.md` from `38e6c8e8b3b1f0a7c75795c9eac8c1c6189cf7ab`; `treatment` loads them from `dc290674b755977378d6170a0128c1540f0a2b6a` plus the linked workflow guide. Both must use the same agent/model/provider version, temperature, tool policy, prompt shape, repository and source cutoff, time/token/cost ceilings, evaluator, and clean workspace. Instruction discovery must be verified: logging files accessed is necessary; assuming the agent read a link is insufficient. Model runs must be separate, with isolated memory and cache. No condition may access the historical answer patch or oracle.

The `protocol-v0.1.json` identifies **30 immutable historical PR candidates** selected deterministically (most recently created merged non-bot PRs targeting main, excluding explicit probes and the treatment PR), each with an original base SHA and candidate head SHA. This is a *candidate pool*, **not yet a frozen runnable task set**. Task prompts must be reconstructed from pre-fix issue evidence, independent scoring tests defined and frozen, and historical answer patches sealed from runners. Public historical PRs can leak solutions through training or retrieval. A FAR-internal historical replay is exploratory; it cannot establish general external software-engineering efficacy, even if all runs complete.

## Endpoint and execution gate

The current conversation runtime exposes repository reads/writes and CI status, **not two independently isolated same-model coding-agent invocations with token/cost accounting and a sealed evaluator**. The existing SWE-agent v3 runner explicitly forbids execution before its separate gate is satisfied. No agent calls were made, no pilot was conducted, and no 60-run result exists. The protocol deliberately records these missing inputs rather than inventing them.

Before execution, freeze: (1) full case bundles and 30 task prompts, (2) task acceptance tests and independent scoring oracle, (3) source/answer access barriers, (4) control/treatment instruction bytes and discovery log contract, (5) provider model snapshot, (6) tool/runtime/configuration fingerprints, (7) budgets/retry policy, (8) first-run assignment schedule, (9) identity-blinded evaluator and provider account, and (10) operator-approved cost ceiling and execution launch record. These are independent prerequisites. There is no auto-authorizing inference from this package.

## Analysis

The primary intention-to-treat outcome is independently verified successful completion without unintended regressions. A single failure, timeout, abstention, or budget exhaustion counts as unsuccessful, not excluded; a qualifying infrastructure outage must be reported and handled under a frozen condition-blind rule. Scoring must be done without revealing condition labels. Record elapsed time, model token usage, provider cost, review rework, and regression count per run, including operator labor where measurable.

The provisional analysis script `tools/workflow_efficacy_analysis.py` rejects an incomplete set of 60 runs, duplicate IDs, mismatched models/configs/bundles/adjudicators, missing provenance/isolation, and unverified outcomes. For valid pairs it reports treatment-minus-control success risk difference, paired bootstrap interval, exact two-sided sign test on discordant pairs, and mean deltas in time, tokens, cost, rework, and regressions. The bootstrap is illustrative for these 30 selected cases; it does not address correlated tasks, known-answer contamination, model drift, or external validity.

Run these *non-experimental* structural checks:

```bash
python tools/workflow_efficacy_analysis.py verify
python tools/workflow_efficacy_analysis.py schedule
python -m unittest tests.test_workflow_efficacy_analysis -v
```

When actual independently adjudicated records exist, call `python tools/workflow_efficacy_analysis.py analyze --runs <validated-jsonl>`; until then `NOT_ESTABLISHED` is mandatory. **The synthetic unit-test cases are arithmetic fixtures, not model runs or efficacy evidence.**

## Root-cause caveats

The earlier `AGENTS.md` and `CLAUDE.md` already required planning, investigation, testing, and learning. The treatment largely reorganizes and reinforces them. A null treatment effect would therefore be plausible. The 30 historical candidates are neither independent by topic nor guaranteed to reflect future development work; selection and shared validation machinery can correlate failures. A placebo-size instruction arm and external held-out tasks would be needed to separate instructional content from attention/verbosity and establish broader generality.

This record is Research only. It changes no FAR-CORE claim, schema, product capability, research authority, or historical experiment.
