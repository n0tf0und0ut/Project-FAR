# FAR Epistemic Debugger 1.0

Status: **Research application implementation. No Accepted theory, scientific assurance, production release or commercial-superiority promotion.**

This is an additive application of the existing investigation engine. It closes a demonstrated software gap: formal proof success can coexist with a changed source meaning. It does not solve arbitrary natural-language understanding or establish external-world truth.

## Run the complete workflow

From the repository root, using Python 3.11 or later:

```sh
python commercial/far-investigation-audit/debugger_cli.py investigate \
  commercial/far-investigation-audit/examples/epistemic_debugger.json \
  --output /tmp/far-debugger-case --memory /tmp/far-memory.sqlite
python commercial/far-investigation-audit/debugger_cli.py verify /tmp/far-debugger-case
python commercial/far-investigation-audit/debugger_cli.py replay --memory /tmp/far-memory.sqlite
```

The example intentionally assigns one atom to “some reviewed deployments” and “all reviewed deployments.” Its propositional proof passes. Its semantic acceptance fails, with a checked population of two containing one safe deployment. A collision contract is generated and checked by the existing `far-ir/2.0` verifier.

`full_cli.py REQUEST --debugger --output NEW_DIRECTORY` enables the same capability. Existing supplied proposals and legacy workflows remain unchanged unless the additive debugger contract is explicitly enabled. No historical audit package is rewritten. Replay old packages with their recorded runtime; the earlier campaign preserves its original runtime and outputs.

The existing local UI runs with `python -m uvicorn webapp:app --app-dir commercial/far-investigation-audit --host 127.0.0.1 --port 8000` after installing `requirements-dev.txt`. Pasted sources enable the debugger and show the same human report. JSON package downloads contain the graph and witnesses. Network acquisition remains explicit server opt-in. There is no public hosting or authentication claim.

## Resume and correct

Write a JSON **list** of additional evidence-source configurations to `evidence.json`, for example `[{"kind":"text","text":"One reviewed deployment failed."}]`. A replacement proposal may explicitly link that new source (`ev1`, or the next available evidence ID) to claims and revise interpretations:

```sh
python commercial/far-investigation-audit/debugger_cli.py resume /tmp/far-debugger-case \
  --evidence evidence.json --proposal revised-proposal.json \
  --output /tmp/far-debugger-followup --memory /tmp/far-memory.sqlite
python commercial/far-investigation-audit/debugger_cli.py source-state source:SNAPSHOT_SHA256 \
  --state retract --reason 'Source corrected by its custodian' \
  --valid-time 2026-10-27T12:00:00Z --memory /tmp/far-memory.sqlite
python commercial/far-investigation-audit/debugger_cli.py replay --memory /tmp/far-memory.sqlite --through 1
```

`SNAPSHOT_SHA256` is the original exact source-text hash in `input.json`, not a URL or reviewer claim. The source-state command records a supplied correction; it does not authenticate the custodian. Use `--state restore` with an explicit reason for a reversible later status. A source replacement is a new investigation with new source bytes/proposal, plus retraction of the affected prior snapshot. Existing sources are retained by resume and newly known at the follow-up capture time. Their original acquisition and time remain in the prior immutable package, linked by `resumes_input_sha256`. An unchanged inherited proposal does **not** automatically adjudicate new evidence.

Each package contains machine input, formal audit, proposed interpretation, raw extraction records, critical questions, `debugger.json`, a human report and file commitments. The debugger records deterministic source-file commitments, Python version and a runtime fingerprint so different construction revisions cannot masquerade as the same implementation. This is source/version consistency, not a complete environment or authenticated execution seal. Replay requires the originating runtime; memory refuses differing historical outputs rather than silently migrating them. Package verification recomputes every debugger result and human report. Changing a verdict or deleting its debugger file fails even after unsigned manifest rehashing. Hashes do not authenticate a publisher, prove source truth, or prevent wholesale replacement by an attacker controlling every input.

## Architecture and actual baseline gaps

| Capability | Protected-main baseline | Additive implementation | Remaining boundary |
| --- | --- | --- | --- |
| Source intake | Text, HTML, SRT/VTT, guarded HTTPS, optional captions/PDF/transcription | Reuses `workflow.py`, acquisition and hostile-input bounds | Optional dependencies/permissions required; no visual interpretation, OCR or guaranteed remote availability |
| Meaning | Exact quote anchors, supplied atom meanings, interpretation cards; semantic mapping unverified | `semantic.py`: complete controlled-grammar parsing, typed AST, reconstruction, contrast witnesses, collision detection | Open-domain interpretation, anaphora, pragmatics, implicit premises and broad paraphrases abstain |
| Inference | Exhaustive bounded propositional audit and separate checker | Same engine; additional acceptance requires grammar fidelity of every premise and conclusion | Formal validity never proves premise truth or natural-language intent |
| Counterfactuals | Countermodels for invalid supplied formulas | Exhaustive cost-aware withdrawals and explicitly supplied assumption additions, then rechecking | At most eight edits, 12 atoms and a conservative work cap; no causal-intervention or universal minimality claim |
| Memory | Portable packages and optional prior-source import; governed research corpus separately exists | `memory.py`: transactional content-addressed events, source/semantic indexing, cross-investigation records, dependency invalidation, reversible state and replay | No automatic source-trust promotion, learned truth, automatic research-corpus promotion or demonstrated accuracy/speed improvement |
| Cognition | Unadjudicated argument-scheme questions | `cognitive.py`: paired-trace framing, user-position/anchor tracking, authority sensitivity, declared evidence omission, answer preservation and unsupported certainty | These are observable traces; motives, cognitive mechanisms, consciousness and disorders remain UNKNOWN |
| Philosophy and learning | Existing epistemic/ELENCHUS schemas, scoring, revision and causal-model records | Composes their actual validator, preserves framework labels and normative/causal distinctions | No AGM completeness, new Bayesian update rule, causal identification, resolved metaphysics or moral proof |
| Assurance | Accepted lineage, time, abstention and audit-process contracts | Existing lineage and audit-assurance validators; explicit unknown checks; source-state valid/known times | A passing schema is not independent evidence or authentication |

The call graph is `debugger_cli / full_cli / webapp → workflow → existing audit + debugger → existing package writer/verifier`; memory imports **verified packages only**. There is one propositional inference implementation. The design does not alter `PROJECT-FAR-CORE-THEORY-1.1`, any frozen source, `far-ir/2.1` cost semantics, the research corpus's governed promotion rules, or EFR.

## Semantic contract

`far-semantic/1.0` admits whole, bounded English strings in explicitly recognized forms: singular/copular predication; some/all/every/no populations; exact, at-least, at-most, more-than and less-than counts (0–99 digits, zero–twenty word table); explicit negation; listed modal copulas; date-qualified predicates; causal versus correlational relations; normative “should be”; and explicit if/then structure. Quantified subjects are bounded lexical terms and predicates are single opaque terms. The unquantified singular lane admits one identifier, optionally prefixed by “the”; unquantified plural descriptions and unsupported count words abstain. Dates must parse. No entity, synonym, taxonomy or pronoun resolution is inferred.

`SUPPORTED_IN_GRAMMAR` means equality of the source and reconstructed AST under the stated grammar, fixed reference and nonempty-population assumptions. It is not independent semantic certification. `CONTRADICTED` means the proposed mapping loses a checked distinction, not that the source's factual proposition is false. `ABSTAIN` includes unsupported syntax and unresolved equivalences. In particular, modal outer negation is not moved into a modal predicate, and different count ASTs without a distinguishing witness are not automatically called distortions.

Count/quantifier/polarity contrasts can emit a rechecked finite population witness. Temporal, modal, causal, conditional and normative differences emit typed alternative-interpretation contrasts; they are not causal interventions or automatically asserted formal countermodels. Collisions are local to a fixed supplied atom dictionary and observation contract, with a checked two-case `far-ir/2.0` record. They establish no general representation theorem or novelty.

`far-epistemic-debugger/1.0` is an application envelope defined by [debugger-1.0.schema.json](debugger-1.0.schema.json), runtime type/reference checks and deterministic recomputation. `far-debugger-trace-observations/1.0` records byte-level trace observations, with psychological cause UNKNOWN. It does not define the separate `FAR-COG/0.1` contract introduced by concurrent PR #596. An explicitly supplied `debugger_options.cognitive_audit` composes that existing cognitive validator and auditor when the dependency is installed; absence fails explicitly rather than substituting this lower-level trace observer. That optional path is unavailable on the pinned baseline and is not counted as an executed canonical cognitive capability. All epistemic documents retain `far-epistemic/1.0` and its canonical `FAR-ELENCHUS-1.0` composition. No legacy schema is silently migrated. No probabilities, confidence scores or FAR loss/cost coordinates are repurposed.

## Counterfactual and dependency contract

Each inference links exact assertions, interpretation nodes, evidence links, a classical warrant, interpretation defeaters, critical questions and downstream inference dependencies. Assumption edits are relative to the supplied formulas. The target is a switch from conditional entailment to nonentailment, or from a nonentailing/inconsistent problem to consistent entailment. Positive integer edit costs are explicit; all minimum-cost ties are retained. Exactness is only over this operation universe. Larger problems abstain rather than receiving an unqualified optimum.

An added bridge premise is a hypothetical assumption, not discovered evidence. Critical questions identify potential discriminating observations and causal/normative obligations; they do not prove that these obligations are unmet. Causal interventions require an independently specified causal model and evidence. Validating an existing causal-model record checks conformance, not identifiability. Circular dependencies are reported structurally, with independent evidence as a possible explanation for why the conclusion could still be justified.

## Persistent history contract

`far-investigation-memory/1.0` stores immutable JSON payloads in a SQLite event chain. Import recomputes the formal audit, separate formal checker, debugger and proposal commitment. It records no inferred source authenticity. Exact source bytes deduplicate, while every investigation's source metadata and lineage occurrence remain retained. Semantic indexing uses the checked AST identity; it is not a complete paraphrase-equivalence algorithm. Conclusions remain scoped to their investigation and are never counted as independent corroboration of themselves.

Retraction invalidates the transitive downstream projection, including dependent later readings. Unrelated graph nodes retain their states. Restoration recomputes the projection without deleting prior invalidation history. `replay(through=N, valid_at=UTC)` separates recorded history from state applicability; future-effective changes do not affect the present projection. The CLI exposes recorded-sequence replay. Arbitrary database SQL access is outside the append-only API boundary: an attacker replacing the entire DB can create a different internally consistent chain. There is no independently sealed external history.

Predictions, calibration, error histories, causal hypotheses and ELENCHUS records are retained through the validated existing epistemic document, rather than by a duplicate learning architecture. Unknowns, failed mappings, counterexamples and corrections remain visible. The mechanism demonstrates correction tracking and reuse availability; it has not demonstrated epistemic learning or a compounding moat.

## Prior art and hostile conclusion

The [24-record prior-art inventory](evaluation/debugger-001/prior-art-v1.json) distinguishes original papers, implemented source, product documentation, unresolved leads, licenses and missing reproductions. Pinned source inspections cover Noesis, Minerval and RoastMyPost. No competitor source is incorporated. Read source licenses before incorporating future implementations; a public repository is not automatically reusable code. Patent publication screening here is neither an exhaustive search nor a freedom-to-operate determination.

| Layer | Strong counterexample to novelty | Disposition |
| --- | --- | --- |
| Natural language plus verifier | AWS ARc redundant formalization/semantic checks; Monty assertion conformance | Established overlap; no new general technique |
| Counterfactual diagnosis | Reiter model diagnosis and de Kleer assumption-based truth maintenance | Brute-force bounded integration, not a new algorithm |
| Persistent claims/revisions | Minerval, Noesis, Graphiti, PROV-O | Persistent graphs and provenance are commoditized architecture |
| Evidence-first product | Fact Engineering, Factiverse, scite | Overlapping customer value already documented; mature performance not inferred from marketing |
| Argument criticism | QURI/RoastMyPost, ASPARTIX | Schemes, fallacy criticism and formal argumentation preexist FAR |
| Belief revision and causality | AGM/Isabelle formalization, DoWhy | FAR composes bounded existing records, not new epistemology or identification |
| Behavioral auditing | Operational sycophancy and cognitive-bias benchmarks | Paired input/output checks are established methods |

The observed integration improvement is narrowly against the previous FAR workflow: meaning changes can block acceptance despite proof success, and corrections can invalidate stored dependencies. A well-funded team can reproduce this implementation with ordinary parsers, SAT/SMT solvers, event storage and existing LLMs. No defensible novelty, customer advantage, independent factual reliability or moat is established. A correction corpus becomes an asset only if it measurably improves held-out accuracy, human correction burden or investigation cost under matched evidence and time cutoffs. Storing more records alone is no such evidence.

## Reproducible validation

See the [internal campaign record](evaluation/debugger-001/README.md), frozen cases, registrations, preserved failures, complete missingness and portable audit packages. The protocol was frozen before implementation; the same developer authored and saw the cases. Results are conformance evidence, not independent confirmation.

```sh
python -m pip install -r commercial/far-investigation-audit/requirements-dev.txt
python -m unittest discover -s commercial/far-investigation-audit/tests -p 'test_*.py' -v
python tools/run_debugger_evaluation.py freeze --output /tmp/debugger-registration.json \
  --baseline /path/to/clean/pinned/FAR --noesis /path/to/noesis
python tools/run_debugger_evaluation.py run --registration /tmp/debugger-registration.json \
  --baseline /path/to/clean/pinned/FAR --noesis /path/to/noesis --output /tmp/new-debugger-run
```

Actual registered comparator arms are previous FAR and minimal model-free Noesis, plus design-diverse SymPy logic checks and project-controlled generic argument/evidence controls. Noesis's explicit refusal without classifiers is not evidence that its configured capabilities are inferior. Frontier-model, QURI, Fact Engineering, Factiverse, scite, Minerval and other unconfigured arms stay missing. The test campaign makes zero external model calls; host compute, analyst labor, human correction and operating costs beyond external API charges are unmeasured. No external scientific review, recruitment, EFR execution or frozen confirmatory experiment is performed.

The locked public-source shift test exposes narrow coverage (34 of 878 extracted statements in the reviewed runtime). The next highest-value evidence, when separately authorized, is a matched blinded recurring-investigation comparison with and without retained correction history. Measure adverse carryover, factual/semantic errors, human repair effort and total cost. A memory benefit must survive those tests before it can support commercial defensibility.
