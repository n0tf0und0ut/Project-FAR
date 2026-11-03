# Investigation implementation finding ledger

Status: Research. Protected baseline `a3f5825ee74af723d660a55e6708ef96e305b156`;
starting PR #608 head `272a203d338877110f232b1c034dd04e8648ee3f`.
Fix commits and final exact-head review/CI are recorded in the successor PR.

| ID | Invariant and reproducer | Disposition and regression evidence |
|---|---|---|
| HIST-608-CRLF | Original transport bytes must survive newline handling; old CLI normalized CRLF. Thread `PRRT_kwDOTH_vCM6y4ONX`. | Historical fix retained; real CRLF file/stdin regression preserved. |
| HIST-608-OPEN | A semantically valid `OPEN` contract must retain successful validation. Thread `PRRT_kwDOTH_vCM6y4ONd`. | Historical fix retained and parity-tested against current verifier. |
| HIST-608-MODEL-200 | Malformed HTTP 200 model output must survive parsing failure. Thread `PRRT_kwDOTH_vCM6y4ONi`. | Historical fix retained; successor also audits failed raw envelopes. |
| HIST-608-TEST-CRLF | Byte regression must use actual newlines. Thread `PRRT_kwDOTH_vCM6y5XSW`. | Historical fixture correction retained; no weakening of production check. |
| HIST-608-SOURCE-200 | Source bytes must be checkpointed before JSON parsing. Thread `PRRT_kwDOTH_vCM6y5XSb`. | Historical source/refetch fix retained and regression-tested. |
| RC608-HTTP-EVIDENCE | HTTP 429, oversized and interrupted responses lost status/body/hash. | Fixed by bounded response reader; distinguish complete-body from retained-prefix hashes; failed source/model envelopes survive. |
| RC608-MODEL-REDIRECT | A local HTTP 302 caused another destination to be requested. | Both legacy model clients refuse redirects; native urllib handler regressions over an in-memory HTTP transport verify the second destination is never requested, with an unguarded positive control. Earlier development also exercised local listeners. |
| RC608-VERIFIER-JOURNAL | Rejected/unavailable verifier attempt was absent from count and checkpoint. | Record input/hash/count before call and rejection/exception afterward; preserve failed native attempts. |
| ENG-SEARCH-CHRONOLOGY | Searching after initial source retrieval produced a saturation observation predating the search receipt. | Discovery chronology covers all source/search receipts; regression reproduces order independently. |
| ENG-STALE-RECHECK | A failed later search recheck could reuse an earlier successful completion timestamp. | Clear completion at every pass start; require a complete pass after final discovery; source and search drift tests fail closed. |
| ENG-BUDGET-PARITY | Deterministic execution ignored the agent's step ceiling. | Shared proposal ceiling; all lanes stop at the same nine-step boundary and complete the ten-step fixture only with sufficient budget. |
| ENG-FUNCTION-TRANSPORT | Example JSON strings were copied as literal tool arguments in actual development runs. | Typed native function schemas with Qwen's Jinja template; original unsuccessful model transcripts retained separately. No fabricated success or controller substitution. |
| ENG-REPEATED-READ | Repeated successful identical reads did not advance discovery and consumed resources. | Log and reject duplicate read/extract/compare requests without another side effect; actual source/interpretation choices stay with model. Rediscovery remains possible after changed context. |
| ENG-OFFLINE-AUDIT | A final seal alone did not validate internal receipt/result/report consistency. | Separate auditor recomputes recursive envelopes, bindings, exact model arguments, counters, native results and aggregation; resealed-corruption tests detect these failures. |

Internal workers shared the filesystem and project context. Their review is
internal code inspection, not external/I2 independence. Automated hosted review,
required branch checks and merge authority remain separate obligations. The
existing #608 machine review summary and its clean prose receipt disagree;
resolved threads alone do not repair that protected metadata. No policy has
been weakened to treat the discrepancy as a clean review.


## Repository convergence on November 3, 2026

Protected-main integration `54fe2358ecd7fd865827e59999097732a7da1486`
preserves original implementation, selections, registrations and failed local
execution history. The original completed hosted artifact is now retained and
replayed as documented in [its observation](hosted-recovery-observation-v0.1.md).
The corrective commit is the commit adding this section.

| ID | Reviewed source / violated invariant | Disposition and reproducer |
| --- | --- | --- |
| ENG-CAMPAIGN-EXPOSURE | Audit of original `7ffb943386d4cc6450417ba472f45ab55b2b6823`; duplicate or missing rows were accepted if surviving transcripts audited. | Fixed in existing campaign auditor: bind every registered task/mode slot exactly once in original order. Rehashed duplicate/missing exposure mutations fail. |
| ENG-CAMPAIGN-CLAIMS | Same source; valid transcript plus fabricated row/summary could report success or invalid cost. | Recompute metrics and summary from raw transcripts; rehashed forged completion, cost and summary tests fail. |
| ENG-CAMPAIGN-IDENTITY | Same source; embedded selection/source identity was not reconciled against retained execution binding. | Bind frozen external selection, source commit/hashes, model, task question/mode/budget and canonical transcript filename. Mutation regressions fail; all original 24 slots pass. |
| ENG-CAMPAIGN-SHADOW | Same source; duplicate ZIP member could shadow original bytes. | Reject duplicate archive names before reading campaign/transcript bytes; hostile-copy regression fails closed. |
| ENG-TRANSPORT-TIME | Same source; `received_at` was recorded before HTTP open/read. | Separate request/completion instants in existing shared bounded reader. Controlled-clock success/timeout tests fail under original behavior; resealed backwards new timing records fail audit. Original timestamps remain unchanged and explicitly limited. |

Existing #614 legacy HTTP confinement/evidence and verifier-journal repairs are
also backported to predecessor #608, with byte-identical implementation and
regression fixtures. That prevents knowingly merging a defective predecessor;
there is still one implementation. The two inherited completed live workflows
are archived byte-for-byte and now run offline maintenance controls.
The original hosted workflow is separately archived and converted to evidence
replay. Neither metadata policy nor protected authority has been weakened.

## Source-bound comparator preparation and native framing correction

**ENG-COMPARATOR-SOURCE:** the registered original Open Deep Research adapter has
no recoverable frozen source binding. It remains BLOCKED_GOVERNANCE. The separate
[FAR-ODR-PREP-001 observation](odr-preparation-v0.1.md) now demonstrates actual
pinned upstream graph invocation through existing read tools using scripted
fixtures, with source drift, policy and restoration regressions. Seven tests pass;
no live comparison, semantic adjudication or competitor score was manufactured.

**HTTP-FRAMING-01:** substantive review of predecessor #608 exact head
`562eb24f007601c0e6a0f9ffb48f953ab8c68338`, comment
[4458991461](https://github.com/n0tf0und0ut/Project-FAR/pull/608#discussion_r4458991461),
reproduced silent short Content-Length acceptance by the native HTTP decoder.
The shared helper now validates declared length and bounded native chunk framing,
retains incomplete decoded prefixes and prevents freezing/verification on the
short source. Native positive controls detect removal of the guard. The full
source, reproducer and disposition appear in the
[predecessor ledger](../uncertain-routing/finding-ledger.md). Original historical
source framing is not retroactively established by this correction.

Final local verification: 191 focused tests collected, 186 passed and five
optional actual-graph tests skipped in the ordinary environment; all seven
preparation tests pass in the isolated pinned graph environment. Original
campaign replay passes 24/24 transcripts, native conformance passes 7/7, and fast
repository health reports 124 passed, zero warnings and zero failures. These
checks establish the stated engineering invariants, not live-model efficacy.
