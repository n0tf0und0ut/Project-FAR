"""Verify persisted AgentAlphaXiv source evidence; zero scientific adjudications."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research/external-validation/agent-alphaxiv-002/source-coverage-receipt.json"
SELECTION = ROOT / "research/external-validation/agent-alphaxiv-002/selection-receipt.json"
SCRIPT = ROOT / "tools/agent_alphaxiv_source_screen.py"
spec = importlib.util.spec_from_file_location("source_screen", SCRIPT)
screen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(screen)


class PersistedSourceEvidence(unittest.TestCase):
    def test_receipt_is_canonical_and_unchanged(self):
        receipt = json.loads(SOURCE.read_text(encoding="utf-8"))
        expected = receipt.pop("receipt_sha256")
        self.assertEqual(screen.digest(receipt), expected)
        self.assertEqual(expected, "5fecd596dacc52ba696789ad57294b5b0544670f1b777ea0effd6c300917a21c")

    def test_source_and_selection_are_exactly_joined(self):
        source = json.loads(SOURCE.read_text(encoding="utf-8"))
        selection = json.loads(SELECTION.read_text(encoding="utf-8"))
        self.assertEqual(source["selection_manifest_sha256"], selection["manifest_canonical_sha256"])
        self.assertEqual(source["source_revision"], selection["dataset_revision"])
        selected = {r["project_id"]: r for r in selection["selected"]}
        self.assertEqual(len(selected), 60)
        self.assertEqual(len(source["records"]), 60)
        for r in source["records"]:
            s = selected.pop(r["project_id"])
            self.assertEqual(r["selected_version_id"], s["latest_version_id"])
            self.assertEqual(r["selection_digest"], s["selection_digest"])
            self.assertTrue(r["latest_version_found"])
            self.assertEqual(r["scientific_eligibility"], "NOT_ADJUDICATED")
            self.assertFalse(r["pdf_bytes_independently_checked"])
            self.assertFalse(r["tar_bytes_independently_checked"])
        self.assertFalse(selected)

    def test_aggregate_counts_and_evidence_ceiling(self):
        x = json.loads(SOURCE.read_text(encoding="utf-8"))
        rows = x["records"]
        s = x["summary"]
        self.assertEqual(s["selected"], len(rows))
        self.assertEqual(s["paper_text_present"], sum(bool(r["source_text_present"]) for r in rows))
        self.assertEqual(s["pdf_paths_listed"], sum(bool(r["pdf_path_present_in_source_listing"]) for r in rows))
        self.assertEqual(s["tar_paths_listed"], sum(bool(r["tar_path_present_in_source_listing"]) for r in rows))
        self.assertEqual(s["latest_artifact_rows"], sum(r["latest_artifact_records"] for r in rows))
        self.assertEqual(s["marked_latest_release_members"], sum(r["latest_marked_in_release_tar"] for r in rows))
        self.assertEqual(s["marked_latest_unreleased_members"], sum(r["latest_marked_excluded_from_release"] for r in rows))
        self.assertEqual(s["native_claims_adjudicated"], 0)
        self.assertEqual(s["paired_far_checker_runs"], 0)

    def test_live_intake_digest_is_enforced_in_runtime(self):
        receipt = json.loads(SELECTION.read_text(encoding="utf-8"))
        self.assertEqual(len(screen.verify_selection_receipt_hash(receipt)), 60)
        receipt["selected"][0]["title"] += " unauthorized change"
        with self.assertRaisesRegex(ValueError, "canonical digest mismatch"):
            screen.verify_selection_receipt_hash(receipt)
        receipt = json.loads(SELECTION.read_text(encoding="utf-8"))
        receipt["selected"][0]["selection_digest"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "identity hash mismatch"):
            screen.verify_selection_receipt_hash(receipt)
        receipt = json.loads(SELECTION.read_text(encoding="utf-8"))
        receipt["manifest_json_file_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "serialized-source digest mismatch"):
            screen.verify_selection_receipt_hash(receipt)

    def test_mutant_record_breaks_sha256(self):
        x = json.loads(SOURCE.read_text(encoding="utf-8"))
        digest = x.pop("receipt_sha256")
        x["records"][0]["source_text_bytes"] += 1
        self.assertNotEqual(screen.digest(x), digest)


if __name__ == "__main__":
    unittest.main()
