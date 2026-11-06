# FAR-MECH convergence and replay correction

Status: Research software-maintenance and evidence-preservation record.
Protected-main integration base:
`c7456b469f9dfe88b92d0fc7a211e5c9ed64de61`.
Reviewed starting head: `bac0fe554247b1e71c18848f838adb1524ebea9e`.

## Preserved original observations

The exact downloaded GitHub ZIPs, unmodified member bytes, original head/run IDs
and SHA-256s are retained under
[`evaluation/evidence`](../../evaluation/evidence/pretrained-originals-manifest.json):

| Original artifact | Execution | Archive SHA-256 | Disposition |
|---|---|---|---|
| 13050862275 | 41223025391 | `4751401927162f4b511672bb982917d41b92af0b7241328476663a0fc6cee407` | Original two-token projection; no full-vocabulary claim |
| 13051320299 | 41223761759 | `ee8a60502f6735f71d07018fb16f4c0e3c4f5608844247514da594a7d8291281` | Original full-vocabulary negative result |
| 13052923193 | 41229617588 | `16aa1a0aa2f5443ec247f7097c7843c4b8e5f4f0c7ea1a170172965ce747fac5` | Measurements completed; independent replay FAILED |

The last failed execution remains a failure. Its traces are not replaced with
outputs from a repaired runner. All three original mechanism audits recompute
against the current contract. This does not attest source truth or checkpoint
execution. The old full-vocabulary result retains its exact previously reported
negative and positive cohort findings.

## Finding ledger

| Root cause | Source | Reproducer and disposition |
|---|---|---|
| MECH-BASELINE-001 | comments 4429318152/4429318155 | Numeric-equivalent distributions and equal-activation baseline pairs; already fixed before this maintenance; current regression suite verifies both. |
| MECH-REPLAY-001 | comments 4429422772/4429422775 | NaN probabilities and wrong component declarations; already rejected at starting head; actual trained-checkpoint mutation controls verify the rejections. |
| MECH-GRADE-001 | comments 4432601598/4432601604 | Coordinated incorrect per-case outcomes/KL and forged selective accuracies; already fixed at starting head; current hostile tests pass. |
| MECH-ARCHIVE-001 | comment 4432601609, reviewed head `bac0fe554247b1e71c18848f838adb1524ebea9e` | FIXED by exact original ZIP preservation and member/outer hash regression tests above. |
| MECH-SPLIT-001 | comment 4432843659, same reviewed head | Reassigning heldout/adversarial in both submitted trace and report passed. FIXED by binding both to independently keyed `task_cases()` split; regression recreates coordinated mutation. |
| MECH-RELU-001 | comment 4432843663, same reviewed head | Recorded runner intervenes after ReLU, but replay previously inserted before ReLU. A true negative post-ReLU intervention failed old replay with probability discrepancy `0.004975`; a forged zero intervention could pass. FIXED with an `fc2` input pre-hook. Real trained-weight regression accepts the true negative and rejects the zero forgery. |
| MECH-PRECISION-001 | failed job 124620919308, run 41229617588 | Rounded six-decimal amplitudes were physically replayed instead of the registered unrounded train fit/mean. FIXED as detailed below, without loosening any replay tolerance. |
| MECH-COHORT-001 | convergence adversarial inspection of the starting verifier | Coordinated omission of a case plus denominator/aggregate rewrite passed. FIXED by requiring the exact `per_split`-selected frozen task set and registered training count. The old verifier fails the new omission regression; the corrected verifier rejects it. The training question-population digest is also reconstructed and a substituted digest rejected. Full registered synthetic fixtures retain all 32 cases. |
| MECH-BINARY-001 | comment 4458971989, reviewed head `3ad6ab6df1e5aaf0608876c292604f6d0646c11b` | Three-outcome source distributions passed binary metrics with only yes/no declared. Reproduced by adding common 0.1 third-outcome mass and coordinating KL/entropy summaries; the old verifier accepted it. FIXED by requiring exactly two outcomes in all three source probability vectors before binary grading. The generic multi-outcome FAR-MECH schema remains unchanged for the digits experiment. |
| MECH-DEPS-001 | comment 4458971983, same reviewed head | DISPROVEN at this exact source. The checkout vendors `jsonschema/__init__.py` and `_validator.py`; `python -I -S` with only the checkout root added imports `MechanismAudit` and the vendored validator successfully. A subprocess regression executes that clean-import check. Manual module execution starts in the checkout root. Separate job environments do not remove checked-out source packages. No missing external-jsonschema failure or need to alter the scientific workflow was reproduced. |

The complete source IDs and exact historical commits remain available through
the original review threads. Each corrective change requires fresh final-head
substantive review; local tests do not close the protected review gate themselves.

## Precision defect: controlled engineering reproduction

A separate local software reproduction used pinned SmolLM2 revision
`12fd25f77366fa6b3b4b768ec3050bf629380bac`, actual weight fingerprint
`f628c8c925c895e0c3380249695793e6e6a7e2d1031afa4ae84e485664f69594`,
Transformers 4.49.0, PyTorch 2.9.0+cpu and two CPU threads. It collected one new
32-case engineering reproduction under a new output directory; it is not a
registered confirmatory study, a replacement observation, independent replication
or additional evidence for the primary scientific effect.

The original replay failed on `heldout-03`. The actual registered regression
amplitude `4.304758769178021` produced first answer probability
`0.38552507758140564`; substituting the six-decimal display value `4.304759`
produced `0.38552242517471313`. The latter misses the recorded quantized answer
probability by `2.6344e-6`, exceeding the unchanged `2e-6` tolerance. These two
decimals map to different float32 amplitudes.

The corrected replay independently reconstructs all 24 training activation
vectors, the train-only component selection, regression coefficients and mean.
It verifies the reported coefficients, verifies that the six-decimal trace
commitments match, and uses full-precision amplitudes for actual interventions.
Identity controls use the actually measured original activation. Binary softmax
uses the same float32 calculation as the measured runner; full-vocabulary KL
continues to use float64 logits.

The corrected replay completed **32/32 cases and 64/64 distribution pairs**, with
maximum full-vocabulary KL error **0.0**, retaining tolerances `5e-8` for KL and
`2e-6` for quantized two-token probabilities. The original failure log, new
engineering trace/result, corrected receipt, exact verifier sources, environment
and member hashes are preserved in
[`pretrained-replay-regression-20261103.zip`](../../evaluation/evidence/pretrained-replay-regression-20261103.zip),
SHA-256 `ad184273340a576cdaedc3436c3ca26273f9cc205b92a6e3abb0db0763720f56`.
An archived receipt records an actual local run; it is not cryptographic execution
attestation. Replaying the original historical reports on a different numerical
runtime can still fail its exact reconstructed fit; that must remain explicit.

## Execution and integration boundary

Maintenance PR pushes now run protocol, validator, mutation and archive checks
without automatically generating another scored scientific cohort. The optional
scientific job runs only on explicit manual dispatch, after its separate
prospective registration/freeze and unique output identity have been established.
No required protected check is removed or relaxed.

FAR's tested token-count explanation still has no probe-specific correctness
advantage and loses to the mean comparator on every original adversarial case.
No new semantic circuit explanation, competitor advantage, general agent
reliability, external validation or commercial benefit is established here.

## November 6 report-intake correction

MECH-JSON-001: review of head
`2b6a161805458f4c77deb732b9b1819df3f46746` found a raw report with
contradictory duplicate `status` or nested `model_id` fields could pass source
verification: the default JSON decoder silently selected the final value.
A synthetic source-bound fixture reproduces both failures in the
[before log](../../evaluation/evidence/report-intake-convergence-20261106/before.log).

The report verifier now reuses the existing FAR-MECH strict loader, matching
the trace-input duplicate-key boundary. The new raw-byte regression rejects
both variants; the [after log](../../evaluation/evidence/report-intake-convergence-20261106/after.log)
preserves the corrected result. The complete mechanistic suite passes
**73/73 tests with zero skips**, including the optional temporary trained-digits
and separate forward-hook controls using the available CPU dependency runtime.
Those are software regression controls; no archived experiment, frozen data,
reported outcome or scientific claim is replaced. The original successful and
failed archives retain their exact bytes and hashes. Final-head independent
review and protected checks remain separate obligations.

### Committed cohort and metadata binding

MECH-MANIFEST-001 / review comment `4494409924`, thread
`PRRT_kwDOTH_vCM60k72i`, reviewed head
`ace3b2221b976f086436a18c678e6d7c93d1869f`: the report could declare
`per_split=2`, retain only the first two cases in each split and recompute its
audits/summaries while the trace-committed source still declared the full cohort.
The earlier single-case omission control did not detect this distinct selector
substitution. A source-committed synthetic fixture reproduces acceptance of the
six-case truncation before correction; the untouched preserved full-vocabulary
archive `13051320299` is the real-data positive control.

The verifier now strictly decodes the existing `run-manifest` source and binds
the complete report metadata to its canonical JSON bytes before cohort selection.
Missing, nonobject or duplicate-key committed manifests are rejected. A distinct
smaller cohort remains valid only when its own manifest is committed consistently;
no source authenticity or external preregistration is inferred.

The [before log](../../evaluation/evidence/report-intake-convergence-20261106/manifest-before.log)
retains the failing truncation rejection and passing untouched archive; the
[after log](../../evaluation/evidence/report-intake-convergence-20261106/manifest-after.log)
passes both. All **77/77 mechanistic tests pass with zero skips**. The synthetic
fixture now explicitly commits its run metadata; no original archived source,
observation, denominator, tolerance or outcome is edited. Fresh exact-head review
and hosted protected checks remain required.
