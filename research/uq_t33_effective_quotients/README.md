# UQ-T33 — Effective Observational Quotients

**Status: Research only.** This is evidence and proof analysis for the registered open question UQ-T33. It does not promote or revise accepted FAR theory or close the canonical question.

## Findings

- [Discovery report](discovery.md): sharp finite separating basis of at most k−1 tests for k observable classes; nondecidability of exact sufficiency in a uniformly computable infinite-test class; decidable finite explicit-table fragment; limitations and prior art.
- [Continuation report](continuation.md): a positive computability theorem for known finite deterministic Moore machines with an infinite action-word test family. Exact observational equivalence is obtained through partition refinement and the sharp distinguishing-word horizon max(n−2,0). With a certified state-count bound and resettable oracle, black-box equivalence is decidable; without such a bound, no uniform total finite-query decider exists even for finite-state targets.
- [Original executable experiment](experiment.py): six finite regressions, including 65,812 exhaustive binary test-family configurations, seeded multivalued tables, sharpness witnesses and finite-prefix counterexamples.
- [Additional finite-state experiment](finite_state.py): seven regressions over exhaustive small deterministic transition systems, a certified black-box equivalence oracle, deliberate false-certification witnesses under an invalid state bound, and negative/edge cases.
- [Recorded original results](results.json): exact output from the original six-test local run, not the result of an independent replication.
- [Evidence and real-world correspondence boundary](evidence_boundary.md): R7 conditional finite behavioral envelope, externally checkable proof obligations, and a negative RFC 1661 source audit.
- [Finite-model evidence checker](evidence_gate.py) and [example model](example_evidence.json) / [checked report](example_report.json): the checker validates declared finite tables, *not* external system correspondence.
- [Evidence regression suite](../../tests/test_uq_t33_evidence_gate.py): positive mapping plus twelve adversarial/induction checks.
- [Real existing source correspondence](real_implementation_correspondence.md) and [source-bound checker](source_bound_status.py): R8 links the exact FAR decision-integrity adjudicator source blob and final status branch to a finite three-flag abstraction of its **status-only** output. It does not certify whole-program semantics or third-party I3 independence.
- [Source-bound integration tests](../../tests/test_uq_t33_source_bound_status.py): source pin, adversarial mutations, exhaustive finite add-rule refinement and real production function invocations when the full checkout is available.
- [Independent source-to-runtime replication packet](external_replication_packet.md): exact pinned subject source and failure criteria for two external teams; prepared, not executed.

## Reproduction

From the repository root with Python 3.10 or later, no third-party dependencies:

    python -m unittest tests.test_uq_t33_effective_quotients tests.test_uq_t33_evidence_gate tests.test_uq_t33_source_bound_status
    python research/uq_t33_effective_quotients/experiment.py

The first command includes **37 test cases** (25 original/evidence tests plus 12 source-bound cases). The ten source-bound tests runnable with a synthetic fixture passed in local scratch. Two mandatory real-production integration tests **fail closed** if no complete checkout exists; they were not executed successfully in that scratch environment. The real subject source Git blob and SHA-256 were separately verified from GitHub; that does not replace live runtime execution. The second reruns the original six and rewrites results.json. These checks test bounded code cases and do not establish the undecidability theorem through execution.

## Provenance and assurance limits

Base authority was protected main commit 8c6dc6cf840a0d82fb4dcde114c1af471b3f74fe, current AGENTS.md and Research Execution Charter. The original supplied standalone research package was independently re-executed locally in this task. Its code and results are committed byte-identically; its original narrative has been integrated into discovery.md with explicit source SHA-256, scope and negative findings.

The model certificate's source digest authenticates only the submitted table against its stated digest; it does not authenticate external source code or runtime semantics. The RFC 1661 review provides external documentary evidence of a control-state specification, but no implementation-bound certificate.

R8's source identity binds only a reviewed fragment of a real implementation. The additional analysis wrapper does not reflect an actual event API in the adjudicator, and the rest of the production program remains outside its claim.

No I3-independent proof review, adversarial external evaluation, prior-art novelty determination or governed Acceptance has occurred. A self-authored executable test is not external replication, and the results neither establish universality nor domain-specific suitability of any declared contract.
