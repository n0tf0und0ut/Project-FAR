# UQ-T33 continuation: evidence needed for a real state-bound claim

**Status:** Research. Conditional deductive result plus finite-explicit implementation and tests. No canonical theory revision, external scientific replication, independent implementation audit, or real-system certification.

## The problem

R4–R6 established exact quotient computation for a complete known finite deterministic Moore machine, but do not establish that the states of a real implementation are fully captured. Finite black-box observations cannot supply that missing premise: for any tested horizon, a longer finite chain can agree on the entire observed prefix and differ later.

Separate three evidence levels:

1. **Declared model:** a finite table of states, actions, outputs and transitions. Its internal consistency can be checked.
2. **Verified refinement:** a checked proof mapping a complete concrete transition semantics to a finite abstract model, preserving each relevant observation and transition.
3. **External correspondence:** independently controlled evidence that the concrete semantics faithfully describes the specific source code, hardware, runtime environment, version, configuration, inputs and initial states of the real system.

The supplied verifier establishes only the finite-tabular version of (1) and (2), **relative to a declared complete concrete table**. It cannot establish (3).

## R7: finite behavioral envelope via a commuting abstraction

Let C be the concrete state domain, A a finite admitted action alphabet, S a finite abstract carrier of size N, and O the outcome type. Suppose total deterministic functions

- delta_C: C × A -> C; out_C: C -> O
- delta_S: S × A -> S; out_S: S -> O
- alpha: C -> S

satisfy for **every** c in C and a in A:

- Output fidelity: out_C(c) = out_S(alpha(c)).
- Transition fidelity: alpha(delta_C(c,a)) = delta_S(alpha(c),a).

Assume C includes all relevant reachable concrete states and is closed under the admitted inputs, with correctly specified output/input semantics.

**Theorem.** For any c in C and any finite action word w, the output after executing w from c equals the abstract output after w from alpha(c). Consequently C realizes no more than N distinct observational behaviors, and two concrete initial states are equivalent exactly when their abstract images are observationally equivalent. A pair that differs has a distinguishing word of length at most max(N-2,0).

**Proof.** For the empty word use output fidelity. For a word extended by one action, induct on the word length and apply transition fidelity at the reached concrete state. Applying output fidelity there gives equal observations. Thus every concrete word observation factors through alpha. Distinct concrete behaviors cannot map to one abstract behavior. The finite abstract Moore machine obeys the R4 partition-refinement depth bound, which yields the witness horizon. QED.

This is a **behavioral** bound; C itself can be infinite. It is not a claim that mere syntactic labels establish a complete real-world state model. The method is the familiar deterministic abstraction/simulation pattern and asserts no mathematical novelty.

## Executable conditional certificate

The research-only evidence_gate.py checker takes:

- a complete explicitly enumerated concrete table with state names, action names, outputs and successor indices;
- a candidate abstract table over the **same ordered action alphabet**;
- a total map from concrete indices to abstract indices;
- a claimed state bound and the canonical SHA-256 of the submitted concrete table.

It checks table totality, target closure, action coverage **relative to the given concrete table**, output fidelity, transition commutation, claimed abstract bound and digest integrity. It derives the abstract observational quotient and the max(N-2,0) distinguishing-word depth, and can return a distinguishing action-index sequence for a pair of concrete states.

A successful report always reads:

- result: FINITE_TABLE_REFINEMENT_VERIFIED
- authority: DECLARED_MODELS_ONLY
- external_system_correspondence: NOT_VERIFIED

The digest proves only that the submitted table matches the submitted expected digest. The author may regenerate both; it does not authenticate source or show that a runtime implements the table. Even explicit claims of external approval in added metadata are **not** treated as external evidence. No black-box-only inference of completeness is permitted.

The submitted example has six toy concrete states (three controller phases times a hidden flag), three abstract states, two actions, six output obligations and twelve transition obligations. The hidden flag is intentionally irrelevant under the declared model. Tests reject modifications making it behaviorally relevant.

Reproduce from repository root:

    python -m unittest tests.test_uq_t33_effective_quotients tests.test_uq_t33_evidence_gate
    python -c "import json; from research.uq_t33_effective_quotients.evidence_gate import certificate; print(json.dumps(certificate(json.load(open('research/uq_t33_effective_quotients/example_evidence.json'))), indent=2))"

The original UQ-T33 tests and twelve new correspondence tests passed locally: **25/25**. Neither these tests nor the model-level report is a proof of source-to-runtime correctness.

## What an external investigator must independently establish

- **Identity and provenance:** pin the exact source or executable artifact, dependencies, configuration, build settings, hardware and environmental assumptions. Verify source and build digests under independent custody.
- **Complete concrete semantics:** prove that all reachable behaviorally relevant state is modeled, including counters, timers, queues, persistent history, error/recovery modes, concurrency and environmental state when material; alternatively prove a sound abstraction that removes those dimensions.
- **Complete input and observation contract:** enumerate action classes and typed outcome distinctions, with a justified partition for unbounded inputs. Include unexpected, timed and failure events or explicitly narrow the claim. Verify deterministic behavior or prove a separate theorem for nondeterminism.
- **Inductive coverage:** establish an initial-state invariant, closure of all admitted transitions, output fidelity, and commuting transitions for every reachable state and input. Audit any admitted reset/replay guarantee independently.
- **Independent checking and mutation:** replay the proof/extractor against the pinned artifact. Introduce hidden-state-dependent outputs, delayed transitions, omitted input classes and false bounds and verify that the checker rejects them.
- **Scope-limited declaration:** state the exact behaviors, inputs, system version, assumptions, model-to-reality proof status, bound and verification apparatus. If correspondence is unproved, report it as unestablished rather than converting table conformance into reality.

For a finite source-level state domain, an independently verified interpreter and exhaustive enumeration can establish local transition obligations. For an infinite or large domain, a formally checked invariant and inductive abstraction can establish the same property without enumerating all concrete states. The checker here does **not** inspect source-language execution semantics or validate such a proof; that is precisely the missing external trust boundary.

## A real external-source stress test: RFC 1661

RFC 1661 (July 1994), sections 4.1 and 4.2, explicitly lists ten PPP option-negotiation control states (0–9) and calls its state transition table complete. But sections 4, 4.4 and 4.6 also describe input events, counters, timers and actions with implementation-dependent effects; illegal entries in the table also need an explicit treatment to form a total observation contract.

Primary specification: https://www.rfc-editor.org/rfc/rfc1661.html#section-4.1

**Supported by the RFC:** ten specified *abstract control-state labels* in a particular protocol model. **Not supported by that evidence alone:** that the complete concrete state of an arbitrary deployed PPP implementation has ten states; that real timers, retransmissions, configuration options and packet-processing outputs factor through those ten labels; or that a deployed binary faithfully implements the table.

This is a bounded **negative audit** of a tempting inference, not an external proof of a real-system bound, a runtime test, or independent I3 replication. A timer-dependent observable difference between two instances with the same controller label could make the ten-label mapping insufficient. Whether that occurs depends on a separately declared observation contract and concrete implementation evidence.

Established prior art includes finite-state conformance testing with a known state-count bound (Chow/Vasilevskii/W-method) and active automata-learning equivalence queries. See https://link.springer.com/chapter/10.1007/978-3-031-57249-4_6 and https://www.lrde.epita.fr/dload-new/techreps/2024-07-01.techrep.alexis-pinson.pdf. The result here is an explicit FAR applicability boundary and conditional audit artifact, not a claim to invent finite automata conformance testing.

## Research disposition

**Derived:** an observation-preserving and transition-commuting finite abstraction is sufficient to bound the number of concrete observable behavior classes and provide a finite distinguishing horizon. **Tested internally:** finite explicit evidence checking, witness production and negative mutations. **Not established:** any independent source-to-runtime abstraction proof, fully justified real input closure, real system certification, novel theorem, external I3 replication or product utility.

This does not change accepted FAR Core, closed historical evidence, or canonical UQ-T33's unresolved status. A real-system promotion requires externally verifiable artifacts plus the governing research lifecycle.
