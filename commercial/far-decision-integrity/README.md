# FAR Decision Integrity Core

This package validates explicit decision packages and deterministically classifies them as:

- `justified`;
- `unsupported`;
- `underdetermined`;
- `unverifiable`.

`far-decision-package/0.2` adds a semantic-integrity lane without reinterpreting historical `far-decision-package/0.1` packages. Version 0.1 remains readable, but only 0.2 may carry `semantic_contracts`.

## Semantic integrity

A 0.2 package may bind governed FAR IR records to declared decision nodes. Each entry in `semantic_contracts` names a `binding_id`, `target_node_id`, purpose, and FAR IR `record`. This binding layer is deliberate: an unrelated valid FAR IR record cannot silently authorize a decision.

The commercial package does **not** reimplement FAR IR semantics. It locates the canonical Project FAR repository, invokes the governed `far-ir/2.0` or `far-ir/2.1` verifier, and records SHA-256 identities for the exact verifier and schema used. `far-ir/2.0` records go through current verification rule v1.1 (`contract_v2_strict_v11`), which applies `far-ir/2.0` errata 1 and rejects a `PROVED` or `REFUTED` outcome unless its evidence is `CHECKED_FINITE_EXPLICIT`. `far-ir/2.1` records go through its errata 1 successor (`contract_v21_errata1`). The frozen baseline `contract_v2.py` is bound as a shared artifact, and every module the loaded verifier wraps is bound as a wrapped artifact.

Supported purposes are:

- `exact_sufficiency`: requires `far-ir/2.0`; only a valid `PROVED` factorization clears the gate, a valid `REFUTED` collision forces `unsupported`, and a quotient proof is treated as analysis rather than a proof that the package representation is sufficient;
- `approximation_candidate`: requires `far-ir/2.1` plus `selected_candidate_id`; a valid approximation/cost result clears the gate only when the selected candidate is in the verifier-confirmed feasible set, while an infeasible selected candidate forces `unsupported`;
- `analysis_only`: verifies quotient or other FAR IR analysis and reports its evidence, but does not satisfy `--require-semantic-contract` by itself.

Malformed bindings, invalid FAR IR evidence, typed `Unknown`, or an unavailable/crashing canonical verifier fail closed as `unverifiable` unless a stronger existing status applies. A satisfying semantic result cannot override contradicted evidence, missing authorization, material alternatives, declared unknowns, or incomplete traces.

## Use

From a Project FAR checkout:

```bash
python -m pip install ./commercial/far-decision-integrity
far-decision package.json --require-semantic-contract --output report.json
```

If the package is installed outside the checkout, set `FAR_REPO_ROOT` to the canonical Project FAR repository root. `--require-semantic-contract` requires at least one decision-gating `exact_sufficiency` or `approximation_candidate` binding; without the flag, legacy and non-semantic workflows preserve their existing behavior.

A 0.2 package extends the previous shape with a binding such as:

```json
{
  "schema_version": "far-decision-package/0.2",
  "semantic_contracts": [
    {
      "binding_id": "decision.semantic.1",
      "target_node_id": "conclusion",
      "purpose": "exact_sufficiency",
      "record": {
        "format_version": "far-ir/2.0",
        "id": "example.semantic.audit",
        "contract": {},
        "report": {},
        "provenance": {},
        "freeze": {}
      }
    }
  ]
}
```

The abbreviated FAR IR object above only shows placement; the embedded record must satisfy its own canonical schema and semantic verifier.

## Claim boundary

This package evaluates disclosed package structure, dependencies, contradictions, alternatives, unknowns, declared trace completeness, and the finite explicit semantics actually encoded in supplied FAR IR records. It does not infer hidden reasoning, prove external factual truth, establish that a domain mapping is correct or complete, certify safety, certify legal compliance, establish empirical utility, or establish novelty.

A `justified` decision means that no failure is present under the disclosed package rules and every required semantic binding cleared its explicitly declared gate. It is not a universal truth or safety certificate.


## Commercial demonstration and validation

Two **synthetic, structural-only** packages are included for immediate operator testing:

```bash
far-decision commercial/far-decision-integrity/examples/clear-package.json
far-decision commercial/far-decision-integrity/examples/contradicted-package.json
far-decision commercial/far-decision-integrity/examples/clear-package.json --require-semantic-contract
```

Expected results are `justified` (exit 0), `unsupported` (exit 30), and `unverifiable` (exit 32), respectively. The clear structural case has no required semantic contract; the third command deliberately checks that the semantic gate refuses to treat it as checked. These fixtures demonstrate deterministic adjudication only; they are not empirical evidence of external accuracy or commercial value.

All commercial JSON file loaders reject duplicate object keys, `NaN`/`Infinity`, and finite-number overflow before domain interpretation. Decoder nesting-limit failures use the same invalid-input contract: the decision CLI reports `invalid-package` (exit 40), and evidence verification returns false. Evidence bundles also refuse to serialize non-finite numeric results.

See [pilot validation](PILOT_VALIDATION.md) for the proposed customer/comparator experiment, economic measurement, failure conditions and evidence gates. Its price and milestones are commercial hypotheses, not validated market facts.

The optional hosted demo's upload adapters also share this parser at the original
JSON-byte boundary. Duplicate/non-finite data must not be decoded permissively
before calling `DecisionPackage.from_dict`; direct Python objects cannot recover
ambiguity already lost during parsing. JSON/JSONL uploads, sniffed/declared JSON
in documents and JSON-valued tabular cells are covered by actual-route tests.
Both source components must be installed from the same reviewed checkout; no
new release or effectiveness claim is made.

November 6 boundary follow-up: **CJSON-006** reproduced permissive hosted upload
decoding before the package's strict loader (31 failed assertions and two parser
errors in the initial actual-route regression). The demo now shares the strict
JSON parser across direct, line-delimited, sniffed/fenced and tabular JSON.
**CJSON-007** reproduced a duplicate-key YAML flow fallback with a trailing comma
being accepted on direct/sniffed/fenced YAML routes (three failed assertions).
The local unique-key YAML loader closes that ambiguity while preserving tested
merge defaults/explicit override and legitimate YAML/TOML inputs. All **48**
package and **26** dependency-equipped baseline demo tests pass; combined
semantic-augmentation validation is a separate integration obligation.
