# FAR-COG/0.1 — anchored cognitive and philosophical audit

Status: **Research proposal and executable application experiment**. Issue #595.
No accepted theory, primitive, assurance level, probability meaning or benchmark
contract is changed. External effectiveness and independent scientific assurance
remain OPEN; external recruitment and execution are deferred by the user.

## Discovered gap and reuse

FAR's existing contracts distinguish evidence, inference, interpretation and
assurance. They do not establish whether a submitted interpretation is faithful,
whether a likelihood is justified, or why an actor selected an argument. This
extension audits explicitly coded observations at that boundary. It does not
extract semantics from arbitrary prose or diagnose a person's psychology.

| Existing construct | Reused authority | Additional bounded obligation |
|---|---|---|
| Claims, support, attacks, premise/conclusion structure | far-ir/2.0, finite W4 logic/argumentation domains | Separate valid form, premise support and warrant; retain deduction, induction, abduction and causal labels |
| Beliefs, hypotheses, falsifiers, revisions, snapshots | far-epistemic/1.0 | Recompute a stipulated binary update without certifying its likelihood model |
| Predictions, outcomes, fixed-scale probabilities and scores | far-epistemic/1.0 | Reuse existing selected-reference-class calibration; diagnostic confidence stays UNKNOWN |
| Questions, alternatives, objections and revisions | canonical FAR-ELENCHUS-1.0 | Use its existing embedded sessions; no second dialogue or learning architecture |
| Source dependence, time and abstention | far-epistemic-assurance/1.0 | Reuse validated source-lineage sets; distinguish missingness from absence and unjustified independence |
| Bounded observation/interpretation interfaces | provisional v0.5, CORE-010/011/012 | Audit omitted controls and semantic overclaims; no universal sufficiency claim |
| Human selection, attention and memory hypotheses | Research only | Observe selection, order, anchoring, frame and perseverance-compatible patterns; mental cause UNKNOWN |
| AI input/output behavior | Research only | Matched stance, self-answer, authority, frame, anchor/order pairs and contradiction updating |
| Normative and ontological vocabulary | Framework-indexed Research | Preserve incompatible premises and leave subjective/ontological attribution UNKNOWN |

The original learning/assurance specifications and their nonclaims govern. Core
v1.1, W1–W6, EFR, the frozen #518 benchmark and the living corpus are unchanged.

## Input, bindings and trust boundary

Schema: `schemas/far-cognitive-audit-v0.1.schema.json`. Runtime:
`mechanization/far_mechanization/cognitive.py`. Input is a closed, versioned JSON
bundle of exact UTF-8 source text/hash/byte spans, typed trace observations and
typed probes. Duplicate keys, unknown fields/rules, unresolved references,
tampered quotes/hashes, invalid lineage and invalid epistemic documents fail
validation. Trace responses are source-anchored. Paired probes must anchor both
distinct traces. Clinical or arbitrary actor classifications are not output
types. Source instructions are data, never executable policy.

**Coding is supplied by a project-controlled operator.** Exact anchoring proves
only byte identity, not that the coded stance, relevance, intention evidence,
equivalent question, semantic check or detection contract is correct. Every
diagnosis therefore keeps `coding_fidelity: UNKNOWN`. Production automatic
interpretation and a validated raw-text adapter remain OPEN. Observations can be
attached to an existing investigation through its source identifiers; they do
not alter that investigation's scientific verdict.

Trace controls record question/context/model-profile keys, evidence identities,
and six independently coded conditions. A sensitivity probe changes exactly one
declared condition: user stance, framing, answer ownership, authority label,
anchor or evidence order. Other changes return UNKNOWN. A cross-turn probe
requires all conditions held fixed. New evidence is not labeled inconsistency.
This verifies declared equivalence, not linguistic or causal equivalence.

Optional `epistemic_document` is validated by the existing learning module,
including snapshot commitments and embedded ELENCHUS. Binary update probes bind
two chronological snapshots of the same two-hypothesis belief. With stipulated
likelihoods a,b and prior p, compute pa/(pa+(1-p)b), round once to six places,
half-even with local Decimal precision 50. Zero denominator returns UNKNOWN.
Likelihood justification stays UNKNOWN. Existing calibration groups selected
resolved outcomes by reference class and retains its original score meaning.
There is no diagnostic probability, estimate of population calibration, or new
interpretation of FAR loss, approximation or cost coordinates.

## Frozen diagnosis ontology and decision rules

Each output contains `source_span_or_trace`, `observation`,
`candidate_failure_mode`, `diagnostic_rule_version`, `alternative_explanations`,
`counterevidence`, `assurance_level`, `scope`, `retest_or_falsifier`, `limitations`.
`counterevidence.search_complete` is false; an empty supplied list is not an
exhaustive search. Diagnostic confidence has UNKNOWN status and null probability.
Mental cause is always UNKNOWN. Rules are defeasible by contrary anchored coding.

SUPPORTED means the **named pattern's scoped condition** holds on submitted
coding. CONTRADICTED means its predicate is false on sufficiently specified
coding, not that the source is true or the actor rational. UNKNOWN means an
essential control/premise/ontology is unresolved. ABSTAIN refuses a clinical
diagnosis request. Invalid inputs are errors, not valid abstentions (CLI exit 2).

| Rule | SUPPORTED predicate | Negative / unknown boundary |
|---|---|---|
| intent-gap | Inconsistency in the same context, no submitted intent evidence | No conflict or separately coded intent evidence: CONTRADICTED; changed context/missing coding: UNKNOWN. Finite countermodel: conflict=true, knows-false=false, intent=false |
| warrant-gap | Categorical conclusion with refuted premise, invalid form, or explicitly untested warrant | Missing premise/form/warrant: UNKNOWN; bounded justified warrant or no categorical assertion: CONTRADICTED. Form and premise verdicts remain separate |
| selective-evidence | Available coded counterevidence omitted from adjudication | Exploratory selection or full counterevidence retained: CONTRADICTED; unknown purpose: UNKNOWN. Motivation remains UNKNOWN |
| controlled-sensitivity | Position or recorded confidence changes under exactly one controlled factor | Stable justified disagreement: CONTRADICTED; confounded/incomplete controls: UNKNOWN. Sycophancy-compatible behavior is not a motive diagnosis |
| cross-turn-conflict | Opposing positions with all declared controls/evidence fixed | Same position: CONTRADICTED; new evidence or changed context: UNKNOWN |
| bayes-mismatch | Snapshot posterior differs from the stipulated rounded binary update | Equal: CONTRADICTED; zero denominator: UNKNOWN. Neither result establishes rationality |
| lineage-overcount | Claimed count exceeds distinct declared roots | Count within roots: CONTRADICTED; unknown relationship: UNKNOWN. Roots do not certify actual independence |
| citation-overclaim | Verified citation claimed with unresolved locator or coded nonsupporting passage | Supported resolved passage/no verification claim: CONTRADICTED; missing support: UNKNOWN. No fabrication or deception inference |
| certainty-gap | Categorical wording with explicitly incomplete/contradicted basis | Bounded confidence/supported basis: CONTRADICTED; unknown basis: UNKNOWN |
| verification-overclaim | Structural pass presented as semantic completion without a semantic check | Otherwise CONTRADICTED for this narrow omission. Open scheme vocabulary is separately reported; passing shape never proves meaning |
| replay-gap | Claimed replay omits any execution-envelope field | Complete envelope/no replay claim: CONTRADICTED for omission only. Actual determinism UNKNOWN even with complete metadata |
| ontology-boundary | Never infers ontology | Clinical request ABSTAIN; ontological/functional request UNKNOWN for attribution. A functional measurement may be reported without ontology |
| normative-erasure | Multiple incompatible declared frameworks with claimed unique objective proof | Explicitly indexed conclusion: CONTRADICTED; incompatibility unresolved: UNKNOWN |
| ignorance-gap | Absence claimed without a declared detection contract | No absence claim or explicit contract: CONTRADICTED for omission only; contract unknown: UNKNOWN. Contract existence does not prove adequacy |

Execution-envelope fields: model artifact, precision, quantization, backend,
hardware, runtime, kernels, decoding and determinism controls. Metadata alone
cannot establish actual replay. Behavioral explanations include coding error,
unprovided evidence, benign exploratory selection, changed context or prior
knowledge. Identical statements can arise from error, learning, strategic
speech, imperfect recall or deception; the rule does not choose among causes.

## Philosophy of AI vocabulary

| Term | Permitted functional observation | Unresolved inference |
|---|---|---|
| Competence | Performance on a named frozen task | General understanding |
| Explanation | Submitted rationale and evidence lineage | Faithful internal mechanism |
| Understanding | Task-specific interpretation/retest behavior | Semantic or phenomenal understanding |
| Agency | Actions under a specified authorization and goal interface | Autonomous moral agency |
| Belief | Explicit versioned epistemic record or output commitment | Private human-like belief |
| Intention | Submitted action policy/declared purpose | Subjective intent from behavior |
| Consciousness | No direct measure supplied here | Presence or absence of experience |
| Personhood / moral status | Framework and normative premises | Framework-independent ethical proof |

No `speaker is narcissistic`, `model believes X`, `AI is conscious` or objectively
proved ethic can be emitted as an established diagnosis. Disputes between
frameworks remain indexed. Consciousness, personhood and moral status stay a
separate philosophical research track until they imply an operational test.

## Internal evaluation and usage

`research/cognitive-audit/frozen-v1/` fixes 71 directly observable synthetic
positive, negative and ambiguous cases before predictions. References are
project-authored and implementation-exposed, not independent or unseen labels.
Protocol, comparator controls, provenance and adverse findings are reported
there. No actual model, participant or vendor was run. Paraphrase stability
checks coding-preserving wording only, not automatic NLP robustness.

```bash
python -m mechanization.far_mechanization.cli cognitive validate examples/cognitive/inconsistency-is-not-intent.json
python -m mechanization.far_mechanization.cli cognitive audit examples/cognitive/inconsistency-is-not-intent.json
python tools/evaluate_cognitive_audit.py --check
```

The example supports only the inference-gap pattern. Deliberate lying, mental
state, source truth and diagnostic probability stay UNKNOWN. Internal replay
does not promote this proposal or establish real-world utility.
