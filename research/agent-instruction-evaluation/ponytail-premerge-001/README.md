# FAR-PONYTAIL-PREMERGE-001 — Preregistered instruction screen

**Status:** Research — protocol and corpus prepared; **zero agent executions observed**. This work is linked to [PR #632](https://github.com/n0tf0und0ut/Project-FAR/pull/632), which proposes a small change to `AGENTS.md`. No benchmark result, performance advantage, scientific status promotion, or merge authorization is claimed.

## Question and comparison

Do three Ponytail-inspired paragraphs in FAR's root `AGENTS.md` introduce a material correctness, security, integration, or governance regression under a bounded coding-agent screen?

Both conditions use **the same ten authored tasks and runtime**. The only intended intervention is the root instruction file:

- Control: Git commit `05b8adf3dac9493d229b682f0a620e0a14925a8e`, `AGENTS.md` Git blob `7d2ddee5150ab907818e43f43d8c4398f7570f34`.
- Treatment: Git commit `4ef6c39a3b779365bbf15975b4fe80807a76e69a`, `AGENTS.md` Git blob `ce0c8b22e1555707d576037fd4840cca4a6f8f26`.

Each candidate workspace is assembled from the exact same authored fixture files, with only the `AGENTS.md` bytes switched. Control and treatment instructions are resolved from immutable Git commit objects and their Git blob identity is rechecked. The protocol (`protocol.json`), ten tasks with six independently scored examples each (`tasks.json`), and deterministic balanced 40-slot sequence (`schedule.json`) must remain unchanged after exposure. Changes require a separately identified successor protocol, not amendments to observed outcomes.

## Design and interpretation

Ten tasks × two instruction conditions × two repetitions = **40 execution slots**. Categories include caller integration, money arithmetic, path safety, JSON handling, pagination, reuse, append-only records, protected merge-gate behavior, frozen evidence and configuration consistency. Each workspace contains task source, its public requirement and **only the first two examples**. The four remaining test inputs and all expected hidden outputs remain in the trusted controller, never the agent's task workspace.

The planned execution environment is Codex using the explicitly pinned `gpt-6` model, a fresh workspace for every slot, bounded runtime, and no access to other tasks, grader files, memory, or arbitrary task-network tools. Actual backend identity, instruction exposure and isolation must be recorded before a performance claim. If that cannot be confirmed, the outcome remains `NOT_EXECUTED` or `INVALID_EVIDENCE` instead of silently substituting a different model. Provider API transport may be necessary even when task-network access is disabled.

Each candidate is tested by running its actual `transform(payload)` in the same isolated, network-disabled Docker grader mechanism used by FAR's existing scripted-repair harness. A trusted host compares strict JSON outputs against six authored expected results. The candidate cannot edit the host-side expected answers. Wrong values, missing completions, unauthorized file edits, changed instruction bytes, incomplete/invalid transcripts and infrastructure failures are separate outcomes. No candidate may change frozen evidence or governance to obtain success.

The prospective screen passes only if **all 40 execution receipts are complete**, each treatment security/governance/integrity slot succeeds, and no other treatment run fails where its paired control succeeds. A passing screen is **not** a statistical superiority result, a complete security assessment, or an alternative to PR #632's independent exact-head review and protected GitHub merge requirements. Both paired differences and absolute success counts must be reported. A failed task stays in the denominator; selective reruns are prohibited.

## Commands

From a Git checkout containing both pinned instruction commits:

```bash
python -m unittest tests.test_agent_instruction_premerge
python tools/agent_instruction_premerge.py validate
python tools/agent_instruction_premerge.py schedule
python tools/agent_instruction_premerge.py prepare --output /path/outside/the/repo/far-ponytail-premerge-001
```

`prepare` constructs all 40 isolated workspaces. It fails before writing anything when either pinned instruction Git object is absent. Each workspace's `README.md` contains the task prompt and two public examples. `schedule.json` fixes the randomized-but-balanced execution order. The output root contains an `evidence/` directory kept outside agent workspaces.

On a secured operator machine with the intended model, Docker and a suitable Codex CLI installed, execute each registered slot once using the existing staged workspace and a command that explicitly selects the pinned model:

```bash
python tools/agent_instruction_premerge.py run-slot \
  --output /path/outside/the/repo/far-ponytail-premerge-001 \
  --slot CALLERS-01-R2-control \
  --agent-command 'codex exec --json --model gpt-6 --sandbox workspace-write --ephemeral --ignore-user-config --ignore-rules "Read README.md and AGENTS.md, then make the code changes needed to satisfy the task."'
```

The command shown is an **operator execution example**, not evidence this environment has the CLI, model, credentials, Docker, or a proven agent sandbox. Configure the agent's tool restrictions and record model/provider identity and environment provenance before any actual run. Do not execute a different model under this protocol. Complete the exact 40-slot schedule without outcome-driven repeats. The runner retains raw stdout and submitted sources, then grades against the hidden cases in Docker; it will not manufacture test results when the grader is unavailable.

After all runs, execute:

```bash
python tools/agent_instruction_premerge.py analyze --output /path/outside/the/repo/far-ponytail-premerge-001
```

The analyzer fails closed on missing slots or malformed evidence and recomputes pass/fail classifications from retained grader outputs and the hidden oracle data. This audit is still internally authored; the CLI-reported model identity and instruction ingestion are not cryptographic attestations. No output from an untrusted agent is a substitute for actual independent validation.

## Dependency and authority limits

This bounded Research study adds no requirement to protected branch rules and does not modify PR #632. It borrows the established output-capture/grader execution helpers from `tools/workflow_efficacy_free_agent.py`. It does not overwrite, pool, or reinterpret any prior FAR experiment, including the existing 60-run scripted-repair study or the 72/72 bounded tool-agent study. The independent Codex review and protected App gate for #632 remain obligatory. External/representative performance superiority is not established even if the internal screen passes.

## Exact-head repair and evidence hardening before model exposure

The first independent PR review found concrete fail-open mechanisms in the initially committed evaluator. The repair preserves the original preregistered `protocol.json`, task corpus and schedule and changes only *operational runner, tests and documentation* before any model exposures. No scored run, favorable resampling, or outcome-driven model tuning has occurred. The prepared manifest now binds SHA-256 of the protocol, schedule, corpus, runner and reused grader helper; changing these after `prepare` prevents later analysis rather than silently changing an acceptance decision.

The repaired runner compares every source against controller-owned initial hashes (not candidate Git HEAD), retains unauthorized extra files, rejects modifications to `AGENTS.md` and `README.md`, and grades a captured immutable source snapshot. A trusted entrypoint independently checks that `transform` did not mutate the input. Every attempt writes a pre-exposure receipt; interrupted/integrity-violating attempts are not reclassified as never executed. Run order is enforced and hash-chained. Grader cleanup errors preserve the pre-cleanup receipt. The host captures both agent stdout and stderr with explicit byte and time limits and kills the private process group before capturing submitted files. The analyzer recomputes outcomes from retained raw grader output, source snapshots, verified Codex CLI JSON event lifecycle and runtime identity receipts.

`codex exec --json` must produce a single `thread.started`, a single `turn.started` and a final `turn.completed` with nonzero token usage. The invocation is restricted to the exact model-argument/sandbox/config command shown above, and the actual executable path, SHA-256 and `codex --version` response are retained. This is **host-verified command and trace provenance**, not a cryptographically signed provider proof of the effective backend model. The operator must also independently establish and record CLI authentication, backend model availability, network/tool restrictions, and the isolation boundary. A Codex workspace-write sandbox on a host that also exposes the hidden task corpus may not be sufficient to establish blind evaluation; running it that way must not be represented as isolated or independently graded. A separate isolated agent host or container seeing only a single task workspace, and a trusted grader holding the oracles, is required for a defensible evaluation.

**Execution boundary:** The connected GitHub reviewer is not a substitute for 40 model executions. This ChatGPT session does not have an authenticated Codex CLI, Docker grader and verified provider/model configuration. The campaign's status remains `PREREGISTERED_NOT_EXECUTED`; structural tests alone cannot satisfy the screen. PR #632 may only merge after its separately required protected review and authorization process. A pre-merge screen result must not be asserted while actual execution and isolation are unverified.
