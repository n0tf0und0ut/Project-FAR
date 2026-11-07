# Project FAR current-head PR convergence evidence bundle

Collected on **November 7, 2026 (UTC)** from the authenticated GitHub connection for `n0tf0und0ut/Project-FAR`. This is a dated, **read-only, non-atomic** snapshot. GitHub may change the checks without moving a PR commit. It is neither a merge authorization nor a scientific-validity certification.

## Files

- `project_far_current_head_convergence.md`: human-readable twenty-PR matrix, gate and evidence map, dependencies, findings, scientific limitations, and full five-advisor council analysis.
- `project_far_current_head_convergence.json`: machine-readable complete SHA identities, candidate/body discrepancies, review-state links, current and historical Git blob identities, all three source-bound required checks, direct review-finding links, blockers and dispositions, plus **68 literal GitHub URLs** from the PR descriptions.
- `project_far_council_review.md`: council peer review and Chairman verdict as a standalone report.
- `verify_far_pr_manifest.py`: standard-library Python fail-closed verifier; supports offline invariants and optional authenticated live comparison. It **never writes** to GitHub.
- `test_far_manifest.py`: fifteen offline positive and adversarial unit tests, including simulated live drift and forged check-origin rejection.
- `build_far_manifest.py` and `add_body_link_catalog.py`: fully reproducible formatting of the **manually transcribed, authenticated connector observations**. These are not GitHub clients and do not refresh live inputs. Re-run them only to reconstruct the archived observation, not to certify current GitHub state.

## Validate this snapshot locally

From the extracted directory, with Python 3.10 or newer:

```sh
python3 -m unittest discover -s . -p 'test_far_manifest.py' -v
python3 verify_far_pr_manifest.py project_far_current_head_convergence.json
```

The first command exercises all fifteen tests. The second checks the manifest's SHA/URL/check/finding/aggregate invariants and must output `SNAPSHOT_INVARIANTS_PASS` and `LIVE_NOT_CHECKED`.

## Compare to actual GitHub again

The command below makes only GET and read-only GraphQL requests through GitHub's API. Supply a GitHub token able to read the repo's pull requests, checks, discussions, and GraphQL review threads. Do not put the token in logs or the manifest.

```sh
python3 verify_far_pr_manifest.py project_far_current_head_convergence.json --live
```

Set the `GITHUB_TOKEN` environment variable before running it. A complete successful result ends with `LIVE_RECONCILIATION_PASS`. **Any difference or inaccessible endpoint fails closed**. A drift failure can simply mean a check just completed: re-collect evidence from the new state rather than rewriting outcomes to force a pass. The live check reads the protected main and full open-PR inventory at both the beginning and the end to reject moving targets; it also checks source App IDs, review states, thread identities, individual evidence-file blobs and exact SHA binding.

The actual authenticated live verifier could not be invoked from this container because external DNS/network access was unavailable. Instead, the snapshot was built from authenticated GitHub connector reads, and the verifier's live comparison and refusal paths were tested against controlled simulated GitHub responses. These are different validation claims.

## Principal current findings

- All twenty open heads and protected `main` SHA were re-read after collection; the set and SHAs were stable on that final inventory check.
- Protected main SHA: `eff47bc4fc9e272e87d71ecfc8d559cd1176753e`.
- **17/19 ordinary PRs** had a failing required review-convergence check. #617's review-convergence check was green while its protected repin and merge-authority checks failed and the PR remained draft. #625's review and repin checks were green, with merge-authority still running.
- PR #623 has two open, current exact-head P2 review threads. Its referenced source comments are directly linked in the JSON.
- PR #617 requires an owner-authenticated signature on its protected repin request. No signature was supplied here.
- #490 is a permanent draft intake, intentionally **NEVER MERGE**.
- #608 is the explicit predecessor of #614. #625 should precede #597 for README/W4/W6 digest integration once independently authorized.

## Evidence/authorization limits

Only one principal current-head evidence file per PR was Content-API verified, with historical byte comparisons where cited; all explicit body GitHub URLs were catalogued, but historical run logs and linked ZIP contents were **not** all opened or revalidated. The branch-protection direct API returned HTTP 403, although the branch metadata exposed source App IDs for the three required contexts. No PR, workflow, signature, rule, protected branch or frozen research result was modified during this task.
