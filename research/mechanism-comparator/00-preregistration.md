# FAR executable semantic checker versus matched generic checker

**Study ID:** FAR-MECH-COMP-001. **Status:** Research, prospective *secondary* mechanism audit on previously exposed, Project-FAR-authored frozen cases; not an independent agent trial.

**Preregistered before creation/execution of the new comparison code.** This registration is a distinct supplementary study and does not amend the frozen PCA-W6 protocol, original W4 records, or SWE-agent v3. Main baseline at registration: `f3c04e423df798960f64599ff638994aaaae981c`; governing root `AGENTS.md` blob `0c21bb208e2f624742fde13715326882b178dcc7`. Preserve all source hashes and the original scientific outcomes.

## Registered question and cohort

Does FAR's actual strict `far-ir/2.0` verifier detect more **finite representational collisions** than a generic, information-matched explicit-table collision checker? At what runtime cost? The intended falsifier is generic checker parity or superiority. This is *not* a test of general agent reliability or the effectiveness of a tool-using FAR recovery loop.

Use only the six exact SHA-256 pinned repaired W4 records and six exact pinned native lossy W4 records from the existing PCA-W6 independent-encoding corpus `tools/check_pca_w6_empirical_audit_utility.py` at the registered main. Construct exactly the six PCA-W6 *registered* mutant records with `inject_registered_collision`; no new primary cases or outcome-driven selection. Primary 18-item set: six clean repaired (label NO_LOSS), six registered mutants (label LOSS), six native lossy controls (label LOSS). Labels are defined by independently comparing representation/required behavior pairs, not by trusting FAR report outcome labels.

Secondary integrity challenge set, unscored separately from primary: use the first **three** domains in alphabetical registered order, starting from each repaired record: (i) corrupt its freeze hash without changing tables; (ii) replace `report.outcome` with `REFUTED` while leaving factorization evidence untouched; (iii) replace the factorization evidence status with `DECLARED_UNCHECKED`. These are not examples of a semantic collision; they test whether differently broad verifier contracts detect metadata/evidence mismatches. A generic table-collision checker is not held responsible for metadata it does not claim to validate.

## Arms

1. **Schema-only ablation:** the actual JSON Schema validator (same schema as FAR), no semantic detection.
2. **Generic active comparator:** JSON Schema validation + independent canonical JSON table-collision test; consumes the same complete input document, including tables. It must not import FAR's verifier or its oracle; a standalone implementation with zero FAR dependencies.
3. **FAR actual executable checker:** `mechanization.far_mechanization.contract_v2_strict_v11.validate_contract`, the current fail-closed strict `far-ir/2.0` engine. For clean checked PROVED, valid = NO_LOSS; for checked REFUTED, valid = LOSS; for a constructed inconsistent PROVED mutant, `FACTORIZATION_FAILURE` = LOSS; otherwise INVALID/UNKNOWN rather than counting every parse or provenance failure as a collision. Never treat `validation.success` alone as an absence-of-loss verdict.

## Measures and acceptance rules

For 18 primary items compute per-arm TP, FN, TN, FP against independent fiber-collision truth, total correctness, discrepancy identities and errors. Both generic and FAR must see **identical record objects and typed outcomes**. Perform an explicit independent parity challenge against the existing frozen PCA-W6 results and a mutation test in which a clean repaired record collapses one representation: neither semantic checker may miss it. Mutation scoring is secondary and must not be pooled into a larger sample.

For runtime cost run on the same GitHub Actions host/process with Python 3.12 and pinned source commit, warmed imports, deterministic order seed `20261112`; precisely 2 warm-up passes and 21 measured passes per 18-item cohort, alternating FAR/generic/schema per case in a deterministically shuffled order. Record `perf_counter_ns` per call, median/p95 latency per lane, runner fingerprint, and costs per correctly classified item. Do **not** infer model inference/token costs: none are incurred. A fixed-host measurement is not a performance guarantee across hardware or future versions.

Secondary integrity challenges are separately scored for strict invalidity and recorded as outside the primary outcome; no cherry-picked promotion.

**If generic matches FAR on all 18 primary items:** conclude no **FAR-unique incremental detection benefit on this exposed finite collision corpus**. If FAR costs more, conclude it has higher *measured verifier execution overhead* for this scope, while separately recognizing its more comprehensive contract/trace validation. This does not refute the mathematical theorem or broader effects.

**If FAR detects additional loss:** provide the exact differing input, ground truth, cost and independent witness. If checks cannot run on original source, return UNAVAILABLE rather than simulating.

## Integrity and limits

The study is post-hoc relative to PCA-W6's already known outcomes, prospective only for the comparator design and costs. No primary FAR-versus-generic result may be called blind, I3-independent, general-purpose agent reliability, real-world performance, or a proof of general superiority. Do not change any accepted theory, existing W4/W6 results, frozen protocol, or SWE-agent v3's false prelaunch gates. Run read-only CI under protected standard workflows, keep research draft and do not merge before review and authorization.

**Evidence to retain:** exact head SHA, original W4 source hashes, constructed mutated case hashes, source code and tests for each lane, the entire per-item matrix, ordered per-call latency, secondary challenge results, provenance and a machine-readable summary. Evidence must be sufficient to detect input corruption, algorithmic mismatch and overclaim. Negative results are legitimate outcomes.
