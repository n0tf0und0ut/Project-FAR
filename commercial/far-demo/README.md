# FAR hosted demo

The hosted demo is an optional commercial component, not a dependency of the
canonical Project FAR research package. Its runtime and test dependencies are
declared in this directory's `pyproject.toml`.

JSON uploads use `far_decision_integrity.strict_json` from the matching reviewed
source checkout. Install both components together as below; an older separately
installed `far-decision-integrity` artifact without that helper is incompatible
with this source candidate. This PR does not publish a new package release.

The JSON, JSONL, JSON-sniffed text and JSON/JSONL fenced-code paths reject duplicate
members, non-finite constants, overflow and unsupported nesting before package
adjudication. JSON-valued CSV/XLSX cells use the same parser. A fenced language
declaration is binding: rejected declared JSON cannot fall through to YAML.
Unlabelled text that is not JSON syntax can still contain YAML or TOML; ordinary
direct and declared YAML/TOML routes retain their existing support.

YAML mappings reject repeated explicit keys, including nested mappings and
JSON-shaped flow mappings that reach YAML during format detection. YAML merge
defaults retain PyYAML's existing precedence and explicit-override behavior;
repeating the merge key itself is rejected. This component-local adaptation
uses the repository's unique-key SafeLoader pattern without importing the
canonical mechanization package or changing its parser/frozen semantics.
Validation inspects the complete original YAML node graph before construction,
including inline/aliased merge sources, so merge flattening cannot erase a
duplicate or turn valid inherited overrides into false duplicate findings.
Valid non-object supporting snippets are skipped during embedded package search;
strict JSON semantic failures remain terminal.

Run its tests in the component environment:

```bash
python -m pip install -e commercial/far-decision-integrity -e commercial/far-demo
python -m pytest -q commercial/far-demo/tests
```

When repository-wide pytest discovery runs without the optional demo
dependencies, the demo test modules skip at collection with an explicit reason.
They must not fail import collection or be treated as executed component tests.
The canonical repository health suite continues to discover `tests/` through
`tools/run_tests.py`; it does not claim to execute this optional component.

## Human reasoning augmentation (Research prototype)

Run `uvicorn far_demo.app:app --host 127.0.0.1 --port 8000` after installing
both commercial components, then open `http://127.0.0.1:8000/augment`.
The existing root decision-integrity demo and its endpoints remain intact.

The augmentation page captures original claims, evidence labels, alternatives,
assumptions and confidence, elicits targeted questions, and records revisions.
Sessions are held in browser localStorage and exportable as hash-linked JSON;
the API processes them transiently without persistent server storage. The
questions only assess missing *declared* fields, not external truth, formal
entailment, mental causes or measured cognitive improvement. SHA-256 is not a
signature. See `AUGMENTATION.md` for protocol, testing, and assurance limits.

### Optional model-directed analysis

The `/augment` workspace now supports server-configured Chat Completions models.
It produces source-anchored, explicitly unverified semantic critiques alongside
its existing deterministic questions. It never claims external factual
verification or measurable cognitive improvement. Set the provider URL, model,
API key and private workspace access token as described in `AUGMENTATION.md`,
and run the semantic API/test suite before exposing the service. The browser
never receives the provider's API key.
