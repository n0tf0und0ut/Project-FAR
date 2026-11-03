# Internal preexecution review v0.2

Status: **Research; internal review only. No v0.2 model calls yet.**

V0.1 stopped after three genuine preflight trajectories: all substantive answers correct, strict success 1/3, one unrequested simulated file write. Its original source, protocol, workflow, raw bytes and stopping record remain preserved. It was neither rerun nor pooled. A separate policy version clarifies two interface rules exposed by that failure, using fresh preflight inputs. The 24 unexposed scored task objects, model and thresholds are unchanged. This successor is development informed by v0.1, not an independent replication or causal before/after experiment.

The coordinator and a separate read-only internal reviewer inspected the runner, protocol, both workflows, preserved v0.1 evidence and the CI hygiene repair before successor inference. All 48 targeted tests passed. The reviewer independently replayed the three v0.1 traces from their original frozen checkout; the result exactly matched the hosted report. No new concrete blocking defect was found at these reviewed SHA-256 identities:

| File | SHA-256 |
| --- | --- |
| `tools/tool_agent_reliability.py` | `60e80696e5ddf7df17f60d69839fe0fc00ca5ddfdad8f8a5a0f3aee3761f9f7c` |
| `.github/workflows/far-tool-agent-reliability-v02.yml` | `587e3ab14983aa582e6ff39171924de7da5b98e942d569ab8c40b6bf2b441d4f` |
| `protocol-v0.2.json` | `4ee2ef14e3d0dfff9823d42ac36d7e272bd38852fa8f7c5448bcee578a58ce29` |
| `tools/check_repository_hygiene.py` | `997dc1d9934f64be349fc65e368247b9cafc8c31c29c39109c71fd0352ba230d` |
| `tests/test_repository_hygiene_runtime_paths.py` | `f30738cc152ba149d3a076ab65608c01d040c611b19d3ad911d3996587912a72` |
| `tests/test_tool_agent_reliability.py` | `f54aad3247f855adb2ffd3cb3efccc508b20f2af7a0cfaea6d888128654ff0bc` |

The policy ID and system-prompt digest are explicitly retained and checked during replay. Current live CLI refuses v0.1 launches. Complete v0.2 raw preflight evidence from the exact source, all three valid traces, at least two successes and zero unsafe writes are still required before any broader call. Strings are not coerced into integers by the grader.

RLY-005 records the new CI defect: original full repository health returned 136 passed and one failure because its YAML checker required runtime artifact directories to preexist as source files. The correction recognizes only direct `with.path` values of official artifact upload/download steps in actual root GitHub workflows. Seven adversarial tests retain checks for other source inputs, nested paths, lookalike actions, non-workflow data and malformed step shapes. No workflow-wide exemption, generated placeholder tree, check suppression or protected-gate relaxation was introduced.

RLY-001–004 remain documented in the v0.1 review record with their reproductions and regressions. Scientific outcomes, internal software scrutiny, exact-head external review and protected merge authorization remain separate. This record establishes neither general reliability nor I3 independence.
