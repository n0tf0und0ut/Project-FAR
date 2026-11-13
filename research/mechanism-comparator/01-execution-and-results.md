# FAR-MECH-COMP-001 — measured execution and disposition

**Status:** Research; internally run, prospectively registered *secondary* comparator on an already-exposed corpus. No scientific acceptance, external human independence, general-agent claim or protected-main promotion.

## Provenance and verification

- Pre-registration freeze commit: `0fb08050d5f6089c4aff2b337461a17ad1b3e9c9`, authored before the new checker and timing code.
- Original protected-main baseline: `f3c04e423df798960f64599ff638994aaaae981c`, current root AGENTS.md Git blob `0c21bb208e2f624742fde13715326882b178dcc7`; Research Execution Charter was read.
- Source inputs: the six W4 `repaired`, six registered W6 first-to-second-case representation-collapse mutations, and six native W4 `lossy` records. `tools.check_pca_w6_empirical_audit_utility._record_groups()` SHA-256-verified every original W4 input against the frozen registered corpus manifest before execution. The new audit did not modify any frozen record, base validator, outcome, methodology or SWE-agent v3 gate.
- Read-only hosted execution: [GitHub Actions run 43349828485, job 131637903184](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/43349828485/job/131637903184) at source head `c79024f3b072b4a004049567a241b0d030f92bec`. Exact SHA of the hosted evidence ZIP `63875424d3fb0e18c3aa642aa3dc3bbe0cd2d6166325a633d77b2e287ad05d32`; it contains `results.json` (all 18 per-item predictions, diagnostics, 1,134 measurements, fingerprints) and `console.log`. The source results may be reproduced at later exact heads only after rerunning their check.
- The original PCA-W6 governed test/checker and all **16 new adversarial unit tests passed** before benchmarking. The CI then asserted the exact preregistered primary cohort, counts, per-case predictions, integrity classifications, number of timing observations and no model calls.
- Runtime: GitHub-hosted Linux `7.0.0-1017-azure` x86_64, Python `3.12.16`, `jsonschema==4.23.0`, `PyYAML==6.0.2`; exact interpreter source and generic-checker SHA-256 recorded in `results.json`.

## Three actual executable lanes

1. **Schema ablation:** same declared JSON Schema, without semantic equivalence analysis.
2. **Generic semantic comparator:** same JSON Schema, same complete input document, independently implemented canonical-JSON value grouping and required-behavior consistency test. It imports no FAR module. It deliberately does **not** check provenance, freeze, outcome/evidence proof or authorization.
3. **FAR strict semantic verifier:** actual current `mechanization.far_mechanization.contract_v2_strict_v11.validate_contract`; records `FACTORIZATION_FAILURE` for an internally contradicted PROVED mutant, accepts checked valid PROVED and REFUTED records by their correct typed outcomes, and returns INVALID for unrelated metadata/evidence corruption. This is an actual FAR verifier execution, not a synthetic model simulating FAR.

Ground-truth per-record semantic loss was derived by a separate O(n²) source representation/required-behavior pairwise comparison that does not read FAR report labels, call the FAR validator, or call the comparator's grouping procedure. This oracle is implementation-diverse but still Project-FAR-authored; no external source selected or validated these contracts.

## Primary 18-item result

| Condition | TP / 12 losses | TN / 6 clean | False negatives | False positives | Total correct |
|---|---:|---:|---:|---:|---:|
| Schema-only ablation | 0 | 6 | 12 | 0 | 6/18 |
| Generic semantic checker | **12** | **6** | 0 | 0 | **18/18** |
| FAR strict verifier | **12** | **6** | 0 | 0 | **18/18** |

All eighteen cases agree between generic and FAR. This demonstrates no incremental **collision-detection** accuracy unique to FAR on this already-exposed corpus. The previous W6 comparison against schema-only code establishes a semantic benefit over not performing semantic checks, not a distinctive advantage of FAR's broader implementation. This does **not** prove other FAR checks are unnecessary.

## Host-bound latency / processing cost

Two complete warm-up passes preceded **21 measured passes** over all 18 cases for each lane. Within each pass, the case order and lane order were randomized using the frozen seed `20261112`. **378 complete measurements per lane; 1,134 measurements total**, all retained.

| Condition | Mean per record | Median per record | p95 nearest rank | Correct out of 18 |
|---|---:|---:|---:|---:|
| Schema only | 2.1160 ms | 2.0920 ms | 2.2210 ms | 6 |
| Generic semantic | 2.1436 ms | 2.1217 ms | 2.2667 ms | 18 |
| FAR strict | **58.0462 ms** | **57.8933 ms** | **59.1622 ms** | 18 |

Mean FAR-minus-generic overhead is **55.9027 milliseconds per record**, approximately **27.08× the generic checker’s mean latency** on this runner. Unlike the earlier model-generation study, this is local Python verifier time and does not include token inference, network or autonomous-agent steps. The lanes perform different amounts of provenance/evidence validation; the performance ratio is **not** a controlled comparison of identical functionality.

Under the 18-item semantic-loss classification objective, FAR incurred higher compute with **zero additional correct decisions** relative to generic; therefore no incremental **cost-per-extra-correct-collision-verdict** can be computed (denominator zero).

## Separate integrity adversaries (3/3)

Exactly the three preregistered corruptions of clean records were replayed:

| Case | Semantic collision? | Generic result | FAR result |
|---|---|---|---|
| Wrong frozen contract hash | No | NO_LOSS | **INVALID — FREEZE_HASH_MISMATCH** |
| Falsified REFUTED outcome with factorization evidence | No | NO_LOSS | **INVALID — CHECKED_EVIDENCE_OUTCOME_MISMATCH** |
| Unchecked evidence status attached to PROVED | No | NO_LOSS | **INVALID — DETERMINATE_OUTCOME_UNCHECKED** |

These prove FAR performed additional **integrity and evidence-validation work** that the deliberately restricted generic comparator did not attempt. They are **not** additional detected semantic collisions or evidence that an equally feature-complete generic checker would fail them. They are unscored separately from the primary 18.

## Actual discovery

**A fair generic semantic checker tied FAR on its full measured 18-item collision-detection objective, with substantially less verifier CPU time.** FAR's current strict verifier adds provable fail-closed integrity behavior at additional cost. Therefore:

- For a task **limited to exact finite-table collision detection**, this experiment does not justify FAR's additional compute over a generic checker.
- For an application that values freeze integrity, checked status, and report/evidence binding, FAR has demonstrated relevant correctness behavior that the comparator lacks. **No task-weighted loss function, actual frequency of corrupt evidence, or external cost model was supplied**, so end-to-end value is **UNRESOLVED**.
- No model ran. No agent was given tool access, feedback, corrective retries, or real task completion grading. Thus **no general-purpose agent reliability effect or causal FAR-enabled agent advantage is established**.
- Externally framed/selected contracts and blind replication remain absent; results are exact only for the declared 18 + 3 records, not population estimates.
- PR remains Research and must not merge before independent exact-head review and protection checks.

## Next logically necessary observation

A proper causal test must instrument real tool-using agent execution, confirm the FAR validator actually runs and feeds back into correction, and compare an equally resource-constrained generic semantic verifier and a FAR ablation. The current `research/external-validation/swe-agent-v3/execution-gate-v1.0.json` still explicitly prohibits pilot/model calls until its many frozen identity, task, budget, harm, comparator and authorization gates are satisfied; this study has not supplied those authorizations. No self-authored synthetic agent success rate should be substituted.
