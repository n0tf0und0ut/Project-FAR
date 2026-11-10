# Before/after source-exact test runner (Research)

**Role.** Provides a small independent-observer *execution primitive* for the [Research factory evaluation protocol](factory-self-evaluation.md) tracked in [#629](https://github.com/n0tf0und0ut/Project-FAR/issues/629). It **does not run the registered eight-task factory-vs-control pilot** and is not a provider/agent runner, an independent reviewer, signed evidence collector, protected GitHub result, or demonstration of FAR agent reliability.

## Inputs and trust boundary

`tools/factory_before_after.py` uses a trusted local Git repository, two exact full commit SHAs where baseline is ancestor of candidate, one already-frozen `tests/test_*.py` oracle with independently supplied exact SHA-256, and a bounded integer timeout. **The test file must exist with identical bytes at both commits.** The operator must freeze the oracle digest *before* seeing or changing candidate code; the tool cannot prove the operator did so. The fixture is not generated or chosen by the candidate worker.

The runner creates separate, fresh detached Git worktrees, executes the same trusted Python unittest discovery command, preserves complete stdout and stderr files with SHA-256 and byte lengths, records test counts, exit status, monotonic duration, UTC timestamps and a small environment fingerprint, then removes the temporary worktrees. Output receipts and logs are stored outside the repository, and an existing output directory cannot be overwritten. A commit whose test oracles differ returns **INCOMPARABLE** without running tests; timeouts, zero-test passes, missing results and tracked-source modifications remain **UNKNOWN**.

The observation vocabulary is deliberately narrower than proof:

- `OBSERVED_EXIT_STATUS_IMPROVEMENT`: baseline unit test exit failed and candidate passed, with nonzero discovered tests and identical frozen oracle bytes.
- `OBSERVED_REGRESSION`: baseline passed, candidate failed.
- `OBSERVED_NO_REGRESSION`: both passed.
- `NO_OBSERVED_IMPROVEMENT`: both failed.
- `INCOMPARABLE` or `UNKNOWN`: no sound basic process comparison.

These indicate observed process behavior only. A baseline failure might arise from test infrastructure, not the intended defect. Tests from candidate code and their dependencies can be malicious. **Git worktrees, environment filtering, and no-shell process execution do not isolate network, host filesystem, existing credentials, other processes, or child processes.** Run only in an ephemeral, nonprivileged, network-restricted and credential-free external runner before trusting any unreviewed source. This repo's demonstration uses throwaway synthetic local repositories in read-only GitHub Actions, not a real untrusted PR execution.

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

The regression suite creates real temporary Git histories: failing baseline to fixed candidate, passing baseline to regressed candidate, source mutation, empty test discovery, incompatible frozen oracle, expired timeout, input/path traversal, duplicate output path, and worktree cleanup. All outcomes are synthetic engineering fixtures, **not** registered factory performance data.

## Next dependency

A source-bound, independently controlled artifact and protected-merge observer is still needed to establish the registered `verified_protected_delivery_rate` denominator and numerator. The selected controller and coding-worker implementations must be frozen before prospective enrollment; current PR #630 remains an unmerged Research prototype that does not actually execute workers. No historical red/green test may be promoted into a new prospective factory-vs-control observation.
