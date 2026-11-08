# Mechanization

## Purpose

This directory contains executable representation/conformance machinery and proof-assistant formalization for Project FAR. Their authority is limited to the exact contracts, premises, and scopes documented in the current governance records.

## Current status and routes

- **Lean formalization:** [PCA-W2 status](../docs/governance/pca-w2-formalization-status-v1.0.md) records 14/14 governed core claims formalized under pinned Lean 4.19.0, with the explicit assurance and premise limits in that record. This supersedes the earlier partial-scaffold description.
- **`far-ir/1.0`:** the original storage/graph MVP remains at its declared interchange scope; it is not silently reinterpreted as the later contract verifier.
- **`far-ir/2.0`:** [contract specification](../docs/specification/far-ir-2.0-contract.md), [current strict verification rule](../docs/specification/far-ir-2.0-current-verification.md), and [W3 status](../docs/governance/pca-w3-contract-schema-status-v1.0.md) describe the finite-explicit contract and conformance machinery.
- **`far-ir/2.1`:** [approximation/cost specification](../docs/specification/far-ir-2.1-approximation-cost.md) and [W5 status](../docs/governance/pca-w5-approximation-cost-status-v1.0.md) delimit its additional finite-explicit verification scope.

## Run a bounded contract check

From the repository root:

```bash
python -m mechanization.far_mechanization.contract_conformance --manifest conformance/far-ir-2.0-current/manifest.json
python -m unittest tests.test_far_contract_v2 tests.test_far_contract_v2_strict
```

The [tests](../tests/test_far_contract_v2.py) and registered [conformance fixtures](../conformance/far-ir-2.0-current/manifest.json) show what the checks exercise. See [repository health checks](../docs/maintenance/repository-health-checks.md) for broader validation.

## Boundary

Formalization, verifier conformance, and successful tests are distinct assurance dimensions. They do not by themselves establish external replication, general-purpose agent reliability, scientific novelty, or production readiness. For governing interpretation use the [project status](../docs/project-status.md) and [canonical map](../docs/CANONICAL_MAP.md).
