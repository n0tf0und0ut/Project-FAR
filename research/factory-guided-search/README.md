# Factory guided search — bounded Research prototype

**Status: Research / unpromoted / no performance study executed.**

## Problem and justification

The factory study in issue #629 establishes a requirement to verify independently graded engineering delivery, while existing candidate search research targets neural architecture selection rather than engineering patch selection. PR #614 has been explicitly retired unmerged; this prototype does not copy or depend on its investigation runtime. The model-architecture search experiment and the registered factory self-evaluation protocol remain unchanged.

This code examines one narrower question: can a bounded candidate loop preserve failure evidence, bind each candidate to one exact repository base and source commit, require both task-test and FAR-contract PASS declarations, and select eligible candidates without exposing hidden evaluator artifacts to the proposer? Passing these checks is internal software behavior, not evidence of autonomous performance or source authenticity.

## Implementation

- Module: tools/factory_guided_search.py
- Focused tests: tests/test_factory_guided_search.py
- Reproduction: python -m unittest tests.test_factory_guided_search -v (Python 3.11+)
- Inputs: an operator-wired proposer callback and evaluator callback, frozen exact 40-character base SHA and 64-character oracle digest, one-to-32 bounded attempts and an integer reported-cost budget.
- Candidate declaration: candidate ID, exact base SHA, exact source SHA, artifact SHA-256.
- Evaluator receipt: same candidate and source SHA, exact frozen oracle digest, PASS/FAIL/UNKNOWN for independently specified tests and FAR-contract audit, evidence SHA-256, nonnegative integer cost and duration.
- Selection: both gates must be PASS. Among eligible candidates, lexicographically minimize reported micro-dollar cost, elapsed milliseconds, then original slot and candidate ID. Previous proposer feedback contains only slot/status labels, without raw oracle or evidence details.
- Failure handling: preserve invalid candidates, callback errors and UNKNOWN/ineligible outcomes; reject mismatched source/oracle receipts. Stop on observed budget overrun. No attempt is silently regraded or replaced.
- Result: CANDIDATE_PENDING_INDEPENDENT_VERIFICATION or NO_ELIGIBLE_CANDIDATE. Neither status authorizes protected delivery.

## Trust and scientific limits

The callbacks are operator-supplied Python code, not isolated model workers. The scheduler does not generate patches, execute repository tests, implement an authenticated FAR contract adapter, authenticate supplied digests, attest evaluator independence, enforce a prepaid monetary cap, constrain wall time, merge PRs, or prove correctness of unobserved behavior. A self-declared PASS is not independent evidence; the source and oracle bind only supplied strings. Future integration must invoke the existing native verifier and external exact-head provenance collector, using independently frozen task oracles and protected GitHub review/merge controls.

A real comparative study must register a distinct experimental treatment (e.g. one candidate versus bounded search with the same total budget) before prospective enrollment. Do not retrofit this component into the already registered FAR-FACTORY-SELF-EVAL-001 treatment midtrial, change its oracle, or pool unrelated historical results. Negative and timeout outcomes remain part of any later denominator.

## Validation scope

The focused suite exercises hard gates, UNKNOWN results, mismatched receipts, duplicate candidates, base-SHA mismatch, budget accounting, malformed scalar types, exception redaction, feedback isolation, and deterministic tie-breaking. It does not provide a behavioral accuracy estimate. Hosted CI and independent review remain separate requirements before protected integration.
