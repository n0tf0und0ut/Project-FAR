# Internal investigation correctness and matched comparator campaign

Status: **Research; project-controlled exploratory execution. External scientific verification/recruitment deferred by user.** This is separate from EFR-001 and the untouched 60-case confirmatory benchmark. No Accepted theory, field-truth gate, product-readiness or customer-value claim changes.

The internal campaign executed the requested correctness tests and the runnable local comparisons. It did **not establish commercial advantage**. All cases and reference labels were authored with prior implementation exposure. They are controlled software probes, not unseen or independently adjudicated real investigations. Public-paper intake motivated failure classes; these runs do not replicate those papers' studies.

## Results and decision

- **16/16** source-to-report controls passed their declared checks. All packages replay. Premise truth, mapping fidelity, source eligibility, formal validity and factual truth remain distinct. All **37** factual predictions are ABSTAIN: zero decisive factual coverage.
- Two deliberately collapsed quantifier/threshold interpretations remain **formally valid despite unfaithful meanings**. FAR does not independently verify their semantics. These controls expose the interpretation gap rather than certify that it has been solved.
- On identical supplied formulas, FAR and SymPy agree on **40/40 decisive FAR cases**; SymPy substitution verifies **15** FAR countermodels. FAR abstains on **6/46** cases beyond its 12-atom bound (13,16,25-atom probes); SymPy solves all six. This supports a bounded implementation comparison, with a concrete FAR coverage disadvantage, not novelty or semantic reliability.
- Six raw-source comparisons use identical supplied document bytes and no FAR-only formula annotations. FAR recovers **13/13 exact reference quote targets**; Noesis minimal recovers **0/13** because its classifier is absent, visibly reports degraded extraction, and refuses all six answers. Both avoid decisive world-truth verdicts. Noesis evidence bundles verify. This limited configuration cannot support a claim that FAR beats a fully configured Noesis system. Exact-span recall here is not independently measured semantic claim recall.
- Two follow-up pairs execute actual prior investigations, then reuse the same Noesis warehouse and import verified FAR package bytes. Extra source availability is observed in both. No factual-answer benefit is demonstrated in this configuration, and no human corrections or customer time savings were measured. FAR's reuse is explicit caller import, not an automatic persistent claim graph.

**Next product question:** can a configured system resolve meanings and applicable evidence while reducing consequential errors and retaining useful coverage? These internal results do not answer it. A growing history or a green logic checker alone cannot establish that value.

## Raw-text workflow measurements

| Case | FAR exact quote hits | Noesis minimal hits | FAR workflow seconds | Noesis workflow seconds | Noesis outcome |
| --- | --- | --- | --- | --- | --- |
| true-premises-invalid | 2/2 | 0/2 | 0.129 | 4.747 | refused / classifier unavailable |
| false-premise-valid | 3/3 | 0/3 | 0.135 | 5.061 | refused / classifier unavailable |
| quantifier-faithful | 2/2 | 0/2 | 0.329 | 5.715 | refused / classifier unavailable |
| threshold-faithful | 2/2 | 0/2 | 0.128 | 5.005 | refused / classifier unavailable |
| exact-citation-irrelevant | 2/2 | 0/2 | 0.131 | 6.856 | refused / classifier unavailable |
| hindsight-later-capture | 2/2 | 0/2 | 0.158 | 5.839 | refused / classifier unavailable |

Times are single local operational observations, including serialization, process startup, ingestion/audit, export, verification and verdict extraction. FAR uses one source-to-report CLI plus replay; Noesis uses init/ingest/ask/export/verify CLI calls. Tool architectures and enabled capabilities differ. Do not convert these small configured-workflow observations into a product-wide speed claim or statistical population estimate. Earlier run-002 FAR timing omitted parent-side verification and is retained but **excluded** from this comparison.

## Actual retained-history treatment

| Pair | Noesis documents fresh → retained | FAR follow-up seconds fresh / retained | Noesis follow-up seconds fresh / retained | Result |
| --- | --- | --- | --- | --- |
| retained-lamp | 1 → 2 | 0.125 / 0.196 | 4.371 / 4.723 | No decisive factual answer in either condition |
| retained-audit | 1 → 2 | 0.179 / 0.142 | 7.791 / 4.509 | No decisive factual answer in either condition |

Initial investigation costs are retained separately in each `prior_investigation` record. Noesis reuses its actual prior config/warehouse and does not reingest the retained prior source. FAR reads prior input bytes once, binds them to the in-memory replayed manifest hash, then explicitly imports that verified source. Both receive the same prior text. Source count is not a factual-accuracy or customer-value metric; neither two timing pairs nor zero answers establishes a moat.

## Registration and preserved failures

All protocol/case/runtime hashes were frozen before each corresponding execution. Original cases and references are byte-identical across versions.

| Registration | Frozen executable source | Disposition |
| --- | --- | --- |
| [v1](registration-v1.json) | `97524e4ea9c8944d559966a08b8ae6cecc367935` | 16 pipeline and 46 formula controls ran; ten Noesis calls failed because the harness passed relative source paths after changing cwd. Those are harness errors, not competitor losses. |
| [v2](registration-v2.json) | `703da0d62b8c2b13954d2a46d9a01e327cbee48d` | Absolute-path repair; all declared runs completed. History was an availability-only control; FAR timing did not yet include all parent-side verification. |
| [v3](registration-v3.json) | `29a2095ef719820a654e2fb1b5a50379e7af71bc` | Declared timing/history procedural extension before its outcomes; same case bytes; actual reuse and full-workflow timing. Primary report above uses this version. |

Regressions preserve root causes: relative-path adapter binding, complete timing scope, read-once verified-history import, reuse of the prior warehouse, source/registration drift and duplicate-key rejection. No failed run, null result, boundary abstention, reference or original registration was erased to improve the report. A subsequent software-only test-isolation repair moves the changed-byte regression fixture outside the checkout after hosted tracing correctly rejected its temporary writes; trace policy and all frozen campaign bytes/results remain unchanged. Independent software PR review does not make the experiment scientifically independent.

## Exact comparators and unavailable arms

| Comparator | Version / configuration | Executed scope |
| --- | --- | --- |
| FAR | engine/service/checker 0.4.6; repository baseline `81a84bbf48325a6c8b732872cd7ce9977f2d2f5a` | Frozen source-to-report fixtures, supplied-formula checker, raw local CLI, replay and explicit prior-source import |
| SymPy | 1.14.0 | Same supplied formulas; satisfiability and separate countermodel substitution |
| Noesis | 0.1.0, commit `d38eb1fd956843b6eeeaeb582d3b4e1092255d94`; minimal profile, no classifier weights/providers | Real local CLI ingestion, explicit degraded/refusal behavior, portable bundle export/verification and persisted warehouse reuse |
| Minerval | Official architecture screened; local stack/authorized model-backed ingestion not configured | **NOT RUN**; missing arm, not a FAR win |
| Fact Engineering / Stamp AI | Official API docs require authenticated token and quoted credits; no authenticated paid arm configured | **NOT RUN**; missing arm, not a FAR win |

Primary access records: [Noesis source](https://github.com/Ikey168/Noesis/tree/d38eb1fd956843b6eeeaeb582d3b4e1092255d94), [Minerval architecture](https://github.com/minerval-ai/minerval/blob/main/web/content/architecture.md), [Fact Engineering API](https://fact.engineering/docs/api). Documentation/marketing overlap is not a performance result. The selected local configuration omits the model-enabled functionality that could change the comparison.

Experiment subprocesses made **zero external model/API calls** and used no API credentials. External API charge for those subprocesses is zero; analyst effort, host compute, CI and human correction cost are **not measured**. Model tokens, provider capability, independent adjudicator effort, real investigations and customer benefit cannot be inferred from this experiment.

## Replay and fresh execution

Portable ZIPs retain every artifact-manifest-listed raw JSON receipt, source text, FAR package, Noesis answer bundle and failure record. Generated Noesis databases are excluded; CLI inputs/commands and the pinned source reconstruct them. Run result and artifact-manifest JSON copies are also directly readable beside each ZIP.

| Archive | Bound artifact files | Recorded failures | SHA-256 |
| --- | --- | --- | --- |
| [run-001-portable.zip](run-001-portable.zip) | 247 | 10 | `ae6a797c98807beceadc7e0d9c5ffe3b2b42da060c63dd7564b1f08339595f1e` |
| [run-002-portable.zip](run-002-portable.zip) | 295 | 0 | `d73857c80cb17d5f93f161a72560bb305fc095a754717f28ea37ee2c238b6b2b` |
| [run-003-portable.zip](run-003-portable.zip) | 325 | 0 | `a317735c022174fc22b4b069c6750a9924a3fadfdf03ea3e54436b7f10b4a5b1` |

```bash
python -m zipfile -e commercial/far-investigation-audit/evaluation/internal-001/run-003-portable.zip /tmp/far-internal-replay
python tools/run_internal_investigation_evaluation.py verify /tmp/far-internal-replay/run-003
```

The primary run verifies 325 retained files, 28 FAR packages and three controlled auditor records. Noesis bundles have their own captured successful verification receipts; they can be verified again using its pinned CLI. The controlled temporal records assume fixture date-verification flags deliberately; they are separate from the raw workflow's unverified source metadata and are not external timestamp seals.

For a new execution, create an isolated worktree at the frozen executable source commit, clone Noesis at its exact pin, install `comparator-requirements.lock` and its minimal package into one isolated Python environment, then make a **new** registration and output directory:

```bash
python tools/run_internal_investigation_evaluation.py freeze --output /tmp/new-registration.json --noesis-root /path/to/pinned/Noesis
python tools/run_internal_investigation_evaluation.py run --registration /tmp/new-registration.json --output /tmp/new-internal-run --noesis-cli /path/to/venv/bin/noesis
```

The registration records exact dependency versions, host/Python metadata and runtime hashes. A content hash is not an independent timestamp, identity seal or scientific replication. Do not overwrite historical registrations or use these fixtures as unseen tests. Do not execute the frozen confirmatory study or EFR under this exploratory authorization.
