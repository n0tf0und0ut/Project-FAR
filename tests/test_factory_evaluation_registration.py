"""Source-anchoring and adversarial checks for factory protocol registration."""
from __future__ import annotations

import base64
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

from tools import factory_evaluation_registration as registration

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "research/factory-evaluation/protocol-registration-v1.json"
SOURCE = ROOT / "research/factory-evaluation/protocol-v1.json"
SOURCE_SHA = "12b0b4c86b26da72b8f845ed65740baf092503ea"


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.reg = registration.validate_registration(registration.strict_json(RECORD.read_bytes()))
        self.source = SOURCE.read_bytes()
        self.root = "https://api.github.com/repos/n0tf0und0ut/Project-FAR/"
        self.sample = {
            "pulls/633": {"merged": True, "merge_commit_sha": SOURCE_SHA},
            "branches/main": {"protected": True, "commit": {"sha": SOURCE_SHA}},
            "compare/" + SOURCE_SHA + "..." + SOURCE_SHA: {
                "status": "identical", "behind_by": 0,
                "merge_base_commit": {"sha": SOURCE_SHA},
                "base_commit": {"sha": SOURCE_SHA},
            },
            "contents/research/factory-evaluation/protocol-v1.json?ref=" + SOURCE_SHA: {
                "type": "file", "sha": self.reg["protocol"]["git_blob_sha1"],
                "encoding": "base64", "size": len(self.source),
                "content": base64.b64encode(self.source).decode("ascii"),
            },
        }

    def fetch(self, url):
        self.assertTrue(url.startswith(self.root), url)
        return self.sample[url[len(self.root):]]

    def test_source_exact_byte_and_git_blob_id(self):
        registration.verify_bytes(self.reg, self.source)

    def test_live_source_ancestry_success(self):
        self.assertEqual(registration.verify_live(self.reg, self.fetch), SOURCE_SHA)

    def test_live_ancestry_with_newer_protected_main(self):
        newer = "c" * 40
        self.sample["branches/main"]["commit"]["sha"] = newer
        comparison = self.sample.pop("compare/" + SOURCE_SHA + "..." + SOURCE_SHA)
        comparison["status"] = "ahead"
        self.sample["compare/" + SOURCE_SHA + "..." + newer] = comparison
        self.assertEqual(registration.verify_live(self.reg, self.fetch), newer)

    def test_changed_source_bytes_fail_closed(self):
        with self.assertRaisesRegex(registration.RegistrationError, "SHA-256 mismatch"):
            registration.verify_bytes(self.reg, self.source + b"\n")

    def test_wrong_git_blob_fails_closed(self):
        self.reg["protocol"]["git_blob_sha1"] = "a" * 40
        with self.assertRaisesRegex(registration.RegistrationError, "blob SHA-1 mismatch"):
            registration.verify_bytes(self.reg, self.source)

    def test_bogus_protected_merge_is_not_trusted(self):
        self.sample["pulls/633"]["merged"] = False
        with self.assertRaisesRegex(registration.RegistrationError, "not observed merged"):
            registration.verify_live(self.reg, self.fetch)

    def test_crossed_merge_commit_is_rejected(self):
        self.sample["pulls/633"]["merge_commit_sha"] = "b" * 40
        with self.assertRaisesRegex(registration.RegistrationError, "not observed merged"):
            registration.verify_live(self.reg, self.fetch)

    def test_unprotected_current_branch_is_rejected(self):
        self.sample["branches/main"]["protected"] = False
        with self.assertRaisesRegex(registration.RegistrationError, "protected main"):
            registration.verify_live(self.reg, self.fetch)

    def test_rewritten_history_or_not_ancestor_is_rejected(self):
        self.sample["compare/" + SOURCE_SHA + "..." + SOURCE_SHA]["behind_by"] = 1
        with self.assertRaisesRegex(registration.RegistrationError, "not verified ancestor"):
            registration.verify_live(self.reg, self.fetch)

    def test_comparison_base_mismatch_is_rejected(self):
        self.sample["compare/" + SOURCE_SHA + "..." + SOURCE_SHA]["base_commit"]["sha"] = "b" * 40
        with self.assertRaisesRegex(registration.RegistrationError, "not verified ancestor"):
            registration.verify_live(self.reg, self.fetch)

    def test_comparison_pins_exact_captured_main_sha(self):
        newer = "c" * 40
        self.sample["branches/main"]["commit"]["sha"] = newer
        captured = []
        def spy(url):
            captured.append(url)
            if url.endswith("compare/" + SOURCE_SHA + "..." + newer):
                return {
                    "status": "ahead", "behind_by": 0,
                    "merge_base_commit": {"sha": SOURCE_SHA},
                    "base_commit": {"sha": SOURCE_SHA},
                }
            return self.fetch(url)
        self.assertEqual(registration.verify_live(self.reg, spy), newer)
        self.assertTrue(any(url.endswith("compare/" + SOURCE_SHA + "..." + newer) for url in captured))

    def test_lookalike_content_with_wrong_hash_is_rejected(self):
        key = "contents/research/factory-evaluation/protocol-v1.json?ref=" + SOURCE_SHA
        self.sample[key]["content"] = base64.b64encode(self.source + b" ").decode("ascii")
        self.sample[key]["size"] = len(self.source) + 1
        with self.assertRaisesRegex(registration.RegistrationError, "SHA-256 mismatch"):
            registration.verify_live(self.reg, self.fetch)

    def test_missing_or_malformed_remote_content_is_rejected(self):
        key = "contents/research/factory-evaluation/protocol-v1.json?ref=" + SOURCE_SHA
        self.sample[key]["content"] = "%%%"
        with self.assertRaisesRegex(registration.RegistrationError, "base64"):
            registration.verify_live(self.reg, self.fetch)

    def test_remote_size_mismatch_is_rejected(self):
        key = "contents/research/factory-evaluation/protocol-v1.json?ref=" + SOURCE_SHA
        self.sample[key]["size"] = len(self.source) + 1
        with self.assertRaisesRegex(registration.RegistrationError, "byte size"):
            registration.verify_live(self.reg, self.fetch)

    def test_rejects_fabricated_results_or_frozen_execution(self):
        for claim in self.reg["trial"]:
            with self.subTest(claim=claim):
                candidate = copy.deepcopy(self.reg)
                candidate["trial"][claim] = True
                with self.assertRaisesRegex(registration.RegistrationError, "must not claim"):
                    registration.validate_registration(candidate)

    def test_rejects_cross_study_registration(self):
        self.reg["study_id"] = "FAR-FACTORY-SELF-EVAL-002"
        with self.assertRaisesRegex(registration.RegistrationError, "identity/status"):
            registration.validate_registration(self.reg)

    def test_rejects_boolean_pr_number(self):
        self.reg["protocol"]["merged_pr"] = True
        with self.assertRaisesRegex(registration.RegistrationError, "protocol path"):
            registration.validate_registration(self.reg)

    def test_rejects_unexpected_fields(self):
        self.reg["verified_delivery_rate"] = 100
        with self.assertRaisesRegex(registration.RegistrationError, "registration fields"):
            registration.validate_registration(self.reg)

    def test_rejects_duplicate_json_and_nonfinite(self):
        with self.assertRaisesRegex(registration.RegistrationError, "duplicate JSON"):
            registration.strict_json(b'{"x":1,"x":2}')
        with self.assertRaisesRegex(registration.RegistrationError, "nonstandard JSON"):
            registration.strict_json(b'{"x":NaN}')

    def test_offline_cli_does_not_pretend_to_check_live_github(self):
        p = subprocess.run(
            [sys.executable, str(ROOT / "tools/factory_evaluation_registration.py"), str(RECORD), str(SOURCE)],
            cwd=ROOT, capture_output=True, text=True,
        )
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("external GitHub source and protected-main ancestry NOT VERIFIED", p.stdout)


if __name__ == "__main__":
    unittest.main()
