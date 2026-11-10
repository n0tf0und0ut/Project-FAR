# Cloudflare security-audit skill in Project FAR

Status: operational, pinned agent capability. This is **not a required merge gate**,
an independent external reviewer, an empirical claim, or a completed security audit.

## Source, discovery and provenance

Project FAR contains Cloudflare's entire unmodified `security-audit` skill and its
validators under [`.agents/skills/security-audit/`](../../.agents/skills/security-audit/SKILL.md).
It is locked to upstream commit
[`c1c8a8c1471069fb0e188eeaff69b8e8db6564a8`](https://github.com/cloudflare/security-audit-skill/tree/c1c8a8c1471069fb0e188eeaff69b8e8db6564a8/skills/security-audit)
using [`cloudflare-security-audit-source-lock.json`](cloudflare-security-audit-source-lock.json).
The 21-file lock includes Cloudflare's MIT license and the upstream Node.js
validator test suites. No `npx` install, mutable tag, runtime download, or remote
model credential is required to *make the instructions available*.
`python tools/check_cloudflare_security_skill.py` fails closed on any file drift.

Codex CLI/IDE can discover skills in `.agents/skills`. Codex Cloud/ChatGPT Work
might not expose repository skills automatically; direct the agent to read the
canonical `SKILL.md` if not discovered. Claude can discover
[`.claude/skills/security-audit/SKILL.md`](../../.claude/skills/security-audit/SKILL.md),
a minimal adapter to the same pinned source. Claude follows its separate
`CLAUDE.md`; Codex/ChatGPT follows the fresh root `AGENTS.md`.
Both continue to obey FAR's governing sources and protected repository controls.

The integration's [CI workflow](../../.github/workflows/cloudflare-security-audit-skill.yml)
only validates the vendored source and upstream validator self-tests. It grants
`contents: read`, has no model secrets, does not post findings, and cannot approve
or merge PRs. Green CI here is **not** a security clearance.

## Intended use

Use guidance mode for focused source-only security questions and review.
For a requested full security audit, launch a coding agent with the necessary
parallel independent subagents and a checked-out **exact target SHA**, then
invoke the `security-audit` skill in full mode. High-value FAR targets include
agent execution, prompt/tool injection, workflow tokens and protected-merge
checks, review evidence, artifact ingestion, factory runners, supply chain,
resource quotas, and authentication/authorization boundaries.

The six-phase Cloudflare process is: architecture reconnaissance; coverage
ledger and hunting; fresh candidate verification; schema-validated findings;
fresh independent record verification; and source-grounded reports.
Its typed verdicts stay distinct: `confirmed`, `needs_validation`, and
`rejected`. A scoped or budget-limited run must report its exact untested
scope. One run is never a proof of complete security coverage.

**Mandatory sandbox:** target-controlled builds, tests, browsers, agents'
local test cases, fuzzer inputs and execution fixtures run only under
OS-enforced isolation with no external network, clean allowlisted environment
without credentials, read-only target and toolchain, scratch-only writable
paths, and strict CPU/memory/process/file/disk/time limits. Use local dummy
principals and harmless fixtures only; never probe live services or identities.
Do not perform a dynamic test when the sandbox is not available. A missing
decisive fact becomes `needs_validation` with an explicit blocker.

Audit outputs live **outside the repository** unless the user explicitly chooses
an entire directory verified to be Git-ignored. The trusted parent alone owns
`run-metadata.json`, `architecture.md`, `coverage-ledger.json`,
`findings.json`, `REPORT.md`, `FINDINGS-DETAIL.md`, and
`NEEDS-VALIDATION.md`. Hunters and verifiers cannot modify shared outputs;
trusted parent-side artifact promotion must follow the upstream no-follow,
size-checked descriptor procedure. Never publish secrets or offensive payloads
by copying the raw audit directory into a PR.

Run both original validators against the final retained data **inside the
approved audit environment**:

```sh
node .agents/skills/security-audit/validate-coverage-ledger.cjs "$AUDIT_OUTPUT/coverage-ledger.json"
node .agents/skills/security-audit/validate-findings.cjs "$AUDIT_OUTPUT/findings.json"
```

The validators check formats and typed constraints, not whether a vulnerability
was actually reproduced. Cloudflare's public issue
[`#107`](https://github.com/cloudflare/security-audit-skill/issues/107)
reports a possible resource-amplification weakness in its findings validator;
that is an unresolved allegation, not a proven exploit. Until source changes
are reviewed, treat even validated audit records as untrusted and bounded.

## FAR review-ledger handoff

Following Cloudflare's final independent verification, use the **advisory**
read-only handoff converter (if present on the audited checkout):

```sh
python tools/cloudflare_security_audit_ledger.py \
  --run-dir "$AUDIT_OUTPUT" \
  --expected-head "$(git rev-parse HEAD)" \
  --output "$AUDIT_OUTPUT/FAR-REVIEW-LEDGER.md"
```

The handoff requires an exact source-head match, verifies cited worktree file
bytes against the exact Git HEAD blobs (including skip-worktree cases), and
runs the pinned Cloudflare findings validator against a private snapshot
before emitting a report. This requires local Node.js as well as Python and
Git; absent or rejecting validation fails closed. It only
produces a human-review template outside the repository. A `confirmed`
Cloudflare record is still *unadjudicated* under FAR; `needs_validation` is
an open research lead without severity; `rejected` does not cancel another
reviewer's reproducible defect. The PR finding ledger must retain root-cause
IDs, source/review IDs, violated invariant, reproduction, disposition, fix,
before/after regression checks, and stale-head invalidations according to
[PR Review Convergence v1.1](../governance/pr-review-convergence.md).

No security skill or agent-orchestrated panel is I3 external scientific
replication. A skill run is not a GitHub APPROVED review, nor a Codex exact-head
receipt. Do not alter the required `pr-review-convergence-observation`,
`merge-authority`, or `protected-repin-gate` contexts. CodeRabbit and Alibaba
OpenCodeReview remain independent *advisory* integrations that have separate
GitHub App and inference-credential activation requirements.

## Reproducible integration tests

```sh
python tools/check_cloudflare_security_skill.py
python -m unittest tests.test_cloudflare_security_skill \
  tests.test_cloudflare_security_audit_ledger tests.test_workflow_token_permissions -v
node --test .agents/skills/security-audit/validate-findings.test.cjs \
  .agents/skills/security-audit/validate-coverage-ledger.test.cjs
```

These tests verify installation and contract behavior only. They do not establish
a live vulnerability-audit result, production readiness, independent validation,
or inference-provider availability.
No dynamic audit result is claimed until an appropriately sandboxed, exact-head
agent audit actually executes and records its evidence.
