# UQ-T33 — Effective Observational Quotients

**Status: Research only.** This is evidence and proof analysis for the registered open question UQ-T33. It does not promote or revise accepted FAR theory or close the canonical question.

## Findings

- [Discovery report](discovery.md): sharp finite separating basis of at most k−1 tests for k observable classes; nondecidability of exact sufficiency in a uniformly computable infinite-test class; decidable finite explicit-table fragment; limitations and prior art.
- [Continuation report](continuation.md): a positive computability theorem for known finite deterministic Moore machines with an infinite action-word test family. Exact observational equivalence is obtained through partition refinement and the sharp distinguishing-word horizon max(n−2,0).
- [Original executable experiment](experiment.py): six finite regressions, including 65,812 exhaustive binary test-family configurations, seeded multivalued tables, sharpness witnesses and finite-prefix counterexamples.
- [Additional finite-state experiment](finite_state.py): five regressions over exhaustive small deterministic transition systems and negative/edge cases.
- [Recorded original results](results.json): exact output from the original six-test local run, not the result of an independent replication.

## Reproduction

From the repository root with Python 3.10 or later, no third-party dependencies:

    python -m unittest tests.test_uq_t33_effective_quotients
    python research/uq_t33_effective_quotients/experiment.py

The first command discovers both suites (11 tests in the locally verified run). The second reruns the original six and rewrites results.json. These checks test bounded code cases and do not establish the undecidability theorem through execution.

## Provenance and assurance limits

Base authority was protected main commit 8c6dc6cf840a0d82fb4dcde114c1af471b3f74fe, current AGENTS.md and Research Execution Charter. The original supplied standalone research package was independently re-executed locally in this task. Its code and results are committed byte-identically; its original narrative has been integrated into discovery.md with explicit source SHA-256, scope and negative findings.

No I3-independent proof review, adversarial external evaluation, prior-art novelty determination or governed Acceptance has occurred. A self-authored executable test is not external replication, and the results neither establish universality nor domain-specific suitability of any declared contract.
