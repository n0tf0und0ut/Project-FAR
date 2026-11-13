# FAR foundational completeness and general-agent reliability — hostile evidence determination

**Status: Research, secondary evidence audit. No canonical promotion, no new primary trial, no EFR-001 execution.**

**Authority:** current protected main at investigation start \`aea2f8494a4a5fb04281d433c28acb6ff8116a22\`; current root \`AGENTS.md\` blob \`0c21bb208e2f624742fde13715326882b178dcc7\`; Research Execution Charter; corrected Core Theory v1.1; registered limitations \`LIM-008\`, \`LIM-031/032\`, \`LIM-035–039\`, \`LIM-043\`; current SWE-agent v3 execution gate. Explicit prior accepted and frozen material remains unchanged.

## Question and decision map

Does a universal complete representation or universal semantic-completeness certificate exist? And does FAR *causally improve general-purpose agent reliability* versus an equally resourced control and active generic checker?

Keep universal representation sufficiency, minimality, external semantic faithfulness, identifiability, and empirical causal efficacy separate. A proved algebraic theorem is not evidence that its observation contract corresponds to a particular real system; a model-backed simulator success is not evidence that the FAR treatment caused a general increase in reliability.

### Foundational results — deductive, finite and exact scopes separated

| Formulation | Verdict | Strongest exact statement / countermodel |
| --- | --- | --- |
| Sufficiency on a fully specified case domain for **every** declared observation contract | **PROVED (trivially achievable)** | Identity representation on X preserves all distinctions. It need not be minimal. |
| One contract-free representation simultaneously **least informative sufficient** for every contract on a domain with ≥2 cases | **REFUTED** | Constant and injective behavior maps require incompatible observational quotient sizes. Source: accepted Core v1.1 \`FAR-CORE-004\`. |
| Universal completeness for **every** target on fixed W under a given observer O | **PROVED iff O injective** | If O collapses any pair, choose target F = identity to defeat universality. If injective, every F factors on the reachable image. |
| Certifying an unknown target's completeness from self-generated, finite observations of a noninjective O | **REFUTED (without identifying restrictions)** | A constant target and a single-point-flip target agree at all samples but have opposite verdicts. |
| A single YES/NO answer valid for all behavior targets surviving independently justified evidence | **PROVED iff all candidates agree** | Nonempty version space H_D required. Conflicting candidates entail UNDERDETERMINED; empty H_D is inconsistent, not YES. |
| Worst-case finite positive certificate for unknown unrestricted binary target with known world W | **PROVED exactly with oracle values on every point in non-singleton O fibers** | Unqueried point in any such fiber admits a behavior-flip counterexample. Observed collision counterexample needs just two oracle samples. |
| Universal externally semantic completeness for all unspecified real systems and all materially relevant distinctions | **NOT ESTABLISHED; unrestricted internal-only certification REFUTED** | No free theorem produces the real-world domain, target function or source-to-model correspondence; stated world scope and external evidence are necessary. |
| A real-engine finite exact preservation claim | **PROVED at scoped six-case SQLite test** | Separate Research PR #670 binds actual SQLite observations to a four-class quotient, with an observed extension collision. No universal promotion. |

Primary provenance for the quotient and no-go proofs: accepted [Core Theory v1.1](../../theory/theorems/Project-FAR-Theory-Closure-v1.1.md); independently rewritten and hosted Lean checked Research [PR #665](https://github.com/n0tf0und0ut/Project-FAR/pull/665), especially FARContractCompleteness.lean and FARVersionSpace.lean. Those are mathematical consequences with no I3 external investigator; do not call a Research PR Accepted.

**Important logical point:** a universal proof requires precise quantifiers. The identity-on-X positive theorem and no-universal-minimum negative theorem are **compatible**, not competing. The absence of an externally justified world and target cannot be repaired by copying every field in a self-authored model.

### Empirical evidence — what was actually executed

**Immutable primary source:** [research/workflow-efficacy/result/campaign-41556392256.json](../workflow-efficacy/result/campaign-41556392256.json), Git blob \`90b3a56bb43d772a9e891766a578a93e73928aa8\`. Exact original run \`41556392256\`, source merge \`a750c5523183f64a20ff644846c4fcd91c887824\`, model \`ollama/qwen2.5-coder:1.5b\`, digest \`d7372fd828518a4d38b1eb196c673c31a85f2ed302b3d1e406c4c2d1b64a0668\`.

Frozen cohort: 30 investigator-authored one-shot synthetic Python repairs, ten related families, two conditions, one generation per arm and task, 60 provider-backed executions; 2 public and 4 hidden comparisons per task. The original 31 Actions artifacts, 30 pair outcomes, instruction revisions and model identities are already recorded and have not been altered here.

| Outcome | Control | FAR-bundled instruction treatment |
| --- | ---: | ---: |
| Repairs passing all six comparisons | 11/30 | 10/30 |
| Success rate | 36.67% | 33.33% |
| Mean generation seconds | 42.050 | 68.813 |
| Mean input tokens | 2525.97 | 3946.97 |
| Mean output tokens | 59.23 | 57.30 |

**Paired success difference: -1/30 (-3.33 percentage points).** Nine pairs pass both, 18 fail both, one favors treatment, two favor control. The original two-sided exact conditional McNemar/sign-test probability is 1.0; the fixed-corpus task-bootstrap diagnostic interval is [-13.33, +6.67] percentage points. New ten-family cluster resampling is explicitly **post hoc sensitivity**, not a valid population confidence interval. Treatment on this measured corpus uses ~63.6% more generation time and ~56.3% more input tokens while solving one fewer task. The protocol bundled longer instructions and did not equalize compute, so an advantage or disadvantage of any uniquely FAR-specific reasoning mechanism is **not identified**.

**Separate noncausal result:** [bounded tool-agent study v0.3](../tool-agent-reliability/RESULTS-V0.3.md) used Qwen2.5-Coder 7B to complete 72/72 authored virtual-file/calculator runs, but **had no FAR-vs-control or active comparator**, at deterministic temperature and repeated seeds. It supports no causal FAR or general reliability claim. It cannot be pooled with 30 toy repairs.

**Scientific verdicts (do not conflate):**

- Original measured bundled-instruction advantage on those 30 tasks: **NO IMPROVEMENT OBSERVED**; the observed success difference is negative.
- Statistically defensible causal improvement attributable **specifically to FAR**: **NOT ESTABLISHED** (no generic active comparator, no ablation, bundled context/timing mismatch).
- General-purpose autonomous-agent reliability advantage across systems/tasks/models: **INCONCLUSIVE / NOT TESTED** under a valid comparative study.
- General FAR effect of exactly zero or inferiority: **NOT PROVED** from a single related-family cohort.

### Raw evidence and replay

\`verify_evidence.py\` checks the Git blob of the original source JSON, exact thirty task identities, paired successes and all timing/token measures, frozen signs/bootstrap, 31 original artifact IDs and digests, provenance, no-double-counting and explicit no-overclaim fields. \`test_verify_evidence.py\` uses adversarial deletions, regrades, duplicates, forged digests, malformed JSON, and invalid source hashes. New GitHub Actions job \`replay-original-60\` also:

1. Fetches each of the original 31 immutable GitHub Actions ZIPs with a read-only ephemeral GitHub token, requiring each SHA-256 to agree with the recorded evidence manifest. The original run's Actions artifact retention currently ends **2026-12-03 UTC**; this raw verification is expected to fail closed after expiry unless a separately preserved original raw bundle is supplied.
2. Extracts original pair files with ZIP traversal, decompression-size, duplicate-member and missing-slot checks.
3. Separately checks out *exact* original execution commit \`a750c5523183f64a20ff644846c4fcd91c887824\`, invokes its original frozen fail-closed grader/replay against the **60 actual retained provider responses and grader traces**, and compares the reconstructed report byte-semantically with the original registered report.
4. Retains replay logs and post-hoc sensitivity outputs, without mutating any original artifact or accepted theory.

A pass is authenticated **internal reproduction of externally executed model calls**; not an external blinded study, not evidence of source/target independence, and not a new experiment. Missing raw evidence must fail the check and cannot be papered over with published aggregates.

## Exact obstacles to the requested four-arm causal conclusion

The repository's current prospective [SWE-agent v3 Research experiment](../external-validation/swe-agent-v3/README.md) registers baseline, structure-matched placebo, and FAR, but remains **design-only, execution prohibited**. It requires a source-and-identity-sealed externally supplied task manifest containing at least 24 tasks across five provider-stable non-FAR repositories, no repository dominating above 20%, five mandatory strata, independently audited ground truth and GitHub fork lineage, frozen model endpoint and budget, treatment/placebo roots, secure execution, explicit safety thresholds, a frozen sacrificial pilot, and an authorized launch record. These are substantive evidence/authorization conditions, not merely missing YAML.

An additional FAR-specific ablation would require a **prospective protocol amendment**, not a post-outcome fabricated fourth arm. The frozen EFR-001 independent human/field program similarly requires a truly external custodian, inputs, reviewers and sites; it remains not executed. The present study does not satisfy either program, and creating a competing ad hoc pilot with FAR-authored tasks would evade, not close, the main external validity problem.

## Completion statement

**Universal completeness:** the unrestricted claim is answered at its exact mathematical quantifiers: trivial universal sufficiency exists on a declared domain; universal contract-free least-informative sufficiency is refuted; a noninjective observer with unconstrained unknown target cannot self-certify; restricted target-specific completeness can be established with independently grounded sufficient evidence.

**FAR improves general-purpose agent reliability:** **NOT ESTABLISHED.** The only completed direct controlled repair sample gives FAR-bundled instructions 10/30 vs control 11/30 at higher generation burden, and does not identify FAR-specific mechanisms. Claiming positive general-purpose advantage now would contradict the available evidence.

No research-status promotion, production-readiness label, external independence, or protected-main merge is authorized by these results.
