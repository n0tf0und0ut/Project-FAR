# FAR-RAW-RESPONSE-FORENSICS-001 — Instrument/mechanism mismatch

**Status: Research; post-hoc analysis of immutable original traces.** No new model execution, no replacement of frozen evidence, and no accepted theory or efficacy promotion.

## Exact evidence and question

What actually changed when FAR-bundled instructions were added to the 30-task scripted-repair pilot, and which underlying agent capabilities did the intervention exercise?

Original execution: Actions [run 41556392256](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41556392256); frozen source commit `a750c5523183f64a20ff644846c4fcd91c887824`; original paired-record Git blob `90b3a56bb43d772a9e891766a578a93e73928aa8`; Qwen2.5-Coder 1.5B, digest `d7372fd828518a4d38b1eb196c673c31a85f2ed302b3d1e406c4c2d1b64a0668`. The original grader and 31 historical artifact SHA-256 values were independently replayed on [PR #672's green exact-head original-trace gate](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/43338949422/job/131602146173).

**Post-hoc inspection** examined all 60 original raw `agent-events.ndjson` model responses, 60 actual `submitted-solution.py` files, 60 `grader-trace.txt` records (360 individual test comparisons), and all 30 paired metadata records. Every read file's SHA-256 was matched against its originally recorded digest before using it. No outcome substitution, selective rerun, or inferred model call was performed.

## Direct discovery

| Exact fixed-corpus result | Observation |
| --- | ---: |
| Byte-identical **model-generated response text** across two arms | **20 / 30** |
| Byte-identical submitted solution source | **20 / 30** |
| Identical six-component public/hidden grade vector | **26 / 30** |
| Treatment slower than control | **30 / 30** |
| Full-task success, control vs treatment | **11 / 30 vs 10 / 30** |
| Public test comparisons passed, control vs treatment | 29/60 vs 27/60 |
| Hidden test comparisons passed, control vs treatment | **77/120 vs 77/120** |
| New FAR-only task success | FWE-014 |
| Lost FAR task successes | FWE-002, FWE-015 |
| Other change in test vector without changing failure verdict | FWE-022 |
| Input tokens, treatment minus control | **+1,421 in every task** |
| Mean additional total provider-request time | **+26.7622 seconds** |
| Mean additional reported prompt-evaluation time | **+26.345715267 seconds** |
| Mean additional response decoding/evaluation time | +0.4091681 seconds |
| Mean excess time in the twenty **byte-identical** response pairs | **+25.7292 seconds** |
| Treatment slower with no worse control success outcome | **29 / 30** |

`prompt_eval_duration` accounts arithmetically for **98.44%** of the observed mean request-time difference, with `eval_duration` accounting for approximately 1.53%. This is a decomposition of recorded provider telemetry **not a causal mediation estimate**. Prompt caching favored control in 15 trials and treatment in 15 trials; the mean cached-token difference was zero, not proof of a fully standardized model/hardware runtime. The mean generated-output-token difference was -1.9333, so the added time cannot be explained by writing substantially more output.

Six additional tasks produced different Python files yet the *same outcomes on all six tests*. Four changed their grade vectors; only three changed the all-tests-pass outcome. The partial-outcome exception FWE-022 remained a failure under both arms.

## Construct validity: the target mechanism was absent

Inspect `tools/workflow_efficacy_free_agent.py` at the **frozen execution commit**, especially `local_patch_request`. It invokes a **single** parameterized `api/chat` generation with two messages, no tool API, no model-visible checker output, no iterative repair, no active agent planner and no actual subagents. The treatment was the earlier `AGENTS.md` plus `docs/maintenance/agent-workflow-orchestration.md` at `dc290674b755977378d6170a0128c1540f0a2b6a`; the latter asks for tool-enabled planning, root-cause verification and subagent work that **could not be executed in this one-shot request**. The trusted grader ran only *after* the one response and did not feed back into the agent.

Thus the tested intervention is **a longer governance/orchestration instruction bundle**. It does not turn on the FAR representation/semantic-loss verifier, real runtime provenance, feedback-driven verification or tool orchestration. This mismatch is already implicit in the experiment's originally declared scope; this post-hoc measurement makes its behavioral and time consequences explicit. It is **not a newly discovered grader correctness defect**.

The conditional theory of semantic sufficiency and the separate real SQLite bound are neither supported nor refuted as agent reliability claims by this intervention.

## Reproduction and falsification

A separate reproducible local research package contains `forensic.py`, `test_forensic.py`, the entire 30-pair JSON result, a report and SHA-256 file manifest. The original 31 untouched artifact ZIPs are retained in the separately supplied original archive at SHA-256 `f4b2d454a44f4e480b5d01dbc8c2caaec92b39737ba37086ee19ed49a1e0b9ac`. Local post-hoc checks: **9/9 PASS**, including deliberate raw-response, candidate-source, grader-trace, outcome, missing-record and malformed-JSON mutations; tests check 20 identical response pairs, 26 identical grade vectors, complete pair counts and timing decomposition. Do not treat local source checksum validation as an independent external I3 replication or a new model execution.

## Verdict and live obligation

**VERIFIED SCOPED FINDING: PROMPT OVERHEAD + EXPERIMENTAL MECHANISM MISMATCH.** At the original finite experimental scope, extra governance prompt processing imposed consistent cost; it left 20/30 generated responses unchanged, 26/30 grade vectors unchanged, and did not improve aggregate success. The study is **evidence against the benefit of this instruction-only treatment**, not evidence that execution of FAR's actual mechanisms worsens general-purpose agents.

A properly gated prospective trial of actual FAR tool/checker execution versus baseline, generic structured checking and component ablation is required to identify the distinctive causal contribution. The existing SWE-agent v3 study remains design-only and explicitly prohibits model runs until its independently frozen task identities, matched comparators, environment, oracles, safety gates and authorization are satisfied. Do not bypass it with an internally chosen one-shot replacement.

No modification to accepted Core, frozen evidence, existing success counts, original experiment protocol, or protected-main authorization follows from this Research note.
