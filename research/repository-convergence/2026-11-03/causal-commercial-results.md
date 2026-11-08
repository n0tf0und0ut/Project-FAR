# Causal diagnosis, active comparators, retained evidence and commercial validation

Status: **Research / internal source audit and exposed-fixture software replay.** Protected-main source: `c7456b469f9dfe88b92d0fc7a211e5c9ed64de61`. No repository files, protected controls, frozen protocols, historical results, PRs or customer records were changed by this work.

## Observed result

FAR's current reusable contracts and retained artifacts already cover causal-model declarations, correction and supersession propagation, provenance-aware evidence reuse, deterministic comparisons and prospective external/human protocols. Another memory or causal engine is not justified by an uncovered representational invariant in this audit.

The executed controls do **not** establish general agent reliability, verified causal diagnosis of real agent failures, successful causal repairs, human augmentation, willingness to pay, or a compounding economic advantage. Existing negative results remain negative:

- The retained internal source-to-report campaign makes 37 factual predictions, all `ABSTAIN`.
- On the 46 existing supplied-formula controls, FAR returns 40 correct decisive outcomes and six declared atom-limit abstentions. Independent SymPy returns all 46 reference outcomes. This audit reproduced those counts through actual LangSmith local evaluation and Phoenix code scoring.
- Retained-history experiments already executed two fresh-versus-retained pairs. Both systems gain source availability, but neither establishes a factual-answer benefit, customer time saving, or human correction benefit.
- The existing generic table checker agrees with the 12 W4 preserved lossy/repaired classifications. Access to a deterministic answer is therefore an active comparator, not evidence of FAR-specific benefit.

## Executions in this assignment

### Cold restoration of prior campaign

Commands, run from the pinned repository:

```sh
python -m zipfile -e commercial/far-investigation-audit/evaluation/internal-001/run-003-portable.zip /workspace/scratch/e1c41a89d76e/causal-commercial/internal-replay
python tools/run_internal_investigation_evaluation.py verify /workspace/scratch/e1c41a89d76e/causal-commercial/internal-replay/run-003
```

Observed: 325 files verified, 28 FAR packages replayed, three controlled auditor records replayed. The verifier explicitly reports `external_independence: false` and scope `retained bytes and software replay only`.

Original run-003 ZIP SHA-256: `a317735c022174fc22b4b069c6750a9924a3fadfdf03ea3e54436b7f10b4a5b1`. Its original ten-failure run-001 and intermediate timing-incomplete run-002 remain preserved. They were not rerun as replacements or silently omitted from the history.

### Executable LangSmith/Phoenix/deterministic baseline

Installed only in an isolated scratch virtual environment: SymPy `1.14.0`, LangSmith `0.14.17`, `arize-phoenix-evals` `3.9.5`. No production dependency was added. `local-sdk-protocol.json` froze the existing input hashes, exact executable script, package versions, outcomes, limitations and network constraint before execution. Protocol SHA-256: `ea0e0102f73a3197cff2a9c0afb5d425055bbc04a27fdee14680c2c7377eb18d`.

```sh
causal-commercial/venv/bin/python causal-commercial/local_sdk_probe.py freeze
LANGSMITH_TRACING=false causal-commercial/venv/bin/python causal-commercial/local_sdk_probe.py run
```

LangSmith's real `evaluate(..., upload_results=False)` orchestrated both target functions on the same 46 formulas. Each target received premises, conclusion and case identity, with no reference label. The evaluator alone received reference labels. Phoenix's real code-evaluator API scored the resulting 92 rows. Socket connection calls were blocked; zero attempts were recorded. No model was called, and no hosted dashboard or model-based vendor diagnosis was evaluated.

| Target | Executions | Exact reference matches | Explicit abstentions | Target errors |
|---|---:|---:|---:|---:|
| FAR existing bounded entailment | 46 | 40 | 6 | 0 |
| Independent SymPy satisfiability | 46 | 46 | 0 | 0 |

Every per-case output and SDK score is retained in `langsmith-far.json`, `langsmith-sympy.json`, and `phoenix-scores.json`; aggregate `local-sdk-results.json` retains all denominator counts. The initial and only execution completed; its output, including vendor deprecation warnings, is preserved in `local-sdk-run-001.log`.

Interpretation: these are already exposed, project-authored finite logic controls. LangSmith/Phoenix provide executable evaluation plumbing with the supplied deterministic evaluator. Their model-assisted diagnosis effectiveness is not measured. Wrapping the same checker does not create an independent scientific oracle or estimate real-world accuracy. The six FAR abstentions are a coverage disadvantage at its declared bound, not false confident verdicts.

### Existing causal and generic-checker controls

`generic-causal-replay.json` retains exact hashes, all 12 generic-checker outputs and the causal native recomputation. No new causal theory or model was introduced.

The existing W4 models `X := U; Y := X` and `Y := U; X := Y`, with Boolean `U ~ Bernoulli(1/2)`, have the same observational joint distribution. Under `do(X=0)`, their required `P(Y=1)` values are `0` and `1/2`. The existing native recomputation reproduced those values. This is a concrete counterexample to inferring intervention response from those observational data alone. It is not causal identification of an actual agent failure.

The generic checker independently recomputed consistency for the exact supplied representation/required-behavior tables and agreed with all 12 preserved FAR classifications. It imports no FAR code. FAR's richer provenance, contract and interpretation fields were not secretly provided to the generic arm.

### Tests

Commands executed:

```sh
python -m unittest tests.test_project_memory tests.test_internal_investigation_evaluation tests.test_epistemic_learning tests.test_epistemic_assurance tests.test_efr_comparator_amendment
python -m unittest tests.test_research_corpus
python -m unittest tests.test_pca_w4_domain_contracts
```

Observed: 73, 34 and 21 tests passed respectively. These cover causal-reference and DAG controls, later-comparison retest scores, provenance/lifecycle checks, history-source read-once binding, baseline timing scope, stale/corrected/withdrawn evidence propagation, duplicate identities, source changes, EFR active-comparator preservation, and native causal intervention mutations. They test declared software semantics; they do not verify that an externally supplied causal explanation or reference label is true.

A broader optional investigation-component suite was first run in the base interpreter: 226 tests, ten dependency-import errors and one skip. The missing FastAPI dependency was environmental; the component documents its `requirements-dev.txt`. This failed execution remains in `investigation-tests.log`. After installing that exact documented requirements file into the isolated environment, the separate invocation below passed all 226 tests in 5.203 seconds. Its output is retained in `investigation-tests-provisioned.log`; the intentional `FAR_REPLAY_MISMATCH` diagnostic is an exercised rejection case, not a test failure.

```sh
causal-commercial/venv/bin/python -m pip install -r commercial/far-investigation-audit/requirements-dev.txt
causal-commercial/venv/bin/python -m unittest discover -s commercial/far-investigation-audit/tests -p 'test_*.py'
```

## Causal capability reconciliation

| Capability | Existing authority / implementation | What is actually established |
|---|---|---|
| Error categories and corrective rules | `far-epistemic/1.0`; `mechanization/far_mechanization/epistemic.py` | Typed error, rule, later retest and exact Brier-score comparison records |
| Causal declarations | `CausalModelRecord` in the same existing contract | Variable/intervention/counterfactual/assumption references and DAG acyclicity; identification status remains a submitted declaration |
| Competing causal models | W4 native Bayesian/causal contract and recomputation | Observational equality can hide different intervention outcomes in two stated finite models |
| Causal criticism of language | `commercial/far-investigation-audit/diagnostics.py` | Source-anchored critical questions, explicitly `QUESTION_NOT_ADJUDICATED`; lexical triggering is not causal diagnosis |
| Detection/localization in real agent traces | Agent/investigation work plus declared evidence contracts | Must be evaluated against independently prepared trace labels; no new measurement from this audit |
| Causal repair and regression prevention | Existing corrective/retest machinery | A later lower error score alone does not identify the corrective rule's causal effect; matched interventions and regression exposures are still required |

No numerical diagnosis accuracy, repair success, escaped-consequential-defect rate, causal false-positive/false-negative rate or human-review effort is manufactured from these conformance tests. Raw traces with no eligible exposure denominator cannot become a failure rate. Explanations and interventions need separate evidence.

## Current competitors: primary-source inspection and execution status

Access date: November 3, 2026. Source availability is not product effectiveness.

| System | Directly inspected current primary source | Executed here | Remaining comparison boundary |
|---|---|---|---|
| Microsoft AgentRx | [Microsoft release article](https://www.microsoft.com/en-us/research/blog/systematic-debugging-for-ai-agents-introducing-the-agentrx-framework/), [paper](https://arxiv.org/abs/2602.02475), [code](https://github.com/microsoft/AgentRx/tree/7a18c79708e7671be15124460f4f7296107c2a55) | Cloned and inspected exact source; **no full diagnosis run** | Current source uses authenticated Copilot CLI or Azure/TRAPI inference. `gh`, `copilot` and `az` are absent; no authorized configured model endpoint was supplied. Its first unrecoverable step differs from first consequential deviation. The 115 failed trajectories cannot estimate incidence without successful-run exposure. |
| LangSmith | [Official local evaluation documentation](https://docs.langchain.com/langsmith/local), [SDK source](https://github.com/langchain-ai/langsmith-sdk), [agent-evaluation product documentation](https://www.langchain.com/langsmith/evaluation) | Actual local SDK evaluation on all 92 deterministic target executions, results not uploaded | Hosted tracing, human annotation queues and LLM-assisted debugging were not executed. User-provided evaluators determine scores; platform output is not proof of causal truth. |
| Arize Phoenix | [Official repository](https://github.com/Arize-ai/phoenix), [product page](https://arize.com/phoenix) | Actual Phoenix evaluator library attached correctness/abstention scores to all 92 rows | Full server, trace-instrumented production app, PXI agent and model-assisted diagnosis were not executed. Self-hostability does not establish comparative accuracy or free total operation. |
| Generic deterministic constraint checker | Existing EFR generic-checker source | 12/12 W4 table classifications recomputed | Same table-preservation classification at this scope; no natural-language or causal-truth claim |
| SymPy | Pinned `1.14.0`, existing declared conversion | 46/46 formula cases executed with independently implemented satisfiability | Supplied formal semantics only; no raw-source interpretation or agent investigation |
| Human-assisted diagnosis | Existing human protocols | **No participants or human outcomes collected** | Needs eligible people, blinded labels, lawful authorized case artifacts and measured effort |

AgentRx version caution: the release blog describes a nine-category taxonomy; the current pinned repository README describes ten categories. This audit preserves that version difference rather than treating the two labels as one frozen taxonomy. The paper/blog's improvement percentages are published findings under their experimental settings; they were not reproduced here and cannot be transferred to FAR.

## Human augmentation and commercial evidence

Existing preparation is substantial and should be reused:

- `commercial/far-demo/VALIDATION_PROTOCOL.md` defines four buyer workflows, segmentation and a hierarchy from payments to generic praise. Its structured web form is low-level feedback, not willingness-to-pay evidence.
- `commercial/far-investigation-audit/FIELD_VALIDATION.md` separates formal correctness, semantic fidelity and factual adequacy, and requires prospectively sealed predictions plus independent references.
- The already merged #518 60-case, four-condition benchmark remains **prepared**; its corpus/reference/prompt/environment/evaluator freeze inputs cannot be filled with invented identities or project-authored independent adjudication.
- EFR comparator amendment v2.0 requires the existing FAR/checker/standard arms. `EFR-HD2` needs 60 external reviewers and 2,160 ratings; `EFR-U2` needs three external sites with 60 consecutive investigations each; `EFR-C2` measures time, direct cost and workload. These are not replaceable by another internal synthetic test.

The specific candidate workflow with the clearest current engineering fit is **post-incident reconstruction or release assurance for a team deploying tool-using AI agents**. This is an inference from FAR's available trace/provenance/verification behavior and the independently documented debugging problem, not evidence of a paying customer.

| Candidate buyer / workflow | Existing problem evidence and substitutes | FAR contribution to test | Observed frequency/cost, authority, budget, payment | Falsifier |
|---|---|---|---|---|
| AI application engineering manager: unexplained tool action | Actual failure trajectories exist in AgentRx's research corpus; AgentRx, LangSmith and Phoenix already offer diagnosis/trace/evaluation workflows | Auditable exact evidence, authorization checks, correction lineage and explicit uncertainty | **Not measured for any FAR customer** | Matched existing tooling reaches the same verified diagnosis/repair with lower total investigation burden |
| Release owner: regression before agent update | FAR already has executable release/decision-integrity interfaces; generic CI and evaluation products are substitutes | Trace-to-requirement discrepancy plus reproducible assurance package | **No observed buyer incident frequency, avoided loss or budget commitment** | FAR misses consequential regressions, adds unsupported blocks, or costs more review time than the errors it prevents |
| Independent assessor / procurement reviewer | Existing validation form names this segment; vendor governance and observability tools overlap | Inspectable exact-source limits and exportable audit evidence | **No recorded purchasing authority or budget evidence located in the inspected artifacts** | Buyers accept existing evidence packages and do not pay for FAR's incremental assurance |
| Human investigator / decision augmentation | Existing bounded cognitive/semantic interfaces and preregistered external designs | Fewer unsupported decisions, faster corrections, calibrated reliance and delayed unassisted transfer | **No independently rated A/B/C outcomes, retained-learning results or purchases collected** | Report detail rises without decision accuracy/coverage gains, or reliance and workload worsen |

An economically defensible price requires measured incremental expected avoided loss or saved labor to exceed price plus compute, review and integration cost. None of those buyer-specific quantities is supplied by a passing test suite. No interviews, invitations, contact messages, purchases, testimonials or customer outcomes were fabricated or sent. No actual user was available in the authorized inputs to perform a genuine blinded participant session.

## Compounding evidence asset

The existing corpus already implements content-addressed sources, source-dependence lineage, current availability, governed atomic findings, transitive correction/supersession, stale-dependency invalidation and bounded generated synthesis. Existing source reuse validates exact package bytes before import. Those mechanisms should be extended only for a demonstrated missing invariant, not replaced with another memory subsystem.

What was tested: source mutation and withdrawal fail closed; correction-of-correction retires old history rather than resurrecting it; aliases cannot multiply evidence; unknown/missing dependencies block unconditional conclusions. The 34 corpus tests passed. These are information-integrity properties.

What remains unestablished: improved repeated-discovery cost, time to known mechanisms, intervention selection, decision accuracy, calibration and economic benefit from retained evidence on independent cases. The two historical fresh/retained pairs show source availability without a decisive-answer gain. Reuse rights are not established merely by retaining a URL or bytes; no proprietary-data or switching-cost advantage is inferred.

## Scientific disposition

- **Established at declared software scope:** byte-bound restoration/replay; local SDK evaluation interoperability; formula and table-checker outcomes; existing correction-history invalidation semantics; finite stipulated causal counterexample.
- **Bounded observations:** FAR 40 decisive correct formula outcomes plus six abstentions; generic checker agrees on 12 supplied W4 tables; historical retained evidence increases source availability without demonstrated factual benefit.
- **Supported inference:** FAR's current stronger opportunity is audit-evidence discipline within an existing debugging/release workflow. Existing competitors already supply much of the tracing and evaluation infrastructure.
- **Unresolved:** agent failure diagnosis/repair advantage, human decision benefit, durable learning, real buyer economics, willingness to pay, external replication and compounding asset value.
- **Unsupported claim rejected:** passing the pipeline, storing more history or producing longer reports establishes general reliability, causal understanding or commercial superiority.

No result was promoted into Accepted theory or EFR status. No PR was merged, closed, discarded or put on auto-merge by this worker.
