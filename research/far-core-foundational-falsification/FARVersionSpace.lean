import FARContractCompleteness

/-!
Research-only deeper audit: exact information required to decide semantic completeness.
No reality oracle is silently granted. Candidate contains only targets admitted by
the declared independent hypothesis predicate AND consistent with observed samples.
-/

namespace FARVersionSpace

open FARContractCompleteness

universe u v w

/-- Records are individually queried world states with authoritative target outcomes. -/
def Fits {World : Type u} {Y : Type w}
    (samples : List (World × Y)) (target : World → Y) : Prop :=
  ∀ record, record ∈ samples → target record.1 = record.2

/-- Possible target semantics after independent restrictions and oracle samples. -/
def Candidate {World : Type u} {Y : Type w}
    (hypotheses : (World → Y) → Prop)
    (samples : List (World × Y)) (target : World → Y) : Prop :=
  hypotheses target ∧ Fits samples target

/-- One binary answer must be correct for every remaining possible target. -/
def SoundVerdict {World : Type u} {O : Type v} {Y : Type w}
    (observe : World → O) (possible : (World → Y) → Prop)
    (answer : Bool) : Prop :=
  ∀ target, possible target → (answer = true ↔ Complete observe target)

/-- A sound binary decision exists iff the evidence fixes the verdict, provided at least one
    candidate exists. Empty candidate sets are inconsistent evidence, not a certification. -/
theorem binary_decidable_iff_candidates_agree
    {World : Type u} {O : Type v} {Y : Type w}
    (observe : World → O) (possible : (World → Y) → Prop)
    (nonempty : ∃ target, possible target) :
    (∃ answer : Bool, SoundVerdict observe possible answer) ↔
      ∀ f g, possible f → possible g →
        (Complete observe f ↔ Complete observe g) := by
  constructor
  · rintro ⟨answer, hanswer⟩ f g hf hg
    exact (hanswer f hf).symm.trans (hanswer g hg)
  · intro hagree
    obtain ⟨anchor, hanchor⟩ := nonempty
    classical
    by_cases hc : Complete observe anchor
    · refine ⟨true, ?_⟩
      intro f hf
      have hfcomplete := (hagree anchor f hanchor hf).mp hc
      simp [hfcomplete]
    · refine ⟨false, ?_⟩
      intro f hf
      have hnot : ¬ Complete observe f := by
        intro hcomp
        exact hc ((hagree anchor f hanchor hf).mpr hcomp)
      simp [hnot]

/-- Ambiguity makes a sound two-valued certificate impossible; a truthful verifier must
    preserve UNDERDETERMINED rather than collapse it into either verdict. -/
theorem conflicting_candidates_prevent_verdict
    {World : Type u} {O : Type v} {Y : Type w}
    (observe : World → O) (possible : (World → Y) → Prop)
    (good bad : World → Y)
    (hgood : possible good) (hbad : possible bad)
    (hc : Complete observe good) (hn : ¬ Complete observe bad) :
    ¬ ∃ answer : Bool, SoundVerdict observe possible answer := by
  rintro ⟨answer, hanswer⟩
  exact hn ((hanswer bad hbad).mp ((hanswer good hgood).mpr hc))

/-- A nonvacuous universal-positive certificate transfers to the actual target only when
    an externally justified membership premise places it inside the version space. -/
theorem candidate_certificate_sound
    {World : Type u} {O : Type v} {Y : Type w}
    (observe : World → O)
    (possible : (World → Y) → Prop)
    (actual : World → Y)
    (hactual : possible actual)
    (hcertificate : ∀ f, possible f → Complete observe f) :
    Complete observe actual := hcertificate actual hactual

/-- The key query lower bound: if even one state in a nontrivial observation fiber was not
    queried, two target functions agree on every queried state but have opposing verdicts.
    DecidableEq is used only for the explicit single-state flip. -/
theorem missing_nonsingleton_fiber_point_blocks_yes
    {World : Type u} {O : Type v} [DecidableEq World]
    (observe : World → O)
    (queried : World → Prop)
    (x y : World) (hxy : observe x = observe y)
    (hneq : x ≠ y) (hunqueried : ¬ queried x) :
    ∃ good bad : World → Bool,
      (∀ z, queried z → good z = bad z) ∧
      Complete observe good ∧ ¬ Complete observe bad := by
  let bad : World → Bool := fun z => if z = x then true else false
  refine ⟨fun _ => false, bad, ?_, ?_, ?_⟩
  · intro z hz
    have hzne : z ≠ x := by
      intro heq
      subst z
      exact hunqueried hz
    simp [bad, hzne]
  · intro z t _
    rfl
  · intro hcomplete
    have hdiff : bad x ≠ bad y := by
      simp [bad, hneq, Ne.symm hneq]
    exact hdiff (hcomplete x y hxy)

/-- Querying every state in each non-singleton fiber and checking paired target outputs
    equal is sufficient for positive completeness; singleton fibers need no query. -/
theorem complete_from_nontrivial_fiber_coverage
    {World : Type u} {O : Type v} {Y : Type w}
    (observe : World → O) (target : World → Y)
    (queried : World → Prop)
    (hcover : ∀ x y, observe x = observe y → x ≠ y → queried x ∧ queried y)
    (hchecked : ∀ x y, queried x → queried y →
       observe x = observe y → target x = target y) :
    Complete observe target := by
  intro x y hxy
  by_cases heq : x = y
  · subst y
    rfl
  · obtain ⟨hx, hy⟩ := hcover x y hxy heq
    exact hchecked x y hx hy hxy

/-- Empty/inconsistent version spaces satisfy both universal verdicts vacuously.
    Universal quantification must not become a positive certificate without consistency. -/
theorem empty_hypothesis_has_both_fake_verdicts
    {World : Type u} {O : Type v} {Y : Type w}
    (observe : World → O) :
    (∀ f : World → Y, False → Complete observe f) ∧
    (∀ f : World → Y, False → ¬ Complete observe f) := by
  constructor
  · intro f hf
    exact False.elim hf
  · intro f hf
    exact False.elim hf

#print axioms FARVersionSpace.binary_decidable_iff_candidates_agree
#print axioms FARVersionSpace.conflicting_candidates_prevent_verdict
#print axioms FARVersionSpace.missing_nonsingleton_fiber_point_blocks_yes
#print axioms FARVersionSpace.complete_from_nontrivial_fiber_coverage
#print axioms FARVersionSpace.empty_hypothesis_has_both_fake_verdicts

end FARVersionSpace
