# UQ-T33 continuation — a computable finite-state fragment

**Status:** Research. This is an additional, internally reasoned computational result. It does not alter FAR Core, its proof register, UQ-T33's canonical open status, or any frozen result.

## Question and precise assumption

What known structure makes a quotient computable when the full test set is infinite?

Fix a **fully specified finite deterministic Moore machine**: nonempty state set X of size n, finite action alphabet A, total deterministic transition function δ:X×A→X, and total output o:X→O with decidable equality. Declare every finite word w∈A* as a test and define obs(w,x)=o(δ*(x,w)), including the empty word.

This is a restricted exact contract. All transition and output data must be available; no unspecified environment or hidden state is admitted.

## R4: effective quotient and sharp distinguishing depth

**Claim:** The exact infinite-word observational quotient is computable by finite partition refinement. Every observationally distinguishable pair has a distinguishing word of length at most max(n−2,0). For n≥2, this bound is sharp.

**Proof:** Define E_0 on states by equality of immediate outputs. Define E_(d+1) by x E_(d+1) y iff o(x)=o(y) and, for every a∈A, δ(x,a) E_d δ(y,a). Induction on d shows that E_d equates exactly those states that agree under every action word of length at most d: the empty word tests immediate output, while a nonempty word begins with an action a and leaves a suffix of length at most d−1.

Consequently E_0⊇E_1⊇..., so the induced partitions only refine. If the partition does not change at a round, the defining recurrence produces the same partition at all later rounds; the fixed point therefore equals agreement under every finite word.

If E_0 has just one class, all state outputs coincide. No word can distinguish any states because every reached state also has that same output; E_0 is already a fixed point. Otherwise E_0 has at least two classes, and every strict refinement increases the class count by at least one. Since there are at most n classes, at most n−2 strict refinements can occur. Thus E_max(n−2,0) is the full observational equivalence relation. Grouping each state by its current output and the current classes of its action successors until a fixed point computes the exact quotient. ∎

**Sharpness:** For each n≥2, take states 0,...,n−1, a single action advancing x to min(x+1,n−1), and output 1 only at state n−1. States 0 and 1 agree on all words of length less than n−2, while the word with exactly n−2 actions distinguishes them. Therefore the worst-case depth bound is achieved. ∎

The bound concerns word length, not total evaluation count or shortest representation implementation. This is standard finite-state partition refinement; its use here establishes a well-specified positive fragment of UQ-T33 and does not imply mathematical novelty.

## Executable tests

The standard-library implementation is in finite_state.py. Test cases independently compare its fixed-point partition with direct evaluation of all words through the theorem's depth bound, exhaustively for:
- all binary-output one-action machines with 1–4 states;
- all binary-output two-action machines with 1–3 states.

Further tests cover the sharp-length chain, constant-output cases, and malformed transition tables. The complete inherited and continuation suite has 11 tests and passed locally. Run from repository root:

    python -m unittest tests.test_uq_t33_effective_quotients

The implementation assumes outputs have hashable canonical labels (Python dictionary keys), which is stronger than the mathematical requirement of decidable equality; that implementation restriction must not be misread as a theorem premise. Exhaustive tests cover only the displayed finite machines. The mathematical proof uses induction and the monotonic finite-partition bound.

## R5: finite-query black-box equivalence with a certified state bound

Suppose the deterministic Moore assumptions above hold, the action alphabet is known, each of two initial states can be reset exactly, their outputs can be queried after any finite action word, and **external evidence certifies an upper bound N** on the number of states reachable in the combined machine.

Enumerating and comparing the two outputs for every word of length at most max(N−2,0) decides whether the initial states are observationally equivalent under *all* words. By R4, the actual system has n≤N states and every possible difference is witnessed within length max(n−2,0)≤max(N−2,0). This is a complete positive result under the stated promise. The worst-case number of words queried per starting state is at most the sum of |A|^j over j=0,...,max(N−2,0), which can be exponential in N.

The executable reference function black_box_equivalent accepts the external upper bound as an explicit input and uses only observation queries; it does **not** independently establish that the bound is correct. Its oracle contract also assumes the same fully deterministic semantics and reliable reset for every query.

## R6: no uniform exact black-box decider without a state bound

**Claim:** Even when the unknown target is promised to be some finite total deterministic Moore machine with one action and exact binary outputs, no deterministic algorithm can always decide equivalence of two resettable initial states using finitely many black-box queries if no state bound or complete structural certificate is supplied.

**Proof:** Suppose a total algorithm exists. Give it a two-state all-zero machine with self-loops and both initial states outputting zero. It must terminate with the correct answer "equivalent." Its execution made finitely many queries, so let h be the maximum length of the queried words (or zero if there were none). Now replace the hidden machine with the n=h+3-state chain from R4, comparing its first two states. On every queried word (length≤h) both outputs remain zero, so the algorithm receives an identical adaptive transcript and returns "equivalent." But word a^(h+1) distinguishes the two states. Contradiction. ∎

This is a **black-box information limitation** even for finite-state targets; it does not rely on general Turing-machine halting undecidability. It disappears when a justified state bound and exhaustive resettable tests are supplied. It does not assert that no approximate, probabilistic, identification-in-the-limit, or actively learned procedure can be useful.

## Additional verification

Two further tests compare the bound-based black-box oracle to the complete fixed-point quotient across all small two-action machines already enumerated, and exercise 12 deliberately underquoted state bounds against delayed chain witnesses. The full suite now passes **13/13 local regression tests**.

## Falsification and limitations

A counterexample would be two states of a valid finite complete deterministic Moore machine agreeing on all words of length at most max(n−2,0) but differing on a longer word; or a flaw in the recurrence/fixed-point argument. Tests actively compare the algorithm to independently evaluated word outcomes.

This result cannot certify that a real reasoning environment has a known finite complete state set or deterministic transition semantics. Partial, probabilistic, nondeterministic, hidden-state, continuous, oracle-dependent, changing-ontology, or unrestricted computational processes require different contracts and arguments. The infinite-family undecidability result in discovery.md remains valid outside this restricted model.

**Next research question:** What externally checkable evidence can justify the finite-state completeness assumption, or establish a completeness horizon without assuming complete transition knowledge? The fixed-point proof cannot supply that premise itself.
