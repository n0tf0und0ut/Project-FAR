# Validator Assurance Hardening

## Status

This package is the second-stage hardening layer for the unified Project FAR validation platform. It carries the unified validator from PR #231 onto `main` and adds executable controls for the seven assurance gaps previously left open.

## Assurance layers

### Runtime undeclared-dependency tracing

Every registered command check can execute under Linux `strace`. The trace records repository-local reads, writes, child executables, and network attempts. The result is compared against the check's declared inputs and outputs plus the frozen runtime policy.

A traced check fails with `FAR-VAL-TRACE-001` when it reads an undeclared repository path, writes outside an allowed output, launches an undeclared executable, or attempts network access under the deny policy. CI requires the trace backend; an unavailable backend is not treated as a pass.

The trace claim is bounded to operating-system-visible system calls made by the command process tree on the Linux runner. It does not claim visibility into hardware, kernel compromise, or activity outside the traced process tree.

### Independent oracle validation

`far_validation.oracle` independently parses every discovered legacy checker and every manifest command entrypoint using only the Python standard library. It checks:

- manifest coverage and stable failure-code registration;
- nontrivial control flow;
- visible failure paths;
- repository-artifact or subprocess observation;
- rejection of empty, trivial-success, no-failure-path, and syntax-corrupted hostile checker mutations.

This is an independent implementation oracle for checker structure and enforcement identity. It is not an independent scientific re-proof of every domain-specific proposition checked by those scripts.

### Automated weakening detection

`far_validation.weakening` compares changed tests and validators with an explicit Git base. It rejects deleted tests, removed test functions, reduced assertions or failure paths, new skips, new unreachable statements, new conditional quiet exits in an existing test, fixture, or checker `main`, major branch loss, and large unexplained AST contraction. Any exception requires a versioned waiver bound to the exact base commit and a nonempty justification.

These rules are syntactic. A change can still disable a test through a called helper, through data, or through a runtime patch, so the detector catches mistakes, not an adversary. Files under the assurance lock are protected against both, because changing them requires an owner-signed repin.

### Signed cross-runner cache trust

Cache entries and validation certificates use canonical JSON plus HMAC-SHA256 envelopes. Trust is bound to a trust domain and key identifier. CI requires a signing key; unsigned, wrong-domain, wrong-key, and tampered entries are rejected.

The current CI workflow demonstrates **cross-runner cache transport and reuse**, not independent producer provenance. The producer creates an ephemeral HMAC key and packages that **same verification/signing key** in the cache archive. It also writes an SHA-256 sidecar digest. The consumer obtains both from GitHub Actions artifacts, checks the digest, extracts the key, and requires an HMAC-signed cache hit. Neither the packaged HMAC nor a digest supplied alongside the data authenticates its origin against an actor capable of replacing both artifact and digest; the artifact service is a separate assumed trust boundary. **No GitHub Sigstore attestation is issued or verified by this workflow.** A future independently authenticated provenance control would need a trusted producer identity and an actual consumer verification step. Persistent cache reuse across separate runs is not demonstrated by this ephemeral-key job; the separate persistent-key mode requires its own authorized trust boundary.

### Mutation and hostile-acceptance campaign

`far_validation.mutations` runs every registered mutation family against every discovered legacy checker and the shared assurance components. The campaign covers:

- four hostile source mutations per checker;
- cache payload, signature, domain, key, and kind tampering;
- certificate commit, tree, required-check, and unsigned-content tampering;
- undeclared read, write, executable, and network activity;
- synthetic test deletion and assertion weakening;
- exhaustive abstract state-space validation.

“Complete” means complete over the versioned mutation registry and every checker discovered by the frozen discovery rule. It does not mean every logically conceivable implementation fault has been enumerated.

### Formal verification

Two formal layers are included:

1. `mechanization/lean/ValidationEngine.lean` machine-checks dependency safety, blocking soundness, successful-run soundness, and exact commit/tree certificate binding.
2. `far_validation.formal_model` exhaustively enumerates every forward-edge dependency DAG through four checks, every Boolean check-outcome assignment, and hostile attestation mutations.

The Lean file proves the abstract assurance model. The Python model checker exhaustively checks `far_validation.formal_model.simulate`, a separate Python abstraction of the scheduler; it does not import or execute `ValidationEngine.run`, so agreement between that abstraction and the executable engine is not checked by either layer. This package does not claim a machine-checked refinement proof connecting the Python implementation to the Lean model or to that abstraction.

### Merge authority and merge queue

The `Validator Assurance` workflow runs on pull requests, pushes to `main`, workflow dispatch, and the GitHub `merge_group` event. The `merge-authority` job issues a signed certificate bound to the exact checked commit and Git tree and requires all five assurance evidence artifacts.

`tools/configure_validation_protection.py` applied strict branch protection requiring the `merge-authority` status check, an up-to-date branch, pull requests, conversation resolution, and no force pushes or branch deletion. It is superseded: it would now drop the App-bound `protected-repin-gate` required check. It makes no change and exits non-zero, because a locked file cannot be removed through the repin gate. The owner changes protection by hand, following `docs/governance/protected-repin-procedure.md`. `tools/check_validation_protection.py --gate-app-id <App ID>` independently reads the GitHub control plane. It fails unless every required setting matches, including both required checks bound to their Apps: `merge-authority` to GitHub Actions and `protected-repin-gate` to the owner's App. A successful read-back is the evidence of live enforcement.

Control-plane closure on 2026-09-04: the repository is public and personal-account owned. After PR #467 merged, a one-shot bootstrap workflow used the repository-scoped `FAR_GITHUB_ADMIN_TOKEN` Actions secret to run the governed configurator and then the independent fail-closed read-back. Both steps succeeded. GitHub branch metadata reports `main` as protected with `merge-authority` required at enforcement level `everyone`, and the read-back returned `control_plane_enforced: true` with no errors. The exact Accepted closure record is `docs/governance/canonical-branch-protection-closure-2026-09-04.md`.

Security retirement completed on 2026-09-06 by irreversible GitHub issuer revocation. Both repository-secret deletion identities returned 403, so the encrypted entry remains explicitly recorded as invalid metadata. The separately pinned credential received revocation HTTP 202 and authentication HTTP 401; an independent read-only rerun confirmed the same fingerprint still receives HTTP 401. Both privileged consumers remain disabled, the complete pre-revocation policy matched the earlier capture, and subsequent independent branch reads retain enforced protection. The one-shot is removed by protected cleanup. Exact receipts, failed attempts, review scope, and promotion evidence are in `docs/governance/privileged-token-retirement-2026-09-05.md`.

Native GitHub merge queues remain unavailable while the repository is personal-account owned. This is not a branch-protection failure. The validator workflow is merge-group compatible and becomes queue-ready after transfer to an eligible organization.

The nested full-health runner gives the complete canonical test suite the same 900-second budget recorded for `tests.canonical` in the validation manifest. Individual health checks retain their shorter default; explicit `--timeout` and `PROJECT_FAR_HEALTH_TIMEOUT` overrides still apply to every subprocess. This corrects the 120-second nested-suite timeout observed in exact-head run [34010171919](https://github.com/notfoundout/Project-FAR/actions/runs/34010171919) while preserving required checks and timeout failures.

## Credential inventory

- `FAR_VALIDATION_CACHE_SIGNING_KEY`: persistent HMAC secret for cross-runner cache and certificate trust.
- `FAR_GITHUB_ADMIN_TOKEN`: revoked obsolete administrator token; its undeletable encrypted entry is invalid metadata, not a usable credential. It must not be recreated as a long-lived Actions secret. Future protection changes require an ephemeral, externally controlled administrator credential and a separately reviewed fail-closed procedure that does not execute mutable repository code.

The cross-runner cache test intentionally places its **ephemeral HMAC key in an Actions artifact** with the cached data; that key is not a protected credential. The workflow does not intentionally export persistent credentials or privileged GitHub tokens to artifacts or logs. The bundled ephemeral key must not be described as an independently secret authentication key.

## Commands

```bash
make validate-trace
make validate-oracle
make validate-weakening
make validate-mutations
make validate-formal
make validate-assurance
```

## Claim boundary

This package substantially closes the registered assurance gaps. It does not establish literal impossibility of validator defects, immunity to compromised runners or secrets, independent scientific validation of Project FAR's research claims, or a full refinement proof of the Python engine.

## Exact PR head assurance

The protected `merge-authority` job validates GitHub's proposed merge commit. The additive `.github/workflows/exact-head-assurance.yml` also runs the same complete traced profile, independent oracle, weakening audit, Lean proof, exhaustive model, registered mutations, and signed certificate checks with checkout explicitly bound to the PR head SHA. It uses only a read-only short-lived Actions token and verifies the actual commit/tree. Both runs are required by the EFR promotion record; live main protection continues to require the existing `merge-authority` context. The exact-head job also runs on canonical main pushes. It does not configure repository protection or handle administrator credentials.

## Bounded claim-ownership composition correction — November 8, 2026

Evidence class: **Implementation**, internal regression verification. Source base: `ea834906b3880c144d51f300268993bffccf52fc`. The governance checker remains a finite clause/status heuristic; this correction does not establish arbitrary-English coverage or source truth.

| Root cause and original review | Violated invariant and correction |
| --- | --- |
| **GOV-623-STATUS-CHAIN-01** — [4507130384](https://github.com/n0tf0und0ut/Project-FAR/pull/623#discussion_r4507130384), thread `PRRT_kwDOTH_vCM61Czqs`, reviewed `fdf2c6b2e7ae72a25e8afc007a6561758045eb21` | A pair member's complete local scalar status must be consumed before finding pair coordination or shared suffixes. The earlier left-only extra regex recognized fewer atoms than `STATUS_VALUE`; the CLI still rejected a genuinely conditional pair when the left member contained `not established and not yet confirmed` or `not established and cannot be confirmed`. Both members now consume coordinated chains from the same existing scalar-atom grammar. Their local negation stays local; genuine pair-level conditions and prohibitions remain shared. The narrower left-only exception is removed. |
| **GOV-623-PREDICATE-OWNERSHIP-01** — [4507130375](https://github.com/n0tf0und0ut/Project-FAR/pull/623#discussion_r4507130375), thread `PRRT_kwDOTH_vCM61Czql`, and [4507130380](https://github.com/n0tf0und0ut/Project-FAR/pull/623#discussion_r4507130380), thread `PRRT_kwDOTH_vCM61Czqp`, same reviewed head | Independent prose assertions must not donate negation across a structured claim boundary; a genuine shared pair predicate must retain it. Prefix, suffix and pair-predicate regexes used inconsistent finite verb/subject lists. The CLI falsely accepted preceding `Priority won't be established` and following `neither priority nor uniqueness is established`, while falsely rejecting an explicit pair ending `aren't confirmed`, `weren't validated` or `shouldn't be asserted`. One finite predicate vocabulary now serves all three paths, including contracted equivalents under the already-recognized `n't` negation. Both prose directions share the same topic/neither–nor subject grammar. |

Before source correction, seven of eight new actual-CLI cases failed, and an independently specified **7,054-case** status-chain/prose composition oracle found **1,148** exact-topic mismatches. The test expectations are declared by finite templates rather than imported production regexes. After correction, the complete focused governance, behavioral and cache-provenance suites pass **60 tests**, including every retained original regression and all eight original behavioral source-mutant contrasts. The two new methods are `test_existing_status_and_predicate_vocabulary_composes_at_claim_boundaries` and `test_status_chain_and_prose_ownership_composition_oracle`. The changed checker's registered rule-deletion campaign detects **5/5** deletions; the actual governance CLI and diff-whitespace check pass.

These finite counts describe declared composition coverage, not a population detection rate or proof that no other heuristic defect exists. No frozen evidence, accepted theory, protected workflow, signature or gate is changed. Independent review of the final published head, current-main integration and all protected checks remain separate merge obligations.
