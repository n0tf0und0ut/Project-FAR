# FAR versus active generic checker: autonomous-agent causal study

Program: `FAR-AGENT-GENERIC-CAUSAL-001`
Status: **Research candidate; NOT FROZEN; NOT AUTHORIZED; NOT EXECUTED**

## Observed necessity and scope

Protected-main SWE-agent v3 `FAR-SWE-V3-001` currently registers
`baseline`, `placebo`, and `far`, with `far_minus_placebo` as its primary
contrast. It contains no matched active generic-checker arm; its FAR treatment
capsule and sealed task cohort are uninstantiated and its launch flags false.
No observational/statistical analysis of that three-arm design can identify
`far_minus_generic_checker`. The internally exposed finite checker comparison
also cannot establish autonomous-agent success.

This **separate prospective two-arm candidate** targets precisely the missing
contrast. It neither mutates the original v3 sealed design nor reinterprets
its negative or absent evidence. The old v3 gate cannot grant permission here,
and this candidate does not grant permission under v3. The exact candidate
registration was committed before this verifier and test source; prospective
independent review and normal protected-main promotion must occur before any
independent task release. If the old or new contracts conflict on shared assets,
stop; don't silently substitute parameters.

## Experimental contract and limitation

`protocol-v0.1.json` records the prospective contrast, minimum population
conditions, paired run equivalence, outcomes, fixed analysis, critical
invalidity rules and nonclaims. Source identities are pinned to protected main
`a9eb83eee705ba3e242b3f329712f6352761c6c1`. The strict FAR verifier
is `mechanization/far_mechanization/contract_v2_strict_v11.py`; the active
generic checker is `tools/efr_generic_collision_checker.py`. Those paths are
historical implementation candidates, not proof that either is connected to
a live agent. They must be wrapped behind an equal-capability tool interface
and independently verified **before** freeze. The generic checker can match
finite collision detection; the treatment additionally evaluates FAR-specific
evidence integrity. Both arms must receive the same underlying task facts and
opportunities to invoke a checker. When an agent never invokes a checker,
record that fact; never drop the run from the primary denominator.

For each task, run two fresh repetitions per arm in isolated identical snapshots,
counterbalance order, and freeze allocations before any outcomes. The primary
estimand is the task-weighted mean difference in independently graded resolution
probabilities, FAR minus generic. The minimum practically important difference
is 0.10. The candidate fixes **24 tasks across exactly six provider-stable
repositories, four tasks per repository**, with two runs per arm/task (96 frozen
slots). This deliberately small fixed cohort is **not** a power claim.
An independent prospective precision/power review must decide whether that
minimum permits a meaningful test **before** any task identities are unblinded;
otherwise publish an explicit inconclusive design finding or a new prospective
version, never quietly add outcomes or change thresholds. Repetitions are
dependent within task and are never counted as 96 independent tasks.

A positive treatment effect is an intention-to-treat effect of the checker
*package* against the generic active package. It does not by itself establish
causal mediation by evidence-integrity behavior. The latter needs a separately
preregistered intervention/ablation and evidence that downstream choices
differed. Apparent activation, intervention, and task success are distinct.

## Independent roles and prospective gates

An independent custodian must source, screen, seal and retain the complete
external task cohort with source identities, eligibility exclusions, exact
repository snapshots, hidden grader, hashes, and a one-to-one identity ledger.
The task curator and judge must be genuinely separate from treatment authors,
with prior exposure and conflicts disclosed. Private task identities must not
be released to this PR's authors or the model harness before sealed review.

Before the sacrificial pilot, separately verify exact protected-main promotion,
frozen FAR and generic wrapper bytes, agent/model/environment/budget identities,
independent task intake audit, hidden grader, signed custody seal, paired
randomization, a genuine observer-owned append-only logging channel, and
evidence-store restoration. A written, identity-bound prospective authorization
must be issued by a real authorized party. Before the confirmatory study,
independently verify the excluded pilot and all updated launch bindings. Neither
a true flag nor a self-authored hash grants execution.

`launch-state-v0.1.json` intentionally contains **zero supplied external
credentials, seals, or authorizations**. It cannot turn a model or benchmark on.

## Mechanism evidence: rawest available records

A trusted observer *outside the agent's writable workspace* must capture each
run's raw tool requests/responses, context continuation, pre/post state, tool
identity, model/provider identity, complete task/runtime configuration, and
termination. A log entry can be marked `activated`, `not_triggered`, or
`tool_failed` under the frozen contract; **every run** must retain its state,
including no-call runs and negative outcomes.

Each `far-agent-mechanism-receipt/1` record binds an exact
`far-agent-tool-log/1` raw byte stream and the candidate event by SHA-256,
run identity, arm, task, repetition and five raw payloads. The validator
checks canonical base64, event sequence, exact linkage, arm/tool identity,
duplicates, and missing data. It returns
`STRUCTURALLY_BOUND_UNATTESTED_...` deliberately. **No local checksum
establishes the observer's identity, a genuine model/tool invocation, a correct
enforcement decision, or the absence of omitted events.** Those require a
separately trusted execution service, external signature/key provenance,
independent source replay of the actual invoked checker, and terminal-state
grading. The tool log and receipt formats are prospective minimum contracts;
their compatibility with a real harness must be demonstrated before launch.

A receipt alone cannot establish that FAR caused a better result. The primary
causal estimate must use the frozen intention-to-treat sample, never select only
runs where FAR activated.

## Verify without running any agent

```bash
python research/external-validation/far-agent-generic/verify_candidate.py
python -m unittest discover -s research/external-validation/far-agent-generic \
  -p 'test_verify_candidate.py' -v
python research/external-validation/far-agent-generic/verify_candidate.py --require-launch
```

The final command **must exit 3**, indicating launch is denied. All tests use
synthetic log bytes and mutate their contents; they are not agent or model runs.
These commands are safe on untrusted candidate content only in the ordinary
isolated CI environment and never require provider credentials.

## Decision, provenance, and completion

- **Author-generated artifacts:** candidate protocol, no-launch record,
  structural validator and adversarial tests. These are neither independent
  preregistration approval nor external task custody.
- **Frozen prior evidence:** SWE-agent v3 design, its negative launch state,
  earlier scripted repair and finite semantic checker observations remain
  unchanged.
- **Unresolved external prerequisites:** task custodian, independently signed
  seal, selected model/harness, operational observer and verifier, excluded
  pilot, exact-head review, prospective signed launch authorization.
- **Current verdict:** `NOT_EXECUTED`. No new model calls, tool-using runs,
  independent outcomes, causal advantage, or scientific promotion.

Research status must not be promoted from test success or PR creation. Normal
protected GitHub review and all required checks remain separate; no merge or
external publication is claimed by creating this candidate.
