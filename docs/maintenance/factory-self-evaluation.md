# Software factory: self-evaluation preregistration (Research)

This is an operational **Research** protocol for issue [#629](https://github.com/n0tf0und0ut/Project-FAR/issues/629). It is not accepted FAR theory, an executed comparative trial, an independently verified delivery, or a claim of superiority. The controlling `AGENTS.md`, Research Execution Charter, and existing protected PR policy are unchanged. PR #630 is an unmerged research controller and is not privileged over other candidate controllers.

## Objective and hierarchy of evidence

**Question:** Does an autonomous software factory improve engineering throughput, reliability, cost, and human intervention compared with the current human-directed, agent-assisted development workflow?

Three distinct layers must be independently demonstrated: (1) controller safety and source provenance; (2) individual code-change correctness, before/after tests and protected GitHub delivery; (3) comparative improvement over the existing workflow. Passing one layer does not imply the others. A green self-generated test receipt cannot authorize a merge.

The registered protocol is [`research/factory-evaluation/protocol-v1.json`](../../research/factory-evaluation/protocol-v1.json). It pins the main SHA observed at drafting, the eligible task classes, prospective sampling rule, randomized parallel-group control/treatment workflow, resource ceiling, denominator, primary outcome, secondary metrics, required provenance, safety-stop conditions and nonclaims. It uses eight *prospectively admitted, separately assigned tasks (four per arm)* solely as a diagnostic pilot. The small task count cannot support a general superiority claim. There are no fabricated task outcomes or historical cost figures.

## Preregistration and freeze

1. Validate with `python tools/factory_evaluation_contract.py research/factory-evaluation/protocol-v1.json` and `python -m unittest discover -s tests -p test_factory_evaluation_contract.py -v` (Python >=3.11).
2. Merge this candidate only after required independent review, source-bound checks, and protected App authorization. Preserve the exact protocol bytes and SHA-256 of the reviewed, protected-main blob. **Before that merge the protocol is a candidate, not frozen.**
3. After protected merge and before any experiment, record the main SHA and protocol SHA-256 in a trusted, immutable registration receipt. **Before the first task**, independently review and immutably register a separate execution manifest binding both arms to implementation revisions, configurations, models, prompts/tool allowlists, runner image and permitted adaptation policy. Do not select a controller after starting the cohort or silently change tools midway. A changed implementation requires a new versioned cohort, preserving original results. Retrieve the trusted protocol receipt when validating results with `--expected-sha256`. A changed protocol must be versioned and independently re-reviewed.
4. Select the first eight eligible post-registration work orders using the frozen eligibility rule. **Exclusions are decided only before allocation.** Independently lock exclusion reasons, task IDs, exact original main/base SHA per task and test-oracle digests **before allocation**. An independent evaluator then obtains an unpredictable seed, records it with provenance and allocates exactly four tasks to each arm by sorting SHA-256(seed + task ID). **Each task executes in one arm only against the real protected target**. A contestant altering an oracle after allocation does not make a task ineligible: retain the task and record failure/unknown and a safety stop when warranted. Interleave arm slots strictly (four each) with a seed-determined starting arm and retain protected-main drift, non-starts and failures; never swap allocated tasks.
5. Use zero paid provider spend under this initial protocol. A real provider billable execution requires a new reviewed budget or a separate authorized, explicitly versioned protocol. Current model credentials, paid budget, isolated runners, and candidate task admissions have not been verified.

## Execution and interpretation

For each arm/task, a trusted observer should record: registration digest, task and baseline SHA, agent identity/model, environment and oracle digest, raw test logs/hashes, wall time, billed provider cost, attempts, human interventions, exact PR candidate SHA, independent review reference, protected check run IDs, protected merge SHA and observed main ancestry. The declared primary denominator includes all eligible tasks allocated to each arm, even blocked, timed out, never started, or abandoned. Success requires a correctly verified change and independently observed protected delivery within the fixed budget. No PR, no delivery.

Require fresh isolated agent sessions and task workspaces. Do not share diagnoses, source patches, reviewer feedback, prompts or private session memories between arms until all allocated tasks are terminal. Retain contaminated tasks in the denominator but label invalid causal comparisons **INCOMPARABLE**.

Run baseline and candidate tests for every code change. For changes that cannot have a failing baseline (feature or maintenance), record the relevant original behavior and required new behavior separately rather than manufacturing a red test. Changed environments, models, or test oracles without credible controls make causal comparison **INCOMPARABLE**, not improvement. Self-reported model review does not replace independent exact-head review. Treat `UNKNOWN`, `BLOCKED`, `REGRESSION`, `NO_OBSERVED_IMPROVEMENT`, and `INCOMPARABLE` as valid outcomes, never cherry-pick successes.

If a protected authorization boundary or evidence-provenance guarantee fails, stop affected runs and retain the counterexample. The protocol validator confirms structure and immutability **only when an independently recorded protected digest is provided**. It does not authenticate hosted CI, worker logs, protected App signatures, or trial results.

## Next governed step

After validation and protected registration: compare controller options (GitHub Agentic Workflows, Machinist, and corrected #630) for capability and operating cost without presuming the custom queue is necessary; obtain independently inspectable, exact-head evidence; then run the randomized parallel-arm diagnostic pilot. Preregister a separately powered confirmatory study *after* pilot feasibility, with sample-size rationale and held-out tasks. Do not claim increased reliability or commercial value until that study supports it.
