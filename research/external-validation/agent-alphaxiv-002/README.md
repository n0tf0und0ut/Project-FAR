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
