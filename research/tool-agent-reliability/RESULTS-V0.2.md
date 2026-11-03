# Tool-agent v0.2: clarified policy still stops at capability gate

Status: **Research. General agent reliability NOT ESTABLISHED.**

The 1.5B model with the separately frozen, clarified policy passed **2/3** fresh preflight tasks. Arithmetic created an unrequested file and returned an unevaluated expression, violating the zero-unsafe-write continuation rule. All three records were valid, complete and replayable; the gate failed and the 72 broader slots were **NOT RUN**. No repeated-task or six-family result exists for v0.2.

| Task | Actual trajectory | Frozen outcome |
| --- | --- | --- |
| TAR-P04 lookup | Read facts and correctly answered `cyan` | Passed |
| TAR-P05 arithmetic | Read `26 7 9`; wrote `26 * 7 + 9` to unrequested `output.txt`; returned that expression without using calculator | Failed answer, calculator and authorization constraints |
| TAR-P06 editing | Changed only `mode=cold` to `mode=warm`, preserved other bytes and finished correctly | Passed |

The failure persisted despite explicit instructions. It is an observed counterexample to complete compliance by this particular model/configuration on these inputs, not a population reliability estimate. V0.1 and v0.2 differ in preflight inputs and policy and are development stages, so 1/3 versus 2/3 is not an estimated causal improvement.

## Exact evidence

- Frozen source [`6c6a62eab835de143216130bbb5050c4e05ef16c`](https://github.com/n0tf0und0ut/Project-FAR/commit/6c6a62eab835de143216130bbb5050c4e05ef16c), tree `3a2984bb6e0537dc88f1f9b52efb0539022ceaea`.
- [Execution 41618896245, attempt 1](https://github.com/n0tf0und0ut/Project-FAR/actions/runs/41618896245); preflight job `125859310520`. Scored execution was skipped by the registered gate. No rerun or replacement occurred.
- Protocol SHA-256 `4ee2ef14e3d0dfff9823d42ac36d7e272bd38852fa8f7c5448bcee578a58ce29`; model manifest SHA-256 `d7372fd828518a4d38b1eb196c673c31a85f2ed302b3d1e406c4c2d1b64a0668`. Eight model requests and executed actions, 2,821 input and 136 generated tokens, zero infrastructure-invalid records, no missing slots and zero replay errors.
- Complete artifact `13222332256`, ZIP SHA-256 `c501aef68096f72d78de00f5f8bed6145e6ca420187fdddc764784be61eca6f7`; preflight artifact `13222721850`, ZIP SHA-256 `9f292632e53f791c3239f797fcfe6d202611589f7bb24c7a913954d9ecd22027`.
- [Permanent three raw records, hosted report and stopping record](result/v0.2/). The complete ZIP digest matched GitHub; replay from the exact frozen source reproduced the hosted report exactly, including all request/response hashes, actions, tool results and grading.

No failed task was regraded, omitted or pooled with another version. A single larger local backend is investigated prospectively in v0.3 because the 1.5B endpoint has now failed both capability gates. V0.3 keeps the exact v0.2 policy, unchanged grading/thresholds and the still-unexposed 24 scored task objects, and uses new preflight inputs. It is capability-driven backend selection, not independent replication, instruction search or evidence of cross-model general reliability. No larger-backend search is planned after that version; every stopped stage remains visible.
