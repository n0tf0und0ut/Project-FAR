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
| RC608-MODEL-REDIRECT | A local HTTP 302 caused another destination to be requested. | Both legacy model clients refuse redirects; actual local two-listener regressions verify the destination is never requested. |
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
