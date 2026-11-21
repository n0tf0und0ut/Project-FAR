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


## R-C6 — exact decidability from the nonempty version space

The missing premise is not just model semantics: it is **target identifiability**. Let H be a separately justified class of possible targets W→Y. Let D be authoritative world-state/target-output samples, and let H_D contain exactly the targets in H agreeing with all D. Write C_O(f) for ker(O)⊆ker(f).

**Theorem:** If H_D is nonempty, one YES/NO verdict valid for every target still possible exists exactly when all possible targets agree about completeness:

\[
(\exists b\in\{\mathrm{YES},\mathrm{NO}\}\;\forall f\in H_D,\ 
[b=\mathrm{YES}\iff C_O(f)])
\iff
(\forall f,g\in H_D,\ C_O(f)\iff C_O(g)).
\]

If H_D contains one complete and one incomplete target, the evidence **cannot determine** which verdict is true. Calling either answer proved is an epistemic error, not a limitation of the theorem prover. Moreover, H_D must be **nonempty**: for an empty hypothesis class, universal YES and universal NO are both vacuously true. Establishing that the actual target belongs to H_D is a *separate real-system correspondence obligation*, never implied by consistency of internally generated predictions.

The results are formalized as FARVersionSpace.binary_decidable_iff_candidates_agree, FARVersionSpace.conflicting_candidates_prevent_verdict and FARVersionSpace.empty_hypothesis_has_both_fake_verdicts.

## R-C7 — sharp finite-oracle coverage threshold

Assume the full domain W is finite and known, O:W→B is known, and an authoritative membership oracle supplies f(w) on demand. There is **no** restriction on binary target functions f:W→{0,1}.

Let U = {w∈W | there is v≠w with O(v)=O(w)}: all points in non-singleton observation fibers.

**Worst-case positive certification requires f(w) for every w in U**. If one x∈U is unqueried, choose a distinct y in its fiber. The all-zero f_good and the single-point-flip f_bad agree on every queried state but have opposite completeness verdicts. The claim cannot be decided positively from the evidence. Conversely, if every member of U was queried, and all equal-O sampled pairs had equal oracle outputs, completeness follows for all W. Singleton fibers cannot contain a collision witness and need no target query.

Consequently, the exact worst-case positive target-value query count is |U|, while an observed negative counterexample needs just two queried states sharing O with distinct f outcomes. This counts oracle-value queries on a declared known domain, not discovery of W, trust in the oracle, learning O, or computational search effort.

The lower and upper claims are mechanized by FARVersionSpace.missing_nonsingleton_fiber_point_blocks_yes and FARVersionSpace.complete_from_nontrivial_fiber_coverage.

## Evidence, reproducibility and nonclaims

FARVersionSpace.lean is a Research-only extension of the existing source-independent Lean 4 reconstruction. The exact-head GitHub workflow compiles FARContractCompleteness as a module, then compiles the new proof and prints transitive axioms. The research finite-test file now has 13 tests, including exhaustive binary candidate-version spaces for up to four states (4,681 observation/sample/target triples), 1,360 observation/sample sets through five states for the lower bound, bounded upper checks, contradictory samples, and a wrong-hypothesis-class false-positive control. These do not constitute tests on an externally specified live real system.

**Verdict:** The universal positive claim that an incomplete observer or self-authored model can establish completeness of *arbitrary unknown real-world behavior* from its own data is REFUTED. The necessary and sufficient *information condition* for a definite verdict is proved for the specified H_D. A real-system-positive verdict requires separately justified target membership, domain coverage and source/execution correspondence; the mathematical proof does not conjure those facts.

Relevant prior art: Dana Angluin, Learning Regular Sets from Queries and Counterexamples, Information and Computation (1987), DOI 10.1016/0890-5401(87)90052-6. That work explicitly assumes external membership and equivalence query access. R-C6/R-C7 are elementary function/identifiability results, not originality claims.
