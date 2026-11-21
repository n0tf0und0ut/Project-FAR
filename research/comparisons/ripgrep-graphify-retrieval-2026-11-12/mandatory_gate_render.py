#!/usr/bin/env python3
"""Render factual adoption verdict from preregistered gate results and smoke receipts."""
import hashlib,json,pathlib
D=pathlib.Path(__file__).resolve().parent
p=json.loads((D/'mandatory_gate_protocol.json').read_text())
a=json.loads((D/'mandatory_gate_analysis.json').read_text())
c=json.loads((D/'mandatory_gate_coverage.json').read_text())
smoke=json.loads((D/'mandatory_hook_install_smoke.json').read_text())
uninstall=json.loads((D/'mandatory_hook_uninstall_smoke.json').read_text())
probe=json.loads((D/'mandatory_hook_codex_noop_probe.json').read_text())
assert a['model_run_count']==len(p['tasks'])*3==72
assert c['source_commit']==p['source_sha']
assert smoke['test_assertions_passed'] and uninstall['policy_byte_identical']
assert probe['stdout_bytes']==0 and probe['exit_code']==0
s=a['metrics'];g=a['gate_passes'];f=lambda val:'PASS' if val else '**FAIL / NOT VERIFIED**'
rows=[]
for arm,label in [('rg_only','Ripgrep'),('optional_graph','Optional Graphify after ripgrep'),('mandatory_graph_hook','Auto-injected Graphify')]:
 x=s[arm]
 rows.append(f"| {label} | {x['exact']}/{x['runs']} | {x['micro_precision']*100:.1f}% | {x['micro_recall']*100:.1f}% | {x['total_model_tokens']:,} | {x['model_calls']} | {x['graph_requests']} | {x['fp']} | {x['fn']} |")
unmeasured={'all_14_specialists_live_integration_verified','fail_open_and_stale_index_verified','non_python_and_frozen_evidence_coverage_verified'}
passes='\n'.join(f"| {k} | {('PASS' if v else 'UNVERIFIED' if k in unmeasured else '**FAIL**')} |" for k,v in g.items())
cases=[]
for r in a['scored_runs']:
 if not r['exact_synthetic_patch']:
  cases.append(f"- `{r['function']}` / `{r['arm']}`: missed {r['missing']}, extra {r['extra']}, error {r['reported_error']}, compiles {r['code_compiles']}")
cases='\n'.join(cases[:30])
prev=json.loads((D/'analysis.json').read_text())
md=f"""# Decision study: Graphify mandatory hooks vs ripgrep-first FAR

**Status: Research / internally authored engineering evidence.**
**Pinned FAR source:** `{p['source_sha']}`.
**Verdict:** **{a['verdict']}**.

## Operational recommendation

**Do not install Graphify's permanent agent hooks or Git hooks, and do not make it a required dependency or CI gate in Project FAR.** Keep ripgrep as the default first-pass code search; allow on-demand Graphify as an optional second-stage code dependency graph where indexed source/edges warrant it. Do not exclude a source hit because it is absent from Graphify. This is a decision **against deployment now**, not a proof that an improved future integration could never be valuable.

This gate is complete for the present proposal. It identifies testable criteria under which a materially different future proposal could be assessed; it is not an automatic permanent ban, and research results are not self-promoted into accepted FAR theory.

## Prospective controlled pilot (model-directed sandbox edits)

The [pre-registered protocol](mandatory_gate_protocol.json) and [separately frozen gold sets](mandatory_gate_oracle.json) were committed to this PR **before model inference**. An independent 24-function pool, disjoint from the previous 12-question pilot, was selected by SHA-based ranking. Each original Python task asked a local Qwen2.5-Coder-1.5B-Instruct model to nominate every syntactic call-site file affected by a unique function rename.

Three bounded arms ran on every task. **Ripgrep only:** regex candidate evidence and one model patch-plan response. **Optional Graphify:** same ripgrep evidence, with one model-requested second-stage graph query if the model chose it. **Mandatory simulated hook:** Graphify call-edge context injected on every task before the model answered. The model chose paths; a deterministic mutation tool applied targeted AST token edits in an isolated disposable tree and compiled modified Python, then an evaluator compared the patch plan with the hidden oracle. **No real autonomous model-written refactors, production agents, runtime behavioral tests, or installed agent lifecycle hooks were exercised.** This is a controlled proxy, not a true coding-agent benchmark.

| Condition | Exact synthetic edit-plan success | Precision | Recall | Model tokens | Model calls | Optional graph requests | Extra candidates | Omitted candidates |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

Paired outcomes:
{chr(10).join('- Mandatory vs '+k.split('mandatory_minus_')[1]+': '+str(v['wins'])+' wins, '+str(v['ties'])+' ties, '+str(v['losses'])+' losses; mean exact difference '+str(v['mean_exact_difference'])+'; exploratory 95% bootstrap interval '+str(v['bootstrap_95_interval']) for k,v in a['paired'].items())}

Observed measured batch time, excluding cold graph build: {a['costs']['rg_only']['observed_calls_only_seconds']} s ripgrep, {a['costs']['optional_graph']['observed_calls_only_seconds']} s optional, {a['costs']['mandatory_graph_hook']['observed_calls_only_seconds']} s mandatory-simulated. **Adding one already-measured cold Graphify build ({a['graph_initial_seconds']} s)** yields {a['costs']['mandatory_graph_hook']['total_seconds_with_one_cold_graph_build']} s for this batch; one repeat/refresh was {a['graph_repeat_seconds']} s, not a free operation. This is one environment and one run, not a runtime distribution or production budget estimate.

## Predeclared mandatory-hook acceptance gates

| Criterion | Result |
|---|---|
{passes}

**Interpretation:** a global mandatory hook must demonstrate an advantage over the *option* to invoke the same graph selectively, not merely beat a graph-less baseline. An opt-in workflow can emulate mandatory use when justified. It preserves the choice to avoid graph costs and coverage gaps; a compulsory hook needs extra evidence that agents systematically fail to request the graph when it matters. This study cannot establish that across FAR's full 14-role, multi-language workload.

## Source coverage and actual installed hook behavior

The exact pinned [Graphify source-path inventory](mandatory_gate_coverage.json), computed from the frozen graph and source tarball:

| File type | Source files | Represented by at least one graph node |
|---|---:|---:|
{chr(10).join('| `'+k+'` | '+str(v['source_files'])+' | '+str(v['covered_as_graph_node_source_paths'])+' |' for k,v in c['by_extension'].items())}

**Coverage counts are node source paths, not semantic dependency recall.** The index gives no direct graph-source representation to FAR's **23 Lean files** or **1,515 Markdown files**, which include formal work and governed documentation. This alone precludes treating the graph as a comprehensive search authority for all roles.

Actual **Graphify 0.9.107** installations were tested in a disposable Git scratch repository, never in FAR:
- `graphify install --project --platform codex` changed scratch `AGENTS.md` (SHA-256 {smoke['initial_policy_sha256']} → {smoke['installed_policy_sha256']}) to require `graphify query` **before the first grep/search/source read**, conflicting with FAR's proposed ripgrep-first order. It installed 11 files under `.codex/`.
- The registered Codex `PreToolUse` command was `graphify hook-check`. In a direct replay with `graphify-out/graph.json` present, it exited zero and produced **zero stdout/stderr bytes**. The installer itself labels it an intentional no-op on Codex Desktop; guidance relies on `AGENTS.md`, not the hook.
- `graphify hook install` created **four** local Git hooks (`post-commit`, `post-checkout`, `post-merge`, `post-rewrite`) plus a graph merge driver. This would add maintenance and merge-state trust surfaces; the test does not claim a full FAR-hook execution.
- `graphify codex uninstall` and `graphify hook uninstall` removed the scratch hooks/driver and restored byte-identical original scratch `AGENTS.md`. Proof: [install receipts](mandatory_hook_install_smoke.json), [uninstall receipts](mandatory_hook_uninstall_smoke.json), [Codex no-op replay](mandatory_hook_codex_noop_probe.json).

## Negative findings and unresolved boundaries

The previous [12×3 static retrieval study](README.md) found **10/12** exact answers for ripgrep, **6/12** Graphify, **11/12** combined, with combined model tokens 5,754 versus 6,069 for ripgrep. That small improvement had a paired interval including zero and explicitly excluded graph-build cost. The new experiment is disjoint from its 12 model questions, but not an external independent replication.

Non-exact new task-arm cases (examples, not omitted failures):
{cases}

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
- Source graph SHA-256: `{p['graph_sha256']}`; local model SHA-256: `{a['model_sha256']}`.
- This report is **Research**, does not alter FAR's accepted theory, frozen evidence, 14-role orchestration, required CI, branch protection or agent startup configuration. Merge of these research notes must still satisfy normal exact-head substantive review and protected GitHub gates.
"""
(D/'mandatory_gate_report.md').write_text(md)
print('REPORT_CHARS',len(md))
