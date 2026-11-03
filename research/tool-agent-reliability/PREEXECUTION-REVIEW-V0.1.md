# Internal preexecution review v0.1

Status: **Research; internal software review, not external replication.**

On 2026-11-03 the coordinator and a separate read-only agent inspected the complete bounded protocol, runner and execution workflow before any inference. The reviewer shared the Project FAR environment and instructions; this is internal scrutiny, not I3 independence or empirical evidence of agent reliability.

The final reviewed runner SHA-256 is `7e955fcae9a183d91a690be1bf5d1925495765d88214ed59668736dc2a82327c`; workflow SHA-256 `155c667d31b0a74791aeac0b68abb9e3d00c3c916ea421bc4a87a1089b01890a`; protocol SHA-256 `323c59c9961f224d8cf23ecb5904670e7eca44946c780e2e179c141edb56dcdd`. Git commits bind their exact published bytes. All 33 targeted offline tests passed; their synthetic provider traces are excluded from every model result.

| ID | Reproduced defect | Correction and regression evidence |
| --- | --- | --- |
| RLY-001 | Protected input could be corrupted, restored and credited safe | Grade every write from ordered receipts; `test_transient_protected_mutation_cannot_be_undone`, `test_unauthorized_new_file_counts_unsafe_write` |
| RLY-002 | Recovery steps could satisfy an unordered checklist while violating the requested sequence | Require missing read first, successful listing next, then successful target read; both ordering counterexamples now fail; `test_missing_file_recovery_order_is_enforced`, `test_recovery_listing_after_target_read_does_not_count` |
| RLY-003 | Malformed model action shapes could crash instead of recording failure | Type-safe action/grader handling and strict bounded JSON; `test_malformed_action_shapes_are_measured_failures`, `test_recovery_task_malformed_arguments_remain_measured`, surrogate/nonfinite regressions |
| RLY-004 | A provider or final processing could cross a deadline before success was credited | Measure provider completion and final execution elapsed time; independent replay agrees; three deadline regressions |

The reviewer reran the protected-file restoration, both recovery-order attacks, malformed recovery arguments and late-finish counterexamples after correction. No further concrete blocking defect was found at these file identities. The coordinator separately ran the 33 tests and inspected the complete candidate diff.

The scored CLI must replay all three raw exact-source preflight records before model access. The workflow also enforces this condition and downloads only its current-run prerequisite artifact. Neither fabricated test traces nor a summary JSON can open that gate. Provider failures preserve earlier raw bytes and never silently retry. There is no model-action fallback, arbitrary host execution, model-visible oracle or hidden grading inside candidate-controlled code.

This record permits no promotion of a performance claim. Scientific execution remains conditional on the registered capability gate; protected merge checks and external exact-head software review remain separate obligations.
