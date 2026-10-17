# FAR: open-world truth boundary and independent field-validation protocol

**Status:** Research-only protocol and executable local scoring instrument. This is not an Accepted FAR theory change, preregistered confirmatory benchmark, independent study, or evidence of general factual accuracy. Exact implementations and independently collected labels must be frozen *before* a prospective confirmatory run. The independent FAR-RQ-005 / PR #518 60-case frozen benchmark and EFR remain distinct and unchanged.

## I. The universal guarantee is impossible under incomplete observation

Let `W` be possible worlds; `O: W -> X` be all observations available to a system; `T: W -> {true,false}` be the target factual proposition; and `A: X -> {true,false,unknown}` be the system's decision. Suppose there exist two worlds `w0` and `w1` such that:

```
O(w0) = O(w1),  but T(w0) != T(w1).
```

Since the two observations are identical, a deterministic `A` returns the same answer in both worlds. If that answer is Boolean, it is false in at least one world. `unknown` may avoid an ungrounded truth assertion, but then `A` does not determine the factual truth in all worlds. A randomized system cannot improve the worst-case success probability above 1/2 when forced to choose one Boolean output and the two indistinguishable worlds are equally plausible. This is an observation-indistinguishability impossibility argument; no appeal to consensus or model performance is needed.

The identical form applies to semantic intention: two contexts can have the same recorded utterance but different privately intended propositions. If the differentiating context is not observable, no algorithm can *guarantee* the speaker's unique intended interpretation. Valid tests instead examine whether an interpretation is supported, distinguish plausible alternatives, expose hidden assumptions, and abstain when necessary.

**Consequences:** A claim that FAR determines truth or the uniquely correct meaning of *arbitrary* real-world language is unprovable without restricting admissible worlds, observations, source trust, semantic contracts, or an external truth oracle. No finite test set proves an unrestricted universal. High performance on a particular external dataset is not a proof of universal truth finding.

## II. Three different evidence targets, never conflated

1. **Formal correctness:** For exact finite propositional formulas under the declared interpretation, FAR's computed entailment/countermodel can be mechanically checked. This is a conditional mathematical result, not a source-to-semantics guarantee.
2. **Semantic fidelity:** An *independent, blinded* adjudicator assesses whether each atom/claim/argument matches the source's materially relevant meaning, including quantified scope, time, referents, speaker intent where observable, presupposition, modality, language, tone, and competing readings. Merely quoting a source is not semantic verification.
3. **Empirical factual adequacy:** An *independent, blinded* adjudicator assesses whether authenticated, historically admissible, sufficiently independent and sufficiently complete evidence justifies the precise proposition. Correctly recomputing statistics from a data file does not prove the measurement is authentic, representative, causal, or relevant.

A report must not gain a factual `SUPPORTED`/`REFUTED` status solely because the current verifier reports `CONDITIONAL_FORMAL_SUPPORT_RECORDED`, because an LLM asserted a relation, or because a citation points to an exact byte span. The `field_validation.py` adapter therefore emits `ABSTAIN` for all existing FAR audit claims. This intentionally records the **current empirical-truth capability gap** rather than hiding it behind a favorable metric.

## III. Required independently adjudicated validation

**Prospective protocol:** Before viewing test labels, freeze the product's exact head, model/provider/version, retrieval/search engines, historical source cutoff, prompting byte strings, tool permissions, cost/latency ceilings, data selection rules, registered reviewers, condition definitions, and exclusions. Store exact input/output bytes with content hashes. The scoring code and its benchmarks must be frozen and independently reviewed before confirmatory use.

**Sampling:** Independently select a mixture of representative and adversarial real-world statements from multiple domains and media (speech, interviews/debates, journalism, social video, scientific claims, structured numbers). Include quote context and source links or timecodes. Stratify at minimum by: ambiguity/implicit content; genuine contradiction; missing or conflicting evidence; numerical/quantified statements; causality/correlation; translation; novel events; adversarial quote truncation; pre/post-claim evidence timing; source copying/syndication; and source-authenticity doubt. Define the target deployment distribution, base rates and exclusions before scoring. Report *per stratum* and avoid letting easy examples bury an important failure class.

**Reference construction:** Use independent reviewers who never see FAR verdicts or baselines before creating reference interpretations, evidence requirements, and the time cutoff. More than one interpretation may be acceptable; preserve genuine unresolved disagreements. Distinguish observed utterance, intended interpretation (when knowable), evidence-to-claim judgment, and inference judgment. A reviewer label is an observation, not infallible ground truth. Use separately recorded reviewer identifiers, disagreement rates, adjudication rationales, exact evidence versions, and prospective source provenance. Do not mistake the field `reviewer_count` or a signature for a technically enforced independence barrier.

**Controls:** Include high-quality researched-answer, generic deep-research, and structured fact-check workflows with comparable source cutoff, provider information, tool budget, and human assistance. Existing FAR PR #518 freezes such a comparative design; do not amend it or reuse its labels/outcomes as an unregistered new experiment. Evaluate how and whether the full FAR product adds **reduced unsupported inference**, **improved factual/evidence coverage**, and **fewer unjustified confident answers** against these baselines.

**Primary field metrics, independently rated:**

- Claim detection precision/recall against transcript-anchored exhaustive reviewer candidates. Missing claims count as misses.
- Meaning/interpretation fidelity of materially checkable claims (including alternate reasonable readings); reconstruction fidelity of individual premise and conclusion relations.
- Correct source attribution, quotation boundaries, reference time and source lineage; evidence recall, relevance, and adequate falsification search.
- Correct factual classification *conditional on the independent reference standard*, with `ABSTAIN` retained as a separate output, not silently counted as correct.
- False-certainty rate among decisive outputs, including false content, unfaithful interpretation, inadequate evidence, disputed truth, or temporally inadmissible sources.
- Formally checked inference when formalizable; calibrated abstention otherwise. Causal, statistical and normative tasks require appropriate domain validators, not Boolean NLI alone.
- Review/correction effectiveness; latency, dollars per usable investigation and repeated-case degradation.

**Uncertainty:** Measure exact integer counts and predeclared confidence intervals. `field_validation.py` reports the one-sided Clopper–Pearson upper bound on false certainty *among decisive outcomes*. If `n` independent identically distributed decisions have zero errors, the one-sided 95% bound is `1 - 0.05^(1/n)`: for `n=300`, approximately 0.995% (not 0%). This statement is conditional on an adequately representative and independent sampling process. It does not apply to other populations, unseen domains, distribution shift, or corrupted reference labels. Low-risk consumer and high-stakes professional use require separately declared operating thresholds; abstaining on 100% of cases can yield zero observed wrong decisive verdicts but **zero usefulness** and cannot pass a coverage gate.

**Blindness and evidence integrity:** FAR must emit/freeze predictions before externally adjudicated references are unsealed. Freeze hashes/times in a separately controlled store. The local scorer records content hashes but **cannot independently verify** earlier freezing, signatures, timestamp authority, reviewer identity, correct sampling or adjudication independence. Those are external obligations.

**Baseline sources and known limitations:**

- AVeriTeC: real-world claims with web evidence, justifications, timestamps, and contextual information; independently labeled reference sets but annotator agreement is not perfect: https://github.com/MichSchli/AVeriTeC and https://arxiv.org/abs/2305.13117 . The 2024 task awarded a result only when both verdict and evidence met criteria: https://aclanthology.org/2024.fever-1.1/ .
- FEVEROUS: text/table evidence and explicit `NOT ENOUGH INFO` status: https://fever.ai/dataset/feverous.html . A closed-domain benchmark cannot by itself establish open-world truth verification.
- Claim Cards, arXiv:2610.20457 (Oct. 14, 2026): varying interpretation can materially change verdict; explicitly recording interpretations did *not* itself measurably improve expert agreement.
- No Hindsight, arXiv:2610.04888 (Oct. 4, 2026): benchmark verdicts can be inflated by knowledge/evidence published after claim time.

## IV. Field scorer: narrow machine assurance

`field_validation.py` takes two independently supplied JSON arrays, one of frozen predictions and one of independently adjudicated labels. Each array must contain exactly the same unique `case_id` set: case drops fail closed. Example:

```json
[{"case_id":"case01", "verdict":"ABSTAIN"}]
```

Reference (provided by a separate adjudicator, NEVER synthesized from FAR output):

```json
[{"case_id":"case01", "domain":"journalism", "reference_verdict":"SUPPORTED", "mapping_fidelity":"FAITHFUL", "evidence_adequacy":"ADEQUATE", "temporal_eligibility":"IN_WINDOW"}]
```

Allowed predicted verdicts: `SUPPORTED`, `REFUTED`, `INSUFFICIENT`, `ABSTAIN`. Allowed reference verdicts add `CONTESTED`. The external adjudicator's mapping fidelity is `FAITHFUL`/`UNFAITHFUL`/`DISPUTED`; evidence adequacy is `ADEQUATE`/`INADEQUATE`/`UNDETERMINED`; temporal eligibility is `IN_WINDOW`/`NOT_ADMISSIBLE`/`UNKNOWN`.

```bash
python commercial/far-investigation-audit/field_validation.py --predictions predictions.json --adjudications blinded_reference.json --output score.json
```

To score FAR's **current** output, use `--far-bundle /path/to/a/full_cli/output` in place of `--predictions`. The scorer verifies the package and emits `ABSTAIN` for all its claims, because present FAR outputs never establish real-world truth. This negative result is a feature of honest scoping, not a defect in the scorer.

The scorer returns result provenance hashes, overall and per-domain counts, coverage, false-certainty counts among definite decisions, one-sided error upper bounds, and explicit `false` flags for external independence and universal proof. No score automatically passes a gate, changes the FAR claim ledger, modifies the accepted FAR/FARA kernel, or authorizes a benchmark execution.

## V. Conditions for a publishable bounded claim

A named evaluation universe and protocols must be fixed; independent investigators must verify reference construction and execution controls; missingness, disagreement and abstention must be disclosed; matched baselines and predeclared thresholds must be satisfied with confidence intervals; and a genuinely isolated review must replicate the result. Then FAR may claim **measured performance on that population under those conditions**, not universal semantic access or unrestricted truth determination.

**Current status:** No externally adjudicated prospective outcomes of PR #578 are available here. The existing 60-case PR #518 is prepared, not run. Real-world accuracy, semantic fidelity and independent source authenticity are therefore **UNESTABLISHED**. The current component is not merge-ready on that basis.
