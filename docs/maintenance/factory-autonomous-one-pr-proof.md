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

## Frozen 7B retry after the 1.5B negative result

[Protected-main run 43348516108](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/43348516108) was a real queue-claimed Qwen2.5-Coder 1.5B attempt. The model returned the unchanged defective guard; no patch or PR was produced. This negative result and its raw artifacts are retained independently in issue #629.

The next, separately reviewed trial uses the **7B Q4_K_M coder** at its full Ollama manifest SHA-256 `dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364`. The job checks the exact 64-character model digest from the local Ollama API before model inference; a tag alone cannot attest the model. The source-bound task, four-test original oracle, three-test preservation oracle, and Docker grader remain unchanged. No more attempts are authorized by the original frozen 1.5B experiment; this is an explicit new worker configuration.

The workflow's default `GITHUB_TOKEN` now has read-only contents and pull-request permissions. Autonomous PR publishing requires a separate, explicitly configured `FAR_FACTORY_PUBLISH_TOKEN` with appropriate write authority. GitHub's default workflow token is not substituted because its PR-created checks may require manual approval and therefore fail the fully unattended protected-delivery requirement. An absent or invalid independent publishing token is a genuine external blocker, never evidence of model failure or grounds for protection bypass. Any generated PR still requires independent exact-head review and all required protected checks before protected merge.

**Assurance boundary:** The 7B coding model may still fail the frozen acceptance oracle, time out, or exhaust hosted compute. A merged workflow change, model digest match or green local mocked test is not evidence of successful autonomous code generation. Preserve original raw failures and do not imply completion before a real generated PR is independently merged.
