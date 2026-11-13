# FAR-MECH-COMP-001 — post-hoc schema-validation hotspot

**Status:** Research-only exploratory diagnosis *after* seeing the preregistered FAR-vs-generic cost outcome. This is not a new confirmatory endpoint, not an approved code optimization, and no frozen FAR source was modified.

## Source-level defect hypothesis

At protected main, the FAR strict `far-ir/2.0` checker calls `contract_v2_strict_v11.validate_contract()` → `contract_v2_errata1.validate_contract()` → imported baseline `contract_v2._schema_errors()`. For **every document**, the latter reads `schemas/far-contract-v2.schema.json`, invokes `Draft202012Validator.check_schema(schema)` to validate the **schema definition itself**, constructs another validator, and checks the document. This repeats a schema meta-check even when its source text is byte-identical across calls.

The retained schema's SHA-256 is `45bf6ad58ccd31c19029c525aa8e4e77fe26f5d40d9e89c37be786dc8baedc23`; this is the existing W6 frozen artifact, never changed in this probe.

**Hypothesis:** compiling and meta-checking a validator once per unique schema-source text, while still re-reading that source text each call, preserves the finite checked diagnostic results and removes most redundant processing.

## Prototype construction and safety

`profile_schema_cost.py` defines an `lru_cache(maxsize=8)` keyed by the **exact UTF-8 schema text**. Each verifier call still re-reads the live file, so altered content chooses a new key, reparses, calls `Draft202012Validator.check_schema`, and constructs a new validator. The diagnostic conversion retains the original `SCHEMA_CONSTRAINT_VIOLATION` code, message and path ordering.

**Important:** It uses a temporary module-global override to route the existing strict verifier through the cached schema-errors function. This is **not concurrent-safe or deployment-ready**; it exists exclusively to measure and falsify the performance hypothesis without touching any frozen library source. The overridden function is restored after every call, including exceptions.

## Results on the same 24 finite cases

Compared complete **ordered diagnostic sequences**, including exact code, message and path, for 18 original primary W4/W6 records, three integrity corruptions, and three invalid documents.

**Diagnostic parity: 24/24.** Checks do not merely compare boolean pass/fail.

Additional adversarial regression tests: **5/5 PASS**:
1. all 24 complete diagnostic sequences remain identical;
2. changed schema text yields a new validator instead of a stale cache hit;
3. synthetic schema file content changed *during the same process* invalidates the previous cache key and changes validation correctly;
4. restoration after an exception leaves the canonical verifier path untouched;
5. baseline frozen verifier source bytes are unchanged.

Source: [hosted run 43351329354, job 131642829554](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/43351329354/job/131642829554), exact head `209a600f1de2d39f4f94127ae2dafd2e9fb4df30`. It also passed original W6 tests, 16/16 new three-lane tests, and the 18-item preregistered comparison. A previous exploratory probe [run 43350765577, job 131641004013](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/43350765577/job/131641004013) independently passed the same 24/24 diagnostic-parity set before the additional five mutation tests were introduced.

## Independent host measurements (not cross-host guarantees)

| Exploratory run | Current FAR mean | Cached prototype mean | Ratio | Samples each |
|---|---:|---:|---:|---:|
| Run 43350765577 | 26.776 ms | 1.150 ms | 23.28× | 378 |
| Run 43351329354 | 30.824 ms | 1.275 ms | 24.17× | 378 |

Two warm-up passes, 21 measured passes, same 18 W4/W6 cases and randomized case/lane order in each run. The direct JSON-schema **meta-validation** cost measured separately was **25.676 ms** per call in the first run and **32.331 ms** in the second, consistent with this operation dominating the full verifier. It is an independently timed component, so do not present its ratio to the total as a precisely identified causal mediation fraction or combine the timing samples across runner environments.

The prototype gets 24/24 checked diagnostic equivalence without removing FAR's actual freeze-hash or checked-proof validations. The source-original checker remains the authority.

## Falsification and scope

**Evidence supports:** The schema-definition meta-validation on every record is a substantial avoidable processing hotspot in this bounded, warmed, single-process workload. A schema-content-keyed cache can preserve exactly the observed diagnostics while making the operation much faster.

**Not proved:** Full semantic equivalence across arbitrary input JSON, concurrency safety, runtime races on changing schema files, long-lived process behavior, nonfinite external target correctness, historical FAR performance effect, tool-using agent reliability or deployability.

This positive result does not retroactively improve the measured canonical FAR runtime or prove FAR uniquely superior to a similarly feature-complete independent checker. It just falsifies the idea that its initial 27× latency against the weaker generic comparator is inherently required by the finite semantic checking itself.

## Lowest-risk engineering disposition

**DO NOT modify the frozen canonical contract_v2.py or provenance manifests as a side effect of this Research study.** If formally accepted and independently reviewed, integrate a thread-safe, schema-text-keyed compiled-validator facility behind the current verifier interface, preserving its complete diagnostics, disk-change behavior and fail-closed errors; measure it with the actual product wrapper, including independent adversarial/concurrency and mutation tests. Avoid permanent monkeypatching and do not silently rewrite W6/EFR frozen evidence.

The primary question of demonstrated **general-purpose agent causal reliability advantage remains UNRESOLVED**, since no agent, model, tool-feedback loop, recovery or matched generic agent has been executed here; the existing SWE-agent v3 prelaunch gates still prohibit that study.
