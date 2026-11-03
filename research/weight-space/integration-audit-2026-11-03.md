# Weight-space research integration audit — 2026-11-03

Status: Research. This is a subsequent internal audit of preserved evidence, not a new inference campaign, external scientific replication or production approval.

## Baseline and disposition

Read the complete current root AGENTS.md through GitHub. Protected main was `9bde2cb02163d358640f805208aa51de2a998425`, with PR #610 merged and three source-bound required checks: merge-authority, protected-repin-gate and pr-review-convergence-observation. Current README, project status, canonical map, research charter, workflow guide and review-convergence policy control. Accepted theory and production paths are unchanged.

PR #613's description still claimed the pilot was executing, while its head `7a1d48062e86b3d5ff5b6a30af63acddeadc2305` already preserved completed outcomes. The experiment source and original archive remain immutable. Local merge `68a83823` and published merge `964b5313ca0b212b82d8c89649535ab1d237479b` have the identical tree `a92f9982dedef9f85286c6645041f6699a157cda`: both reconcile the branch with protected main, retain #610 evidence, and resolve the research-index conflict using the completed repair result plus links to both distinct research tracks. Git push lacked CLI credentials; connected GitHub object/ref operations published the tested trees with an expected-head, nonforced update. No shared history was rewritten.

| Study | Audited result | Interpretation |
| --- | --- | --- |
| #605 implementation / #609 publication | Control 11/30, FAR 10/30, difference −3.33 percentage points | Completed scripted repair; no FAR benefit or general agent-reliability result. Not repeated. |
| #610 | Frozen-source raw replay reproduced the 3-record preflight and 72-record scored reports exactly; 24/24 tasks pass all three repetitions | Authored virtual-workspace/calculator tasks. Temperature-zero repeated trajectories, no FAR control contrast, no general reliability claim. Earlier 1.5B failures retained. |
| #613 | All 432 scored records and six development records regraded; full checkpoint/tokenizer replay matches published analysis | Selected edit 1/36 heldout, prompt 1/36. No superiority; no production candidate. |
| #611 | Five-arm loop protocol remains design only / NOT RUN | Its generic evidence auditor and this distinct eight-arm pilot have different scopes. No silent completion or pooling. |
| #601 | Separate activation-fidelity research and negative mechanistic findings | No new results or scientific promotion in this integration. |

## MIT reconstruction

Cloned `RikiyaT/lm_understand-logs` and verified revision `4d09ba6d6a7e891dd8063974dfe81b3d78e3494f`. Recomputed all 46 benchmark-condition groups and 561 source-file identities. Original MATH-500 counts are 158/2,000 versus 962/2,000, exactly 7.9% versus 48.1%. Independently fetched the two base tensor byte ranges, replayed the sparse BF16 changes, and matched both evaluated tensor hashes and the separately published edited checkpoint at revision `d1671a178705bcab7644806d23c535517f35723b`. Confirmed 131,072 addressed coordinates and 130,188 actual bit-pattern changes. The [full report](mit/VERIFICATION.md) retains checkpoint identity, edit formula, grading differences, practice rescues/regressions, unsuccessful Gemma results and missing optimized simpler baselines.

No original MIT benchmark inference was rerun. Source arithmetic and tensor reconstruction establish consistency of the released evidence and edit identity, not external reproduction of the full behavioral treatment effect. The MIT result warrants targeted replication against frozen optimized prompt, decoding, non-thinking and interruption/budget baselines. Reliable general optimization, new intelligence and recursive self-improvement are unsupported.

## Reproduced software defects and corrections

| ID | Violated invariant and counterexample | Correction and verification |
| --- | --- | --- |
| WSP-PUB-001 | Publication CI did not verify the retained result archive; it ran synthetic tests and schedule validation only. A changed publication could evade that workflow's evidence checks. | Added `tools/check_weight_space_publication.py`, CI invocation and eight actual-archive tests. Corrupted bytes, missing/duplicate slots, unsafe member names, forged grades, fabricated source and favorable substituted analysis are rejected. Every accepted original record is regraded; this adds zero model observations. |
| WSP-MIT-002 | Rerunning source/published-checkpoint verifiers overwrote supplemented frozen manifests, deleting `local_audit_artifacts` or `score_arithmetic_recomputed`. | Verifiers compare published evidence read-only by default. New reconstruction destinations are exclusive. Published-checkpoint arithmetic now recomputes its supplemental counts. Actual source/tensor/HTTP verification succeeds without changing the original JSON receipts. |
| WSP-PUB-002 | Hosted Python 3.11 job `126046171103` rejected the actual archive while Python 3.12 passed. Python's changed `sum` produced a one-ULP difference (5.684341886080802e-14 seconds) in random-ablation CPU cost. | Reproduced on actual Python 3.11.17 and with the new legacy-summation regression. Explicit `math.fsum` reconstructs both floating cost totals identically across versions, with no tolerance or change to any primary grade, outcome, statistic or evidence byte. Both versions now produce identical publication receipts. CI directly covers both versions. |
| WSP-CKPT-001 | Independent review `5755800352`, comment `4457471645`, found that an extra `chat_template.jinja` could override pinned tokenizer configuration. Reproduced both validator acceptance and actual Transformers 4.49.0 sidecar precedence without model inference. | Strict successor validation rejects every extra file/directory, root symlinks and duplicate manifest names before loader access. Two permanent regressions fail on the original helper and pass on the successor. The original eight-file checkpoint passes; no evidence that published traces used an override. The [v0.1.1 correction binding](postexecution-checkpoint-patch-v0.1.1.json) records exact before/after source hashes. Original experiment bytes remain frozen; the publication checker admits only this explicitly bound successor while rejecting unrelated source drift. |

The new publication checker never extracts or executes archive contents. It reconstructs grades/analysis from retained bytes and compares the measured source against Git objects, separately binding the documented software successor; tokenizer and tensor reconstruction remain separate checks. Neither checker proves remote execution authenticity, an oracle's semantic correctness, or independent scientific reproduction. Prospective source remains preserved at its original commit; task objects, proposals, trace bytes, primary grades, analysis and archive were not altered. Current loader validation is explicitly a post-execution correction, not the source that generated the recorded results.

## Commands and validation boundary

From the integrated checkout:

```bash
python -m tools.check_weight_space_publication
python -m unittest tests.test_weight_space_edits tests.test_weight_space_pilot tests.test_weight_space_publication -v
python tools/run_tests.py
make health-fast
```

For MIT reconstruction, use the pinned upstream clone and the documented optional NumPy environment:

```bash
python research/weight-space/mit/verify_original_evidence.py --source-dir /tmp/far-mit-source
python research/weight-space/mit/replay_tensor_diff.py --source-dir /tmp/far-mit-source
python research/weight-space/mit/verify_published_checkpoint.py
```

Full archived tokenizer/checkpoint replay used the pinned eight-file Smol checkpoint and reproduced the complete published analysis exactly. Tool-agent replay used an isolated worktree at frozen source `6c382c798df0a95824b79e76263318865ee24c68`; both reports matched exactly. Checksums of all outer tool-agent archive members were verified before extracting the complete original artifact. These are cold trace reconstructions, not new model samples.

The first integrated candidate passed 40 targeted tests and 2,802 canonical tests with three skips. An initial concurrent health run passed 125 component checks but failed its read-only-tree check because the audit scripts/source files changed during execution; this remains a failed validation attempt. The stabilized rerun passed 125 health checks with zero warnings/failures, the remaining Makefile validators and 20 theory-dependency tests. Uncached pr-fast passed all nine checks on tree `792976612f558e512edbba346bb80854eaac918e`, published by candidate `1211686f559416c856d5b13f3f87bd715b5fa55d`. Hosted Python 3.11 then exposed WSP-PUB-002 on successor `2fef3b9f33f95d3adcf6d0498c24ae9a4d26fcd2`; preserve that failed check rather than calling earlier local success final. The corrected publication checks pass all nine controls on actual Python 3.11.17 and 3.12 and produce identical receipts. Final whole-suite/hosted checks and review are reported on PR #613, not inferred from earlier-head success. No failed model attempt was retried or omitted.

## Adoption and remaining gates

Reject the tested Smol column edit as an adoption candidate: it tied the tested prompt fix, failed the registered meaningful-gain screen, and the zero-success regression cohort cannot establish useful capability preservation. Development showed zero repetitive-suffix failures, so the loop hypothesis was not testable. Cross-model transfer, stronger optimized baselines and independently controlled model regeneration remain NOT RUN. They are necessary before a future positive candidate can advance; they cannot turn this negative candidate into a positive result.

The internally actionable deliverable is research infrastructure plus a reproducible bounded negative experiment. General agent reliability remains unestablished. Final independent substantive PR review, current-head checks, the protected App's decision and merge authorization remain separate obligations. No merge or production integration is authorized by this report.
