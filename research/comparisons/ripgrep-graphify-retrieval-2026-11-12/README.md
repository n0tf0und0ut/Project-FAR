# Ripgrep-first / optional Graphify retrieval pilot — 2026-11-12

**Status: Research (bounded internal engineering evaluation); not Accepted theory, independent replication, proof of general agent reliability, or authority to add a production dependency.**

## Operational decision, with scope

- Keep **ripgrep (`rg`)** as the default when available for initial FAR code and test search. Native authorized search remains a fallback.
- Use **Graphify only optionally** for *second-stage* code dependency and impact navigation, after source search warrants it. The candidate set must preserve ripgrep-only findings; a missing graph edge is **not** grounds to drop a source hit or assert there is no dependency. Check material conclusions against code, tests, and governing evidence.
- **Do not** install persistent Graphify agent hooks, modify agent startup, add Graphify as a required dependency or CI gate, or promote research status on this evidence. This is a conservative tool-use guideline, **not permanent integration**.
- The only behavioral documentation change proposed alongside this record is a paragraph in [operational workflow guidance](../../../docs/maintenance/agent-workflow-orchestration.md#code-search-and-dependency-analysis-operational-guidance). This does not modify `AGENTS.md`, theory, research registries, frozen experiments, existing agents, or executable paths.

## Executed local-model comparison

**Source snapshot:** protected-main commit `8c6dc6cf840a0d82fb4dcde114c1af471b3f74fe` on 2026-11-12. **Protocol:** 12 frozen uniquely defined Python functions selected by a SHA-seeded rule from 92 eligible functions, three fixed retrieval arms per function, **36 executed local-model calls**. Each call used the same Qwen2.5-Coder-1.5B-Instruct GGUF Q4_K_M model under `llama-cpp-python==0.3.36`, temperature zero, with separate model context. The correct file sets came from an AST `ast.Call` terminal-identifier oracle; this is a **syntactic** metric, not proof of runtime binding.

| Measure | Ripgrep only | Graphify only | Ripgrep then Graphify |
|---|---:|---:|---:|
| Exactly correct file sets | 10/12 | 6/12 | **11/12** |
| File-set micro precision | 97.67% | 100.00% | 97.73% |
| File-set micro recall | 97.67% | 76.74% | **100.00%** |
| File-set micro F1 | 97.67% | 86.84% | **98.85%** |
| Model prompt tokens | 5,400 | 3,795 | 5,071 |
| Model completion tokens | 669 | 551 | 683 |
| **Total measured model tokens** | **6,069** | **4,346** | **5,754** |
| False-negative files | 1 | 10 | **0** |
| False-positive files | 1 | 0 | 1 |

**Observed comparison:** the combined arm answered **one more task exactly** than ripgrep alone, while using **315 fewer local inference tokens (5.19%)**. On paired per-task F1, hybrid won one task, tied 11 and lost zero. The exploratory 10,000-resample paired-bootstrap 95% interval for mean F1 difference was **[0.0000, 0.0500]**; it includes zero. These results do **not** demonstrate a stable population advantage, economic ROI, or better autonomous agent work.

**Negative evidence and concrete examples:**

- `terminally_closed`: ripgrep and combined retrieval reported `tools/upp_queue_history.py` as a call-site even though it held a *definition* rather than a call; Graphify omitted a real test-file call. All three arms failed this question.
- `maximality_verdict`: the ripgrep-only model omitted the real call in `tools/check_upp_w14_maximality.py`, whereas the combined arm recovered it. Graphify alone omitted that and another valid file.
- Graphify alone omitted valid call-site files for `discover_suite`, `promotion_clauses`, `predictions_from_far_bundle`, and `semantic_agreement`. Thus Graphify must not serve as an exhaustive filter on code-search evidence.
- All 36 calls completed with valid JSON and no model-execution errors; these are substantive retrieval/answer errors, not provider-availability failures.

## Graph construction and earlier direct retrieval controls

The Graphify 0.9.107 index used `GRAPHIFY_BACKEND=none`, `--code-only --no-cluster --max-workers 4`: **19,100 nodes, 43,839 edges**, 18,991,350-byte JSON, SHA-256 `44684f162f115b4193d09b49ec42d0bee2e30751e0f2de662cfd55ac22f59625`, **zero model tokens** during graph extraction. Initial extraction took **117.16 seconds**. An unchanged-checkout repeat took **138.68 seconds**, reporting three changed inputs and 2,357 unchanged; the graph bytes matched exactly. Building and refreshing this graph is **not included** in the model-token comparison. Graphify skipped 1,537 non-code files and reported 156 unclassified files; it is not a complete map of FAR documents/Lean semantics.

The earlier *direct tool*, non-model AST-call evaluation of 12 questions found Graphify call-edge precision **100%** (66 true positives, 0 false positives), recall **91.67%** (6 false negatives); ripgrep precision **94.74%** (72 true positives, 4 false positives), recall **100%** (0 false negatives). A separate 12-question replay on changes from merged PRs #658, #636 and #650 found Graphify **12/12** exact versus ripgrep **10/12**. These two historical/selected evaluations also do not establish generalization; see the [earlier evidence archive](https://d2ol7oe51mr4n9.cloudfront.net/user_3IVsV5OQ41U43FV2Cnr4dHkvb3g/eaf61d02-3953-4190-bd3f-bfbd8cbfb2b3.zip) (SHA-256 `d6686f572316bd5a0593729e37f17e25ab116b810456243445b75f4e542e463b`).

## Frozen receipts and replay

The following **exact executed research artifacts** are retained here, without upgrading their status:

- [`protocol.json`](protocol.json): frozen task selector, prompt regimen, reference commit, and source/graph hashes. Protocol SHA-256: `f6ca19d8f772d1e487579ea7ef460de41bf24e4392161334b0e968e766960564`.
- [`oracle.json`](oracle.json): independently constructed AST identifier-match file sets, not disclosed to the model. SHA-256: `a23c05325d326c0c9f5a79ae26e776c84f63a89b3e292c51ca959a4c0300bd30`.
- [`execution_manifest.json`](execution_manifest.json): model SHA-256 `f530705d447660a4336c329981af164b471b60b974b1d808d57e8ec9fe23b239`, settings, execution-script SHA, and evidence provenance.
- [`run_results.jsonl`](run_results.jsonl): all 36 raw model outputs, returned token usage, retrieved evidence, timings, parsing/error fields, and exact task identities. Raw receipts SHA-256: `e29a3548586989e4434b6e7f099e9ffc5e10f156d755d4613cfea5e7d487f01a`.
- [`analysis.json`](analysis.json): per-task scores, aggregate metrics, bootstrap and retained failures. SHA-256: `0c75972a72a6ca5f5b22dc1a29645322af2d471b971c32292a79b460a6243f30`.
- [First extraction log](graphify_initial_extraction.json) and [unchanged-checkout repeat](graphify_repeat_extraction.json): observed stdout/stderr, exit status and wall-clock timing.

The [complete verified evaluation archive](https://d2ol7oe51mr4n9.cloudfront.net/user_3IVsV5OQ41U43FV2Cnr4dHkvb3g/82494e28-e248-4ef1-bcaf-c5f06cf3c3ba.zip) (ZIP SHA-256 `58d5ae67dc049536e402f55cff96766f1c832f11fa4c581f1473ec61117b994e`) additionally holds the pinned **19 MB graph**, executed `compare.py`, `prepare.py`, `analyze.py`, seven passing focused tests, `reproduce.sh`, and the complete study report. The external archive is supplemental; this repository retains the task manifest, oracle, all 36 raw receipts, analyzed outcomes and graph-construction observations. The graph and model weights are not vendored.

## Limits and next acceptance gate

This was **one small local model** responding to *fixed, non-agentic retrieval evidence* in 12 syntactic Python call-site tasks. It did not execute autonomous tool selection, source edits, held-out code tests, multi-hop impact verification, FAR's 14 specialists, or external independent reviews. Answer quality, prompt payload, and small sample size constrain inference; 5.19% refers only to **local model token counts** and excludes index generation, maintenance and actual agent operating cost.

Before any production Graphify integration, separately preregister and adjudicate a larger held-out multi-hop coding-agent experiment with executable fixes and tests; report accuracy, negative controls, indexed/unindexed coverage, latency, all model tokens, amortized graph setup/refresh and failure modes. Research records, including negative findings, remain Research until governed replication, acceptance and promotion.


## 2026-11-12 prospective mandatory-hook adoption gate — executed

**Current operational verdict: NO mandatory Graphify hooks, required installation, default graph-first instructions, mandatory CI dependency, or Git-update hooks.** Keep ripgrep as FAR's default initial search and Graphify as optional source-bound code dependency navigation. The decision is a bounded engineering adoption disposition, **not acceptance or promotion of Research to theory**.

The [complete adoption report](mandatory_gate_report.md) documents a prospectively frozen **24-task × 3-arm local-model experiment** disjoint from this page's earlier 12 tasks, with a **synthetic AST refactor planner and sandbox-only source edits**. Exact successes were ripgrep **9/24**, optional graph **10/24**, and simulated mandatory graph **10/24**; model tokens were respectively **14,885**, **17,876**, and **18,408**. Mandatory did not beat optional; it lost to optional on one case, won one, and tied 22. Including one measured cold graph build raised the mandatory study's batch time to **574.86 seconds** versus **401.38 seconds** for ripgrep without indexing. All requested acceptance gates failed or remained unverified. This experiment did not run genuine autonomous repair agents, actual installed model hooks, production workloads, or the 14 FAR specialists.

[Preregistered protocol](mandatory_gate_protocol.json), [separately frozen oracle](mandatory_gate_oracle.json), [72 gzip-compressed raw execution receipts](mandatory_gate_raw.jsonl.gz), [scoring output](mandatory_gate_analysis.json), [run manifest](mandatory_gate_execution_manifest.json), [frozen runner](mandatory_gate_run.py), [continuation wrapper](mandatory_gate_resume.py), [scorer](mandatory_gate_analyze.py), [isolated installer](mandatory_hook_install_smoke.json), [installer cleanup](mandatory_hook_uninstall_smoke.json), [no-op Codex probe](mandatory_hook_codex_noop_probe.json), [source-path coverage](mandatory_gate_coverage.json), and [interrupted-run resumption evidence](mandatory_gate_resumption_receipt.json) are retained. The 15-minute hosted lease expired after 50 completed pairs; the remaining 22 were produced by append-only resumption and neither the interruption nor its replay is misrepresented as an uninterrupted execution. Full replay instructions and eight passing focused tests appear in the report.

The **stock Graphify 0.9.107 Codex installer** was exercised in a separate scratch Git repo. It added a graph-before-grep clause to scratch `AGENTS.md` (conflicting with FAR's ripgrep-first policy), a `graphify hook-check` PreToolUse command that returned zero output in an actual local probe, four Git hooks, and a merge driver. Scratch uninstall restored the original `AGENTS.md` bytes. On FAR's pinned Graphify source-path index, **0/23 Lean** and **0/1,515 Markdown** files appear as node sources, even though 945/945 Python files do. Neither installer nor hooks were installed in FAR.

These results reject the **current permanent/mandatory integration proposal**. A future materially different candidate still requires prospective, independently reviewed semantic and executable evidence across all relevant FAR specialists, language classes, mutation/recovery states, and true provider/agent costs. The earlier pilot remains frozen and retains its distinct scope and results.
