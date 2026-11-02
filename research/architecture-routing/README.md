# FAR architecture routing — bounded comparison

Status: Research / NOT EXECUTED. This work does not modify FAR Core, accepted methodology, or the current contract verifier.

## Question

For an explicit finite FAR comparison contract, does model-directed selection of the verification tool improve correct outcomes or efficiency over deterministic routing and a declarative workflow? The three arms must use the same current semantic verifier and frozen source records. The intervention is routing policy, not the verifier or the evidence.

## Preregistered scope

The initial corpus comprises the four existing far-ir/2.0 conformance cases and four pairs from the W4 formal-logic, argumentation, Bayesian/causal, and model-based domains. Exact source blobs and expected categorical outcomes will be frozen before execution. Three arms per twelve cases make 36 paired-by-case cells, counterbalanced across all six possible arm orders. An invalid response, abstention, missing output, or timeout counts as failure.

Primary outcome is exact match to frozen, independently evaluated categorical validity and report outcome. Secondary outcomes are elapsed time, token consumption, provider cost, and unapproved actions. Compare complete-case counts alongside intention-to-treat results; never drop failures to inflate success. Both model and execution environment identity must be frozen before a live test.

## Required execution gates

A model snapshot, tool interface, isolated runner, frozen task bundles, blinded independent oracle, concealed scoring cases, cost and token ceilings, randomized schedule, trusted execution logs, and permission to incur API cost remain unresolved. The labels in existing conformance documents are project-authored and publicly visible. Therefore the initial set is a *functional routing regression corpus*, not an unbiased external benchmark.

No numerical model-performance, causal, efficiency, general reliability, or architectural-superiority claim is established by this registration. The planned experiment is distinct from PR #603, which tests coding-agent instruction efficacy. Follow the Research Execution Charter, canonical FAR workflow, current far-ir/2.0 verification rule, and hostile-source boundary.
