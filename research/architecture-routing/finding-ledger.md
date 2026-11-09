# Architecture routing convergence evidence

Status: Research. Protected-main integration commit
`00f8618dfc0f1c79ca8be8e4aab673e1c552c49f` preserves all original protocol and
observation bytes from starting head `9d691caaebbe3b17f598c4711d37d337bbea933a`.
It reconciles the research index with main's completed #605 result. No trial was
rerun. The completed v0.3 result remains fixed 12/12 versus model 9/12, with three
abstentions, 4,064 model tokens and a 963.1036 ratio of median latencies. No
model-routing advantage was demonstrated on these authored cases.

| Root cause | Original source and reviewed SHA | Corrective commit and present verification |
| --- | --- | --- |
| ARCH-CLI-01: direct script omitted repository import root | [4445918783](https://github.com/n0tf0und0ut/Project-FAR/pull/606#discussion_r4445918783), thread PRRT_kwDOTH_vCM6yzAe1; `6b8fcf838bb01edbe1c2c1264a7f4cffd0b6cf58` | Fixed in `bf157a6ef52d68b92f5e727b366e2a014ba4ef6a`; actual direct-script smoke and `test_direct_script_smoke_executes_from_repository_root` pass. |
| ARCH-ORDER-01: replay ignored registered counterbalancing | [4445918791](https://github.com/n0tf0und0ut/Project-FAR/pull/606#discussion_r4445918791), thread PRRT_kwDOTH_vCM6yzAe6; same reviewed SHA | Fixed in `bf157a6ef52d68b92f5e727b366e2a014ba4ef6a`; exact schedule and smoke-order regressions pass. |
| ARCH-OUTCOME-01: self-reported verdict could credit abstention | [4445991291](https://github.com/n0tf0und0ut/Project-FAR/pull/606#discussion_r4445991291), thread PRRT_kwDOTH_vCM6yzLRu; `9cc778dc0ccc3e760c22cf082cec919f3abf2345` | Fixed in `431f6ddf885578a5668e5b179a150f7562bac97d`; action/outcome contradiction and fake-verdict regressions reject forged success using native recomputation. |
| ARCH-PROMPT-01: A01/A04 projection collision | [4446302221](https://github.com/n0tf0und0ut/Project-FAR/pull/606#discussion_r4446302221), thread PRRT_kwDOTH_vCM6yz53I; `6853b92d2bee9f4c22f98eb06cb616103865ae44` | Original negative v0.2 preflight retained. Separately frozen v0.3 includes submitted witness in `7aa907fd821d6551a9e8037953196d8cfd814a06`; uniqueness and no-oracle-projection regressions pass. Original experiment was not rewritten. |
| ARCH-PARTIAL-01: later timeout erased prior calls | [4446302230](https://github.com/n0tf0und0ut/Project-FAR/pull/606#discussion_r4446302230), thread PRRT_kwDOTH_vCM6yz53O; same reviewed SHA | Fixed in `8a85e8aae8b1a0907c21d3226edee49decf5725d`; partial evidence, monotone checkpoints and atomic-replace regressions pass. |
| ARCH-STATUS-01: obsolete unexecuted caveat contradicted real trial | [4446401033](https://github.com/n0tf0und0ut/Project-FAR/pull/606#discussion_r4446401033), thread PRRT_kwDOTH_vCM6y0IVQ; `c3b0001be844b47a915e5a79c235fb3cec5a724c` | Fixed in `9d691caaebbe3b17f598c4711d37d337bbea933a`; README distinguishes completed bounded observations from absent external validity. |

The current maintenance commit archives the original exact live workflow in
[`original-workflow-v0.3.yml`](original-workflow-v0.3.yml), SHA-256
`f1aa9eee500d2ca2fd0904aa897615152b602eb53ad115523f3ebf620b9479a3`.
The original job name now verifies offline contracts instead of repeating the
completed scored trial on every maintenance push. New live scoring requires a
separate prospective registration, identity and output location. The
[original observations](execution-observation-v0.3.md), failed v0.2 and repeated
single-prompt v0.1 remain unchanged.

Verification: both routing test modules pass 24 tests; the actual direct CLI
smoke completes all 24 fixed checks. Unit mocks are not additional model trials.
The six source threads still require hosted disposition and final exact-head
substantive review. Required CI and protected repin authority are separate; this
ledger does not itself establish merge readiness or semantic correctness.

## Prospective research-index compatibility

`ROUTING-INTEGRATION-001`: a read-only `git merge-tree --write-tree` simulation of head `ed1dce1464f2f8445bac6bcdd31ebc041f95d4fd` with the pending explicit-dispatch/investigation branches found an adjacent insertion conflict in `research/README.md`. No runtime or frozen research contract conflicted. The architecture link is relocated to the first major-area entry, preserving its exact wording and source target, so the independent navigation additions apply cleanly. This is a documentation-only integration correction; it generates no new experiment or model observation. The final candidate must retain hosted checks and renewed exact-head review. No PR or protected branch is merged by the simulation.

`ROUTING-DOC-001` (2026-11-06): at `cd77adffc3473439445fc295756f7d3f853e4c00`, the README command example still said that the current maintenance workflow launched the runtime study, contradicting its unit-test/smoke/schedule-only steps and the archived-live-workflow boundary below. The example now states the actual offline behavior and identifies the preserved original live workflow. No executable source, protocol, workflow or observation changed. Documentation validation passes with zero failures; the original 24 routing regressions and 24/24 fixed smoke remain valid. The original artifact `13170780390` was retrieved again: ZIP SHA-256 `1fb533502a20c860c28b2a6a8d4a4d8a1b43b133b93c0d376bdb6bc9350e7f6f` and result SHA-256 `17b92856c59e077c3dfb4dfec08fb19ae7ae6d9d0be84439a65eaf1f73622922` match; all 36 schedule/outcome records, twelve raw request/response hashes, prompt projections, token totals and medians reconstruct. This is replay of preserved evidence, not another model trial.
