# FAR — Can a contract certify its own semantic completeness?

**Status: Research.** Governing current Core: Project FAR 1.1 (no change). This investigation narrows the user-raised assumption A2 and the completeness/contract-justification limits UQ-T32, LIM-036, and LIM-038; it does **not** reopen a settled core theorem, change frozen evidence, or establish an external real-world contract.

## Question and raw objects

Can FAR establish that a model's observation contract captures every distinction relevant to an intended real-world target, without first assuming that its selected observations exhaust the target-relevant behavior?

Separate four maps that must not be conflated:

- W: full intended possible-world/state domain, if independently established.
- e: W → X: actual-world-to-modeled-case encoding; it may omit latent state.
- ρ: X → R: the internally verified representation.
- β: X → Y: the modeled outcome specified by a contract.
- F: W → Y: actual target behavior. Whether F equals β ∘ e is a separate semantic claim.

Let O:W→B be the *actual* observable contract on W. Define Complete(O,F) iff for every w,w' with O(w)=O(w'), F(w)=F(w'). This is equivalently the existence of a decoder on the reachable image of O factoring F. The word 'complete' here means **complete relative to the named F on the named W**, not complete relative to all real phenomena.

## Result R-C1 — sharp universal completeness boundary (deductive)

For any typed sets W and B and map O:W→B:

**(∀Y, ∀F:W→Y, Complete(O,F)) iff O is injective.**

Proof: If O is injective, O(w)=O(w') entails w=w', so every F agrees there. Conversely choose Y=W and F=identity; if every F is complete, this particular F is complete, hence O(w)=O(w') entails w=w'. This holds even for empty or singleton W.

Thus an observation contract can be universally sufficient by retaining every distinction in its declared world domain. It need not be **least informative** for any particular target and need not be computable, succinct, or operationally feasible. Crucially, this does not show that W correctly represents all physically possible situations.

## Result R-C2 — self-evidence ambiguity (deductive)

If distinct w0,w1 satisfy O(w0)=O(w1), define F_good(w)=w0 for every w and F_bad(w)=w. Then:

- O is complete for F_good, because F_good is constant.
- O is **not** complete for F_bad, because w0 and w1 are distinct.
- The two targets even agree at the observed case w0, and the same O is supplied to a would-be certifier.

A verifier that receives only the observer, its self-asserted model, and data not separating these alternatives cannot decide completeness for the *unknown specific* F without additional constraints. This is a conditional indistinguishability impossibility, **not** a claim that no positive completion certificate can ever exist: an injective O works for all F, and an externally specified F can be checked.

Finite-sample counterpart: on W={0,1}, O constant, F_good constant zero and F_bad=identity agree at sampled world 0 but differ at world 1. Any test confined to world 0 returns identical data for the two targets; a universal assertion is therefore unwarranted.

## Result R-C3 — real-world modeling collapse (deductive)

Suppose the actual observation is O(w)=ρ(e(w)). If e(w0)=e(w1) while F(w0) ≠ F(w1), then O(w0)=O(w1) for **every** ρ. Hence no downstream representation can be complete for F, even if ρ is the identity on X.

Smallest explicit countermodel: W=Bool×Bool, X=Bool, e(a,b)=a, ρ=id, F(a,b)=b. Worlds (false,false) and (false,true) are modeled identically yet have different targets. Internal identity, model-level completeness, complete Lean proofs of ρ, and large numbers of self-authored tests do not restore the omitted bit.

This is a direct counterexample to any inference 'the model proves its own real-world completeness', not to the contract-relative FAR quotient theorem.

## Result R-C4 — precise sufficient conditions for positive certification

**Finite known-world route:** Given a complete enumeration of every element of W and exact evaluation of O and F, checking all pairs with O(w)=O(w') decides Complete(O,F). The mathematical theorem requires that the enumeration cover **all W**, not merely a tested sample. For unknown/infinite W or unavailable F, exhaustive pairwise checking is not thereby effective.

**Independent semantics route:** Suppose a reference trace E:W→Z is established with Complete(O,E), and separately establish a target relation F(w)=h(E(w)) for all w for a declared h:Z→Y. Then F factors through O and completeness follows by equality. Equivalently, if the modeled target β is known complete under ρ and a real-to-model correspondence F=β∘e is established, then F is complete under ρ∘e.

These are real positive mathematical theorems. They expose a specific external obligation: a correct bridge from actual target semantics to the chosen model. The bridge must be independently warranted by domain proof, exhaustive specification, verified semantics, trusted instrumentation, or explicit restricted-world assumptions. Calling a self-authored equality assumption a 'verified' equality would be circular.

## Result R-C5 — marginal probabilities can lose joint information

Two distributions of two binary outputs can both have marginal probabilities P(A=1)=P(B=1)=1/2 while one concentrates on 00 and 11 and the other assigns 1/4 to every pair. A contract consisting only of marginals equates the distributions, but a joint-event target distinguishes them. An outcome type called 'probability distribution' is not enough: the chosen **events and joint/conditional observation interface** determine adequacy.

## Formal and executable evidence

- FARContractCompleteness.lean is an independent Lean 4/Std module (no import of FAR proofs). It encodes R-C1 through R-C4, empty/singleton-compatible quantification, two-bit modeling loss, an incomplete finite sample, an explicit covered-world positive certificate, and an exact factorization equivalence.
- test_contract_completeness.py runs eight independently structured finite/adversarial regressions. The core fiber-check test covers 4,331 observation/target pairs for |W|=0..4 with a binary target. The other tests independently search injection, reference factorizations, and omitted-world-state examples.
- The existing pinned Lean 4.19.0 hosted job is extended to compile the additional source, reject sorry warnings/errors, print transitive axioms, and run the eight finite controls. Only hosted execution can establish that these exact committed Lean bytes passed the kernel.
- The result was developed against protected main aa5cb8faf36b5e033bb96bf6e9f7f3f351387913 under current root AGENTS.md and the Research Execution Charter. Research branch: research/far-core-foundational-falsification-20261112, PR #665.

## Prior art and novelty boundary

These are elementary factorization/non-identifiability consequences related to classical structural identifiability, observability, causal identification and active automata learning. Do not claim novelty or global certification.

- https://pmc.ncbi.nlm.nih.gov/articles/PMC8923730/ — structural versus practical identifiability.
- https://pmc.ncbi.nlm.nih.gov/articles/PMC2652882/ — identifying assumptions in causal inference must supplement observational data.
- https://proceedings.mlr.press/v217/kruger23a.html — active automata-learning query lower bounds.

These sources contextualize the result; the proofs here stand or fall on the explicit mathematical constructions, not citations.

## Verdict and remaining obligations

**REFUTED:** A noninjective observation contract cannot reliably certify its own completeness for an unknown, unrestricted target based only on its internally supplied evidence. A complete internally validated modeled representation cannot restore omitted real-world information.

**CONDITIONALLY PROVED:** A contract *can* be complete for a specified F, and completeness can be established without simply assuming the final conclusion if one has a verified injective whole-world observer, an exhaustive true-world enumeration plus target oracle, or a separate proof of real-world target-to-model correspondence.

**OPEN:** Whether any concrete FAR-selected contract captures every relevant outcome for a specific externally selected real reasoning system. Neither mathematics alone nor an internally coherent model automatically supplies W, F, admissible tests, or the correspondence premise. The governing contract-selection/empirical assurance limitations remain.

This is not an impossibility of all mathematical real-world reasoning; it is a proof that real-world semantics cannot be conjured from an observation interface that leaves live alternatives indistinguishable.
