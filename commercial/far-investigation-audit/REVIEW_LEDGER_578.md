# PR #578 review convergence and defect ledger

**Scope:** Research-only investigation lab v0.4.3. This ledger records reviewed invariants, reproducible counterexamples and correction evidence. It grants no independent scientific, factual-verdict, source-authenticity, or production-security status.

**Original reviewed head:** `181e7abc531e17e9c7322c62e0945f5e40dfaa0b`.
**Protected main and merge base at intake:** `959a2c3cce9935963882b7856c7de31d54179ac5`.
**Reviewer:** `chatgpt-codex-connector`, 2026-10-20 15:17 UTC. One submitted Codex review; six unresolved in-scope comments when triaged; no distinct human approval was recorded.
**Reproducer-only head:** `3a77279098d19a82dc93d52174001be01f78d40f`. Hosted [FAR Bounded Investigation Audit run 39454138156](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/39454138156), Python 3.11 and 3.13: all six new regression tests **FAILED** before correction; 137 tests run, one pre-existing optional skip on Python 3.11. These are genuine red tests, not presumed defects.

| Invariant/defect key | Reviewed comment | Verified before-fix counterexample | Root-cause repair | Correction-specific regression |
|---|---|---|---|---|
| `REPLAY-EXTRACTION-IDENTITY` | [4326698367](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4326698367) | Rewrite a text acquisition as permitted nonreplayable PDF; omit raw bytes and regenerate the derived report/manifest while audit hash is unchanged | SHA-256 commitment to the **entire** per-source acquisition record in the audited input; replay independently compares acquisition and binding | `test_replay_method_downgrade_cannot_keep_original_audit_identity` |
| `ORIGIN-DESIGN-DIVERSITY` | [4326698394](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4326698394) | Rewrite both finding origin and aggregate as `origin-B` while source specifies `origin-A`; old independent checker agrees | Recheck each finding against source record; rebuild claim origin sets from sources rather than from report claims | `test_source_origin_must_be_checked_independently` |
| `NO-SELF-CORROBORATION` | [4326698411](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4326698411) | One-character shorter same-source span obtains false conditional support | Same-source **span intersection** rejected by primary and independent engines for propositional and numeric evidence | `test_overlapping_same_source_claim_is_not_corrobating_evidence` |
| `STRUCTURED-SUMMARY-INDEPENDENCE` | [4326698424](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4326698424) | Single matching JSON count re-labelled to 99 mismatches/CONFLICTING, with cross-check still agreeing | Independently reconstruct all numeric status/denominators, including snapshot-only and unverifiable partitions | `test_independent_checker_detects_forged_structured_summary` |
| `REMOTE-CAPTURE-AFTER-FETCH` | [4326698439](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4326698439) | Fetch starts at cutoff and completes later, yet capture is falsely equal to cutoff | Store completion clock for every live source/discovery acquisition; preserve a separate investigation cutoff | `test_remote_capture_is_recorded_after_fetch_not_at_cutoff` |
| `UNTRUSTED-MARKDOWN-NEUTRALIZATION` | [4326698451](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4326698451) | A raw HTML tag and Markdown link in proposal unknowns persist in downloadable report | Escape HTML and Markdown syntax in model-supplied prose, interpretation card values, source metadata, and critical questions; report replay remains deterministic | `test_report_escapes_untrusted_html_and_markdown` |

**Finding disposition:** Six current findings reproduced and assigned structural fixes. Zero rejected, duplicated or speculative findings among the six. The previous PR conversation includes historical integration and billing notes, not distinct code-review findings. Completion status must be set only after successful final-head validation and independent review.

### Correction-induced defect, separately reproduced

- **`PRESENTATION-EXACT-SOURCE-QUOTE`** was discovered after implementing the Markdown injection fix: the previous HTML escape and triple-backtick substitution rewrote attributed source content shown in the downloadable report. The attribution and hash in the JSON remained exact, but the human-readable quotation was no longer a literal reproduction.
- **Red test proof:** New `test_report_quote_preserves_exact_markup_and_backticks_as_code` committed at `9e66c5d322db9ead14ff52bbe01505098728c305`; hosted [run 39456944132](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/39456944132) failed that test on Python 3.11 and 3.13 (138 tests, one new failure, one optional skip). Exact literal `<img ...>` and ``` were rewritten to entities and spaced backticks.
- **Root-cause correction:** Instead of modifying raw quoted bytes, `presentation.py` uses an adaptive Markdown code fence longer than any run of backticks in the untrusted quote. Fenced code prevents executable markup without corrupting the visible quotation. Independent compilation and package replay remain required on the final head.
- **Scope:** A report-output integrity and security correction; neither source authenticity nor natural-language fidelity is promoted by faithful quotation.


## Second independent Codex review: substantive new findings

**Reviewed code head:** `77dddabe451132dac6a29e802768addcbac27eb0`.
**Reviewer:** `chatgpt-codex-connector[bot]`, review submitted 2026-10-20 16:22:50 UTC. Five valid findings; none dismissed as duplicates, style or speculation. The two interpretation defects share a checker-coverage root cause and were corrected together.

**Falsifying test-only head:** `e149ba276b6fba7387c788b7d32d70c19a0b9757`. Hosted [FAR Bounded Investigation Audit run 39457706458](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/39457706458): Python 3.11 and 3.13 ran **144** tests each, with 5 new assertion failures and 1 new IndependentCheckError, 1 previously optional skip. The six red regressions identify root causes directly.

| Invariant / defect | Reviewed finding | Reproduction and root-cause correction | Red/green test |
|---|---|---|---|
| `INDEPENDENT-NUMERIC-DOMAIN` | [4327410018](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4327410018) | `sum_field` over `[{"x":1e100}]` gives valid `STRUCTURED_UNVERIFIABLE` from engine, but old Fraction oracle accepts out-of-domain source number and calls it a mismatch. Enforce 40-digit coefficient and 40-exponent bounds separately before Fraction arithmetic | `test_numeric_oracle_respects_bounded_decimal_contract` |
| `PROVIDER-CALLS-NETWORK-PROVENANCE` | [4327410029](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4327410029) | External model proposal and transcription can transmit text/audio while `manifest.network_used` is false. Include these providers in the source/network manifest flag. Model/provenance fixtures separately reproduce both paths | `test_external_model_proposal_declares_provider_network_usage`, `test_external_transcription_declares_provider_network_usage` |
| `SIGNED-REVIEW-UNAMBIGUOUS-IDENTITY` | [4327410036](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4327410036) | Signed `object_id: c1` can refer to both a claim and evidence record named `c1`. A correct Ed25519 signature cannot disambiguate the review. Reject ambiguous reviewed ID references, retaining allowed namespace-local IDs for unrelated audit operations | `test_signed_review_rejects_ambiguous_cross_type_object_identity` |
| `INTERPRETATION-OPERANDS-COMMITMENT` | [4327410044](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4327410044) | Forge reported reading operands and unsupported-premise list while reusing unchanged valid `formal_inference`; old oracle accepted. Independently bind all report reading metadata and premise-evidence list to declared bundle and independently checked claim statuses | `test_checker_binds_reported_interpretation_operands_and_premises` |
| `INTERPRETATION-ID-BIJECTION` | [4327410051](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4327410051) | Duplicate a valid reading result and omit a second registered reading, preserving list length and logical result; old oracle accepted. Require exact 1:1 ID set and no duplicates before checking content | `test_checker_rejects_duplicate_interpretations_with_missing_reading` |

**Provider provenance replay hardening:** The same `PROVIDER-CALLS-NETWORK-PROVENANCE` root cause also affects the unsigned manifest verifier. A package legitimately generated with a model call could have only `manifest.network_used` flipped to `false` without changing any recorded artifact hash, and replay would have accepted it. Regression `test_model_network_provenance_survives_manifest_replay` introduced at `533064087076767d9af04f986bd02b1c805363b6`; `full_cli.verify_package` now independently requires truthful positive network disclosure whenever archived proposal, transcription, URL, or discovery records identify an external route. The verifier does not claim to prove external calls absent when no route is archived; it checks a one-way integrity obligation. Verify red/green hosted logs for this new regression before release.

**Important limit:** This Codex finding cycle was performed on `77ddd...`, superseded by later corrections, and is not an independent clean final-head signoff. The next review must reference the newly stabilized SHA, challenge these regressions and their integration, and receive the protected-repin App's own final-head decision.

## Third Codex review: verification-boundary defects

**Reviewed code head:** `80de02898ad7466b1737704d8c2abc13504a2f80`.
**Reviewer:** `chatgpt-codex-connector[bot]` at 2026-10-20 16:44:04 UTC. All four findings are valid, substantive, new at the indicated invariant level, and originally reproducible.

**Falsifying test-only head:** `4edc58f0b5087bb8935a47340f93b76999e5e33a`. Hosted [FAR Bounded Investigation Audit run 39460346172](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/39460346172), Python 3.11 and 3.13: 149 tests, **six intentionally failing assertions** (the report-flag case uses three independent subtests), one optional skip, 0 unrelated failures.

| Invariant / defect | Source review finding | Reproducer and structural correction | Regression |
|---|---|---|---|
| `PROPOSAL-PROVIDER-COMMITMENT` | [4327628856](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4327628856) | Change model-proposal route to supplied, delete model metadata, adjust unsigned proposal hash/manifest fields and claim `network_used=false`; original audited input/report identity remains unchanged. `compile_proposal` now binds **SHA-256 of the complete proposal** (method/model and all fields) into the audited input, validated in engine and independently compared with `proposal.json` by package replay | `test_proposal_provider_downgrade_cannot_preserve_audit_identity` |
| `INTERPRETATION-REPORT-WIDE-AGGREGATION` | [4327628873](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4327628873) | Flip the three report-wide interpretation flags on an otherwise correct two-reading report; prior `check_report` still agreed. After independently checking each reading, recompute `interpretation_sensitive_inference`, `interpretation_cards_differ`, and `interpretations_present` | `test_independent_checker_rebuilds_report_wide_interpretation_flags` (three subtests) |
| `NO-UNAUTHENTICATED-MAPPING-PROMOTION` | [4327628887](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4327628887) | Falsely promote claim and evidence `mapping_status` to `review_recorded`; previous checker accepted. Independently compare both mapping fields against input, and require `origin_independence_verified=false` | `test_checker_refuses_promotion_of_unreviewed_semantic_mappings` |
| `MANIFEST-PREPARSE-BOUNDS` | [4327628895](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4327628895) | Append 6,000,001 whitespace bytes to otherwise valid manifest; old verifier parses arbitrarily oversized JSON. Require non-symlink regular manifest, <=6 MB, before parsing | `test_manifest_size_is_bounded_before_read_or_parse` |

**Convergence diagnosis:** The first two review cycles exposed missing independent bindings for distinct derived surfaces: acquisitions, proposal provenance, per-evidence metadata, per-reading metadata, aggregate flags, and unsigned delivery metadata. The corrected source-to-audit input commitments and report cross-check now cover the reported subclasses. A new review is permitted only on a stabilized SHA after a completed full validation, for a substantive independent final-head check. Do not claim that the ledger or this agent's verification is independent human approval or that absence of further reviewer comments establishes absolute correctness.

## Consolidated independent-oracle surface audit (third-review root-cause expansion)

Following the third review, the audit examined every already-declared output field rather than requesting a new automated review before checking the remaining nearby contract:

- **`STRUCTURED-DISPLAY-BINDING`:** Independent numeric calculations already verified status and number but omitted `declared_value`, `unit`, `operation`, `rows_inspected`, `structured_temporal_eligibility`, origin/authenticity markers and the discrepancy flag. This can misstate the evidence scope or appear authenticated with a formally correct numerical result. Correction independently checks the complete structured-result schema, admissibility, operation, row denominator, claim-bound unit/value, nonverification flags and discrepancy annotation. A nonempty reason is required for `STRUCTURED_UNVERIFIABLE` without pretending that the independent oracle reproduced the human-readable reason text.
- **`BOUNDARY-CONSERVATION`:** `check_report` accepted a report whose `unknowns` removed safeguards or whose `assurance_boundary.real_world_truth` falsely claimed certification. Correction compares unknowns with input and requires the complete declared nonproduction assurance contract.
- **Red counterexamples:** `test_independent_checker_binds_structured_display_and_provenance_metadata` exercises eight mutated subfields; `test_independent_checker_preserves_assurance_boundaries_and_unknowns` mutates two blocker fields. Test-only SHA `33243ab3765e57b2c689aa3049ddc1d7ef6efcca`; [hosted run 39460967051](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/39460967051) provides its exact red-test results. These are additional structural strengthening tests, not an instruction to expand product features.
- **Threat-model boundary:** All these checks inspect declared inputs and internally generated metadata. They do not verify independent source truth, reviewer identity, whether an operator genuinely used an external API, or correctness of text-to-logic mapping.

## Verification obligations and limits

- **Source replay:** Hashes of untrusted snapshots and commitment to the recorded acquisition method now participate in the audit identity; source authenticity remains unestablished. Replacement of an entire unsigned package, including recomputed audit bytes, remains possible absent external trusted signatures.
- **Temporal admissibility:** Publication flags alone do not authenticate real historical evidence; a source observed after the declared cutoff cannot supply in-window evidence. Distinguish provider completion timestamps from investigation start.
- **Evidence relations:** Self-overlapping spans cannot corroborate their own primary claim. Formal support and contradiction still depend on unverified text-to-formula mapping.
- **Independent checks:** Separate bitmask inference and Fraction numeric calculations remain limited to their declared deterministic contracts. Verify per-evidence origin and claim-level numerical aggregation to avoid correlated report errors.
- **Field scoring:** Distinguish `SUPPORTED`/`REFUTED` decisive verdicts from `INSUFFICIENT` and `ABSTAIN`. No real-world verdict coverage has been demonstrated by this adapter.
- **Security:** HTML/Markdown is untrusted; report rendering cannot promote scripts or spoofed Markdown commands. The HTTP service remains loopback-only and unauthenticated.
- **Release:** The review must cite the final immutable PR head; hosted suite, `exact-head-assurance`, `merge-authority`, and the distinct protected-repin App must pass there. A substantive independent external review is required. An author's own work cannot satisfy it.

## Review-convergence protocol

A new review request requires a materially changed head or a new stated verification objective. Classify new comments by invariant and counterexample, not comment ID. Reject repeats already disproven by the existing regression without adding churn. Resolve real new defect classes, revalidate integration on the stable head, and obtain one final independent review referring to that SHA. Do not merge without independent authorization and genuine protected gate results. Tests, synthetic fixtures and automated review never establish open-world truth, semantic fidelity, source provenance, or production-readiness.

## Fourth exact-head Codex cycle — 2026-10-20

**Reviewed exact SHA:** `cb11eae622d16a1b8495e538760974736eb55859` (merged former protected `main` into PR #578).
**Reviewer:** `chatgpt-codex-connector` automated review, independently authored relative to the code changes.
**Result:** Five new concrete issues; none represented by the prior four resolved threads. This cycle reopens integration obligations and supersedes any previous merge-readiness claim.

| Invariant | Primary review discussion | Reproducible exploit / obligation | Root repair / permanent regression |
|---|---|---|---|
| `DISCOVERY-NETWORK-COMMITMENT` | [4330149530](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4330149530) | A Tavily-only, unexpanded discovery call can be erased from the optional file and unsigned manifest while reusing the old report identity and reporting offline execution. | Hash the whole non-expanded discovery receipt into the input bundle, validate hash shape and bind replay to exact archived `discovery.json`; `test_unexpanded_discovery_route_is_immutable_audit_provenance`. |
| `REPORT-IDENTITY-CROSSCHECK` | [4330149544](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4330149544) | Report schema, engine, subject, input SHA, cutoff and self-excluding report SHA can be mutated while the design-diverse checker previously agrees. | Independently recompute source input and report digests plus six identity fields; `test_identity_fields_and_self_excluding_digest_independently_checked`. |
| `HOSTILE-JSON-DEPTH-BOUND` | [4330149556](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4330149556) | Small but deeply nested manifest/other package JSON causes a raw `RecursionError` bypassing the bounded rejection contract. | Translate recursion/JSON exceptions into `InvalidBundle` on all package JSON reads; `test_over_nested_manifest_and_nested_input_fail_closed`. |
| `FIELD-CASE-ID-INJECTION-BOUND` | [4330149568](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4330149568) | Accepted 80-character subject and 80-character claim produce 161-character case ID, rejected by scorer; colon concatenation can also alias distinct identity pairs. | Stable SHA-256 of canonical ordered identity pair with retained original IDs; `test_generated_case_ids_fit_bounds_and_do_not_alias_colon_pairs`. |
| `PROVIDER-ERROR-TRANSLATION` | [4330149578](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4330149578) | Model provider timeouts / API exceptions leaked as raw exceptions instead of documented bounded public workflow failure. | Translate provider-call exceptions to `InvalidBundle`, preserve distinct provider-vs-response-shape error; `test_model_provider_timeout_is_bounded_workflow_error`. |

**Integrated repair follow-up:** A first hosted run on `0fda11647ae4b5320efb51984a08b2c742324bb3`, [run 39496003081](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/39496003081), reported 156 tests with 11 errors and three failures on Python 3.11. The common reconstruction root cause was that `compile_proposal()` reconstructs the signed input without `discovery_sha256`; the final package verifier now restores the archived discovery commitment before comparing canonical bundle bytes. An independent second root cause was `InvalidBundle` being a `ValueError` subtype caught/relabelled by the broad response-shape handler. A specific `except InvalidBundle: raise` preserves the provider failure classification. Both have been corrected; **the initial failing run is not validation of the successor head**.

**Release condition:** complete hosted final-head tests (including this five-test suite) on both Python versions, independent final-head review with no unresolved substantive findings, trusted owner-main review observation, strict merge-authority and protected-repin checks. All claims remain bounded to local proposal/replay and synthetic tests: no real-world fact accuracy, source authenticity, model-call completeness, independently checked source semantics or commercial adoption is inferred.

## Completion inspection and verification

Intake head `3b97856903d8357e9ed014dda93645177351bf2e` executed 156 tests (155 passes, one optional skip) on both Python 3.11 and 3.13 in hosted run [39496457349](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/39496457349), including all five fourth-cycle regressions, compilation, package replay and service import. Full job logs were inspected. These are predecessor results, not validation of subsequent edits.

Completion inspection reproduced additional manifestations of the last two failure invariants on `3b978569`: malformed source objects were dereferenced by the historical-network guard before validation; provider client construction escaped the protected call boundary; deeply nested model JSON escaped parsing. `tests/test_failure_boundaries.py` has four local red-before/green-after tests (the malformed-source test has two cases). Corrections validate source shapes before use, redact both proposal and transcription client setup failures, and translate model JSON recursion. The web JSON ingress now also translates recursion into HTTP 422; its regression additionally requires that a subsequent valid request succeeds, proving the worker permit is released. Local web verification requires unavailable FastAPI dependencies and remains a hosted obligation.

The corrected candidate requires fresh hosted validation and an independent review on its final exact SHA. This record is correction evidence, not self-approval or a claim that optional live providers were exercised.

**Whole-parser correction:** Hosted validation of `440c5713b60830b2b75112a965430f087d8c4303` passed 161 tests (160 passes, one skip) on both Python 3.11 and 3.13; the web recursion/recovery test passed and full source-package replay succeeded. Completion then replayed the same 20 KB nested JSON against the four legacy JSON CLIs (`cli.py`, `verify.py`, `field_validation.py`, `review.py`) and a fake search-provider response. On that predecessor the two new tests produced four failing CLI subtests and one raw `RecursionError`. The correction translates parser recursion at every remaining public JSON ingress, including the field reader and search adapter; the auditor's serialization boundary also translates it. All six local failure-boundary tests and 25 earlier review regressions pass. These are additional manifestations of `HOSTILE-JSON-DEPTH-BOUND`, not an unrelated feature expansion. The final successor still requires its own hosted evidence and independent review.

## Fifth independent review: aggregate bounds and oracle contracts

**Reviewed head:** `26e1460828d6998573f05e9a2b2efa76bc359400`. Seven findings were accepted. The earlier claim that every public JSON parser was covered was incomplete: `evaluate.py` had been omitted. A source enumeration of all JSON parses and file reads now includes that diagnostic entry point, caption utility output, optional review inputs and signing-key input.

| Invariant | Source discussion | Root correction | Permanent regression |
|---|---|---|---|
| `DIAGNOSTIC-JSON-FAILURE` | [4330456271](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4330456271) | Diagnostic JSON parser translates recursion into `FAR_DIAGNOSTIC_INVALID`; added to the shared public-CLI depth test | `test_all_json_clis_reject_parser_recursion_without_tracebacks` |
| `NUMERIC-FAILURE-REASON-INDEPENDENCE` | [4330456291](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4330456291) | Fraction oracle independently classifies parse, pointer, row and numeric-domain failures and compares the complete reported reason | `test_unverifiable_reason_is_recomputed_not_merely_nonempty` |
| `AGGREGATE-ENTAILMENT-WORK` | [4330456302](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4330456302) | Per-audit cache of exact inference pairs and conservative 8,000,000-node-visit total budget, including interpretation checks | `test_aggregate_distinct_entailment_work_is_bounded`, `test_repeated_entailment_pairs_are_computed_once_per_audit` |
| `RAW-SNAPSHOT-EXTRACTION-IDENTITY` | [4330456310](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4330456310) | PDF parser reads a bounded in-memory snapshot; media converter reads a staged bounded snapshot. Hash the same bytes rather than re-reading the mutable original path afterward | `test_pdf_hash_and_extraction_use_the_same_snapshot`, `test_media_hash_and_converter_use_the_same_snapshot` |
| `PREALLOCATION-INPUT-BOUNDS` | [4330456321](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4330456321) | Shared descriptor-based regular-file/size validation before allocation, followed by limit-plus-one reads to reject growth. Covers all CLI sources, optional review, signing key, field files, package artifacts and caption files | `test_all_file_clis_reject_oversize_before_allocation`, `test_file_growth_after_size_check_remains_bounded` |
| `TEMPORAL-ORACLE-CHRONOLOGY` | [4330456329](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4330456329) | Oracle independently parses cutoff/capture/publication as UTC and rejects publication after capture and invalid verification flag types | `test_temporal_oracle_rejects_invalid_publication_and_non_utc_capture` |
| `FORMAL-RESULT-JSON-TYPES` | [4330456335](https://github.com/n0tf0und0ut/Project-FAR/pull/578#discussion_r4330456335) | Compare canonical JSON types for formal results, countermodels, interpretation metadata and structured summaries; boolean/integer/float equality cannot launder a type change | `test_formal_results_preserve_json_number_and_boolean_types` |

**Observed before/after:** On the predecessor's exact component bytes, the first eight tests in `test_review_578_cycle5.py` produced **22 failing assertions**. The oversized cases use a sparse 512 MiB file and a 128 MiB address-space limit in the child, so the regression does not allocate the adversarial file into the test runner. A separate predecessor diagnostic probe exited 1 with a `RecursionError` traceback. The corrected eight tests pass; a ninth positive control additionally rejects file growth between descriptor size inspection and reading. All 34 earlier-plus-new review tests pass locally, with zero failures. The complete local 172-test suite still needs hosted FastAPI dependencies for six web tests; it is not claimed as a full local pass.

The work-budget tests instrument the expensive inference primitive to test rejection and duplicate-call accounting; they do not claim a measured runtime benchmark or independently verified real-world semantics. The snapshot tests use fake extraction/conversion adapters and mutate the original file during the operation. No live provider or source-authenticity claim follows. All final-head hosted, independent-review and protected-App obligations remain in force on the corrected successor.

### Fifth-review integration follow-up

Additional counterexamples were checked against `92b8cae2fe24af038651ad0692bef53e749d54dd`.
Two replay paths still used Python container equality: legacy replay accepted
floating-point counts substituted for integers; package replay accepted `0`
substituted for a Boolean assurance flag after only the unsigned artifact hash
was refreshed. Canonical JSON comparison now covers those paths and signed
review replay. Regressions: `test_legacy_replay_does_not_coerce_float_counts_to_json_integers`
and `test_package_replay_does_not_coerce_zero_to_false`.

The same 48-record logic family caused 96 repeated calls in the independent
oracle. `test_independent_repeated_queries_are_computed_once` requires two
actual independent computations. A separate 400-reading, sub-two-megabyte
counterexample measures serialized bytes rather than runtime: cache keys may
not repeatedly expand the entire premise family. The primary cache now retains
per-formula metadata, charges query-reference work to the existing 8,000,000-unit
budget and returns separate result objects.

Bounded I/O is also enforced across the delivery transaction: snapshot each
artifact once, admit only the nine defined names, enforce 6 MB per artifact and
36 MB total, and reject excessive writer output atomically. The manifest-family
and oversized-writer regressions detect those missing composition bounds.
These are extensions of the reported JSON-type and aggregate-resource invariants,
not new product features or assurance promotion. Final-head validation and
independent review remain required after the integrated corrections.


## Sixth review: delivery provenance, transport bounds and caption grammar

Reviewed predecessor `92b8cae2fe24af038651ad0692bef53e749d54dd`; the three
findings also reproduce on integrated head `ae18d3dfd01d49349b5c88841801f1bdea1b60f5`.

| Invariant | Source discussion | Root correction | Permanent regression |
|---|---|---|---|
| `COMMITTED-PROVIDER-DISCLOSURE` | 4330718724 | Derive external-provider disclosure from the committed proposal method as well as the live proposal mode; supplied provider proposals retain their provenance and replay | `test_supplied_provider_method_produces_replayable_network_disclosure` |
| `PREALLOCATION-TRANSPORT-BOUND` | 4330718737 | Count JSON request chunks before retaining them, independently of missing or understated Content-Length; stop at overflow | `test_chunked_json_stops_consuming_at_the_byte_limit_and_recovers` |
| `CAPTION-TIME-GRAMMAR` | 4330718751 | Accept two-component minute/second captions alongside the bounded three-component hour form; constrain minute and second fields to 00–59 | `test_caption_two_component_and_hour_timestamps_preserve_anchors_and_replay` |

The three tests produced six assertion failures and one parser error on the
integrated predecessor, including all three missing/understated transport-length
cases. They pass after correction. Positive controls include a subsequent valid
chunked JSON request, an offline supplied proposal, SRT and hour-form VTT, exact
cue anchors and full package replay. Invalid minute/second values are rejected.
The complete local component suite passes 181 tests. No live provider or source
authenticity is claimed. Final-head hosted checks, substantive independent review
and protected merge authorization remain required.


### Sixth-review adjacent upload boundary

The same `PREALLOCATION-TRANSPORT-BOUND` defect reproduced on `e85900fc`
for multipart uploads with an understated Content-Length. The parser consumed
more than the 16 MB transport cap before checking the extracted file. The shared
bounded transport reader now captures at most the permitted body before the
multipart parser can spool it. A permanent regression detects consumption past
the first overflowing chunk and requires HTTP 413 plus a subsequent successful
upload, proving worker release. This fourth sixth-review test fails on the
predecessor; all four and the complete 182-test component suite pass after
correction. This is the same reported ingress-bound invariant, not an added
feature. Hosted and independent exact-head validation must use this successor.


## Seventh review: unambiguous replay and composed resource bounds

Reviewed integration `ae18d3dfd01d49349b5c88841801f1bdea1b60f5`; fixes below
preserve the sixth-review correction `e85900fcfeb0a7354b3cd0fe693c6d0d7dec1c83`.

| Invariant | Source discussion | Root correction | Permanent regression |
|---|---|---|---|
| `WRITER-VERIFIER-SIZE-CONSISTENCY` | 4330776142 | Serialize and cap the complete manifest before stage publication; rejection removes staging output | `test_writer_rejects_oversized_manifest_without_publishing` |
| `UNAMBIGUOUS-PACKAGE-JSON` | 4330776148 | Reject duplicate object keys at every nesting level in all package JSON, including the manifest | `test_rehashed_duplicate_keys_are_rejected_in_every_json_artifact` |
| `LOSSLESS-ACCEPTED-TIME-PRECISION` | 4330776154 | Primary and independent validators each reject precision beyond six fractional digits before datetime conversion; unsupported precision cannot collapse chronology | `test_timestamp_precision_is_never_silently_truncated` |
| `BOUNDED-DIRECTORY-ENUMERATION` | 4330776160 | Stream directory entries and stop at the first unexpected name; retained names are bounded by the schema allowlist | `test_untracked_entries_stop_enumeration_at_first_mismatch` |

All four regressions are red on `e85900fc`, with nine failing assertions and no
fixture errors; they pass after correction. Duplicate-key probes preserve the
original last value and refresh the unsigned file hash, so the prior parser
accepted all six ambiguous JSON artifacts. Timestamp probes independently
exercise both validators with rehashed input/report identity.


Two additional full-ASGI regressions exercise the sixth-review actual-byte
limits through the complete middleware stack, including understated multipart
Content-Length. They complement the direct route tests. Per-request quotas do
not establish global concurrency admission control or production readiness.

The complete local component suite executes **188 tests, all passing**, with
installed FastAPI/Starlette/httpx dependencies. Hosted Python-version checks,
final independent review and protected merge authorization remain separate
requirements.

## Eighth-cycle review: exact-head follow-up corrections

- Manifest assurance: verification rejects unknown manifest keys and altered self-digest scope, including contradictory positive truth/semantic claims in unsigned extensions.
- Standalone replay: input/report parsing uses the package's duplicate-rejecting parser, preventing first-key/last-key ambiguity.
- Field adapter: predictions consume the already-validated in-memory manifest and audit instead of reopening mutable package files.
- Expanded discovery: oversized lead text is recorded as a failed candidate and the remaining investigation continues within the primary source cap.
- Synthetic diagnostics: empty and misspelled expectations cannot count as passing checks.
- Native required-check contract: fail-closed enforcement at job and step levels, exact PR activity types, and a single protected-main checkout without repository override. Mutation tests exercise each escape.
- The three independent workflow-contract findings on #589 are also repaired in this integration tree. Their original branch remains a historical ancestor.
- This work requires fresh hosted validation and independent review on its new commit; no green predecessor or earlier review is transferred.

## Ninth review: generated bounds and complete numeric source tokens

Independent review `5633278067` covered exact head
`d1fb637cfc5c4c60e036f6fdf2a01b80958085de` on 2026-10-23. Three findings
reproduced; none is dismissed by predecessor green checks.

| Invariant | Source discussion | Root correction | Permanent regression |
|---|---|---|---|
| `GENERATED-READING-COMPILER-CONSISTENCY` | 4363320217 | Cap default heuristic arguments at `MAX_READINGS`, preserve all retained claims, disclose the exact omitted discourse-cue count in committed proposal/report uncertainty | 13- and 23-cue source-to-package replays, plus the exact 12-cue boundary |
| `SOURCE-DECIMAL-FAILURE-CONTRACT` | 4363320234 | Both JSON parsers classify Decimal conversion failures as structured source unavailability with the same stable reason; neither aborts the whole investigation | Positive/negative extreme exponents, public independent cross-check and full CLI/package replay |
| `COMPLETE-NUMERIC-SOURCE-ANCHOR` | 4363320242 | Check the full numeric token against the original claim source, including context outside a clipped quotation; a separately coded scanner checks the independent path | Reject sign/digit/decimal/exponent/grouping fragments and clipped-source prefixes; retain complete signed decimals and sentence punctuation |

`tests/test_review_578_cycle9.py` was copied without implementation changes into
an isolated worktree at the reviewed head: **8 tests, 20 assertion failures and
2 Decimal parser errors**. On the corrected tree all **201 component tests pass**,
including the eight new tests and the installed SymPy solver control. Engine,
service and independent report identity advance together to **0.4.2** so earlier
packages cannot be silently certified under changed numeric semantics.

The field-validation document's readiness wording is reconciled with the
Research-only integration contract: external outcomes remain mandatory for
validated factual/utility/production claims, while Research integration
separately requires substantive review, hosted assurance and protected gates.
No empirical result, Accepted artifact, frozen benchmark or EFR contract changes.

Fresh hosted validation, independent substantive review of the complete
successor head and all protected source-bound gates remain required.

## Tenth review: close adjacent token, generator, lane and transport gaps

Reviewed head: `cee521a3fd0fbc184988be9ff908cfc0303fc63e` (2026-10-23).
All four findings below reproduced. The first two extend prior invariant
repairs; they are not dismissed as duplicates merely because the earlier
root-cause tests passed.

| Invariant | Source discussion | Correction | Regression evidence |
|---|---|---|---|
| `COMPLETE-NUMERIC-SOURCE-ANCHOR` reopened | 4363507656 | Treat underscore groups, fractions and ratios as indivisible unsupported tokens, including spaced/Unicode fraction separators; reject numeric substrings of identifiers in both implementations | Primary and independently forged-report controls for numerator/denominator, group prefix/suffix and identifiers |
| Generated-candidate/compiler consistency, extending the reading-cap repair | 4363507663 | Use the same 1,000-character bound in generated and supplied quotation/proposition validation; omit whole overlong primary/evidence sentences with source-specific disclosure, retain exact original offsets; explicitly reject a primary source with no bounded candidates | Mixed long/short sources replay; exactly 1,000 characters remain accepted after an omitted sentence; all-overlong source reports a bounded error |
| `STRUCTURED-LANE-MEMBERSHIP` | 4363507671 | Reject all structured annotations on non-structured input evidence; aggregate only independently recomputed input-lane members, deriving admissibility from input source/overlap records | Rehashed fabricated numerical results, temporal markers and discrepancy annotations are rejected |
| `DISCOVERY-HTTP-FAILURE-CONTRACT` | 4363507676 | Translate HTTP protocol exceptions into redacted `DiscoveryError` while preserving connection cleanup and the CLI error contract | Real HTTP parsers process truncated chunked bodies and invalid status lines; CLI returns 2 without traceback, key disclosure or published package |

The complete six-test regression file was copied onto the unchanged reviewed
head in an isolated worktree: **21 assertion failures and three errors**. On the
corrected tree all **207 component tests pass**, including the installed SymPy
control. Engine, service and independent report identity advance together to
**0.4.3**; no prior package is silently re-certified.

These are Research implementation and internal-oracle corrections. They add no
external source authentication, semantic-verification result, independent human
study, Accepted scientific claim or production-readiness claim. Fresh final-head
review, hosted assurance and protected merge gates remain required.

## Review-evidence policy v1.1 repair (deployment pending)

Predecessor: `6c874db2e0dc2ce8a4281bf9c507001a3b0787fd`.
Root cause `CODEX-COMPLETION-EVIDENCE-COMPATIBILITY`: the protected-main
collector requires a completed summary's unresolved flag to be boolean, while
the observed authenticated service summary leaves it null despite separate
no-major-issues completion receipts. Native jobs 120644160046, 120644960518
and 120653906205 fail closed; summary 6293998197 and receipts 6374221633 /
6374521211 preserve the original evidence. Metadata reconciliation request
6374505392 did not change the null flags. This is not proof of a vendor defect.

After the blocker was reported, the user explicitly instructed implementation
of the review-evidence policy repair. Policy v1.1 accepts a narrowly specified
authenticated receipt plus contemporaneous completed full-head summary as
metadata evidence, preserving unknown flags. The receipt cannot clear known
unresolved findings, threads, changes requested, or a running/failed review.
Authentication now checks bot type and numeric App ID as well as login/slug;
GitHub resolves short commit prefixes, duplicate JSON keys reject, and both
source records survive in the v2 artifact. The exact compatibility limits and
weaker finding-state assertion are documented in the policy.

The new CLI regression
`ReceiptContractTests.test_actual_cli_resolves_prefix_via_read_only_commit_endpoint`
fails on the unchanged predecessor with exit 2 (`unrecognized or incomplete
authenticated Codex state`) rather than expected exit 0. All 56 review-policy
tests pass after repair. A read-only reconstruction of 68 reviews, 110 inline
comments, 55 resolved threads and 32 issue comments passes the v1.1 metadata
criterion, preserving `unresolved: null`, summary ID 6293998197 and receipt ID
6374521211. This is local compatibility evidence, not a protected green check.

Deployment requires the separately documented immutable collector-source
exception for only PR #578 at the exact old main, digest verification, fresh
independent review of the final head, complete hosted assurance and all original
protected context/App bindings. No protected-main update, fabricated finding
flag, check publication or administrative bypass is authorized by this record.
Engine/service/oracle remain 0.4.6. Scientific claims, EFR and frozen benchmarks
are unchanged.

The native deployment loads only collector commit
`21db5b82282bf5759b96016eff84daf5783b6236`, SHA-256
`02795d65f14029ccf8b86c83397d6b3ff979c17b6c6f8e84f85da02fc0be585c`,
and only for the canonical repository's PR #578 at old main `e4d936ca`.
Six actual-shell regression tests exercise successful verified loading,
wrong-PR/repository refusal, corrupt bytes and failed downloads, collector
failure, pre/post head drift, and return to protected-main code after main moves.
Four additional workflow mutations remove/alter the pin, digest, PR or repository
binding and are rejected by the contract. Shell command adapters use the allowed
Python interpreter for base64/hash operations so tests do not add an undeclared
executable to the frozen runtime policy.

Current local validation: **62** review-policy tests; **2,446** repository tests
with three skips; **225** component tests; **137** full-health checks with zero
warnings/failures; workflow parsing and diff checks. The initial component command
failed because FastAPI was absent from the default interpreter; installing the
existing declared development dependencies in an isolated target resolved that
environment failure without repository dependency changes. These local results
do not substitute for fresh hosted certificates or final-head independent review.

### Review of policy repair at 9970958a

Independent discussion **4364741900**, thread `PRRT_kwDOTH_vCM6vysd0`,
identified a real `KNOWN-UNRESOLVED-STATE-PERSISTENCE` defect: the receipt path
retained prior explicit unresolved flags only from completed states, allowing a
completed/null receipt to mask flags from running or failed observations.
Two new tests on unchanged `9970958a` produce **three assertion failures**:
both reported bypasses and the locally added converse where an intervening
explicit completed-clean result should clear an older completed unresolved flag.

The correction folds all authenticated exact-head observations chronologically:
every explicit true flag sets the outstanding state regardless of review status;
only an explicit completed false flag clears it. A later null flag never performs
that clearance. Both regressions and the explicit-clean converse pass after the
correction. This is an implementation repair of v1.1, not a further weakening of
the policy. The deployment pin/digest must advance to the corrected collector,
and the final successor needs new independent review and complete assurance.


## Eleventh review: numeric groups, malformed input and closed report shapes

Reviewed head: `5772c629c7a85e7869a37c9bb3550410f0375bac` (2026-10-23).
All four substantive findings reproduced; prior passing suites did not establish
these invariants.

| Invariant | Source discussion | Root correction | Permanent regression |
|---|---|---|---|
| `COMPLETE-NUMERIC-SOURCE-ANCHOR` reopened | 4363653639 | Conservatively group adjacent numeric terms separated only by punctuation, symbols, underscores or whitespace; check Unicode math/dash boundaries in separately implemented scanners | Mixed fraction components, ASCII/narrow/nonbreaking-space grouping, arithmetic fragments, repeated and Unicode signs; forged rehashed reports exercise the separate checker |
| `MALFORMED-ENUM-ERROR-CONTRACT` | 4363653644 | Type-check enum and identifier values before set/dictionary membership in core and proposal validation; preserve the audit CLI bounded-error contract | List/dict enum values, reading IDs, premises, conclusions and evidence references; subprocess exit 2 without traceback or report |
| `PRODUCER-REPLAY-JSON-CONSISTENCY` | 4363653650 | Use the same duplicate-rejecting artifact parser for audit production and replay | Duplicate top-level and nested fields rejected before output; ordinary producer/replay round trip remains valid |
| `CLOSED-REPORT-ASSURANCE-CONTRACT` | 4363653652 | Enforce exact report, claim and evidence result field sets, derived from the input lane and independently recomputed outcome | Rehashed positive truth, semantic-mapping and authenticity extensions at all three levels are rejected |

The unchanged six-test regression file produces **28 assertion failures and 11
errors** on the reviewed head. The corrected complete component suite passes
**213 tests**, including the installed SymPy control. Engine, service and
independent report identity advance together to **0.4.4**. The conservative numeric
group grammar may reject adjacent numeric lists; it does not parse mixed-number
semantics or establish natural-language fidelity.

These are Research implementation and internal-checker repairs. They do not
supply external source authentication, human semantic adjudication, scientific
replication, measured customer utility or production assurance. Fresh final-head
substantive review, hosted assurance and protected merge gates remain required.


## Twelfth review: resource-bounded report numbers, cue coverage and arithmetic context

Reviewed head: `8ec9a4683e393c22f4dd7ac42dc1b839317ea83d` (2026-10-23).
Three new findings reproduced despite the predecessor's passing component suite.

| Invariant | Source discussion | Root correction | Permanent regression |
|---|---|---|---|
| `BOUNDED-REPORTED-NUMERIC-CONVERSION` | 4363821905 | Require producer-format fixed decimal strings with at most 85 integer and 40 fractional places (127 characters including sign/dot) before Decimal/Fraction conversion; this accommodates 10,000-row sums of the admitted 40-digit, exponent ±40 inputs | Rehashed reports with billion-scale positive/negative exponents, nonfinite and oversized values reject in bounded subprocesses; large aggregates and small fractional results still cross-check |
| `CAPTION-METADATA-KEYWORD-BOUNDARY` | 4363821913 | Match NOTE only at end or ASCII space/tab boundary; STYLE/REGION require complete header lines. Preserve non-ASCII identifier whitespace rather than stripping it into a reserved keyword | Eight keyword-prefix/Unicode-whitespace cue identifiers retain both cues, extracted text, offsets and package replay; genuine metadata remains excluded |
| `ARITHMETIC-CONTEXT-INDEPENDENCE` | 4363821922 | Accumulate filtered counts as integers, constructing Decimal only after counting. Also give sums a complete fixed arithmetic context rather than inheriting caller exponent limits, traps or clamping | 101- and 10,000-row counts under precision 2 and rounding traps, low-context generation/default-context replay, and sums under hostile caller exponent/trap settings |

The unchanged seven-test regression file was executed on the exact reviewed
predecessor in an isolated worktree: **10 assertion failures and four errors**.
All **220 corrected component tests pass**. Engine, service and separate-checker
identity advance together to **0.4.5**; earlier packages retain their originating
engine requirement. Caption grammar was checked against the W3C WebVTT editor's
draft at https://w3c.github.io/webvtt/ (metadata and cue syntax); this is a bounded
parser correction, not a claim of complete WebVTT conformance.

These are internal Research implementation/oracle repairs. No external semantic
fidelity, source authenticity, factual accuracy, commercial advantage, EFR result
or production-readiness claim changes. Fresh substantive review, complete hosted
assurance and all protected merge gates remain required on the successor head.


## Thirteenth review and caption-context self-review

Reviewed head: `574a00dbf0fe3347bea2b6afdd51ef8aed740242` (2026-10-23).
Two independent findings and one locally discovered follow-up remain genuine
new counterexamples to earlier invariant repairs, not stale duplicates.

| Invariant | Source discussion | Root correction | Permanent regression |
|---|---|---|---|
| `ARITHMETIC-CONTEXT-INDEPENDENCE` reopened at parsing | 4363924546 | Supply complete explicit contexts to Decimal JSON conversion in both separately implemented parsers, including a trapping InvalidOperation policy; parsing cannot silently replace out-of-range source numbers with NaN when caller traps are disabled | Both extreme exponent directions under relaxed traps produce the same unavailability report as default context; relaxed-context generation replays under default context |
| `INDEPENDENT-SOURCE-ANCHOR-BOUNDS` | 4363924557 | Validate claim and evidence offset types, nonempty ordered bounds and quotation equality before any overlap routing; negative/clamped Python slices and bool-as-int are not valid anchors | Fourteen malformed claim/evidence span variants and a rehashed negative-coordinate self-corroboration bypass reject; equivalent valid positive overlap remains SELF_REFERENCE_NOT_CORROBORATION |
| `CAPTION-METADATA-KEYWORD-BOUNDARY` reopened at file context | self-review PR comment 6373977465 | Restrict WEBVTT file-header handling to the initial block; later cue identifiers equal to the header keyword retain their contents | Two-cue source extraction and complete package replay retain the second WEBVTT-identified cue |

On the unchanged reviewed predecessor in an isolated worktree,
`test_review_578_cycle13.py` produces **17 assertion failures and one error**
across four tests; `test_review_578_header_context.py` adds **one failing test**.
All five pass after correction. Engine/service/oracle identity advances together
to **0.4.6**; current component suite contains **225 tests**.

The source anchor oracle remains separately coded and does not import primary
validation to certify itself. These fixes do not independently establish that
text means the supplied formulas, sources are authentic, or any real-world
claim is true. They change no frozen benchmark, EFR contract, Accepted theory,
external-independence status or product-readiness claim. Final-head independent
review, hosted assurance and protected merge gates remain required.
