# Explicit dispatch and bounded investigation convergence

Status: Research. Starting head `272a203d338877110f232b1c034dd04e8648ee3f`;
protected-main integration `f71ae8ca4a9b3ae67a3b7986e0b3fc85cc9f1960`.
Frozen task, preregistration and observation files remain byte-identical.
The bounded model selected ASK_SCOPE on all 12 authored uncertain cases: its
11/12 admissibility equals the strongest constant baseline. The live release
investigation required deterministic-controller overrides on seven of eight
proposals. Neither observation establishes adaptive model reliability or a FAR
causal benefit. No live trial was repeated during this repair.

## Original review dispositions

| Root cause | Source and exact reviewed SHA | Fix and regression evidence |
| --- | --- | --- |
| DISP-BYTES-01: CLI newline normalization changed source hash | [4448158559](https://github.com/n0tf0und0ut/Project-FAR/pull/608#discussion_r4448158559), PRRT_kwDOTH_vCM6y4ONX; `8150c2d14f99e5a71f2bb60f25ee62641b65c4c5` | Fixed `31d26cfd6ba60ced1725c35971f1e82b9b401b9d`; actual CRLF file and stdin SHA regression passes. |
| DISP-OPEN-01: successful OPEN contract was sent back to discovery | [4448158567](https://github.com/n0tf0und0ut/Project-FAR/pull/608#discussion_r4448158567), PRRT_kwDOTH_vCM6y4ONd; same SHA | Fixed `31d26cfd6ba60ced1725c35971f1e82b9b401b9d`; current verifier parity and existing unchecked-open fixture pass. |
| DISP-MODEL-01: malformed HTTP 200 completion lost observed bytes | [4448158579](https://github.com/n0tf0und0ut/Project-FAR/pull/608#discussion_r4448158579), PRRT_kwDOTH_vCM6y4ONi; same SHA | Fixed `210e53abeb26ad341a373b94113903a762e9fbba` and live-client `44aea3bc4c1f65cee636f9970ade4cd2299486ff`; partial raw-envelope regressions pass. |
| DISP-TEST-01: CRLF test contained literal backslashes | [4448649306](https://github.com/n0tf0und0ut/Project-FAR/pull/608#discussion_r4448649306), PRRT_kwDOTH_vCM6y5XSW; `81e7f937834f56aea9e5ab3a3c48dd4957f118da` | Fixed `f940212eb55153ff843bd699beea85d58080f8d5`; actual newline byte mutation executes production path. |
| DISP-SOURCE-01: failed source parse erased response | [4448649316](https://github.com/n0tf0und0ut/Project-FAR/pull/608#discussion_r4448649316), PRRT_kwDOTH_vCM6y5XSb; same SHA | Fixed `bcef9d71a2259576f269e89d8f3fbb99b6970e77`; initial and recheck malformed-body regressions pass. |

These five hosted threads were already resolved at intake. The authenticated
machine summary on the old head nevertheless explicitly reported unresolved
findings; a clean prose receipt does not override that state under current
policy. Main integration and the substantive maintenance changes require a fresh
exact-head review rather than weakening or reinterpreting the protected policy.

## Backported existing successor corrections

PR #614 had already implemented three further legacy corrections. This commit
reuses those exact implementations and adversarial fixtures so #608 can be
reviewed without knowingly retaining their defects. It adds no competing engine.
The corrective commit is the commit introducing this ledger.

- **HTTP-EVIDENCE-01:** non-200, oversized and interrupted HTTP responses lost
  body/status evidence. The shared bounded reader now retains explicit complete
  bytes or a bounded prefix and records the correct hash scope. Initial and
  refetch failures remain FAILED_OR_INCOMPLETE with no verifier result.
- **HTTP-REDIRECT-01:** model-client redirects could request an unapproved second
  destination. The native urllib redirect handler refuses redirects; an in-memory
  transport confirms exactly one request. A positive control without the handler
  demonstrably follows the second destination, so the test can detect removal.
- **VERIFIER-JOURNAL-01:** rejected or interrupted native verifier attempts were
  missing from the counter and checkpoint. Submitted contract/hash and attempt
  count are saved before execution; rejected result or exception remains durable.
- **HTTP-TIME-01:** the successor helper labeled the request-start instant as
  `received_at`. It now records separate start/completion instants, including on
  timeout; two clock-controlled tests detect the old behavior. Historical
  envelopes remain unchanged and are not given corrected timestamps.

The original exact live workflows are archived as
[`original-uncertain-workflow-v0.1.yml`](original-uncertain-workflow-v0.1.yml)
(SHA-256 `bd3bb3cc5615851f0187e2f377f8770905b4a0b3501b73c027821fb7f9b41dba`)
and [`original-live-workflow-v0.1.yml`](original-live-workflow-v0.1.yml)
(SHA-256 `8b4a7afcfe60b4e2b4e652e01e4969d325cf297f1dab7044273f2ee00f086540`).
Their original job names retain offline invariants. Maintenance pushes no longer
repeat completed scored trials. A live successor needs a separate prospective
registration, identity and output location. The original results and source
commits remain the authority for the old trials, not this maintenance harness.

Verification: the three focused modules pass **44 tests**. They exercise real
native verifiers and native redirect handling using controlled source/model
fixtures; they are not independent model or human evidence. Required protected
checks, exact-head substantive review and branch authority remain separate.

## Native framing correction after substantive review

**HTTP-FRAMING-01**, [review comment 4458991461](https://github.com/n0tf0und0ut/Project-FAR/pull/608#discussion_r4458991461), thread `PRRT_kwDOTH_vCM6zR3E6`, reviewed exact head `562eb24f007601c0e6a0f9ffb48f953ab8c68338`: native `HTTPResponse.read(amt)` can return a syntactically valid prefix at premature EOF without raising `IncompleteRead`. The old helper treated the prefix as a complete body, permitting model action acceptance and source-backed invariant verification.

The corrective commit introducing this section validates declared Content-Length independently and rejects duplicate, malformed, ambiguous or unsupported transfer framing. For native chunked responses, a bounded observer checks chunk separators and the terminating trailer section while retaining the decoded prefix. Native positive controls demonstrate that the unguarded standard library accepts both a short Content-Length body and an unterminated trailer; regression tests reject both. Complete Content-Length and chunked controls pass. A real intake/verifier integration test rejects the short first source before freezing or verification; no proof aggregate is produced.

Verification: **51 focused tests pass**, including seven new native framing and investigation regressions. Retained incomplete bytes carry `retained_prefix`, never `complete_body`. Original frozen observations, archives and workflow source bindings remain byte-identical. This changes the maintenance harness only and does not retroactively certify historical HTTP framing.
