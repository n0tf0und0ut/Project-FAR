from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools/check_validation_protection.py"
SPEC = importlib.util.spec_from_file_location("check_validation_protection", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
PROTECTION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROTECTION)
GATE_APP_ID = 5073230


def compliant_readback() -> dict:
    actual = {
        "required_status_checks": {
            "strict": True,
            "contexts": ["merge-authority", "protected-repin-gate"],
            "checks": [
                {"context": "merge-authority", "app_id": 15368},
                {"context": "protected-repin-gate", "app_id": GATE_APP_ID},
            ],
        },
        "required_pull_request_reviews": {
            "dismiss_stale_reviews": True,
            "require_code_owner_reviews": False,
            "required_approving_review_count": 0,
            "require_last_push_approval": False,
        },
    }
    for field, enabled in {
        "enforce_admins": True, "required_conversation_resolution": True,
        "required_linear_history": False, "allow_force_pushes": False,
        "allow_deletions": False, "block_creations": False,
        "required_signatures": False, "lock_branch": False, "allow_fork_syncing": False,
    }.items():
        actual[field] = {"enabled": enabled}
    return actual


class CheckValidationProtectionTests(unittest.TestCase):
    def test_exact_policy_passes_readback(self) -> None:
        self.assertEqual(PROTECTION.protection_errors(compliant_readback(), GATE_APP_ID), [])

    def test_missing_merge_authority_fails(self) -> None:
        actual = compliant_readback()
        actual["required_status_checks"]["contexts"] = []
        self.assertTrue(PROTECTION.protection_errors(actual, GATE_APP_ID))

    def test_prospective_review_gate_is_detected_exactly(self) -> None:
        actual = compliant_readback()
        actual["required_status_checks"]["contexts"].append("pr-review-convergence-observation")
        actual["required_status_checks"]["checks"].append(
            {"context": "pr-review-convergence-observation", "app_id": 15368}
        )
        self.assertEqual(
            PROTECTION.protection_errors(
                actual, GATE_APP_ID, require_review_convergence=True), []
        )
        # Existing production contract must reject unapproved addition until cutover.
        self.assertTrue(PROTECTION.protection_errors(actual, GATE_APP_ID))

    def test_review_gate_target_rejects_absence(self) -> None:
        actual = compliant_readback()
        errors = PROTECTION.protection_errors(
            actual, GATE_APP_ID, require_review_convergence=True)
        self.assertTrue(any("pr-review-convergence-observation" in e for e in errors))

    def test_review_gate_target_rejects_spoofable_or_wrong_source(self) -> None:
        for wrong_app_id in (-1, None, GATE_APP_ID, 15369):
            with self.subTest(wrong_app_id=wrong_app_id):
                actual = compliant_readback()
                actual["required_status_checks"]["contexts"].append(
                    "pr-review-convergence-observation")
                actual["required_status_checks"]["checks"].append({
                    "context": "pr-review-convergence-observation",
                    "app_id": wrong_app_id,
                })
                self.assertTrue(PROTECTION.protection_errors(
                    actual, GATE_APP_ID, require_review_convergence=True))

    def test_review_gate_target_does_not_weaken_strict_or_app_gate(self) -> None:
        actual = compliant_readback()
        actual["required_status_checks"]["contexts"].append("pr-review-convergence-observation")
        actual["required_status_checks"]["checks"].append(
            {"context": "pr-review-convergence-observation", "app_id": 15368}
        )
        actual["required_status_checks"]["checks"][1]["app_id"] = 15368
        actual["enforce_admins"]["enabled"] = False
        errors = PROTECTION.protection_errors(
            actual, GATE_APP_ID, require_review_convergence=True)
        self.assertTrue(any("required checks" in e for e in errors))
        self.assertTrue(any("administrator" in e for e in errors))

    def test_review_gate_target_rejects_duplicate_or_extra_context(self) -> None:
        for extra in ("pr-review-convergence-observation", "forged-pass"):
            with self.subTest(extra=extra):
                actual = compliant_readback()
                actual["required_status_checks"]["contexts"] += [
                    "pr-review-convergence-observation", extra]
                actual["required_status_checks"]["checks"] += [
                    {"context": "pr-review-convergence-observation", "app_id": 15368},
                    {"context": extra, "app_id": 15368},
                ]
                self.assertTrue(PROTECTION.protection_errors(
                    actual, GATE_APP_ID, require_review_convergence=True))

    def test_non_strict_checks_and_admin_bypass_fail(self) -> None:
        actual = compliant_readback()
        actual["required_status_checks"]["strict"] = False
        actual["enforce_admins"]["enabled"] = False
        errors = PROTECTION.protection_errors(actual, GATE_APP_ID)
        self.assertTrue(any("strict" in error for error in errors))
        self.assertTrue(any("administrator" in error for error in errors))

    def test_force_push_or_deletion_fails(self) -> None:
        for field in ("allow_force_pushes", "allow_deletions"):
            with self.subTest(field=field):
                actual = copy.deepcopy(compliant_readback())
                actual[field]["enabled"] = True
                self.assertTrue(PROTECTION.protection_errors(actual, GATE_APP_ID))

    def test_dropping_the_app_bound_gate_fails(self) -> None:
        # The superseded configurator wrote exactly this: merge-authority alone.
        actual = compliant_readback()
        actual["required_status_checks"]["contexts"] = ["merge-authority"]
        actual["required_status_checks"]["checks"] = [{"context": "merge-authority", "app_id": 15368}]
        errors = PROTECTION.protection_errors(actual, GATE_APP_ID)
        self.assertTrue(any("protected-repin-gate" in error for error in errors), errors)

    def test_gate_bound_to_another_app_or_to_none_fails(self) -> None:
        for app_id in (15368, None, GATE_APP_ID + 1):
            with self.subTest(app_id=app_id):
                actual = compliant_readback()
                actual["required_status_checks"]["checks"][1]["app_id"] = app_id
                self.assertTrue(PROTECTION.protection_errors(actual, GATE_APP_ID))

    def test_superseded_configurator_makes_no_change_and_fails_closed(self) -> None:
        import subprocess
        import sys
        completed = subprocess.run([sys.executable, str(ROOT / "tools/configure_validation_protection.py"),
                                    "--repository", "x/y", "--branch", "main"],
                                   capture_output=True, text=True, env={}, check=False)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("superseded", completed.stderr)
        source = (ROOT / "tools/configure_validation_protection.py").read_text(encoding="utf-8")
        for forbidden in ("urllib", "http", "PUT", "FAR_GITHUB_ADMIN_TOKEN"):
            self.assertNotIn(forbidden, source.split('"""', 2)[2])


if __name__ == "__main__":
    unittest.main()
