import Std

/-!
Research-only independent reconstruction of FAR's exact mathematical kernel.
Uses only Lean/Std; does not import Project FAR theorem libraries. Every
theorem is relative to a fixed behavior map. No empirical claims are made.
-/
namespace FARFoundationalAudit

universe u v w

abbrev Image {X : Type u} {R : Type w} (rho : X -> R) :=
  {r : R // ∃ x : X, rho x = r}

def represented {X : Type u} {R : Type w} (rho : X -> R) (x : X) : Image rho :=
  ⟨rho x, ⟨x, rfl⟩⟩

def Sufficient {X : Type u} {B : Type v} {R : Type w}
    (beta : X -> B) (rho : X -> R) : Prop :=
  ∃ d : Image rho -> B, ∀ x, d (represented rho x) = beta x

def PreservesCollisions {X : Type u} {B : Type v} {R : Type w}
    (rho : X -> R) (beta : X -> B) : Prop :=
  ∀ ⦃x y⦄, rho x = rho y -> beta x = beta y

def EqualKernels {X : Type u} {B : Type v} {R : Type w}
    (rho : X -> R) (beta : X -> B) : Prop :=
  ∀ x y, rho x = rho y ↔ beta x = beta y

theorem sufficiency_iff_collision_preservation
    {X : Type u} {B : Type v} {R : Type w}
    (beta : X -> B) (rho : X -> R) :
    Sufficient beta rho ↔ PreservesCollisions rho beta := by
  constructor
  · rintro ⟨d, hd⟩ x y hxy
    rw [← hd x, ← hd y]
    apply congrArg d
    apply Subtype.ext
    exact hxy
  · intro h
    classical
    let d : Image rho -> B := fun r => beta (Classical.choose r.property)
    refine ⟨d, ?_⟩
    intro x
    apply h
    exact Classical.choose_spec (represented rho x).property

theorem counterexample_collision
    {X : Type u} {B : Type v} {R : Type w}
    (beta : X -> B) (rho : X -> R) {x y : X}
    (hSame : rho x = rho y) (hDifferent : beta x ≠ beta y) :
    ¬ Sufficient beta rho := by
  intro hs
  apply hDifferent
  exact (sufficiency_iff_collision_preservation beta rho).mp hs hSame

/-! Information-minimality is a precise order on representation kernels. -/
def Least {X : Type u} {B : Type v} {R : Type w}
    (beta : X -> B) (rho : X -> R) : Prop :=
  Sufficient beta rho ∧
    ∀ (S : Type u) (sigma : X -> S),
      Sufficient beta sigma -> PreservesCollisions sigma rho

def observationalSetoid {X : Type u} {B : Type v} (beta : X -> B) : Setoid X where
  r x y := beta x = beta y
  iseqv := {
    refl := fun _ => rfl
    symm := fun h => h.symm
    trans := fun hxy hyz => hxy.trans hyz
  }

abbrev QuotientOf {X : Type u} {B : Type v} (beta : X -> B) :=
  Quotient (observationalSetoid beta)

def project {X : Type u} {B : Type v} (beta : X -> B) (x : X) :
    QuotientOf beta := Quotient.mk (observationalSetoid beta) x

def observable {X : Type u} {B : Type v} (beta : X -> B) :
    QuotientOf beta -> B :=
  Quotient.lift beta (fun _ _ h => h)

theorem quotient_sufficient {X : Type u} {B : Type v} (beta : X -> B) :
    Sufficient beta (project beta) := by
  refine ⟨fun r => observable beta r.val, ?_⟩
  intro x
  rfl

theorem least_iff_equal_kernels
    {X : Type u} {B : Type v} {R : Type w}
    (beta : X -> B) (rho : X -> R) :
    Least beta rho ↔ EqualKernels rho beta := by
  constructor
  · rintro ⟨hs, hleast⟩ x y
    constructor
    · intro hxy
      exact (sufficiency_iff_collision_preservation beta rho).mp hs hxy
    · intro hxy
      exact hleast (QuotientOf beta) (project beta)
        (quotient_sufficient beta) (Quotient.sound hxy)
  · intro hk
    refine ⟨(sufficiency_iff_collision_preservation beta rho).mpr
      (fun {_ _} h => (hk _ _).mp h), ?_⟩
    intro S sigma hs
    exact fun {x y} hxy => (hk x y).mpr
      ((sufficiency_iff_collision_preservation beta sigma).mp hs hxy)

theorem quotient_least {X : Type u} {B : Type v} (beta : X -> B) :
    Least beta (project beta) := by
  apply (least_iff_equal_kernels beta (project beta)).mpr
  intro x y
  constructor
  · intro h
    exact congrArg (observable beta) h
  · intro h
    exact Quotient.sound h

theorem quotient_universal
    {X : Type u} {B : Type v} {R : Type w}
    (beta : X -> B) (rho : X -> R) (hs : Sufficient beta rho) :
    ∃ h : Image rho -> QuotientOf beta,
      (∀ x, h (represented rho x) = project beta x) ∧
      ∀ h' : Image rho -> QuotientOf beta,
        (∀ x, h' (represented rho x) = project beta x) -> h' = h := by
  classical
  let h : Image rho -> QuotientOf beta :=
    fun r => project beta (Classical.choose r.property)
  have href := (sufficiency_iff_collision_preservation beta rho).mp hs
  have hagree : ∀ x, h (represented rho x) = project beta x := by
    intro x
    apply Quotient.sound
    exact href (Classical.choose_spec (represented rho x).property)
  refine ⟨h, hagree, ?_⟩
  intro h' h'agree
  funext r
  obtain ⟨x, hx⟩ := r.property
  have hr : r = represented rho x := by
    apply Subtype.ext
    exact hx.symm
  rw [hr, h'agree x, hagree x]

theorem identity_sufficient {X : Type u} {B : Type v} (beta : X -> B) :
    Sufficient beta (id : X -> X) := by
  refine ⟨fun r => beta r.val, ?_⟩
  intro x
  rfl

theorem incompatible_contract_minima
    {X : Type u} {R : Type w}
    (x y : X) (hne : x ≠ y) (rho : X -> R) :
    ¬ (Least (fun _ : X => true) rho ∧ Least (id : X -> X) rho) := by
  rintro ⟨hconst, hid⟩
  have hk0 := (least_iff_equal_kernels (fun _ : X => true) rho).mp hconst
  have hk1 := (least_iff_equal_kernels (id : X -> X) rho).mp hid
  have hxy : rho x = rho y := (hk0 x y).mpr rfl
  exact hne ((hk1 x y).mp hxy)

theorem two_case_loss :
    ¬ Sufficient (id : Bool -> Bool) (fun _ : Bool => Unit.unit) := by
  apply counterexample_collision (id : Bool -> Bool) (fun _ : Bool => Unit.unit)
    (x := false) (y := true)
  · rfl
  · simp

theorem singleton_simultaneous_minimum :
    Least (fun _ : Unit => true) (id : Unit -> Unit) ∧
    Least (id : Unit -> Unit) (id : Unit -> Unit) := by
  constructor
  · apply (least_iff_equal_kernels _ _).mpr
    intro x y
    cases x
    cases y
    constructor <;> intro _ <;> rfl
  · apply (least_iff_equal_kernels _ _).mpr
    intro x y
    cases x
    cases y
    constructor <;> intro _ <;> rfl

/-! Stronger impossibility fails if allowed contracts cannot distinguish. -/
theorem singleton_outcome_contracts_have_one_minimum :
    ∃ rho : Bool -> Unit, ∀ beta : Bool -> Unit, Least beta rho := by
  refine ⟨fun _ => Unit.unit, ?_⟩
  intro beta
  apply (least_iff_equal_kernels beta _).mpr
  intro x y
  cases beta x
  cases beta y
  constructor <;> intro _ <;> rfl

theorem proper_panel_underdetermines
    {D : Type u} [DecidableEq D]
    (panel : List D) (outside : D) (h : outside ∉ panel) :
    ∃ p q : D -> Prop,
      (∀ d ∈ panel, p d ↔ q d) ∧ p outside ∧ ¬ q outside := by
  refine ⟨fun _ => True, fun d => d ≠ outside, ?_, trivial, ?_⟩
  · intro d hd
    have dne : d ≠ outside := by
      intro heq
      subst d
      exact h hd
    constructor
    · intro _
      exact dne
    · intro _
      trivial
  · intro hcontra
    exact hcontra rfl

def oneTest (_ : Unit) (s : Bool × Bool) : Bool := s.1
def splitAction (s : Bool × Bool) : Bool × Bool := (s.2, s.2)
def ObservationalAgreement {T : Type u} {X : Type v} {V : Type w}
    (obs : T -> X -> V) (x y : X) : Prop :=
  ∀ t, obs t x = obs t y

theorem missing_continuation_counterexample :
    ObservationalAgreement oneTest (false, false) (false, true) ∧
    ¬ ObservationalAgreement oneTest
      (splitAction (false, false)) (splitAction (false, true)) := by
  constructor
  · intro t
    cases t
    rfl
  · intro h
    have := h Unit.unit
    simp [oneTest, splitAction] at this

def Common {Index : Type u} {Sentence : Type v}
    (truth : Index -> Sentence -> Prop) (s : Sentence) : Prop :=
  ∀ i, truth i s

def Residue {Index : Type u} {Sentence : Type v}
    (truth : Index -> Sentence -> Prop)
    (closure : (Sentence -> Prop) -> Sentence -> Prop)
    (frame : Sentence -> Prop) (s : Sentence) : Prop :=
  Common truth s ∧ ¬ closure frame s

theorem common_is_frame_independent
    {Index : Type u} {Sentence : Type v}
    (truth : Index -> Sentence -> Prop)
    (frame0 frame1 : Sentence -> Prop) :
    (fun _ : Sentence -> Prop => Common truth) frame0 =
    (fun _ : Sentence -> Prop => Common truth) frame1 := by
  rfl

theorem residue_may_change
    {Index : Type u} {Sentence : Type v}
    (truth : Index -> Sentence -> Prop)
    (closure : (Sentence -> Prop) -> Sentence -> Prop)
    (frame0 frame1 : Sentence -> Prop) (s : Sentence)
    (hc : Common truth s)
    (h0 : ¬ closure frame0 s) (h1 : closure frame1 s) :
    Residue truth closure frame0 ≠ Residue truth closure frame1 := by
  intro heq
  have ha : Residue truth closure frame0 s := ⟨hc, h0⟩
  have hb : Residue truth closure frame1 s := congrFun heq s ▸ ha
  exact hb.2 h1

/-! The weakest premise for quotient action descent is congruence. -/
def ObsSetoid {T : Type u} {X : Type v} {V : Type w}
    (obs : T -> X -> V) : Setoid X where
  r := ObservationalAgreement obs
  iseqv := {
    refl := fun _ _ => rfl
    symm := fun h t => (h t).symm
    trans := fun h k t => (h t).trans (k t)
  }

abbrev ObsQuot {T : Type u} {X : Type v} {V : Type w}
    (obs : T -> X -> V) := Quotient (ObsSetoid obs)

def obsQuot {T : Type u} {X : Type v} {V : Type w}
    (obs : T -> X -> V) (x : X) : ObsQuot obs :=
  Quotient.mk (ObsSetoid obs) x

def obsLift {T : Type u} {X : Type v} {V : Type w}
    (obs : T -> X -> V) (t : T) : ObsQuot obs -> V :=
  Quotient.lift (fun x => obs t x) (fun _ _ h => h t)

def Congruent {T : Type u} {X : Type v} {V : Type w}
    (obs : T -> X -> V) (action : X -> X) : Prop :=
  ∀ ⦃x y⦄, ObservationalAgreement obs x y ->
    ObservationalAgreement obs (action x) (action y)

theorem action_descends_iff_congruent
    {T : Type u} {X : Type v} {V : Type w}
    (obs : T -> X -> V) (action : X -> X) :
    (∃ lifted : ObsQuot obs -> ObsQuot obs,
       ∀ x, lifted (obsQuot obs x) = obsQuot obs (action x)) ↔
    Congruent obs action := by
  constructor
  · rintro ⟨lifted, hlifted⟩ x y hxy t
    have hquot : obsQuot obs x = obsQuot obs y := Quotient.sound hxy
    have hstep : obsQuot obs (action x) = obsQuot obs (action y) := by
      rw [← hlifted x, ← hlifted y]
      exact congrArg lifted hquot
    exact congrArg (obsLift obs t) hstep
  · intro hc
    refine ⟨Quotient.lift (fun x => obsQuot obs (action x))
      (fun x y h => Quotient.sound (hc h)), ?_⟩
    intro x
    rfl

def ContextClosed {T : Type u} {X : Type v} {V : Type w}
    (obs : T -> X -> V) (action : X -> X) : Prop :=
  ∀ t, ∃ continued : T, ∀ x, obs t (action x) = obs continued x

theorem closed_implies_congruent
    {T : Type u} {X : Type v} {V : Type w}
    (obs : T -> X -> V) (action : X -> X)
    (h : ContextClosed obs action) : Congruent obs action := by
  intro x y hxy t
  obtain ⟨continued, hcontinued⟩ := h t
  rw [hcontinued x, hcontinued y]
  exact hxy continued

def constantAction (_ : Bool × Bool) : Bool × Bool := (false, false)

theorem closure_is_not_necessary :
    Congruent oneTest constantAction ∧
      ¬ ContextClosed oneTest constantAction := by
  constructor
  · intro x y _ t
    cases t
    rfl
  · intro h
    obtain ⟨continued, hcontinued⟩ := h Unit.unit
    have h0 := hcontinued (true, false)
    cases continued
    simp [oneTest, constantAction] at h0

#print axioms FARFoundationalAudit.sufficiency_iff_collision_preservation
#print axioms FARFoundationalAudit.quotient_least
#print axioms FARFoundationalAudit.quotient_universal
#print axioms FARFoundationalAudit.incompatible_contract_minima
#print axioms FARFoundationalAudit.singleton_outcome_contracts_have_one_minimum
#print axioms FARFoundationalAudit.action_descends_iff_congruent
#print axioms FARFoundationalAudit.closure_is_not_necessary

end FARFoundationalAudit
