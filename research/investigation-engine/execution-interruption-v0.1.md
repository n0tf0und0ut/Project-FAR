# Execution interruption and recovery

Status: Research. Recorded 2026-11-03.

The first local selection-v2 campaign began from local source commit
`79048885` and the exact pinned 3B model. The coordinator did not inspect the
eight question contents. The last observed progress reported two completed
workflow slots for the first case and an unfinished model slot. Those progress
observations are not a verified campaign result: the local raw transcripts,
model files and uncommitted external-comparator adapter became unavailable
when the workspace reset. The interruption time and later completed slot count
cannot be reconstructed. Do not score unobserved slots as model failures, count
lost outputs as verified results, or claim that the process remains running.

The repository implementation, original registrations, both frozen selections,
execution profile and test history survive in PR #614. Selection-v2 SHA-256 is
`c10854197fdff2f02785c66ab6ebe1795af1486525fe5885cd917ca939ac0f0a`.
The coordinator still has not read the v2 questions during recovery.

A separately identified hosted recovery campaign uses the same frozen questions,
model bytes and unchanged investigation implementation. Its Ubuntu runner uses
explicit DNS preflight rather than the previous environment's proxy mode. All
three lanes in that recovery run receive the same host policy and budgets.
Environment/transport differences prevent pooling it with local development
timings. This is recovery after missing evidence, not independent replication or
replacement of observed unsuccessful outcomes. All published negative results
must remain visible.

The hosted job preserves partial files even after a bounded execution-step
timeout. Artifacts have explicit retention limits; permanent repository evidence
still requires downloading, hashing and preserving the completed artifact.
The existing external-system adapter's observed development failures are not
promoted to verified raw evidence because its uncommitted files were lost.
The full existing-system comparison and substantive adjudication remain undone.

## Exact-head test correction

Hosted exact-head assurance on `1fb3b04b02c2049a2711bfb68f44f85df761b13d`
reported two loopback `connect()` observations in each canonical test/health
execution, violating their declared no-network dependency policy. The test
commands exited zero; trace assurance correctly rejected the undeclared sockets.
No validation policy or protection is weakened.

The redirect regressions now use native urllib redirect/error handlers above an
in-memory HTTP transport. They still verify refusal, retained HTTP 302 bytes and
absence of a request to the second destination. A positive control executes an
unguarded native opener, follows the same fixture redirect and observes the
second request, demonstrating that the fixture can detect the original defect.
The two affected suites pass 31 tests without opening network sockets. This
changes engineering test transport only, not the frozen investigation program.
