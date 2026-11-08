# FAR live autonomous investigation — first complete execution

**Status: Research / bounded GitHub API release-tag experiment. No FAR Core change or general open-world investigation claim.**

## Exact executed environment

- Preregistered question: `Is the latest release tag of n0tf0und0ut/Project-FAR v1.0.0?`
- First completed exact-head workflow: [41537563154](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41537563154), executed head `53aa667bf9b420c68e3299815ddca10ce0651f8a`.
- [Raw ZIP artifact 13183284935](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41537563154/artifacts/13183284935), ZIP SHA-256 `422c8a5830d79308cd51f6f676d6a71998a433aaf1d39c9d486e044fd13c1779`.
- `deterministic.json` SHA-256 `819a6ab667eb38730c9b065f10bd54fcf3b6e066ce554cf2d52ab83da550df48`.
- `model.json` SHA-256 `9f51e176496c6bc6468c36458192fa6716b82385fbae45fa220454d550bacc8b`.
- The job installed checksum-pinned llama.cpp b12023 and Qwen2.5-0.5B-Instruct Q4_K_M. The test step passed 28 tests. Both independent investigation modes completed through the actual current `contract_v2_strict_v11` verifier.

## Evidence retrieved (not scripted)

| Public GitHub source | Retrieved tag | Release ID | Raw response SHA-256 |
|---|---|---:|---|
| `/releases/latest` | `far-swe-agent-v2-source-53438d4e327f` | 360110778 | `9f11d0fd4746c02fcade83bd3ee6ca7fc66c5964fc743d1dd19eecbeb1c0e92a` |
| `/releases?per_page=10` first item | `far-swe-agent-v2-source-53438d4e327f` | 360110778 | `820a8f20f2aae23c9146b6c66c973d1d85609f77aa2952c9ee34093e6f3c5f5d` |

Each source was fetched twice by **each** arm (eight real HTTP responses across two arms). The terminal semantic projections and in this run the raw response hashes were unchanged within each arm. This is bounded source-registry rechecking, **not** proof of global saturation or independent source agreement.

## Actual execution and constrained conclusion

| Observed stage | Deterministic arm | Model-proposal + protected controller |
|---|---:|---:|
| HTTP sources initially retrieved | 2 | 2 |
| HTTP source rechecks | 2 | 2 |
| Material release-tag interpretations preserved | 2 | 2 |
| Governed `far-intake/1.0` freezes | 1 | 1 |
| Frozen candidates | 2 | 2 |
| Successful canonical FAR verifier calls | 2 | 2 |
| Verified candidate outcomes | REFUTED + REFUTED | REFUTED + REFUTED |
| `aggregate_manifest` result | `INVARIANTLY_REFUTED` | `INVARIANTLY_REFUTED` |
| Model proposal calls | 0 | 8 |
| Model proposals overridden by controller | 0 | **7** |
| Model total tokens | 0 | 923 |

The model returned `FETCH_LATEST` first, then `FORK`, `UPDATE`, `UPDATE`, `Frozen`, `UPDATE`, `UPDATE`, `Frozen`. Only the first was an eligible tool action. The controlled execution used the same fail-closed, deterministic stage plan after the invalid proposals. Therefore the completed model-guided investigation **cannot** be represented as an independently successful LLM plan. It does demonstrate real model-tool interaction and a working guarded execution loop, with an observed model planning failure rate of 7/8 on this bounded task.

The value `INVARIANTLY_REFUTED` is **contract-relative**: under both declared GitHub API interpretations, the observed tag does not equal `v1.0.0`. The verifier checked a finite equality-as-factorization reduction. It did not prove whether GitHub's metadata is historically complete, which semantic version is latest, the tag's content quality, or whether all systems agree.

## Independent artifact audit

Separately from the GitHub CI result, all artifact SHA assertions were recomputed directly from downloaded bytes: raw ZIP integrity; all **4** first-response receipts and **4** recheck receipts across arms; each arm's `intake_sha256` and `freeze_sha256`; every frozen candidate contract SHA; all eight model request/response SHA-256 pairs; every evaluation's frozen contract and freeze binding; and that evaluation times postdated freeze. **Zero mismatches.**

## Boundaries still open

This is a complete *vertical* investigation for a fixed public GitHub release-tag question, not a general autonomous evidence debugger. Parsing, comparison design, search scopes and tools are authored and bounded in the code. No semantic source reliability independent of GitHub was demonstrated. Model choice is restricted to ordering the first two fetches and following required stages; once only one action is admissible, selecting it establishes no decision advantage. A general open-domain investigator would require trustworthy retrieval, a much wider guarded action set, source contradiction resolution, genuine LLM-discovered interpretation candidates with comprehensive semantic provenance, a stronger model and held-out independent scoring.
