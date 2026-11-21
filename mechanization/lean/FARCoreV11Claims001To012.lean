import FARCoreV11Substrate

/-!
# Project FAR core theory v1.1: FAR-CORE-004--012

Each theorem retains the governing contract and scope.  In particular, the first theorem
denies one simultaneous contract-free minimum, not the existence of universally sufficient
representations such as the identity map.
-/

namespace FARCoreV11

universe u v w

/-! ## FAR-CORE-004 -/

/-- No representation has both the constant and identity kernels on a nontrivial domain. -/
theorem no_contract_free_simultaneous_minimum {X : Type u} {R : Type v}
    (x₀ x₁ : X) (hdistinct : x₀ ≠ x₁) (rho : X -> R) :
    ¬ (KernelEqual rho (fun _ : X => true) ∧ KernelEqual rho (id : X -> X)) := by
  rintro ⟨hconstant, hidentity⟩
  have representationCollision : rho x₀ = rho x₁ :=
    (hconstant x₀ x₁).mpr rfl
  exact hdistinct ((hidentity x₀ x₁).mp representationCollision)

/-- The identity representation is sufficient for every fixed behavior map. -/
theorem identity_is_universally_sufficient {X : Type u} {B : Type v}
    (beta : X -> B) :
    ExactlySufficient beta (id : X -> X) := by
  refine ⟨fun represented => beta represented.val, ?_⟩
  intro x
  rfl

/-- FAR-CORE-004 in its governing prose form: no representation is simultaneously a
least-informative *sufficient* representation for two observation contracts, hence not for
every observation contract on a nontrivial domain.

`no_contract_free_simultaneous_minimum` states the kernel incompatibility.  This states the
minimality claim itself, through `leastInformativeSufficient_iff_kernelEqual`, so the governed
statement no longer depends on reading kernel equality as a definition of minimality. -/
theorem no_simultaneous_least_informative_sufficient {X : Type u} {R : Type v}
    (x₀ x₁ : X) (hdistinct : x₀ ≠ x₁) (rho : X -> R) :
    ¬ (LeastInformativeSufficient (fun _ : X => true) rho ∧
        LeastInformativeSufficient (id : X -> X) rho) := by
  rintro ⟨hconstant, hidentity⟩
  exact no_contract_free_simultaneous_minimum x₀ x₁ hdistinct rho
    ⟨(leastInformativeSufficient_iff_kernelEqual (fun _ : X => true) rho).mp hconstant,
      (leastInformativeSufficient_iff_kernelEqual (id : X -> X) rho).mp hidentity⟩

/-! ## FAR-CORE-005 -/

/-- Invariance under a declared class of typed self-transformations. -/
def InvariantUnder {X : Type u} (transformations : (X -> X) -> Prop)
    (property : X -> Prop) : Prop :=
  ∀ transformation, transformations transformation ->
    ∀ x, property x ↔ property (transformation x)

/-- Invariants are antitone in the admitted transformation class. -/
theorem invariants_antitone {X : Type u}
    {smaller larger : (X -> X) -> Prop} {property : X -> Prop}
    (hinclusion : ∀ transformation, smaller transformation -> larger transformation)
    (hinvariant : InvariantUnder larger property) :
    InvariantUnder smaller property := by
  intro transformation hmember
  exact hinvariant transformation (hinclusion transformation hmember)

/-! ## FAR-CORE-006 -/

/-- An injection is an equivalence with its reachable image. -/
noncomputable def embeddingRangeEquiv {X : Type u} {H : Type v}
    (encoding : X -> H) (hinjective : IsInjective encoding) :
    Isomorphism X (RepImage encoding) where
  toFun := imageValue encoding
  invFun := fun represented => Classical.choose represented.property
  left_inv := by
    intro x
    apply hinjective
    exact Classical.choose_spec (imageValue encoding x).property
  right_inv := by
    intro represented
    apply Subtype.ext
    exact Classical.choose_spec represented.property

/-- Transport a finitary operation along an equivalence. -/
def transportOperation {X : Type u} {Y : Type v} (equiv : Isomorphism X Y) {n : Nat}
    (operation : (Fin n -> X) -> X) : (Fin n -> Y) -> Y :=
  fun arguments => equiv.toFun (operation (fun i => equiv.invFun (arguments i)))

/-- Every named operation commutes with its transported image operation. -/
theorem transport_operation_commutes {X : Type u} {H : Type v}
    (encoding : X -> H) (hinjective : IsInjective encoding) {n : Nat}
    (operation : (Fin n -> X) -> X) (arguments : Fin n -> X) :
    transportOperation (embeddingRangeEquiv encoding hinjective) operation
      (fun i => imageValue encoding (arguments i)) =
      imageValue encoding (operation arguments) := by
  apply Subtype.ext
  apply congrArg encoding
  apply congrArg operation
  funext i
  exact (embeddingRangeEquiv encoding hinjective).left_inv (arguments i)

/-- Transport a finitary relation along an equivalence. -/
def transportRelation {X : Type u} {Y : Type v} (equiv : Isomorphism X Y) {n : Nat}
    (relation : (Fin n -> X) -> Prop) : (Fin n -> Y) -> Prop :=
  fun arguments => relation (fun i => equiv.invFun (arguments i))

/-- Every named relation commutes with its transported image relation. -/
theorem transport_relation_commutes {X : Type u} {H : Type v}
    (encoding : X -> H) (hinjective : IsInjective encoding) {n : Nat}
    (relation : (Fin n -> X) -> Prop) (arguments : Fin n -> X) :
    transportRelation (embeddingRangeEquiv encoding hinjective) relation
      (fun i => imageValue encoding (arguments i)) ↔ relation arguments := by
  have harguments :
      (fun i => (embeddingRangeEquiv encoding hinjective).invFun
        (imageValue encoding (arguments i))) = arguments := by
    funext i
    exact (embeddingRangeEquiv encoding hinjective).left_inv (arguments i)
  simp [transportRelation, harguments]

/-! ## FAR-CORE-007 -/

/-- Reified occurrences of a binary relation. -/
abbrev RelationOccurrence {X : Type u} (relation : X -> X -> Prop) :=
  { pair : X × X // relation pair.1 pair.2 }

/-- Typed argument position retained by the reified presentation. -/
inductive ArgumentPosition where
  | left
  | right
  deriving DecidableEq

/-- Typed incidence from a relation occurrence to one argument position. -/
def typedIncidence {X : Type u} {relation : X -> X -> Prop}
    (occurrence : RelationOccurrence relation) (position : ArgumentPosition) (value : X) : Prop :=
  match position with
  | .left => occurrence.val.1 = value
  | .right => occurrence.val.2 = value

/-- A binary relation is recovered exactly from occurrences plus typed incidence. -/
theorem reification_recovers_relation {X : Type u} (relation : X -> X -> Prop) (x y : X) :
    relation x y ↔
      ∃ occurrence : RelationOccurrence relation,
        typedIncidence occurrence .left x ∧ typedIncidence occurrence .right y := by
  constructor
  · intro hrelation
    exact ⟨⟨(x, y), hrelation⟩, rfl, rfl⟩
  · rintro ⟨⟨⟨left, right⟩, hrelation⟩, hleft, hright⟩
    simp [typedIncidence] at hleft hright
    subst left
    subst right
    exact hrelation

/-- Count only primitive sort and relation symbols in a presentation. -/
structure PrimitiveVocabularyCount where
  sortCount : Nat
  relationCount : Nat
  deriving DecidableEq

/-- Direct presentation: one carrier sort and one binary relation symbol. -/
def directBinaryVocabulary : PrimitiveVocabularyCount where
  sortCount := 1
  relationCount := 1

/-- Reified presentation: participant, occurrence, and position sorts with one incidence relation. -/
def reifiedIncidenceVocabulary : PrimitiveVocabularyCount where
  sortCount := 3
  relationCount := 1

/-- Exact recovery plus unequal primitive-count profiles witnesses count noninvariance. -/
theorem primitive_vocabulary_count_noninvariant {X : Type u}
    (relation : X -> X -> Prop) :
    (∀ x y, relation x y ↔
      ∃ occurrence : RelationOccurrence relation,
        typedIncidence occurrence .left x ∧ typedIncidence occurrence .right y) ∧
      directBinaryVocabulary ≠ reifiedIncidenceVocabulary := by
  constructor
  · intro x y
    exact reification_recovers_relation relation x y
  · decide

/-! ## FAR-CORE-008 -/

/-- Combine a tagged dependent operator family into one dispatcher. -/
def combineOperator {I : Type u} {A : I -> Type v} {B : Type w}
    (family : (i : I) -> A i -> B) : Sigma A -> B :=
  fun tagged => family tagged.1 tagged.2

/-- Split one tagged dispatcher back into its operator family. -/
def splitOperator {I : Type u} {A : I -> Type v} {B : Type w}
    (dispatcher : Sigma A -> B) : (i : I) -> A i -> B :=
  fun i argument => dispatcher ⟨i, argument⟩

/-- Explicit finiteness witness for the operator-tag carrier. -/
structure FiniteTagCarrier (I : Type u) where
  enumeration : List I
  complete : ∀ tag, tag ∈ enumeration

/-- A finite tagged family, with finiteness carried rather than silently assumed. -/
structure FiniteOperatorFamily (I : Type u) (A : I -> Type v) (B : Type w) where
  tags : FiniteTagCarrier I
  operation : (i : I) -> A i -> B

/-- A dispatcher whose tag carrier is explicitly finite. -/
structure FiniteTaggedDispatcher (I : Type u) (A : I -> Type v) (B : Type w) where
  tags : FiniteTagCarrier I
  dispatch : Sigma A -> B

/-- Count the named primitive operator symbols in a presentation. -/
structure PrimitiveOperatorCount where
  operatorCount : Nat
  deriving DecidableEq

/-- A concrete two-operator presentation before tagged dispatch. -/
def splitTwoOperatorVocabulary : PrimitiveOperatorCount where
  operatorCount := 2

/-- The faithfully equivalent tagged-dispatch presentation uses one primitive dispatcher. -/
def combinedDispatcherVocabulary : PrimitiveOperatorCount where
  operatorCount := 1

/-- Splitting the combined finite family recovers every tagged operator. -/
theorem combine_split_operator_family {I : Type u}
    {A : I -> Type v} {B : Type w} (family : FiniteOperatorFamily I A B) :
    splitOperator (combineOperator family.operation) = family.operation := by
  funext i argument
  rfl

/-- Combining a split tagged dispatcher recovers the dispatcher. -/
theorem split_combine_operator {I : Type u}
    {A : I -> Type v} {B : Type w} (dispatcher : FiniteTaggedDispatcher I A B) :
    combineOperator (splitOperator dispatcher.dispatch) = dispatcher.dispatch := by
  funext tagged
  cases tagged
  rfl

/-- A concrete finite two-operator presentation is faithfully recoverable from one tagged
    dispatcher while the primitive operator counts differ. -/
theorem finite_operator_count_noninvariant
    {A : Bool -> Type v} {B : Type w}
    (opFalse : A false -> B) (opTrue : A true -> B) :
    let family : (i : Bool) -> A i -> B := fun
      | false => opFalse
      | true => opTrue
    let dispatcher : Sigma A -> B := combineOperator family
    (splitOperator dispatcher = family) ∧
      splitTwoOperatorVocabulary ≠ combinedDispatcherVocabulary := by
  dsimp
  constructor
  · funext i argument
    cases i <;> rfl
  · decide

/-! ## FAR-CORE-009 -/

/-- A proper finite panel has two completions that agree on-panel and disagree off-panel. -/
theorem finite_panel_two_completions {D : Type u} [DecidableEq D]
    (panel : List D) (outside : D) (houtside : outside ∉ panel) :
    ∃ trueCompletion falseCompletion : D -> Prop,
      (∀ x ∈ panel, trueCompletion x ↔ falseCompletion x) ∧
      trueCompletion outside ∧ ¬ falseCompletion outside := by
  refine ⟨fun _ => True, fun x => x ≠ outside, ?_, trivial, ?_⟩
  · intro x hx
    have hne : x ≠ outside := by
      intro hequal
      subst x
      exact houtside hx
    constructor
    · intro _
      exact hne
    · intro _
      trivial
  · intro hself
    exact hself rfl

/-- An arbitrary observed predicate on the finite panel has two extensions agreeing
with every panel observation but disagreeing at an outside case. Unlike the
unparameterized completion witness above, this ties both extensions to the
actual submitted panel predicate rather than merely to each other.
This remains a finite-panel underdetermination result, not an open-domain
completeness or soundness theorem. -/
theorem finite_panel_observation_extensions {D : Type u} [DecidableEq D]
    (panel : List D) (observed : D -> Prop) (outside : D)
    (houtside : outside ∉ panel) :
    ∃ positive negative : D -> Prop,
      (∀ x ∈ panel, positive x ↔ observed x) ∧
      (∀ x ∈ panel, negative x ↔ observed x) ∧
      positive outside ∧ ¬ negative outside := by
  classical
  refine ⟨(fun x => if x ∈ panel then observed x else True),
    (fun x => if x ∈ panel then observed x else False), ?_, ?_, ?_, ?_⟩
  · intro x hx
    simp [hx]
  · intro x hx
    simp [hx]
  · simp [houtside]
  · simp [houtside]


/-! ## FAR-CORE-010 -/

/-- Exact common theory for fixed language/interpretation profile/target class. -/
def CommonTheory {Index : Type u} {Sentence : Type v}
    (truth : Index -> Sentence -> Prop) : Sentence -> Prop :=
  fun sentence => ∀ index, truth index sentence

/-- The part of exact common theory not already in the declared frame closure. -/
def Residue {Index : Type u} {Sentence : Type v}
    (truth : Index -> Sentence -> Prop)
    (consequence : (Sentence -> Prop) -> Sentence -> Prop)
    (frame : Sentence -> Prop) : Sentence -> Prop :=
  fun sentence => CommonTheory truth sentence ∧ ¬ consequence frame sentence

/-- Gamma is absent from exact common theory when the interpreted models stay fixed. -/
theorem commonTheory_frame_independent {Index : Type u} {Sentence : Type v}
    (truth : Index -> Sentence -> Prop)
    (frame₀ frame₁ : Sentence -> Prop) :
    (fun _frame : Sentence -> Prop => CommonTheory truth) frame₀ =
      (fun _frame : Sentence -> Prop => CommonTheory truth) frame₁ := by
  rfl

/-- Pointwise-equivalent fixed truth profiles have the same exact common theory. -/
theorem commonTheory_invariant_under_truth_equivalence
    {Index : Type u} {Sentence : Type v}
    (truth₀ truth₁ : Index -> Sentence -> Prop)
    (hequivalent : ∀ index sentence, truth₀ index sentence ↔ truth₁ index sentence) :
    CommonTheory truth₀ = CommonTheory truth₁ := by
  ext sentence
  constructor <;> intro h index
  · exact (hequivalent index sentence).mp (h index)
  · exact (hequivalent index sentence).mpr (h index)

/-- A common sentence crossing the frame closure boundary changes the residue. -/
theorem residue_can_change_with_frame {Index : Type u} {Sentence : Type v}
    (truth : Index -> Sentence -> Prop)
    (consequence : (Sentence -> Prop) -> Sentence -> Prop)
    (frame₀ frame₁ : Sentence -> Prop)
    (sentence : Sentence) (hcommon : CommonTheory truth sentence)
    (houtside₀ : ¬ consequence frame₀ sentence)
    (hinside₁ : consequence frame₁ sentence) :
    Residue truth consequence frame₀ ≠ Residue truth consequence frame₁ := by
  intro hequal
  have hresidue₀ : Residue truth consequence frame₀ sentence := ⟨hcommon, houtside₀⟩
  have hresidue₁ : Residue truth consequence frame₁ sentence :=
    congrFun hequal sentence ▸ hresidue₀
  exact hresidue₁.2 hinside₁

/-! ## FAR-CORE-011 -/

/-- Omitting an attainable consequence-affecting parameter creates a fatal collision. -/
theorem omitted_parameter_refutes_sufficiency
    {X : Type u} {Context : Type v} {B : Type w} {R : Type u}
    (rho₀ : X -> R) (beta : X × Context -> B)
    (x : X) (context₀ context₁ : Context)
    (hbehavior : beta (x, context₀) ≠ beta (x, context₁)) :
    ¬ ExactlySufficient beta (fun pair : X × Context => rho₀ pair.1) := by
  apply collision_refutes_sufficiency beta (fun pair : X × Context => rho₀ pair.1)
    (x := (x, context₀)) (y := (x, context₁))
  · rfl
  · exact hbehavior

/-! ## FAR-CORE-012 -/

/-- Minimal typed outcomes needed for the determinate-absence/Unknown distinction. -/
inductive EpistemicOutcome where
  | present
  | absent
  | unknown
  deriving DecidableEq, Repr

/-- Exact sufficiency preserves a declared absence/Unknown distinction. -/
theorem absent_unknown_must_separate {X : Type u} {R : Type v}
    (rho : X -> R) (beta : X -> EpistemicOutcome)
    (xAbsent xUnknown : X)
    (hAbsent : beta xAbsent = .absent) (hUnknown : beta xUnknown = .unknown)
    (hsufficient : ExactlySufficient beta rho) :
    rho xAbsent ≠ rho xUnknown := by
  intro hcollision
  obtain ⟨decoder, hdecoder⟩ := hsufficient
  have himage : imageValue rho xAbsent = imageValue rho xUnknown := by
    apply Subtype.ext
    exact hcollision
  have hbehavior : beta xAbsent = beta xUnknown := by
    rw [← hdecoder xAbsent, ← hdecoder xUnknown]
    exact congrArg decoder himage
  rw [hAbsent, hUnknown] at hbehavior
  cases hbehavior

end FARCoreV11
