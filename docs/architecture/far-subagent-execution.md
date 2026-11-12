# FAR subagent execution

Status: provisional execution architecture. This is not a change to FAR theory,
claim acceptance, or the isolation classification doctrine.

The single implementation is [`tools/subagent_orchestration.py`](../../tools/subagent_orchestration.py).
It coordinates existing specialist skills using an `OrchestrationPlan`, a typed
`AgentRuntime`, and content-addressed tasks and reports. `far_research_plan()`
builds a reference graph for all 14 FAR roles, including the terminal coordinator,
from the skill files currently on disk. A coordinator
receives all specialist reports and performs final integration. Specialists are
read-only under this protocol; they do not write shared repository state.

## Graph and context

Every agent has a bound skill path and SHA-256. Before invoking anyone, the
orchestrator verifies every runtime's instruction hash, sandbox identity,
isolation signal, shared-state declaration, and repository-tool authorization.
The graph must be acyclic, and the coordinator must be its terminal node with
every specialist as a dependency. A dependency may be used for ordering while
its report is hidden.

An agent can declare `context_ids` to receive only the named `ContextArtifact`
values. A missing artifact fails before the first invocation. Dependency views
are `full`, `findings`, and `claims-only`. The last view contains claim IDs only;
it carries no upstream disposition, evidence, recommendation, or narrative.
The engine binds the local task to its report. The reasoner adapter separately
hashes the redacted provider packet and checks that the provider echoed that
hash before binding the report to the local task. A report citing an evidence artifact
or finding absent from that packet fails closed.

For a clean-room lane, set `clean_room=True`, an explicit `context_ids` allowlist,
and `dependency_view=CLAIMS_ONLY`. Names such as `prior_far_verdict`,
`preferred_conclusion`, and `synthesis` are rejected as context IDs. The runtime
must assert `clean_room_verified=True` as well as verified isolation and no
repository tools. The supplied artifact text and objective must still be
reviewed and frozen by the operator: metadata checks cannot detect disguised
conclusions in prose or prove external I2 independence. The reference plan
does not claim a clean-room or independent stage; a separate plan and the
applicable [isolation doctrine](../doctrine/isolation-classification.md) control
that claim. The `ReasonerLaneRuntime` adapter leaves clean-room verification
false, so a runtime that can establish the required controls must supply that
capability explicitly.

## Reports and failure gates

The runtime returns typed findings with claim IDs, dispositions, statements,
and references to visible input. Task ID, agent ID, and input hash are checked.
Runtime exceptions become durable failed reports; failed dependencies block
their dependents. A support/contradiction pair for the same claim is preserved
as a conflict and blocks coordinator invocation, even under a majority.

`RunStatus.COMPLETED` means the graph executed without a detected binding,
runtime, or support/contradiction failure. It is **not** an acceptance,
promotion, evidence closure, or independent audit verdict. The applicable FAR
quality gates and claim-level evidence policy remain separate requirements;
in particular, I-class internal reasoning cannot itself justify acceptance.

## Runtime integration

`CallableRuntime` can exercise a plan locally. `ReasonerLaneRuntime` adapts the
repository's `ReasonerLane` abstraction and strictly parses a JSON report while
redacting credential-shaped text in outbound prompts. It rehashes the
transmitted skill and context text, rejects credential-shaped routing metadata,
and computes the wire input digest over canonical JSON with the wire hash field
omitted. An invocation receipt binds the wire input digest to the request and
response byte digests. The result digest includes these receipts and the
preflight capability snapshot, including the lane's declared model, provider
and prior exposure. A missing response digest means the adapter obtained no
hashable response. These are local observations and declarations, not provider
signatures or independent verification of sandbox controls. Other providers can
implement `AgentRuntime`. A serial local run tests functional routing, but
does not establish independently isolated agents. The plan hash and result hash
make repeated identical inputs comparable; no hash establishes factual truth.

Run the focused tests with:

```bash
python -m unittest tests.test_subagent_orchestration
```
