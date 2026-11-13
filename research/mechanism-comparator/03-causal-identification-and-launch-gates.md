# FAR-SWE-V3-CAUSAL-IDENTIFICATION-AUDIT — current evidentiary boundary

**Research status; read-only analysis. Not a preregistration amendment, model call, manual authorization, or scientific efficacy claim.** The v3 registered design, task gate, protected main and frozen artifacts remain unchanged.

## Authority and original sources

Read complete current root AGENTS.md on protected main, source blob 0c21bb208e2f624742fde13715326882b178dcc7, and Research Execution Charter. Current protected main: f3c04e423df798960f64599ff638994aaaae981c.

- research/external-validation/swe-agent-v3/preregistration-v1.0.json: baseline, inert placebo and FAR capsule are the only three required arms; the primary contrast is FAR-minus-placebo, not FAR-minus-generic semantic checker.
- research/external-validation/swe-agent-v3/execution-gate-v1.0.json: all five global execution/model/pilot/benchmark/confirmation authorization flags are false; 0/16 pilot gates and 0/17 confirmatory gates true; no separately reviewed, identity-bound prospective launch record or manual authorization is present.
- research/external-validation/swe-agent-v3/treatment-capsule-contract-v1.0.json: capsule is uninstantiated; merely making a static checker available does not show an agent used it.
- research/mechanism-comparator/01-execution-and-results.md: an ordinary generic semantic checker tied FAR on all 18 previously exposed finite collision classifications, motivating a matched active comparator rather than a schema-only or inert baseline.

## Constructive impossibility of identifying a FAR-specific generic-checking effect with three arms

Write Y_b, Y_p, Y_f and Y_g for task resolution probabilities under baseline, placebo, FAR and matched generic semantic-checker arms. The registered three-arm program could estimate Y_f - Y_p after valid execution. It cannot identify Y_f - Y_g without a generic arm or independently justified structural assumptions linking Y_g to observed arms.

Explicit pair of hypothetical models: in both worlds Y_b=0.4, Y_p=0.4, Y_f=0.6. In World A, Y_g=0.4 and the FAR-minus-generic contrast is +0.2. In World B, Y_g=0.6 and the FAR-minus-generic contrast is 0. Both worlds agree on every variable observed by the three-arm design yet differ on the proposed distinctive FAR advantage. No statistical method can resolve this from the same data. **The numbers are purely mathematical countermodels, not FAR benchmark observations.**

Additionally, assignment to a FAR capsule and observing task success establishes an intention-to-treat effect if the trial is correctly run, but does not establish that the FAR semantic verifier was invoked, that evidence was interpreted, or that tool feedback produced a correction. Mechanism attribution requires authoritative tool-call receipts and a prospective controlled component ablation. A generic active-comparator arm alone identifies the relative capsule-level effect, not each internal causal mechanism.

## Executed read-only checks

Source: research/mechanism-comparator/audit_causal_readiness.py (actual v3 source parser). Tests: research/mechanism-comparator/test_audit_causal_readiness.py. Nine mutation/negative tests enforce actual false gates; 3-arm under-identification; opposed FAR-minus-generic worlds; false permission even after forged all-true gate flags; lack of outcomes after merely adding an arm to an in-memory design; malformed Boolean, duplicate arm, wrong program, and duplicate JSON key refusal.

A read-only Actions Research job reruns these with existing W6 and comparator checks and retains an exact source output named v3-readiness.json. Do not assert a hosted pass until the exact-head job confirms it.

**The audit has no API capable of calling a model or launching the pilot.** It never modifies the v3 contract. The fact that all 17 launch gates are currently false is an objective blocker, not a task the audit is authorized to bypass.

## Verdict

- Actual FAR-versus-generic general-purpose agent causal advantage: **UNIDENTIFIED / NO VALID EXECUTED STUDY**.
- Registered v3 FAR-versus-placebo effect: **NOT EXECUTED**.
- Actual FAR verifier versus generic finite collision checker: **18/18 tie** on an internally authored and exposed finite corpus, not a general agent outcome.
- No claim of independence, model/provider access, results, repair receipts, readiness or external task coverage may be inferred from these read-only checks.

A meaningful next experiment needs independently sourced and blinded tasks; an actual runnable model/tool agent; frozen budgets, environment and grader; a generic active comparator (and controlled FAR ablations for mechanism claims); complete execution receipts; and separately authorized pre-launch identity and safety gates. None can be replaced by synthetic execution data, a fabricated reviewer or a manual gate flip.
