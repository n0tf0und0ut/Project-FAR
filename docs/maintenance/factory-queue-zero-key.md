# Queue-bound genuine local-model execution — Research observation

Status: **Research / unpromoted**, excluded from `FAR-FACTORY-SELF-EVAL-001`.

## Question and minimum intervention

Can a `tools/software_factory.py` **real SQLite lease** dispatch the repository's **existing** pinned Ollama/Qwen coding worker and retain a truthful, source-exact attempt record? This is the narrow missing dispatch boundary identified after protected PR #668. It does **not** demonstrate PR creation, independently verified agent authorship, authenticated identity, or protected delivery. All original governance, review checks, and no-merge exceptions remain controlling.

`tools/factory_queue_zero_key.py` reuses, without modifying, `tools/factory_zero_key_smoke.py` (which invokes one real Qwen request and grades code inside a bounded Docker container). The new bridge validates exact frozen work-order and model-manifest identity *before* leasing, calls the model runner once, writes a receipt and source hashes, then records `Factory.fail` with either the explicit failed model outcome or **"patch proposal has no PR"**. Even a syntactically valid patch that passes visible tests never advances the factory's `build` stage. This deliberately prevents an untrusted model response or mocked test from masquerading as a delivered PR.

Research candidate `FAR-MAINT-003` is a distinct attempt using protected base `5253a45ac7f5bfbda1278cf3b8fbf4b9b22136f8`, source Git blob `3217647b5ca09ed40ab79a849952aa29f7c033ab`, issue #629, and a bounded change to `tools/software_factory.py`. The original bug: `Factory.fail` compares `max_attempts < 1` before verifying it is a strict integer. `None`, string, list and dict raise uncontrolled `TypeError`; `True` is accepted as `1` and consumes the lease, violating the input contract. A holdout test checks rejection without lease consumption and positive ordinary integer retry behavior; it is frozen as plain text, not shown in the model prompt. Its author is the initiating coordinator, so it is not an independently authored or external oracle.

## Execution and evidence

The named same-repository development branch `research/factory-queue-zero-key-20261112` alone can start the model-attempt job from PR CI. The workflow has `contents: read`, no token persistence and no code-pushing permission, uses the repository's pinned local Ollama model and existing Docker grader, and retains original red-baseline stdout/stderr plus model response, patch when accepted, before/after Docker outputs and hashes, and the queue snapshot. **The workflow's successful completion means an attempt was observed, not that the model generated a valid patch or that a delivery occurred.** It never receives a GitHub write token or creates a branch or PR; no model code executes on the GitHub Actions host.

Offline controls:

```sh
python -m unittest tests.test_factory_queue_zero_key -v
python -m py_compile tools/factory_queue_zero_key.py
```

Hosted experimental invocation (existing workflow controls authorization):

```sh
python -m tools.factory_queue_zero_key \
  --db "$RUNNER_TEMP/far003_queue.sqlite" \
  --order research/factory-evaluation/queue-zero-key-work-order-far-003-v1.json \
  --repository "$GITHUB_WORKSPACE" \
  --task-file research/factory-evaluation/zero-key-worker-smoke-far-003-v1.json \
  --output "$RUNNER_TEMP/far003_model_attempt"
```

The SQLite database and raw lease capability remain outside the repository and out of uploaded public artifacts. The receipt hashes the lease token but does not expose it. An attempt after a false source/repo identity rejects before model dispatch. After three attempts, existing queue semantics prevent indefinite retry. CI evidence must be retrieved from the actual run and inspected; presence of this workflow/code alone is **not evidence that an agent ran**.

## Unchanged blockers for full factory closure

A source-exact model patch is only an **advisory proposal**. To close issue #629's actual one-PR delivery obligation, a trusted publisher must turn a valid generated patch into a PR without passing GitHub credentials to the model; independent exact-head tests and review must follow; only authorized protected GitHub merge may be reconciled. This bridge makes one worker execution reachable from a real queue, but intentionally does not fabricate any of those later stages. The current suite tests queue correctness with injected callable responses; those tests are **not** a model execution or an independence attestation. The live model job and its raw artifact are the only evidence of actual provider invocation.
