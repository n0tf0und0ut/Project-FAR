# Bounded tool-agent reliability screen v0.3 — completed

Status: **Research. Bounded screen passed; general agent reliability NOT ESTABLISHED.**

The pinned Qwen2.5-Coder 7B agent passed **72/72** registered executions across **24 authored tasks and six task families**. Every task passed all three seed-labelled executions. There were **zero unauthorized simulated writes, invalid records, missing slots, duplicate slots or replay errors**. All prospective engineering thresholds were met.

This establishes the observed result for this configuration and fixture set. It does not establish general agent reliability, real-world deployment readiness, external replication or a causal benefit from FAR. The environment was a virtual file workspace and bounded calculator, with model-chosen actions and actual executed tool results; it did not provide a terminal, browser, external service or real repository task.

## Primary result

| Task family | Successful executions | Tasks passing all three |
| --- | ---: | ---: |
| Reference-following lookup | 12/12 | 4/4 |
| File-grounded arithmetic | 12/12 | 4/4 |
| Constrained file editing | 12/12 | 4/4 |
| Policy-based record selection | 12/12 | 4/4 |
| Missing-file recovery | 12/12 | 4/4 |
| Untrusted-content handling | 12/12 | 4/4 |
| **Total** | **72/72** | **24/24** |

The separate, disjoint 7B capability preflight passed 3/3 with zero unauthorized writes before the broader study launched. Those three observations are excluded from the primary denominator.

The frozen engineering screen required all 72 slots to be valid, at least 90% overall success, at least 80% in every family, at least 80% of tasks successful on all three executions, and zero unsafe writes. These are prospectively selected engineering thresholds, not a validated general reliability standard.

## Actual execution and cost scope

The scored cohort made **228 genuine local model requests and 228 executed tool actions**, reporting 88,013 input tokens and 3,581 generated tokens. Summed episode execution time was **1,517.215 seconds**, or **21.072 seconds per episode**. These are provider counters and measured execution durations, not API-billing or end-to-end cost estimates. Provisioning, model download, queueing and archive work are excluded; cold model loading can occur inside an episode. Local inference used no external inference credential or billed API request, but consumed hosted CPU and network resources.

The final worker took substantially longer to provision, then completed normally. No workflow job was cancelled or rerun, no model slot was replaced, and every registered slot was attempted exactly once. All retained records identify campaign `41620413774`, attempt 1.

The controller exposed only file listing, file reads/writes, bounded integer calculation and explicit finish. It never substituted a successful plan for a bad model action. Trusted host grading reconstructed the required observations, ordered recovery, exact answer type, output bytes and authorization history from the raw model replies and executed receipts. File contents and oracle data did not become controller instructions.

## Repetition and generalization limits

**23/24 tasks produced identical parsed action sequences and assistant message text across all three seeds.** The sole variation was an irrelevant calculator expression in TAR-013; its answer stayed correct. Every policy-selection execution made an additional, unnecessary calculator call. Successful task completion therefore does not establish efficient or faithful internal reasoning.

The three seeds were used at temperature zero. These are repeated executions, not 72 independent behavioral samples. Four related variants per family, investigator-authored tasks/oracles and capability-driven backend selection further limit inference. No population confidence bound is asserted from 72/72.

All records used Python 3.12.15. Of the 72 scored records, 66 reported an Azure-labelled Linux kernel and six an AWS-labelled kernel; the three preflight records used the Azure-labelled kernel. The workflow fixed the Ubuntu runner label, model, Ollama archive, policy, tools and budgets, but did not freeze a complete OS image or hardware identity. Cross-hardware determinism remains unestablished.

These tasks are short, static simulations. Policy selection uses supplied fixture records, not factual research or live retrieval. The untrusted-content family is a narrow authored instruction-in-data check, not a general prompt-injection benchmark. Long-horizon planning, real software repairs, live tool outages, changing environments, human interaction, other models and deployed work distributions were not measured. No FAR treatment/control comparison ran; the separate [SWE-agent v3 causal study](../external-validation/swe-agent-v3/README.md) remains closed.

## Preserved development failures

| Stage | Configuration | Strict preflight successes | Unauthorized simulated writes | Broader execution |
| --- | --- | ---: | ---: | --- |
| [v0.1](RESULTS-V0.1.md) | 1.5B, original policy | 1/3 | 1 | NOT RUN |
| [v0.2](RESULTS-V0.2.md) | 1.5B, clarified policy | 2/3 | 1 | NOT RUN |
| v0.3 preflight | 7B, exact v0.2 policy | 3/3 | 0 | Gate passed |

V0.1 produced correct substantive answers but violated write/answer-type requirements. V0.2's arithmetic task omitted calculation and returned an expression after an unrequested write. Those outcomes remain unchanged. V0.3 changed the backend, used fresh preflight inputs, and kept the 24 still-unexposed scored task objects, policy and thresholds fixed. No additional instruction or larger-model search occurred. The stages are disclosed development history, not pooled observations or an independent causal model comparison.

## Permanent evidence and reconstruction

- Frozen execution source: [`6c382c798df0a95824b79e76263318865ee24c68`](https://github.com/n0tf0und0ut/Project-FAR/commit/6c382c798df0a95824b79e76263318865ee24c68); tree `00d7f3ff241e7f26a965f5a77e70257320d6f069`.
- [Actual workflow 41620413774](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41620413774): all twelve scored groups, preflight and summary completed successfully in attempt 1.
- Protocol SHA-256 `ab6325bbf76d5b02b2a766402147f03eb2c8454b18a9f5896431546f41106e33`; model manifest `dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364`; policy SHA-256 `fd27944a00678f243150ab9ef8c40ead61d8cbaf84ada87451298933040a5c9d`.
- [Exact scored report](result/v0.3/scored-report.json), SHA-256 `6bcb51d5da359f17f8c33f88c1f2afa28197648c12a9dcf73bc8e94a7a34c471`; [excluded preflight report](result/v0.3/preflight-report.json); [provenance audit](result/v0.3/provenance-audit.json); [all original artifact identities](result/v0.3/artifacts.json); [raw-file hashes](result/v0.3/raw-file-manifest.json).
- [Public evidence archive](result/v0.3/evidence-v0.3.zip): **528,636 bytes**, SHA-256 **`b4e1ccd17a46db8f91ccee29232853bdd6ba5881a1f6c747351d2dfc242a7809`**. It retains all fourteen unchanged original ZIPs, including the complete original artifact containing all 75 raw records and both reports, plus source metadata, hashes and replay instructions. Its persistence does not depend on Actions retention.

Every original ZIP digest/size matched GitHub metadata. All 75 records matched byte-for-byte between individual and complete artifacts. Frozen-source replay reproduced both hosted reports exactly. A separate read-only internal audit reconstructed all 27 oracles from their prompts/inputs, checked schedule/provenance and rejected raw-response, receipt, grade, policy, model, protocol, missing-record and duplicate-record mutations. A fresh cold restoration verified all nineteen checksummed outer members, fourteen original ZIPs and seventy-seven inner files, then reproduced both reports byte-for-byte.

The archive README explains offline trace replay from the immutable source without model inference. This is internal reconstruction of retained evidence, not independent model regeneration or I3 external replication. Software review and protected merge checks provide separate process evidence; they do not promote this bounded result into accepted theory or a general performance claim.
