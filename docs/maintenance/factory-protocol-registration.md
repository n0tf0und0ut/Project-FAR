# Factory protocol source registration (Research)

This is a provenance observation for [the merged factory self-evaluation preregistration](factory-self-evaluation.md) and [issue #629](https://github.com/n0tf0und0ut/Project-FAR/issues/629). The implementation is deliberately **read-only**, with Python standard-library dependencies only. It records *which protocol bytes were merged*, not an executed experiment, signed certificate, verified delivery, approval to choose a controller, or evidence that the factory outperforms control.

The registration candidate [`research/factory-evaluation/protocol-registration-v1.json`](../../research/factory-evaluation/protocol-registration-v1.json) identifies original protected source commit `12b0b4c86b26da72b8f845ed65740baf092503ea` (merged PR #633), protocol Git blob `a9cde761b10ca85b0faaed3a5b0a8bd94ed46cdd`, and exact file SHA-256 `f3526d953e087fba98d84d6332e02c88442ec12d965cec74e8d09ef6e35a4f44`. Those are an independent *identity anchor* to protected Git history, not a performance observation.

## Verification

```sh
python -m unittest discover -s tests -p test_factory_evaluation_registration.py -v
python tools/factory_evaluation_registration.py research/factory-evaluation/protocol-registration-v1.json research/factory-evaluation/protocol-v1.json
python tools/factory_evaluation_registration.py research/factory-evaluation/protocol-registration-v1.json research/factory-evaluation/protocol-v1.json --verify-live
```

The ordinary CLI validates the registration schema, exact local SHA-256, Git object SHA-1, and that the referenced protocol passes its existing Research-only validator. It explicitly reports **external GitHub provenance NOT VERIFIED**.

The `--verify-live` command additionally fetches *actual* GitHub REST source records for PR #633, the current protected main branch, commit ancestry, and the protocol bytes at the original full protected commit. It rejects a missing merge, changed merge SHA, rewritten or unrelated history, unprotected current default branch, altered blob hash, missing bytes, non-base64 source, or mismatched object size. The hosted targeted pull-request job uses this live mode without any stored credential or write permission. An API failure reports an unknown verification result (exit 2), never success. Avoid rapid retries under rate limiting.

**Trust boundary:** the public GitHub TLS API supplies repository observations. This does not prove historical branch-protection settings, authenticate the provenance collector as independent of the current PR until that collector is itself reviewed/merged, certify the source as scientifically accepted, or create an external signature. The original Git commit is content-addressed; this candidate registration record becomes retained in protected Git history **only after** a separate normal reviewed, authorized merge.

## Not yet executed

No prospectively selected cohort, independent seed, frozen control/factory revision pair, isolated agent credentials, valid source-bound outcome receipts, or verified production deliveries exist from this registration. PR #630 remains an alternative unmerged Research queue controller. A subsequent separately reviewed execution manifest must identify both workflows before admitting any task, and a trusted observer must retain actual failed and successful attempts. Do not silently populate this record with fabricated values.
