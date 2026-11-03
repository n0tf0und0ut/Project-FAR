# Internal preexecution review v0.3 — fixed larger backend

Status: **Research; prospective internal review, no v0.3 model observations yet.**

Two 1.5B capability stages stopped without any broader scored-task exposure. V0.1 achieved 1/3 strict successes and v0.2 achieved 2/3; each executed one unrequested simulated file write. All raw records, source identities and failed gates remain preserved. These stages motivated one fixed larger backend that fits the available CPU environment; they are not hidden exclusions from a primary performance estimate.

V0.3 changes the model to pinned Qwen2.5-Coder 7B. It keeps the exact v0.2 system policy, action/request/run/token limits, three seeds, scoring, continuation criteria and all 24 still-unexposed scored task objects. P07–P09 are fresh capability inputs. No additional instruction or larger-local-model search is planned. This is capability-driven development, not independent replication or a randomized cross-model causal experiment.

The primary registry manifest response contains 858 bytes and hashes to `dae161e27b0e90dd1856c8bb3209201fd6736d8eb66298e75ed87571486f4364`. Its exact bytes are retained losslessly in the metadata wrapper. Registry metadata retrieval performed no inference. Live model installation must match the full digest before a model request; every request and reply is checked for the selected model, with no fallback to 1.5B.

The coordinator and a read-only internal reviewer inspected the entire v0.3 model-selection trust boundary, startup script, workflow, raw-replay gate and predecessor preservation. All 56 targeted tests passed, including eight new model-binding regressions; protocol validation, shell syntax, hygiene and diff checks passed. No further concrete blocking defect was found at these SHA-256 identities:

| File | SHA-256 |
| --- | --- |
| `tools/tool_agent_reliability.py` | `b8f8e9f74cfd5c5be3acb602060b1b146d065e11af5aeb2cf6f188f01bf7dffb` |
| `.github/workflows/far-tool-agent-reliability-v03.yml` | `0aabbbf63e0258569ec27bb9a0a2a75b3a0c215c2e01861f0fc8c419e7c825b1` |
| `scripts/tool_agent_reliability_start_7b.sh` | `8b05199dd694e5bba758fc4a76b9bf772207407b41345d5ace2b7fb71d8967ee` |
| `protocol-v0.3.json` | `ab6325bbf76d5b02b2a766402147f03eb2c8454b18a9f5896431546f41106e33` |
| `model-qwen2.5-coder-7b-manifest.json` | `437545c9687e56af0805f048847af5149fe60dbedac4ca6602f8ba012f8a8934` |
| `tests/test_tool_agent_reliability.py` | `d2e8bd402bfc191f47858613a1a07714668dec47e77b33f56d87b90d53786357` |

Current live CLI permits only this v0.3/7B/v0.2-policy configuration. Source verification includes its actual startup script and workflow. Predecessor raw records cannot open this gate: all three fresh exact-source preflight traces must be valid and replayable, at least two must pass, and unsafe writes must equal zero before the broader 72 slots execute. A failed gate still stops rather than triggering another local-model search.

This shared-environment internal review is not I3 assurance. General reliability, FAR-specific benefit, real-world readiness and accepted theory status are unchanged. Protected merge authorization and external exact-head software review remain separate obligations.
