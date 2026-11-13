# One constrained model repair: source-bound feasibility only

**Status:** Research, unpromoted. Not part of `FAR-FACTORY-SELF-EVAL-001` and not evidence of general agent performance.

## Question

The first two real queue-bound runs on PR #669 invoked the pinned Qwen2.5-Coder 1.5B model, but generated no usable patch. Run 43331387909 returned malformed Markdown-wrapped diff JSON after consuming its entire 1,800-token output budget; run 43331723201 hit the 180-second model request timeout. Both retained original negative results. We now test whether the *same model and frozen defect* can produce a one-line edit when presented only the relevant AST-extracted method rather than the complete source and asked to return one JSON `line` string instead of a long diff.

## Exact scope and source

- **Task:** `FAR-MAINT-003`: reject non-integer `max_attempts` in `Factory.fail`, including `bool` and containers, without consuming a running queue lease.
- **Original source:** protected main `5253a45ac7f5bfbda1278cf3b8fbf4b9b22136f8`, Git blob `3217647b5ca09ed40ab79a849952aa29f7c033ab` for `tools/software_factory.py`.
- **Immutable manifest:** `research/factory-evaluation/zero-key-worker-smoke-far-003-v1.json`, SHA-256 `52d2d22c5fb0f708ace2a331e91a8d0558b86b41132b19679f8c7bd2d86ff308`.
- **Frozen acceptance oracle:** `research/factory-evaluation/holdout-far-003.py.txt`, SHA-256 `45b73d2b4a0f2092ae82e79e5c137aaecd0c5e8537f2820b1e0c96819f61c67e`; this oracle already failed baseline with 1 failure and 5 errors. It is **not shown to the model**. It was authored by the coordinator, so is not externally independent.

## Mechanism

`tools/factory_queue_targeted_model.py` reuses the existing real transactional `Factory` lease and retry history by calling `tools.factory_queue_zero_key.run()` with `tools.factory_targeted_model_smoke.run` as its real (not mocked) worker. Before invoking Ollama, the worker checks the original base commit and source blob, exact frozen task and holdout SHA, pinned model digest, and immutable Docker image identity. It runs the public 17-test baseline inside the existing no-network, read-only, unprivileged Docker grader. A Python AST locates the `Factory.fail` guard and passes only its containing function and task objective to the local model. The model is constrained to JSON mode with a single `line` property and a 180-token output budget. Its bounded raw transport, raw generated content, and available generation metrics are persisted **before** output validation so malformed responses remain independently inspectable as negative evidence. One line is then replaced, parsed without execution, and the one-file diff is retained.

After model generation the identical Docker grader executes public tests and the withheld frozen oracle; only all-pass may yield `MODEL_PATCH_PASSED_VISIBLE_AND_FROZEN_TESTS_NOT_PR_DELIVERY`. No generated code executes in the Actions host interpreter. A success is a **source-bound patch proposal only**. The queue records a failed build-stage attempt because no GitHub PR is published or reviewed by this runner. Subsequent publication requires a separate independently reviewed PR and its actual protected GitHub checks. No GitHub write token is used in the worker job.

## Tests and false-success boundaries

Run `python -m unittest tests.test_factory_targeted_model_smoke -v`. It checks AST-scoped source mutation, preserved surrounding bytes, syntax failure, multiline/replacement injection rejection, strict JSON response and model identity, frozen task/holdout mismatch rejection, and actual SQLite queue transition behavior with a **mock** worker that cannot complete a build. Passing these tests proves source and dispatch contracts only; the hosted model job and raw artifacts are required for actual generation evidence.

## Limits

- Task-specific line-level source transformation is **not** general repository editing capability.
- JSON mode and a short prompt may improve output reliability, but one success or failure cannot establish model capability distributions or costs.
- The same Actions runner performs model execution and bounded Docker grading; this is not externally attested I2 isolation or an independent trusted check collector.
- The frozen oracle is coordinator-authored. Protecting it from a prompt does not make its design independently specified.
- The job is research-only, branch-scoped, read-only, and excludes the registered eight-task randomized comparative study.
- The factory build stage deliberately does not advance merely because the model submitted a syntactically valid patch or tests passed; real PR, independent exact-head review, and protected merge remain separate.

## Subsequent source-bound refinement after the first hosted negative result

The first live targeted run on head `05caf79bf7cc7e600f960b155ef5494ddf5e19e0` (run `43336028005`) completed model generation in 11.083 seconds with 473 input and 27 output tokens, but returned the original guard (without eight-space indentation). The parser correctly rejected it as **not a single Python guard replacement**, leaving the queue at `build/queued`. This is a negative observation, not a valid model repair. Codex review on that head found that malformed model content would not be retained. The revised probe now persists bounded raw transport, raw generated content, and available metrics *before* parsing. It accepts an unindented `if` line only by restoring the AST-derived known indentation; this does not alter the generated expression, and an unchanged guard remains rejected. The model prompt explicitly emphasizes the frozen noninteger and boolean counterexamples; this is a new attempt and must not be presented as a repeat of the earlier one.
