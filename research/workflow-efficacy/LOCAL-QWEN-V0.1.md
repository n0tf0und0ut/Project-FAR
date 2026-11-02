# Local Qwen coding-repair instruction experiment (Research v0.1)

This research isolates the pre- and post-PR #602 development instructions across the same 30 authored synthetic Python repair tasks. No provider key is needed: a public Qwen2.5-Coder 1.5B model is downloaded once per GitHub Actions job and invoked at 127.0.0.1 through Ollama. Network egress to a paid/credentialed model API is not used.

The fixed control commit is 38e6c8e8b3b1f0a7c75795c9eac8c1c6189cf7ab. The treatment revision is dc290674b755977378d6170a0128c1540f0a2b6a. The only treatment difference is which instructions are placed into the model prompt. Model digest, generation settings, task input and public examples, same task group, and grader are identical. Half the tasks are assigned control-first. The model never sees hidden examples or the reference oracle.

All generated code is tested inside a Docker container with no network, dropped capabilities and read-only bind mount. Each observation retains model output, submitted solution, grader transcript and per-file hashes. Any incomplete inference or unexecuted grader invalidates the estimate rather than becoming a coded failure.

**Limited claim:** This tests one-shot instruction-conditioned code repair by a small local model, NOT autonomous Codex or Claude workflow effectiveness, nor the historical FAR-PR tasks. Even a complete 60-call sample cannot establish the latter. These results remain Research only.

For offline preflight: python -m unittest tests.test_workflow_efficacy_internal_fixtures tests.test_workflow_efficacy_local_ollama tests.test_workflow_efficacy_local_analysis -v

For experiment contract: python -m tools.workflow_efficacy_local_ollama contract

For pair run after local model installation: python -m tools.workflow_efficacy_local_ollama run-pair --index 0 --output out

For aggregation: python -m tools.workflow_efficacy_local_analysis --root merged-pair-results --out report.json
