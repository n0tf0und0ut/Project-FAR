# PR #578 review convergence and defect ledger

**Scope:** Research-only investigation lab v0.4.1. This ledger records reviewed invariants, reproducible counterexamples and correction evidence. It grants no independent scientific, factual-verdict, source-authenticity, or production-security status.

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

**Important limit:** This Codex finding cycle was performed on `77ddd...`, superseded by later corrections, and is not an independent clean final-head signoff. The next review must reference the newly stabilized SHA, challenge these regressions and their integration, and receive the protected-repin App's own final-head decision.

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
