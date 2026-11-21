"""Adversarial validation of the proposed FAR-REPLAN-001 declaration."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/replanning_evaluation_contract.py"
PROTOCOL = ROOT / "research/workflow-efficacy/replanning-protocol-v1.json"
spec = importlib.util.spec_from_file_location("replanning_evaluation_contract", SCRIPT)
contract = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(contract)


class ReplanningContractTests(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads(PROTOCOL.read_text(encoding="utf-8"))

    def reject(self, term):
        with self.assertRaisesRegex(contract.ContractError, term):
            contract.validate(self.doc)

    def test_protocol_valid_and_status_is_candidate_only(self):
        parsed, sha = contract.load(PROTOCOL)
        self.assertEqual(parsed["study_id"], "FAR-REPLAN-001")
        self.assertEqual(len(sha), 64)
        self.assertFalse(parsed["execution_manifest"]["implementations_frozen"])

    def test_rejects_result_injected_into_registration(self):
        self.doc["outcomes"] = [{"treatment": "passed"}]
        self.reject("protocol keys")

    def test_rejects_claimed_execution_or_promotion(self):
        self.doc["status"] = "Accepted"
        self.reject("status")

    def test_rejects_unpinned_repository_base(self):
        self.doc["registration_base_sha"] = "main"
        self.reject("exact Git SHA")

    def test_rejects_duplicate_arm_and_unmatched_design(self):
        self.doc["arms"][1]["id"] = "control"
        self.reject("arms")
        self.doc = json.loads(PROTOCOL.read_text())
        self.doc["sampling"]["design"] = "unmatched-control"
        self.reject("sampling.design")

    def test_rejects_boolean_count_and_unfrozen_census_claim(self):
        self.doc["sampling"]["distinct_task_count"] = True
        self.reject("distinct_task_count")
        self.doc = json.loads(PROTOCOL.read_text())
        self.doc["sampling"]["task_ids_frozen"] = True
        self.reject("task_ids_frozen")

    def test_rejects_broken_oracle_and_arm_separation(self):
        self.doc["controls"]["same_tools_permissions_oracle_and_runner"] = False
        self.reject("same_tools_permissions_oracle_and_runner")
        self.doc = json.loads(PROTOCOL.read_text())
        self.doc["controls"]["no_cross_arm_feedback_until_pair_terminal"] = False
        self.reject("no_cross_arm_feedback_until_pair_terminal")

    def test_rejects_unbounded_or_paid_execution(self):
        self.doc["controls"]["max_model_replanning_rounds"] = 0
        self.reject("max_model_replanning_rounds")
        self.doc = json.loads(PROTOCOL.read_text())
        self.doc["controls"]["max_paid_provider_usd_per_run"] = 12
        self.reject("max_paid_provider_usd_per_run")

    def test_rejects_fake_readiness_and_missing_reviewer(self):
        self.doc["execution_manifest"]["provider_verified"] = True
        self.reject("provider_verified")
        self.doc = json.loads(PROTOCOL.read_text())
        self.doc["execution_manifest"]["required_fields"].remove("independent_reviewer_identity")
        self.reject("execution_manifest.required_fields")

    def test_rejects_worker_assertion_as_verdict(self):
        self.doc["primary_metric"]["worker_claim_not_evidence"] = False
        self.reject("worker_claim_not_evidence")
        self.doc = json.loads(PROTOCOL.read_text())
        self.doc["receipt_fields"].remove("oracle_execution_receipt_digest")
        self.reject("receipt_fields")

    def test_rejects_no_safety_stop_and_superiority_overclaim(self):
        self.doc["decision"]["security_or_provenance_breach"] = "IGNORE"
        self.reject("decision.security")
        self.doc = json.loads(PROTOCOL.read_text())
        self.doc["decision"]["superiority_or_generalization_claim_allowed"] = True
        self.reject("decision.superiority")

    def test_allocation_is_deterministic_paired_and_permutation_invariant(self):
        seed = "0123456789abcdef" * 4
        tasks = [f"case-{i:02}" for i in range(12)]
        output = contract.assignment_schedule(seed, tasks)
        self.assertEqual(len(output), 24)
        self.assertEqual(output, contract.assignment_schedule(seed, list(reversed(tasks))))
        for j in range(0, len(output), 2):
            self.assertEqual(output[j]["task_id"], output[j + 1]["task_id"])
            self.assertEqual({output[j]["arm"], output[j + 1]["arm"]}, {"control", "replanning"})
            self.assertEqual(output[j]["slot"], j + 1)
        self.assertEqual(len({row["task_id"] for row in output}), 12)

    def test_allocation_fixed_reference_vector(self):
        # A public deterministic regression vector, never a real trial seed.
        seed = "0123456789abcdef" * 4
        tasks = [f"case-{i:02}" for i in range(12)]
        sequence = [(row["task_id"], row["arm"]) for row in contract.assignment_schedule(seed, tasks)]
        self.assertEqual(sequence, [
            ("case-06", "replanning"), ("case-06", "control"),
            ("case-08", "replanning"), ("case-08", "control"),
            ("case-11", "control"), ("case-11", "replanning"),
            ("case-03", "control"), ("case-03", "replanning"),
            ("case-00", "control"), ("case-00", "replanning"),
            ("case-09", "control"), ("case-09", "replanning"),
            ("case-04", "control"), ("case-04", "replanning"),
            ("case-05", "replanning"), ("case-05", "control"),
            ("case-01", "replanning"), ("case-01", "control"),
            ("case-02", "replanning"), ("case-02", "control"),
            ("case-07", "replanning"), ("case-07", "control"),
            ("case-10", "control"), ("case-10", "replanning"),
        ])

    def test_allocation_rejects_invalid_seed_tasks_and_duplicates(self):
        tasks = [f"case-{i:02}" for i in range(12)]
        seed = "0123456789abcdef" * 4
        with self.assertRaisesRegex(contract.ContractError, "seed must"):
            contract.assignment_schedule("A" * 64, tasks)
        with self.assertRaisesRegex(contract.ContractError, "twelve"):
            contract.assignment_schedule(seed, tasks[:-1])
        with self.assertRaisesRegex(contract.ContractError, "duplicate"):
            contract.assignment_schedule(seed, tasks[:-1] + tasks[:1])
        with self.assertRaisesRegex(contract.ContractError, "noncanonical"):
            contract.assignment_schedule(seed, tasks[:-1] + ["case:bad"])

    def test_duplicate_json_keys_and_nonfinite_values_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidate.json"
            raw = PROTOCOL.read_text()
            path.write_text(raw.replace('"study_id": "FAR-REPLAN-001",',
                                        '"study_id": "FAR-REPLAN-001", "study_id": "FAR-REPLAN-001",'))
            with self.assertRaisesRegex(contract.ContractError, "duplicate"):
                contract.load(path)
            path.write_text(raw.replace('"tasks_enrolled": 0', '"tasks_enrolled": NaN'))
            with self.assertRaisesRegex(contract.ContractError, "nonfinite"):
                contract.load(path)

    def test_expected_digest_mismatch_fails_closed(self):
        result = subprocess.run([sys.executable, str(SCRIPT), str(PROTOCOL),
                                 "--expected-sha256", "0" * 64], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("digest mismatch", result.stderr)

    def test_cli_explicitly_does_not_claim_execution(self):
        result = subprocess.run([sys.executable, str(SCRIPT), str(PROTOCOL)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("DECLARATION ONLY", result.stdout)
        self.assertIn("not-executed", result.stdout)


if __name__ == "__main__":
    unittest.main()
