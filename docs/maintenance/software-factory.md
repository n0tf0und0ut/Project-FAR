# Software factory: operational Research prototype

Status: **Research / unpromoted**. This is engineering process infrastructure, not accepted FAR theory, a scientific experiment, a deployment claim, or evidence of reliable autonomous code production.

## Objective

Provide a persistent, deterministic work-order queue that can coordinate external coding workers without confusing worker statements with independently verified GitHub evidence. Design supports multiple repositories and bounded task dependency graphs. It deliberately does not bypass existing protected-main or PR review gates.

## Mechanisms

- A work order pins a repository and a 40-character source commit; each task has a testable objective, acceptance criteria, and acyclic dependencies.
- SQLite transactions serialize claims. An expiring, random lease token bounds each worker attempt; a crashed worker's lease can be reclaimed. Failed attempts stop after three, rather than spin forever.
- Per-task stages: build -> test -> review -> `awaiting_protected_merge`. Task dependencies remain blocked until the read-only GitHub delivery reconciler confirms a merged PR and verifies that its merge commit is an ancestor of current main. The program never merges a PR.
- A build records a PR number and exact head; test and review declarations must reference the exact same SHA. The review worker cannot claim to be its own reviewer. Every submitted declaration is hashed and retained with the worker's identity and time.
- Worker reports are **untrusted assertions**. A clean claim from this store cannot satisfy GitHub's `merge-authority`, `protected-repin-gate` or `pr-review-convergence-observation` requirements. Existing `tools/pr_review_convergence.py` and hosted protected CI retain authority. No source writes, branch updates, PR merges, or credentials are involved in this prototype.

## Usage

From repository root (Python >=3.11):

```bash
python -m unittest discover -s tests -p test_software_factory.py
python tools/software_factory.py --db /tmp/far-factory.sqlite submit examples/software-factory/work-order.json
python tools/software_factory.py --db /tmp/far-factory.sqlite claim pilot builder
python tools/software_factory.py --db /tmp/far-factory.sqlite status pilot
```

A worker records one stage's JSON evidence with `record ORDER TASK LEASE_TOKEN evidence.json`. Failed worker attempts use `fail ORDER TASK LEASE_TOKEN 'reason'`. Once the normal GitHub protected merge is complete, execute `reconcile-delivery ORDER TASK`; the CLI reads GitHub using `GITHUB_TOKEN` when supplied, otherwise unauthenticated public API access. Store database files outside Git; never commit tokens or raw potentially sensitive worker logs.

## Unimplemented integration boundaries

1. An isolated coding-worker adapter (OpenHands SDK, Codex CLI, or equivalent), with separate credentials and least-privilege worktrees.
2. A live GitHub evidence collector binding CI run/check source identity, the independent substantive review, required protected contexts and merge-authority decisions to the exact PR head.
3. Historical independent review and protected-check provenance verification. The current delivery reconciler observes the merged state and main ancestry only; it does not prove that no admin bypass occurred.
4. A bounded benchmark comparing successful, independently verified end-to-end PR delivery per cost and time against the existing manual process; record failures as well as successes.

Those missing parts are *not* implied by passing unit tests. Production autonomy and performance advantage remain unknown.

## Security and adversarial controls

The program validates input schemas, rejects unknown fields, uses SQLite transactions and unique task identifiers, fails closed on invalid dependency graphs, enforces exact SHA bindings, prevents claimed self-review, rejects expired or stale leases, and bounds retries. It does **not** authenticate GitHub identities or check the truth of worker-submitted evidence. Its database is operator-controlled mutable state, not cryptographically frozen research evidence.

## Lease and repository identity review corrections

Lease expiration is evaluated after SQLite acquires the `BEGIN IMMEDIATE` writer lock for claim, record, and failure transitions. An expired worker cannot submit evidence merely because its request arrived before a contended database write. Tests exercise the lock-wait boundary with a second connection and validate failure without committing stage evidence.

GitHub's canonical owner/repository full name is compared case-insensitively with the registered work order name when observing protected merge delivery. A different repository continues to fail closed. This is an identity-string comparison correction, not authentication of worker-reported review evidence or a replacement for protected GitHub checks.

## External GitHub observation and SQLite concurrency

Delivery reconciliation is deliberately separated into a read-only GitHub observation
and a short SQLite writer transaction. The observer verifies the recorded PR head,
canonical repository, main target, merged commit, current main, and ancestry **without
holding the SQLite writer lock**. Only after those observations succeed does it
acquire `BEGIN IMMEDIATE`, recheck the task's `awaiting_protected_merge` state
and original build evidence, and append one delivery receipt. If another observer
already delivered the task or the recorded build state changed, the stale observer
fails without appending a second delivery receipt. This does not authenticate
historical required-check provenance or grant merge permission.

The defect-detecting test `test_reconcile_delivery_does_not_block_unrelated_worker_claim`
was added to an otherwise unchanged implementation and reproduced
`sqlite3.OperationalError: database is locked` in hosted CI because an artificial
GitHub delay held the writer lock. The implementation now releases that lock during
network observation. The independent adversarial test
`test_two_concurrent_merge_observers_commit_delivery_once` verifies that concurrent
observations cannot both commit delivery. These deterministic controls establish
the narrow lock and state-transition properties only, not distributed exactly-once
execution across a mutable GitHub service or worker authenticity.

## Dependency graph depth

Work-order dependency validation now uses an iterative topological check rather
than recursive traversal. A valid chain of 1,250 distinct tasks must pass regardless
of Python's default recursion limit, and adding a closing back-edge must produce
a `FactoryError("cyclic dependency")`. The regression
`test_deep_dependency_dag_preserves_validity_and_detects_cycles` checks both
cases. This corrects a valid-work-order rejection; it does not imply a global
payload-size, task-count, or storage-consumption limit. Production ingestion from
untrusted clients would require separately justified resource ceilings.
