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
- `sources`: `id`, UTF-8 `text`, its SHA-256 hash, `published_at`, `captured_at`, and a **reported, not authenticated** `origin_id` (nullable when unknown);
- `claims`: source-anchored exact quote spans (`start` inclusive, `end` exclusive), natural-language `text`, propositional `formula`, and `mapping_status` (`unreviewed` or `review_recorded`);
- `evidence`: exact quote spans, target `claim_id`, author-proposed relation and optional propositional `formula`. Without the formula, the evidence's semantic relation is explicitly untested;
- `interpretations`: each named candidate has `premises`, `conclusion`, and `mapping_status`. Distinct readings cannot be merged into a majority vote;
- `unknowns`: open questions retained verbatim in output.

Formula operators are JSON `{"atom":"P"}`, `{"not": EXPR}`, `{"and":[EXPR,EXPR]}`, `{"or":[EXPR,EXPR]}`, and `{"implies":[EXPR,EXPR]}`. Variables must be declared. This finite propositional subset cannot establish causal identification, quantifiers, open-world generalizations, statistical evidence quality, social/normative inference, or natural-language intent. It rejects unverifiable or malformed source spans/hashes, limits source size and graph complexity, and returns `NOT_CHECKED_ATOM_LIMIT` for more than 12 distinct variables rather than silently asserting validity.

**Temporal discipline:** only source snapshots *both published and captured* by `as_of` are eligible for evidence→premise formal support. Missing dates remain `UNKNOWN_TEMPORAL_ELIGIBILITY` and cannot satisfy that gate. A claim cannot corroborate itself by citing its exact same source span. Later archives or unknown historical editions require separate version-specific substantiation; the conservative exclusion avoids hindsight leakage. The cutoff does **not** prove that the language model developing a formalization lacked future parametric knowledge.

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

## 0.2 bounded structured-evidence extension

This Research-only extension adds a **second, independently typed computation lane** for numeric facts in frozen JSON snapshots. It complements—not substitutes for—the propositional evidence/inference checks above. The existing `far-investigation-audit/0.1` input envelope is backward-compatible: old files without structured checks are still checked as before. The engine identifies itself as `far-investigation-audit/0.2.0`. No canonical FAR IR or Accepted-theory schema was changed.

Use `data_check` on an `evidence` record **instead of** `formula`, paired with a `quantity` record on its target `claim`. An example is [examples/structured_tally.json](examples/structured_tally.json):

```json
{
  "quantity": {"value":"2", "number_span":{"start":0,"end":1}, "unit":"experiments"},
  "data_check": {"operation":"count_where", "pointer":"/experiments", "where":{"field":"passed", "equals":true}}
}
```

The snippet shows two fields belonging to **different** records. The `number_span` must point to the exact literal number in the claim's source quotation. `data_check` reads the already-hashed JSON evidence source, follows an RFC 6901 JSON Pointer (with bounds), and computes:

- `count_rows`: exact length of a selected array;
- `count_where`: exact type-safe equality count over a required field in every selected object (boolean `true` is not number `1`);
- `sum_field`: exact decimal sum over required JSON numeric fields, with finite digit/exponent bounds and a controlled precision context.

Ambiguous duplicate JSON keys, absent fields, non-numeric sums, invalid JSON pointers and unsupported forms fail closed or report `STRUCTURED_UNVERIFIABLE`. Inputs are limited to 2 MB, each source to 200 KB, selected arrays to 10,000 rows, and bounded finite decimals. Missing values are *not* quietly treated as zero. A mismatch produces an actual counter-result from the supplied dataset, rather than a model verdict.

The new per-claim `structured_value_checks` report is **separate** from the propositional `status`. It may show `STRUCTURED_VALUE_MATCH_CONDITIONALLY`, `STRUCTURED_VALUE_MISMATCH_CONDITIONALLY`, `CONFLICTING_STRUCTURED_VALUES`, or `NOT_ESTABLISHED`. Even a numeric match means only that the disclosed operation on the supplied frozen JSON produces the number recorded in the claim quotation. It **does not** verify the dataset's completeness, representativeness, origin, semantics of its columns, proper choice of statistic, associated source's authenticity, or real-world truth. The checker does not infer that a policy caused an observed change or that a reported study generalizes beyond its observed population. The original inference report separately tests whether the formal *premises* entail the formal *conclusion*.

To inspect the structured demonstration and replay the output:

```sh
python commercial/far-investigation-audit/cli.py commercial/far-investigation-audit/examples/structured_tally.json --output /tmp/far-structured-report.json
python commercial/far-investigation-audit/verify.py commercial/far-investigation-audit/examples/structured_tally.json /tmp/far-structured-report.json
```

The verifier independently **re-runs the deterministic code path**, checking the entire output against an independently provided bundle; it rejects even a report whose attacker has recalculated its own hash. This is reproducible computation, **not** independently authored verification software, proof of independent source provenance, or trusted third-party attestation.

### Exact local source capture

The optional offline importer constructs a SHA-256-bound source snapshot and, where specified, a unique exact quotation anchor:

```sh
python commercial/far-investigation-audit/capture.py document.txt --id source_1 --quote 'The observed quantity increased.'
```

The importer never fetches remote URLs or executes content; input must be UTF-8 text or JSON. The `captured_at` field records the time the command ran. Its `published_at` remains `null` unless a publication date is **explicitly supplied** with `--published-at` (the resulting date is marked unverified). The importer cannot authenticate historic availability, source lineage, or publisher identity. Unknown historical publication dates cause the existing point-in-time evidence gate to abstain rather than count the source as admissible. Ambiguous repeated quotations require `--start` to specify the exact character offset.

### Prior methods incorporated

- [FEVEROUS](https://fever.ai/dataset/feverous.html) explicitly represents factual verification evidence as sentences **and cells in tables**, with annotated numerical reasoning cases. FAR's bounded numerical path is an original *implementation of standard structured-data arithmetic*, not a novel verification algorithm or an evaluated FEVEROUS system.
- [TabVer: Tabular Fact Verification with Natural Logic](https://doi.org/10.1162/tacl_a_00722) demonstrates that table verification requires controlled operators and inference procedures; its reported performance does not transfer to this module without evaluation.
- [W3C PROV-O](https://www.w3.org/TR/prov-o/) motivates distinguishing a recorded computation and its input snapshot from the external authenticity and acquisition chain. This module does not claim PROV compliance or independently authenticated evidence.
- [AVeriTeC](https://aclanthology.org/2024.fever-1.1/) motivates separating evidence sufficiency, claim interpretation and downstream verdict quality in future independent evaluations. No performance claim is made here.

**Remaining work:** reliably retrieved and permissioned documents/media, automatic but challengeable natural-language claim mapping, authenticated reviewer attestations, independent source and temporal provenance, causal/statistical identification checks, external blind evaluations and user/customer validation. `0.2` adds only the bounded mechanical check described above, not all of these prerequisites.
