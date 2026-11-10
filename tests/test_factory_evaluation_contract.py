"""Adversarial tests for a preregistered factory self-evaluation declaration."""
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
SCRIPT = ROOT / "tools/factory_evaluation_contract.py"
FIXTURE = ROOT / "research/factory-evaluation/protocol-v1.json"
spec = importlib.util.spec_from_file_location("factory_evaluation_contract", SCRIPT)
contract = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(contract)


class FactoryEvaluationContractTests(unittest.TestCase):
    def setUp(self):
        self.doc = json.loads(FIXTURE.read_text())

    def reject(self, obj, message):
        with self.assertRaisesRegex(contract.ContractError, message):
            contract.validate(obj)

    def test_registered_protocol_validates_and_has_digest(self):
        doc, digest = contract.load(FIXTURE)
        self.assertEqual(doc["study_id"], "FAR-FACTORY-SELF-EVAL-001")
        self.assertEqual(len(digest), 64)

    def test_rejects_mutable_or_unknown_study_status(self):
        self.doc["status"] = "Accepted"
        self.reject(self.doc, "cannot claim execution")

    def test_rejects_extra_keys(self):
        self.doc["success_rate"] = 1
        self.reject(self.doc, "unexpected")

    def test_requires_full_source_sha(self):
        self.doc["registration_base_sha"] = "abc123"
        self.reject(self.doc, "unbound")

    def test_rejects_duplicate_arm(self):
        self.doc["arms"][1]["id"] = "control"
        self.reject(self.doc, "arms must be")

    def test_rejects_unrandomized_task_design(self):
        self.doc["sampling"]["design"] = "factory-only"
        self.reject(self.doc, "pilot design")

    def test_rejects_paired_design_that_confounds_protected_delivery(self):
        self.doc["sampling"]["design"] = "prospective-paired-pilot"
        self.reject(self.doc, "pilot design")

    def test_requires_per_task_base_pin_before_allocation(self):
        self.doc["controls"]["task_base_sha_pinned_before_allocation"] = False
        self.reject(self.doc, "task_base_sha_pinned_before_allocation")

    def test_requires_oracles_frozen_before_allocation(self):
        self.doc["controls"]["test_oracles_frozen_before_allocation"] = False
        self.reject(self.doc, "test_oracles_frozen_before_allocation")

    def test_requires_task_selection_not_posthoc_freeze(self):
        self.doc["sampling"]["tasks_frozen"] = True
        self.reject(self.doc, "tasks_frozen")

    def test_rejects_boolean_masquerading_as_task_count(self):
        self.doc["sampling"]["target_distinct_tasks"] = True
        self.reject(self.doc, "task target")

    def test_allocation_reference_fixed_vector_and_full_schedule(self):
        seed = "0123456789abcdef" * 4
        ids = [f"task-{i:02d}" for i in range(1, 9)]
        rows = contract.allocation_schedule(seed, ids)
        self.assertEqual(rows, [
            {"slot": 1, "arm": "control", "task_id": "task-06"},
            {"slot": 2, "arm": "factory", "task_id": "task-07"},
            {"slot": 3, "arm": "control", "task_id": "task-02"},
            {"slot": 4, "arm": "factory", "task_id": "task-08"},
            {"slot": 5, "arm": "control", "task_id": "task-04"},
            {"slot": 6, "arm": "factory", "task_id": "task-05"},
            {"slot": 7, "arm": "control", "task_id": "task-03"},
            {"slot": 8, "arm": "factory", "task_id": "task-01"},
        ])
        self.assertEqual(rows, contract.allocation_schedule(seed, list(reversed(ids))))

    def test_rejects_wrong_allocation_algorithm(self):
        self.doc["sampling"]["allocation_algorithm"] = "sha256-utf8-no-delimiter"
        self.reject(self.doc, "allocation algorithm")

    def test_rejects_wrong_execution_order_algorithm(self):
        self.doc["controls"]["execution_order_algorithm"] = "unbalanced"
        self.reject(self.doc, "execution order algorithm")

    def test_allocation_rejects_duplicate_tasks_and_ambiguous_ids(self):
        seed = "0123456789abcdef" * 4
        ids = [f"task-{i:02d}" for i in range(1, 9)]
        with self.assertRaisesRegex(contract.ContractError, "duplicate task ID"):
            contract.allocation_schedule(seed, ids[:-1] + ids[:1])
        with self.assertRaisesRegex(contract.ContractError, "canonical task ID"):
            contract.allocation_schedule(seed, ids[:-1] + ["task:08"])
        with self.assertRaisesRegex(contract.ContractError, "seed must"):
            contract.allocation_schedule("example-seed", ids)

    def test_documentation_reuses_registered_allocation_delimiter(self):
        text = (ROOT / "docs/maintenance/factory-self-evaluation.md").read_text()
        self.assertIn("SHA-256(UTF-8(seed + ':' + task_id))", text)
        self.assertIn("SHA-256(UTF-8(seed + ':start'))", text)

    def test_registered_algorithm_rejects_non_eight_task_cohorts(self):
        for size in (2, 7, 9, 40):
            with self.subTest(size=size):
                self.doc["sampling"]["target_distinct_tasks"] = size
                self.reject(self.doc, "task target")

    def test_validator_and_allocator_agree_on_cohort_size(self):
        seed = "0123456789abcdef" * 4
        for size in (7, 8, 9):
            with self.subTest(size=size):
                cohort = [f"task-{i:02d}" for i in range(size)]
                if size == 8:
                    self.assertEqual(len(contract.allocation_schedule(seed, cohort)), size)
                    self.doc["sampling"]["target_distinct_tasks"] = size
                    contract.validate(self.doc)
                else:
                    with self.assertRaisesRegex(contract.ContractError, "eight"):
                        contract.allocation_schedule(seed, cohort)
                    self.doc["sampling"]["target_distinct_tasks"] = size
                    self.reject(self.doc, "task target")

    def test_requires_independent_execution_manifest_before_tasks(self):
        self.doc["execution_manifest"]["required_before_task_execution"] = False
        self.reject(self.doc, "required_before_task_execution")

    def test_requires_both_implementation_revisions(self):
        self.doc["execution_manifest"]["required_fields"].remove("control_implementation_revision")
        self.reject(self.doc, "incomplete execution manifest")

    def test_rejects_unregistered_midtrial_implementation_changes(self):
        self.doc["execution_manifest"]["change_policy"] = "controllers can change whenever"
        self.reject(self.doc, "implementation freeze")

    def test_rejects_dropping_tampered_allocated_task(self):
        self.doc["sampling"]["post_allocation_violation_policy"] = "Remove altered tasks from eligibility"
        self.reject(self.doc, "denominator")

    def test_requires_balanced_interleaved_schedule(self):
        self.doc["controls"]["balanced_interleaved_schedule"] = "Run all control then all factory"
        self.reject(self.doc, "unbalanced")

    def test_requires_cross_arm_isolation(self):
        self.doc["controls"]["cross_arm_knowledge_isolation"] = False
        self.reject(self.doc, "cross_arm_knowledge_isolation")

    def test_requires_cross_arm_exposure_policy(self):
        self.doc["controls"]["cross_arm_exposure_policy"] = "Share control findings with factory"
        self.reject(self.doc, "information-isolation")

    def test_rejects_unbounded_execution(self):
        self.doc["controls"]["max_wall_minutes_per_arm_task"] = 0
        self.reject(self.doc, "wall time")

    def test_rejects_paid_experiments_not_authorized(self):
        self.doc["controls"]["max_paid_provider_usd_per_arm_task"] = 0.01
        self.reject(self.doc, "paid provider")

    def test_rejects_claimed_superiority_from_diagnostic_pilot(self):
        self.doc["decision"]["superiority_claim_allowed"] = True
        self.reject(self.doc, "superiority_claim_allowed")

    def test_requires_all_protected_check_contexts(self):
        self.doc["verification"]["required_check_contexts"].pop()
        self.reject(self.doc, "protected checks")

    def test_requires_worker_assertions_to_remain_untrusted(self):
        self.doc["verification"]["worker_declarations_are_untrusted"] = False
        self.reject(self.doc, "worker_declarations")

    def test_requires_missing_outcome_to_remain_unknown(self):
        self.doc["decision"]["missing_or_incomparable_evidence"] = "PASS"
        self.reject(self.doc, "missing evidence")

    def test_requires_full_evidence_receipt(self):
        self.doc["verification"]["required_receipt_fields"].remove("task_oracle_digest")
        self.reject(self.doc, "receipt schema")

    def test_rejects_duplicate_json_keys_even_when_value_agrees(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            original = FIXTURE.read_text()
            path.write_text(original.replace('"schema": ', '"schema": "noop", "schema": ', 1))
            with self.assertRaisesRegex(contract.ContractError, "duplicate JSON key"):
                contract.load(path)

    def test_detects_tampered_protocol_with_expected_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            modified = Path(directory) / "modified.json"
            modified.write_text(FIXTURE.read_text().replace("First eight eligible", "First nine eligible"))
            _, digest = contract.load(FIXTURE)
            run = subprocess.run([sys.executable, str(SCRIPT), str(modified), "--expected-sha256", digest], capture_output=True, text=True)
            self.assertEqual(run.returncode, 2)
            self.assertIn("digest mismatch", run.stderr)

    def test_cli_reports_structural_only_not_verified_success(self):
        run = subprocess.run([sys.executable, str(SCRIPT), str(FIXTURE)], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("structural only", run.stdout)
        self.assertNotIn("VERIFIED_IMPROVEMENT", run.stdout)


if __name__ == "__main__":
    unittest.main()
