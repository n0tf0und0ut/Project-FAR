# Governed FAR research corpus

Status: **Research infrastructure and generated Research synthesis; not Accepted theory or promotion authority**

This directory is the permanent interoperability layer between the existing living-research inbox, governed repository artifacts, and a reproducible current synthesis. It does not replace the living discovery, lifecycle, dependency, review, promotion, or implementation machinery. It is **not autonomous semantic research**: people acting through governed review still verify primary sources and declare atomic findings, relations, scopes, mechanism mappings, and conclusion rules.

The chain is:

`content-addressed sources → atomic findings → deduplicated mechanisms → scoped conclusions → current frontier`

`corpus-v1.0.json` declares source-bound observations and conclusion rules, not synthesis results. The reconciler inventories paths matched by the declared repository rules, current living candidates, frozen external receipts, and exact PR snapshots; an unclassified matching material path fails validation. It then evaluates governed relation/history semantics, normalizes and deduplicates findings, derives mechanism state, hashes every conclusion's transitive dependencies, and builds the frontier. Every usable source is identified separately by repository path, source identity, external identifier, content hash, version, availability, review status, and evidence-usability state. `synthesis-v1.0.json` and `docs/research/current-research-frontier.md` are derived views and never independent authority.

Mutable generated living state is a `dynamic_dependency`, not an immutable evidence source. Its current bytes are schema/version checked and content-hashed on every reconciliation; that hash contributes to the synthesis-input identity and stale-view detection, but the generated state cannot support an observation or acquire evidence status. Immutable evidence must instead be registered as a content-addressed source or explicit snapshot.

“Complete” is always dimensioned:

- **inventory completeness** means only that all paths matched by declared rules and all entries in the frozen PR manifests are accounted for;
- **evidence completeness** is not established while unverified leads or unavailable evidence remain;
- **search completeness** is bounded to declared searches and frozen refs;
- **synthesis completeness** means deterministic closure over the active governed semantic inputs;
- **global/open-world completeness is unestablished**.

Run:

```bash
python tools/reconcile_research_corpus.py --write  # intentional regeneration
python tools/reconcile_research_corpus.py          # fail on stale or invalid state
```

## Safe external and scheduled-task intake

Freeze any externally obtained file without executing or interpreting it:

```bash
python tools/reconcile_research_corpus.py --ingest FILE --origin scheduled_task
```

The command copies exact bytes to `external/<sha256>.bin`, writes a receipt identifying the bytes as a discovery lead with `primary_evidence_verified: false`, and immediately refreshes `research/living/corpus-reconciliation-v1.0.json`. It never adds a finding, executes content, or promotes status. A reviewed lead advances only through an explicit entry in `reviewed-inputs-v1.0.json` that binds the exact candidate, independently verified primary evidence, exact review record, scope, and governed observations. All three artifacts are hash-checked. A summary, DOI, URL, scheduled-task output, or AI output cannot support an EVIDENCE finding merely by existing. Missing historical output stays `missing`; it is never fabricated.

The unattended living-research runner refreshes the same reconciliation after every discovery run. Its workflow then regenerates the synthesis/frontier using protected-main code and commits those Research-only views to the permanent inbox branch. Candidate metadata remains an untrusted lead until governed review verifies primary evidence.

## Invalidation and governance

`make research-check` recomputes the bounded inventory, canonical corpus hash, relation/history state, dependency hashes, and both views. Only `SUPPORTS`, or a governed equivalent/narrower replacement, can provide positive support. `CONTRADICTS`, `QUALIFIES`, and `UNRESOLVED` block unconditional mechanism support; `CORRECTS` and `SUPERSEDES` retire their complete transitive target history and may replace it only under an explicit replacement effect. Withdrawal, narrower scope, epistemic ceiling, conflict, or stale dependency propagates to conclusions and the frontier without becoming negative evidence.

A source mutation, withdrawal, correction, contradiction, missing/unknown dependency, duplicate identity/alias, cycle, unsupported evidence label, stale view, unclassified matching input, path escape, symlink, malformed hash, or ambiguous active claim fails closed or produces an explicit unresolved state. Absence of a graph edge never proves independence.

Architecture comparison uses the fixed six-way vocabulary requested by the corpus schema. It compares mechanisms literally against current FAR/Saturation surfaces; aliases do not create mechanisms, absent edges do not imply independence, and repetition does not strengthen evidence.

Automation has no scientific promotion authority. Any correction to Project FAR still requires the existing Question → Execution → Observation → Discovery → Replication → Acceptance → Promotion → Repository Change path and the protected living promotion/implementation controls.
