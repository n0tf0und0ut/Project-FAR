# Living research to factory: one-candidate advisory bridge

Status: **Research / unpromoted engineering pilot**. This is an observation-to-proposal adapter, not scientific adjudication, model-driven investigation, autonomous coding, a deployed service, a source of merge authorization, or a new Research-to-Accepted promotion route.

## Purpose and trust boundary

The permanent rolling inbox [PR #490](https://github.com/n0tf0und0ut/Project-FAR/pull/490) is a **never-merge** research data surface, not an executable instruction source. Its branch is re-created from protected main by the existing living-research workflow. The existing separate living-research snapshot promotion path remains controlling. Do not copy `.rolling-pr-anchor.json`, execute code from the rolling inbox, or merge/close PR #490 to deliver the adapter.

`tools/living_factory_bridge.py` reads **one** named `FAR-LIT-XXXXXXXXXXXXXXXX` record in the exact current head of the open, draft #490. It validates that the PR is the expected owner/repository and rolling branch; resolves the current protected main SHA as a *potential* factory target; fetches the candidate from GitHub pinned to the PR head; checks returned path, regular file type, base64, exact byte length, Git blob SHA-1 and independently calculated source SHA-256; and validates the candidate's Research-only lifecycle and governed-question routing. All network requests are bounded, read-only HTTPS GETs to `api.github.com`, with no redirect following and no token.

The adapter **never interprets titles, abstracts, scholarly query strings, or provider descriptions as task instructions**. It derives one fixed-form advisory investigation objective and explicit acceptance requirements solely from trusted *structural identifiers* (candidate ID, bound governed-question IDs, Git identities and hashes). Untrusted titles and source keys are retained separately for display and provenance. Invalid IDs, malformed JSON, duplicate keys, non-finite values, content spoofing, missing routing, excessive size, abnormal status or changed authority boundaries are rejected.

The output is a deterministic, fingerprinted `far-software-factory/living-bridge-proposal/1` JSON object with `execution_authorized: false`, `submit_to_queue: false` and `ADVISORY_REQUIRES_INDEPENDENT_TRIAGE_AND_AUTHORIZATION`. It contains a `proposed_work_order` validated against the existing `far-software-factory/work-order/1` schema. **A schema-valid proposed order is not permission to submit it.** Only a separate governance-authorized operation could enter work into the factory queue. The adapter imports only the existing validator; it does not open an SQLite database, call `Factory.submit`, create PRs, dispatch workers, request independent reviews, or merge anything.

### Run

From repository root, Python >=3.11:

```bash
python tools/living_factory_bridge.py --candidate-id FAR-LIT-0180C9D6CDB2EBB2
python -m unittest discover -s tests -p 'test_living_factory_bridge.py' -v
```

The output goes to stdout; redirect to a **nonrepository** review artifact if needed. A nonzero exit denotes missing or invalid source/provenance. The network CLI deliberately requires access to the public GitHub API. Tests use deterministic injected read-only GitHub responses, with **no network, credentials, or live operations**.

### Pilot witness

A local, read-only pilot used candidate `FAR-LIT-0180C9D6CDB2EBB2` at recorded rolling inbox head `55be7bdb8d2a9c7fe1caaf877ca1f3020f420c4f`, target main `47a326d61ba9f47f42028d6875896de737fdb2d9`, and candidate Git blob `239d0198ec403dbac96dc9d6cfc8352ba331a5b1`. The adapter verified the blob against byte-exact data obtained through the authorized GitHub connector and produced an advisory proposal. These are *pinned historical observations*, not evidence that the current moving inbox head or main has those identities now. This witness did **not** submit a task, start a worker, change a research claim, or mutate a GitHub branch. No signed independent GitHub review is implied by local testing.

### Dedupe and limits

The proposed order ID hashes the pinned source commit, candidate ID, Git blob, target base SHA and repository identity. Repeating the same inputs produces byte-identical output and the same order ID. A changed candidate, source commit, or target base produces a **new** proposal for independent assessment, rather than silently replacing prior provenance. This is per-snapshot idempotence, not global semantic deduplication across changing inbox heads. The SHA-1 and SHA-256 references detect data mismatches but do not certify scientific truth, user authorization, or cryptographic signer identity.

The current pilot accepts only `CANDIDATE_LITERATURE` in `UNREVIEWED_CANDIDATE` / `DISCOVERED` state with explicit Research-only lifecycle flags. This deliberately excludes other record types, other repositories, queued execution, broad scanning, claim adjudication, and auto-promotion. The one-candidate pilot does not establish autonomous-agent reliability or commercial advantage. Future extension requires a separate authorized change and independent exact-head review.
