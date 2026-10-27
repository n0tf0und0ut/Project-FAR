# Epistemic Debugger internal campaign 001

Status: **Research; developer controlled, implementation exposed, not independent scientific validation.** External EFR/confirmatory execution and recruitment remain unexecuted.

The [protocol](protocol-v1.json) and [24 semantic cases](semantic-cases-v1.json) were committed in `1825f1ab1123b2f63c4f9cbf07e0700de5a90686` before implementation. The [architecture and assurance boundaries](../../EPISTEMIC_DEBUGGER.md) define exactly what these controls can falsify. These are authored acceptance tests, not an estimate of real-world semantic accuracy.

## Observations

| Measurement | Result | Interpretation |
| --- | --- | --- |
| Frozen semantic controls | 8 supported in grammar; 8 changed meanings rejected; 8 correct abstentions | Zero disagreement with the developer-authored references in this set; no population accuracy estimate |
| Matched source-to-report cases | 40 per FAR configuration: previous 16 plus 24 frozen controls | Identical primary inputs and local evidence; complete package creation and replay included |
| Prior quantifier/threshold collisions | Old formal proof passes; debugger rejects changed meanings | Demonstrated correction of two prior FAR workflow gaps |
| Factual decisions | 85 `NOT_ADJUDICATED` in the 40-case set | No increase in external factual-verdict coverage; no hidden truth promotion |
| Conditional semantic acceptance | 10 readings | Conditional on grammar, explicit formulas and premises; not verified world conclusions |
| Noesis | Six actual pinned minimal-config CLI investigations and portable-bundle checks | All answer statuses `refused`; classifiers/providers absent. These are missing configured capabilities, not FAR wins |
| Logic oracle | 216 exhaustive three-formula combinations plus pre-existing seeded SymPy checks | Agreement about supplied finite formulas only |
| Property tests | Generated threshold contrasts, temporal identity and modal-negation abstention | Hypothesis with deterministic generation; bounded software assurance |
| Fault injections | Three declared mutations detected | Quantifier collapse, accepting every mapping, and erased correction propagation; not exhaustive mutation adequacy |
| Memory | Checked import, lookup availability, eight affected nodes invalidated, earlier state preserved | No demonstrated accuracy or speed gain; see [measured record](memory-experiment-v1.json) |

The frozen [distribution-shift protocol](distribution-shift-protocol-v1.json) uses the English text retained in a pinned multilingual FraCaS source. It runs the complete heuristic workflow and checks every emitted package. [Results](distribution-shift-results-v1.json) report coverage, missing texts, failures and abstentions. FraCaS inference labels are **not** used as gold atom mappings, and no NLI or factual accuracy score is fabricated. Grammar is not tuned from these outcomes. The raw dataset is not redistributed because a source-repository license was not located; its exact repository revision/path/hash and extraction recipe are retained.

## Runs and failures

[Registration v1](registration-v1.json), [runtime v1](runtime-v1.zip), [portable run 001](run-001-portable.zip) and its [summary](run-001-summary.json) preserve the first executed configuration. A later optional-lineage unit test exposed an incompatible call to `Draft202012Validator.validate`: the repository's constrained validator exposes `iter_errors`. Both affected tests are preserved in [known-failures-v1.log](known-failures-v1.log). The repair uses the existing supported interface; it does not weaken validation. Additional fixes compose `far-ir/2.0` collision verification and preserve the original campaign.

[Registration v2](registration-v2.json) freezes the repaired runtime before the successor execution. [Portable run 002](run-002-portable.zip), [runtime v2](runtime-v2.zip), [summary](run-002-summary.json) and its artifact manifest preserve all source-to-report outputs, commands, elapsed times and Noesis receipts. Runtime and input hashes are checked before execution. Generated Noesis databases are omitted; exact CLI commands, source snapshots and source/configuration pins reconstruct them. Each FAR package remains independently replayable using the corresponding exact runtime plus unchanged repository contracts.

An early pre-execution harness invocation found no registration file because the preceding shell search did not reach the freeze command. Its traceback is retained as `harness-failure-v0.log`; it produced no experimental result. The first component attempt also exposed a supplied-proposal compatibility regression and missing optional dependencies; `implementation-failures-v0.log` preserves it. Supplied legacy proposals now stay unchanged unless the debugger is explicitly requested.

The first repository-wide profile passed 29/30 checks and failed its read-only-health invariant because edits were made while it ran. No failing check was removed or relaxed. Final validation runs after committing a stable tree; its actual output is retained separately. Treat the early failure as an invalid final-head run, not a software correctness pass.

## Comparisons and missingness

Previous FAR is pinned to protected main `8f0e8e330d8f11a629447e23f3d00e6a5f81c1e6`. Noesis is pinned to `d38eb1fd956843b6eeeaeb582d3b4e1092255d94`, minimal local configuration, version 0.1.0. SymPy is 1.14.0. Exact dependency versions, source hashes and measurements are in each registration and summary. Local latency is a single controlled observation including package replay, not an independent speed benchmark; the debugger adds work and does not demonstrate a speed advantage.

The generic evidence-checking control is the prior source/quote/formula workflow. The argument/fallacy control is the existing unadjudicated critical-question generator, retained on the same claims. These are **internal controls**, not representative commercial-product substitutes. The fully configured frontier-model, QURI/RoastMyPost, Fact Engineering, Factiverse, Minerval, scite and relevant model-backed research arms were not executed; their availability failures are not scored as FAR wins. All missing arms remain in the machine summaries. External API charges for experiment subprocesses are zero; host/CI compute, research-tool use, human correction and analyst labor are not priced.

## Reproduction

Extract the desired portable ZIP into a new directory and verify every file against `artifact-manifest.json`. To replay run 002, use its registered runtime and the same repository contracts, then invoke `debugger_cli.py verify` on each directory under `debugger/`; `full_cli.py --verify` also verifies baseline packages. Run 001 needs its originating runtime because debugger result schemas acquired additive witnesses; a newer runtime intentionally rejects differing bytes rather than rewriting history. Run fresh experiments under new registrations and output directories. Never overwrite prior results.

The implementation and all available internal controls show useful bounded engineering. They establish no new general reasoning method, superiority to configured competitors, externally independent truth reliability, customer benefit or defensible moat. The strongest counterexample to a moat is straightforward reproduction using existing parsers, verifiers, provenance standards and event storage. Memory-derived commercial advantage requires measured held-out benefit and nontrivial reproduction costs, which remain unestablished.
