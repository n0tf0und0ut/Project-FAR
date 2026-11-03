# Local scripted-repair pilot v0.4 — completed result

**Status: Research. Execution: complete; 60/60 valid model-backed observations.**

The FAR instruction treatment did not demonstrate improvement in this pilot. It solved **10/30** authored tasks, compared with **11/30** for control, an observed treatment-minus-control difference of **−3.33 percentage points**. This is one realization of one-shot synthetic repair with Qwen2.5-Coder 1.5B; it is not an autonomous coding-agent, general-reasoning, historical-FAR-development or customer-value result.

| Measure | Control | Treatment |
| --- | ---: | ---: |
| Complete evaluations | 30 | 30 |
| Repairs passing all six comparisons | 11 | 10 |
| Success fraction | 36.7% | 33.3% |
| Mean generation-only seconds | 42.050 | 68.813 |
| Mean input tokens | 2525.97 | 3946.97 |
| Mean output tokens | 59.23 | 57.30 |

Nine pairs both succeeded, eighteen both failed, one succeeded only under treatment and two succeeded only under control. Treatment used 1,421 more input tokens and 26.7622 more generation seconds on average. Generation timing excludes installation, setup, grading and provisioning, and a first request can include local model loading. Zero external API charges do not mean zero compute cost.

## Reconstructable evidence

- Implementation [PR #605](https://github.com/n0tf0und0ut/Project-FAR/pull/605), reviewed head `72e026c71d3fd449c065aa0c0eeab2ff76dfb113`, merged normally as `a750c5523183f64a20ff644846c4fcd91c887824`; the merged tree equals the reviewed tree.
- The [scored campaign](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41556392256) executed once from that exact merge. All thirty pair jobs and the aggregate succeeded. The sixty raw observations identify that campaign and attempt 1; every registered slot occurs exactly once.
- The [protected-main access probe](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41556211522) succeeded before scored launch. Every access/preflight request and every synthetic unit fixture is excluded from the primary sixty observations.
- The [machine-readable result record](result/campaign-41556392256.json) retains the complete frozen analysis, thirty paired outcomes, source identities, all thirty-one original artifact IDs/digests, and explicit nonclaims.
- Original [aggregate artifact 13195228979](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41556392256/artifacts/13195228979), ZIP SHA-256 `10362d05b405f8e21f3bb0e3646134cd72a949bcafead5e9ef397068a9f82815`.
- All original artifact ZIP digests were verified. The frozen analyzer was replayed locally from the exact executed commit and matched the hosted report with sixty observed records, sixty unique slots and zero errors.
- The project deliverable contains a 268-file replay bundle: all sixty raw model replies, submitted sources, grading traces, frozen corpus, immutable source/instruction manifest, original artifact ZIPs, per-task/family tables and release metadata. Its SHA-256 is `93ac266504d82c1b2369bf7e70bb424149296c47cea9dc8f88bdd38bc06344fc`. Actions artifacts have thirty-day retention; later raw replay requires the retained bundle, not this summary alone. No external replication has been established.

The [prelaunch protocol](https://github.com/n0tf0und0ut/Project-FAR/blob/a750c5523183f64a20ff644846c4fcd91c887824/research/workflow-efficacy/KEYLESS-PILOT-V0.2.md) and both instruction revisions remain preserved at their original identities. This result record does not rewrite their frozen bytes or pool this sample with the [unexecuted historical-PR agent study](README.md).

## Controls and validation

The corpus has ten authored algorithm families with three variants each, two public and four hidden comparisons per variant. Fifteen pairs were control-first and fifteen treatment-first. Each condition used one direct localhost Ollama request with the same full model manifest identity, seed, generation options and budgets. Candidate processes received source and one input; expected answers were compared outside the candidate process. Provider/source/grade artifacts, counters, hashes, source identity and registered order were reconciled before analysis.

The full model manifest SHA-256 is `d7372fd828518a4d38b1eb196c673c31a85f2ed302b3d1e406c4c2d1b64a0668`; the corpus SHA-256 is `53e04a8c93e86b48f7413e91e9d2ec5768159fdafa9a884c2f5b4bf704da8ce3`.

Final source validation passed fifty targeted tests, 2,704 canonical tests, all 137 repository-health checks, the remaining Makefile checks and twenty theory-dependency tests. Exact-head automated review, native review convergence, the dedicated signing App and both signed assurance jobs passed before protected merge. A traced check caught an offline test accidentally invoking Docker; its mock boundary was corrected and a process-launch prohibition reproduced and prevented the defect without relaxing the dependency policy.

## Interpretation limits

- The bundled treatment also lengthens context. This design does not isolate a FAR-specific reasoning mechanism from instruction content, verbosity or compute differences.
- There is one small model and one generation per condition, without a frontier-model comparator, human/customer outcomes, independent investigators or a probability sample of software work. Thirty related variants are not thirty independent real-world tasks.
- Sign-test and task-bootstrap outputs in the machine record are exploratory diagnostics. They do not establish population significance, equivalence or absence of a practically important effect. The numerical sign-test value is 1.0; the task-bootstrap interval is approximately −13.33 to +6.67 percentage points, subject to those limits.
- Separate excluded hosted preflights returned different FWE-001 treatment outcomes despite fixed settings and unchanged runtime/model/task bytes. Cross-run or cross-hardware determinism is not established; this single scored realization cannot estimate that variability.
- The original tool-using preflight failed and the protocol was prospectively revised to one-shot repair before scored execution. The historical-PR study, autonomous-agent efficacy, general reasoning reliability, commercial superiority and customer value remain unestablished by this pilot.

No core theory, accepted claim or scientific-status register is promoted by this Research record.
