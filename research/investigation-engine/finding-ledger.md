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

## Exact-head review correction on November 3, 2026

Reviewed PR #614 head: `1caca4e019ed631812aaf1cf0b076e6684fdb401`.
Protected main and merge base: `c7456b469f9dfe88b92d0fc7a211e5c9ed64de61`.
Local construction identity for the implementation/regression fix:
`0b82c18564e23c97b1589f833f2f3d7a1c17c6b9`.
Local history-preserving predecessor integration identity:
`b7eacd0695c1a58560c7b18f1b624e1d7d9409d3` incorporates final PR #608 head
`3d33b42810a92b8e796c8ecb8ddca4d799996423`; it retains the predecessor's
source/model timeout/reset checkpoints, native framing controls and ledger.
These local construction commits are not asserted to be GitHub-reachable.
The [successor PR](https://github.com/n0tf0und0ut/Project-FAR/pull/614) records
the published corrective head, tested tree and thread-closure evidence; an API
publication can preserve the exact tested tree under a different commit identity.
The shared reader gains optional operator-opener, bounded progressive-read and
checkpoint parameters for the general source path; its framing and interrupted
chunk-prefix checks remain shared with the predecessor clients.

| Root cause / source | Violated invariant and observed reproducer | Disposition / regression |
| --- | --- | --- |
| **ENG-SOURCE-FRAMING** — thread `PRRT_kwDOTH_vCM6zSj2V`, [4459293320](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4459293320), `tools/far_investigation_retrieval.py:207–208` | A native response declaring 100 bytes but sending a valid 15-byte prefix was accepted. Native malformed chunk separators and unterminated trailers were also accepted; timeout/reset prefixes were lost. Three framing cases and two interrupted-prefix cases failed before correction. | **Fixed.** Route the general source and public-search paths through the existing hardened reader, preserving forced proxy policy and failure prefixes. `RetrievalTests.test_native_short_and_malformed_chunk_framing_cannot_support_evidence`, complete-length/chunk positive controls, native timeout/reset checkpoints and a valid-JSON-prefix public-search regression pass. |
| **ENG-SOURCE-TRANSPORT-BINDING** — thread `PRRT_kwDOTH_vCM6zSj2b`, [4459293330](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4459293330), `tools/far_investigation_audit.py:224–226` | Adding an allowed-host receipt to failed, unfrozen retained `H201-agent.json` and resealing previously passed audit, despite no retrieval observation. Removing/changing a parse-failure source observation or its HTTP request also escaped detection. | **Fixed.** Every retained source consumes one exact matching retrieval-attempt observation bound to both proposal URL and HTTP reservation; successful tool results are not required after parsing fails. `test_resealed_orphan_source_is_rejected_even_without_intake`, `test_parse_failure_source_requires_its_exact_retrieval_observation` and the original-H201 hostile-copy regression pass. Unmodified failed histories remain valid. |
| **ENG-EXTRACTION-PROPOSAL** — thread `PRRT_kwDOTH_vCM6zSj2i`, [4459293341](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4459293341), `tools/far_investigation_audit.py:235–236` | Resealing both extraction-result and final-state relation copies as `CONTRADICT` while the actual/model proposals still requested `support` passed audit with zero substitutions. Changing both claim copies also passed. | **Fixed.** Reconstruct every successful extraction from the actual proposal, normalized relation, verified source/quote binding and fixed assurance label, then compare both recorded outputs. `test_resealed_extraction_copies_cannot_override_requested_arguments` rejects relation/claim/source mutations. |
| **ENG-SERVER-OWNERSHIP** — thread `PRRT_kwDOTH_vCM6zSj2r`, [4459293355](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4459293355), `tools/far_investigation_campaign.py:211–213` | A fixture listener already on 8085 plus a requested executable exiting 43 and an unrelated successful health response produced an `EXECUTED` campaign before correction. Requested file hashes did not identify the process serving responses. | **Fixed.** Reject occupied startup endpoints; require live direct-child command/executable/model-mapping identity and exclusive kernel-listener ownership at readiness and before/after every model response. A real local fixture process (no inference) passes the positive control; occupied port, wrong command/executable/model/owner, dead child and response-time owner changes fail. Linux `/proc` and model-file mapping are required; unavailable evidence fails closed. |
| **ENG-FINISH-TRANSACTION** — thread `PRRT_kwDOTH_vCM6zSj2y`, [4459293371](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4459293371), `tools/far_investigation_engine.py:462–463` | Advancing the controlled clock from 0 to .3 seconds during finish under a .2-second budget yielded rejected finish plus completed status. A separate delayed finish journal escaped the initial narrow correction in all three lanes; its three failures were also reproduced. | **Fixed.** Construct the report without completion side effects, commit completion only after accepted dispatch/budget/result, and fail completion when the final measured time/token budget is exceeded. `test_finish_is_not_committed_when_postdispatch_budget_expires` preserves no rejected report; `test_completion_journal_cost_cannot_escape_the_final_budget_in_any_lane` prevents scored completion after journal delay while preserving accepted diagnostic evidence. Both audit validly as failures. |
| **ENG-EMPTY-WITNESS** — thread `PRRT_kwDOTH_vCM6zSj26`, [4459293384](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4459293384), `tools/far_investigation_campaign.py:56` | A complete integrity-valid truth-table investigation of `False` from no premises returned `REFUTED` with counterexample `{}` but reported zero witnesses. | **Fixed.** Count `counterexample is not None`. `test_empty_counterexample_valuation_counts_as_a_native_witness` executes the full frozen/native pipeline and reports one witness. |

Verification of the stabilized code, before final documentation-only commit:
**208/208 focused tests pass**, with zero skips, in an isolated environment with
the pinned actual Open Deep Research source and preparation dependencies. The
seven preparation tests comprise five actual-graph tests and two boundary tests;
the positive actual-graph fixture forbids network connections. Offline
archive replay remains valid for all 24 original transcripts; native current
conformance passes 7/7. Before predecessor integration, the ordinary environment
collected 207 tests with only its five pre-existing optional actual-graph skips;
the pinned environment passed all 207. The pre-integration `make health-fast`
run exits zero. After integration, the separately executed focused suite and
`python tools/repo_health_check.py --fast --skip-canonical-tests` pass; the latter
reports **124 passed, zero warnings and zero failures**. Final-head hosted review, protected checks and
merge authorization remain separate, outstanding obligations.

All six hosted findings are accepted, distinct root causes with reproduced
counterexamples. No frozen archive, registration, selection, protocol, result or
source binding was rewritten. Original agent **0/8**, deterministic **7/8** and
declarative **7/8** completions remain the reported bounded result. No new scored
model run, competitor observation, external independence, semantic correctness,
superiority, accepted-methodology change or production promotion is claimed.

## Internal review follow-up before publication

Read-only internal reviewer `/root/review_rebuilt_evidence` inspected local
candidate `b94deb17a4259b451d204a2cf748f2acf324026e`; the coordinator independently
reproduced the reported comparison, resource, orphan-evidence and transport
counterexamples. This is internal code inspection on a shared host, without
external/I2 independence. The local corrective construction identity is
`6c0da35def84f3073e232b88ad10059b7c971f1a`; published head/tree evidence belongs
in the PR linked above and is not inferred from that local commit identity.

| Root cause | Reproducer and correction | Verification |
| --- | --- | --- |
| **ENG-COMPARISON-PROPOSAL** | Changing both final comparison and matching tool-result `asserted_conflict` to false preserved a valid audit and changed conflict count 1 → 0 despite unchanged support/contradiction evidence and proposals. Forged publisher groups, alternatives, evidence IDs and assurance strings had the same mechanism. An orphan final evidence row or duplicated comparison also escaped the one-way output check. Reconstruct comparison outputs from the actual proposal and previously produced quote-bound evidence, then require exact ordered comparison and evidence-inventory coverage. Preserve legitimate effects retained before post-dispatch rejection, while excluding frozen/duplicate pre-dispatch rejections. Neighboring deterministic retrieve/inspect views and FAR-dispatch outputs receive the same proposal-derived binding and applicable inventory coverage. | `test_resealed_comparison_copies_are_reconstructed_from_the_proposal`, `test_orphan_and_duplicate_final_evidence_and_comparisons_are_rejected`, `test_retrieve_and_inspect_results_cannot_change_the_source_projection` and `test_far_verification_results_and_final_inventory_are_bound_to_dispatch` reject mutations. An extra valid extraction and both extraction/comparison effects retained after budget rejection remain auditable. |
| **ENG-RESOURCE-SCALARS** | Setting `elapsed_seconds=-10` and resealing passed audit and exported negative time. Boolean elapsed, nonintegral or oversized budget fields, and completed elapsed exactly at the exhausted limit were also accepted. Require finite nonnegative numeric elapsed, exact runtime budget fields/types/positive bounds, and strict remaining completion budgets. This checks recorded scalars only; it does not invent unrecorded wall-clock measurements or authenticate elapsed time. | `test_elapsed_and_budget_scalars_have_runtime_types_bounds_and_completion_limits` rejects all nine negative/boundary/type mutations. Existing valid completion and over-budget failure controls pass. |
| **ENG-SOURCE-FRAMING**, offline coherence extension | A completed fixture using the real shared retrieval reader stayed audit-valid after every successful receipt's transport was changed to incomplete, prefix-only and `ContentLengthMismatch`. Accepted model proposals had the same optional-envelope coherence gap. Where a transport envelope exists, require complete HTTP 200, untruncated full-body scope, no transport/framing error, and exact retained body/hash/count agreement with the accepted observation. Frozen legacy receipts lacking this envelope remain supported; no historical framing evidence is fabricated. | The real-reader successful-source positive control passes; `test_successful_receipts_cannot_contradict_their_optional_transport` rejects the recursively resealed contradiction. `test_accepted_model_proposal_requires_a_coherent_optional_transport` passes its complete positive control and rejects incomplete accepted model transport. Original legacy archive replay remains 24/24. |
| **ENG-CAMPAIGN-FIXTURE-LOCK** | Two simultaneous invocations of the real-child/occupied-port tests both failed: one bind raised `EADDRINUSE`, and the other child could not emit `READY`. Hosted canonical and health suites can share the production test endpoint. A cross-process POSIX test lock serializes these two fixed-port fixtures; the actual native listener/process ownership checks remain active. | Four simultaneous invocations pass, eight native fixture tests total. No test is skipped and no ownership assertion is replaced with a mock. |

Before correction, the first five new hostile audit methods produced **20
assertion failures**. The stabilized focused suite now passes **216/216**, zero
skips, including the pinned actual-graph preparation controls and all preserved
predecessor regressions. The real-child fixture invokes no model inference.
All original archives, frozen protocols, selections, results and their scientific
source identities remain unchanged. Final independent review and hosted gates
must cover the published candidate separately.

## Temporal source replay correction after candidate publication

**ENG-TEMPORAL-SOURCE-REPLAY.** The coordinator reproduced a false rejection on
published candidate `2fbf5ddb05903ed18b1a670903f2cb49ed1db396`, tested tree
`8f9cdc1298ad9adbaa3017dd78eca1247145a2ee`: prepend the first extraction proposal
from `full_script()` to the unchanged script. The early extraction correctly
fails because `src.1` has not been retrieved. The later corrected pipeline
completes with one rejection, but the auditor used the final source inventory
to attribute the legitimate later `ev.1` to the earlier failed call. That shifted
the reconstructed evidence IDs and falsely rejected the valid completed trace.
An early rejected FAR dispatch followed by a valid retry had the same mechanism.
Conversely, moving a successful extraction, inspection or FAR dispatch before its
source retrieval escaped detection when hashes and incidental chronology were
resealed. These two new methods produced five failing subcases before correction.

Disposition: **fixed** by recording each retained source's actual producing
retrieval-attempt index and reconstructing source-dependent operations with only
the sources and parsed projections available at that attempt. A successful
retrieval result must name the source produced by that exact attempt. Source
bytes retained before a parser or post-dispatch failure remain available after
that attempt; missing projections do not become available merely because raw
bytes exist. Retention no longer borrows from later final-state outputs.

The same source-order invariant exposed one additional reproduced serialization
failure: ten identical retained failure receipts, a FAR read of `src.2` after its
second retrieval, and canonical JSON sorting caused `src.10` to be assigned
before `src.2`. Binding now follows the runtime's numeric source-allocation order
and the explicit producing index of successful retrieval results. Canonical
serialization preserves the same availability relation.

Regressions cover rejected early extract/inspect/FAR calls followed by corrected
retries, hostile successful outputs moved before source creation, parser-failure
and post-dispatch source retention, and repeated identical receipts across
canonical JSON serialization. The unchanged archive, protocol, selection and
negative study results remain preserved. No new live model/source observation
or scientific assurance claim is introduced. The successor's published head and
tested tree must be recorded in the PR; local construction identities remain
separate from API publication identities.

Local source-construction commits are
`1f998471cfba6e0b31522e285df258354cf859e9` and
`9fb1ff4762cf94812d445f805ae9abce883bf6e2`. The four added regression methods in
`tests/test_far_investigation_audit.py` cover rejected-source retries, successful
future-source mutations, retained failure sources and identical-receipt
serialization. Final verification passes **220/220 focused tests**, zero skips,
with the pinned preparation environment; all **24 original transcripts** replay.
The current fast health checks excluding the separately exercised test suite
report **124 passed, zero warnings and zero failures**.

## Ordered producer and failed-usage correction after hosted follow-up

The five hosted findings below belong to review **5760546824**, whose review
receipt names actual reviewed commit
`2fbf5ddb05903ed18b1a670903f2cb49ed1db396`. The coordinator verified its REST
`commit_id` and each comment's `original_commit_id` against that source; the
receipt independently states `2fbf5ddb05`. GitHub remapped the current comment
positions to `f270539e6b27198623f7a97fa113db6a3787db4c`, while the machine summary
named that newer head. Those are distinct provenance facts. Every reported
counterexample was reproduced on current published **f270539e6b27198623f7a97fa113db6a3787db4c**,
tree `248639e354ff0422e3cf5651ffd8f3282c0d52bb`; no finding was dismissed because
the service's reviewed-head labels disagreed.

The common architectural failure was incomplete producer reconstruction: several
outputs had only copy-to-copy or one-way bindings, and accepted tool results were
incorrectly treated as the only possible retained effects. The correction reuses
the runtime's pure discovery, bounded-inspection, native-search and report
builders plus the existing canonical intake compiler. It adds ordered discovery,
terminal-recheck and freeze lineage and complete retained-output coverage; it
does not introduce another execution engine or an independent semantic oracle.

| Root cause and hosted source | Reproducer and correction | Defect-detecting verification |
| --- | --- | --- |
| **ENG-DISCOVERY-PROPOSAL** — [4461345589](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4461345589), `PRRT_kwDOTH_vCM6zXVJ-`, actual reviewed `2fbf5ddb05903ed18b1a670903f2cb49ed1db396`, original audit lines 387–390 | Change both discover proposals and retained fixture response to request `2 + 2 == 2`, retaining the `2 + 2 == 4` snapshot/family. Audit previously accepted the substituted contract. Rebuild the complete discovery from actual arguments and then-available sources, evidence, comparisons and searches. Bind terminal recheck and canonical freezing to that reconstructed draft, including assumptions and missing evidence. | `test_discovery_request_cannot_silently_select_a_different_native_contract` failed before correction and now rejects. Early discovery/freeze failures followed by corrected retries remain valid. Provenance rows are reconstructed by unique JSON path while preserving original path-list enumeration across canonical object-key sorting; the 12-evidence serialization control and 24 frozen transcripts pass. |
| **ENG-TERMINAL-TRANSPORT-BINDING**, extension of the source producer family — [4461345595](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4461345595), `PRRT_kwDOTH_vCM6zXVKD`, actual reviewed `2fbf5ddb05903ed18b1a670903f2cb49ed1db396`, original audit lines 211–216 | Replace terminal HTTP observations with valid receipts for changed text, retaining successful unchanged recheck records. Audit previously accepted contradictory transport evidence. Each source record now consumes its exact request-bound observation in the producing recheck attempt. Source/search order, complete stability passes, search requests/results/receipts and native metadata projection are bound likewise; final inventories require producers. A failed recheck clears an earlier pass even if parsing fails before a new source record exists. | `test_source_recheck_must_consume_its_exact_http_observation` failed before correction. Native-search coordinated title substitution, changed recheck observation, orphan result and altered request query all reject. Unchanged native/injected adapter controls and retained source/search failure cases pass. |
| **ENG-FINISH-REPORT-PROPOSAL** — [4461345606](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4461345606), `PRRT_kwDOTH_vCM6zXVKJ`, actual reviewed `2fbf5ddb05903ed18b1a670903f2cb49ed1db396`, original audit lines 367–368 | Change both report copies' analyst notes, next evidence or scope to a universal/independent-verification claim. These escaped copy equality. Reconstruct the whole report from finish arguments, proposal-derived missing evidence, canonical aggregation, retained native records and every fixed assurance/nonclaim string. Require an accepted finish producer for a retained report. | `test_finish_entire_report_is_derived_from_the_actual_proposal` reproduced six escaping field mutations. All reject; legitimate changed notes/next-evidence arguments pass. An otherwise coherent report attached to a failed execution without finish is rejected. |
| **ENG-FAILED-MODEL-USAGE** — [4461345609](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4461345609), `PRRT_kwDOTH_vCM6zXVKK`, actual reviewed `2fbf5ddb05903ed18b1a670903f2cb49ed1db396`, original engine lines 615–616 | On published f270, controlled complete 1,234-token responses recorded 1,234 tokens for one call but zero for two rejected calls. Credit validated response telemetry once per model attempt at observation time, independently of action acceptance. Reject changed/disappearing validated telemetry and bind final envelopes to their ordered attempts. Audit the new explicit accounting rule separately from legacy accepted-proposal counters. | The exact one/two-call runtime control now records 1,234 in both cases without counting duplicate checkpoints. Zeroed new counters reject. Six raw-usage controls cover invalid telemetry, framing failures, repeated copies and the original archive. Its untouched stored counter remains **141,481**; the separate [raw usage correction](raw-usage-correction-v1.json) reports **142,571 known retained-response tokens**, 29 known attempts and seven unknown timeout attempts. H205 alone contributes the omitted 1,090 (1,005 prompt + 85 completion). Neither value is verified total consumption or billed cost. Legacy integrity validity checks its historical emitted counter, not resource completeness; the audit explicitly exposes both scopes. |
| **ENG-REJECTED-NATIVE-EFFECTS** — [4461345619](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4461345619), `PRRT_kwDOTH_vCM6zXVKN`, actual reviewed `2fbf5ddb05903ed18b1a670903f2cb49ed1db396`, original engine lines 445–446 | Advance the controlled clock to 0.3 seconds immediately after verify dispatch under a 0.2-second budget. Runtime correctly fails, retains one native evaluation, and previously fails audit because no accepted result exists. Bind each retained evaluation's complete record to its exact native request interval and recomputed result, whether the post-dispatch outcome was accepted or rejected. Count retained rejected diagnostics separately from successful outcomes. | `test_postdispatch_native_budget_failure_retains_evaluation_without_success` failed before correction and now passes with status `FAILED_OR_INCOMPLETE`, no accepted verify outcome and one retained diagnostic. The same post-dispatch control exposed freeze's accepted-only producer assumption; discover/recheck/freeze/search/FAR-dispatch retention now all audit without completion promotion. The existing transient native failure followed by a successful retry still passes. |

Before correction, the first four new audit methods produced **nine assertion
failures**; the independent baseline execution separately demonstrated the
1,234-versus-zero usage defect. Inspection of the remaining deterministic views
also reproduced a coordinated Boolean inspect-offset mutation accepted despite
the runtime's exact-integer guard. Runtime and audit now share that guarded
builder; `test_inspection_reconstruction_preserves_runtime_scalar_guards` rejects
the original mutation. Corrected early retries, failed recheck clearing and
canonical serialization supply positive controls against over-rejection.

Local source-construction commit:
`7d2580d387d0d32b11ed24b8113e1c22e5120de3`. This is an unpublished construction
identity; published corrective head/tree and final review belong in the linked
PR. The stabilized whole-PR focused suite passes **238/238**, zero skips, including
the pinned actual-graph preparation tests. The complete original archive replays
**24/24**; its ZIP remains SHA-256
`ac45229fda1e7a38fe23b5127cfd361fc938601bc5b6db94bd5d9a95268473e9`.
No frozen protocol, selection, transcript, campaign row/summary, scientific source
identity or negative result is rewritten. Agent 0/8 and both controls 7/8 remain
the original result; no new model-scored run was performed.

### Final producer-family stabilization

Internal read-only inspection of local construction `7d2580d3` exposed additional
instances of the same ordered-producer invariant before publication. Each was
executed and regression-tested rather than treated as a speculative concern:

- A failed search with an identical observation followed by an accepted retry
  borrowed the later retained row. Controlled first-attempt interruptions of
  extraction, discovery and FAR dispatch showed the same mechanism. Reserve
  accepted producing indices before matching rejected diagnostics across all
  these inventories; earlier failures cannot consume later accepted outputs.
- Moving finish before native verification, while consistently reordering model
  envelopes and retained timestamps, still borrowed final evaluations. Finish
  now receives only earlier produced evaluations and the shared report builder's
  complete frozen-family prerequisites. The original coordinated mutation rejects.
- An orphan projection was accepted. Require each present projection's exact
  source producer and deterministic value, and require projections for accepted
  retrievals. Preserve legitimate absence when a one-time persistence failure
  interrupts the explicit raw-source checkpoint before parsing. Inferring that
  every parseable retained receipt had already produced a projection was itself
  reproduced as a false rejection and corrected.
- A second recheck clears an earlier stability pass before its first HTTP budget
  check. A controlled budget expiry at its proposal checkpoint produced no new
  HTTP request, but legitimately retained an empty pass. Reconstruct the reset
  at eligible dispatch, without resetting on frozen/invalid proposals.
- A one-time `DISCOVERY_INVALIDATED` checkpoint failure left an obsolete draft
  usable after new evidence had already been retained; the runtime could finish
  with that stale draft. Clear intake and stability state before journaling the
  invalidation. The failed execution now remains incomplete; an explicit new
  discovery followed by recheck/freeze/evaluation completes and audits correctly.

The seven additional regression methods retain these exact hostile/positive
controls, including both corrected and uncorrected invalidation paths. The
successor local source-construction identity is
`2364c3e7f4dcb6cc757f485b67b805f420674208`, tree
`5a9653b7c36e71d5d5e982971a22332b95e7b036`. These remain local construction
identities, not presumed GitHub publication commits. Its whole-PR suite passes
**245/245**, zero skips; native conformance passes **7/7** and the original archive
remains **24/24**. A separate internal worker re-executed all eight reported
producer edge controls on the corrected bytes and confirmed the intended
accept/reject outcomes. This is shared-host engineering review, not external
scientific independence; final published-head review and protected gates remain
separate obligations.
