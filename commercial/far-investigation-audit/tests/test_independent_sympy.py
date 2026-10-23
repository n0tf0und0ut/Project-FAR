"""Third-party solver cross-check over seeded finite formulas (not semantic fidelity)."""
import pathlib
import random
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from engine import entailment, evaluate
try:
    from sympy import And, Or, Not, Implies, symbols
    from sympy.logic.inference import satisfiable
except ImportError:
    satisfiable = None


@unittest.skipUnless(satisfiable is not None, "optional SymPy independent solver unavailable")
class IndependentlyImplementedLogicOracleTests(unittest.TestCase):
    def test_hundreds_of_seeded_argument_variants_match_sympy_sat(self):
        rng = random.Random(1729)
        atoms = ["P", "Q", "R", "S", "T"]
        symbols_by_name = dict(zip(atoms, symbols("P Q R S T")))

        def generated(level):
            if level == 0 or rng.random() < .3:
                k = rng.choice(atoms)
                return {"atom": k}, symbols_by_name[k]
            op = rng.choice(["not", "and", "or", "implies"])
            a, sa = generated(level - 1)
            if op == "not":
                return {"not": a}, Not(sa)
            b, sb = generated(level - 1)
            if op == "and":
                return {"and": [a,b]}, And(sa,sb)
            if op == "or":
                return {"or": [a,b]}, Or(sa,sb)
            return {"implies": [a,b]}, Implies(sa,sb)

        for index in range(220):
            premises = [generated(3) for _ in range(rng.randint(1,3))]
            conclusion, sym_conclusion = generated(3)
            our = entailment([pair[0] for pair in premises], conclusion)
            sym_premises = And(*[pair[1] for pair in premises])
            consistency = satisfiable(sym_premises)
            falsification = satisfiable(And(sym_premises, Not(sym_conclusion)))
            if consistency is False:
                expected = "INCONSISTENT_PREMISES"
            elif falsification is False:
                expected = "ENTAILS_CONDITIONALLY"
            else:
                expected = "DOES_NOT_ENTAIL"
            self.assertEqual(our["status"], expected, f"solver disagreement on seed 1729, case {index}")
            if expected == "DOES_NOT_ENTAIL":
                self.assertTrue(all(evaluate(pair[0], our["countermodel"]) for pair in premises))
                self.assertFalse(evaluate(conclusion, our["countermodel"]))
