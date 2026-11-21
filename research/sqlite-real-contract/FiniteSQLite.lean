import Std

/-!
Research-only typed table supplied by live SQLite oracle, verified independently
by replay.py against BOTH Python sqlite3 and the direct native C API. These
kernel-checkable consequences range over SIX declared cases and THREE queries.
The extra query is a deliberately extended contract and supplies a collision.
-/
namespace FARSQLiteReal

inductive Case where
  | nullCase | integerZero | integerOne | textZero | textOne | textOther
  deriving DecidableEq, Repr

structure Behavior where
  isNull : Bool
  eqIntegerZero : Option Bool
  eqIntegerOne : Option Bool
  deriving DecidableEq, Repr

def behavior : Case → Behavior
  | .nullCase => ⟨true, none, none⟩
  | .integerZero => ⟨false, some true, some false⟩
  | .integerOne => ⟨false, some false, some true⟩
  | .textZero => ⟨false, some false, some false⟩
  | .textOne => ⟨false, some false, some false⟩
  | .textOther => ⟨false, some false, some false⟩

def extension : Case → Option Bool
  | .nullCase => none
  | .integerZero => some false
  | .integerOne => some false
  | .textZero => some true
  | .textOne => some false
  | .textOther => some false

def quotientCode : Case → Nat
  | .nullCase => 0
  | .integerZero => 1
  | .integerOne => 2
  | .textZero => 3
  | .textOne => 3
  | .textOther => 3

def storageClass : Case → Nat
  | .nullCase => 0
  | .integerZero => 1
  | .integerOne => 1
  | .textZero => 2
  | .textOne => 2
  | .textOther => 2

def decode : Nat → Behavior
  | 0 => behavior .nullCase
  | 1 => behavior .integerZero
  | 2 => behavior .integerOne
  | _ => behavior .textZero

/-- Positive: every case's complete three-query behavior factors through the code. -/
theorem full_finite_factorization :
    ∀ c : Case, decode (quotientCode c) = behavior c := by
  intro c
  cases c <;> decide

/-- Positive: the code's kernel exactly matches SQLite's observed behavior kernel. -/
theorem finite_least_informative :
    ∀ x y : Case, (quotientCode x = quotientCode y) ↔
      (behavior x = behavior y) := by
  intro x y
  cases x <;> cases y <;> decide

/-- Real lossy representation: SQLite storage class merges values distinct by SQL. -/
theorem storage_class_loss :
    storageClass .integerZero = storageClass .integerOne ∧
      behavior .integerZero ≠ behavior .integerOne := by decide

/-- Real counterexample to extrapolating the quotient to an enlarged SQL contract. -/
theorem extension_loss :
    quotientCode .textZero = quotientCode .textOne ∧
      extension .textZero ≠ extension .textOne := by decide

#print axioms FARSQLiteReal.full_finite_factorization
#print axioms FARSQLiteReal.finite_least_informative
#print axioms FARSQLiteReal.storage_class_loss
#print axioms FARSQLiteReal.extension_loss

end FARSQLiteReal
