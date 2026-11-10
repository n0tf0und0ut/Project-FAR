# Advisory external AI code reviewers

Status: integration configuration; not a change to PR review convergence, protected merge authority, or scientific assurance.

Project FAR uses two separate AI review sources:

1. CodeRabbit, an independent GitHub App configured by `.coderabbit.yaml`.
2. Alibaba OpenCodeReview (OCR), a pinned action and pinned npm CLI version in
   `.github/workflows/advisory-open-code-review.yml`.

Neither source substitutes for FAR's required exact-head Codex review or qualified
nonauthor human approval under `docs/governance/pr-review-convergence.md`.
They do not satisfy the dedicated App protected-repin gate, merge authority,
independent human approval, or I3 scientific external replication.

## One-time activation

**CodeRabbit:** Sign in at https://app.coderabbit.ai and install its GitHub
App on public repository `n0tf0und0ut/Project-FAR`. Verify the installation
under GitHub repository Settings > Integrations > GitHub Apps and on a new
main-targeting PR. Public-repository review is advertised as free, subject to
fair-use and review-rate limits. This GitHub App installation cannot be
performed by committing a repository configuration file.

**Alibaba OCR:** Under GitHub repository Settings > Secrets and variables >
Actions, create repository secret `OCR_LLM_AUTH_TOKEN` and repository variables
`OCR_LLM_URL` (full model API URL) and `OCR_LLM_MODEL` (tool-call-capable
model ID). Optionally set `OCR_LLM_USE_ANTHROPIC` to `true` for Anthropic
protocol; otherwise OpenAI-compatible protocol is selected. Set optional
`OCR_MAX_TOKENS_BUDGET` to bound total usage (default `50000`).
For a free-tier example, a user-supplied OpenRouter key may be paired with
`https://openrouter.ai/api/v1/chat/completions` and a currently available
tool-call-capable free model. Availability and function-calling support must
be checked at activation. A free-tier model can be rate limited, change, or
fail. OCR cannot run without a configured model and access token. Do not
place credentials in tracked files or PR comments.

## Execution and trust boundary

- When an existing `Required PR Review Convergence` run completes for a
  main-targeting PR, a separate trusted-main `workflow_run` job resolves the
  PR again through GitHub, pins its current head SHA, and invokes Alibaba OCR.
  The producer's success is not required; it may fail while Codex/human review
  remains outstanding. Candidate PR events only run a read-only integration
  contract test. Neither GitHub trigger executes PR code with a write token.
- The trusted OCR job refuses drafts, forks, closed PRs and other base branches.
  If GitHub omits PR identity, it accepts only a unique current same-repository
  head-branch match. Ambiguous identity is skipped. Automatic review is also
  skipped if required provider configuration is absent.
- For initial reviews of older PRs or missed automatic triggers, use
  Actions > Advisory OpenCodeReview > Run workflow with the exact PR number.
  The job re-reads the PR head at execution time. It neither merges nor
  changes branch protection.
- OCR action commit `b1dcffb0729f3f2e3e47170968a5014a2e035580` and npm
  version `1.13.7` are pinned together. Updates require ordinary protected
  review and verification. The trusted job has contents:read and
  pull-requests:write only; OCR uses that token to post review comments.
  Do not introduce a PR checkout followed by executable candidate scripts
  into this privileged job.
- OCR preserves raw review artifacts and uses a bounded token budget. The
  upstream CLI can return exit code 0 with partial findings when a budget is
  exceeded. An action success or empty comment list is **not** a clean
  substantive verdict; examine artifacts for skipped files and failed tasks.
  CodeRabbit may likewise report a successful check when a review is skipped
  or rate limited. Neither check is added to required branch protection.
- Review findings remain claims to investigate. Record root cause, reproducer,
  disposition, regression evidence and exact reviewed SHA in the PR's
  finding ledger. Do not auto-resolve or discard threads from either reviewer.
  A new material head requires renewed substantive coverage according to the
  governing convergence policy; checkpointing is only a review-work
  optimization, not an assurance shortcut.

## Verification

The PR validation job runs:
`python -m unittest tests.test_external_ai_reviewers tests.test_workflow_token_permissions -v`

After protected merge and credentials/App installation, use a new small
main-targeting PR and verify separately that (a) CodeRabbit reports the
current SHA, (b) OCR records the current SHA, generates an artifact with no
budget-skipped/failed tasks for the exercised scope, and posts only its
authorized comments, and (c) the established three required FAR gate
contexts retain their original semantics. On failure, record the exact
external blocker; do not manufacture a green review.
