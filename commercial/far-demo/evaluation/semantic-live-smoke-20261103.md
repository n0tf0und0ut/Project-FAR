# One live semantic access/conformance smoke — failed output conformance

Status: bounded engineering observation. One authored fixture, one actual local-model generation, no retries. No human participants, customers, external API charges, semantic-effectiveness measurement, independent replication or general-reliability inference.

Exact tested repository commit: `4b9946497cd96f5f881722650c95a1cd4ab31632`.
Tree: `edf1873db946761a3e890fa9d093125dd2f3a990`.
Model: official `Qwen/Qwen2.5-0.5B-Instruct`, immutable revision `7ae557604adf67be50417f59c2c2f167def9a775`; 494,032,768 parameters.
Raw model.safetensors SHA-256: `fdf756fa7fcbe7404d5c60e26bff1a0c8b8aa1f72ced49e7dd0210fe288fb7fe`.
Actual loaded BF16 state digest: `bf6a807c4b6795a1b5041879e19d4e12430bb568366a801e4319e197b873ed69`.
Freeze file SHA-256: `ec61b5c42d3d3945f9e71b971941d8da8ee4b5fb83d4063010a8d2f2896ec816`.

The freeze was written at 18:49:40.663915 UTC, before generation started at 18:49:40.715704 UTC on 2026-11-03. It binds the complete authored input and session, exact provider request, actual input token IDs, source/wrapper hashes, model/tokenizer asset identities, runtime and inference settings. Nonweight model/tokenizer files are included; the 988 MB public weight file is omitted but content-addressed for retrieval.

CPU BF16/SDPA, four threads, deterministic algorithms, greedy decoding. The existing semantic client retained its 30-second timeout and 4096-token request cap. The scratch-only loopback adapter did no grammar forcing, JSON repair or output substitution; it returned the model's actual completion. A separately declared host max_time of 120 seconds bounded model work if the client disconnected.

Actual observation: 525 prompt tokens, 218 completion tokens, generation elapsed 25.258947 seconds; the local provider delivered HTTP 200. The existing FAR semantic route returned HTTP 502 after 25.314163 seconds because the unchanged strict validator rejected the real model output. The raw output uses Markdown fences; it also lacks the required open_questions field and supplies strings rather than path/quote anchor objects. These are directly observable contract defects, not an independently scored estimate of diagnostic quality. No output was rewritten or resubmitted.

Live model access is established for this local wrapper and checkpoint. End-to-end output conformance FAILED. The failure is retained in full and does not support semantic effectiveness, human augmentation benefit or customer value. The logged Transformers sliding-window/SDPA and ignored sampling-option warnings remain part of the runtime record.

External API charges: zero. Local compute cost, electricity and human-review effort: unmeasured. No cost advantage is inferred.

Source files were unchanged throughout the call. No repository mutations, GitHub writes or production deployment occurred. Hashes and timestamps provide recorded-byte provenance and replayable consistency checks, not trusted execution attestation.

Original execution command (write-once; do not rerun into the existing evidence directory):

```sh
PYTHONPATH=/workspace/scratch/e1c41a89d76e/far-mech-deps:/workspace/scratch/e1c41a89d76e/worktrees/616/commercial/far-demo/src HF_HUB_ETAG_TIMEOUT=15 HF_HUB_DOWNLOAD_TIMEOUT=30 TOKENIZERS_PARALLELISM=false /workspace/scratch/e1c41a89d76e/far-venv/bin/python /workspace/scratch/e1c41a89d76e/semantic-live-smoke/run_smoke.py
```

Validate the preserved bytes without model inference:

```sh
python verify_smoke.py
```
