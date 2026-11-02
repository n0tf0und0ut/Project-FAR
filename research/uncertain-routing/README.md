# Explicit-contract dispatch and uncertain routing — operational boundary

**Status: Research implementation / no accepted theory change.** This work enforces an already governed distinction: machine-readable downstream contracts that pass the applicable schema and semantic verifier can bypass contract discovery; insufficient or invalid input cannot. See the [Contract Discovery Protocol](../../methodology/contract-discovery-protocol.md) and [canonical FAR workflow](../../frameworks/FAR/workflow.md).

## Current default: explicit verification without an agent

`tools/far_routing_dispatch.py` parses exact UTF-8 strict JSON (rejects duplicate keys and non-finite numbers), records the SHA-256 of the original input, and dispatches an explicit `far-ir/2.0` record only to the **current v1.1** verifier `contract_v2_strict_v11`. An explicit `far-ir/2.1` record uses `contract_v21_errata1`. The `--mode deterministic` and `--mode declarative` variants use the same frozen current verifier; neither invokes a language model. All substantive claim/outcome checks are delegated to the canonical verifier.

```bash
python tools/far_routing_dispatch.py conformance/far-ir-2.0/valid-factorization.json
python tools/far_routing_dispatch.py conformance/far-ir-2.1/valid-frontier.json --mode declarative
python tools/far_routing_dispatch.py conformance/far-ir-2.0/invalid-factorization.json
```

The first two exit 0 with `VERIFIED_EXPLICIT_CONTRACT`. The invalid document exits 3 with `DISCOVERY_REQUIRED`: its alleged `PROVED` result is **not** surfaced as a verified outcome. Any unsupported version, malformed JSON, bare prose, or `far-intake/1.0` object also requires governed discovery; the dispatcher itself does not fabricate or complete an intake record. Infrastructure errors are separated as `VERIFIER_UNAVAILABLE` (exit 2). Every output reports `model_calls: 0`. This gate is an opt-in operational entry point; it does **not** silently replace all FAR consumers. The commercial semantic auditor already selects current verifiers deterministically for recognized formats.

## Separate agent investigation: no pretend unique ground truth

The separate [frozen v0.1 uncertain-task corpus](frozen-v0.1.json) contains twelve *under-specified* claims and investigations; none provides a validated machine-readable downstream contract. These tasks do **not** have one uniquely justified next action. Each task has a publicly authored **set of admissible moves**, sometimes multiple equally justified ones. Available conceptual moves are `ASK_SCOPE`, `GATHER_EVIDENCE`, `DISCOVER_CONTRACT`, `PRESERVE_UNKNOWN`, `VERIFY_EXPLICIT`. **VERIFY_EXPLICIT is always inadmissible here**.

The model only proposes a bounded next action. It does not actually retrieve evidence, freeze an intake, prove a statement, or update knowledge. The frozen task-author action sets are *not independent expert adjudications or truth labels*. The baseline `DISCOVER_CONTRACT` on every case is scored against the same sets without automatically calling it a correct universal solution. The executable `tools/far_uncertain_routing_pilot.py` sends only the task text and action vocabulary, never the acceptable-action labels. Any invalid/unsafe route is retained as an observed failure.

The live CPU pilot uses SHA-pinned local Qwen2.5-0.5B-Instruct GGUF and llama.cpp, no remote inference API or secrets, with exactly twelve calls. It records each request and raw response, model identity, usage, latency, exact frozen-protocol hash and an atomic per-call checkpoint. The workflow is [far-uncertain-routing-pilot.yml](../../.github/workflows/far-uncertain-routing-pilot.yml). Unit testing and corpus validation need no model:

```bash
python -m unittest tests.test_far_routing_dispatch tests.test_far_uncertain_routing_pilot -v
python tools/far_uncertain_routing_pilot.py validate
```

The first model workflow [executed successfully](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41529666605). The model chose `ASK_SCOPE` on all twelve under-specified tasks, yielding 11/12 admissible suggestions against the publicly authored sets. An `always ASK_SCOPE` deterministic policy ties **11/12**, without inference cost; **adaptive routing benefit was not demonstrated**. Full raw-artifact SHA-256 records, case/rubric limitations, token and timing totals are in [execution-v0.1.md](execution-v0.1.md). The scored runner now checks every constant-action alternative and number of distinct model actions, without changing task labels or historical observations.

A successful workflow supports only task-author-set admissibility counts for this curated small model/corpus, not a frontier-agent superiority claim, a unique best route, general reasoning reliability, or customer value. Results stay in Research. A genuine system-level adaptive-routing comparison still requires competing executable tools, matched evidence budgets, independent task ground truth or a justified set-valued oracle, and credible held-out cases. No production model escalation is authorized by this pilot.

## Verification and governance

Fail-closed regressions cover verified v2.0/v2.1 dispatch, strict transport, prohibited model fallback, semantic rejection, verifier outages, set-valued scoring, model prompt/oracle separation, attempted unsafe verification and lossless partial-response preservation. The current [Research Execution Charter](../../docs/governance/research-execution-charter.md) and protected-review checks control deployment and promotion. No accepted FAR Core theorem, canonical stage sequence, or scientific validity claim changes here.
