# Agent re-entrancy: bounded operational investigation

Status: Research — prospective internal protocol, not Accepted theory.
Base: protected main aa5cb8faf36b5e033bb96bf6e9f7f3f351387913 (2026-11-12).
Scope: synchronous re-entrant execution of the **same in-flight AgentTask** inside tools/subagent_orchestration.py. This is not a general retry controller or a claim about arbitrary model-generated loops.

## Question and objective

Can a runtime callback recursively invoke the same content-addressed task before the outer invocation finishes, causing redundant worker execution with no new input, and can a minimal context-scoped admission guard prevent that duplicate without blocking normal, distinct, or sequential execution?

**H0:** The current engine already rejects duplicate in-flight invocations, or a guard has no measurable benefit on the preregistered workload.
**H1:** The current engine permits duplicate in-flight invocations; a guard prevents them while retaining legitimate progress and all current failure/report/receipt semantics.

## Source-first discovery gate

Inspect the exact production orchestrator, _build_task, runtime adapters, original unit tests, permissions and receipt lifecycles. Reproduce a two-level same-task re-entry before modifying production code. If this counterexample does not reproduce at the pinned baseline, do not add the guard.

## Mechanistic model and contract

Identity is the exact existing task_id, generated from plan/run/agent/input. The execution-context active-task set is a scoped implementation detail, not a new durable task store. Re-entry from the *same logical context* with the *same task identity* must not issue another runtime.invoke while the first is active. A rejected nested attempt must remain a typed failed report, not silently disappear. Removing an active identity after normal return or exception is mandatory. Different task identities and a subsequent non-overlapping execution of the original identity remain permitted. Parallel independent contexts are intentionally outside this guard's cross-process deduplication claims.

Safety predicates: (S1) no overlapping duplicate same-context runtime invocation for one task ID; (S2) every denied nested invocation yields a non-success result; (S3) no forbidden mutation to frozen evidence; (S4) pre-existing report binding and capability gates remain unchanged; (S5) distinct-run nested invocation and sequential repetition remain allowed. Bounded progress predicate: under finite callback completion and finite plan, this guard removes the edge from an active task to itself. Global liveness is NOT claimed; external provider calls remain potentially unbounded and cross-process duplicate work remains possible.

## Frozen controlled comparison

Control: source from pinned main without treatment code. Treatment: same source except the guarded admission transition, tested using the identical frozen deterministic, in-memory callback workloads. These are executable code path tests, not live model outcomes. Unit of pairing is one task identity under one fixed callback behavior.

Cases and primary estimands (fully specified before outcome exposure):

1. Same task, same run ID and objective, one recursive callback: count actual runtime.invoke calls; require control=2, treatment=1, and nested result FAILED only in treatment.
2. Different nested run ID: count calls; require both baseline and treatment=2, with no new intervention.
3. Same task across two sequential independent orchestrations: count calls; require both baseline and treatment=2.
4. Callback raises after guarded nested attempt: result must be FAILED and later sequential execution must be possible.

Primary safety criterion: no treatment same-context duplicate invocation and no control-path failure for clean cases. Secondary: reduced redundant invocation count in case 1. Negative control: case 2. Regression control: case 3. Failure control: case 4. There is no claim of significant population effect: these are deterministic constructed cases, not independent random samples. No p-value, confidence interval, human or model performance claim is authorized by them.

Execution sequence: commit this protocol first; add and run baseline reproducer on the unchanged production file; record original observed failure; then modify only the narrow enforcement boundary; run the same tests, existing orchestrator/mailbox suites, bounded exhaustive model transitions, and hosted validation. Preserve the original reproduction output and failure observations in an amendment that identifies the exact test and commit, without rewriting this registered protocol.

## Independence and falsification

Independent exact-head code review is necessary for PR readiness but is not I3 scientific replication. A second local Qwen or Codex context remains internal unless an external party controls the work. Publish a clean-room statement-only packet and executable repro steps; an I3 claim requires a qualifying outside operator, verified provenance and sealed outputs. Absence of I3 must be recorded as NOT ESTABLISHED.

## Claim ceilings

C1: finite transition-model safety only if exhaustively checked or proven under stated bounds.
C2: operational enforcement for tested same-context task identities only.
C3: controlled deterministic work reduction, not live autonomous-agent effectiveness.
C4: independent external scientific replication not established until an external team actually executes its own study.

Stop rather than claim recovery or superiority from a successful synthetic test. No VENTRALIS comparison without shared benchmark and evidence.
