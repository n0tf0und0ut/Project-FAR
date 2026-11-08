# Bounded pinned-Lean transport correction

Status: Research. Engineering evidence and unsigned authorization preparation;
no scientific claim, compiler pin, frozen result or protected authority changes.

## Observed defect and correction

Hosted jobs [128692894856](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/42468258181/job/128692894856)
and [128692777236](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/42468276836/job/128692777236)
reported HTTP 504 while downloading the pinned Lean release and exited 22 before
compilation. The commands made one attempt. Other jobs downloaded the same
release successfully; this is intermittent transport failure, not evidence of a
failed theorem or a defective archive.

The five existing Lean-download commands now allow three retries, with a
one-second retry delay, a 120-second window for starting retries, a 15-second
connection timeout and a 120-second per-attempt timeout. The retry window is not
an absolute total deadline: an attempt already started may finish afterward.
There are at most four attempts. Exhaustion remains a failure.

The exact HTTPS release URL and SHA-256 pin
`6fe3ce97a58f44e2b3567d455b994eacec5bfe9ae7774f2a573444480ba813fe`
are unchanged. Digest verification still precedes extraction. No fallback
archive, unchecked installer, relaxed TLS, skipped proof, signature or check is
introduced. The existing Python 3.12.16 cache-runtime correction is retained.

## Verification boundary

The new canonical workflow-contract test failed before the correction (six
assertion failures, zero runner errors) and passes afterward. It checks bounded
arguments, all five identical download commands, the fixed URL and digest,
fail-on-HTTP-error behavior and shell failure propagation. The existing runtime
binding and exact-head workflow tests also pass; bootstrap and CI workflow
validation pass with both updated file pins and an unchanged lock contract.

The managed local runtime rejects socket creation with `EPERM`, including Unix
sockets. The initial HTTP fixture attempt is therefore an environment failure,
not a successful fault test. No local HTTP recovery result is claimed.

The separate read-only [transport fixture workflow](../../.github/workflows/pinned-lean-transport.yml)
runs [real curl over Unix-domain IPC](../../tests/pinned_lean_transport_http.py)
on a hosted Linux runner. It must demonstrate recovery after one HTTP 504,
failure after four persistent HTTP errors and rejection of a downloaded body
with the wrong digest. This probe is outside canonical discovery so ordinary
local unit tests do not require socket capability. It does not weaken the
canonical deny-network policy. Hosted evidence and independent review must be
recorded against the final PR head; this preparation record claims neither.

The first published successor exposed a stale W5 current-state digest for the
changed verification workflow. The existing provenance and independent manifest
tests rejected it. Only the existing tooling entry's current digest and reason
are advanced; its executed digest and the frozen campaign manifest, inputs,
outputs and results remain unchanged. The W5 checker and provenance tests must
pass on that corrected successor. The protected workflow bytes and both unsigned
owner payloads below are unchanged by this metadata correction.

## Owner authorization remains required

Two files are protected: the validator workflow and the standalone Lean
workflow. The lock's non-file contract, allowed signer and consumption ledger
are unchanged. The current repository identity used by these payloads is
`n0tf0und0ut/Project-FAR`, immutable repository ID `1283452680`, matching the
existing request and current canonical GitHub repository identity. The dedicated
App remains authoritative for whether a returned signature authorizes a head.

The owner must inspect the current App transition and sign these exact canonical
files using the pinned FAR-only AgePony identity:

| File | SHA-256 of canonical payload | Bytes |
| --- | --- | ---: |
| [Cache and transport v2](../../validation/repin-requests/PR-617-cache-and-transport-v2.json) | `f51eac66aff6f91be4bf7abd2da9c3dc6071de5b072494d68639767104a3a9fd` | 730 |
| [Standalone Lean transport v1](../../validation/repin-requests/PR-617-lean-transport-v1.json) | `159faa0cc494e8ecfcbd2a1f6cc434d3b1a087180eac20312067d3cf3981b807` | 728 |

Both bind PR 617 and main `275252bfa72b37b5ef99b305b52d34e0543ac494`, and expire
2026-11-22T09:59:30Z. They contain no signature. Only verified returned signatures
may be bundled into the append-only consumption ledger.

The prior [731-byte request](../../validation/repin-requests/PR-617-signed-cache-python.json)
is preserved unchanged at SHA-256
`9be942dbdd931446601680821d3b91c8a371bf8af030c38717fefa3078569722`.
It names the preceding validator digest and cannot authorize this successor.
Do not sign that older file for this head. The normal protected merge remains
blocked until the dedicated App accepts both exact transitions and all other
required obligations qualify. No owner signature or merge authority is claimed.
