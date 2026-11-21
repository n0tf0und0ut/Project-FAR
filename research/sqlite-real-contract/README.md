# FAR-SQLITE-REAL-CONTRACT-001 — Executed SQLite semantic certificate

**Status:** Research; finite externally specified engine behavior, investigator-selected cases. **Not EFR-001, not an I3 replication, not Accepted theory.**

## Question

Can FAR produce a *completed positive* exact-preservation certificate against behavior obtained from a real non-FAR system, and expose a real negative/counterfactual contract extension, instead of presupposing target semantics from FAR's own representation?

## External system and independently published semantics

Upstream SQLite documents SQL null and `IS`/`=` comparison semantics at https://www.sqlite.org/lang_expr.html, and storage classes / comparison affinity at https://www.sqlite.org/datatype3.html. The measured target was the actual SQLite engine called by parameterized SQL, not a FAR-authored oracle. These two URLs provide interpretive documentation, not an independent review of this FAR experiment.

Observed local engine: SQLite **3.46.1**, source identifier **2024-08-13 09:16:08 c9c2ab54ba1f5f46360f1b4f35d849cd3f080e6fc2b6c60e91b16c63f69aalt1**, Python 3.13.5. Compare runtime identity and source ID at every reproduction. Engine variation requires recording the new fingerprint; behavioral disagreement fails closed.

## Exact scoped contract

World domain (six *typed bound values only*): SQL NULL, integer 0, integer 1, text '0', text '1', text 'x'. Observation family: `SELECT ? IS NULL`, `SELECT ? = 0`, `SELECT ? = 1`. Every query is executed separately with a bound parameter through the real engine. SQL `NULL` is preserved as the typed Python `None` outcome, not coerced to false.

| Bound value | IS NULL | = 0 | = 1 | Additional = '0' |
| --- | ---: | ---: | ---: | ---: |
| NULL | 1 | NULL | NULL | NULL |
| integer 0 | 0 | 1 | 0 | 0 |
| integer 1 | 0 | 0 | 1 | 0 |
| text '0' | 0 | 0 | 0 | 1 |
| text '1' | 0 | 0 | 0 | 0 |
| text 'x' | 0 | 0 | 0 | 0 |

Three primary tests induce exactly **four classes**: {NULL}, {integer 0}, {integer 1}, {text '0', text '1', text 'x'}. The proposed representation `missing / number_zero / number_one / other` has exactly this kernel. The script checks **all 36 ordered pairs** and the four output classes, so it supplies a complete **finite real-engine** positive certificate for the chosen domain and contract (not all SQLite).

## Required negative results

1. A representation preserving only the SQLite storage class merges integer 0 and integer 1 while the engine distinguishes them under the primary `= 0` and `= 1` tests: **LOSS CONFIRMED**.
2. Extend the original contract to include `SELECT ? = '0'`: the formerly equivalent text '0' and text '1' now differ (1 versus 0). The original four-class quotient is **NOT sufficient for the extended contract**. This query is an explicit extension, not a blinded held-out benchmark.

## Executed verification and provenance

The local full research package includes `verify.py` (Python `sqlite3` plus separate `ctypes` direct C API binding, both checking the same SQLite library), 15 adversarial Python unit tests, `evidence.json` with all measured rows and countermodels, `generate_lean.py`, a deterministic `FiniteSQLite.lean` proof and a SHA-256 manifest. Results on the recorded local engine: **15/15 tests PASS; positive exact 4-class quotient; both negative controls reproduced; two API paths agree**. The C and Python bindings do *not* constitute independent SQLite engines.

This repository research version includes `replay.py`, `FiniteSQLite.lean` and a read-only CI workflow, which reruns the external engine and kernel-checks the finite table. Local Lean compilation was unavailable when the full package was assembled; **do not claim kernel success here until the exact-head GitHub Actions run succeeds**.

## Scientific boundary

This is an **actual finite executable system certificate**, not a proof of real-world or all-SQLite contract completeness. No external party selected these six cases, no external investigator independently evaluated the results, and no general agent-reliability improvement is measured. The engine/documentation are external but the study framing is project-authored. The contract-to-engine bridge is provided by direct executable behavior on every case, not by a model-generated target label. The bridge to all possible real-world states is unproved.

This study is not a run of the frozen EFR-001 program. It neither modifies accepted Core Theory v1.1 nor upgrades any canonical evidence or assurance status. A genuine external-investigator study remains a separate obligation.
