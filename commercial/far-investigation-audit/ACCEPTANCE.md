# FAR Investigation Lab v0.4 — Testable Acceptance Contract

**Classification:** Research prototype; not certified independent fact verification, not a production service, not an Accepted FAR/FARA/FARO research promotion.

## Demonstrated by locally repeatable execution

| Requirement | Test and result | Guarantee boundary |
|---|---|---|
| Source input → candidate extraction → report | `full_cli.py` on `examples/full_speech.json` and `examples/complete_evidence_case.json`; `webapp.py` TestClient scenarios | Extraction candidate coverage/semantics are not independently measured |
| Exact source quotations | `engine.anchor` and tamper/offset regressions | Hash proves supplied bytes, not authentic external origin |
| Text/HTML/subtitle extraction replay | Archived `raw_snapshot_utf8`, verification recomputes extraction and cue offsets | PDFs, provider transcripts and some acquired materials remain nonreplayable and explicitly reported |
| Explicit finite propositional reasoning | Primary exhaustive checker + separate bitmask oracle; 220 seeded formula cases checked against SymPy satisfiability | Tests the supplied formalization only; does not establish natural-language fidelity |
| No false fallacy from generated labels | Heuristic/model proposals without explicit author-supplied formulas return `NOT_CHECKED_UNFORMALIZED` | Does not automatically solve free-text reasoning validity |
| Historical cutoff semantics | Missing verification flags stay unknown, malformed dates rejected, known late captures excluded | Flag can be author asserted; independent source/publisher dating is not established |
| Exact JSON table calculations | Bounded row counts, filters and decimal sums; rational-oracle cancellation tests span both exponent limits and the 10,000-row cap | Only measures the captured data and chosen operation |
| Report/package replay | Recreates human-readable report and proposal-derived audit, requires raw snapshots for replayable extraction methods, rejects promoted manifest assurance flags, checks review signatures where present | Unsigned whole-package replacement remains possible; a signature must be checked against external trusted key custody |
| Optional network/audio/model paths | Unit tests use injected adapters, permissions/consent gates and fake provider clients | No authenticated live provider/model transcriptions, service availability or real-cost evaluation |
| Threat boundary | Local-only HTTP UI, opt-in remote calls, pinned HTTPS DNS/redirect checks, input bounds | No full penetration test, production authentication, provider/data rights assessment or privacy certification |

## Local reproduction

```bash
python -m pip install -r commercial/far-investigation-audit/requirements-dev.txt
python -W error::ResourceWarning -m unittest discover -s commercial/far-investigation-audit/tests -p 'test_*.py' -v
python -m compileall -q commercial/far-investigation-audit
python commercial/far-investigation-audit/full_cli.py commercial/far-investigation-audit/examples/full_speech.json --output /tmp/far-contract-case
python commercial/far-investigation-audit/full_cli.py --verify /tmp/far-contract-case
python commercial/far-investigation-audit/evaluate.py commercial/far-investigation-audit/examples/diagnostic_cases.json
```

## Blocking criteria for declaring independently auditable real-world verification

1. **Semantic fidelity:** independent, blinded domain reviewers must compare transcript/source claims and evidence transformations to FAR's claimed meanings and formal propositions, across adversarial and representative cases.
2. **Evidence provenance:** independent authenticity and historical availability controls (publisher snapshots, timestamped archives, signatures where available); search/source-lineage analysis must be assessed for recall and error.
3. **Inference validity beyond finite Boolean logic:** causal/statistical/quantified/normative cases require domain-specific validators or explicit abstention. A model's verdict alone never supplies proof.
4. **Production delivery:** full security/authentication/privacy/data-rights audit and live third-party integration trials; no live transcription/search quality is established by offline fakes.
5. **External measured performance:** preregistered, blinded, matched comparisons against strong baseline products, including accuracy, abstention, false-certainty, cost and latency. The existing Project FAR #518 and EFR programs remain separate and unexecuted here.
6. **Hosted exact-head CI and required independent review:** GitHub Actions jobs must actually start and complete successfully on this exact PR head. Earlier observed `runner_id=0`, `steps=[]` results are not code execution and must not be waved away.

**Readiness:** bounded offline analysis is testable; general consumer claim-verification accuracy and production readiness remain **NOT ESTABLISHED**. A green local suite must never change those statuses.
