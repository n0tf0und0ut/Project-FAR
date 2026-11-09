# Pull Request

## Summary

Provide a concise description of the proposed changes.

---

## Motivation

Why are these changes necessary?

---

## Type of Change

Select all that apply.

- [ ] Documentation
- [ ] Theory
- [ ] FARA
- [ ] FAR
- [ ] FARO
- [ ] Validation
- [ ] Examples
- [ ] Research
- [ ] Repository Infrastructure

---

## Files Modified

List the primary files affected.

---

## Dependencies

Does this change introduce any new dependencies?

If yes, describe them.

---

## Architectural Impact

Does this change:

- introduce a new concept?
- modify an existing concept?
- change a definition?
- affect the dependency structure?

Explain.

---

## Research Contribution and Claim Boundary

Complete this section for research, theory, validation, mechanization used as evidence, or evidence-facing release work.

- Central claim tested: existence / bounded sufficiency / universality / necessity / minimality / nontriviality / none
- Evidential role: exploratory / internal robustness / confirmatory / independent replication / enabling engineering / maintenance / application
- Current uncertainty reduced:
- Result that could count against FAR:
- Frozen theory or semantics version:
- External observation contract:
- Negative controls:
- Full-cost accounting method:
- Independence level and conflicts:
- Strongest claim supported:
- Explicit nonclaims:

Confirm all that apply:

- [ ] The PR does not allow FAR to define the theory, source cases, competitors, mappings, verifier, and final adjudication for a confirmatory claim.
- [ ] Any theory change after exposure to a frozen case creates a new version and preserves the earlier result.
- [ ] Internal multi-implementation robustness is not described as external independence.
- [ ] Derived machinery, hidden state, ambiguity policies, and adjudication burden are counted where comparative economy is discussed.
- [ ] Tradeoffs are not reported as superiority.
- [ ] Failed, excluded, unresolved, and divergent outcomes remain visible.
- [ ] Scope was fixed before the challenged result or is identified as post hoc.
- [ ] The work is authorized by `theory/evaluation/research-gates.json`, or the reason for an exception is documented.

---

## Related Research

Reference any relevant documents.

- `docs/governance/central-research-program.md`
- `docs/governance/anti-self-validation-standard.md`
- `docs/governance/research-priority-reset.md`
- `docs/methodology/confirmatory-research-package.md`
- `research/open-problems/open-questions.md`
- `docs/DECISION_LOG.md`
- `research/notes/backburner.md`
- `research/notes/failed-approaches.md`

---

## Checklist

- [ ] Definitions remain consistent.
- [ ] No circular dependencies introduced.
- [ ] Documentation updated.
- [ ] Examples updated (if necessary).
- [ ] Validation updated (if necessary).

---

## Validation

- [ ] `python tools/repo_health_check.py --fast` passes
- [ ] `python tools/check_research_gates.py` passes
- [ ] Internal links pass
- [ ] Math displays render
- [ ] Release docs are consistent if release-facing files changed
- [ ] No broken image or math-display links were introduced
- [ ] No orphaned documentation was introduced unless intentional
- [ ] No theory meaning changed unless explicitly intended
- [ ] No primitives, axioms, theorem statements, proof objects, parser behavior, reasoning-engine behavior, or metadata schemas changed unless explicitly intended

## Scope

Describe whether this PR is:
- theory
- tooling
- docs
- evaluation
- release
- cleanup

---

## Review Convergence

- [ ] Exact PR head, base/main SHA, merge base, changed-file scope and primary review/CI evidence examined.
- [ ] Changed correctness/security invariants and trust boundaries identified.
- [ ] Every substantive review finding assigned a demonstrated root cause or left explicitly unresolved.
- [ ] Fixed findings have defect-detecting regression tests and relevant integration validation.
- [ ] Duplicate, stale, speculative and rejected findings have concrete evidence, not unsupported dismissals.
- [ ] Independent substantive review completed on the stabilized exact head.
- [ ] Reviews were not repeatedly requested on identical code without new evidence.
- [ ] Required protected gates pass on the actual final SHA; claim limitations preserved.

**Finding ledger (or immutable artifact link):**

| Root cause | Review/thread IDs and reviewed SHA | Invariant/reproducer | Disposition and evidence | Fix SHA and regression |
|---|---|---|---|---|
| none recorded | — | — | — | — |

**Disposition:** draft / review required / metadata converged / substantive review completed / external blocker / merge authorized.

See docs/governance/pr-review-convergence.md. Metadata convergence does not prove code correctness.

## Invariant-first pre-review contract (new implementation PRs)

PRs created at or after **2026-11-10 00:00 UTC** that change implementation, test code/fixtures, or validation manifests must carry a machine-readable contract. Replace every example with real changed paths and existing exact-head test symbols. See `docs/maintenance/pr-invariant-preflight.md`. Once separately activated via protected main, the native required review gate enforces structural traceability, **not software correctness**.

<!-- FAR-INVARIANTS-V1
{
  "version": 1,
  "scope": "Describe the precise execution or trust boundary affected",
  "limitations": ["State which correctness or external properties remain unverified"],
  "invariants": [
    {
      "id": "EXAMPLE-BOUNDARY-01",
      "statement": "Define one end-to-end condition that must hold for every allowed execution",
      "boundary": "Name producer, consumer, and trust crossing explicitly",
      "changed_paths": ["tools/replace_with_real_changed_path.py"],
      "failure_modes": [
        {"case": "Describe an observed or plausible failing boundary scenario", "test": "tests/test_replace.py::test_rejects_invalid"},
        {"case": "Describe a distinct adjacent failure mode including cancellation", "test": "tests/test_replace.py::test_rejects_cancelled"}
      ],
      "positive_control": "tests/test_replace.py::test_accepts_valid",
      "integration_control": "tests/test_integration.py::test_end_to_end",
      "assurance_limit": "Document the specific assurances these tests do not establish"
    }
  ]
}
FAR-INVARIANTS-END -->

**Before independent review:** reproduce original failures, demonstrate defect-detecting regressions, test neighboring failure paths, run end-to-end integration, then stabilize the exact head. Request one substantive review after those steps and reconcile every new finding by root cause. A failed oracle/fixture does not count as evidence of production correctness.
