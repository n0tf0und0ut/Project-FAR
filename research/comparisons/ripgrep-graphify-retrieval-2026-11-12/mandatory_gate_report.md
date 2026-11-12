# Decision study: Graphify mandatory hooks vs ripgrep-first FAR

**Status: Research / internally authored engineering evidence.**
**Pinned FAR source:** `8c6dc6cf840a0d82fb4dcde114c1af471b3f74fe`.
**Verdict:** **NO: keep Graphify optional; do not add mandatory agent hooks, required integration or startup hooks**.

## Operational recommendation

**Do not install Graphify's permanent agent hooks or Git hooks, and do not make it a required dependency or CI gate in Project FAR.** Keep ripgrep as the default first-pass code search; allow on-demand Graphify as an optional second-stage code dependency graph where indexed source/edges warrant it. Do not exclude a source hit because it is absent from Graphify. This is a decision **against deployment now**, not a proof that an improved future integration could never be valuable.

This gate is complete for the present proposal. It identifies testable criteria under which a materially different future proposal could be assessed; it is not an automatic permanent ban, and research results are not self-promoted into accepted FAR theory.

## Prospective controlled pilot (model-directed sandbox edits)

The [pre-registered protocol](mandatory_gate_protocol.json) and [separately frozen gold sets](mandatory_gate_oracle.json) were committed to this PR **before model inference**. An independent 24-function pool, disjoint from the previous 12-question pilot, was selected by SHA-based ranking. Each original Python task asked a local Qwen2.5-Coder-1.5B-Instruct model to nominate every syntactic call-site file affected by a unique function rename.

Three bounded arms ran on every task. **Ripgrep only:** regex candidate evidence and one model patch-plan response. **Optional Graphify:** same ripgrep evidence, with one model-requested second-stage graph query if the model chose it. **Mandatory simulated hook:** Graphify call-edge context injected on every task before the model answered. The model chose paths; a deterministic mutation tool applied targeted AST token edits in an isolated disposable tree and compiled modified Python, then an evaluator compared the patch plan with the hidden oracle. **No real autonomous model-written refactors, production agents, runtime behavioral tests, or installed agent lifecycle hooks were exercised.** This is a controlled proxy, not a true coding-agent benchmark.

| Condition | Exact synthetic edit-plan success | Precision | Recall | Model tokens | Model calls | Optional graph requests | Extra candidates | Omitted candidates |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Ripgrep | 9/24 | 88.5% | 65.8% | 14,885 | 24 | 0 | 10 | 40 |
| Optional Graphify after ripgrep | 10/24 | 87.8% | 61.5% | 17,876 | 26 | 2 | 10 | 45 |
| Auto-injected Graphify | 10/24 | 88.6% | 66.7% | 18,408 | 24 | 0 | 10 | 39 |

Paired outcomes:
- Mandatory vs optional_graph: 1 wins, 22 ties, 1 losses; mean exact difference 0; exploratory 95% bootstrap interval [-0.125, 0.125]
- Mandatory vs rg_only: 2 wins, 21 ties, 1 losses; mean exact difference 0.0417; exploratory 95% bootstrap interval [-0.0833, 0.1667]

Observed measured batch time, excluding cold graph build: 401.382 s ripgrep, 438.623 s optional, 457.7 s mandatory-simulated. **Adding one already-measured cold Graphify build (117.16 s)** yields 574.86 s for this batch; one repeat/refresh was 138.68 s, not a free operation. This is one environment and one run, not a runtime distribution or production budget estimate.

## Predeclared mandatory-hook acceptance gates

| Criterion | Result |
|---|---|
| all_14_specialists_live_integration_verified | UNVERIFIED |
| at_least_three_net_extra_exact_over_each | **FAIL** |
| bootstrap_lower_bound_positive_both | **FAIL** |
| fail_open_and_stale_index_verified | UNVERIFIED |
| model_tokens_within_5pct_both | **FAIL** |
| no_new_mandatory_failures | **FAIL** |
| non_python_and_frozen_evidence_coverage_verified | UNVERIFIED |
| wall_time_within_5pct_both_including_one_cold_graph_build | **FAIL** |
| zero_extra_planned_or_syntax_failures | **FAIL** |

**Interpretation:** a global mandatory hook must demonstrate an advantage over the *option* to invoke the same graph selectively, not merely beat a graph-less baseline. An opt-in workflow can emulate mandatory use when justified. It preserves the choice to avoid graph costs and coverage gaps; a compulsory hook needs extra evidence that agents systematically fail to request the graph when it matters. This study cannot establish that across FAR's full 14-role, multi-language workload.

## Source coverage and actual installed hook behavior

The exact pinned [Graphify source-path inventory](mandatory_gate_coverage.json), computed from the frozen graph and source tarball:

| File type | Source files | Represented by at least one graph node |
|---|---:|---:|
| `.js` | 1 | 1 |
| `.json` | 1245 | 53 |
| `.lean` | 23 | 0 |
| `.md` | 1515 | 0 |
| `.py` | 945 | 945 |
| `.sh` | 11 | 11 |
| `.yaml` | 71 | 68 |
| `.yml` | 78 | 78 |

**Coverage counts are node source paths, not semantic dependency recall.** The index gives no direct graph-source representation to FAR's **23 Lean files** or **1,515 Markdown files**, which include formal work and governed documentation. This alone precludes treating the graph as a comprehensive search authority for all roles.

Actual **Graphify 0.9.107** installations were tested in a disposable Git scratch repository, never in FAR:
- `graphify install --project --platform codex` changed scratch `AGENTS.md` (SHA-256 1e8bcde2df2168aa693735cde89acf8cb6bd403990a23d0daa2bb4b21213750e → e7c7e5adc34882146f87cad669e45371840796b6fbbb0b2d4ef82a3c99b8d6d6) to require `graphify query` **before the first grep/search/source read**, conflicting with FAR's proposed ripgrep-first order. It installed 11 files under `.codex/`.
- The registered Codex `PreToolUse` command was `graphify hook-check`. In a direct replay with `graphify-out/graph.json` present, it exited zero and produced **zero stdout/stderr bytes**. The installer itself labels it an intentional no-op on Codex Desktop; guidance relies on `AGENTS.md`, not the hook.
- `graphify hook install` created **four** local Git hooks (`post-commit`, `post-checkout`, `post-merge`, `post-rewrite`) plus a graph merge driver. This would add maintenance and merge-state trust surfaces; the test does not claim a full FAR-hook execution.
- `graphify codex uninstall` and `graphify hook uninstall` removed the scratch hooks/driver and restored byte-identical original scratch `AGENTS.md`. Proof: [install receipts](mandatory_hook_install_smoke.json), [uninstall receipts](mandatory_hook_uninstall_smoke.json), [Codex no-op replay](mandatory_hook_codex_noop_probe.json).

## Negative findings and unresolved boundaries

The previous [12×3 static retrieval study](README.md) found **10/12** exact answers for ripgrep, **6/12** Graphify, **11/12** combined, with combined model tokens 5,754 versus 6,069 for ripgrep. That small improvement had a paired interval including zero and explicitly excluded graph-build cost. The new experiment is disjoint from its 12 model questions, but not an external independent replication.

Non-exact new task-arm cases (examples, not omitted failures):
- `detect_weakening` / `mandatory_graph_hook`: missed ['tests/test_pr436_root_closure.py', 'tests/test_target_category_compositional_invariant.py', 'tests/test_target_category_validator_assurance_hardening.py'], extra [], error None, compiles True
- `detect_weakening` / `optional_graph`: missed ['tests/test_pr436_root_closure.py', 'tests/test_target_category_compositional_invariant.py', 'tests/test_target_category_validator_assurance_hardening.py'], extra [], error None, compiles True
- `detect_weakening` / `rg_only`: missed ['far_validation/mutations.py'], extra [], error None, compiles True
- `read_attestation` / `mandatory_graph_hook`: missed ['far_validation/assured_engine.py', 'far_validation/certificate.py', 'far_validation/formal_model.py', 'far_validation/mutations.py', 'tests/test_validation_assurance.py'], extra ['far_validation/trust.py'], error None, compiles True
- `read_attestation` / `optional_graph`: missed ['far_validation/assured_engine.py', 'far_validation/certificate.py', 'far_validation/formal_model.py', 'far_validation/mutations.py', 'tests/test_validation_assurance.py'], extra ['far_validation/trust.py'], error None, compiles True
- `read_attestation` / `rg_only`: missed ['far_validation/assured_engine.py', 'far_validation/certificate.py', 'far_validation/formal_model.py', 'far_validation/mutations.py', 'tests/test_validation_assurance.py'], extra ['far_validation/trust.py'], error None, compiles True
- `heuristic_proposal` / `mandatory_graph_hook`: missed [], extra ['commercial/far-investigation-audit/proposals.py'], error None, compiles True
- `heuristic_proposal` / `optional_graph`: missed [], extra ['commercial/far-investigation-audit/proposals.py'], error None, compiles True
- `heuristic_proposal` / `rg_only`: missed [], extra ['commercial/far-investigation-audit/proposals.py'], error None, compiles True
- `write_attestation` / `mandatory_graph_hook`: missed ['far_validation/assured_engine.py', 'far_validation/certificate.py', 'far_validation/formal_model.py', 'far_validation/mutations.py', 'tests/test_validation_assurance.py'], extra ['far_validation/trust.py'], error None, compiles True
- `write_attestation` / `optional_graph`: missed ['far_validation/assured_engine.py', 'far_validation/certificate.py', 'far_validation/formal_model.py', 'far_validation/mutations.py', 'tests/test_validation_assurance.py'], extra ['far_validation/trust.py'], error None, compiles True
- `write_attestation` / `rg_only`: missed ['far_validation/assured_engine.py', 'far_validation/certificate.py', 'far_validation/formal_model.py', 'far_validation/mutations.py', 'tests/test_validation_assurance.py'], extra ['far_validation/trust.py'], error None, compiles True
- `load_swe_agent_trace` / `mandatory_graph_hook`: missed [], extra ['commercial/far-decision-integrity/src/far_decision_integrity/swe_agent.py'], error None, compiles True
- `load_swe_agent_trace` / `optional_graph`: missed [], extra ['commercial/far-decision-integrity/src/far_decision_integrity/swe_agent.py'], error None, compiles True
- `load_swe_agent_trace` / `rg_only`: missed [], extra ['commercial/far-decision-integrity/src/far_decision_integrity/swe_agent.py'], error None, compiles True
- `history_contiguous` / `mandatory_graph_hook`: missed ['tests/test_upp_historical_checkers.py', 'tools/check_upp_w3_contract.py', 'tools/check_upp_w6_equivalence.py', 'tools/check_upp_w7_recoverable_commitment.py', 'tools/check_upp_w8_constrained_evolution.py'], extra ['tools/upp_queue_history.py'], error None, compiles True
- `history_contiguous` / `optional_graph`: missed ['tests/test_upp_historical_checkers.py', 'tools/check_upp_w3_contract.py', 'tools/check_upp_w6_equivalence.py', 'tools/check_upp_w7_recoverable_commitment.py', 'tools/check_upp_w8_constrained_evolution.py'], extra ['tools/upp_queue_history.py'], error None, compiles True
- `history_contiguous` / `rg_only`: missed ['tests/test_upp_historical_checkers.py', 'tools/check_upp_w3_contract.py', 'tools/check_upp_w6_equivalence.py', 'tools/check_upp_w7_recoverable_commitment.py', 'tools/check_upp_w8_constrained_evolution.py'], extra ['tools/upp_queue_history.py'], error None, compiles True
- `verify_signature` / `mandatory_graph_hook`: missed ['far_validation/repin_agepony_acceptance.py'], extra [], error None, compiles True
- `recover_target` / `mandatory_graph_hook`: missed ['tests/test_s_core_w3_reference.py', 'tools/check_s_core_w3.py', 'tools/s_core_w3_reference.py', 'tools/w3_5_factorization.py'], extra ['tools/s_core_w3_recovery.py'], error None, compiles True
- `recover_target` / `optional_graph`: missed ['tests/test_s_core_w3_reference.py', 'tools/check_s_core_w3.py', 'tools/s_core_w3_reference.py', 'tools/w3_5_factorization.py'], extra ['tools/s_core_w3_recovery.py'], error None, compiles True
- `recover_target` / `rg_only`: missed ['tests/test_s_core_w3_reference.py', 'tools/check_s_core_w3.py', 'tools/s_core_w3_reference.py', 'tools/w3_5_factorization.py'], extra ['tools/s_core_w3_recovery.py'], error None, compiles True
- `validate_socratic_record` / `rg_only`: missed ['mechanization/far_mechanization/epistemic.py'], extra [], error None, compiles True
- `analyze_checker_source` / `optional_graph`: missed ['far_validation/mutations.py', 'tests/test_validation_assurance.py', 'tests/test_validation_trace_regression.py'], extra [], error None, compiles True
- `analyze_checker_source` / `rg_only`: missed ['far_validation/mutations.py', 'tests/test_validation_assurance.py', 'tests/test_validation_trace_regression.py'], extra [], error None, compiles True
- `source_receipt` / `mandatory_graph_hook`: missed ['tests/test_weight_space_publication.py', 'tools/check_weight_space_publication.py', 'tools/weight_space_replay.py'], extra [], error None, compiles True
- `source_receipt` / `optional_graph`: missed ['tests/test_weight_space_publication.py', 'tools/check_weight_space_publication.py', 'tools/weight_space_replay.py'], extra [], error None, compiles True
- `source_receipt` / `rg_only`: missed ['tests/test_weight_space_publication.py', 'tools/check_weight_space_publication.py', 'tools/weight_space_replay.py'], extra [], error None, compiles True
- `compile_proposal` / `mandatory_graph_hook`: missed ['commercial/far-investigation-audit/full_cli.py', 'commercial/far-investigation-audit/tests/test_end_to_end.py', 'commercial/far-investigation-audit/tests/test_independent_evidence.py', 'commercial/far-investigation-audit/workflow.py'], extra ['commercial/far-investigation-audit/proposals.py'], error None, compiles True
- `compile_proposal` / `optional_graph`: missed ['commercial/far-investigation-audit/full_cli.py', 'commercial/far-investigation-audit/tests/test_end_to_end.py', 'commercial/far-investigation-audit/tests/test_independent_evidence.py', 'commercial/far-investigation-audit/workflow.py'], extra ['commercial/far-investigation-audit/proposals.py'], error None, compiles True

Additional limits:
- All model calls used one local small model and a **syntactic** `ast.Call` identifier oracle; it does not resolve symbol binding, imports, runtime behavior or actual bugfix quality.
- The mandatory condition **simulates** graph context on each task; stock Codex Graphify installation did not provide that capability in the direct hook-check test.
- No validated fail-open behavior on missing/stale graphs, actual 14-role orchestration, real code-review independence, non-Python semantic coverage, or commercial effectiveness. Unmeasured gates are explicit **failures to establish justification**, not fabricated negative test successes.
- Graphify's extracted index is cached at the pinned source revision; code edits can invalidate graph freshness. Frozen inputs, negative findings, model identifiers and complete receipts remain available.

## Reproducible provenance

- [Precommitted selector and criteria](mandatory_gate_protocol.json), [gold file sets](mandatory_gate_oracle.json), [frozen runner](mandatory_gate_run.py), [append-only lease resumer](mandatory_gate_resume.py), [analysis implementation](mandatory_gate_analyze.py).
- [Model inputs, outputs, tool calls and receipts (gzip-compressed JSONL)](mandatory_gate_raw.jsonl.gz), [execution manifest](mandatory_gate_execution_manifest.json), [per-case analysis and final gates](mandatory_gate_analysis.json).
- Raw JSONL SHA-256: `be8903fab02fc4ba94c41f51491331575c9f7e0ca279cc88f9ecbd4daad3d519`; compressed `mandatory_gate_raw.jsonl.gz` SHA-256: `310de9914bdfc140f972920db2e25c1288c225121200f160de5765863043265a`. Decompress with `gzip -dc mandatory_gate_raw.jsonl.gz > mandatory_gate_raw.jsonl`. The [append-only resumption receipt](mandatory_gate_resumption_receipt.json) preserves the first hosted 15-minute lease expiry (exit 124) and continuation of the remaining 22 tasks without rewriting the prior 50 completed receipts. [Initial log](mandatory_gate_initial_run_stdout.txt) and [continuation log](mandatory_gate_resume_stdout.txt) are retained.
- Eight focused tests in [test_mandatory_gate.py](test_mandatory_gate.py) passed, including source isolation, AST token matching, parser path-traversal rejection and disjoint frozen selection. These tests do not imply live FAR agent integration.
- [Code path coverage source](mandatory_gate_coverage.py), [source coverage output](mandatory_gate_coverage.json), [actual isolated installer and removal receipts](mandatory_hook_install_smoke.json) and [no-op probe](mandatory_hook_codex_noop_probe.json).
- Source graph SHA-256: `44684f162f115b4193d09b49ec42d0bee2e30751e0f2de662cfd55ac22f59625`; local model SHA-256: `f530705d447660a4336c329981af164b471b60b974b1d808d57e8ec9fe23b239`.
- This report is **Research**, does not alter FAR's accepted theory, frozen evidence, 14-role orchestration, required CI, branch protection or agent startup configuration. Merge of these research notes must still satisfy normal exact-head substantive review and protected GitHub gates.
