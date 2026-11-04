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

This repair introduced post-execution auditor version 1.1. Its shared `verify_report()`
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

`MAS-VERIFY-002` (fixed): complete registered exposure and comparator results
were not required consistently across current verification boundaries. Source:
[comment 4461644134](https://github.com/n0tf0und0ut/Project-FAR/pull/615#discussion_r4461644134),
thread `PRRT_kwDOTH_vCM6zYBNl`, review `5760891607`, reviewed head
`1d5d29d0a8f93602fb1a3d3b7e169e8cef01638b`, auditor lines 115–118.
The archive path checked reference-event timing but not its results against
the report; the frozen score primitive checked only supplied references.

Reproducer on the reviewed source: retain only `knn5` for both datasets,
recompute `analysis`, report and replay receipt checksums, and manifest member
hashes, leaving the original protocol and journal unchanged. Both archive and
standalone post-execution verification accepted it. The breast-cancer
comparison changed from logistic regression and a difference of
`-0.011695906432748426` (fail) to `knn5` and `+0.023391812865497186` (pass).
The combined two-dataset primary screen still failed; this counterexample
does not turn the original overall result into a success. Two new regression
methods failed in seven subcases before correction, including reference
omission/relabeling, changed journal results, and a duplicated reference event
accepted by standalone verification.

The existing post-execution auditor is now version 1.2. It requires exactly
the registered two datasets, three named references per dataset, and both
complete validation/test prediction cohorts. It checks the full cohort
partition/counts and ordered neural dataset × scale × budget × family × seed
matrix. Shared journal checks cover the exact neural start/training/test
identities and specifications, complete selection groups and validation
averages, one reference-result event per dataset with canonical report/result
equality, and the final completion count. These checks apply to archive,
standalone and replay paths; a journal is mandatory for current verification.
Raw current inputs reject duplicate JSON fields so parser overwrite behavior
cannot conceal a comparator or event substitution. The historical frozen
runner remains unchanged.

Coordinated mutation regressions cover omitted/relabelled references, missing
or extra datasets/cohorts, prediction truncation and cohort recounting,
omitted/duplicated/relabelled neural slots and journal stages, altered start
specifications and selection evidence, duplicated reference events, and raw
duplicate JSON fields. Separate dependency-equipped controls alter predictions,
scores, or equal-sized validation/test cohort assignments in both the complete
report and journal, then re-sign mutable hashes and recompute analysis. They
still fail actual frozen-oracle regrading, demonstrating that agreement alone
does not certify an invented score. Fully coherent, truthful-looking histories
without independent attestation remain outside the assurance claim.

Final verification: all 45 focused architecture tests passed without skips;
the standard-library run passed 41 tests with 16 explicit optional-dependency
skips. The actual archive and standalone report CLIs accepted the unmodified
original evidence under verifier 1.2, preserving all 96 neural records,
six reference entries with both validation/test prediction series, original report digest
`0e316abb4119d10281cec2c4b0d233fe4cbfca8353db23f22eadf770e415e808`
and the negative primary screen. Frozen runner, protocols, original scientific
archives and the supplementary integration failure ZIP remain byte-identical.
This maintenance performed no original-model retraining. Final-head substantive
review, hosted gates and combined integration remain separate obligations.

`MAS-VERIFY-003` (fixed): internal engineering review of local commit
`b55a4689547b960b1255bbc185f8d0781036f9a4` found that coherent report/journal
durations had no numeric-domain constraint. Setting the first neural
`train_seconds` to `-100`, mirroring both training/test journal records, and
recomputing analysis and all mutable hashes was accepted; the affected
comparison's `time_seconds_mean` became `-32.876075`. Setting
`digits/knn5.training_seconds` to `-10` and mirroring its reference event was
also accepted. These are malformed cost observations, not new experimental
results. No GitHub review comment ID exists for this internal review finding.

Current auditor version 1.2 now requires every observed neural `train_seconds`
and simple-reference `training_seconds` to be an exact JSON numeric type
(`int` or `float`, excluding `bool`), finite and nonnegative. Validation happens
before journal comparison or derived-cost aggregation. The independent review's
exact negative values are regressions; coherent negative/boolean mutations
produced 12 missing-rejection failures before correction. Additional controls
require duration-specific rejection of strings, null, arrays, NaN and both
infinities. Nonfinite API values cannot be canonically signed; those controls
explicitly check domain rejection before stale-hash rejection. Coherently
rehashed integer and floating zero-duration controls remain valid. Frozen
runner, protocols, scientific archives and original negative outcomes remain
unchanged; no original model was retrained.

Verification: all 30 affected external/evidence tests passed without skips;
the same standard-library suite passed with ten explicit dependency skips.
The actual frozen-archive CLI still accepts the original 96 records and
report digest `0e316abb4119d10281cec2c4b0d233fe4cbfca8353db23f22eadf770e415e808`,
with `primary_pass: false`. Independent engineering recheck of the final
commit and combined integration remain separate obligations.

`MAS-VERIFY-004` (fixed): post-execution regrading accidentally used the host
interpreter's floating-point summation rather than the recorded interpreter's.
The [actual Python 3.11 compatibility job 126289437121](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41741543817/job/126289437121)
tested merge `2f3a3d8d96d6d971ba4829aea08a109d5205ead4` of candidate
`d143ccb6aba0f623ae4d95cc10caac7f499409bf` against protected main. It failed
canonical tests and health-fast because otherwise coherent comparator mutation
controls encountered `validation selection evidence mismatch` before their
intended invariant. A real local CPython 3.11.17 run also rejected the untouched
original archive with that error. This was an original-positive audit failure,
not a reason to weaken the mutation-test regex or skip its execution.

The original record declares Python 3.13.5. Four of 32 saved selection means
differ from Python 3.11's left-fold arithmetic. For example, the digits
width-48/steps-80 convolution mean is recorded as `0.9018518518518519`, while
left-fold addition produces `0.9018518518518518`. Frozen `grade()` and
`finish_analysis()` also contain float sums, so correcting only the current
journal checker would leave original score/analysis regrading host-dependent.
Python documents the [3.12 float-summation change](https://docs.python.org/3.13/library/functions.html#sum).
The relevant exact implementations were inspected at CPython
[v3.13.5](https://github.com/python/cpython/blob/v3.13.5/Python/bltinmodule.c),
Git blob `cc93424664c69ce9822abb92b473b6ce58bcc3da`, and
[v3.11.17](https://github.com/python/cpython/blob/v3.11.17/Python/bltinmodule.c),
Git blob `f30040507bcb33542a92ed63efd7f4271593c2a2`.
The mapped 3.12 profile was also checked against
[v3.12.14](https://github.com/python/cpython/blob/v3.12.14/Python/bltinmodule.c),
Git blob `2ae28693bee05c4a51c698930aa79de2cb9ac2db`: its relevant integer,
float-compensation and fallback branches agree on the declared 64-bit numeric
profile. Native CPython 3.12.14 independently passed the same complete
32-mean/204-grade/full-analysis and 11 mixed-type edge-vector comparison.
The compatibility adaptation's attribution, change summary and complete
upstream license are retained in [the component license](../../tools/cpython-sum-LICENSE.txt).

Current verifier 1.3 supplies the recorded arithmetic profile to isolated
copies of the frozen `grade`, `finish_analysis` and `verify` function code,
and uses that same profile for journal means. It mutates neither the frozen
module nor shared builtins. The 3.12/3.13 profile mirrors the recorded 64-bit
CPython 3.13.5 summation branches, including the initial integer prefix,
integer overflow fallback, Neumaier compensation for exact float items,
uncompensated in-range integers after a float, and finite-compensation return.
Recorded Python 3.11 uses explicit left-fold addition; unrecognized recorded
profiles fail explicitly. Profile selection is based on recorded metadata,
not a new host-environment prerequisite. Original full-model replay's existing
environment matching remains unchanged. No tolerance was introduced.

Proof on a native CPython 3.13.5 interpreter compared the adapter with the
unaltered original function code using all original predictions and original
cohort gold labels reconstructed from the registered data: all 32 journal
means matched bit-for-bit, all 204 complete grades and the complete analysis
matched canonical bytes, and 11 mixed-integer/float, overflow and cancellation
vectors matched native `sum()`. The original negative primary screen remained
false. This is bounded arithmetic reconstruction, not new model execution or
independent scientific replication.

Regression controls reconstruct the full original analysis and all retained
macro-recall/selection sums without optional ML packages, check mixed-type
summation and concurrent namespace isolation, and reject one-ULP journal and
derived-cost mean forgeries. Coherent mutation fixtures now recompute analysis
using the recorded profile so a Python 3.11 host reaches the intended comparator
and real-score rejection boundaries. The complete architecture suite passed
53 tests without skips under both actual CPython 3.11.17 and 3.12.14 with the
scientific dependencies installed. The actual Python 3.11 archive CLI accepted
the unmodified 96-record original evidence. Frozen source, protocol, original
scientific archives and prior failure records retain their identities. No
original model was retrained; hosted reruns and combined integration remain
separate obligations.
