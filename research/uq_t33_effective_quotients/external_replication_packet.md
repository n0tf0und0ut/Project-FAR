# UQ-T33 R8 — independent source-to-behavior replication packet

**Status:** Research protocol, prepared but **NOT EXECUTED**. Does not supersede EFR-001 and is not I3 evidence by itself.

## Verification target

Test whether an independently obtained, pinned *real* Project FAR application implementation's final decision-integrity status resolver agrees with the three-flag observational abstraction for every accepted finding-rule set, and whether the locally executable evidence generator is fail-closed.

Source artifact: commercial/far-decision-integrity/src/far_decision_integrity/adjudicate.py at protected-main commit aa5cb8faf36b5e033bb96bf6e9f7f3f351387913.

Pinned source Git blob: d6167a41ddff47675db004da2f1bfe409acd7251.

Pinned source SHA-256: cbfaa4462a41aefaaff73344e389e87d50cd95071cd13b11515526c33e22c073.

The target is an **existing real implementation** (a four-status decision-integrity component), not the project-authored toy controller. The observation contract is the adjudicator's returned status alone, after findings have been generated. No larger source domain, environment, actual-world decision accuracy or full-service state bound is in scope.

## Independence, withholding, custody

Two eligible third-party investigators must be outside Project FAR control and from distinct organizations, disclose prior exposure to the project's proofs and code, and perform their work separately. Copies of the supplied status-model proof and the verifier's expected outcomes should not be used during independent re-derivation; since this PR is publicly reviewable, the investigator must report any actual exposure rather than claiming technical blinding that was not enforced.

Each investigator obtains the pinned Git tree through their own authenticated or public means, records commit/tree/source blob/SHA-256, documents Python/runtime/dependency versions and the source module actually imported, and separately derives the status partition *from original source*, not from the Project FAR checker. Retain independent logs, counterexamples, reviewer identity and disclosed conflicts. Do not treat two invocations of one LLM or a team directed by Project FAR as I3 external independence.

## Proof and runtime obligations

1. **Source identity:** verify both pinned digests of the source independently; report mismatch as a failure, not as an automatic re-pin.
2. **Actual loaded code:** confirm the executing module's real path and bytes match that source; reject module shadowing, monkeypatching or unexpected interpreter/environment changes.
3. **Complete relevant branches:** independently trace the real resolver's input rule-ID set, all three precedence guards, all four outcomes and final return propagation. Check whether earlier code can bypass or overwrite this status before return.
4. **Exact observation boundary:** restrict the assertion to returned status; inspect any claimed expansion into findings, error outputs, external semantic auditing or other fields and reject unsupported promotion.
5. **Concrete tests:** exercise all 8 flag combinations in the real function, at least two distinct rule names in each non-singleton category, overlapping unsupported+alternative+unverifiable findings, and no-findings baseline.
6. **Symbolic equivalence:** for arbitrary finite sets F of ordinary string rule IDs, independently prove or refute that resolver status depends only on membership in the five unsupported rules, six unverifiable rules and the alternatives marker.
7. **Dynamic wrapper scope:** if claiming an eight-state state machine, verify that its ADD action is an explicitly declared mathematical wrapper, not an actual service API. Distinguish eight representational states from the four behavioral quotient classes. A claim that the whole adjudication runtime has four states fails scope.
8. **Mutations:** attempt changed source bytes with recomputed claimant digests, reordered precedence, injected final override, omitted imported findings source, unrecognized future statuses, wrong module path, and a new upstream finding ID outside the bounded vocabulary. Record whether each attack is detected, irrelevant under the exact frozen scope, or still unresolved.
9. **Evidence return:** preserve source bytes/digests, command lines, stdout/stderr, interpreter and import paths, independently written proofs and adversarial cases, unmodified and mutated verdicts, and an independent signed/authenticated report.

The source checker can be replayed with:

    python -m unittest -v tests.test_uq_t33_source_bound_status
    python -m unittest tests.test_uq_t33_effective_quotients tests.test_uq_t33_evidence_gate tests.test_uq_t33_source_bound_status

The code under review is research/uq_t33_effective_quotients/source_bound_status.py and its source-level study is real_implementation_correspondence.md. This project's tests and proof text are **not** substitutes for independent evaluation.

## Pre-registered failure and completion criteria

- **FAIL:** any reproduced returned status inconsistent with the three-flag abstraction under the exact frozen subject and valid in-scope input; any unhandled bypass of the captured terminal status logic; any valid counterexample to the claimed dynamic wrapper; forged or unbound source identity in an asserted success report.
- **INVALID/UNDETERMINED:** wrong source, incomplete imported program, unverified runtime path, missing test input trace, absent investigator disclosures, untrusted external reviewer provenance or unsatisfied isolation/independence.
- **PASS limited source scope only:** both independent teams derive the same result with no surviving material counterexample and provide all required provenance; it still does not certify the entire service, an actual external deployment, or customer utility.

## Current actual observation

The Project FAR agent produced and locally tested the checker and synthetic source-mutation cases. No outside investigator has submitted an I3 proof, real-runtime execution transcript, independently replicated source certification, or signed acceptance. The standalone scratch environment lacked the production checkout, so full-checkout-specific tests must **fail closed** until run there. GitHub source fetch confirmed the pinned source blob on both the current PR head's ancestry and protected main; that fetch is source provenance, not an executed real-world runtime trace.

No claim of third-party certification, complete real-process correspondence or governed research promotion follows from adding this packet.
