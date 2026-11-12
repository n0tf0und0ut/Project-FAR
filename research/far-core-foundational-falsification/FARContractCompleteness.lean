import Std

/-!
Research-only reconstruction of FAR's missing completeness premise. Does not import any
Project FAR theorem or formalization. Exact statements concern functions and typed values;
no proposition asserts a concrete system's observations actually exhaust reality.
-/
namespace FARContractCompleteness

universe u v w z

/-- A known observation `observe` captures every distinction of a fixed target `target`. -/
def Complete {World : Type u} {O : Type v} {Y : Type w}
    (observe : World → O) (target : World → Y) : Prop :=
  ∀ x y, observe x = observe y → target x = target y

/-- The concrete reachable observation values, not the arbitrary observable codomain. -/
abbrev ObsImage {World : Type u} {O : Type v} (observe : World → O) :=
  {o : O // ∃ x : World, observe x = o}

def reached {World : Type u} {O : Type v} (observe : World → O)
    (x : World) : ObsImage observe :=
  ⟨observe x, ⟨x, rfl⟩⟩

/-- Completeness is exact factorization. This is *relative to supplied target semantics*. -/
theorem complete_iff_decoder {World : Type u} {O : Type v} {Y : Type w}
    (observe : World → O) (target : World → Y) :
    Complete observe target ↔
      ∃ decode : ObsImage observe → Y,
        ∀ x, decode (reached observe x) = target x := by
  constructor
  · intro hcomplete
    classical
    let decode : ObsImage observe → Y := fun o =>
      target (Classical.choose o.property)
    refine ⟨decode, ?_⟩
    intro x
    apply hcomplete
    exact Classical.choose_spec (reached observe x).property
  · rintro ⟨decode, hdecode⟩ x y hxy
    rw [← hdecode x, ← hdecode y]
    apply congrArg decode
    apply Subtype.ext
    exact hxy

/-- Sharp boundary: completeness for every possible target iff the observer is injective. -/
theorem all_targets_iff_injective {World : Type u} {O : Type v}
    (observe : World → O) :
    (∀ (Y : Type u) (target : World → Y), Complete observe target) ↔
      Function.Injective observe := by
  constructor
  · intro hall x y hxy
    exact hall World (id : World → World) x y hxy
  · intro hinjective Y target x y hxy
    exact congrArg target (hinjective hxy)

/-- Two different target worlds produce indistinguishable observer evidence.
    The good and bad targets even agree on the sampled case `x`! -/
theorem ambiguous_targets_at_collision
    {World : Type u} {O : Type v}
    (observe : World → O) (x y : World)
    (hxy : observe x = observe y) (hne : x ≠ y) :
    ∃ good bad : World → World,
      Complete observe good ∧ ¬ Complete observe bad ∧ good x = bad x := by
  refine ⟨(fun _ => x), id, ?_, ?_, rfl⟩
  · intro a b _
    rfl
  · intro hcomplete
    exact hne (hcomplete x y hxy)

/-- Strongest positive bridge available from separately justified reference semantics.
    A valid *target-correspondence premise* is still required; the theorem cannot produce it. -/
theorem reference_bridge {World : Type u} {O : Type v}
    {Reference : Type w} {Y : Type z}
    (observe : World → O) (reference : World → Reference)
    (target : World → Y) (readout : Reference → Y)
    (hreference : Complete observe reference)
    (htarget : ∀ x, target x = readout (reference x)) :
    Complete observe target := by
  intro x y hobs
  rw [htarget x, htarget y]
  exact congrArg readout (hreference x y hobs)

/-- Finite explicit verification is sound if the list demonstrably covers the world. -/
theorem enumerated_world_certificate
    {World : Type u} {O : Type v} {Y : Type w}
    (cases : List World) (hcover : ∀ x, x ∈ cases)
    (observe : World → O) (target : World → Y)
    (hchecked : ∀ x, x ∈ cases → ∀ y, y ∈ cases →
      observe x = observe y → target x = target y) :
    Complete observe target := by
  intro x y hobs
  exact hchecked x (hcover x) y (hcover y) hobs

/-- Failure cannot be repaired downstream when the model itself collapses target-relevant
    world states. Even an identity representation on the model does not repair the loss. -/
theorem hidden_state_cannot_be_repaired
    {World : Type u} {Model : Type v} {R : Type w} {Y : Type z}
    (encode : World → Model) (rho : Model → R) (target : World → Y)
    (x y : World) (hmodel : encode x = encode y)
    (htarget : target x ≠ target y) :
    ¬ Complete (fun w => rho (encode w)) target := by
  intro hc
  exact htarget (hc x y (congrArg rho hmodel))

/-- Explicit two-bit hidden-variable obstruction. The model retains the first bit exactly,
    but the second bit determines the target; the forgotten bit is unrecoverable. -/
theorem identity_model_misses_hidden_bit :
    ¬ Complete (fun s : Bool × Bool => s.1) (fun s => s.2) := by
  apply hidden_state_cannot_be_repaired
    (encode := fun s : Bool × Bool => s.1)
    (rho := (id : Bool → Bool))
    (target := fun s : Bool × Bool => s.2)
    (x := (false, false)) (y := (false, true))
  · rfl
  · decide

/-- Conversely, exact real-to-model correspondence plus model-side preservation is enough.
    The correspondence premise must be established from outside the self-authored model. -/
theorem world_model_bridge
    {World : Type u} {Model : Type v} {R : Type w} {Y : Type z}
    (encode : World → Model) (rho : Model → R)
    (modelTarget : Model → Y) (worldTarget : World → Y)
    (hmodel : Complete rho modelTarget)
    (hcorrespondence : ∀ x, worldTarget x = modelTarget (encode x)) :
    Complete (fun x => rho (encode x)) worldTarget := by
  intro x y hobs
  rw [hcorrespondence x, hcorrespondence y]
  exact hmodel (encode x) (encode y) hobs

/-- A single sampled case cannot distinguish target completions that differ elsewhere. -/
theorem one_sample_cannot_certify_all_targets :
    ∃ good bad : Bool → Bool,
      good false = bad false ∧
      Complete (fun _ : Bool => Unit.unit) good ∧
      ¬ Complete (fun _ : Bool => Unit.unit) bad := by
  refine ⟨(fun _ => false), id, rfl, ?_, ?_⟩
  · intro x y _
    rfl
  · intro hc
    have h := hc false true rfl
    cases h

#print axioms FARContractCompleteness.complete_iff_decoder
#print axioms FARContractCompleteness.all_targets_iff_injective
#print axioms FARContractCompleteness.ambiguous_targets_at_collision
#print axioms FARContractCompleteness.reference_bridge
#print axioms FARContractCompleteness.enumerated_world_certificate
#print axioms FARContractCompleteness.hidden_state_cannot_be_repaired
#print axioms FARContractCompleteness.identity_model_misses_hidden_bit
#print axioms FARContractCompleteness.world_model_bridge
#print axioms FARContractCompleteness.one_sample_cannot_certify_all_targets

end FARContractCompleteness
