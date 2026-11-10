# Software factory: text and GitHub-Issue intake (Research)

This adapter implements **intake**, not an agent runner, authorization policy, research acceptance, or deployment. It builds on the unmerged factory queue in PR #630. Its `far-software-factory/intake/1` envelope retains the exact original requirement and provenance, compiles only explicitly listed acceptance criteria, validates the existing `far-software-factory/work-order/1` contract, and requires a separate operator `submit` command before persisting any queue work. No background GitHub polling or automatic issue-label trigger is enabled.

**Required inputs:** exact target repository, full base commit SHA and source text. GitHub Issue intake fetches an open non-PR issue from the fixed GitHub API host. Issue text (including Markdown or embedded instructions) is untrusted data. API tokens are used only for a read-only GET request. A repo issue's existence is not authorization to run code. ChatGPT or another front end can supply text through a UTF-8 file; no undocumented ChatGPT webhook or connector is assumed.

## Text request

Write `request.txt`:

```text
Build a word-count command-line tool.

Acceptance criteria:
- Given "red blue green", print 3.
- Report a nonzero exit code for a missing file.
```

From the repository root (Python 3.11+; replace the sample SHA with the current target base SHA):

```bash
python tools/software_factory_intake.py draft-text \
  --repo n0tf0und0ut/Project-FAR --base-sha "$TARGET_BASE_SHA" \
  --text-file request.txt --output intake-draft.json
python tools/software_factory_intake.py submit \
  --draft-file intake-draft.json --db /tmp/far-factory.sqlite \
  --receipt-file /tmp/far-factory-intake-receipt.json
```

## GitHub Issue request

Put objective in the issue title; put an `Acceptance criteria:` heading and bullet points in its body. Then:

```bash
GITHUB_TOKEN="$READ_ONLY_GITHUB_TOKEN" python tools/software_factory_intake.py draft-issue \
  --repo n0tf0und0ut/Project-FAR --issue 123 \
  --base-sha "$TARGET_BASE_SHA" --output intake-draft.json
```

Review the generated draft and explicitly run `submit` as above. Do **not** put tokens in issues. Any user able to create an issue can suggest text; only the operator controlling the queue can submit. GitHub permissions, PR review, CI checks and protected-merge authorization remain separate.

## Semantics and limits

- The compiler is **deterministic extraction**, not a deployed language model. It copies bullet points only under `Acceptance criteria:`, `Acceptance:`, `Done when:`, `Definition of done:` or `Success criteria:`. It does not invent unmentioned requirements or subdivide work. Arbitrary natural language without explicit testable criteria produces `needs_clarification` (exit code 3) and cannot be submitted. It does not assess whether each bullet is actually testable; a downstream requirements review must do that.
- The raw source, source hash, base commit and full draft fingerprint are retained. The generated order ID binds to the request source, while the immutable queue rejects reuse with a different base. SHA-256 detects accidental changes, not a malicious operator rewriting both the source and its digest; no signature or review authentication is claimed.
- The `submit` command creates an advisory queued job only. It **does not** start a coding model, trigger GitHub actions, write code, approve reviews, or merge anything. A subsequent independent execution adapter and authenticated evidence collector are required before any production-autonomy claim.
- No active GitHub webhook or ChatGPT-to-queue transport is provisioned by this PR. This provides executable CLI entry points that such interfaces can call after they exist.
- Input bounds: 64 KiB for request texts; 128 KiB for GitHub JSON issue responses; at most 32 explicit acceptance criteria. Duplicate JSON fields, non-finite JSON numbers, malformed issue identities and issue/PR confusion fail closed.

Run `python -m unittest tests.test_software_factory_intake_nl -v` from the repository root, or run repository-required tests in protected CI. Keep drafts outside the repository when their content is sensitive.