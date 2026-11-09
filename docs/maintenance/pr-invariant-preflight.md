# PR invariant-first preflight

**Status:** proposed operational assurance control. This page supplements the [PR review-convergence policy](../governance/pr-review-convergence.md), not the Research Execution Charter or FAR's scientific acceptance process.

## Purpose and limit

PR #614 repeatedly passed extensive CI while independent reviews uncovered further defects in the same classes: absolute time budgets across HTTP framing/headers/source calls; bytes lost on a late read; model-controlled fields misclassified as trusted transport receipts; inconsistent failed-response bytes; unbound model prompts. Passing tests did not establish these omitted invariants. Do not interpret more tests, a valid manifest, an internally sealed trace, or a clean automated review as proof of correctness.

The preflight makes authors **declare end-to-end invariants before independent review**, tie each changed implementation path to an invariant, identify at least two different failure modes, and identify existing positive, negative, and integration test functions **at the exact candidate head**. The independent reviewer must inspect whether the tests actually exercise the claim, whether boundary-adjacent cases were omitted, and whether each root cause is closed with a reproducer. The checker does not run candidate code, assert tests passed, verify red/green history, or infer semantic correctness. Existing full CI and independent review remain mandatory and separate.

## Rollout and authority

**Two-stage protected rollout:** PR #631 first lands the tested checker, test suite, template and governance documentation on protected main **without modifying the required review workflow**. A second, separately reviewed activation PR adds its invocation to the existing **required** `pr-review-convergence-observation` job, checking out the checker from protected main. Activating before that first merge would fail because protected main does not yet contain the checker. It uses `pull_request` and `pull_request_review` events; the workflow remains read-only and checks that the PR head has not moved. Both stages must merge normally with independent review and all required protected checks. The cutover applies **only after activation merges**, not merely when the checker exists on a development branch. Until then, this is a proposed control, not an active merge gate.

After activation, for non-draft PRs **created at or after 2026-11-10 00:00 UTC** targeting `main`, a changed implementation file requires a machine-readable `FAR-INVARIANTS-V1` block. The cutover uses the immutable PR creation time, not the latest edit or push. Historical PRs (including #614) retain their existing governance obligations; they are not retroactively blocked solely by this metadata change. Drafts defer enforcement until ready for review, and documentation-only PRs need no block. A newly added or edited source cannot be excluded by an author's risk label; changed paths are collected from the GitHub API, checked against GitHub's `changed_files` total, and matched mechanically.

### Contract in PR description

Use the template at `.github/pull_request_template.md` or this exact shape; remove the sample if the PR is documentation-only. The JSON is inside a literal HTML comment, so it is not shown as a noisy table in the rendered PR description.

```text
<!-- FAR-INVARIANTS-V1
{
  "version": 1,
  "scope": "Read-only native HTTP transport and journal boundaries",
  "limitations": ["Internal test traces do not establish external source authenticity or model autonomy"],
  "invariants": [{
    "id": "HTTP-BOUNDARY-01",
    "statement": "Every accepted source read is complete and within its absolute execution budget",
    "boundary": "Untrusted HTTP peer to native retained transport receipt",
    "changed_paths": ["tools/your_reader.py"],
    "failure_modes": [
      {"case": "A header line trickled beyond the absolute budget is rejected", "test": "tests/test_reader.py::test_trickled_headers"},
      {"case": "A failed response retains all already-observed body bytes", "test": "tests/test_reader.py::test_late_body_prefix"}
    ],
    "positive_control": "tests/test_reader.py::test_complete_response",
    "integration_control": "tests/test_engine.py::test_source_recheck",
    "assurance_limit": "A local mocked transport test does not certify real network deadline scheduling"
  }]
}
FAR-INVARIANTS-END -->
```

Replace example paths and tests with *real* ones in the PR. Every changed implementation path must be covered at least once, and the named tests must exist on the exact head. Contract rows can cover several files when they genuinely share a violated invariant; naming one general invariant merely to group unrelated changes is not acceptable substantive review.

## Required review process

Before the first independent review of a stabilized head, reviewers should verify:

1. **Invariant coverage:** Decompose requirements into end-to-end contracts, trust boundaries, and at least two adversarial neighboring cases per changed invariant. Distinguish real shared causes from superficial duplicate symptoms.
2. **Oracle adequacy:** Reproduce the original defect *before* the repair where feasible, prove the regression detects it, then verify successful behavior afterward. Include genuine native integration paths where a mock cannot model scheduling, framing, persistence, or transport. Failing tests caused by broken fixtures do not count as counterexamples.
3. **Closure and residual risk:** Execute the targeted tests before broad health; check error and cancellation paths and data provenance; review final changed paths; preserve negative findings, failed runs, and frozen evidence.
4. **Independent exact-head verification:** Request a substantive external review only after stabilization. Any new reproducible defect reopens its root-cause class, and a materially modified head invalidates the old review.
5. **Merge authority:** Retain separately required review-convergence, merge-authority, protected-repin, and exact-head checks. The preflight output has `software_correctness_verified=false` even when structurally valid.

If a purely mechanical or otherwise genuinely untestable change lacks a suitable regression, record that as an unresolved verification limitation for human judgment. Do not fabricate a test symbol to satisfy the parser. Request a documented policy exception through a separately reviewed governance PR rather than bypassing protected main.

## Running and troubleshooting

The trusted workflow calls:

```sh
python3 tools/pr_invariant_preflight.py --repository "$GITHUB_REPOSITORY" --pr "$PR_NUMBER" --expected-head "$EVENT_HEAD" --output "$RUNNER_TEMP/pr-invariant-preflight.json"
```

The output records head and base SHA, changed implementation paths, test-symbol count, phase (`enforce`, `historical-pr`, `draft-deferred`, or `documentation-only`), and errors. For any failure, the required job must fail rather than skip. The author corrects the PR body or real tests; the normal eligible event reruns the required context. A bot or candidate branch cannot grant itself an exception, since the collector comes from protected main.

**Known limits:** Static checks cannot measure test quality, oracle independence, semantic adequacy, or actual test execution. The PR body is self-reported. Github branch protection is not changed by this document. A passing preflight is a structural prerequisite, never an authorization to merge.
