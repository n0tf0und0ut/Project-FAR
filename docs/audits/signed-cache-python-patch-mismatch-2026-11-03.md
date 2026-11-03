# Signed cross-runner cache Python mismatch

Status: Research operational defect record; no scientific claim promotion.

Root cause `SC-PY-001`: `far_validation/engine.py` includes the exact
`platform.python_version()` in each cache key, while the three assurance jobs
requested floating `3.12`. Different hosted runner caches can resolve different
patch releases. Keeping exact runtime binding is correct; floating job selection
violated the prerequisite for transferring the cache.

On PR #615 head `ffc7916430d91f5e132838764b87a1e1f0502210`,
[producer job 126101141637](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41688674632/job/126101141637)
selected CPython **3.12.15**, while
[consumer job 126102020116](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41688674632/job/126102020116)
selected **3.12.16**. Artifact transport digest validation succeeded; the consumer
then emitted `signed cross-runner cache misses: ['bootstrap.manifest']`.
This reproduces the same failure mechanism reported in #616, with patch order reversed.

Correction: select exact `3.12.16` for producer, consumer and merge-authority.
The assurance lock is updated to the actual workflow SHA-256,
`26df5e427d2d8865589fc51f621e4bce2917babdcb800db8c9d6aa3f588ad7f9`;
the old protected pin was
`2a2633bc53efa9188e8b62700d74b5fc3c8415f652974022044aa50d4f20f39a`.
No cache key, signature validation, check or oracle is weakened.

`tests/test_signed_cache_runtime_binding.py` checks that the three jobs select
one exact patch release. Its executed signed-cache experiment uses the unchanged
engine and a temporary check: a simulated 3.12.15 producer followed by 3.12.16
misses; a second 3.12.16 consumer hits and verifies its signature. This is a local
regression test, not a successful hosted run of the new workflow.

## Authorization preparation

Unsigned canonical payload:
[`PR-617-signed-cache-python.json`](../../validation/repin-requests/PR-617-signed-cache-python.json).
Prepared by the current canonical `repin_signature.py prepare` helper against
protected main `c7456b469f9dfe88b92d0fc7a211e5c9ed64de61`. It binds the current
repository name `n0tf0und0ut/Project-FAR`, immutable repository ID 1283452680,
PR #617 and the exact workflow transition. The procedure's historical
`notfoundout` spelling is not substituted for current repository identity.

Only the owner may sign these exact bytes with the pinned FAR repin key after
comparing the current App-authored transition. A signature remains absent; the
consumption ledger is unchanged. Preparation does not authorize the change.
After signature return, use `repin_signature.py bundle` to verify and append;
required hosted and independent final-head review gates remain separate.

No merge or auto-merge is authorized in this convergence assignment.
