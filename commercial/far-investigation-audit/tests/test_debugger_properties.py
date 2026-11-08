"""Generated property tests; optional in base runtime, executed in the campaign."""
import importlib.util
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from semantic import fidelity, compile_text, _count_truth
from engine import canonical

if importlib.util.find_spec("hypothesis"):
    from hypothesis import given, settings, strategies as st
    class GeneratedSemanticProperties(unittest.TestCase):
        @settings(max_examples=120,derandomize=True,deadline=None)
        @given(st.integers(0,99),st.integers(0,99))
        def test_thresholds_do_not_collapse(self,a,b):
            result=fidelity(f"At least {a} birds are blue.",{"atom":"P"},{"P":f"At least {b} birds are blue."})
            self.assertEqual(result["status"],"SUPPORTED_IN_GRAMMAR" if a==b else "CONTRADICTED")
            if a!=b:
                witness=result["witness"]
                self.assertNotEqual(witness["source_value"],witness["interpretation_value"])

        @settings(max_examples=100,derandomize=True,deadline=None)
        @given(st.sampled_from(["some","all","no"]),st.sampled_from(["before","after","during","in","on"]),st.integers(1,9999))
        def test_roundtrip_identity_is_deterministic(self,q,time,year):
            source=f"{q} birds are blue {time} {year:04d}."
            a=fidelity(source,{"atom":"P"},{"P":source})
            b=fidelity(source,{"atom":"P"},{"P":source})
            self.assertEqual(canonical(a),canonical(b))
            self.assertEqual(a["status"],"SUPPORTED_IN_GRAMMAR")

        @settings(max_examples=100,derandomize=True,deadline=None)
        @given(st.sampled_from(["may be","must be","should be","can be","will be"]))
        def test_outer_modal_negation_does_not_move_inside(self,copula):
            self.assertEqual(fidelity(f"Rain {copula} not wet.",{"not":{"atom":"P"}},{"P":f"Rain {copula} wet."})["status"],"ABSTAIN")
else:
    @unittest.skip("optional Hypothesis unavailable; recorded internal campaign installs and executes it")
    class GeneratedSemanticProperties(unittest.TestCase):
        def test_optional_property_dependency(self):
            pass
