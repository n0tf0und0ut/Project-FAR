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
