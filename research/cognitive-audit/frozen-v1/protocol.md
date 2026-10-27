# FAR-COG-INTERNAL-001 — frozen internal contract

Status: Research. This is an explicitly authorized internal exploratory campaign,
not EFR, #518, independent replication, a human study or commercial comparison.

Freeze the spec, schema, candidate rules, corpus and references in a Git commit
before executing predictions. Record that source commit and byte hashes in the
run artifact. Do not overwrite frozen inputs to improve scores. A source defect
requires a named successor version and preservation of prior outcomes. Code
corrections after this freeze are exposed follow-ups, not a fresh unseen test.

The 71 references were authored by the same project-controlled executor who
implemented the rules and saw the implementation. Cases directly stipulate the
semantic/control coding. They are regression/conformance evidence with severe
selection and implementation-exposure bias. Counts are not estimates of external
accuracy. Some ambiguous labels are intentionally UNKNOWN, not fabricated binary
ground truth. Synthetic traces never claim execution by a real language model.

Run three deterministic arms on identical input bundles:

1. FAR-COG/0.1 submitted-coding verifier.
2. Generic lexical argument/fallacy annotator: named phrases for intent and
   argument from ignorance, otherwise UNKNOWN. A small runnable internal control.
3. Structured evidence checker: checks coded premise support, citation support
   and declared root independence; lacks cognitive controls and ontology.

Publish every prediction/error. Report TP/FP/FN/TN only for frozen binary labels;
separate abstentions rather than count them as negative predictions. Also report
binary coverage, unresolved-case disposition accuracy, status counts and metrics
by rule. Compare wording stability on the declared stance paraphrase pair.
Diagnostic calibration is unavailable (no diagnostic probabilities); existing
epistemic selected-outcome Brier scores retain their original restricted scope.

Independent logic checks where feasible: enumerate finite inconsistency/intent
countermodels and recompute the binary snapshot posterior using exact Fraction
arithmetic in a separate checker without importing the candidate decision rule.
All other reference labels remain project coding, not an independent oracle.

Acceptance for this internal implementation: deterministic replay, no invalid
inputs accepted by hostile tests, complete scoped output fields, no forbidden
actor/ontology certainty, all discrepancies retained and explained. No minimum
accuracy gate can establish external effectiveness. Report disadvantages and
null comparisons as observed. Real automatic extraction, independent labels,
human effects, vendor comparisons and external effectiveness remain OPEN.
