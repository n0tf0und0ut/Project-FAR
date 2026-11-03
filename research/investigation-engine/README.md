# Research investigation engine

Status: Research. No accepted core theorem, methodology or assurance status is
changed. General autonomous reliability and superiority are **not established**.

## Executable behavior

[`far_investigation_engine.py`](../../tools/far_investigation_engine.py) accepts
natural-language input. A local model selects actual searches, URLs, exact
quotations, evidence relations, atomic claims, material interpretations and
native verification plans. The runtime enforces read-only permissions, registered
host boundaries, resource budgets, canonical intake validation, terminal source
rechecks, freeze-before-evaluation and mechanical family aggregation. Invalid
calls are rejected and returned to the model; the controller never substitutes
a successful action. A valid native result does not certify its translation from
natural language: the unresolved semantic-correspondence assumption is retained.

The independent implementation in
[`far_investigation_audit.py`](../../tools/far_investigation_audit.py) reconstructs
raw-byte hashes, quotation coordinates, model-to-tool arguments, counters,
chronology, canonical freeze/candidate lineage, native results and report
aggregation offline. This is internal integrity assurance. Self-signed hashes
cannot establish external authenticity or prevent an author rewriting a history.

The qualitative evidence assessor inventories support, opposition, source
dependence and missing evidence. Its relation labels remain fallible analyst
judgments. Exact rational arithmetic, typed source-JSON equality, bounded Boolean
truth tables and two-proportion statistics have separate native scopes. The
statistical result uses a registered Newcombe/Wilson interval; it does not prove
causal identification. Formal entailment concerns the quoted Boolean formulas,
not an unchecked natural-language translation. Source truth, interpretation
completeness and domain adequacy remain separate obligations.

Pipeline completion means actual retrieval, extraction, comparison, valid frozen
intake and every native candidate evaluated. It does not mean FAR evidence
closure: `investigation_closure` remains `Incomplete` unless EC-01 through EC-11
are separately satisfied. An `Unknown` result may be appropriate, but mere
abstention cannot replace unexecuted stages.

## Run and reproduce

From a repository checkout, install the declared dependencies, then run the
deterministic or declarative lane directly:

```bash
python -m pip install 'PyYAML>=6.0,<7' 'jsonschema>=4.22,<5'
python tools/far_investigation_engine.py run \
  'Does the JSON name field at the supplied source equal "cpython"?' \
  --seed https://api.github.com/repos/python/cpython \
  --allow-host api.github.com --mode deterministic --output /tmp/investigation.json
python tools/far_investigation_engine.py audit /tmp/investigation.json
```

For the agent, run a compatible local function-calling model on
`127.0.0.1:8085`, using llama.cpp's `--jinja` template support, then use
`--mode agent`. The campaign command starts and stops the pinned server itself,
which also works in runtimes that isolate loopback between command sessions:

```bash
python tools/far_investigation_campaign.py selection.json \
  --model /absolute/path/Qwen2.5-3B-Instruct-Q4_K_M.gguf \
  --server /absolute/path/llama-server --output /tmp/new-campaign
```

Model: `bartowski/Qwen2.5-3B-Instruct-GGUF`, revision
`f302c64a2269a69fb27b2f9473b362f5bb8e78d8`, `Qwen2.5-3B-Instruct-Q4_K_M.gguf`,
SHA-256 `9c9f56a391a3abbd5b89d0245bf6106081bcc3173119d4229235dd9d23253f94`.
llama.cpp release `b12023`, Ubuntu x64 archive SHA-256
`ae1311cdc0f67bd78e01e7b20bc5ed403814a621c290dd0ee29b8c67c0feece0`.
The campaign additionally records the actual executable hash, source hashes,
Python/platform identity and all raw model envelopes. Neither weights nor
credentials are committed. Pin downloads and verify these hashes before use.

Campaign startup now refuses an occupied model endpoint. Before readiness and
before/after each model response, Linux `/proc` evidence must bind the live direct
child, exact launch command, executable file identity, mapped model-file inode
and exclusive listening socket to the requested weights and runner. PID
namespaces are reconciled against the actual direct-child parent relationship.
An unavailable process view, unmapped weights, dead/replaced child, or different
endpoint owner fails the attempt. This is local process provenance; it does not
authenticate a malicious host or runner. The standalone engine's explicitly
operator-started model remains a separate, operator-owned provenance boundary.

Default network mode requires all observed DNS addresses to be public. In a
proxy-only environment, explicitly select `--dns-mode proxy`: this requires the
inherited HTTPS proxy, forces proxy routing, rejects bypass rules, preserves the
exact host allowlist and records target IP validation as unestablished. It trusts
the configured proxy's DNS/destination enforcement; it does not fabricate a DNS
answer or claim IP pinning. Source-controlled redirects, credentials, arbitrary
methods, IP-literal destinations, private hostnames and automatic host expansion
remain unavailable. Model/source text cannot change this policy.

General source retrieval and public-search adapters use the existing shared
bounded HTTP reader for declared-length and native chunk-framing validation.
Incomplete and interrupted bodies retain their bounded byte prefixes and fail
before evidence parsing. The offline auditor binds every retained source to the
exact proposal, HTTP reservation and transport observation, including sources
retained before a parser failure. Extraction is reconstructed from the actual
proposal and verified quote binding; matching altered output copies cannot
replace the requested source, claim or relation. These are internal consistency
checks, without source-truth or external-authenticity assurance.

Comparisons are also reconstructed from the dispatched evidence IDs and
alternatives, verified quotes, publisher groups and normalized relation labels.
Every retained evidence/comparison row must correspond to a producing tool
attempt, including valid effects retained before a post-dispatch budget
rejection. Recorded time and budgets must satisfy their runtime scalar bounds.
When an accepted source or model observation includes a transport envelope, its
complete-body flags, status, bytes and hash must agree; older frozen receipts
without such an envelope do not gain retrospective framing assurance.

`finish` commits completion only after its dispatch and budget checks succeed.
The final measured budget also includes finish journaling in all three lanes;
an over-budget attempt stays incomplete even when an accepted report is retained
as diagnostic evidence. Native counterexamples are counted by existence, so an
empty Boolean valuation `{}` remains a valid witness.

Sources are projected as strict JSON, UTF-8 text or visible HTML. PDF, OCR,
audio/video, arbitrary code execution, authenticated sources and consequential
external actions are not supported. Crossref and Wikimedia searches provide
discovery metadata only. Retrieved links outside the operator's host permissions
remain unavailable. Changed source projections or search hits block freeze;
start a successor investigation to adopt changed evidence. All failed histories
remain available in their original transcripts.

## Evaluation and evidence

The [registration](preregistration-v0.1.md) precedes new investigation runs.
Selection v1 is preserved byte-for-byte but was exposed to the implementing
coordinator before generic prompt/transport stabilization; it is not promoted
as fresh held-out evidence. Fresh selection and exact execution configuration
are frozen separately before first execution. No case-specific answers or
source-specific parsing branches are implemented.

[`far_investigation_campaign.py`](../../tools/far_investigation_campaign.py)
runs the same tasks under common budgets in agent, deterministic and declarative
lanes. The latter two intentionally use the same bounded retrieval algorithm;
they are two execution representations, not independent competing algorithms.
They preserve relevant lexical passages and abstain on unsupported semantics.
This baseline does not represent every strong deterministic research system.

Mechanical scores describe completion, source/quote/hash integrity, valid
freeze/evaluation bindings, rejections, controller substitutions, tool calls,
tokens, latency and observed source bytes. Semantic correctness, contract
adequacy and unsupported narrative claims require separate substantive review;
they are never inferred from schema success. `http_calls` counts reserved tool
attempts, including policy/transport rejection, rather than successful responses.
Billing, energy and amortized hardware cost remain unmeasured.

The registered Open Deep Research comparison was not completed: its original
uncommitted adapter was lost at the workspace interruption, with no recoverable
exact-source binding or competitor observations. Reconstructing it requires a
separately registered successor; the absent original condition cannot be
recovered by rerunning new source. A competitor is not failed for missing
observations or for lacking FAR artifact formats. Common substantive task
fulfillment and raw graph returns must be assessed separately in any successor.

The separately identified [source-bound preparation](odr-preparation-v0.1.md)
now exercises the actual pinned Open Deep Research graph with scripted model
fixtures and existing FAR read tools. Seven conformance tests pass; there are no
live comparator calls or effectiveness scores. The lost original condition is
still blocked by its missing frozen source identity.

Run the same targeted CI checks locally:

```bash
python -m unittest tests.test_far_investigation_retrieval tests.test_far_investigation_verifiers tests.test_far_investigation_engine tests.test_far_investigation_audit tests.test_far_investigation_campaign tests.test_far_investigation_odr_preparation tests.test_far_autonomous_investigation tests.test_far_uncertain_routing_pilot tests.test_far_routing_dispatch tests.test_far_intake_v1 -v
python tools/far_investigation_campaign.py audit research/investigation-engine
```

Scripted unit fixtures are engineering controls, not model-autonomy evidence.
Statistical interval calculations were also checked independently against
Statsmodels on 441 count combinations (maximum endpoint difference `2.22e-16`);
Statsmodels is not a runtime dependency. The [finding ledger](finding-ledger.md)
records reproduced defects and corrections to PR #608 and its successor.

The [retained hosted recovery observation](hosted-recovery-observation-v0.1.md)
records agent **0/8**, deterministic **7/8**, and declarative **7/8** bounded
pipeline completions. All 24 original transcripts replay; semantic effectiveness
and the existing-system comparison remain unestablished.
