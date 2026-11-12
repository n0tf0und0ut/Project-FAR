# UQ-T33 — Effective observational quotients

**Status:** Research. Internally derived and finitely tested. Not Accepted, not canonical, not an I3-independent replication, not a novelty finding, and not an amendment to Project FAR Core Theory.

**Question:** UQ-T33 asks under which computability assumptions an observational quotient can be constructed, approximated, or learned. The specific trigger is the gap between set-theoretic existence of the quotient and an effective procedure to find or certify it.

**Base authority:** protected main at 8c6dc6cf840a0d82fb4dcde114c1af471b3f74fe (2026-11-12), current Core Theory v1.1, UQ-T33 in the unresolved-questions register, and the Research Execution Charter. No frozen evidence or current authority is changed here.

**Source provenance:** This note preserves the substantive arguments and negative findings from the original UQ-T33 local research package, whose source report SHA-256 is bb7e6a95417eb06f77d7a24f256172a6077bbe7dd84defc77fb9de88807dd52f. The program and results are committed separately with their original bytes (respective SHA-256 713d3173637dbb49d4ed4616a6c83517f19216857cad186a45d33a7b668dc46a and b36cf49af425bd29a5434df6f9213f7860a007da3e0faab66d5d6793a6e545a1).

## Model

Let X be a finite nonempty set of n cases, T an arbitrary set of exact tests, V an outcome set, and obs:T×X→V a total observation function. For each F⊆T let x~F y mean that obs(t,x)=obs(t,y) for every t in F. Let Q_T=X/~T and k=|Q_T|, with 1≤k≤n. This is the same observational equivalence used by FAR-CORE-001/002 under a fixed exact contract. A computation additionally needs an effective test interface and decidable equality of produced outcomes.

### R1: sharp finite separating basis (deductive)

**Claim.** There exists F⊆T with at most k−1 distinct tests such that ~F=~T. The bound is sharp.

**Proof.** Begin with F empty and one equivalence class. Every ~F is coarser than ~T. If ~F differs from ~T, choose two cases equivalent under F but inequivalent under T; at least one t∈T separates them. Adding t strictly refines the current partition, increasing the class count by at least one. No intermediate partition can have more than k classes, because each remains coarser than ~T. Therefore at most k−1 additions achieve k classes, hence exactly ~T. If k=1 the empty family already suffices. ∎

**Sharpness.** With X={0,...,n−1}, use n−1 binary tests t_i whose output is 1 exactly on case i (i<n−1). Every test is necessary: omitting t_i merges case i with case n−1. Thus k=n and the minimum basis has n−1 tests. ∎

The proof establishes **existence**, not a uniform method to discover the separating tests. In particular, the construction assumes an oracle or other means of finding a currently missing distinction. Neither the existence of F nor a small k bounds the observations needed by a learner unaware of the full contract.

### R2: exact certification is undecidable over an effective infinite test family (deductive)

**Claim.** Even when X contains two cases and every single test is uniformly total and computable, no total algorithm decides exact sufficiency for every instance of a particular effectively given infinite family.

**Proof.** Fix X={0,1}, outcomes V={0,1}, T=natural numbers, and the constant representation rho(0)=rho(1)=0. For any Turing-machine code e, let H(e,t) be the total decidable predicate that checks whether e halts on input e within t simulation steps. Set obs_e(t,0)=0 and obs_e(t,1)=H(e,t). All individual observations terminate. By FAR-CORE-001, rho is sufficient exactly when the two cases never differ on a test, equivalently when e does not halt on input e. A total sufficiency decider would decide diagonal nonhalting and hence diagonal halting, contradicting the diagonal undecidability proof. ∎

**Classification under the stated effective-input promise.** When X is explicitly finite, tests are effectively enumerable, rho is computable **with decidable equality on its reached values (or its collision relation is explicitly given)**, and observations are uniformly total with decidable outcome equality, *insufficiency* is semidecidable: enumerate colliding case pairs and tests until a separating witness appears. Thus sufficiency is co-c.e.; the displayed construction makes this restricted problem co-c.e.-hard (and co-c.e.-complete within this promise class). This says nothing about the arithmetic complexity of recognizing which arbitrary program indices satisfy the totality promise.

**Finite-prefix counterexample.** For every finite horizon h, a program delaying its halt until beyond h yields the same observations as a divergent program on every test t≤h, but the two differ at a later test. No amount of unqualified finite black-box agreement proves full equivalence for this class. Structural certificates, a supplied complete test basis, or a proved bound on distinguishing witnesses are additional information, not consequences of finite X alone.

### R3: a decidable explicit-table fragment (constructive)

If X and T are both finite, explicitly enumerated, and every obs(t,x) is effectively computable with decidable equality, then each case's complete outcome vector is computable. Grouping identical vectors constructs Q_T and checking every rho collision against those vectors decides exact sufficiency.

For the empty test family, the quotient has one class over nonempty X; no calls to obs are required, provided X (and its size) is explicitly known. The original demonstration script has no independent X argument when there are zero rows, so its exhaustive harness represents empty T using a constant dummy row instead of invoking the finite-table helpers on an empty table. That is a **reference API limitation**, not a theorem exception.

The executable greedy algorithm finds a quotient-preserving subfamily of at most k−1 tests once the *full finite table is available*. The exhaustive subset search computes a minimum-cardinality subfamily, at potentially exponential cost. Neither algorithm certifies unknown, undeclared, or unenumerated tests.

## Internal executable evidence

The standard-library experiment exposes six tests:

1. Exhaustive binary test-family enumeration for n=1,2,3 with independently enumerated minimum-cardinality bases.
2. Exhaustive greedy-basis verification for all 65,536 binary test-family subsets on n=4.
3. 750 seeded multivalued finite tables across n=2,...,6.
4. Sharpness witnesses for n=2,...,9.
5. Twenty-five finite-prefix delayed-halting counterexamples (h=0,...,24) using a bounded two-counter-machine simulator.
6. Rejection of inconsistent table row lengths.

Observed after local rerun on the supplied source package: **6/6 tests pass**, including **65,812 binary families** (4+16+256+65,536). The results JSON gives explicit sharpness instances and a delayed counterexample (agreement through test 6, separation at test 8). These finite executions corroborate implementation behavior; R1 and R2 rely on the mathematical proofs above.

Reproduction from repository root:

    python -m unittest tests.test_uq_t33_effective_quotients
    python research/uq_t33_effective_quotients/experiment.py

The second command regenerates results.json. The script has no non-standard dependencies.

## Falsifiers, dependencies, and nonclaims

- **R1 failure:** a finite table for which every subfamily of size at most k−1 loses a distinction, or a valid logical counterexample to strict partition refinement.
- **R2 failure:** a uniform total decision procedure for the constructed observer class, or a failed reduction to diagonal halting. The simulator must be total for each finite horizon.
- **R3 failure:** a finite complete observation table for which exact vector grouping or checked collisions yields the wrong quotient.
- Neither test counts nor runtime output prove the infinite undecidability statement.
- Finite X does not imply that all tests are available, valid, unbiased, or semantically complete. Contract choice remains external and domain-specific (LIM-038).
- No external reasoning system, customer utility, scientific priority, independence class I3, or general-purpose agent improvement is established.
- UQ-T33 remains open in canonical governance until the required independent replication, evaluation, acceptance, and promotion stages occur. This research note does not override the register.

## Prior-art and authority

- [Project FAR Core Theory v1.1](https://github.com/n0tf0und0ut/Project-FAR/blob/8c6dc6cf840a0d82fb4dcde114c1af471b3f74fe/theory/theorems/Project-FAR-Theory-Closure-v1.1.md)
- [Unresolved Questions Register, UQ-T33](https://github.com/n0tf0und0ut/Project-FAR/blob/8c6dc6cf840a0d82fb4dcde114c1af471b3f74fe/docs/governance/unresolved-questions-register.md)
- [Research Execution Charter](https://github.com/n0tf0und0ut/Project-FAR/blob/8c6dc6cf840a0d82fb4dcde114c1af471b3f74fe/docs/governance/research-execution-charter.md)
- [Stanford Encyclopedia of Philosophy, Recursive Functions](https://plato.stanford.edu/entries/recursive-functions/) (halting and computability)
- [Separating families of convex sets](https://doi.org/10.1016/j.comgeo.2013.06.001) (related separating-family bounds, not an attribution of this exact theorem)
- [HKU TR-96-07](https://citeseerx.ist.psu.edu/document?doi=3e304c1c7aea9e351c59dc8c4cdbe9aa3f357e2f&repid=rep1&type=pdf) (related observational-equivalence concerns)

**Research disposition:** A finite exact quotient admits a short distinguishing-test basis, but that existence does not imply decidable detection of completeness over an unbounded test domain. With finite explicit tests, exact verification is decidable. These results sharpen the computational boundary of FAR's contract-relative factorization theorem without revising the theorem itself.
