# Local Qwen coding-repair instruction experiment (Research v0.1)

> Historical registration retained. The original preflight failed with zero model responses; no scored 60-run result exists for this condition. The live entry point is retired. See [post-execution validation and finding dispositions](LOCAL-QWEN-VALIDATION-V0.2.md).

This research isolates the pre- and post-PR #602 development instructions across the same 30 authored synthetic Python repair tasks. No provider key is needed: a public Qwen2.5-Coder 1.5B model is downloaded once per GitHub Actions job and invoked at 127.0.0.1 through Ollama. Network egress to a paid/credentialed model API is not used.

The fixed control commit is 38e6c8e8b3b1f0a7c75795c9eac8c1c6189cf7ab. The treatment revision is dc290674b755977378d6170a0128c1540f0a2b6a. The only treatment difference is which instructions are placed into the model prompt. Model digest, generation settings, task input and public examples, same task group, and grader are identical. Half the tasks are assigned control-first. The model never sees hidden examples or the reference oracle.

All generated code is tested inside a Docker container with no network, dropped capabilities and read-only bind mount. Each observation retains model output, submitted solution, grader transcript and per-file hashes. Any incomplete inference or unexecuted grader invalidates the estimate rather than becoming a coded failure.

**Limited claim:** This tests one-shot instruction-conditioned code repair by a small local model, NOT autonomous Codex or Claude workflow effectiveness, nor the historical FAR-PR tasks. Even a complete 60-call sample cannot establish the latter. These results remain Research only.

For offline preflight: python -m unittest tests.test_workflow_efficacy_internal_fixtures tests.test_workflow_efficacy_local_ollama tests.test_workflow_efficacy_local_analysis -v

For experiment contract: python -m tools.workflow_efficacy_local_ollama contract

Historical pair command (now fails closed): `python -m tools.workflow_efficacy_local_ollama run-pair --index 0 --output out`. A newly registered successor with a separate identity and output location is required for any new live study.

For aggregation: python -m tools.workflow_efficacy_local_analysis --root merged-pair-results --out report.json


## CPU-feasible scope amendment before scored trials

The initial excluded full-instructions preflight generated zero model responses: both arms timed out at 300 seconds (artifacts from run 41529850758), with Qwen model digest d7372fd828518a4d38b1eb196c673c31a85f2ed302b3d1e406c4c2d1b64a0668. Before any scored trials, the prompt was narrowed to *exact, unmodified canonical sections*: Rules for getting work done; Completion standard; and, in the treatment only, Workflow orchestration plus the complete newly added orchestration guide. This is explicitly a **subset-specific instruction efficacy** test rather than an evaluation of the full AGENTS.md content, general coding agents, or FAR reasoning correctness. Context was reduced to 4096, output cap 320 tokens, CPU thread allocation four. All arms and tasks use these identical frozen settings. No result from the earlier failed preflight enters the study.

## Prospective CPU-feasible treatment definition (before scored runs)

The first excluded full-context smoke (GitHub run 41529850758) yielded no response in either arm: both requests timed out at 300 seconds. The model digest was identical. The new treatment uses exact, verbatim canonical sections of AGENTS.md: Rules for getting work done and Completion standard for both arms; Workflow orchestration and the complete new guide for the treatment. This reduces input size without paraphrasing. The fixed model options are now 4096 context tokens, 320 output tokens, four CPU threads, seed 602, and temperature zero. These adjustments were made before any scored model runs. This tests a focused instruction subset, not the full FAR development-agent workflow or its commercial reliability.
