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

## Latest-pass readiness and shared dispatch preconditions

The next hosted review receipt `PRR_kwDOTH_vCM8AAAABV2HtIw`, submitted
2026-11-03T23:34:58Z, explicitly names reviewed commit `1ab5b8a7e6`:
`1ab5b8a7e690be7665108c51e66516d5eafa6bdd`, tree
`71a14e81af0f65b77666dacd1ba5afbbb0919c57`. All three findings below were read in
full and reproduced on that published tree before correction. The three initial
regression methods each failed, for three independently observed failures.

| Root cause and exact hosted source | Reproducer and correction | Regression and compatibility evidence |
| --- | --- | --- |
| **ENG-LATEST-RECHECK-COMPLETION** — [4461742007](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4461742007), `PRRT_kwDOTH_vCM6zYPdO`, reviewed `1ab5b8a7e690be7665108c51e66516d5eafa6bdd`, audit lines 616–617 | Native Crossref-shaped search receipts support one complete pass. A second pass retrieves all sources but rejects changed search hits. Restoring only the obsolete completion marker before freeze previously yielded a completed, audit-valid pipeline despite the recorded failure. Reconstruct readiness independently of source-record count: every later eligible pass revokes earlier readiness, and only a complete accepted source-and-search pass restores it. Runtime rejection also clears readiness even if full terminal diagnostics were already retained. | `test_failed_later_search_recheck_revokes_earlier_full_completion` now rejects the exact stale-marker mutation. A third genuinely complete pass can replace the failed pass and finish. Frozen or malformed recheck proposals that never begin a new pass preserve the earlier valid completion. Terminal-checkpoint interruption preserves diagnostic receipts without readiness; an actual retry can complete. |
| **ENG-RECHECK-PREAPPEND-CHECKPOINT** — [4461742019](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4461742019), `PRRT_kwDOTH_vCM6zYPdW`, reviewed `1ab5b8a7e690be7665108c51e66516d5eafa6bdd`, audit lines 581–584 | A one-time `OSError` at the first `SOURCE_RECHECK` event leaves the observed receipt journaled but interrupts before append to retained rechecks. `full_script()[:7]` under budget seven correctly fails with zero retained rows; the auditor previously invented one row and rejected coverage. Distinguish observation from state commitment. Progress to a subsequent request/record proves earlier appends; a failed final observation admits only its bounded possible committed prefixes, never readiness. | `test_source_recheck_checkpoint_failure_preserves_preappend_diagnostic_state` now accepts the unchanged genuine failure. Existing pre-HTTP budget, raw-source preparse persistence, post-dispatch effects, corrected retry and original archive controls remain valid. Partial-prefix compatibility cannot authorize freeze because rejected passes never establish completion. |
| **ENG-DISPATCH-PRECONDITIONS** — [4461742023](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4461742023), `PRRT_kwDOTH_vCM6zYPdZ`, reviewed `1ab5b8a7e690be7665108c51e66516d5eafa6bdd`, audit lines 297–299 | Prepend unsupported `execute_shell`; runtime rejects it. Change that rejection to a matching success, decrement rejected calls and reseal: audit previously accepted the impossible operation. Complete inspection also reproduced malformed notes/next-evidence/evidence-ID types, ignored extra arguments, and a shape-invalid rejected retrieval acquiring forged retained source/HTTP effects. Share the authoritative tool-schema validator and frozen/duplicate dispatch guards between execution and replay. Gate accepted outcomes and retained-effect producers; preserve malformed rejected proposals as failures. A distinct pending sentinel permits legitimate rejected JSON null/scalar/list proposals without treating them as missing events. | Unknown forged success and eight coordinated accepted-argument mutations reject. Fifteen malformed/unsupported/type/extra-argument cases are runtime failures with no HTTP reservation or retained outputs and remain audit-valid. A shape-invalid rejected retrieval cannot acquire source effects. Optional comparison alternatives, empty report arguments and actual Unicode `.upper()` relation normalization remain supported. All **142 successful** and **30 rejected** original frozen proposals satisfy the shared static contract; no historical exception or metric change was needed. |

The validator derives schemas from the runtime's existing `function_schema`,
retains documented defaults, rejects unsupported nested discovery fields, and
uses the repository's `Draft202012Validator.iter_errors` API. Native semantic
checks remain in the existing builders and native-plan validator. The correction
introduces no second execution engine and no independent semantic-adequacy claim.

Local source-construction commit:
`195ac1bce1119da28ce9b70106db5b06c2a0a1c7`, tree
`3b80c3c2de6f1323f4d0e5f5fed143a269239580`. This is a local construction identity;
the successor's published head/tree and final hosted review must be recorded in
the PR. The stabilized whole-PR suite passes **255/255**, zero skips, including
the pinned actual-graph preparation controls. All **24 original transcripts**
still replay with unchanged byte-checked campaign metrics. Original counters
remain **141,481**; the separate retained-response lower bound remains **142,571**,
with 29 known and seven unknown attempts. The immutable ZIP, protocols,
selections, scientific source identities and agent 0/8 versus both controls 7/8
remain unchanged. No inference, model trial, GitHub write or gate change was
performed by this corrective construction.

## Canonical test-launch executable boundary

**ENG-CANONICAL-PYTHON-LAUNCHER** — accepted and corrected after the coordinator
reported exact-head `1ab5b8a7e690be7665108c51e66516d5eafa6bdd` hosted failures:
[exact-head assurance job 126275864977](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41739122658/job/126275864977)
and [merge-authority job 126276077671](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41739122724/job/126276077671).
Both commands exited zero but the unchanged tracing policy reported
`FAR-VAL-TRACE-001` for undeclared
`/opt/hostedtoolcache/Python/3.12.15/x64/bin/python3.12` in `tests.canonical` and
`repository.health-full`. The actual native server fixture explicitly resolved
`sys.executable`, converting the admitted Python launcher into its versioned
binary path.

The local before-fix harmless interpreter canary exited zero, while the actual
trace parser and existing runtime policy rejected its constructed resolved
`python3.12` exec path. Native `strace` was installed but ptrace was prohibited
(`PTRACE_TRACEME: Operation not permitted`), so this is explicitly deterministic
parser-canary evidence, not an observed native syscall trace.

The fixture now constructs its command with the existing `sys.executable`
launcher. Its regression runs the real child through a canonical `python3`
symlink to the same interpreter, checks the constructed launcher against the
unchanged trace policy, and retains every executable-file identity, mapped-model,
listener, command and wrong-owner assertion. The occupied-endpoint control also
passes. Neither executable policy nor protected manifests were changed; a
versioned executable remains inadmissible through the original parser control.

## Accepted-operation producer coverage

**ENG-NATIVE-OPERATION-PRODUCER** — hosted review **5761265038**,
[comment 4461967436](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4461967436),
thread `PRRT_kwDOTH_vCM6zYw6S`, reviewed commit
`89a4dc6ef0f480f5eb34abfcafd512e65b3c84d2`, tree
`e78cabcbd7de99015d752a46ec154d8beb23331f`, audit lines 760–761.
Disposition: **fixed**. The exact native-response-shaped scripted reproducer
prepends `verify(candidate_id='nonexistent')` before discovery/freezing. Its real
rejection audits correctly. Replacing that outcome with an accepted verification
and decrementing rejected calls previously left the completed transcript valid,
although the operation had neither native invocation nor evaluation. The new
regression failed before correction, independently of response-shape hashing.

Runtime inspection established that repeat verification is rejected with
`candidate already evaluated`; there is no permitted cached-success path. The
existing frozen-family/candidate selection logic is now a shared pure helper.
Every accepted verification must satisfy those actual preconditions, contain
exactly one native request in its own attempt, bind the candidate and freeze,
and equal one retained evaluation produced by that attempt. Its full accepted
tool result is the native observation; no nonexistent observation marker is
invented. Request-to-result native recomputation and evaluation-to-request
coverage remain active in the opposite direction. Genuine failed invocations
can have no result, and a post-dispatch rejected invocation can retain a bound
diagnostic evaluation without becoming successful.

Regressions cover the exact prefreeze nonexistent candidate; an existing name
before freeze; a nonexistent frozen-family member; repeat verification after
evaluation; missing/duplicated own requests; missing retained evaluation; and a
failed invocation falsely claiming a later retry's evaluation. Existing transient
native-failure retry and post-dispatch budget-rejection positives still audit.

The required bounded producer inspection covered every supported operation:

| Accepted operation | Reconstructed producer and prerequisite boundary |
| --- | --- |
| `retrieve` | Actual URL/request/transport observation, runtime-allocated source ID, retained bytes/projection and complete returned view. |
| `search` | Actual query/provider/request/observation, native metadata projection where applicable, retained search row and returned view. |
| `extract` | Then-available source, exact quotation/coordinates, actual relation/claim and allocated retained evidence row. |
| `inspect` | Then-available source projection and shared bounded inspection guards/output. |
| `compare` | Previously produced evidence, publisher projection groups, alternatives, fixed assurance strings and retained comparison. |
| `discover` | Then-available source/evidence/comparison/search context, actual arguments, shared builder and exact discovery snapshot. |
| `recheck` | Ordered source/search request-bound observations, actually retained original projections, committed diagnostic prefix and latest accepted full-pass readiness. |
| `freeze` | Proposal-derived draft, latest complete accepted pass and exact canonical freeze. |
| `verify` | Existing fresh frozen candidate, one own native request, exact native observation/evaluation and bidirectional coverage. |
| `verify_far` | Then-available raw source, actual source argument, existing router recomputation and retained result inventory. |
| `finish` | Earlier native evaluations, shared complete-family/report prerequisites, fixed nonclaims and retained final report. |

This inspection reproduced two additional instances of deterministic output/input
coverage, both also accepted by the exact published 89a4 auditor in read-only
baseline execution:

- **ENG-SOURCE-ALLOCATION:** renaming a one-step retained source, projection and
  accepted result from `src.1` to `src.0` passed despite the allocator always
  starting at one. Enforce the consecutive runtime ID sequence. This proves a
  mechanical identity defect; no separate semantic or metric impact is claimed.
- **ENG-RECHECK-ORIGINAL-PROJECTION:** a third source retained only as raw bytes
  after a one-time preparse checkpoint failure has no original projection. Real
  recheck fails after its actual HTTP observation. Forging the impossible third
  source-recheck event, retained row and accepted outcome previously passed.
  Require each source-recheck observation to use its actually retained original
  projection. The original raw-only failed retrieval/recheck remains valid.

A complete native-shaped fixture exercises all eleven tools; adding an invented
field to each accepted result independently rejects. The all-tool coverage set
is checked against the supported tool set. This is a bounded mechanical
regression matrix, not proof of arbitrary semantic correctness or external
execution authentication.

Local source-construction identity:
`a5e50483a015db1e6a5f9c37f69c3404c4357b88`, tree
`8d52644e17a3d90a6e0f17cd8e99ef5cb5626620`. It is not presumed to be a published
GitHub commit. Whole-PR verification passes **261/261**, zero skips, including
pinned actual-graph preparation. Original **24/24** transcript replay, frozen
metrics and the separately labelled **141,481** legacy counter versus **142,571**
known-response lower bound with seven unknown attempts remain unchanged. No new
inference, frozen-evidence edit, executable-policy change or GitHub write was
performed. Final published head/tree, substantive review and hosted gates remain
separate obligations recorded in the PR.

Final internal review of local construction `a5e50483` also permuted the
consecutive source IDs `src.1` and `src.2` consistently across a two-retrieval
state and its returned IDs. The set-only allocator check still accepted that
impossible producing order. The expanded regression failed before correction.
IDs now follow strictly increasing retained-retrieval attempt indices as well
as the exact consecutive allocator sequence. The repeated-identical-failure
receipt and canonical JSON ordering positive remains valid. This completes the
same **ENG-SOURCE-ALLOCATION** root cause without claiming a separate scientific
or metric effect. The successor local source-construction identity is
`f32bc1b7c232cdc295ed14fd6fc9b0e63076c410`, tree
`d246b5649254f99002865fd1877ff4f8089c935b`; publication identity remains separate.

## November 5 review findings: accepted-outcome durability and source metadata

Reviewed head: `e19f78a12c33bc605720e74fa3143c20ecf4ece0`.
Protected-main integration base: `c7456b469f9dfe88b92d0fc7a211e5c9ed64de61`.
Corrective implementation commit: `37cfd0f646139fb8136b8ac5a76b4ac428f3a98f`.
These are post-execution engineering corrections; frozen investigations and reported
model outcomes are unchanged. The test suite proves the encoded journal/transport
invariants at its fixture boundary, not the scientific truth of sources or autonomous
investigation reliability.

| Root cause and original review | Observed invariant violation | Disposition and regression |
| --- | --- | --- |
| **ENG-ACCEPTED-CHECKPOINT-DURABILITY**, thread `PRRT_kwDOTH_vCM6zZGl9`, comment [4462111092](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4462111092), reviewed `e19f78a1`, `tools/far_investigation_engine.py:459` | A one-time OSError from saving an already-appended `TOOL_RESULT` caused both accepted and rejected outcomes for one proposal. The apparent completed transcript then failed the offline audit. | **Fixed in `37cfd0f`**. Retry persistence of the existing accepted journal without adding a rejection. Persistent failure raises a distinct nonrecoverable `CheckpointPersistenceError` and does not return a false completion. `test_transient_tool_result_checkpoint_failure_keeps_one_accepted_outcome` and `test_persistent_tool_result_checkpoint_failure_cannot_claim_completion` exercise complete native-function-shaped fixtures; final hosted exact-head verification is separate. |
| **ENG-NATIVE-PARSER-METADATA**, thread `PRRT_kwDOTH_vCM6zZGmA`, comment [4462111097](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4462111097), reviewed `e19f78a1`, `tools/far_investigation_audit.py:106` | Native transport headers could be changed from plain text to HTML while receipt parser metadata and evidence stayed unchanged, and a self-consistently resealed trace still passed audit. HTML hiding of `<script>` made the error consequential to extracted quotations. | **Fixed in `37cfd0f`**. Reconstruct receipt content-type, content-encoding, final URL and HTTP status from retained native transport, while retaining legacy receipts without native transport at their declared evidence scope. `test_native_receipt_content_type_and_encoding_bind_to_transport` mutates complete native fixture receipts and seals. |

The branch remains a draft successor to #608. Current required checks,
independent final-head review, unresolved-thread closure and protected-repin
authorization must be verified separately before any readiness promotion.

## November 6 source, framing, budget and journal convergence

These maintenance changes preserve all original raw outputs, source manifests, frozen campaign inputs and negative results. This is engineering assurance at the retained evidence and controlled-fixture boundary. It does not authenticate a self-signed transcript or demonstrate autonomous scientific reliability.

| Root cause and original review | Reproduction and final correction |
| --- | --- |
| **ENG-NATIVE-FRAMING-BINDING**, [4493930574](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4493930574), reviewed `0a6d4ed776f448b4a40688bfe55317723836d00b` | The existing successor corrected a declared Content-Length/body mismatch. Further falsification of `ebdf992f8fc7ed9f5c14dff1e866cc13a5ba1e54` exposed five passing resealed impossibilities: header/list disagreement, omitted explicit length list, ambiguous Content-Length plus chunked transfer, unsupported transfer coding, and omitted explicit transfer list. The new regression failed in all five cases before correction. Accepted native transports now require header/list agreement, exact declared byte length and supported unambiguous framing. Original envelopes lacking list fields derive them from their retained headers, so the original 24 transcripts remain replayable without rewriting them. The auditor validates retained metadata; it cannot reconstruct missing wire chunk delimiters or externally authenticate the server. |
| **ENG-REGISTERED-SOURCE-EXPOSURE**, [4493930585](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4493930585), reviewed `0a6d4ed7` | Already corrected in ancestor `51bd43ea`: campaign audit binds transcript seeds to registered task source hints and allowed hosts to the selection-derived policy. Existing regressions cover off-registration source hints and host exposure. The original registered-source 24-transcript replay remains valid. |
| **ENG-TOKEN-DISPATCH-ELIGIBILITY**, [4493930594](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4493930594), reviewed `0a6d4ed7` | Existing successor correction rejects later model/tool transitions after cumulative observed usage exhausts the token budget. The final response itself may legitimately exhaust the budget and remain retained as failure evidence. Regression `test_no_tools_can_follow_exhausted_model_budget` is included explicitly in the hosted focused workflow. |
| **HTTP-NONCHUNK-PREFIX-01**, [4494208086](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4494208086), reviewed `ebdf992f8fc7ed9f5c14dff1e866cc13a5ba1e54` | Real native `HTTPResponse` over an in-memory buffered raw stream reproduced eight lost-prefix cases: Content-Length/connection-close framing, timeout/reset and default/explicit chunk sizes. All eight failed before correction. Native nonchunked bodies now use bounded incremental `read1`; every observed prefix is checkpointed before another blocking read. Incomplete bodies retain exact prefix bytes/hash and cannot become successful sources/model responses. The same defect was reproduced and corrected in predecessor #608 at `83f8468e17f65b99231e0870ca35e1799897c5fe`; this successor retains that commit as an integration parent. |
| **ENG-PROPOSAL-CHECKPOINT-OUTCOME**, [4494208092](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4494208092), reviewed `ebdf992f8fc7ed9f5c14dff1e866cc13a5ba1e54` | Four injected one-time proposal checkpoint failures (retrieve/discover/freeze/finish) reproduced unmatched proposals before correction. Proposal journaling now participates in the existing pre-dispatch rejection path. Each failed checkpoint records one undispatched rejection, permits a legitimate retry and retains an auditable complete fixture with unchanged four HTTP calls and one native evaluation. Persistent storage failure cannot establish durable completion. |

The focused hosted workflow now explicitly includes both review-regression and usage modules. Original agent **0/8** versus deterministic **7/8** and declarative **7/8**, the **141,481** legacy counter versus **142,571** known-response lower bound and seven unknown timeout attempts remain unchanged. No new inference or scientific experiment was run. #608 remains open as predecessor; the original ODR experiment remains BLOCKED_GOVERNANCE and independent semantic/reference and custodian obligations are not discharged by these fixture tests. These missing experimental assurances do not prohibit publication of the bounded Research implementation and negative record. Exact final-head review, required hosted checks, owner signing authorization and protected integration obligations remain separate.

### Partial-chunk follow-up after predecessor review

[Review comment 4494361655](https://github.com/n0tf0und0ut/Project-FAR/pull/608#discussion_r4494361655) on predecessor `83f8468e17f65b99231e0870ca35e1799897c5fe` exposed a distinct interrupted-byte location: inside a declared chunk body. The shared observer read that body portion as an aggregate, losing a buffered `abc` on timeout/reset. Two newly added native buffered controls failed before correction; oversize controls already passed. The observer now retains each incremental body read before satisfying the exact-size decoder input, preserving framing checks and retention bounds. Predecessor correction `593bddfde86ec55ddf937a4d861813318b2971d1` is retained as a development integration parent. The successor passes **273 focused tests run (268 passed, five optional upstream skips)**, **24/24** frozen transcript/source-binding replays and **7/7** native conformance cases; predecessor passes **56** focused tests. Frozen evidence and negative findings are unchanged. This supersedes the earlier stabilized candidate for final-head review and hosted gates.

### Recorded retrieval-policy byte ceiling

**ENG-SOURCE-BYTE-CEILING**, [review comment 4494410326](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4494410326), reviewed `e53e3539ed194877b3698f3f453d90ec77687fab`: lowering both policy copies to one byte and resealing still allowed successful 91-byte/78-byte sources. Five invalid ceiling controls (one below the largest source, one byte, Boolean, zero and above the runtime maximum) reproduced acceptance before correction. The auditor now applies the existing pure RetrievalPolicy constructor and compares each successful receipt's exact retained-byte count with the recorded ceiling. No DNS or network is invoked. The exact-largest-source ceiling remains a positive control. The duplicate partial-chunk finding [4494410314](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4494410314) is already corrected by ancestor `e2de3fe6765537497932846fed51016a01d6ce7c`.

Merge eligibility and experiment authorization are distinct. The registration and source-bound ODR preparation forbid replacing missing historical evidence or promoting unsupported efficacy; they do not require the Research implementation and preserved negative record to stay draft. The earlier statement tying draft status to these scientific gaps was an overbroad interpretation. Future ODR efficacy work remains BLOCKED_GOVERNANCE pending its required prospective lock and evidence; engineering publication may converge under ordinary exact-head independent-review and protected-check rules. No missing scientific result is treated as a code defect or fabricated success.

### Shared offline clone-fixture isolation

[Hosted merge-authority job128001115478](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/42246514987/job/128001115478) rejected a real DNS lookup from the baseline promotion/corpus regression although its commands exited zero. Native resolver interception identifies the shared fixture's `git clone --quiet --shared`: its first reflog was written before the fixture configured identity, causing implicit Git email discovery to resolve the runner hostname. The correction supplies command-scoped identity before clone and asserts the actual initial reflog name/email. The new assertion fails before correction; both corpus/promotion tests pass after correction under isolated global/system Git config and a blocking native resolver spy. The original corpus forgery assertions remain active. This shared fixture-only correction does not alter engine behavior, protected trace/network policy, frozen source bindings or scientific evidence. The predecessor records the exact before/after diagnostic evidence and is retained in development ancestry.
