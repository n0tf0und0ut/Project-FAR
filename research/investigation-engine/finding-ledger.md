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

## November 8 aggregate transcript archive admission

**ENG-CAMPAIGN-RECORDING-BOUNDS** — [review comment 4507127065](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4507127065), thread `PRRT_kwDOTH_vCM61CzKB`, reviewed head `f797f5042839d87558a46f8424091cb9e4c29dfb`, campaign admission lines 206–207. Invariant: campaign execution and offline archive admission must use compatible recording budgets; permitted individual source sizes alone do not bound the serialized multi-source transcript to 64 MB.

The reviewer reported a completed, integrity-valid native-response-shaped two-source transcript of **75,560,459 bytes**, with each source approximately 1.9 MB and below the default 2 MB response ceiling. The fixed 64,000,000-byte archive-member ceiling rejected that transcript before replay. This differs from the earlier quadratic progressive-journal defect: geometric checkpointing was already present in the reviewed source.

Disposition: **source corrected; independent final-head review and protected gates remain separate**. [Source correction `e9387ab524219008a1fbce65f1a4b1bf7b718c28`](https://github.com/n0tf0und0ut/Project-FAR/commit/e9387ab524219008a1fbce65f1a4b1bf7b718c28) defines the finite per-transcript ceiling as `64_000_000 * max(1, Budget().max_http_calls // 2)`: **512,000,000 bytes** under the default 16-call budget, scaled for up to eight retrieval/recheck pairs. Cumulative uncompressed archive admission is capped at **1,024,000,000 bytes**, and `campaign.json` at **8,000,000 bytes**. The execution checkpoint and final transcript retention enforce the same per-transcript recording ceiling; execution also checks cumulative JSON recording size after each transcript. Exceeding these separate recording budgets fails the campaign rather than silently certifying an oversized archive. This is a conservative operational budget, not a proved tight maximum for every possible transcript or custom execution budget.

The archive regressions were added in [`361c6a93e08caee19190bd83103a5b0c0b8398a3`](https://github.com/n0tf0und0ut/Project-FAR/commit/361c6a93e08caee19190bd83103a5b0c0b8398a3). [Test-fixture correction `d90ed1041090f36674b0a7478724b15a3afd1b48`](https://github.com/n0tf0und0ut/Project-FAR/commit/d90ed1041090f36674b0a7478724b15a3afd1b48) uses a context-managed `MagicMock` so oversized ZIP metadata reaches the actual admission guards. At that exact head, campaign source blob `c7ee2ce9a043aafa5d45bf8bf8e296657eea85ab` and test blob `a08acec9aa59adc0dffc494d0930bea69b6c4d37` passed these two targeted regressions in **4.364 seconds**:

- [`test_large_bounded_two_source_campaign_remains_archive_replayable`](https://github.com/n0tf0und0ut/Project-FAR/blob/d90ed1041090f36674b0a7478724b15a3afd1b48/tests/test_far_investigation_campaign.py): executes the real native-response-shaped deterministic fixture with two 1,900,000-byte bodies, requires completed integrity-valid state and a serialized transcript larger than 64 MB, then archives and successfully replays it.
- `test_campaign_archive_bombs_remain_bounded`: separately rejects a member above the new per-transcript ceiling and cumulative declared uncompressed sizes above the total ceiling before replay.

This bounded engineering verification runs no model inference and establishes no general agent reliability, source truth, semantic correctness or efficacy advantage. Frozen campaign evidence, registrations, source bindings and negative results are unchanged. The exact integrated candidate, substantive review, thread disposition and required protected checks must be recorded in PR #614 before merge readiness.

## November 8 campaign index and final recording-budget parity

**ENG-CAMPAIGN-INDEX-BOUNDS** — [review comment 4507227583](https://github.com/n0tf0und0ut/Project-FAR/pull/614#discussion_r4507227583),
thread `PRRT_kwDOTH_vCM61DCpj`, reviewed head
`4655961dddafefdd685c55c296d24b5c89a7fe74`. This completes the same
execution/archive recording-budget invariant as
**ENG-CAMPAIGN-RECORDING-BOUNDS** above. The earlier correction bounded transcript
members and archive admission but did not apply the separate 8,000,000-byte index
ceiling to the four campaign-index writes. Its aggregate execution check also
used the previous index's size rather than preflighting the proposed replacement,
leaving per-case growth and final completion metadata outside that check.

The original counterexample was independently reproduced before the managed
runtime became unavailable: 23 valid 30,000-character astral-Unicode questions
with empty source hints produced 23 integrity-valid failed-investigation
transcripts. Execution returned `EXECUTED`, while the unchanged archived output
failed admission with `archive member exceeds bound` before any transcript replay.
This run's index measured **8,319,009 bytes** and all recorded JSON **16,665,314
bytes**. These are this control's measurements; exact metadata-dependent byte
counts need not equal the reviewer's 8,316,155 / 16,659,912-byte observation.

The correction routes every initial, server-startup, per-case and final index
write through one preflight helper. It measures the actual indented,
ASCII-escaped JSON serialization plus final newline, requires the proposed index
to fit the existing index ceiling, and requires all other recorded JSON bytes
plus the proposed replacement to fit the existing cumulative ceiling. The old
index is excluded from that sum because the existing atomic persistence function
replaces it. Both declared ceilings and archive-admission rules remain unchanged.

A rejected write raises rather than returning an executed campaign, leaves the
last bounded index untouched, and retains all raw transcript checkpoints.
A failure index is written only when its proposed bytes also fit; otherwise the
last durable index remains an explicitly unfinished prefix. No selection, raw
receipt, transcript or index is truncated to satisfy admission.

Five regression methods cover the original 23-question counterexample,
initial/per-case/final overflow and last-bounded-byte preservation, the final
proposed-index cumulative check, exact positive index/total boundaries, and
ASCII-escaped astral-Unicode byte accounting. The original real native-shaped
two-source transcript larger than 64 MB and the member/cumulative ZIP-bomb
admission controls remain unchanged. The new tests and corrective source were
prepared through repository APIs during the runtime outage; **no new local test
pass is claimed**. Their hosted regression-only and corrective-head results,
exact source identities and substantive review must be recorded separately in
PR #614 before any readiness claim.

These are bounded recording and replay controls, not authenticated external
execution, source truth, semantic correctness, general investigation reliability
or FAR superiority. Frozen campaign evidence, original source-hash bindings,
registrations, protocols, selections, results and negative findings retain their
bytes. No model inference or new scientific experiment was performed.

### Hosted regression evidence and safe-initial-refusal oracle correction

The unchanged regression-only head
`663655bcaba541769140f5cd53422b62e41b7bb7` produced **six expected assertion
failures and zero runner errors** in [investigation-runtime job
128820379233](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/42509869420/job/128820379233);
the exact index/total positive-boundary control passed.

The corrective source head
`e59afac49ec40c44e339730e38f43ced157ce518` then ran **284 tests**, with **zero
assertion failures, one runner error and five explicit optional skips** in
[investigation-runtime job 128821554436](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/42510247938/job/128821554436).
The four other new regression methods passed: overflow stages, final cumulative
budget, exact positive boundaries and Unicode serialization accounting. The
remaining error was a test-oracle defect: after the required controlled
`ValueError`, the original 23-question test unconditionally called
`campaign.json.stat()`, although its initial selection was already larger than
the index ceiling and the helper correctly refused before creating any index or
transcript.

The successor changes only that oracle and this ledger. It retains the controlled
overflow exception requirement. If a durable prefix exists, the test still
requires a bounded non-`EXECUTED` index and integrity-valid retained transcripts;
if the index was never committed, it requires zero transcripts and no temporary
index. The separate explicit per-case/final last-bounded-byte controls remain
unchanged. Campaign source blob
`90431288e2572b562246af12361b53ad11a4965c` is unchanged. The corrected-oracle
hosted run and final-head review remain pending; no new pass is claimed here.

## November 9, 2026 — new current-head review corrections

Reviewed exact head `b4824bcbb55648ada848a3e6503b08d295b93a00` after
ordinary integration of protected main `302f16d939dd96395d096fb82328f326c999f2de`.
These findings concern production runtime guards, not new scientific results.

| Finding | Counterexample and violated invariant | Scoped correction and regression |
| --- | --- | --- |
| **ENG-RECHECK-DEADLINE-20261109** — `PRRT_kwDOTH_vCM61S-JV`, Codex thread at `tools/far_investigation_engine.py:580–585` | A one-second wall-clock budget can expire during the first of three registered search rechecks; the old loop still dispatched the other two searches because it only inspected the HTTP count. Every network reservation must recheck the actual deadline. | Call the existing `self.limits()` before single-search and each recheck-search reservation. `test_recheck_searches_stop_before_later_reservations_after_deadline` advances a controlled monotonic clock during the first recheck; rejects subsequent network calls and clears readiness. |
| **ENG-MODEL-ARGS-DEPTH-20261109** — `PRRT_kwDOTH_vCM61S-Ja`, Codex thread at `tools/far_investigation_engine.py:714` | A complete, bounded 1,551-byte model response with 700 nested JSON arrays can parse successfully but crash recursively during `MODEL_PROPOSAL` journaling, leaving the investigation unsealed. Untrusted arguments must not bypass failed-attempt recording. | Apply an iterative depth limit before LocalModel returns or agent journals a proposal. Normal `EngineError` handling retains the raw model envelope and final failure seal; `test_deep_model_arguments_fail_with_final_seal_and_raw_evidence` uses an actual parsed nested JSON response. |

These changes are intended to preserve existing failed observations, bounded
research claims, frozen registrations and prior finding dispositions. The
new source and tests have not yet been certified by hosted exact-head CI
or the required independent review; those remain separate merge prerequisites.

## November 9, 2026 — source projection recursion boundary

**ENG-SOURCE-DEPTH-20261109** — Codex thread `PRRT_kwDOTH_vCM61Tfip`,
review of exact head `c870d362526beed16a691b91ad319844cfa0cd63`,
found a distinct input-to-checkpoint recursion failure: a completed
application/json source only 1,401 bytes long with 700 nested arrays
was successfully parsed, but its deeply nested `document` was retained
in runtime state and could make `copy.deepcopy` raise `RecursionError`
during checkpointing, leaving no failed final seal. The model-argument
nesting guard does not cover independently retrieved source content.

**Correction:** the shared source parser rejects JSON document nesting
over 64 via iterative stack traversal immediately after strict parsing
and before exposing/storing the projection; the retained native HTTP
receipt remains untouched. `test_deep_json_document_fails_after_preserving_native_http_bytes`
checks a native HTTP response, exact receipt retention, and an accepted
64-level positive control. `test_deep_native_json_source_rejected_with_raw_receipt_and_final_seal`
checks a real retrieval invocation through the full investigation engine
with a bounded local HTTP transport: exactly one rejected attempt, raw
receipt retained, no parsed projection, and auditable failed final seal.
Final source/test validation and independent exact-head review are required
before any merge; this is an engineering bound, not scientific efficacy.

**ENG-SOURCE-PARSER-STACK-20261109 (verified pre-existing protection):**
Inspection of `mechanization/far_mechanization/_intake_v1_core.py` shows
that `_strict_json_loads` already catches `RecursionError` and raises a
bounded `ValueError` before `parse_receipt` processes the parsed result.
The earlier hypothesis of an uncaught parser-recursion defect was
**disproven**; no production exception-handler change is needed.
The retained `test_json_decoder_stack_limit_preserves_raw_source_receipt`
exercises approximately 12,000 nested arrays through the existing native
retrieval and source parser and confirms a `ToolError` caused by the
pre-existing `ValueError` conversion, with original raw bytes and hash intact.
This is regression coverage, not a correction to production behavior.
No frozen evidence or scientific result is changed.

## November 9, 2026 — malformed model envelopes and baseline algorithm attribution

These findings were independently reported on reviewed head `c20b41b71193dceb5ddb17104073cee2982ecf18`. They are distinct engineering invariants and neither changes the frozen campaign outcomes nor establishes agent reliability.

| Root cause | Original reproducer and violated invariant | Repair, regression, and verification boundary |
| --- | --- | --- |
| **ENG-MODEL-MESSAGE-SHAPE-20261109** — `PRRT_kwDOTH_vCM61UlZE`, comment 4514615909 | Complete local response `{"choices":[{"message":null}],"usage":{"total_tokens":10}}` passed initial parsing; runtime attempted `message.get` and raised uncaught `AttributeError`, escaping failure sealing and interrupting the campaign. | Validate that `message` is a JSON object before field access, raising `ValueError` through the existing recorded `EngineError` path. Commit `098b105538cfe3ada71c551743f8d281a776c82c`; regression `test_null_model_message_is_auditable_sealed_failure` added at `fb0a0455debdd3544bd1d78d54cbcd17a23ec104` checks bounded HTTP response, exact retained raw bytes, token tally, `FAILURE`, and `FINAL_STATE_SEAL`. |
| **ENG-BASELINE-ALGORITHM-BINDING-20261109** — `PRRT_kwDOTH_vCM61UlZU`, comment 4514615933 | A model-generated native function history can be relabeled deterministic/declarative, model counters removed and fixed plan event forged; all hashes resealed. Historical audit only excluded model records and incorrectly permitted baseline scoring of an `evidence_assessment` plan the fixed baseline could not choose. | Independently reconstruct the exact fixed workflow plan, lexical passage selection, extraction, comparison, bounded discovery/recheck/freeze, verification, and finish arguments and require the recorded ordered operations to be its possible prefix. Commit `e67ed5db5301e2c3da59a3911b26895991a74939` and regressions `test_baseline_mode_cannot_claim_agent_selected_verification_plans`, `test_baseline_plan_and_failed_fixed_prefix_are_enforced` at `bff23372212995837e0c7fae5a9db2f2a38a0b40`. |

**Real hosted counterexample and root-cause refinement:** Initial audit implementation incorrectly assumed a rejected tool ends a deterministic workflow. The preserved frozen `H204-deterministic.json` legitimately records continuation after a rejected individual tool, because `Investigation.call()` returns an error result and `run_workflow()` follows the next fixed proposal. The hosted investigation-runtime and health checks failed the original archive replay with `workflow.failure: baseline continued after a rejected operation`. The follow-up commit `1125a6473661376276c4ffbf5dd9a8d37fe2486a` removes this invalid stopping assertion while retaining exact proposal-order binding for both accepted and rejected calls. The original preserved 24-transcript replay is the required compatibility oracle. A clean rerun of the full hosted suite is necessary before merge readiness; no successful new run is asserted here.

The frozen original agent 0/8, deterministic 7/8 and declarative 7/8 comparison and its original recordings remain intact. These are record-authenticity/algorithm-attribution improvements under controlled bounds; general independent autonomy, semantic correctness, external value and superiority remain unestablished.

## November 9, 2026 — exact-head independent review follow-up

The Codex review of `dfc99dda59ae157ac9561598d125e7ecab2ad318` identified four additional P2 defects. They concern legitimate baseline histories or offline reconstruction consistency, not a demonstrated agent reliability gain. The fixed source is `tools/far_investigation_audit.py`; corresponding native-receipt regressions live in `tests/test_far_investigation_audit.py`.

| Finding | Reproduced invariant | Corrected behavior and counterexample |
| --- | --- | --- |
| **ENG-BASELINE-RETAINED-EVIDENCE** — `PRRT_kwDOTH_vCM61XRBc`, comment 4515766294 | A one-time `OSError` in an extraction proposal checkpoint leaves one genuine evidence row from two projections. The fixed controller compares `list(state['evidence'])`, not one identifier per projection. | Generate the ordered IDs from the retained evidence count; numeric ID order is invariant under canonical JSON key sorting. `test_baseline_keeps_retained_extraction_ids_after_checkpoint_rejection` executes native bounded HTTP retrieval in deterministic and declarative lanes and accepts the valid one-rejection completed transcript. Independent evidence-coverage reconstruction remains mandatory. |
| **ENG-BASELINE-DRAFT-CONTINUATION** — `PRRT_kwDOTH_vCM61XRBi`, comment 4515766307 | A source drifts at terminal recheck, leaving an existing `DRAFT` intake. Runtime attempts `verify` and `finish` even though neither can succeed. A frozen-only audit reconstruction falsely rejects the legitimate failure. | Reconstruct those fixed attempts whenever intake exists, including the DRAFT case; ordinary dispatch/freeze validation still forbids acceptance. `test_changed_source_baseline_keeps_draft_verify_and_finish_attempts` executes native changed-source rechecks in both baseline modes and validates the failed sealed transcript without manufacturing successful evaluations. |
| **ENG-RECORDED-DNS-PREFLIGHT** — `PRRT_kwDOTH_vCM61XRBr`, comment 4515766322 | Self-consistently rewriting observed preflight addresses to `127.0.0.1` allowed offline audit acceptance of an impossible successful native retrieval under the runtime DNS policy. | On native source receipts, verify the recorded destination's exact host/mode, parseable timestamp, nonempty sorted unique public addresses (`ipaddress.ip_address(...).is_global`), and declared trust boundary without new DNS access. In proxy mode require unknown target addresses and explicit unestablished public-IP assurance. `test_native_success_rejects_resealed_nonpublic_preflight_addresses` tests private/link-local, empty, mismatched mode/host cases. This is **recorded-policy consistency**, not proof of the actual network peer or DNS authenticity. |
| **ENG-UNTRUSTED-JSON-ENVELOPE-COLLISION** — `PRRT_kwDOTH_vCM61XRBy`, comment 4515766332 | A legitimate source JSON `document` may contain `timing_scope`, `raw_base64`, or `request_sha256` as application keys. The generic audit walker erroneously treats those source values as journal metadata. | Exclude only the nested `state.projections.src.*.document` payload from generic envelope-field interpretation. The whole projection is still independently rederived from retained source bytes through `parse_receipt`, which enforces JSON nesting bounds. `test_native_json_document_envelope_lookalikes_are_untrusted_data` covers a complete native agent and both baseline modes while retaining envelope checks on actual journal records. |

Corrective implementation head `ba1c102b52b122dfe21c843c9291c41eae869ffe`; regression head `c99b1e85be5099fcbdc79ee8c9c0f4b5b06945dd`. Hosted `FAR Investigation Engine` workflow `42674124369`, `investigation-runtime` job `129351503371`, ran **296 tests: 291 passed, five explicit optional skips, zero failures**, including all four new native-response regressions. The frozen campaign's original 24 transcripts remain untouched and its replay passes in that suite. Other hosted assurance workflows, exact-head independent review, owner App decision and protected merge checks are separate and still required. A passing bounded integrity audit does not authenticate the source, establish general autonomous reliability, or change accepted research claims.

## November 9, 2026 — fifth exact-head review: five additional trust-boundary findings

Independent Codex review of head `86dd185160ccc40f7823f31f06bc11d3d8904ce2` returned five distinct P2 findings. Each is a reproducible contract-level defect; none demonstrates a real-world attack, general autonomous success or scientific advantage. Corrective source and regressions are on the same PR branch; whole-head hosted verification and new independent review remain separate obligations.

| Finding and source | Violated invariant / counterexample | Narrow correction and regression |
| --- | --- | --- |
| **ENG-OBSERVED-SOURCE-ENVELOPE-20261109** — thread `PRRT_kwDOTH_vCM61ZA1x`, comment 4516517478 | A `source_json` contract may return a nested source object containing the application field `timing_scope`. Its copies in verifier `projection.observed` and `counterexample.observed` are data, not transport records, but generic recursive envelope interpretation rejected a legitimate `REFUTED` native evaluation. | Audit recognizes timing only on explicitly located `.transport` envelopes, source-receipt validation only on `far-source-receipt/0.1` schema, and excludes verifier-observed values from generic envelope inspection while independently recomputing verifier results. `test_verifier_observed_json_objects_do_not_become_transport_metadata` executes actual native HTTP fixture retrieval, the full agent workflow and a `source_json` refutation. Earlier projection-source JSON test remains. |
| **ENG-PLAIN-TEXT-JSON-DEPTH-20261109** — thread `PRRT_kwDOTH_vCM61ZA13`, comment 4516517485 | Allowed `text/plain` receipt can carry 700 nested JSON arrays, which `source_json` reparses as data. Unbounded verifier observation can exceed checkpoint recursion and escape final sealing. | Reuse the already-governed `_enforce_bounded_document_depth` before extracting verifier pointer values, including text/plain inputs, with no altered accepted comparison semantics. `test_plain_text_json_reparse_is_depth_bounded_before_observation` requires controlled `ValueError` for 70/700 depths and retains a shallow positive case. |
| **ENG-LOCAL-MODEL-PROXY-20261109** — thread `PRRT_kwDOTH_vCM61ZA19`, comment 4516517497 | urllib's default opener honors inherited `HTTP_PROXY`, so model requests to the exact loopback URL may be served by an unrelated proxy, defeating process-attested response provenance. The separate readiness health URL had the same flaw. | Use `urllib.request.build_opener(urllib.request.ProxyHandler({}))` for both local model inference and health probes. Source-retrieval proxy policy is unchanged. Tests `test_local_model_ignores_inherited_http_proxy` and `test_local_campaign_health_never_uses_inherited_http_proxy` check actual selected openers and failure boundaries with inherited proxy configuration. |
| **ENG-RETAINED-REQUEST-METHOD-20261109** — thread `PRRT_kwDOTH_vCM61ZA2G`, comment 4516517510 | Successful native source receipt can report `GET` while the retained transport reports `POST`, and offline audit incorrectly accepts the resealed contradictory record. | Bind native `transport.request_method` to exact `GET` in `accepted_transport` without claiming runtime write capability. `test_native_source_transport_cannot_claim_post_instead_of_get` mutates all retained native receipt copies, reseals, and requires rejection. |
| **ENG-MODEL-ATTEMPT-STEPS-20261109** — thread `PRRT_kwDOTH_vCM61ZA2I`, comment 4516517515 | A malformed final model response still consumes a loop iteration. Auditing only accepted proposals against `max_steps` allows a resealed two-model-attempt failure to claim a one-step budget. | Require `len(model_calls) <= policy.budget.max_steps` in agent mode; retained successful proposal and raw-usage accounting remain independently enforced. `test_failed_model_attempts_still_consume_agent_step_budget` executes two bounded native-shape attempts (accepted proposal then malformed response) and rejects a narrowed resealed step budget. |

Source commits include `79f2a3231ce1fc650bada5b1b097bfb448d0cf53`, `1463887abac3b2487216e6170fc0f54a9d9b0ae9`, `25859bb586947b0674b9c557717ce0cf56096292`, and `c550b8edcd7e4caf7b3059fbd4a1b944a6f66d01`; regression commits include `b48acc3c8bc7f42b1615437bd82101adfcd4addc`, `17da7bdce729641ff12b3f00e424e2cb63c2492c`, `7d45b9d677cdb8ae60fbb2c1b61acc452cf43232`, and `f067951429eda8e47294fd7311005a766a5b3b9f`. **Status at this record:** corrections committed; latest-head hosted full validation and independent review not yet complete. Frozen archive and original negative findings remain unchanged. The JSON observation, method and proxy corrections assert only local recorded-boundary consistency, not external source authenticity.

## November 9, 2026 — exact local-model redirect provenance

**ENG-LOCAL-MODEL-REDIRECT-20261109.** A separate adversarial transport probe after the five P2 corrections found that `urllib.request.build_opener(urllib.request.ProxyHandler({}))` disables inherited proxies but **retains the default HTTP redirect handler**. A genuine local loopback POST server responding with HTTP 302 and `Location: http://127.0.0.1:<second-port>/untrusted` caused urllib to follow the redirect, return `b'forged model'` from a second server, and attribute that response to the first listener. This was reproduced with two native local HTTP servers and no external network. A custom redirect handler that returns `None` prevented the second request and caused HTTPError 302. Process identity checks against the originally launched server cannot certify bytes obtained by following a redirect.

Correction: a shared `local_model_opener()` creates an explicit proxy-free and redirect-refusing opener using the existing `_NoRedirect` handler. Both the model-completion POST and campaign-health GET use that same opener; the permitted endpoint and process/weight identity checks remain unchanged. Native regression `test_local_model_redirect_cannot_escape_attested_listener` uses two ephemeral real loopback HTTP listeners to assert HTTPError 302 and zero requests to the decoy endpoint. Corrective commit `c6b818e745d2560631a05fc48e012c60fae2d030`. This is local transport-provenance hardening, not proof against a malicious host, source-truth authentication or autonomy advantage. Hosted validation and independent exact-head review remain mandatory; no new test pass is asserted here. Frozen 24-transcript campaign evidence is untouched.

## November 9, 2026 — sixth exact-head review: five further P2 invariants

Independent Codex review of `30abb51b617311fb3cfaf23619934a4625ea338f` identified five actionable flaws. This record links source-root corrections and newly written counterexample tests. Hosted results and an independent review of the corrective head are **not yet claimed** here.

| Finding / thread | Reproducer and violated invariant | Candidate repair and targeted control |
| --- | --- | --- |
| ENG-FAILED-SEARCH-RESERVATION-20261109 / `PRRT_kwDOTH_vCM61adIa` | Failed native Crossref HTTP 500 search receipt remained in TOOL_REJECTED while a resealed transcript erased the producing SEARCH_REQUEST and SEARCH_OBSERVATION and reduced the HTTP count. | Require failed native search receipts to match that same attempt's request, provider, query, canonical URL and observed receipt. `test_failed_native_search_receipt_requires_its_own_reservation` verifies authentic failure and adversarial excision. |
| ENG-REJECTED-ARGUMENT-ENVELOPE-20261109 / `PRRT_kwDOTH_vCM61adIh` | Invalid retrieve action with a `response_base64` argument rejected correctly, but the generic audit walker misread that argument as native transport metadata. | Restrict response-base64/hash checks to specifically located model/transport envelopes. `test_rejected_model_response_named_argument_is_not_an_envelope` verifies legitimate rejected-then-completed history. |
| ENG-MODEL-ID-METADATA-DEPTH-20261109 / `PRRT_kwDOTH_vCM61adIn` | Native local response retained a valid flat action but deeply nested top-level model identifier; journaling recursion escaped final sealing. | Validate the model identifier as bounded text before returned metadata is journaled, and reject deeply nested model metadata. `test_deep_model_identifier_retains_raw_evidence_and_final_seal` preserves raw bytes and a final failure record. |
| ENG-MODEL-BODY-DEADLINE-20261109 / `PRRT_kwDOTH_vCM61adIs` | A local endpoint trickled model response bytes repeatedly within a per-socket timeout but past the absolute investigation budget. | Propagate a monotonic execution deadline into the shared bounded reader, checking during incremental body consumption and chunk framing. `test_local_model_trickle_is_interrupted_at_execution_deadline` records interrupted prefix, final incomplete transport and elapsed bound. This is application-layer deadline checking, not independent OS-level preemption of a blocking syscall. |
| ENG-DUPLICATE-CAMPAIGN-LANE-20261109 / `PRRT_kwDOTH_vCM61adIx` | Two identical modes produced the same transcript path; later run overwrote evidence while reporting two attempts. | Validate nonempty unique allowed modes before creating the output or running tasks. `test_duplicate_modes_rejected_before_any_attempt_can_overwrite_evidence` asserts rejection with no output directory. |

The original frozen 24-transcript archive and all registered negative results are untouched. These changes are engineering integrity claims only; no independent semantic correctness, agent reliability advantage, external replication, or customer effectiveness has been established.

**Hosted correction check (before merge):** Source/test head `2d1239c0d194c39713d36d729069da2538471cfa` ran `FAR Investigation Engine` job `129427363485` and failed with 15 regression failures and 2 errors. Independent log inspection localized 16 native chunked-framing failures/errors to switching chunked `HTTPResponse.read` to `read1`, which changed validated framing and observed-prefix capture, and one failed-search fixture rejection to unnecessarily requiring a native Crossref URL from an injected operator adapter. The next source correction restores chunked `read()` and retains deadline instrumentation in the chunk-frame observer; it binds failed searches to their own recorded request and observation without inventing a native adapter identity. No clean follow-up run is claimed until separately observed.

## November 9, 2026 — independent review of integrated native execution head

The independent Codex review submitted at 2026-11-09T21:02:38Z against
`7dc06f60c52926722891eefc069d524033b209e2` identified three distinct
P2 counterexamples. They are engineering-invariant corrections, not new
inference experiments or scientific result promotions.

| Root cause / source | Counterexample and violated invariant | Repair and defect-detecting control |
| --- | --- | --- |
| **ENG-CHUNK-FRAMING-DEADLINE-20261109** — `PRRT_kwDOTH_vCM61cUuY`, comment `4517941054` | A chunk extension or trailer line trickled byte-by-byte allowed buffered `readline()` to exceed the absolute model deadline; the body deadline guard did not run during framing. | `_ChunkFramingObserver.readline` consumes bounded framing bytes incrementally, checking remaining absolute time before and after each operation and limiting the socket's blocking timeout. `test_trickled_chunk_size_and_trailer_deadline_is_checked_per_byte` covers both stages; existing native good/failed-chunk controls remain applicable. |
| **ENG-TRANSPORT-TIMESTAMP-SCOPE-20261109** — `PRRT_kwDOTH_vCM61cUug`, comment `4517941067` | Invalid model action `retrieve(..., transport={'timing_scope':'domain interval'})` was correctly rejected in runtime but its untrusted argument was audited as native HTTP metadata. | Timestamp checks now admit enumerated real transport-envelope locations only. `test_rejected_transport_named_model_argument_is_not_http_metadata` preserves accepted native/fixture traces; `test_resealed_new_transport_timestamps_cannot_move_backwards` remains the negative control for actual recorded transports. |
| **ENG-FAILED-RECHECK-RESERVATION-20261109** — `PRRT_kwDOTH_vCM61cUuo`, comment `4517941079` | A recheck's failed native search (HTTP 500) retained its receipt while a resealer could remove the producing `SEARCH_REQUEST` and `SEARCH_RECHECK_OBSERVATION`, reducing the apparent HTTP budget from nine to eight. | Failed recheck source/search receipts must consume and match their exact pending reservation and final observation, including original registered search identity. `test_failed_search_recheck_receipt_requires_exact_reservation` requires a real bounded-reader failed search followed by successful retry, then rejects the forged missing-reservation trace. |

The candidate must pass hosted targeted and canonical tests, independent
substantive exact-head review, and all required native/App protected checks
before a protected merge. No frozen transcript, experiment registration,
source hash, result, or negative outcome is rewritten. Native engineering
conformance does not establish general agent autonomy, semantic truth,
external scientific independence, causal performance advantage, or
commercial effectiveness.

## November 9, 2026 — seventh review: native deadline, receipt, and model-prompt boundaries

Independent Codex reviewed `507d0211312d114776382ee2837ba01a1e788f55` and reported six P2 invariants. These repairs are submitted as **candidates**, not asserted verified until hosted exact-head checks and independent review complete. No frozen original campaign results or raw evidence blobs were edited.

| Root cause and review thread | Observed counterexample | Correction / adversarial regression |
| --- | --- | --- |
| ENG-HEADER-DEADLINE-20261109 / `PRRT_kwDOTH_vCM61c1U3` | Trickle of HTTP status/header bytes evaded one-time opener deadline and idle socket timeout. | Install per-request HTTP/HTTPS header readers in the existing urllib opener, checking monotonic remaining time per header byte without changing proxy and redirect handlers. Check bounded fake stream and full urllib-over-AF_UNIX socketpair trickle response; no external network. |
| ENG-SOURCE-DEADLINE-20261109 / `PRRT_kwDOTH_vCM61c1VA` | Initial and recheck source/search tools omitted absolute investigation deadline, allowing legitimate body trickles after budget. | Thread fixed execution deadline into native `retrieve` and `public_search` and the shared bounded response reader. Operator-injected adapters keep their explicit trust scope; native dispatch and recheck use the same deadline. Verify source native reader invocation receives runtime deadline. |
| ENG-BODY-PREFIX-DURABILITY-20261109 / `PRRT_kwDOTH_vCM61c1VD` | A body chunk returned after deadline was discarded before entering the preserved prefix. | Retain newly returned body bytes and decoded chunk-prefix before post-read deadline rejection; maintain incomplete framing/status. Verify two-byte delayed body preserves both observed bytes. |
| ENG-RECEIPT-SCHEMA-COLLISION-20261109 / `PRRT_kwDOTH_vCM61c1VJ` | Invalid model arguments containing a receipt-shaped application object were treated as an authentic native source envelope. | Check `far-source-receipt/0.1` only in explicitly owned source/search/recheck/observation/failed-tool paths. Rejected-then-completed authentic fixture with malicious receipt-shaped argument remains audit-valid. |
| ENG-FAILED-TRANSPORT-BYTE-BINDING-20261109 / `PRRT_kwDOTH_vCM61c1VN` | An attacker could change internally resealed failed receipt bytes/hash/length without changing the retained native transport evidence. | Bind source-receipt body/hash/length to native retained transport even when receipt status is FAILED. Adversarial failure mutation must be rejected without claiming transport success. |
| ENG-MODEL-QUESTION-ATTRIBUTION-20261109 / `PRRT_kwDOTH_vCM61c1VU` | A rewritten, resealed request sent a different question/system instruction while the report attributed its source/model output to the recorded question. | Bind native request's fixed system message, immutable question/seeds/policy, tool schemas, deterministic request parameters, prior tool proposals and chronological observed results. Adversarial re-questioning of all raw model request copies must fail even if hashes are resealed. External model provenance and semantic truth remain unproven. |

**Traced canonical-test integration blocker:** Exact-head assurance job `129444190661` and merge-authority job `129444776114` failed `FAR-VAL-TRACE-001` because an unrelated in-process native redirect regression created an AF_INET loopback connection inside the deterministic canonical test suite. This is not a failing functional assertion. Reproduce the same urllib redirect chain using two separate in-memory AF_UNIX socketpair endpoints and confirm both refusal by the governed opener and successful decoy reachability by default opener as a positive control. Do **not** relax the trace policy's deny-network invariant. The hosted test and trace verdict on the new patch are not yet known.

Evidence scope: test fixtures are not real model autonomy, external source authentication, independently adjudicated truth, or a demonstrated treatment advantage.

**First hosted correction feedback.** Source/test head `4eb16ef907a0dd1f8144f998956c793c2c9ab197` failed one of 322 investigation-runtime tests (five optional skips): `test_transcript_sources_must_match_registered_task_hints` expected a resealed *agent* transcript with substituted seeds to remain internally valid. The new request-to-seeds audit binding correctly rejects it, making the old assertion obsolete. The test now demands transcript rejection, checks the specific `request.prompt.seeds` invariant, and separately demands campaign-level source-exposure rejection. This preserves and strengthens both independent guards; no forged transcript is retroactively treated as valid. Hosted revalidation still required.

## November 9, 2026 — eighth review: chronological native prompt and nonchunked deadline

Independent Codex review of exact head `f445a4467f6c9b545a4d17bdf2d928d149cd07d7`
reported two additional P2 invariant failures. The following are corrective
source and regression *candidates*; they must pass current-head hosted checks
and a new independent review before protected merge authorization.

| ID / review thread | Counterexample and root cause | Correction and regression boundary |
| --- | --- | --- |
| **ENG-MODEL-CHRONOLOGICAL-PROMPT-20261109** / `PRRT_kwDOTH_vCM61eq3G`, comment 4518956168 | The auditor checked question, seeds, policy, prior proposals and recent observations, but accepted self-consistently rewritten model request `sources`, `evidence`, `comparisons`, `freeze`, `candidate_ids`, `evaluated_ids`, `searches` or eligible `tools`. A request could therefore claim access to future or fabricated evidence even with the actual source/tool producers unchanged. | Reconstruct per-attempt model-view inventory and eligibility from the existing validated chronological tool replay, including retained effects of rejected post-dispatch attempts. Compare every native request's model-visible fields at the boundary before its first response. For an interrupted recheck, retain only actually possible committed prefixes rather than certifying an unknown append. Regression `test_native_model_prompt_all_chronological_views_resist_resealed_mutation` rewrites every journaled copy, rebuilds request hashes and reseals, and requires each affected field to fail offline audit. |
| **ENG-NONCHUNKED-BODY-ABSOLUTE-DEADLINE-20261109** / `PRRT_kwDOTH_vCM61eq3K`, comment 4518956172 | A native `read1()` after an initial early body fragment inherited the socket idle timeout set during header parsing. The clock guard before `read1` did not bound the blocking syscall; a 2-byte trickle could overrun the absolute deadline and observe the later byte. | Refresh native socket timeout to the remaining monotonic whole-request budget before *every* nonchunked blocking body `read1` while preserving the earlier returned prefix. Regression `test_real_nonchunked_socket_trickle_uses_remaining_absolute_deadline` uses a real `http.client.HTTPResponse` over AF_UNIX socketpair, checks only the first byte survives an interrupted 2-byte body, and leaves the trace deny-network policy unchanged. |

These are internally controlled integrity/transport counterexamples, not a
measurement of real model planning, external truth, or agent superiority. Frozen
campaign registrations, original evidence and negative outcomes are unchanged.

**First hosted counterexample on corrective head `06e014b65262e93297e2e3e9a19e7764ee94d90b`:** The frozen-investigations job `129528969165` ran 309 tests with five optional skips and five failures. The new native prompt test and original frozen 24-transcript campaign replay failed because the first snapshot check mistakenly compared 1-based terminal tool-event indices with a 0-based first-MODEL_OBSERVATION index using `<`. It therefore omitted the most recent completed tool effect at each model prompt, rejecting valid source, evidence, freeze, and tool views. The correction uses `<=` to include exactly that prior completed tool outcome while still excluding the model's own future actions. Existing full native-journey and preserved frozen-archive replay tests provide the positive boundary; resealed mutations provide negative controls. This fixes the audit oracle, not the frozen evidence. A clean corrected-head rerun has not yet been observed.

## November 10, 2026 — ninth independent review: chunk separator whole-request deadline

Independent Codex exact-head review of `fabdd9960bd41aba6bb32492fe8c61a5a277e36c` reported
**ENG-CHUNK-SEPARATOR-DEADLINE-20261110**, thread `PRRT_kwDOTH_vCM61gAcW`
(comment 4519535689). After the header, chunk-size line and chunk-body
deadline repairs, a remaining uninstrumented path called the native buffered
`read(2)` for the CRLF between chunks. One socket receive supplied CR just
before the execution deadline; the same originally calculated socket timeout
allowed the LF read to continue past that deadline. The reviewer reproduced
a 171-ms failure under a 100-ms absolute limit.

The candidate correction replaces only the separator's two-byte buffered
read with two bounded one-byte `read1(1)` operations, calling the
monotonic deadline/socket-timeout guard before and after each receive.
Strict CRLF checking and failed-response decoded-prefix preservation
remain mandatory. The new `test_real_chunk_separator_trickle_uses_remaining_absolute_deadline`
drives an actual native chunked `HTTPResponse` over AF_UNIX socketpair
with the first byte of chunk data and CR before the limit, LF after the
limit, and demands an interrupted receipt retaining exactly the decoded
`a` prefix with matching hash. Existing native positive, malformed
separator, chunk framing, deadline and frozen-archive controls must remain
green; this is not yet a verified current-head result. No original
campaign evidence or experiment outcomes have been modified.

## November 10, 2026 — tenth independent review: configured transport timeout cap

Independent Codex exact-head review of `c94bf3143d0b0db7bc12485792ffc40146ed13ee`
reported **ENG-CONFIGURED-TRANSPORT-TIMEOUT-20261110**, thread
`PRRT_kwDOTH_vCM61gGoG` (comment 4519577674). Although a monotonic
investigation deadline now constrains HTTP header, nonchunked body,
chunk body, chunk separator and chunk-line reads, the helper's socket
refresh used the full **remaining investigation budget**, even when the
transport policy had configured a shorter timeout. With a native response,
a configured 50-ms timeout, and a 500-ms investigation deadline, a delayed
body could arrive after 216 ms and be accepted, violating the configured
per-operation timeout ceiling.

Candidate root-cause correction: pass the configured transport timeout
into the header and chunk-framing readers, and set the underlying socket
timeout to `max(.001, min(configured_timeout, remaining_absolute_budget))`
before each respective blocking syscall. Apply the same cap in the
nonchunked `read1` path. Without an absolute deadline, the original
configured socket timeout remains unchanged. A new AF_UNIX socketpair
regression `test_native_socket_timeout_is_capped_by_policy_during_all_deadline_refreshes`
covers header, nonchunked-body and chunk-separator interruptions with
a short configured timeout and deliberately longer absolute deadline,
asserting no delayed bytes are falsely accepted. Existing real-client
framing, prefix and frozen-archive tests remain mandatory. This is
transport-resource governance; it does not establish general autonomy,
truth or performance advantage. No frozen records have been changed.

## November 10, 2026 — eleventh review: reopened transport ownership and failed-model audit provenance

Independent Codex reviewed exact head `5228514155e66b6e9076e947c0129ca90cf69080` and reported **three P2 findings**. At this entry the fixes are *candidate changes*, not claims of tested or independently reviewed success. No frozen experiment or scientific conclusion was changed.

| Finding and thread | Original counterexample | Corrective mechanism and regression |
| --- | --- | --- |
| **ENG-OPENER-REQUEST-SCOPE-20261110** / `PRRT_kwDOTH_vCM61gS5u`, comment 4519660017 | Reusing an operator-supplied `OpenerDirector` appended another deadline handler. A first request with 200-ms timeout captured a closure; a second with 50-ms timeout still accepted headers delayed 123 ms, and later requests could inherit an expired deadline. | Create a request-local `OpenerDirector` from shallow-copied original handlers and install deadline handlers **only on that local director**. Preserve the caller's handlers, their parent references, proxy and redirect choices. `test_reused_opener_cannot_inherit_previous_deadline_or_transport_timeout` uses real HTTP over AF_UNIX socketpair for success, shorter-timeout failure and success after the first deadline has expired; also verifies original handler identity/ownership remains unchanged. |
| **ENG-UNTRUSTED-NESTED-REQUEST-CHECKSUM-20261110** / `PRRT_kwDOTH_vCM61gS51`, comment 4519660025 | A valid recorded native LocalModel execution with an intentionally rejected function argument `metadata.envelope.request_sha256='not-hash'` completed, but offline audit treated the argument as native model-envelope metadata because it matched a broad path suffix. | Validate request checksums only on the already identified **owned** `model_envelope` locations: `model_calls[n]`, `MODEL_OBSERVATION.payload`, `MODEL_PROPOSAL.payload.metadata.envelope`. Do not interpret arbitrary rejected function-argument keys. `test_native_rejected_nested_metadata_envelope_is_application_data` uses actual LocalModel-shaped requests and response transport, an intentionally rejected first proposal, and a successful subsequent full pipeline. |
| **ENG-FAILED-MODEL-TRANSPORT-BYTE-BINDING-20261110** / `PRRT_kwDOTH_vCM61gS53`, comment 4519660034 | An actual malformed final model response had 10 tokens in its completed native transport, but self-consistently rewriting outer model response body/hash to `{}` and declared model tokens to zero passed audit despite contradictory transport bytes. Existing byte binding covered accepted `MODEL_PROPOSAL` only. | For every owned model envelope with native transport, including `MODEL_OBSERVATION` and failed final `model_calls[n]`, require outer response body, hash and retained byte count to equal that nested native transport. `test_failed_native_model_bytes_cannot_disagree_with_transport_after_reseal` executes malformed `message=null`, confirms the original failure is audit-valid with retained token usage, then rewrites every outer response copy and reseals; the audit must reject the mismatch. |

The new external independent exact-head review, canonical/targeted hosted CI, protected merge authority, authenticated review-convergence metadata, and protected App gate remain separate release requirements. Internal consistency checks do not authenticate the model process, source truth or actual token billing.


## November 10, 2026 — twelfth exact-head Codex review and corrective candidate

Independent Codex reviewed PR #614's exact head `e9ca716951af1fe89677ae2adc69c01ec2b813fe`
and opened four substantive P2 threads. This entry preserves the concrete
counterexamples, candidate root-cause corrections, and regression obligations.
It is not a certification of the new head, a new scientific experiment, or
authorization to bypass protected checks.

| Finding / review thread / comment | Independent counterexample | Correction and defect-detecting regression |
| --- | --- | --- |
| **ENG-DEADLINE-OPERATOR-TLS-20261110**, `PRRT_kwDOTH_vCM61nuuY`, 4522844715 | An operator-supplied `HTTPSHandler(context=operator_context)` is superseded by the deadline handler at priority 450, which constructs a default TLS context. Native HTTPS connection uses a different trust context when deadline enforcement is enabled. | Derive the request-local deadline HTTPS handler's `context` from the copied original operator HTTPS handler; retain hostname checking on that same configured SSLContext, without inventing a private `_check_hostname` attribute. `test_deadline_https_keeps_operator_ssl_context_and_opener_ownership` observes context identity through a native HTTPS connection over an AF_UNIX socketpair while checking the caller-owned handler list and parent links remain unchanged. |
| **ENG-TERMINAL-FAILURE-STATUS-20261110**, `PRRT_kwDOTH_vCM61nuug`, 4522844730 | Insert a `FAILURE` event into an otherwise completed run immediately before `FINAL_STATE_SEAL`, renumber events, and recompute hashes. Offline audit previously accepted completed status even though the runtime always terminates after emitting `FAILURE`. | Require at most one `FAILURE`, immediately before the final seal, and only with `FAILED_OR_INCOMPLETE`; conversely require that a failed final status have its terminal failure evidence. `test_resealed_terminal_failure_cannot_be_scored_as_completion` mutates valid agent and deterministic transcripts; the genuine completed controls must remain valid. |
| **ENG-MODEL-NATIVE-BYTE-CEILING-20261110**, `PRRT_kwDOTH_vCM61nuur`, 4522844744 | Rewriting all six owned copies of a native model response, padding beyond the reader's 1,000,000-byte limit, and resealing still certified a completed run. The native reader cannot accept that body. | Name the runtime's 1,000,000-byte finite `LOCAL_MODEL_RESPONSE_MAX_BYTES` once, use it in `LocalModel` and the offline native-transport auditor, and reject over-limit retained responses even after consistent hashes and lengths are forged. `test_resealed_oversized_native_model_response_cannot_pass_replay` retains genuine accepted native evidence as positive control before the mutation. |
| **ENG-FREEZE-PRODUCER-ATTRIBUTION-20261110**, `PRRT_kwDOTH_vCM61nuux`, 4522844758 | A freeze proposal checkpoint fails before dispatch; a second freeze actually mutates intake to FROZEN but is post-dispatch rejected when the wall-clock deadline expires. A permissive fallback credited the earlier undispatched rejection, producing a false prompt reconstruction. | Attribute a retained freeze without `TOOL_RESULT` only to the matching post-dispatch budget-expiration rejection of `freeze`, never to a prior `OSError` proposal checkpoint rejection. `test_undispatched_freeze_rejection_cannot_steal_retried_freeze` exercises the two attempts with a native LocalModel-shaped request and verifies authentic audit success. |

The first hosted corrective candidate `316f8fc0806e16e81f6f59a5bed7b65483408727`
exposed an implementation defect in the TLS adapter, not a preserved
research-evidence discrepancy: Python's standard `HTTPSHandler` does not
provide an `_check_hostname` attribute. Frozen-evidence and uncertain-routing
workflows failed with `AttributeError` from the added lookup. Candidate commit
`5826eafcf40ded2231a037bed2c72edc3c3b5fcd` removes the unsupported
attribute access and instead passes the preserved original SSLContext through
stdlib's `context` parameter. The exact-head hosted rerun, independent review,
review-convergence metadata and protected checks must be verified separately
before any merge-ready verdict. No frozen evidence, prior negative outcome,
research registration, accepted theory, or general agent performance claim
was changed by these corrections.

## November 10, 2026 — thirteenth exact-head Codex review: two fresh P2 defects

The authenticated Codex review of predecessor head
`0c0a221752f07ab3cefc23e45c28e50dc392208d` surfaced two new,
independently reproducible failure modes. Both were still present in the
normal two-parent protected-main integration head
`1318703a567a9ad13469a472d47590eb1d6d7a6c`; neither was
covered by the earlier four fixes. The review itself is independent
automated inspection, not experimental truth or merge authorization.

| Root cause and source | Exact failure mode and scope | Candidate correction and regression obligation |
| --- | --- | --- |
| **ENG-RETRY-EFFECT-PRODUCER-20261110**, thread `PRRT_kwDOTH_vCM61p4nU`, comment 4523761618 | After a `TOOL_PROPOSAL` checkpoint fails with pre-dispatch `OSError`, a second attempt executes `extract`, `compare`, or `discover`, mutates retained state, and is later rejected for exceeding the wall-clock budget. Without any accepted result, the auditor's `successful_*_at.get(..., index) == index` fallback credits the first, undispatched rejection. A genuine LocalModel transcript then fails the reconstructed evidence, available tools or discovery views. | Only credit a rejected mutation to an attempt with a runtime-distinguishable post-dispatch outcome: exact post-dispatch wall-clock `EngineError`, or for evidence/comparison the recorded `DISCOVERY_INVALIDATED` event emitted after the mutation. A pre-dispatch proposal-checkpoint `OSError` can never claim the effect. `test_rejected_pre_dispatch_retry_does_not_steal_mutable_effect` uses actual `LocalModel`-shaped responses and controlled first/second attempts for each of the three tools, with the unchanged transcript as an audit-positive oracle. Existing positive controls continue checking legitimate post-dispatch failures and accepted producer precedence. |
| **ENG-DNS-PREFLIGHT-DEADLINE-20261110**, thread `PRRT_kwDOTH_vCM61p4ne`, comment 4523761630 | The default exact-host public-address preflight synchronously executes the operator's resolver before the bounded HTTP transport. An unresolved DNS call can block the investigation worker past both transport timeout and remaining wall-clock investigation deadline, despite the HTTP reader timing out immediately afterward. This affects initial retrieval, public search and every recheck. | Enforce the minimum of per-request timeout and remaining investigation deadline across DNS and HTTP; perform blocking resolution only inside daemon workers whose outstanding count is bounded and whose result is accepted solely before deadline. On expiry fail closed, preserve the failed source receipt, never open HTTP or claim resolved addresses, and release a resolver slot only after the worker actually exits. `test_dns_preflight_cannot_overrun_request_or_investigation_deadline` checks both clocks with a controlled stalled resolver and no HTTP; `test_expired_dns_budget_never_calls_resolver` checks pre-expiry rejection. Retained DNS output remains preflight evidence, not a pinned transport destination or source-truth guarantee. |

The repairs were made on PR #614's development branch without modifying
frozen research inputs, prior negative experiment results, canonical theory,
protected main or independently attested artifacts. They are **candidate**
repairs until their hosted exact-head regression and integration workflows
pass. Previous-head green CI and resolved threads are not substituted for a
new independent review, native review-convergence, merge-authority,
exact-head assurance or the dedicated protected App gate.

## November 10, 2026 — parallel integration-head Codex review and Python 3.11 TLS override

The authenticated Codex review of integration head
`1318703a567a9ad13469a472d47590eb1d6d7a6c` opened two additional
P2 threads. One is the same DNS preflight deadline defect independently
reported against `0c0a221...`; it was already being corrected on the
successor branch before this review completed. The other is a separate
TLS compatibility defect that the earlier SSLContext-identity test missed.

- **ENG-TLS-HOSTNAME-OVERRIDE-PY311-20261110**, thread
  `PRRT_kwDOTH_vCM61qASn`, comment 4523811853.
  On Python 3.11, `HTTPSHandler(context=context, check_hostname=True)`
  can retain a per-handler `_check_hostname` override even if
  `context.check_hostname=False`. Deadline override had preserved the
  SSLContext object but dropped that separately stored operator setting.
  The adapter now preserves and forwards the override when the running
  standard library actually exposes it, omitting a constructor parameter
  that Python 3.12+ no longer supports. The regression
  `test_deadline_https_retains_python311_hostname_override` checks
  source/isolated TLS context identity, conditional override propagation
  through the deadline connection factory, and original opener ownership.
  It complements the native socketpair SSLContext regression rather than
  replacing it.
- **ENG-DNS-TRANSPORT-BUDGET-INTEGRATION-20261110**, thread
  `PRRT_kwDOTH_vCM61qASx`, comment 4523811864.
  The review reproduced slow DNS in the deterministic
  `Investigation.run_workflow()` lane, confirming the same underlying
  preflight blockage as comment 4523761630 in the native source retrieval
  lane. The single bounded resolver-worker correction and regressions in
  the preceding section address both contexts. Separate reviews do not
  imply independent experiments or two different root causes.

These are corrective candidates until hosted tests on the new exact head
and a fresh authenticated substantive review pass. The last attempted
Codex request was rejected by the service's review usage limit; that
external block is explicitly unresolved. Neither this ledger nor
resolving a thread substitutes for a clean exact-head Codex review or
the protected `review-convergence`, `merge-authority` and
`protected-repin-gate` checks.

## November 10, 2026 — connection-time DNS deadline bypass, exact-head review

**ENG-CONNECTION-DNS-DEADLINE-20261110** — independent exact-head Codex review
of `6783dfc8fca53d35da8b46874fabda391addecc2`, thread
`PRRT_kwDOTH_vCM61uQRG`, comment 4525629209.

**Observed counterexample:** A quick successful `validate_url` DNS preflight
does not bound the separate DNS lookup in `HTTPSConnection.connect()`.
The reviewer observed roughly 230 ms elapsed despite 50 ms configured
transport and absolute budgets when the second lookup stalled for 220 ms.
The existing socket idle timeout cannot stop synchronous `getaddrinfo`.

**Root-cause correction:** Native deadline adapters now install an isolated
`HTTPConnection._create_connection` / `HTTPSConnection._create_connection`
callable per request. Its DNS lookup runs in a finite, capacity-limited daemon
worker with a monotonic wait bounded by both the remaining request deadline
and configured socket timeout. A timed-out lookup cannot start socket
connections; only the caller connects resolved addresses, with each attempt
bounded by the same remaining deadline. Numeric addresses avoid DNS.
Native urllib still owns the configured proxy/redirect and TLS context,
hostname/SNI, CONNECT tunnel and certificate decisions. No global resolver
or transport monkeypatch is installed and the supplied opener is not mutated.

**Regressions:** `test_native_connection_dns_cannot_outlive_successful_preflight`
reproduces the previously unbounded second lookup after a valid preflight
and requires a bounded failed receipt without opening a socket;
`test_connection_dns_deadline_also_bounds_explicit_proxy` covers proxy-host
resolution; `test_deadline_native_connection_uses_resolved_address_with_socket_timeout`
is the timely positive connection factory. Existing frozen evidence,
native socketpair/TLS/proxy tests, exact-head hosted validation and independent
review remain separate requirements.

**Limits:** Uncooperative resolver threads cannot be killed; they retain
one of eight slots until actually terminating. The preflight and
connection-time DNS pools are separately bounded. This fix bounds time
spent waiting on DNS without claiming DNS result authenticity, general
network security, complete whole-process resource elimination, or real-world
agent reliability. Prior closed review findings are not reopened by metadata.

## November 10, 2026 — TLS handshake inherited stale TCP-connect timeout

**ENG-POST-CONNECT-TLS-DEADLINE-20261110** — authenticated Codex review of
`705ef4464f016e3f9d9bb4ef300c11fa0d5c669a`, thread
`PRRT_kwDOTH_vCM61vE8u`, comment 4525980810 (P2).

**Counterexample:** DNS resolution completes immediately, but TCP connection
uses most of the budget before returning. The socket previously retained its
pre-connect idle timeout. HTTPSConnection then began TLS negotiation using
that stale timeout and could stall beyond the absolute request deadline before
any header deadline reader ran. The reviewer measured approximately 193 ms
against a 100 ms deadline using an 80 ms connect and a stalled TLS peer.
This is independent of the corrected DNS preflight and connection-time
resolver timeout failures.

**Correction:** Immediately after a successful native TCP connection, compute
the remaining monotonic request budget and apply it to the returned socket
before urllib's TLS/CONNECT machinery takes ownership. If the budget is
exhausted, close the socket and fail instead of performing a TLS handshake.
No global monkeypatch, operator TLS-context override, proxy configuration,
or frozen scientific evidence is changed.

**New regression controls:**
`test_native_connect_refreshes_tls_socket_budget_after_tcp` demonstrates
that a delayed successful TCP connect lowers the timeout that TLS inherits;
`test_native_connect_exhausted_budget_closes_before_tls` enforces closure
and fail-closed behavior when connect consumes the entire budget. Existing
HTTPS TLS-context/hostname, retry, native framing, DNS and source receipt
regressions remain required. A clean exact-head hosted test and independent
substantive review remain separate obligations; green checks alone do not
promote scientific validity or authorize protected merge.

## November 10, 2026 — per-address socket construction fallback

**ENG-ADDRESS-FAMILY-SOCKET-CONSTRUCTION-20261110** — authenticated Codex
exact-head review of `03b60d946310b3e87cdb7a102b6549a7b5972a35`, thread
`PRRT_kwDOTH_vCM61wi7t`, comment 4526606546 (P2).

**Counterexample:** Native connection-time DNS returns AF_INET6 before a
usable AF_INET result. On an IPv4-only host, constructing the IPv6 socket
raises `OSError(EAFNOSUPPORT)` before the per-address retry handler starts;
the IPv4 address is never attempted. Python's native `create_connection`
would try later addresses. This regression affects the new deadline-aware
connection adapter, not frozen investigation research evidence.

**Root cause and repair:** Socket construction was outside the existing
per-address `try/except OSError`. Move it inside, initialize the socket
handle to `None`, and close only successfully constructed handles. The
remaining monotonic deadline is recomputed on each candidate; hostname,
operator TLS, proxy and deadline checks are retained. A construction error
now falls through to later usable addresses and propagates when exhausted.

**Regression controls:**
`test_native_connection_retries_ipv4_when_ipv6_socket_creation_fails`
reproduces EAFNOSUPPORT on the IPv6 attempt then verifies that IPv4 connects
with no premature socket closure. `test_native_socket_creation_failure_keeps_last_error`
verifies the real native error is propagated when there is no fallback.
These are controlled offline socket mocks, not measured real-host IPv6
availability, and neither source truth nor general autonomy is established.
Hosted exact-head execution and authenticated independent review on any
new head remain mandatory before protected merge.

## November 10, 2026 — exact-integrated-head model-data provenance findings

**ENG-EVENT-TRANSPORT-OWNER-20261110** — authenticated Codex review of
`8e084b4f27ba0eb4ff51e43ca70ece0e1108b456`, thread
`PRRT_kwDOTH_vCM61zF7p`, comment 4527704385 (P2).

**Counterexample:** LocalModel's supported `message.content` response
fallback returns a malformed tool proposal with a top-level `transport`
object. The runtime correctly rejects the extra proposal field and continues
the bounded pipeline, but offline audit treats `TOOL_PROPOSAL.payload.transport`
as trusted HTTP evidence solely because its dictionary path looks like a
native transport envelope. Arbitrary `timing_scope` or `raw_response_base64`
data triggers false audit failures.

**Correction:** Determine ownership from the actual event kind plus exact
transport suffix before validating native timing and transport bytes.
Only established transport-producing events (`MODEL_OBSERVATION`,
`HTTP_OBSERVATION`, `SEARCH_OBSERVATION`,
`SEARCH_RECHECK_OBSERVATION`, `TOOL_REJECTED`, `SOURCE_RECHECK`,
`SEARCH_RECHECK`, and model-proposal's native metadata envelope) qualify
at their corresponding paths. Rejected tool proposals are never promoted
into native transport observations. Other source and model transport owner
paths retain their previous validation; no valid provenance is suppressed.

**Control:** `test_native_rejected_top_level_transport_does_not_become_http_evidence`
uses LocalModel's real content fallback, bounded native HTTP reader envelope,
rejected proposal plus full legitimate script, then audits the resulting
chronological transcript.

**ENG-NATIVE-MODEL-ID-REPLAY-20261110** — authenticated Codex review of
`8e084b4f27ba0eb4ff51e43ca70ece0e1108b456`, thread
`PRRT_kwDOTH_vCM61zF7x`, comment 4527704394 (P2).

**Counterexample:** A resealed LocalModel transcript replaces the final
native model response's `model` field with a dictionary or text longer than
512 characters and updates all mirrored raw-body/hash/length and metadata
copies. The auditor previously checked only equality between the two invalid
values; the producer runtime rejects that identifier before proposing tools.

**Correction:** Replay enforces the exact native runtime constraint:
`model` must be absent/null or exactly a Python string of at most 512
characters, in addition to matching the retained proposal metadata.
`test_native_model_identifier_replay_enforces_actual_runtime_limits`
validates legitimate full native replay then reseals dictionary and oversized
model identifiers across response bytes and mirrored metadata, requiring
offline audit rejection in both cases.

These are source-to-replay consistency properties, not proof of the external
model's identity or scientific claim validity. The frozen negative results
and research evidence are unmodified. Hosted exact-head tests and fresh
independent exact-head review are separately required before protected merge.


## November 10, 2026 — chronological ownership of identical search results

**ENG-SEARCH-DUPLICATE-PRODUCER-20261110** (internal root-cause audit; PR comment 6774076217): the offline auditor reserved the first retained search row for a later accepted attempt merely because the two result values matched. Runtime `_dispatch('search')` appends a result before invalidating the existing discovery; if its `DISCOVERY_INVALIDATED` checkpoint raises `OSError`, that first rejected-but-dispatched attempt legitimately owns a retained row. A retry with an identical request and response can append an identical second row and succeed. The previous `successful_search_at` reservation misattributes both and can reject an unmodified, model-selected, bounded completion.

**Correction:** commit `b3a67ac9e8e1df7f0052a8963f8ecd269d64e5b4` requires actual query/provider/receipt-observation binding and either an accepted producer or a demonstrated post-dispatch mutation, allocating duplicate retained rows in chronological attempt order. **Regressions:** `test_failed_postdispatch_search_retry_keeps_both_identical_retained_rows` in commit `8b2782b7f86e9a65b4a04bc14baaabc128291136` exercises the failed-checkpoint/accepted-retry path; the existing `test_identical_failed_search_observation_cannot_consume_a_later_retry` protects a failure *before* any row is retained. Both passed in the hosted exact-head Investigation Engine runtime step of run 42864359899 (351 tests, 5 optional skips); complete workflow, separate exact-head independent review and protected merge requirements remain outstanding. This preserves original frozen negative evidence.

## Known review-failure-class coverage index (2026-11-10)

This Research-status index classifies **every unique recorded root-cause ID** in the preceding ledger, including inherited historical fixes, into one primary testable failure class. The controls below are *representative existing regression methods* for each class, not one-to-one proofs for every root-cause ID. In particular, a method's existence is not a proof that it detects every member of its class. These are engineering-level controlled tests, not independent scientific replication, source truth, general agent reliability, or evidence that any future defect is impossible. Missing original Open Deep Research source binding remains BLOCKED_GOVERNANCE. Original frozen results remain unchanged.

New root-cause IDs require corresponding class allocation and evidence-linked tests before claiming class-level coverage. Do not weaken or hide a failing check to satisfy this index. The class-index contract verifies inventory identity and named test presence only; behavioral adequacy requires actual negative and positive regression execution and exact-head independent review.

<!-- BEGIN FAR-INVESTIGATION-FAILURE-CLASS-COVERAGE/1 -->
```json
{
  "schema": "far-investigation-failure-class-coverage/1",
  "scope": "Finding IDs in the PR #614 Research ledger, including inherited #608 historical findings",
  "classes": [
    {
      "name": "execution_environment_and_identity",
      "purpose": "Real child/process ownership, correct launcher identity, and raw-input fixture fidelity.",
      "negative_controls": [
        "tests.test_far_investigation_campaign.CampaignTests.test_occupied_model_endpoint_cannot_attest_an_executable_that_exits_43"
      ],
      "positive_controls": [
        "tests.test_far_investigation_campaign.CampaignTests.test_live_child_listener_command_and_mapped_model_are_bound_together",
        "tests.test_far_routing_dispatch.KnownContractRoutingTests.test_crlf_file_and_stdin_preserve_raw_hash"
      ],
      "finding_ids": [
        "ENG-CAMPAIGN-FIXTURE-LOCK",
        "ENG-CANONICAL-PYTHON-LAUNCHER",
        "ENG-SERVER-OWNERSHIP",
        "HIST-608-CRLF",
        "HIST-608-TEST-CRLF"
      ]
    },
    {
      "name": "native_verification_and_semantics",
      "purpose": "Native verification rejects forged inputs and keeps bounded witnesses and fallible semantic interpretation separate.",
      "negative_controls": [
        "tests.test_far_investigation_verifiers.NativeVerifierTests.test_forged_binding_rejected"
      ],
      "positive_controls": [
        "tests.test_far_investigation_campaign.CampaignTests.test_empty_counterexample_valuation_counts_as_a_native_witness",
        "tests.test_far_investigation_verifiers.NativeVerifierTests.test_exact_decimal_arithmetic_avoids_float_error"
      ],
      "finding_ids": [
        "ENG-EMPTY-WITNESS",
        "HIST-608-OPEN",
        "RC608-VERIFIER-JOURNAL"
      ]
    },
    {
      "name": "model_protocol_and_admission",
      "purpose": "Native model request/response shapes, provenance, routing, nesting, token telemetry, and action admission.",
      "negative_controls": [
        "tests.test_far_investigation_audit.OfflineInvestigationAuditTests.test_native_replay_rejects_over_nested_model_proposal",
        "tests.test_far_investigation_engine.InvestigationIntegrationTests.test_local_model_redirect_cannot_escape_attested_listener"
      ],
      "positive_controls": [
        "tests.test_far_investigation_audit.OfflineInvestigationAuditTests.test_live_shaped_single_function_call_envelope_reconstructs_actual_arguments"
      ],
      "finding_ids": [
        "ENG-FAILED-MODEL-TRANSPORT-BYTE-BINDING-20261110",
        "ENG-FAILED-MODEL-USAGE",
        "ENG-FUNCTION-TRANSPORT",
        "ENG-LOCAL-MODEL-PROXY-20261109",
        "ENG-LOCAL-MODEL-REDIRECT-20261109",
        "ENG-MODEL-ARGS-DEPTH-20261109",
        "ENG-MODEL-ATTEMPT-STEPS-20261109",
        "ENG-MODEL-BODY-DEADLINE-20261109",
        "ENG-MODEL-CHRONOLOGICAL-PROMPT-20261109",
        "ENG-MODEL-ID-METADATA-DEPTH-20261109",
        "ENG-MODEL-MESSAGE-SHAPE-20261109",
        "ENG-MODEL-NATIVE-BYTE-CEILING-20261110",
        "ENG-MODEL-QUESTION-ATTRIBUTION-20261109",
        "ENG-NATIVE-MODEL-ID-REPLAY-20261110",
        "ENG-REJECTED-ARGUMENT-ENVELOPE-20261109",
        "HIST-608-MODEL-200",
        "RC608-MODEL-REDIRECT"
      ]
    },
    {
      "name": "producer_attribution_and_offline_replay",
      "purpose": "Recorded receipts, proposals, evidence, comparisons and native results derive from their actual producing attempts.",
      "negative_controls": [
        "tests.test_far_investigation_audit.OfflineInvestigationAuditTests.test_resealed_comparison_copies_are_reconstructed_from_the_proposal",
        "tests.test_far_investigation_audit.OfflineInvestigationAuditTests.test_native_rejected_top_level_transport_does_not_become_http_evidence"
      ],
      "positive_controls": [
        "tests.test_far_investigation_audit.OfflineInvestigationAuditTests.test_postdiscovery_rejected_comparison_retry_retains_both_identical_rows",
        "tests.test_far_investigation_audit.OfflineInvestigationAuditTests.test_valid_agent_and_both_workflows_reconstruct_without_network_or_model"
      ],
      "finding_ids": [
        "ENG-ACCEPTED-CHECKPOINT-DURABILITY",
        "ENG-COMPARISON-PROPOSAL",
        "ENG-DISPATCH-PRECONDITIONS",
        "ENG-EVENT-TRANSPORT-OWNER-20261110",
        "ENG-EXTRACTION-PROPOSAL",
        "ENG-FAILED-SEARCH-RESERVATION-20261109",
        "ENG-FINISH-REPORT-PROPOSAL",
        "ENG-NATIVE-OPERATION-PRODUCER",
        "ENG-NATIVE-PARSER-METADATA",
        "ENG-OBSERVED-SOURCE-ENVELOPE-20261109",
        "ENG-OFFLINE-AUDIT",
        "ENG-PLAIN-TEXT-JSON-DEPTH-20261109",
        "ENG-PROPOSAL-CHECKPOINT-OUTCOME",
        "ENG-RECEIPT-SCHEMA-COLLISION-20261109",
        "ENG-REJECTED-NATIVE-EFFECTS",
        "ENG-REPEATED-READ",
        "ENG-RETRY-EFFECT-PRODUCER-20261110",
        "ENG-SEARCH-DUPLICATE-PRODUCER-20261110",
        "ENG-SOURCE-ALLOCATION",
        "ENG-SOURCE-DEPTH-20261109",
        "ENG-SOURCE-PARSER-STACK-20261109",
        "ENG-UNTRUSTED-JSON-ENVELOPE-COLLISION",
        "ENG-UNTRUSTED-NESTED-REQUEST-CHECKSUM-20261110",
        "HIST-608-SOURCE-200"
      ]
    },
    {
      "name": "http_transport_framing_and_timeouts",
      "purpose": "Transport deadlines, framing, content-length, provenance of bounded byte prefixes, and source/model reader agreement.",
      "negative_controls": [
        "tests.test_far_uncertain_routing_pilot.NativeFramingTests.test_real_chunk_separator_trickle_uses_remaining_absolute_deadline",
        "tests.test_far_investigation_retrieval.RetrievalTests.test_native_short_and_malformed_chunk_framing_cannot_support_evidence"
      ],
      "positive_controls": [
        "tests.test_far_investigation_retrieval.RetrievalTests.test_native_complete_length_and_chunks_are_accepted"
      ],
      "finding_ids": [
        "ENG-BODY-PREFIX-DURABILITY-20261109",
        "ENG-CHUNK-FRAMING-DEADLINE-20261109",
        "ENG-CHUNK-SEPARATOR-DEADLINE-20261110",
        "ENG-CONFIGURED-TRANSPORT-TIMEOUT-20261110",
        "ENG-FAILED-TRANSPORT-BYTE-BINDING-20261109",
        "ENG-HEADER-DEADLINE-20261109",
        "ENG-NATIVE-FRAMING-BINDING",
        "ENG-NONCHUNKED-BODY-ABSOLUTE-DEADLINE-20261109",
        "ENG-SOURCE-BYTE-CEILING",
        "ENG-SOURCE-DEADLINE-20261109",
        "ENG-SOURCE-FRAMING",
        "ENG-SOURCE-TRANSPORT-BINDING",
        "ENG-TERMINAL-TRANSPORT-BINDING",
        "ENG-TRANSPORT-TIME",
        "ENG-TRANSPORT-TIMESTAMP-SCOPE-20261109",
        "HTTP-FRAMING-01",
        "RC608-HTTP-EVIDENCE"
      ]
    },
    {
      "name": "discovery_recheck_and_freeze",
      "purpose": "Search/source chronology and terminal rechecks produce valid discovery and freeze only after observed completeness.",
      "negative_controls": [
        "tests.test_far_investigation_engine.InvestigationIntegrationTests.test_failed_second_search_recheck_cannot_reuse_old_saturation_timestamp",
        "tests.test_far_investigation_audit.OfflineInvestigationAuditTests.test_undispatched_freeze_rejection_cannot_steal_retried_freeze"
      ],
      "positive_controls": [
        "tests.test_far_investigation_engine.InvestigationIntegrationTests.test_full_scripted_pipeline_executes_actual_injected_tools"
      ],
      "finding_ids": [
        "ENG-DISCOVERY-PROPOSAL",
        "ENG-FAILED-RECHECK-RESERVATION-20261109",
        "ENG-FREEZE-PRODUCER-ATTRIBUTION-20261110",
        "ENG-LATEST-RECHECK-COMPLETION",
        "ENG-RECHECK-DEADLINE-20261109",
        "ENG-RECHECK-ORIGINAL-PROJECTION",
        "ENG-RECHECK-PREAPPEND-CHECKPOINT",
        "ENG-SEARCH-CHRONOLOGY",
        "ENG-STALE-RECHECK",
        "ENG-TEMPORAL-SOURCE-REPLAY"
      ]
    },
    {
      "name": "resource_limits_and_terminal_state",
      "purpose": "Token, step, HTTP, elapsed-time, and finalization budgets bind outcomes and forbid continuation after terminal exhaustion.",
      "negative_controls": [
        "tests.test_far_investigation_audit.OfflineInvestigationAuditTests.test_resealed_wall_clock_exhaustion_cannot_continue_to_completion",
        "tests.test_far_investigation_engine.InvestigationIntegrationTests.test_completion_journal_cost_cannot_escape_the_final_budget_in_any_lane"
      ],
      "positive_controls": [
        "tests.test_far_investigation_engine.InvestigationIntegrationTests.test_full_scripted_pipeline_executes_actual_injected_tools"
      ],
      "finding_ids": [
        "ENG-BUDGET-PARITY",
        "ENG-DNS-TRANSPORT-BUDGET-INTEGRATION-20261110",
        "ENG-FINISH-TRANSACTION",
        "ENG-RESOURCE-SCALARS",
        "ENG-TERMINAL-FAILURE-STATUS-20261110",
        "ENG-TOKEN-DISPATCH-ELIGIBILITY"
      ]
    },
    {
      "name": "campaign_archive_and_comparator",
      "purpose": "Frozen selection and campaign identity, archive integrity, honest scoring and missing-comparator evidence boundaries.",
      "negative_controls": [
        "tests.test_far_investigation_campaign.RetainedCampaignReplayTests.test_duplicate_zip_member_cannot_shadow_evidence",
        "tests.test_far_investigation_odr_preparation.ODRPreparationBoundaryTests.test_missing_original_source_is_not_fabricated"
      ],
      "positive_controls": [
        "tests.test_far_investigation_campaign.RetainedCampaignReplayTests.test_original_exact_archive_replays_24_transcripts"
      ],
      "finding_ids": [
        "ENG-BASELINE-ALGORITHM-BINDING-20261109",
        "ENG-BASELINE-DRAFT-CONTINUATION",
        "ENG-BASELINE-RETAINED-EVIDENCE",
        "ENG-CAMPAIGN-CLAIMS",
        "ENG-CAMPAIGN-EXPOSURE",
        "ENG-CAMPAIGN-IDENTITY",
        "ENG-CAMPAIGN-INDEX-BOUNDS",
        "ENG-CAMPAIGN-RECORDING-BOUNDS",
        "ENG-CAMPAIGN-SHADOW",
        "ENG-COMPARATOR-SOURCE",
        "ENG-DUPLICATE-CAMPAIGN-LANE-20261109",
        "ENG-REGISTERED-SOURCE-EXPOSURE"
      ]
    },
    {
      "name": "network_policy_and_connection",
      "purpose": "DNS/SSRF, proxy, redirect, TLS, socket ownership and connection-level boundedness.",
      "negative_controls": [
        "tests.test_far_investigation_retrieval.RetrievalTests.test_exact_policy_rejects_network_escape_before_open",
        "tests.test_far_investigation_retrieval.RetrievalTests.test_connection_dns_deadline_also_bounds_explicit_proxy"
      ],
      "positive_controls": [
        "tests.test_far_investigation_retrieval.RetrievalTests.test_native_connection_retries_ipv4_when_ipv6_socket_creation_fails"
      ],
      "finding_ids": [
        "ENG-ADDRESS-FAMILY-SOCKET-CONSTRUCTION-20261110",
        "ENG-CONNECTION-DNS-DEADLINE-20261110",
        "ENG-DEADLINE-OPERATOR-TLS-20261110",
        "ENG-DNS-PREFLIGHT-DEADLINE-20261110",
        "ENG-OPENER-REQUEST-SCOPE-20261110",
        "ENG-POST-CONNECT-TLS-DEADLINE-20261110",
        "ENG-RECORDED-DNS-PREFLIGHT",
        "ENG-RETAINED-REQUEST-METHOD-20261109",
        "ENG-TLS-HOSTNAME-OVERRIDE-PY311-20261110"
      ]
    }
  ]
}
```
<!-- END FAR-INVESTIGATION-FAILURE-CLASS-COVERAGE/1 -->
