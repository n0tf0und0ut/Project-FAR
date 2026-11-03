# MIT weight-space programming: source and tensor audit

Status: Research. Audit date: 2026-11-03. This audit performs source retrieval, arithmetic reconstruction and exact tensor-diff replay. **It executes zero neural-model inference runs.** It supplies no FAR performance observations and makes no production recommendation.

## Finding and source identity

The November 2 authors' report is [Sparks of Weight-Space Programming](https://rikiyat.github.io/blog/weight-space-programming/) by Rikiya Takehi, Jayden Teoh, Alex Zhang and Omar Khattab, affiliated with MIT CSAIL. It is a research blog report; its own citation labels it a blog post. The primary evidence release is [RikiyaT/lm_understand-logs](https://github.com/RikiyaT/lm_understand-logs), inspected at immutable Git commit `4d09ba6d6a7e891dd8063974dfe81b3d78e3494f`.

Locally recomputed **46 benchmark-condition groups** from the original shard counts and per-problem correctness lists, including all released Qwen and Gemma conditions. All reconstructed counts, accuracy, cut share, mean token counts and unique-problem coverage matched their merged tables. This checks internal evidence consistency; it does not independently regrade every model answer or reexecute the evaluations. `mit-source-manifest.json` hashes 561 inspected source files and points to their immutable URLs. `verify_original_evidence.py` reproduces these calculations without executing author code.

## Exact model and intervention

Base: `Qwen/Qwen3.5-0.8B` at revision `2fc06364715b967f1860aea9cf38778875588b17`. Authors evaluated its text-only export, using unchanged `model.language_model.*` tensor names, 24 layers, residual width 1,024, MLP intermediate width 3,584, bfloat16 evaluation. The public base's single shard is named `model.safetensors-00001-of-00001.safetensors`.

Editor: `gpt-6-astra`, reasoning effort `max`, through Codex CLI with its own tools disabled. A separate CPU Python sandbox provided tensor inspection/editing plus budgeted remote generation and teacher-forced activation tools. Internet, gradients, backward passes, optimizers and iterative loss fitting were forbidden. Embedding/output/final-norm edits and whole-tensor scalar rescaling were rejected. This was iterative feedback-guided weight editing, not zero-feedback editing.

The final p50c change is, separately at layers 15 and 19,

`W' = W0 − 6 × outer(u, mask64 ⊙ (u @ W0))`.

Each `W` is `model.language_model.layers.{15,19}.mlp.down_proj.weight`, shape `[1024,3584]`. Layer-specific unit directions came from the mean late-token residual difference between four matched repetitive/productive contexts, at residual outputs 16 and 20. Selected columns were identified from original-model writer contrast. The exact 64 column indices per layer are recorded in `runs/p50c/work_notes/frozen_weights_manifest.json` and checked against the sparse diff in the local manifest. The scale 6 matters: this exceeds an orthogonal projection that merely removes the component once.

Touched coordinates: `2 × 64 × 1024 = 131,072`. Actual changed BF16 bit patterns: **130,188** (65,260 in layer 15 and 64,928 in layer 19); the remainder round back to their original values. Thus the headline "0.016%" is approximate. The fetched base safetensors header contains 873,438,784 entries including vision/MTP, or 752,393,024 under `model.language_model.*`. Actual changed fractions are respectively **0.0149052%** and **0.0173032%**. A percentage without its denominator obscures this distinction.

`replay_tensor_diff.py` independently fetched only the two exact immutable HTTP byte ranges, verified the base raw BF16 hashes, applied the published sparse replacement arrays with NumPy, and verified both evaluated edited hashes. It checked actual changed indices and column counts, plus equality everywhere else within these two tensors. It also fetched those two tensors from published edited checkpoint revision `d1671a178705bcab7644806d23c535517f35723b` and confirmed identical hashes. It did not compare every other tensor of that checkpoint.

| Tensor layer | Base raw BF16 SHA-256 | Rebuilt edited raw BF16 SHA-256 |
|---|---|---|
| 15 | `ef60d2c687bab19464dca9c8bfd7777e46ad226df0c9e25643b0bab04b5a1cca` | `82e2d733ea64feaeb4af93a1e065641d3df98b494a8b7576ef2f52e90fe2ee53` |
| 19 | `638eedeb701b94aa861f4438e615c07ec6c60ee703db1bfee2de577bb6498c3e` | `8ef3c61bc36af113ad58e89dbb0a4a14dcba5a45cb750c15ab515c82ddd12eb2` |

## Evaluation and directly reconstructed results

Editor practice pool: 7,469 GSM8K train problems, 7,275 MATH train problems and 714 AIME problems. The documented protocol withheld benchmark test inputs; the complete access-enforcing agent harness is not released. These public benchmarks do not exclude pretraining contamination. One counted pass could generate up to 512 sequences (paired "both" means up to 256 per arm) or teacher-force up to 1,024 texts; failed requests were not charged. The 50-pass run involved 69 requests, 158 turns, 80 Python executions and four conversations. Its reported 20.3 wall hours include 4.7 hours awaiting provider availability. It was not fifty single-example forward evaluations.

Held-out evaluation used vLLM, thinking enabled, problem plus a fixed boxed-answer instruction, temperature 0.6, top-p 0.95, top-k 20, presence penalty 1.5, seed 0 and 32,768 maximum new tokens. Mathematical grading used the last boxed answer with math-verify 0.9.0. MATH-500 used four samples per problem; GSM8K and IFEval two. IFEval used strict prompt-level checking on the answer after the thinking closure. Multiple outputs share problems and a fixed sampling setup; they are not four independent model-training seeds.

| Qwen condition | MATH-500 correct / 2,000 | Accuracy | Hit token limit | Mean generated tokens |
|---|---:|---:|---:|---:|
| Base | 158 | 7.900% | 93.000% | 30,868.4345 |
| p10c | 247 | 12.350% | 87.250% | 30,084.0215 |
| p25c | 282 | 14.100% | 86.350% | 29,658.5365 |
| p50c | 962 | 48.100% | 33.050% | 22,037.1475 |

The headline gain is **40.2 percentage points**, approximately 6.09 times the base accuracy. It is not 40.2% relative improvement. GSM8K changed from 13.836% to 67.096%; IFEval from 20.980% to 62.292%. The p10c/p25c/p50c curves compare different selected edits from different budgeted runs, not a clean randomized causal effect of extra editor compute alone.

The local audit also recomputed the released 1,152-row frozen practice confirmation CSV: 122→696 correct, 579 rescues, five regressions, of which 576 rescues were originally truncated. Aggregate accuracy on originally completed answers was unchanged. These are author-produced practice traces; their arithmetic is reproduced here, while their original large generated-text/activation files are not in the release.

## Mechanism, controls and causal limits

The evidence supports a localized intervention that sharply reduces a pathological repetitive-generation failure under the measured setup. The author logs include dose changes, individual-layer tests, matched productive/repetitive teacher-forced contexts, and one seeded orthogonal random-direction control norm-matched to a dense alpha-4 intervention. That control gained only 1.56 points with paired SE 3.52 points. It is useful specificity evidence but is not an exact sparsity/dose-matched control for the final sparse alpha-6 edit. Final edited correct practice answers still contained thousands of reasoning tokens. Whitespace degeneration, wrong answers, omitted boxes and truncation remained.

Both arms used fixed evaluation settings and actual parameter intervention, supporting a bounded causal effect of those edited weights on measured output distributions. The proposed underlying loop circuit is a mechanistic interpretation supported by probes and interventions, not an exhaustive causal circuit proof. Batching-dependent RNG is explicitly noted in the logs: only paired "both" practice passes should be treated as paired stochastic comparisons; separate calls with seed zero do not guarantee aligned random numbers.

The released benchmark comparison lacks optimized non-thinking, alternative sampling, interrupt/restart, prompting and inference-budget baselines. The pinned Qwen model card explicitly warns about thinking loops, recommends sampling adjustments and streaming interruption, and defaults this small model to non-thinking mode. Therefore superiority over the strongest simpler repair is **unestablished**. Earlier prompt trials are expressly omitted from the release, limiting any all-attempt success-rate claim.

## Negative results, replication and adoption

Gemma follow-up: `google/gemma-3-270m-it` @ `ac82b4e820549b854eebf28ce6dedaf9fdfa17b3`; 18 layers, width 640. Sampling was temperature 1, top-k 64, top-p .95, cap 8,192, no thinking mode. Its reported format-agnostic MATH-500 accuracy was 6.8% base, then 7.05%, 7.6%, 7.7%, 7.0% for 5/10/25/50-pass edits. Strict boxed grading instead gave 2.75% base and 3.55%, 3.1%, 3.75%, 2.6%. The 50-pass intervention increased cut frequency from 8.5% to 10.4%. No established broad capability gain follows; failure of these edits is not proof that no future edit could improve Gemma.

The published [edited HF checkpoint](https://huggingface.co/RikiyaT/Qwen3.5-0.8B-weight-space-programming) reports an external MATH-500 rerun: 51.0% over 2,000 edited outputs and 31.6% truncation, 43.4M generated tokens, 51 minutes on H200. The local audit recomputed its published per-problem labels as 1,020/2,000 correct. Its base comparison was only a 25-problem smoke (5/100 samples, 5.0%); it used a full multimodal release with language tensor hashes matched to the text export. This is a useful edited-checkpoint reproduction report, not a fully matched independent replication of the treatment effect or a FAR-run experiment. Reported runtime: vLLM 0.33.0, transformers 5.20.2, math-verify 0.9.0. Source config field `transformers_version` in the text config is 5.17.0; no complete lockfile for the original evaluation was identified. The agent harness and some graders/large intermediate artifacts are absent, so exact editor-trajectory reproduction needs reconstruction in addition to the released prompts and logs.

Decision: investigate and independently replicate the loop repair, against frozen strongest simpler baselines and regression/transfer tests. No current evidence warrants production promotion, claims of general reasoning reliability, increased intelligence, reliable weight optimization across models, or recursive self-improvement. No self-rewriting or recursive improvement loop was demonstrated.
