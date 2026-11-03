# Local Qwen post-execution validation v0.2

Status: Research / no scored efficacy estimate. This maintenance correction does
not rerun or replace the failed original preflight. The original run
[41529850758](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41529850758)
returned zero model responses: both arms timed out at 300 seconds. The paired
study remained unexecuted. The separate completed #605 pilot retains its
control 11/30 and treatment 10/30 result; it demonstrated no FAR advantage.

The exact original automatic-scoring workflow is retained in
[`local-qwen-original-workflow-v0.1.yml`](local-qwen-original-workflow-v0.1.yml),
SHA-256 `dcb291b3b73f6062d99b057f55a24b421418957311426e09ecf842db555883bf`.
Its control/treatment commits, failed run and original branch history are
unchanged. Maintenance pushes now run offline checks instead of repeating the
old scoring study. The legacy live CLI fails closed. A new live trial requires a
separately registered successor condition and new output location; validation
v0.2 is not retroactively the original frozen harness.

## Finding ledger

All three original findings reviewed head
`7dc830b2504cb11b096b8f88fd74072ddeb20790` and remained reproducible in the
starting head `5623d5c282cafaf4689dc304c6d6b16811083fc8`. Main was integrated through
`2e0edb8888c89450198588b86506619ba732ff85`, bringing in the existing #605
trusted-host scorer rather than introducing another grading implementation.
The corrective commit is the commit introducing this record.

| ID | Original finding | Root cause and reproducer | Disposition and verification |
| --- | --- | --- | --- |
| LOCAL-FINISH-01 | [4448166610](https://github.com/n0tf0und0ut/Project-FAR/pull/607#discussion_r4448166610), thread PRRT_kwDOTH_vCM6y4PbD | A provider `done=true, done_reason=length` was accepted as completed inference. | Fixed: require `stop`, matching model and positive integer tokens; length/missing finish reason remains INCOMPLETE and invokes no grader. Tests `test_token_limit_completion_cannot_be_scored`, `test_missing_termination_reason_cannot_be_scored`. |
| LOCAL-ORACLE-01 | [4448166618](https://github.com/n0tf0und0ut/Project-FAR/pull/607#discussion_r4448166618), thread PRRT_kwDOTH_vCM6y4PbI | Submitted Python shared an interpreter with unittest and expected answers, allowing monkeypatched assertions to forge success. | Fixed by reuse of `workflow_efficacy_free_agent.grade`: expected-value comparisons run on the trusted host, outside candidate execution. Candidate monkeypatch regression executes actual Python through the test transport and fails its wrong outputs; analyzer recomputes retained comparisons even when hashes and claimed verdicts are changed together. |
| LOCAL-CLEANUP-01 | [4448166623](https://github.com/n0tf0und0ut/Project-FAR/pull/607#discussion_r4448166623), thread PRRT_kwDOTH_vCM6y4PbL | Timing out Docker's client did not guarantee removal of its daemon-managed container. | Fixed by shared scorer's uniquely named per-case containers and unconditional `docker rm --force` cleanup. Timeout regression verifies six distinct containers each receive cleanup. |
| LOCAL-REPLAY-01 | This audit on the same reviewed head | Analyzer trusted summary outcomes and lacked provider-completion evidence and independent grade reconstruction. | Fixed: persist canonical provider JSON, bind it to output/source/tokens, reconcile full prompts, replay trusted comparisons, reject duplicate JSON keys, invalid numeric telemetry, malformed digests and extra pair files. Synthetic complete and adversarial fixtures are validation inputs only. |

Provider JSON is the parsed provider object serialized canonically; it is not
represented as an exact transport-byte capture. Self-recorded hashes detect
inconsistency, not a coordinated rewrite or provider authenticity. No live model,
customer, independent adjudicator or paid provider was invoked in this repair.
Docker is unavailable in the maintenance runtime: the adversarial grading test
runs the candidate interpreter through a local test transport, and container
lifecycle behavior is checked with mocks. Hosted validation must also pass; these
controls do not establish real-world model reliability or treatment benefit.

## Verification

```bash
python -m unittest tests.test_workflow_efficacy_internal_fixtures tests.test_workflow_efficacy_local_ollama tests.test_workflow_efficacy_local_analysis tests.test_workflow_efficacy_free_agent tests.test_workflow_efficacy_free_agent_analysis -v
python -m tools.workflow_efficacy_local_ollama contract
```

The focused suite passed 70 tests. Any exact-head review, protected workflow
repin requirement and required hosted checks remain separate merge prerequisites.

## Offline transport dependency correction

**LOCAL-OFFLINE-DOCKER-01** — [exact-head assurance job 126134972224](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41698416079/job/126134972224) on `41af707f7f411de7cd8727cf6f5bdf524052e3e5` rejected both `tests.canonical` and `repository.health-full` with `FAR-VAL-TRACE-001`, although their commands exited zero. Artifact `13264462159` records the undeclared `/usr/bin/docker` executable. This is a real fixture dependency violation: `test_grader_rejects_unexecuted_docker` mocked `subprocess.run`, but the reused grader launches candidate clients through `capture_candidate_process` and `subprocess.Popen`; only cleanup was intercepted.

Before correction, a process-launch tripwire failed at `['docker', 'run', '--rm', '--name']`. With a harmless local canary executable named `docker`, the original fixture passed while launching six real clients, each exiting 127; the unchanged runtime policy rejects that executable. The corrected fixture mocks the shared candidate-transport boundary, prohibits `Popen`, verifies six attempted comparisons and six mocked cleanup calls, and still requires unexecuted, unsuccessful, ungraded output. Disposition: fixed by the commit introducing this section. No executable whitelist, manifest, assurance rule or production grading behavior changes.

The 70 focused tests pass after correction. Local native `strace` replay is blocked by `PTRACE_TRACEME: Operation not permitted`, so the canary and process-launch prohibition provide the local regression evidence; they do not substitute for rerunning the hosted traced assurance job on the new head. Original workflows, the failed model preflight and all prior negative observations remain unchanged.
