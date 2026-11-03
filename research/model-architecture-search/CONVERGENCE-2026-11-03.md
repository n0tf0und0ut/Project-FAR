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
