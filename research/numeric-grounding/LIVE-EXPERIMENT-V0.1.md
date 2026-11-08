# Frozen prospective numeric-source grounding pilot v0.1

**Status: Research — registered before scored execution.** No model result is incorporated in this preregistration.

## Question and exact hypothesis

For a pinned local Qwen2.5-Coder 1.5B model responding to 16 authored questions about FAR's retained v0.3 execution, does a model-selected, replay-grounded metric tool reduce incorrect *published numerical outputs* versus a direct JSON-answer baseline? How much latency, extra token use, and legitimate-answer loss does the tool introduce?

The actual intervention is **tool availability plus strict numerical release enforcement**, not changes to model weights, training, external retrieval, or the FAR core verifier. A tool refusal is counted as an abstention, never a correct numerical answer. The two prompts differ because one grants a tool, which is part of the intervention.

## Original source, prospective freeze, and evaluation scope

- The complete frozen specification is [protocol-live-v0.1.json](protocol-live-v0.1.json), introduced **before any new model call** at commit `4956893084d49fe42bde275105cf58a0bb240008`.
- Authoritative recorded facts: original v0.3 tool-agent 72/72 scored executions and excluded preflight. The [source replay adapter](source_replay.py) pins the protocol and archive digests and reconstructs every original action/grade.
- Eight answerable authored question variants target the *same* registered v0.3 success percentage, `100.0000`. Eight other variants ask questions outside the recorded domain and require `UNKNOWN`. These are **not 16 independent source truths**, and there is no held-out real-world source dataset.
- One pretrained model: Qwen2.5-Coder 1.5B, original verified Ollama digest `d7372fd828518a4d38b1eb196c673c31a85f2ed302b3d1e406c4c2d1b64a0668`; existing pinned Ollama v0.34.0 bootstrap. Temperature zero, seed zero, 128 generated-token cap, 8192 context and 120-second request timeout.
- Two isolated conditions per case, counterbalanced by task index. The control model may answer the numerical question or explicitly abstain. The treatment model may request the registered metric tool, receive the pinned replay result, then provide a final answer. A final numeric reply that does not match the trusted tool output cannot be released.
- The complete original author-generated question set, known source, and scoring rules are visible to the coordinator before execution. No human/external adjudicator, blinded task collection, open-world domain coverage, or independent trusted execution is asserted.
- Exactly 32 condition attempts are registered (16 paired cases), with at most two model calls per condition; every malformed output, refusal, timeout, infrastructure error, missing case and nonconforming action must remain visible. No favorable rerun or selective discard is allowed.

## Scoring and stop rules

The [live runner and deterministic analyzer](live_pilot.py) record exact requests, provider JSON, byte hashes, model identity, model token counts, elapsed time, attempted actions, verifier receipts, final allowed outputs, and the run commit. The trusted analyzer reconstructs the prompts and release decisions and rejects missing/duplicate slots or modified provider bytes. Raw evidence is retained from the GitHub Action regardless of success; no outcome may be imputed from a failed model setup.

Primary outcome: per-arm count of published incorrect numeric values across all 16 registered cases. Secondary: correct numeric outputs, legitimate abstentions on unsupported questions, unnecessary abstentions on supported questions, invalid/malformed replies, model calls, reported tokens, and generation latency. The exploratory positive-signal gate requires **at least two fewer wrong numeric releases without more than two additional unnecessary abstentions**. No significance or population-confidence claim follows from the gate.

A treatment consisting of a strict output filter may suppress mistakes mechanically. Even an observed advantage therefore cannot establish improved internal reasoning, novel mathematics, or a general agent-reliability benefit. It establishes at most the bounded output-gateway effect under the exact tested agent, authored prompts, metric catalog and source.

## Commands and execution boundary

Before running any model:

```sh
python -m unittest tests.test_numeric_live_pilot tests.test_numeric_grounding_integration -v
python research/numeric-grounding/live_pilot.py validate
```

The gated [GitHub Actions workflow](../../.github/workflows/numeric-grounding-live-v01.yml) is launchable only by a dedicated research-branch commit marked `[NUMERIC-GUARD-LAUNCH]`. It runs the existing pinned model-bootstrap script, writes each model/arm attempt once, and replays the result after the full registered sequence. Provider setup failures remain failed/incomplete observations rather than negative model scores.

An observed result, if obtained, must be published separately with the immutable run ID, exact execution commit, original raw evidence, verified counts and full limitations. The protocol and experiment source must not be rewritten to improve observed outcomes.
