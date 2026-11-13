"""Mutation tests: causal-identification gaps and fail-closed launch refusal."""
from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("v3_readiness", HERE / "audit_causal_readiness.py")
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class CausalIdentificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = audit.exact_json(audit.V3 / "preregistration-v1.0.json")
        cls.gate = audit.exact_json(audit.V3 / "execution-gate-v1.0.json")

    def test_live_v3_is_design_only_not_an_executed_trial(self):
        r = audit.audit_design(self.protocol, self.gate)
        self.assertEqual(r["arm_names"], ["baseline", "placebo", "far"])
        self.assertEqual(r["pilot_true_gates"], 0)
        self.assertEqual(r["pilot_total_gates"], 16)
        self.assertEqual(r["confirmatory_true_gates"], 0)
        self.assertEqual(r["confirmatory_total_gates"], 17)
        self.assertFalse(r["causal_effect_estimated"])

    def test_three_arms_cannot_identify_unique_far_effect(self):
        r = audit.audit_design(self.protocol, self.gate)
        self.assertFalse(r["far_minus_generic_checker_identified_by_protocol"])
        self.assertFalse(r["contains_matched_generic_active_comparator"])

    def test_same_three_arm_data_admit_conflicting_far_generic_verdicts(self):
        # Hypothetical countermodels, not observations of any FAR execution.
        observed = {"baseline": 0.4, "placebo": 0.4, "far": 0.6}
        a = {**observed, "generic_checker": 0.4}
        b = {**observed, "generic_checker": 0.6}
        self.assertEqual({k: a[k] for k in observed}, {k: b[k] for k in observed})
        self.assertGreater(a["far"] - a["generic_checker"], 0)
        self.assertEqual(b["far"] - b["generic_checker"], 0)

    def test_all_gates_true_still_not_prospective_authorization(self):
        gate = copy.deepcopy(self.gate)
        for name in gate["pilot_gates"]:
            gate["pilot_gates"][name] = True
        for name in gate["gates"]:
            gate["gates"][name] = True
        for field in ("execution_authorized", "model_calls_authorized",
                      "benchmark_execution_authorized", "pilot_execution_authorized",
                      "confirmatory_execution_authorized"):
            gate[field] = True
        r = audit.audit_design(self.protocol, gate)
        self.assertTrue(r["pilot_all_flags_and_gates_true"])
        self.assertTrue(r["confirmatory_all_flags_and_gates_true"])
        self.assertFalse(r["prospective_fully_bound_launch_record_verified"])
        self.assertFalse(r["pilot_model_calls_permitted_by_this_audit"])
        self.assertFalse(r["confirmatory_model_calls_permitted_by_this_audit"])

    def test_fake_generic_arm_does_not_generate_executed_outcomes(self):
        protocol = copy.deepcopy(self.protocol)
        protocol["arms"].append({"id": "generic_checker"})
        r = audit.audit_design(protocol, self.gate)
        self.assertFalse(r["far_minus_generic_checker_identified_by_protocol"])
        self.assertFalse(r["causal_effect_estimated"])
        self.assertEqual(r["far_mechanism_exercised_by_executions"],
                         "UNKNOWN_NO_VERIFIED_TOOL_EXECUTION_RECEIPTS")

    def test_even_declared_generic_estimand_creates_no_effect_without_runs(self):
        protocol = copy.deepcopy(self.protocol)
        protocol["arms"].append({"id": "generic_checker"})
        protocol["secondary_contrasts"].append("far_minus_generic_checker")
        r = audit.audit_design(protocol, self.gate)
        self.assertTrue(r["far_minus_generic_checker_identified_by_protocol"])
        self.assertFalse(r["causal_effect_estimated"])
        self.assertFalse(r["confirmatory_model_calls_permitted_by_this_audit"])

    def test_malformed_gate_counts_are_rejected(self):
        gate = copy.deepcopy(self.gate)
        gate["pilot_gates"]["theory_version_frozen"] = 1
        with self.assertRaises(ValueError):
            audit.audit_design(self.protocol, gate)

    def test_duplicate_arm_rejected(self):
        protocol = copy.deepcopy(self.protocol)
        protocol["arms"].append({"id": "far"})
        with self.assertRaises(ValueError):
            audit.audit_design(protocol, self.gate)

    def test_different_program_rejected(self):
        gate = copy.deepcopy(self.gate)
        gate["program_id"] = "OTHER-PROGRAM"
        with self.assertRaises(ValueError):
            audit.audit_design(self.protocol, gate)

    def test_duplicate_json_keys_rejected(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            p = pathlib.Path(temp) / "spec.json"
            p.write_text('{"arms":[],"arms":[]}')
            with self.assertRaises(ValueError):
                audit.exact_json(p)


if __name__ == "__main__":
    unittest.main()
