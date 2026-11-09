# Mechanization

## Purpose

This directory contains executable representation/conformance machinery and proof-assistant formalization for Project FAR. Their authority is limited to the exact contracts, premises, and scopes documented in the current governance records.

## Current status and routes

- **Lean formalization:** [PCA-W2 status](../docs/governance/pca-w2-formalization-status-v1.0.md) records 14/14 governed core claims formalized under pinned Lean 4.19.0, with the explicit assurance and premise limits in that record. This supersedes the earlier partial-scaffold description.
- **`far-ir/1.0`:** the original storage/graph MVP remains at its declared interchange scope; it is not silently reinterpreted as the later contract verifier.
- **`far-ir/2.0`:** [contract specification](../docs/specification/far-ir-2.0-contract.md), [current strict verification rule](../docs/specification/far-ir-2.0-current-verification.md), and [W3 status](../docs/governance/pca-w3-contract-schema-status-v1.0.md) describe the finite-explicit contract and conformance machinery.
- **`far-ir/2.1`:** [approximation/cost specification](../docs/specification/far-ir-2.1-approximation-cost.md) and [W5 status](../docs/governance/pca-w5-approximation-cost-status-v1.0.md) delimit its additional finite-explicit verification scope.

## Choose an execution path

| Goal | Entry point | What the result establishes |
|---|---|---|
| Verify an explicit `far-ir/2.0` contract | [Conformance manifest](../conformance/far-ir-2.0-current/manifest.json) and [strict verifier documentation](../docs/specification/far-ir-2.0-current-verification.md) | Conformance to the declared finite-explicit contract and the current verifier rules only. |
| Inspect a known collision and rejection | [Registered collision](../conformance/far-ir-2.0/valid-collision.json), [incorrect factorization](../conformance/far-ir-2.0/invalid-factorization.json), and [strict tests](../tests/test_far_contract_v2_strict.py) | Distinguishes a correctly described failure from a false proof claim; does not determine whether external facts are true. |
| Trace a formal theorem to Lean | [W2 status](../docs/governance/pca-w2-formalization-status-v1.0.md) and [claim-to-declaration ledger](../theory/evaluation/far-core-formalization-ledger-v1.0.json) | The recorded formalization and its explicit premises, not novelty or domain-general correctness. |
| Reproduce a bounded agent-routing check | [Architecture-routing study](../research/architecture-routing/README.md) | Internally registered tool-choice results; distinguish smoke tests, replay and actual model runs. |
| Reproduce an empirical negative result | [60-run scripted-repair result](../research/workflow-efficacy/KEYLESS-PILOT-RESULTS-V0.4.md) | The registered internal comparison only, not general agent efficacy. |

### Trace one verifier outcome

1. Read the [manifest](../conformance/far-ir-2.0-current/manifest.json) to identify the registered input, expected disposition, and case identifier.
2. Open the [input record](../conformance/far-ir-2.0/valid-collision.json) and inspect the declared source domain, required behavior, and colliding representation.
3. Run the conformance command below on a checkout of the exact repository revision being evaluated, and preserve the command, revision, exit status, and raw output.
4. Compare the observed outcome with the registered tests and the [W3 acceptance boundary](../docs/governance/pca-w3-contract-schema-status-v1.0.md). A green test checks this encoded case; it is not external scientific replication.

## Run a bounded contract check

From the repository root:

```bash
python -m mechanization.far_mechanization.contract_conformance --manifest conformance/far-ir-2.0-current/manifest.json
python -m unittest tests.test_far_contract_v2 tests.test_far_contract_v2_strict
```

The [tests](../tests/test_far_contract_v2.py) and registered [conformance fixtures](../conformance/far-ir-2.0-current/manifest.json) show what the checks exercise. See [repository health checks](../docs/maintenance/repository-health-checks.md) for broader validation.

## Boundary

Formalization, verifier conformance, and successful tests are distinct assurance dimensions. They do not by themselves establish external replication, general-purpose agent reliability, scientific novelty, or production readiness. For governing interpretation use the [project status](../docs/project-status.md) and [canonical map](../docs/CANONICAL_MAP.md).
