# FAR-AGENT-ALPHAXIV-002 — independently identified source-succession candidate

**Status: Research; metadata-only candidate, not an approved preregistration, not executed as a scientific study.**

This is a new prospective candidate because the source pinned by FAR-AGENT-ALPHAXIV-001 is unavailable. Do **not** reinterpret, replace or repair study 001's stopped execution as a successful experiment.

## Source custody and selection

Source: `alphaXiv/AgentAlphaXiv`, full accessible Hugging Face revision `cc892aab131be3872283e1a778af663382315817`. Current-branch source identity and counts were independently queried in GitHub Actions run 44744679448 at 2026-11-20 13:29 UTC (https://github.com/n0tf0und0ut/Project-FAR/actions/runs/44744679448): 916 total studies, 881 in the publication cohort. These are metadata facts only, not source validation or scientific findings. The older revision `a63f46066ac16fcb470f41933415e175825b6bcc` returned 404. Preserve those negative receipts.

Frozen **candidate** selection design: 60 `in_paper_cohort` study IDs, one minimum SHA-256 key per represented lab and global minimum-key fill, sorting by `FAR-AGENT-ALPHAXIV-002/candidate-v0.1 + LF + project_id` under exact revision. No post-selection replacement or outcome-dependent adjustment. Nonprobability lab coverage is explicit. Validate the exact source counts and schema; stop if either drifts. The manifest must state `RESEARCH_CANDIDATE_NOT_LAUNCHED` and `verified_empirical_claims: 0`.

Execute **metadata-only** intake after source revision verification:

    python tools/agent_alphaxiv_external_intake.py --candidate 002 --from-hub --output agent-alphaxiv-002-candidate.json

This uses only the `studies` configuration; no model inference, experiments, downloaded study execution, scientific scoring, claims of independence or outcome adjudication. The GitHub workflow has read-only repository rights and no secrets. Preserve the manifest's SHA-256 and all selected identities to enable independently reviewable screening.

## Forward scientific gates — NOT SATISFIED

Do not merge the two candidate cohorts, treat 001 as a pilot control, or select papers from prior revision substitutes. Before any substantive scientific audit, an authorized and **independent** custodian must: verify source version, hash/licensing for each selected source, inspect the complete candidate denominator, freeze eligibility and direct ground truth before exposing either arm, and establish an equal-capability generic-checker comparison (FAR's existing table-collision checker applies ONLY to complete finite tables). Record unverifiable/missing data without scoring them as defects; exclude material deleted after withdrawal, and preserve all denied access.

Any FAR-vs-checker comparison requires a separately accepted prospective protocol, frozen denominators, adjudication, randomization, pairing, budgets, tool/commit pinning, falsification rules and exact run receipts before outputs are viewed. No downstream EFR-001, theory or empirical utility promotion follows from this metadata intake. See the original candidate proposal at `../agent-alphaxiv-001/README.md` for the unanswered comparative question, with the original study's failures preserved at `../agent-alphaxiv-001/execution-attempt-2026-11-20.md`.

## Observed metadata-only execution (2026-11-20)

The exact successor source was retrieved successfully in GitHub Actions run [44745783234](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/44745783234), and its metadata-only job concluded **SUCCESS**. Pinned Python 3.12, `datasets==4.4.1`, deterministic intake and the synthetic sampling controls were used; GitHub checkout had read-only permissions and no persisted credentials.

- Source input metadata SHA-256: `c5d7993d6d4382111c6f154e4e87c91e4184956abb7b62a64f3c58522ef47d25`.
- Canonical complete candidate manifest SHA-256: `771d7b6cb86d93b804e165def7507a6ec517d59839d65e603c911459d0cab603`.
- Pretty-printed manifest JSON file SHA-256: `f201fd60042cf10c266755826831cb1ab77dd4cb0471c7a6730221d24ec21f47`.
- Selected sample: 60 distinct study IDs across all 31 represented laboratory labels; every entry is `UNSCREENED`.
- A source-derived JSON artifact is retained in GitHub Actions (14-day expiry); a [durable selected-study receipt](selection-receipt.json) is committed on this Research branch. `tests/test_agent_alphaxiv_receipt_integrity.py` mechanically reconstructs the manifest/fingerprint chain from that record.
- Exact prospective scientific comparison status: 0 independently sealed cases, 0 FAR runs, 0 checker runs, 0 independently adjudicated defects, 0 external-effectiveness claims.

This result completes the **candidate metadata intake**, not eligibility screening, independent sealing, experimental execution, peer review, acceptance, promotion, or merge. The original 001 source-availability failure remains independently recorded. No claim about the prevalence of scientific defects or FAR's advantage can be made from this stage.

## Executed full-archive verification (2026-11-20)

**Research status: source-corpus audit executed; scientific FAR-versus-checker comparison NOT executed.**

1. [Full-source coverage workflow 44786211359](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/44786211359) screened all **60** frozen candidate IDs for exact-version paper text, artifact inventory, and published file *listings*. It found 60 paper texts, 60 PDF paths and 60 latest-version archive paths; 4,252 latest-version inventory records, of which 1,082 were marked as included in released tar files and 3,170 as excluded. Read the complete [source coverage receipt](source-coverage-receipt.json), SHA-256 5fecd596dacc52ba696789ad57294b5b0544670f1b777ea0effd6c300917a21c. Listed paths by themselves were not yet byte verification.
2. [Archive byte workflow 44787961811](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/44787961811) then downloaded and inspected the exact pinned released archives for **60/60 selected studies**, totalling **338,677,760 bytes**. It enumerated every regular tar member without extracting or executing source code and recomputed its hash and size against the frozen artifact inventory. Of 1,082 included members, **966 SHA-256 checksums matched** and **116 did not**; 100 of the mismatches also differed in byte size. There were no missing declared-included members, unindexed archive members, unexpectedly included declared-excluded files, download errors, or budget skips. The [complete byte receipt](archive-byte-receipt-v0.1.json) has canonical SHA-256 dd0375ea74c91ca65cc19eb6bf03ea3dea24c6ff338b90fbcba0c73c5911ad86.
3. [Second byte-identical triage workflow 44789242398](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/44789242398) independently re-downloaded all 60 archives and verified that their whole-file SHA-256 digests were identical to the prior successful byte audit. It reproduced all 116 mismatched members, affecting 59/60 archives. Mismatches by publisher artifact kind: paper_source 61, code 40, report 5, agent_trace 4, paper 4, and environment 2. By format: 71 ZIP, 30 gzip, 5 JSON, 4 PDF, 3 Markdown, 2 Python, and 1 JSONL files. The [replayable triage receipt](mismatch-triage-receipt-v0.1.json) has canonical SHA-256 eb7d54b6767d37550d2392d4db559555c2696aaccb00e9e144e7611c6caabcf3.

The research scripts use standard-library tar traversal with explicit path, duplicate, symlink, member-size, download budget, archive SHA, source revision and receipt checks. Synthetic negative controls reject malicious archive paths, modified bytes, duplicate identities, changed source versions, tampered receipt data and exceeded budgets. All live source-contact workflows have been bound to their exact already-executed heads to prevent automatic redundant downloads; the current-head offline test workflow checks the preserved evidence.

## Interpretation and evidentiary ceiling

The 116 mismatches are mechanically verified **publisher artifact inventory-versus-released-file discrepancies**. The publisher describes extensive release-time redaction of papers, source code, logs and names, and automated redaction could alter released bytes; the observed concentration in compressed paper sources and code is compatible with that explanation. However, original pre-redaction bytes are unavailable and the dataset does not supply an authenticated before/after transformation log. **Cause of any mismatch remains UNDETERMINED**; none is independently adjudicated as a scientific error, fraud, malicious alteration or model failure.

The same publisher release excludes roughly 62 GB of raw data, result tarballs, run logs and checkpoints. The 3,170 missing-from-release latest-version inventory entries are declared exclusions, not accidental missing entries in the tar files. Existing code archives and paper text do not automatically fill the unavailable underlying experiment evidence. The study denominator is still 60, not a selectively filtered favorable subgroup.

**Scientific comparison: 0 independently sealed eligible native cases; 0 active generic-checker arm runs; 0 FAR arm runs; 0 independently adjudicated scientific defects; 0 confirmed FAR-specific advantage.** A generic table-collision checker can match FAR's exact finite-table loss classification when the complete table is supplied. Claims outside that finite contract need a different preregistered, equally capable neutral comparator. Independently validated source/native claims, blinding and approved prospective execution remain unsatisfied. Neither a clean CI run nor internal hash agreement grants EFR-001, theory, external effectiveness or product claims. The completed result is a bounded, externally sourced **release integrity and evidence-availability audit**.
