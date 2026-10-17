# FAR Investigations: bounded auditable evidence and inference checks (Research prototype)

**Status:** experimental downstream commercial/research component. It does **not** modify or claim Accepted FARA/FAR/FARO authority, the frozen FAR-CORE theory, the EFR campaign or the 60-case confirmatory benchmark. **It does not independently establish real-world truth.** No general-purpose text/video ingestion or automatic semantic adjudicator is claimed.

This implements a concrete, independently replayable *formal* audit of two distinct steps:

1. **Evidence → premise.** Validate an exact quoted span of a content-addressed source and, **when the auditor is supplied a reviewed/inspectable propositional formalization of that source content**, decide whether the *formalized evidence* entails or contradicts the *formalized premise*.
2. **Premises → conclusion.** Exhaustively check entailment across all valuations of the supplied propositional atoms and return a countermodel when entailment fails. Inconsistent premises never receive a vacuously favorable result.

Different possible interpretations are checked separately; source provenance, asserted evidence relationships, uncertainty, source-origin grouping, and time cutoffs remain visible. No composite True/False verdict is produced. An assessor's label does not override the formal relation.

## Run

Python 3.11+, no third-party dependencies:

```sh
python commercial/far-investigation-audit/cli.py commercial/far-investigation-audit/examples/causal_jump.json --output /tmp/far-audit.json
python -m unittest discover -s commercial/far-investigation-audit/tests -p 'test_*.py' -v
```

The input (`far-investigation-audit/0.1`) is a JSON file containing:

- `investigation_id`, an ISO 8601 UTC `as_of` cutoff and a dictionary of named propositional `atoms` with human-readable definitions;
- `sources`: `id`, UTF-8 `text`, its SHA-256 hash, `published_at`, `captured_at`, and a **reported, not authenticated** `origin_id`;
- `claims`: source-anchored exact quote spans (`start` inclusive, `end` exclusive), natural-language `text`, propositional `formula`, and `mapping_status` (`unreviewed` or `review_recorded`);
- `evidence`: exact quote spans, target `claim_id`, author-proposed relation and optional propositional `formula`. Without the formula, the evidence's semantic relation is explicitly untested;
- `interpretations`: each named candidate has `premises`, `conclusion`, and `mapping_status`. Distinct readings cannot be merged into a majority vote;
- `unknowns`: open questions retained verbatim in output.

Formula operators are JSON `{"atom":"P"}`, `{"not": EXPR}`, `{"and":[EXPR,EXPR]}`, `{"or":[EXPR,EXPR]}`, and `{"implies":[EXPR,EXPR]}`. Variables must be declared. This finite propositional subset cannot establish causal identification, quantifiers, open-world generalizations, statistical evidence quality, social/normative inference, or natural-language intent. It rejects unverifiable or malformed source spans/hashes, limits source size and graph complexity, and returns `NOT_CHECKED_ATOM_LIMIT` for more than 12 distinct variables rather than silently asserting validity.

**Temporal discipline:** only source snapshots *both published and captured* by `as_of` are eligible for evidence→premise formal support. Later archives or unknown historical editions require separate version-specific substantiation; the conservative exclusion avoids hindsight leakage. The cutoff does **not** prove that the language model developing a formalization lacked future parametric knowledge.

**Replay:** input hash, method version, per-reading checked assignment count, returned countermodel and deterministic report hash are included. A changed bundle produces a changed input hash; hashes prove consistency of supplied bytes, **not** identity/authenticity or independence of the real source, semantic correctness of atom mappings, or correctness of a third-party assessor. `mapping_status=review_recorded` is an *unauthenticated claim of review*, not independent review evidence. Fail-closed `InvalidBundle` errors are not silently turned into a "verified" result.

## Assurance boundary

For a reading with status `ENTAILS_CONDITIONALLY`, the **formal formulas** have been checked to entail the formalized conclusion, conditional on the mappings, premises, interpretation and bounded propositional semantics. It does *not* follow that the natural-language argument is deductively valid or its conclusion true. `FORMALLY_SUPPORTS_IF_MAPPINGS_CORRECT` likewise establishes only formal entailment between **supplied** formalizations, not that the cited words mean those formulas, represent reliable facts, or are independently corroborated.

Before any commercial truth-oriented claim, FAR additionally needs (1) real media/source capture and authentic historical versions, (2) independently checked quote-to-proposition mapping, (3) retrieval and adversarial evidence assessment, (4) source dependence/copying analysis, (5) causal/statistical/nonmonotonic validators, (6) authenticated reviewer records, (7) head-to-head blind evaluation against strong matched systems, and (8) reliable operational delivery and buyer proof. Those capabilities are not simulated here.

## Existing research used; no novelty claim

- W3C [PROV-O](https://www.w3.org/TR/prov-o/): entity/activity/agent provenance and derivation chain. This implementation adopts content-addressed source snapshots and inspectable transform boundaries, but does *not* claim PROV-O compliance.
- [Argument Interchange Format](https://doi.org/10.1017/S0269888906001044) and [Argument Web](https://pmc.ncbi.nlm.nih.gov/articles/PMC6979725/): premise, inference-scheme, conclusion and conflict separation. JSON `interpretations` is only a bounded typed application, **not** an AIF serializer.
- [AVeriTeC](https://aclanthology.org/2024.fever-1.1/): fact-verification evaluations must measure evidence as well as verdict correctness. This prototype contains no automated AVeriTeC run.
- [No Hindsight for LLM Fact-Checkers](https://arxiv.org/abs/2610.04888): explicit point-in-time source eligibility to prevent post-claim evidence from silently establishing claims.
- [Rethinking Inline Citation Verification](https://arxiv.org/abs/2610.05355): do not equate citation existence with citation support; expose review and intent boundaries.
- [Auditable Claims about AI Agents](https://arxiv.org/abs/2610.07459): source claims must declare scope, evidential records and explicit decision checks before verdict, including coverage versus integrity.
- [Same Claim, Different Interpretations](https://arxiv.org/abs/2610.20457): alternative interpretations require outcome-sensitivity testing; recording interpretations alone is not an accuracy guarantee.
- [Argument Graph Uncertainty](https://arxiv.org/abs/2610.20328): structured argument uncertainty can complement but not substitute for verified entailment or source authenticity.
- Project FAR [Saturation Baseline v0.5](../../docs/architecture/saturation-baseline-v0.5.md): provisional capability classes, no implicit collapse of claim/evidence/inference status. This implementation uses existing extension points rather than changing the baseline or canonical core.

The next independent test is a blinded real-cases comparison assessing attribution fidelity, evidence-to-premise judgments, inference validity, abstention, false certainty, cost and latency. The registered #518 and EFR experiments remain unchanged and unexecuted by this component.
