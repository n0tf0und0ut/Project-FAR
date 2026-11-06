# Numeric source-grounding pilot: original execution and negative primary result

Status: **Research; original 32/32 conditions recovered and replayed; primary exploratory gate FAILED.**

The [prospective protocol](LIVE-EXPERIMENT-V0.1.md) was frozen at `4956893084d49fe42bde275105cf58a0bb240008`. The only scored launch was [run 42090379885](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/42090379885), exact source commit `2b6a52f6c5fdc7d55240a358c42fe45818571672`, job `127466539393`. All 32 registered conditions executed once. The following independent-replay step failed because execution and filename traversal enumerated the derived outcomes differently; the original failed workflow and its [full log](original-launch-42090379885.log) remain preserved.

On November 6 the authenticated GitHub artifact download became available to this audit. The original [artifact 13445236161](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/42090379885/artifacts/13445236161) is preserved byte-for-byte in [original-live-42090379885.zip.b64](original-live-42090379885.zip.b64). Decoded size: **48,898 bytes**. SHA-256: `b731cfb1730f443d0f06eff07535fe23cf09c16b9beec6d4aa0c30613b7b89a3`, matching both GitHub artifact metadata and the original job's upload log. The archive contains all 32 condition records, original `analysis.json`, and original `state.json`; none was rewritten. [Preservation metadata](preserved-live-v0.1.json) records the evidence identifiers and separate post-execution correction.

## Replayed observation

| Metric | Direct JSON control | Grounded tool and release gate |
|---|---:|---:|
| Registered conditions | 16 | 16 |
| Correct final outcomes, including legitimate abstentions | 8 | 12 |
| Correct numeric answers among 8 supported variants | 0 | 4 |
| Legitimate abstentions among 8 unsupported variants | 8 | 8 |
| Wrong numeric releases | 0 | 0 |
| Unnecessary abstentions on supported variants | 8 | 4 |
| Model calls | 16 | 20 |
| Reported input tokens | 2,517 | 4,096 |
| Reported output tokens | 176 | 447 |
| Sum of measured model seconds | 18.783667184999985 | 32.68937596500001 |

The [deterministic replay report](replay-live-v0.1.json) reconstructs every original request, raw response, protocol/model/source identity, response-dependent call count and release decision. The saved original report agrees exactly after normalizing **only** outcome enumeration order; numerical aggregates, durations and grades are not tolerated or altered. All original source/protocol bytes and the original failed workflow remain unchanged. No model calls or favorable reruns were added during convergence.

The preregistered primary gate required at least two fewer wrong numeric releases, with no more than two additional unnecessary abstentions. Both arms released zero wrong numbers, so **the primary gate fails**. Treatment produced four more correct numbers in these authored variants but that secondary descriptive observation does not demonstrate the registered error-reduction hypothesis. Treatment also consumed more model calls, tokens and measured generation time.

The eight answerable variants ask about **one known source metric**, and all unsupported questions use the same frozen source. They are not independent source truths or a held-out population. This was one deterministic local Qwen2.5-Coder 1.5B checkpoint and a bundled tool-plus-filter intervention. The result does not identify an internal-reasoning benefit, isolate tool access from strict release filtering, establish superiority over a simpler fixed calculator, demonstrate general autonomous reliability, or establish external-world accuracy, scientific independence, trusted execution attestation, commercial value, or production readiness.

## Post-execution defect ledger and verification

- **NUM-REPLAY-COUNT-001**, review `4494187522` on `655d4222f072bc82e6096a3dbcc841247beee3e2`: an answerable metric-request record with its required second call removed could be relabeled as `UNKNOWN` and accepted. The new missing-followup and unsolicited-second-call regressions both failed before repair. The analyzer now requires exactly the call count prescribed by the first validated action and task answerability. Original records already satisfy that rule.
- **NUM-REPLAY-ORDER-001**, review `4494187531` on the same head: full counterbalanced execution succeeded but standalone replay failed. The end-to-end mocked-run/CLI regression reproduced this error, and reversing fixture enumeration changed the report. All derived outcomes and duration aggregation now use registered slot order. Legacy report comparison normalizes only that order and still rejects a one-count score mutation.
- **NUM-PRESERVE-001**: prior claims of inaccessible live evidence are superseded by the authenticated original download above. The observer defaults to hash-pinned preserved bytes, retaining the original workflow's `failure` conclusion separately from the current `REPLAY_VERIFIED_BOUNDED_RESULT`. `--remote` retains an independent read-only GitHub query path and still fails closed on unavailable/invalid remote evidence. Archive controls reject missing, extra, aliased or duplicate members, changed preserved bytes, incomplete state, and mismatched record schema/types.
- Earlier attempt-persistence (`4493868142`), provider-envelope (`4493868156`) and source-commit (`4493868165`) fixes were already present at the initial convergence head; their regressions were rerun. They do not retroactively create new attempt journals inside the original archive. The original completed run contains its 32 retained condition records; no unrecorded attempt is invented.

Reproduction without model calls:

```sh
python -m unittest tests.test_numeric_grounding_integration tests.test_numeric_live_pilot -v
python research/numeric-grounding/observe_live.py
```

The observer's success means exact preserved-byte correspondence and bounded deterministic replay. It does not turn the original hosted failure into success or the failed scientific gate into a positive result. Qualifying independent substantive review and current protected checks remain separate obligations.
