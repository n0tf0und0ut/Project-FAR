# Project FAR — source-derived statement-only packet candidate

**Status: Research, UNSEALED, not an EFR-R1 input.**  
**Generated from checked protected main:** `a9eb83eee705ba3e242b3f329712f6352761c6c1`.  
**Original v1.0 SHA-256 (governed archive):** `b7cbd28d54686da33773a66edf9af9480044ffaabfeb83cfa4bfc1a12fe862a5`.  
**v1.1 correction source:** `theory/theorems/Project-FAR-Theory-Closure-v1.1.md` §§1–2.

**Custodian warning:** This draft was extracted by a Project FAR assistant with prior access to W1/W2 material. It is **not** independently validated, independently sealed, or approved for transmission to clean-room reviewers. An eligible external custodian must verify each byte, definition, correction and omission directly against the pinned authoritative originals, ensure no proof or prohibited material is included, screen reviewer exposure, and independently seal the actual permitted packet. Follow EFR-R1's frozen protocol and any separately approved correspondence test. Do not send a repository URL or this source file as first contact.

The sections below preserve the governing formal-vocabulary and premise text. The theorem statements are extracted without their proofs. FAR-CORE-004 and FAR-CORE-010 use their v1.1 corrections; the superseded v1.0 wording is not an alternative hypothesis for review.

---

## 2. Formal vocabulary

The following are **formal roles**, not claims about metaphysical primitives.

### 2.1 Local comparison contract

A local exact comparison contract is a tuple

\[
C=(X,T,V,\operatorname{obs}).
\]

- \(X\) is a set of **cases**. A case may be a state, history, proof-search frontier, model,
  probability structure, argumentation framework with active context, execution, or any other
  fully specified situation relevant to the investigation.
- \(T\) is a set of admissible **tests or contexts**. A test may be a query, continuation,
  intervention, action sequence, proof obligation, decision problem, or observation protocol.
- \(V\) is a typed **outcome space**.
- \(\operatorname{obs}:T\times X\to V\) gives the outcome of applying a test to a case.

If the native semantics is partial, nondeterministic, or probabilistic, it is not forced into a
Boolean. Instead:

- partiality is totalized with explicit typed outcomes such as `undefined`, `not-applicable`,
  or `unknown`;
- nondeterministic outcomes may live in \(\mathcal P(Y)\);
- probabilistic outcomes may live in a space of probability measures;
- multi-extension argumentation outcomes may be sets or families of extensions;
- graded outcomes may live in an ordered or metric space.

The key rule is that outcome distinctions are preserved whenever a declared test can observe
them.

### 2.2 Behavior map

The contract's complete exact behavior map is

\[
\beta_C:X\longrightarrow V^T,
\qquad
\beta_C(x)(t)=\operatorname{obs}(t,x).
\]

This packages every declared test outcome for a case. It does not assert that the native
system internally stores such a function.

### 2.3 Representation and decoder

A representation is a map

\[
\rho:X\to R.
\]

It is **exactly sufficient for \(C\)** when a decoder

\[
d:\rho[X]\to V^T
\]

exists such that

\[
\beta_C=d\circ\rho.
\]

Only the image \(\rho[X]\) matters. No arbitrary behavior outside the represented image is
required.

### 2.4 Observational equivalence and quotient

Define

\[
x\sim_C y
\quad\Longleftrightarrow\quad
\forall t\in T,\ \operatorname{obs}(t,x)=\operatorname{obs}(t,y).
\]

Equivalently, \(\sim_C=\ker(\beta_C)\). The contract-relative observational quotient is

\[
Q_C=X/{\sim_C},
\]

with quotient map \(q_C:X\to Q_C\), \(q_C(x)=[x]_C\).

### 2.5 Dynamic and compositional contracts

When future behavior matters, \(T\) must contain the allowed continuations, actions,
interventions, or contexts. If \(A\) is a family of unary actions on \(X\), require semantic
test closure: for every \(t\in T\) and \(a\in A\), there is a test denoted \(t\circ a\in T\)
such that

\[
\operatorname{obs}(t,a(x))=\operatorname{obs}(t\circ a,x)
\quad\text{for all }x\in X.
\]

Then \(\sim_C\) is action-compatible and the actions descend to the quotient. Multi-argument
operations use the corresponding one-hole context closure.

This is how the same formal core covers traces, state transitions, proof continuations,
interventions, and context-dependent argument defeat without assuming that they share one
native state type.

### 2.6 Cross-system comparison contract

For a family \(\{S_i\}_{i\in I}\), a cross-system contract must additionally fix:

- the target class \(I\);
- a comparison language/signature \(L\);
- an interpretation/profile \(J_i\) for each target;
- an interface frame \(\Gamma\) containing only constitutive typing and declared definitions;
- admissible re-representations or morphisms \(G\);
- any cost or approximation order used for claims stronger than exact information minimality.

Without these data, “same structure,” “common theory,” “lossless,” and “minimal” are not
well-formed predicates.

---

## 3. Formal premises and admission principles

### 3.1 Formal premises (“axioms” of the model)

These are not empirical claims about cognition. They state the mathematical setting in which
Theorems 1–14 are proved.

- **A1 — Set presentation:** cases, tests, representations, and outcomes are sets at the level
  of the core theory.
- **A2 — Explicit semantics:** the observation relation is represented as a total function
  after partiality, nondeterminism, and probability are moved into typed outcome values.
- **A3 — Fixed-contract evaluation:** adequacy and minimality are evaluated only after the
  tests and outcome distinctions are fixed.
- **A4 — Extensional exactness:** exact adequacy means equality of every declared test outcome;
  approximate adequacy requires an additional metric/order/loss contract and is outside the
  exact theorems unless explicitly supplied.
- **A5 — Declared invariance:** representation independence is evaluated only against an
  explicitly named transformation or morphism class.

### 3.2 Admission principles

These principles govern valid uses of the theory. They are explicit methodological premises,
not alleged laws of all reasoning.

#### P1 — Scope closure

Every universal quantifier names its domain. “All reasoning systems” is invalid unless the
membership rule for that class is explicit and every proof obligation ranges over it.

#### P2 — Parameter completeness

Every parameter capable of changing a declared consequence belongs in the case, test, or
calculus specification. An omitted active context, semantics choice, query mode, decision
loss, threshold, execution choice, or history is a hidden variable, not a property of the
representation.

#### P3 — Outcome separation

Distinct declared outcomes remain distinct. In particular, determinate absence is not
epistemic Unknown, inapplicability is not falsity, and a set of permissible extensions is not
one arbitrarily selected extension.

#### P4 — Sufficiency by factorization

No representation is called lossless or sufficient merely because examples can be encoded.
It must satisfy the factorization criterion for the declared behavior.

#### P5 — Equivalence before spelling

Token names and surface syntax are not semantic identities. Identity is evaluated under the
contract's admitted isomorphisms or equivalences.

#### P6 — No universality by finite induction

A finite panel establishes only a result over that panel unless a separate theorem covers the
remainder of the named domain.

#### P7 — No minimality without an order

Information minimality is supplied by the quotient theorem below. Any stronger claim about
size, runtime, cognitive simplicity, explanatory power, or implementation cost requires a
declared preorder or cost function. Different cost orders can have different optima.

#### P8 — Provenance does not transfer truth

Repository acceptance, implementation, repeated model agreement, or successful validation
does not promote a theorem beyond the exact premises that were proved.

---

---

## Exact-scope statements to reconstruct

### FAR-CORE-001: Exact factorization criterion

For a fixed contract \(C\) and representation \(\rho:X\to R\), the following are equivalent:

1. \(\rho\) is exactly sufficient for \(C\);
2. \(\ker(\rho)\subseteq\ker(\beta_C)\);
3. whenever \(\rho(x)=\rho(y)\), every declared test gives the same outcome on \(x\) and
   \(y\).

### FAR-CORE-002: Canonical minimal observational quotient

For every exact contract \(C\):

1. \(q_C:X\to Q_C\) is sufficient;
2. for every sufficient \(\rho:X\to R\), there is a unique map
   \(h:\rho[X]\to Q_C\) such that
   \[
   q_C=h\circ\rho;
   \]
3. a sufficient representation is least-informative exactly when its kernel equals
   \(\sim_C\); every such representation is isomorphic to \(Q_C\);
4. in the finite case, every sufficient representation has at least \(|Q_C|\) represented
   values, and \(Q_C\) attains that bound.

### FAR-CORE-003: Dynamic descent under context closure

Let \(A\) be allowed actions on \(X\), and let \(T\) be closed under precomposition with
those actions. Then \(x\sim_C y\) implies \(a(x)\sim_C a(y)\) for every \(a\in A\).
Consequently each action induces a well-defined action

\[
\bar a:Q_C\to Q_C,
\qquad
\bar a([x]_C)=[a(x)]_C.
\]

### FAR-CORE-004: No contract-free nontrivial minimum (v1.1 corrected)

> **On every nontrivial domain, no single representation is simultaneously a least-informative sufficient representation for every observation contract.**

The identity representation is universally sufficient for every contract on the same domain. The impossibility concerns simultaneous least-informativeness, not sufficiency alone.

### FAR-CORE-005: Invariance antitonicity

Let \(G_1\subseteq G_2\) be two classes of admitted re-representations. If
\(\operatorname{Inv}(G)\) is the collection of properties invariant under every transformation
in \(G\), then

\[
\operatorname{Inv}(G_2)\subseteq\operatorname{Inv}(G_1).
\]

### FAR-CORE-006: Transport triviality

Let \(S\) be any structure on carrier \(X\), and let \(e:X\to H\) be an injection into a host
with sufficient capacity. Every operation and relation of \(S\) can be transported to the
image \(e[X]\) so that \(e\) is an isomorphism between \(S\) and the transported image.

### FAR-CORE-007: Primitive-vocabulary noninvariance

Under faithful encoding with explicit tags and a decoder, the number and names of primitive
sorts and relations are not invariant.

### FAR-CORE-008: Operator-count noninvariance

Any finite family of operators \(f_1,\ldots,f_n\) can be represented by one tagged operator

\[
U(i,x)=f_i(x)
\]

with arguments encoded into a common tagged domain. Conversely, \(U\) can be split into the
family by fixing the tag. Therefore the number of primitive operators is not invariant under
faithful tagged re-presentation.

### FAR-CORE-009: Finite-panel boundary

Let \(D_0\) be a finite proper subset of an open target class \(D\). Observing or proving
\(P(S)\) for every \(S\in D_0\) does not entail \(\forall S\in D\,P(S)\) unless an additional
deductive premise covers \(D\setminus D_0\).

### FAR-CORE-010: Common theory is profile-relative (v1.1 corrected)

Fix a logical signature \(L\), target index class \(I\), interpretation profiles \(J\), and resulting interpreted models \(M_i\). The exact common theory is

\[\mathcal T_{L,J,I}=\bigcap_{i\in I}\operatorname{Th}_L(M_i).\]

With constitutive interface frame \(\Gamma\), the substantive residue is

\[\mathcal R_{L,J,I,\Gamma}=\mathcal T_{L,J,I}\setminus\operatorname{Cn}_L(\Gamma).\]

With \(L,J,I,M_i\) fixed, changing \(\Gamma\) alone cannot alter the exact common theory, although it may alter the residue. Changing the language, profiles, or target class can change the exact common theory.

### FAR-CORE-011: Omitted-parameter failure

Suppose full cases have the form \((x,c)\), where \(c\) is a context or calculus parameter,
and a representation omits it:

\[
\rho(x,c)=\rho_0(x).
\]

If some declared test satisfies

\[
\operatorname{obs}(t,(x,c_1))\ne
\operatorname{obs}(t,(x,c_2)),
\]

then \(\rho\) is not sufficient.

### FAR-CORE-012: Determinate absence/Unknown separation

If `absent` and `unknown` are distinct outcomes in \(V\), and two cases produce those outcomes
for some declared test, every sufficient representation must distinguish the cases.

### FAR-CORE-013: Ω elimination

Under canonical FARA, let \(z\) be the complete investigation/calculus input, let
\(\operatorname{Class}_\kappa(z)\) be the classifications produced by reasoning calculus
\(\kappa\), and let

\[
\Omega(z)=\operatorname{Rep}(\operatorname{Class}_\kappa(z)).
\]

For any resolution rule \(r\), the consequence is

\[
r(\Omega(z))
=
(r\circ\operatorname{Rep}\circ\operatorname{Class}_\kappa)(z).
\]

Ω is therefore eliminable as an independent semantic primitive.

### FAR-CORE-014: Search-state sufficiency is a factorization instance

The SSS results in PR #453 are instances of Theorems 1–3.

- With individual sequents, the rule-induced projected successor relation discards which
  premises belong to the same rule instance/resource partition. Under the stated four uniform
  monotone successor-set decoders, cases with different derivability behavior become
  indistinguishable. Factorization fails.
- A resource-labelled hyperedge retains the joint premise family. The standard AND/OR decoder
  factors derivability through it.
- A frontier multiset internalizes the joint obligation into the state. A binary expansion
  relation on frontiers then suffices for any finitary rule system.

This does not make SSS a universal operator architecture. It shows that adequacy belongs to the
pair **(state type, transition representation)** relative to a decoder/test contract.

---

## Excluded material and pending independent controls

This packet intentionally omits proofs, countermodels, W1 verdicts, W2 Lean declarations/types, formalization ledgers, reviews, and prior correspondence findings. It is an **unsealed extraction candidate**, not a certification, not a replacement for the registered EFR-R1 packet, and not a new protocol version.

**Pre-release obligations:** The independent custodian must validate completeness against the exact governing text, including the original source's type/scope conventions and every v1.1 supersession. A missing assumption, source conflict, or non-verbatim correction blocks release until adjudicated. The custodian separately certifies that no prohibited proof/review material entered the delivered bytes. The two external teams must not view each other's outputs or the original Lean sources until their independent reconstructions are sealed.
