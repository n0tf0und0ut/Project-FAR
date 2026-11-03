# Model architecture search convergence

Status: Research maintenance record; all measured artifacts remain immutable.

Head inspected before maintenance:
`ffc7916430d91f5e132838764b87a1e1f0502210`.

`MAS-CI-001`: the optional score-mutation test required only scikit-learn in
its skip condition, but the frozen v0.3 verifier also invokes PyTorch while
reconstructing model capacity specifications. In the available environment with
scikit-learn and no PyTorch, the targeted suite failed with `ModuleNotFoundError`
in `specs`, before either intended mutation could be evaluated. Its guard now
requires both declared optional dependencies. Archive hash and member-integrity
controls remain executable without those optional packages. The frozen model,
protocol, original tests inside the archive, journals and predictions were not
changed or regenerated.

Verification on the maintenance source:

- Standard-library environment (`python -S`): 25 tests run, 13 optional-dependency
  skips, no errors. A skip is not a completed score or model reconstruction.
- System environment with scikit-learn and no PyTorch: 25 tests run, 12 explicit
  skips, no errors.
- Available scientific environment (PyTorch 2.9.0+cpu): all 29 focused tests
  passed without skips. This includes actual tiny training controls, capacity
  matching, archived-score regrading and mutation rejection. It is a new local
  software verification run, not the original 80/96-trial full model replay, not
  a replay in the original PyTorch version and not external replication.

`MAS-CI-002`: full hosted logs establish that the prior exact head's signed-cache
producer selected Python 3.12.15 and its consumer selected 3.12.16; artifact
transport integrity passed, but the consumer reported no signed cache hit for
`bootstrap.manifest`. The current cache key intentionally binds Python patch
version. [PR #617](https://github.com/n0tf0und0ut/Project-FAR/pull/617) corrects
floating job runtime selection; its protected change requires the owner's exact
signature. This PR does not weaken cache checks or copy the protected workflow.

Both v0.2 and v0.3 primary screens remain failed. The latest earlier automated
clean review covered `80fabcbc050166ec2e482302d4ee7b674de5044c`, not the final
experimental or maintenance source; a qualifying substantive review of the final
head remains required. No merge or auto-merge is authorized by this record.

`MAS-CI-003` (fixed): the architecture training smoke fixture violated the
grader's requirement that every evaluation class occur in the gold labels.
On head `cae211e3c4668ea05fbb4cdf9b3b89b16a239f83`, it drew 30 validation
labels independently from ten classes using ambient PyTorch RNG state.
That does not ensure class coverage. The prospective 13-branch integration
at `0f500d64513de9e88144fbc03b3e6bdde9b8bd78` ran 3,337 canonical tests and
reported four errors, one for each architecture, with `missing class in
evaluation` (eight other tests skipped). Health's 124 passing checks did not
erase that failure. These were software-validation observations.

The [supplementary integration evidence](integration-fixture-regression-20261103.zip)
retains the original failure log, health log, 13 published input heads and
simulation receipt, and the actual dependency-environment metadata captured
after execution. Its SHA-256 is
`b55a67ca2aa4973e969a98d3a0dd5d92f123868804b4b9180b4d59699a6ced48`;
the original canonical log inside has SHA-256
`e6e7776cd0d1eb67a7c02c212dd19c86119f5a50f1f0e30b04a2848bb04da792`.
The capture is post hoc and asserts no prospective registration or new model
study. Each retained member's byte count and digest is in the ZIP manifest.

Minimal reproducer: set `torch.manual_seed(2)` immediately before running
`TorchTests.test_all_architectures_train_and_share_output_contract` on the
unmodified head. Validation class counts are `[3,5,5,0,2,0,4,5,5,1]`, omitting
classes 3 and 5; all four architecture subcases raise the original error.
Extracting the unchanged old fixture into the shared test helper made the new
fixture regression fail in six subcases before correction, exposing missing
class coverage, ambient-state dependence and global RNG consumption.

The shared nonbenchmark fixture now constructs cyclic labels explicitly for
both train and validation splits, covering every class for both tested sizes.
Feature generation uses a local generator. Each Torch test restores the
caller's CPU RNG state. The regression checks class coverage in each split,
identical fixture tensors under ambient seeds 2, 42 and 999 with prior random
draws, and unchanged ambient RNG state after fixture construction. An explicit
negative control still requires `grade` to reject missing gold classes. The
runtime grader and experimental sources were not changed.

Verification after correction (PyTorch 2.9.0+cpu):

- `python -m unittest discover -s tests -p 'test_model_architecture*.py' -v`:
  all 30 focused tests passed without skips.
- The canonical runner's discovered prefix through this module ran all 1,313
  preceding and affected tests in their canonical order, starting from global
  Torch seed 2: passed, with two explicit skips. This is a prefix check of this
  PR's source, separate from the complete combined integration run.
- `python -S -m unittest discover -s tests -p 'test_model_architecture*.py' -v`:
  26 tests ran without errors, with 14 explicit optional-dependency skips.

The frozen v0.3 source, protocol and 96-trial archive remain byte-identical;
their SHA-256 values are respectively
`83cd655603557bd62b95119216aaf674938c698f915eff65fab7f1bd5523202f`,
`73281ff83c57a7893220b21245e45c43a57ecca2089bfd03d2bb391188abf05b`, and
`5d98feda61f9689f055c3d776de3328767dfc51b779337152c0f044da68ef31c`
(the last hashes the retained base64 file). Both original negative primary
screens remain unchanged. Complete integration verification, final-head review
and protected gates remain separate obligations.

`MAS-VERIFY-001` (fixed): duplicated execution configuration and identity were
not consistently bound across the report, registered protocol, journal start
and saved replay receipt. Source review: [comment 4461520029](https://github.com/n0tf0und0ut/Project-FAR/pull/615#discussion_r4461520029),
thread `PRRT_kwDOTH_vCM6zXvAO`, review `5760746572`, reviewed head
`eb0111f09f15b104ac630d8814e0735dc1b7d556`, archive auditor lines 48–49.

The original reproducer changed only embedded `learning_rate` from 0.004 to
0.008, recomputed the report checksum, updated the replay receipt's report
checksum, and rebuilt member checksums in the manifest. The original registered
protocol and journal remained unchanged. The reviewed archive auditor accepted
that inconsistent archive. Twelve coordinated archive mutation subcases all
failed to raise before correction: four embedded protocol fields (learning
rate, batch size, training threads, study ID), a protocol-plus-digest rewrite
against the unchanged journal, four report environment/identity substitutions,
and three replay receipt identity substitutions. The frozen standalone
`verify()` also accepted the changed learning rate both with and without a
rebound environment protocol digest, despite receiving the unchanged journal.
Those are validation defects, not replacement experimental observations.

The current post-execution auditor is version 1.1. Its shared `verify_report()`
binds canonical embedded protocol bytes to the environment digest and, when
supplied, registered protocol bytes; checks study ID, device, thread count and
frozen source identity; and binds the complete report environment and study ID
to the journal start. Archive validation also binds the saved replay's study,
source, threads and complete per-trial identities/checkpoints to the report.
Current replay calls this boundary before training. The current standalone
command requires a journal and accepts registered protocol bytes; see the
[current commands](README.md). The frozen original runner, including its weaker
historical `verify()` and CLI, remains byte-identical and is not current
verification authority.

Regression controls coordinate mutable report, journal, receipt and manifest
hashes so stale-checksum rejection cannot conceal the missing bindings. They
also cover empty replay coverage, a substituted journal-start study, rejection
at both standalone and replay boundaries before any training call, the actual
standalone CLI, and a coherently rewritten report/journal that still disagrees
with separately supplied registered protocol bytes. These consistency checks
cannot attest the truth of a completely coordinated untrusted replacement
history, nor establish independent scientific replication.

After correction, all 38 focused architecture tests passed without skips in
the dependency-equipped environment; the standard-library run passed 34 tests
with 15 explicit optional-dependency skips. Both current archive and standalone
report CLI commands accepted the unmodified original evidence, retaining 96
records, original report digest
`0e316abb4119d10281cec2c4b0d233fe4cbfca8353db23f22eadf770e415e808`
and `primary_pass: false`. No original model was retrained for this repair.
The frozen source, protocol, scientific archives and supplementary integration
failure ZIP retain their previously recorded identities. Final-head review,
hosted checks and complete combined integration verification remain separate.
