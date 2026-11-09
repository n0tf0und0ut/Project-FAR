# CPU experiment v0.2 — preserved failed preflight

Status: **Research / NOT EXECUTED / input projection insufficient**.

GitHub Actions run [41502297913](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41502297913), head `6853b92d2bee9f4c22f98eb06cb616103865ae44`, failed before model load at `test_all_case_specific_prompts_have_distinct_hashes`. Observed distinct projected prompts: **11 of 12**. Other tests failed downstream because the runner correctly refused the missing distinct-input prerequisite. There are no v0.2 model decisions, token counts, or performance estimates.

The collision was independently identified from the frozen source files:

- A01: `conformance/far-ir-2.0/valid-factorization.json`.
- A04: `conformance/far-ir-2.0/invalid-factorization.json`.

These two records share the exact `contract` and its case/representation/required-behavior descriptions and tables. They differ in the **submitted evidence decoder table**: A01 maps representation value 1 to `odd`; A04 maps representation value 1 to `even`. The latter is inconsistent with its frozen required behavior. V0.2 intentionally excluded `report` as a whole, so its model had no way to distinguish those otherwise identical inputs.

The experiment therefore found a **bounded information-loss collision**, not an agent error. Showing a model only the contract does not suffice to distinguish two different verification *submissions*. The successor v0.3 must provide the typed submitted witness evidence as untrusted input while excluding the already-adjudicated reported outcome. Retain the v0.2 preregistration unchanged; do not retroactively count the failed preflight or claim 12 unique model tasks.

This is a Research diagnostic only and does not reopen FAR Core or establish a novel representation theorem.
