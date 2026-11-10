# Before/after source-exact test runner (Research)

**Role.** Provides a small independent-observer *execution primitive* for the [Research factory evaluation protocol](factory-self-evaluation.md) tracked in [#629](https://github.com/n0tf0und0ut/Project-FAR/issues/629). It **does not run the registered eight-task factory-vs-control pilot** and is not a provider/agent runner, an independent reviewer, signed evidence collector, protected GitHub result, or demonstration of FAR agent reliability.

## Inputs and trust boundary

`tools/factory_before_after.py` uses a trusted local Git repository, two exact full commit SHAs where baseline is ancestor of candidate, one already-frozen *top-level* `tests/test_*.py` oracle (no nested path or duplicate discovered basename anywhere under `tests/`) with independently supplied exact SHA-256, and a bounded integer timeout. **The test file must exist with identical bytes at both commits.** The operator must freeze the oracle digest *before* seeing or changing candidate code; the tool cannot prove the operator did so. The fixture is not generated or chosen by the candidate worker.

The runner creates separate, fresh detached Git worktrees, executes the same trusted Python unittest discovery command, streams stdout and stderr through trusted-owned anonymous pipes into sealed log files (up to 8 MiB per stream per run; overflow yields UNKNOWN) with SHA-256 and byte lengths, records test counts, exit status, monotonic duration, UTC timestamps and a small environment fingerprint, and terminates its POSIX process group and closes both inherited output pipes **before hashing**, then removes the temporary worktrees. Windows/non-POSIX execution is not supported by this bounded collector. Output receipts and logs are stored outside the repository, and an existing output directory cannot be overwritten. A commit whose test oracles differ returns **INCOMPARABLE** without running tests; timeouts, zero-test passes, missing results and tracked-source modifications remain **UNKNOWN**.

The observation vocabulary is deliberately narrower than proof:

- `OBSERVED_EXIT_STATUS_IMPROVEMENT`: baseline unit test exit failed and candidate passed, with nonzero discovered tests and identical frozen oracle bytes.
- `OBSERVED_REGRESSION`: baseline passed, candidate failed.
- `OBSERVED_NO_REGRESSION`: both passed.
- `NO_OBSERVED_IMPROVEMENT`: both failed.
- `INCOMPARABLE` or `UNKNOWN`: no sound basic process comparison.

These indicate observed process behavior only. The runner accepts only a direct `tests/<pattern>` oracle, fails closed on ambiguous discovered basenames or precompiled `.pyc` files in either checkout's tests tree, and starts each Python interpreter with a private empty alternate pycache prefix so normal source-tree bytecode caches cannot substitute the frozen oracle. `PYTHONDONTWRITEBYTECODE` alone was insufficient because it prevents *writing* bytecode but not reading unchecked-hash compiled caches. Identical test-file bytes do **not** establish that imported helpers, fixtures, dependencies or test meaning are unchanged; the single-source digest is not a full semantic oracle freeze. A baseline failure might arise from test infrastructure, not the intended defect. Tests from candidate code and their dependencies can be malicious. **Git worktrees, environment filtering, and no-shell process execution do not isolate network, host filesystem, existing credentials, other processes, or child processes.** Run only in an ephemeral, nonprivileged, network-restricted and credential-free external runner before trusting any unreviewed source. This repo's demonstration uses throwaway synthetic local repositories in read-only GitHub Actions, not a real untrusted PR execution.

## Command example

After obtaining two full immutable commits in the *same* trusted local repository, and independently recording the oracle SHA-256:

```sh
python tools/factory_before_after.py \
  --repository /path/to/trusted/repo \
  --baseline <full-40-character-before-commit> \
  --candidate <full-40-character-after-commit> \
  --test-pattern test_existing_behavior.py \
  --oracle-path tests/test_existing_behavior.py \
  --expected-oracle-sha256 <pre-registered-64-character-hex-digest> \
  --timeout-seconds 120 \
  --output /path/outside/repo/unique-new-receipt
```

A receipt and source-raw `before.stdout`, `before.stderr`, `after.stdout`, `after.stderr` result. The local receipt is **not independently signed**; a trusted external observer must retain and verify the artifact bytes, GitHub checks and exact-head authorization separately.

## Verification

Run:

```sh
python -m unittest discover -s tests -p test_factory_before_after.py -v
python -m py_compile tools/factory_before_after.py
```

The regression suite includes an adversarial candidate that adds a forged passing *unchecked-hash* compiled oracle while preserving identical failing `.py` bytes. It must be rejected as UNKNOWN; the interpreter's private cache is removed after process-group finalization. It also creates real temporary Git histories: failing baseline to fixed candidate, passing baseline to regressed candidate, source mutation, empty test discovery, incompatible frozen oracle, expired timeout, nested/duplicate oracle rejection, symlinked output-directory alias, inherited background writer, bounded stdout overflow, input/path traversal, duplicate output path, and worktree cleanup. All outcomes are synthetic engineering fixtures, **not** registered factory performance data.

## Retrospective queue-repair smoke (real source, not a prospective trial)

The dedicated GitHub workflow also attempts one **real source-exact retrospective** on PR #630's previously documented SQLite writer-lock defect. It fetches the historical PR branch without persistent checkout credentials; verifies that the defect-reproducing test-only commit `e2648ea204d033756c8185fc3cea82ce9f26d125` is an ancestor of fix commit `6a7d5eb2864bb3440a34b0bcbdb041a452996d44`; independently compares the two historical `tests/test_software_factory.py` byte digests before running; and then invokes this runner on both exact commits. The source-only diff from before to after modifies `tools/software_factory.py`, not the test oracle. The job retains a short-lived artifact containing each run's raw logs and receipt, whether it passes or fails.

This is **post hoc**, not one of the eight prospectively admitted factory-vs-control tasks. It measures the process behavior of one corrective factory-queue source revision under hosted GitHub tests; it does not establish autonomous coding, safe provider credentials, protected merge for that separate PR, or a generalized performance advantage. If the old test fails and the fixed test passes, the supported claim is limited to that exact Git revision and test-oracle configuration. A failed smoke job is retained as a finding to investigate, not quietly excluded.

## Next dependency

A source-bound, independently controlled artifact and protected-merge observer is still needed to establish the registered `verified_protected_delivery_rate` denominator and numerator. The selected controller and coding-worker implementations must be frozen before prospective enrollment; current PR #630 remains an unmerged Research prototype that does not actually execute workers. No historical red/green test may be promoted into a new prospective factory-vs-control observation.
