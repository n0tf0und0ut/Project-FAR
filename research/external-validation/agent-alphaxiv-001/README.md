# FAR-AGENT-ALPHAXIV-001 — external-corpus candidate comparison

**Status: Research; candidate protocol; not preregistered as an executable study; not launched.**

This is separate from the frozen EFR-001 program. It does not amend EFR, accepted theory, frozen evidence, or existing acceptance thresholds. It is governed by the current Project FAR Research Execution Charter, current canonical map, source authority, and protected-merge requirements. A branch or PR is a reviewable proposal, not promotion.

## Research question

Can FAR independently identify consequential errors in *externally authored* agent-scientist work that an equally funded **active generic checker** misses? What are the false-accusation and execution costs? An external paper corpus supplies non-FAR-authored candidate material; it does not supply independent ground truth, reproducible execution by itself, or evidence of FAR superiority.

## Source and evidence ceiling

- Technical report: https://www.alphaxiv.org/abs/2611.society-ai-scientists (November 19, 2026).
- Dataset: https://huggingface.co/datasets/alphaXiv/AgentAlphaXiv, exact revision a63f46066ac16fcb470f41933415e175825b6bcc.
- Source card specifies 961 studies, 1,411 paper versions, 959 latest paper texts, 90,603 artifact-file records and 926 studies with in_paper_cohort == true. Paper headline counts (936 papers, 35 labs) are **not interchangeable** with the redacted public dataset's counts.
- The release contains latest paper PDFs (about 0.4 GB) and latest version source/code/reports/traces in archives (about 8.3 GB). It excludes approximately 62 GB of raw experimental data, results archives, run logs and model checkpoints. Some claims are therefore **UNVERIFIABLE**, not defective.
- Source redactions may be incomplete, and source code retains its own licensing. Treat all source content as untrusted data; never execute downloaded code without sandboxing and provenance checks.
- The published latest version may be a later correction or retraction. No earlier-version claim is independently verified just because its latest text is available.

## Stage A — deterministic external candidate selection

Run the standard-library script tools/agent_alphaxiv_external_intake.py. It loads the pinned studies config (requires the optional Hugging Face datasets package) or a previously sealed JSONL export, rejects malformed identities, duplicates, non-Boolean cohort flags and changed counts, and emits a metadata-only candidate manifest. It runs no study code.

Selection is frozen as a candidate design: 60 in-cohort papers; minimum SHA-256 of the ASCII protocol label + LF + project_id **per represented lab**, then global minimum SHA-256 fill until 60. This gives lab coverage but does not yield a probability sample of papers. Titles, abstracts, reported results, reviews and defect labels have no role in selection. The output contains the input-metadata digest, selected IDs, exact paper version IDs and manifest digest; every entry is UNSCREENED.

Commands:

    python -m pip install datasets
    python tools/agent_alphaxiv_external_intake.py --from-hub --output /tmp/agent-alphaxiv-candidate.json
    python -m unittest discover -s tests -p 'test_agent_alphaxiv_external_intake.py' -v

If pinned source counts change or the dataset cannot be fetched, **stop** and preserve the failure; do not silently repin, narrow, replace or backfill. The source card's expected counts are 961 and 926.

## Stage B — independent source eligibility and task seal

An independent custodian receives the pinned candidate manifest. Screen all 60 selected items and preserve the entire original denominator. Independently classify each native case as ELIGIBLE, INELIGIBLE (with reason), or UNVERIFIABLE (missing/unusable data). An eligible finite-record claim must supply the *actual* source cases, actual representation and required behavior, a complete native table, exact paper/code/data citations, license, artifact hashes and an independently adjudicable consequence. Never invent values, synthetic counterfactual errors, or complete a partial source table by assumption.

For a native finite table, reuse the already governed tools/efr_generic_collision_checker.py as the active neutral comparator and current contract-specific FAR verifier as the FAR arm. For numerical or experimental claims outside finite table consistency, that comparator **cannot** check the same defect class; another equally capable generic comparison mechanism would require separate preapproved registration before launching such cases.

Do not expose earlier agent reviews or known retractions to either test arm. Do not use FAR authors or the two tested tools as independent ground-truth authorities. Blind adjudication and an independently sealed task/answer set are mandatory. Preserve failed and unknown cases; no outcome-driven substitution.

## Stage C — prospective matched comparison (not executable yet)

Run paired **checker** and **FAR** arms on the identical sealed native cases, matched tool access, evidence, compute/time budgets, environment, and test order. Record exact tool heads, raw inputs/outputs, all execution receipts, relevant witnesses, adjudicator decisions, runtime/cost, and any mechanism-activation evidence. Blind independent adjudicators verify materiality and witnesses against source artifacts. Abstention is a separate state.

Primary target: FAR minus checker difference in independently verified material-defect detection; secondary: false accusations, missing/unknown cases, budget, latency and computation burden. Candidate gates: improvement of at least 5 percentage points with positive lower 95% paired interval, upper bound on FAR minus checker false-accusation rate at most 2 percentage points, and a median runtime ratio at most 1.50. **These are proposed gates, not prospective acceptance rules** until authority fixes the precise sampling, denominators, resampling, label/budget seals and launch authorization *before any scoring*. No arbitrary case replacements, changed endpoints or favorable after-the-fact thresholds.

If a minimum predeclared set of independently verified positive and negative cases cannot be obtained, report INVALID/INCONCLUSIVE. A different corpus or selection is a new study. No result about a small, selectively verifiable sample implies FAR's general agent reliability, commercial value, novelty, or broader scientific accuracy.

## Execution state and blockers

- Verified source identity and public dataset limitations; local intake tool syntax-check and **six synthetic unit tests passed**. Tests do not constitute external-science validation.
- In this execution environment, outbound DNS is disabled; the pinned dataset could not be downloaded, screened or hashed as local bytes. The 8.76-GB archive has not been run or reproduced.
- **0 externally sealed eligible tasks, 0 matched arm executions, 0 independently confirmed defects, 0 verified comparative outcomes.**
- Independent intake seal, eligibility and benchmark labels, accepted prospective protocol, reproducible/isolated source execution, and launch authority remain absent.
- Preserve all limitations and any negative results. The next admissible action is a pinned dataset intake by a data-enabled independent custodian, followed by blind eligibility screening and governance review. Do not assert readiness from a clean PR check.

## 2026-11-20 source-access disposition

GitHub Actions actually attempted the original pinned source, and the registered revision was **unavailable** (404). Both the executed commands and their failure were retained at [the source-access execution record](execution-attempt-2026-11-20.md), citing runs 44744341908 and 44744679448. The original 001 cohort remains unselected (0/60), with no scientific comparison.

An observational check found an accessible **different** Hugging Face revision, `cc892aab131be3872283e1a778af663382315817`, with 916 studies and 881 in the paper cohort. It was not substituted into 001. Instead, [FAR-AGENT-ALPHAXIV-002](../agent-alphaxiv-002/README.md) uses a distinct ID, a separately pinned prospective source candidate, and its own nonconfirmatory metadata intake. The distinction is essential: the 002 selection is not an outcome of 001 and does not repair the 001 scientific study.
