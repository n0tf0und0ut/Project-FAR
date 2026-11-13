# One autonomous source-code PR proof — Research

Status: **Research / unpromoted / one frozen engineering task**.

## Purpose

Check a strictly limited missing factory boundary without replacing governance:
GitHub Actions on newly merged trusted main submits a work order to the actual
SQLite `Factory`, claims a build lease, invokes the pinned *real* local Qwen
worker, constructs a one-line source patch, grades baseline/candidate in the
existing bounded no-network Docker grader, then uses **a separate trusted
publisher step** to open a PR if and only if the model patch passes the frozen
oracle and the existing factory regression suite. The model never receives a
repository write credential and no model-generated Python runs on the Actions
host. The trusted publisher gets a GitHub token only after model evaluation.

## Frozen independent-from-model oracle

`research/factory-evaluation/claim-parameter-holdout.py.txt`, SHA-256
`73a34c32a4ea99576fd2ee65121406eae57406528a1bdc3f3b13822b2877b0b4`.
The oracle was written and reproduced *before* any worker call. The user task
is to reject invalid `Factory.claim` lease parameter types (including bool)
without consuming a lease. The current preimage fails with six failures and
eight errors across four test methods. The original oracle is never included
in the model's chat prompt; its hash is validated before use. It is authored
by this coordinator, not independently by an external party.

A separate preservation oracle was introduced after independent exact-head
Codex review exposed an untested regression possibility: a model could remove
preexisting worker-name validation or accept nonpositive/oversized durations
while passing the first oracle. The preservation oracle is frozen at
`research/factory-evaluation/claim-preservation-oracle.py.txt`, SHA-256
`104f24eeaede44a6f25bf16e2910c2512a7c21150646c1ebd66f06d88901cb51`.
It passes the original source (three methods) and fails the reviewer's concrete
faulty replacement (11 failures). Both frozen oracles must pass the candidate.
This second oracle was also created **before** any model attempt in this new
workstream and is not shown to the coding model.

## Exact execution contract

1. Only a protected-main push containing the workflow file starts this one-shot job.
2. Pin source Git commit and source blob, freeze work order and unchanged oracle SHA.
3. Record the queue's authentic build lease before any Ollama query.
4. Preserve raw bounded model transport/content and generation counters before parsing.
5. Enforce AST-selected, single-line mutation of `Factory.claim`, and no other source edits.
6. Grade the original frozen test (expected red), both candidate frozen test suites (must green), and existing factory regression suite in Docker with no network/capabilities/host secrets.
7. If anything fails, record failure in the durable queue and upload raw evidence. No PR.
8. Only after pass, the trusted publisher independently verifies raw source/patch identity, stages model-produced source and both frozen test files, commits and pushes a distinct branch, opens a normal PR, and records its exact head in the factory build stage.
9. New head must independently pass protected CI, exact-head Codex review and all required gates before any authorized merge. Publishing is not delivery.

An Actions `GITHUB_TOKEN`-authored PR may not trigger ordinary PR checks because
of GitHub's anti-recursion rule; a separately authorized, installed
`FAR_FACTORY_PUBLISH_TOKEN` secret is preferred. If absent, the default token
may only establish publishing feasibility, **not** autonomous protected
completion. This limitation must be reported from actual GitHub evidence, not
explained away. No auto-merge, force-push, or protected bypass is enabled.

No claims of agent general reliability, commercial value, or a performance
advantage follow from a single small task. Worker identity is local-provider
reported, and Docker is bounded rather than full host isolation.


