# Maintenance recovery: historical defect control (Research)

**Status:** Research; an algorithm-level local replay and four offline harness tests were executed on 2026-11-10. A source-exact execution of the new runner on the two historical Git blobs, a fresh blind agent repair, and a human maintenance assessment have **not** been executed. This record does not establish maintainability, agent competence, or effects of any FAR instruction or architecture gate.

## Question and scope

Can a reproducible real defect provide positive/negative controls for a future *maintenance-recovery* evaluation without introducing a new mandatory repository gate? This package records a known factory dependency-graph regression as a historical **calibration control only**. The underlying regression has already been addressed in open PR [#630](https://github.com/n0tf0und0ut/Project-FAR/pull/630). It is unsuitable as a fresh blinded task because its bug, fix and tests are public and the answer is already exposed.

The independent-maintainer question from the council remains **UNKNOWN**, not a positive result. [PR #635](https://github.com/n0tf0und0ut/Project-FAR/pull/635) already provides a research-only isolated coding-agent evaluation approach; it reports zero actual model executions. Reuse an appropriately verified external agent runtime and genuine hidden task/evaluator separation for any successor study. Do not rewrite frozen inputs in #635.

## Immutable historical sources

| Condition | Exact commit | `tools/software_factory.py` Git blob |
| --- | --- | --- |
| Defective predecessor | `23893f0c45ab3afb038c401f4b1d53295009f2c1` | `7d622ec33ed367d7335ab5318519635a251e1c10` |
| Corrected successor | `66047a9e61b615063d4ef62aeb09be10b13a8112` | `6a395d71cc049e9b2cceacbc0b971e2523ac06d2` |

Both files are read from Git history by exact commit and verified against their expected Git blob identity. The runner does not write to source or alter the checkout, and refuses missing or mismatched source. If either historical commit is unavailable in the local checkout, fetch the open PR branch through ordinary Git mechanisms first (for example, `git fetch origin refs/pull/630/head`), then execute:

```bash
python3 research/maintainability/maintenance-recovery-001/replay.py --repo .
python3 -m unittest tests.test_maintenance_recovery_001 -v
```

The script runs four graph cases per source with the recursion limit fixed at 900, including a valid 1,250-node chain and a closing back-edge cycle. It reports structured outcomes and whether they match frozen expectations. Child-process execution is not a hardened operating-system sandbox. The two historical sources are trusted, project-authored Git objects; the report is internal retrospective verification only.

## Recorded local algorithm-level observations

The replay at `/mnt/data/far-maintainability-replay/replay.py` used manually reconstructed versions of the inspected pre/post algorithms, not the full committed source blobs. The observed outcomes matched all eight expected case results:

| Case | Before | After |
| --- | --- | --- |
| Small valid DAG | accepted | accepted |
| Small cycle | structured_cycle | structured_cycle |
| Deep valid DAG | recursion_error | accepted |
| Deep cycle | recursion_error | structured_cycle |

Offline harness contract tests: **4 passed**. These tests use synthetic source fixtures and demonstrate fail-closed Git blob binding, subprocess observer outputs, and rejection of unavailable history or malformed evidence; they do not certify the actual Git-history replay or an agent's performance. The earlier hosted PR #630 red/green checks remain separately recorded in that PR; do not relabel them as new runs.

## Evidence boundaries and successor criteria

A valid new blinded maintenance trial requires a newly registered, previously unrevealed task; an immutable base commit; a privately held independent behavioral oracle; authenticated isolated coding-agent execution; exact workspace and model receipts; unchanged task/oracle hashes; declared time and tool budgets; and an evaluation of correct repair, regression avoidance, unnecessary changes and discovery behavior. If any of these conditions is missing, record `NOT_EXECUTED`, `INCOMPLETE` or `UNKNOWN` as appropriate. A historical PR replay and internally authored tests cannot establish independent repair capability.

No new permanent CI gate, scientific claim, protected branch setting, accepted theory, or existing frozen experiment is changed by this package.
