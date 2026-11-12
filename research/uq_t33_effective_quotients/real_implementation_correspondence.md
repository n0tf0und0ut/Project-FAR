# UQ-T33 continuation — binding an existing executable source

**Status: Research.** The subject is an existing production Project FAR code path, but external I3 independence, whole-program semantics, and deployed-environment correspondence remain unestablished.

## Question and provenance

Earlier R7 verified that two supplied finite tables commute. The table claimant could still invent both tables. This investigation tests a separate requirement: binding the abstract observable behavior to the actual bytes and behavior of an existing application implementation.

- Subject: commercial/far-decision-integrity/src/far_decision_integrity/adjudicate.py.
- Frozen protected-main starting commit: aa5cb8faf36b5e033bb96bf6e9f7f3f351387913.
- Exact subject source Git blob: d6167a41ddff47675db004da2f1bfe409acd7251.
- Independently pinned source SHA-256: cbfaa4462a41aefaaff73344e389e87d50cd95071cd13b11515526c33e22c073.
- Program fragment: adjudicate() terminal findings-to-IntegrityStatus resolver.
- Observation: only returned Adjudication.status after all findings have been generated. Upstream finding generation, imports, I/O, semantic checks, other output fields and environment are not included.

## R8: source-bound output correspondence

The actual source computes rule_ids as the set of each finding.rule_id. It then assigns output status in this exact order:

1. If any rule belongs to its five-element unsupported set, status is UNSUPPORTED.
2. Otherwise, if material-alternatives-remain is present, status is UNDERDETERMINED.
3. Otherwise, if any rule belongs to its six-element unverifiable set, status is UNVERIFIABLE.
4. Otherwise status is JUSTIFIED.

Let F be any finite set of ordinary string rule IDs, U and V be exactly the two categories appearing in the frozen source, and a be the alternatives marker. Define alpha(F) as the three Boolean membership/existence flags (F intersects U; a belongs to F; F intersects V). Thus the abstract carrier has eight states.

**Deductive proof (scoped):** The frozen source has exactly the displayed if/elif/elif/else branch and returns the selected status. Each condition is equivalent to its corresponding alpha bit, in priority order. Therefore for every F the real resolver's returned status is fully determined by alpha(F). This establishes output correspondence for the named source fragment, conditional on standard Python interpretation and stable string-valued finding rule IDs. It is not a mechanized proof of the complete interpreter or entire application.

For a **separately declared analysis wrapper**, let the concrete state be F and let action ADD(r) perform set union with {r}. Then alpha(F union {r}) equals the componentwise OR of alpha(F) and alpha({r}). This defines an eight-state abstract Moore machine with actions adding one representative of each relevant category or an unrelated rule. Its 32 abstract transition obligations are checked exhaustively by the reference implementation. The wrapper is a mathematical analysis device: the actual production adjudicate function does **not** implement this event protocol. The eight-state bound and six-step distinguishing horizon pertain to this wrapper, not the whole running service.

## Stronger source evidence than an authored model table

The new source_bound_status.py checker reads the actual source path and validates both the immutable Git blob SHA and an independently calculated SHA-256. It parses the real adjudicate AST and requires the exact final statement sequence, status conditions, branch order and return expression. Source drift, mutated status priority, an inserted final override, an unavailable source file, and stale identities fail closed.

The checker does not accept a claimant-provided digest as authority. It reports SOURCE_BOUND_STATUS_FRAGMENT_VERIFIED with explicit negative fields: whole_program_correspondence=NOT_VERIFIED, deployed_environment_correspondence=NOT_VERIFIED and independent_external_replication=NOT_OBTAINED.

The added test suite contains eleven cases. Nine local negative/finite-logic cases can run without the production checkout; two integration cases require an actual checkout and then must inspect the real source blob and call the actual production adjudicate function with all eight combinations of three independently generated finding categories. An unavailable checkout causes these integration cases to skip, **not** to count as passing.

Run from the complete Project FAR repository root:

    python -m unittest -v tests.test_uq_t33_source_bound_status
    python -m unittest tests.test_uq_t33_effective_quotients tests.test_uq_t33_evidence_gate tests.test_uq_t33_source_bound_status
    python -c "import json; from pathlib import Path; from research.uq_t33_effective_quotients.source_bound_status import certify_source; print(json.dumps(certify_source(Path.cwd()), indent=2))"

## Independent verification obligations

True I3 certification requires an investigator outside Project FAR control, independent custody of the pinned implementation bytes, review or reimplementation of the proof and verifier, inspection of the execution environment, and failure-preserving reports. Repeated calls to an agent controlled by Project FAR cannot meet that definition.

The next full-system challenge is to prove source and runtime correspondence for the upstream finding-generation pipeline under a separately frozen input and observation contract. It must account for external semantic checkers, object validity, emitted findings, non-status fields and environment. The R8 certificate alone does not imply a bounded complete deployed system.

**Disposition:** the source identity and a finite observable resolver have been bound to a real software artifact for independently checkable replay, but no independent I3 replication, total application-model correspondence, or empirical process identification has occurred. Preserve this Research-only result and all negative findings.

## Third-party verification

See [the independent replication packet](external_replication_packet.md). It freezes proof obligations, source and build identity, negative controls, pass/fail standards, and evidence retention requirements. **No external I3 team has executed that protocol; no external independent certification is claimed.**
