# FARGraph 0.1 — Research factory integration

Status: **Research advisory only**. This package implements an independent local dependency graph and read-only MCP/CLI. It does not replace FAR governance, native protected checks, exact-head review, or merge authorization. The MIT license in `fargraph/LICENSE` covers this independently authored prototype. GitNexus code was not incorporated.

## Running against a work order

On the software-factory branch, provide an exact candidate checkout and an external work-order JSON file (must be validated by the existing `tools.software_factory.parse_order_text` parser):

```bash
python -m tools.factory_fargraph \
  --root . \
  --work-order /tmp/factory-order.json \
  --head-sha "$(git rev-parse HEAD)" \
  --repository n0tf0und0ut/Project-FAR > /tmp/fargraph-advisory.json
```

`tools.factory_fargraph` checks work-order schema, source SHA-256, repository string, base ancestry, exact checkout HEAD and clean working tree. It reads changed-file paths from the exact Git `base...head` diff and builds a source graph from that tree; deleted paths are explicitly flagged as unindexed. It prints an **advisory** JSON report with indexed source hashes, evidence-linked impact paths, uncertainties, and diagnostics. Output status is always `ADVISORY_ONLY_NO_MERGE_AUTHORITY`. Failed validation returns exit code 2 and no positive evidence.

Additional read-only operations:

```bash
python -m fargraph --root . stats
python -m fargraph --root . impact --git-base main
python -m fargraph.mcp --root .
```

The MCP subprocess exposes only structural read and refresh operations; it has no ability to write GitHub content, change factory queue state, approve reviews, or merge PRs. A graph finding may guide testing and source inspection but cannot replace either.

## Tested boundaries

`python -m unittest discover -s tests -p 'test_fargraph.py' -v`

`python -m unittest discover -s tests -p 'test_factory_fargraph.py' -v`

The standalone prototype was checked with Python 3.11+ standard library, synthetic repositories, and local Git fixtures. The factory integration tests verify head and base pinning, work-order source hash, changed/deleted paths, dirty tree rejection, repository identity rejection, and no authority promotion. These are local tests, not hosted PR evidence.

## Explicit limitations and security

Analysis includes Python imports/call syntax, local Lean imports, Markdown links, and local GitHub Actions `uses` edges. It cannot resolve all dynamic code, theorem semantics, unsupported languages, external dependencies, or deleted-file outgoing edges. A missing edge does not mean no dependency exists. It currently scans all supported files on each request, skips files above 2 MB, and has no total file/byte budget. Do not execute it over untrusted giant repositories without resource caps. Before any production use, implement caps, retention policy, held-out change-impact evaluation, independent code review, and actual MCP client tests.

There is no automatic hook in the protected CI or factory stage transitions. Operators may use the report to select human review/test targets, but the factory controller's existing three stages and protected gates remain untouched. The graph and advisory are noncanonical Research evidence; current GitHub `main` and its governing sources control FAR.
