# Codex adapters for FAR specialist skills

Status: operational routing metadata, subject to exact-checkout validation. These adapters do not create FAR theory, research authority, an approved GitHub review, or external isolation.

## Single source of truth

The 14 original specialist definitions remain under `.claude/skills/far-*/SKILL.md`. The Codex discoverable skill entries in `.agents/skills/far-*/SKILL.md` and custom agent profiles in `.codex/agents/far_*.toml` **only reference** those files. Do not copy the specialist procedures into the adapters. Edit the original skill when a governed procedure legitimately changes, then synchronize adapter metadata with the original name and description. The Cloudflare vendor skill is separate and unchanged.

Codex uses `AGENTS.md` for repository instructions, `.agents/skills/` for skill discovery, and `.codex/agents/` for explicitly selectable delegated agent types. An agent profile's `developer_instructions` directs it to read the **entire** specialist source in the checkout before acting; a metadata-only wrapper is not a substitute for reading it. No model, provider, credential, approval policy, or sandbox override is specified here, so those remain governed by the parent runtime.

## Use

From a Codex CLI, IDE, or desktop checkout of Project FAR, start a new session after this PR merges. Invoke a specialist skill explicitly, e.g. `$far-counterexample-hunter`, or ask the parent Codex agent to delegate a bounded research task to the custom subagent `far_counterexample_hunter`. For independent research tasks, assign separate scopes and prohibit overlapping writes; collect typed findings, reconcile contradictions, and separately perform required PR reviews or research acceptance. A fresh source fetch, suitable sandbox, and actual subagent tools are required for any claim that those operations ran.

For a source-focused initial test, ask Codex to open `AGENTS.md`, delegate a bounded non-mutating question to `far_canonical_source_resolver` and `far_contradiction_detector`, and identify their source skill paths, findings, and limits. This is a runtime smoke test, not external independence. Subagents inherit the parent runtime's permissions and sandbox.

## Reproducible checks

```sh
python tools/check_codex_far_specialists.py
python -m unittest tests.test_codex_far_specialists -v
```

The separate read-only `Codex FAR Specialist Adapter Contract` workflow runs both commands on relevant PRs and by manual dispatch; protected Repository Health remains unchanged and hash-locked. The validator compares all 14 source names and descriptions with both adapter surfaces, validates TOML, rejects missing/stale/altered adapters and symlinked sources, and fails on metadata drift. This checks wiring, not model invocation, live task quality, or actual Codex runtime discovery.

## Boundaries

`tools/subagent_orchestration.py` remains FAR's provider-neutral, typed orchestration layer. Native Codex subagent sessions are a distinct runtime; these profiles do **not** automatically satisfy that layer's isolation attestations or plug into the experimental software factory. The isolated factory coding-worker adapter and GitHub delivery evidence collector remain unimplemented. Do not claim end-to-end autonomous delivery from this configuration alone.
