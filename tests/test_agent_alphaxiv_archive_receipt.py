"""Tests for the pinned v0.1 all-study archive byte observation."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from agent_alphaxiv_source_screen import digest

SOURCE = ROOT / "research/external-validation/agent-alphaxiv-002/source-coverage-receipt.json"
ARCHIVES = ROOT / "research/external-validation/agent-alphaxiv-002/archive-byte-receipt-v0.1.json"


class ByteReceiptTests(unittest.TestCase):
    def test_receipt_hash_exact_recompute(self):
        r = json.loads(ARCHIVES.read_text(encoding="utf-8"))
        expected = r.pop("receipt_sha256")
        self.assertEqual(digest(r), expected)
        self.assertEqual(expected, "dd0375ea74c91ca65cc19eb6bf03ea3dea24c6ff338b90fbcba0c73c5911ad86")

    def test_selection_matches_source_and_all_60_completed(self):
        r = json.loads(ARCHIVES.read_text(encoding="utf-8"))
        source = json.loads(SOURCE.read_text(encoding="utf-8"))
        self.assertEqual(r["source_coverage_sha256"], source["receipt_sha256"])
        self.assertEqual(r["selection_manifest_sha256"], source["selection_manifest_sha256"])
        self.assertEqual([s["project_id"] for s in r["records"]],
                         [s["project_id"] for s in source["records"]])
        self.assertEqual(len(r["records"]), 60)
        self.assertTrue(all(x["status"] == "ARCHIVE_BYTES_EXAMINED" for x in r["records"]))
        self.assertEqual(r["summary"]["archive_bytes_examined"],
                         sum(x["archive_bytes"] for x in r["records"]))

    def test_recount_all_hashes_and_missingness(self):
        r = json.loads(ARCHIVES.read_text(encoding="utf-8"))
        rows, summary = r["records"], r["summary"]
        for aggregate, field in [
            ("members_matching_inventory_sha256", "members_matched_inventory_hash"),
            ("members_mismatching_inventory_sha256", "members_mismatched_inventory_hash"),
            ("declared_included_members_missing", "members_marked_included_but_missing"),
            ("unmatched_archive_members", "members_unindexed")]:
            self.assertEqual(summary[aggregate], sum(x[field] for x in rows))
        self.assertEqual(summary["archives_examined"], 60)
        self.assertEqual(summary["members_matching_inventory_sha256"], 966)
        self.assertEqual(summary["members_mismatching_inventory_sha256"], 116)
        self.assertEqual(summary["declared_included_members_missing"], 0)
        self.assertEqual(summary["unmatched_archive_members"], 0)
        self.assertEqual(summary["independently_adjudicated_scientific_claims"], 0)

    def test_mutated_one_member_digest_is_detected(self):
        r = json.loads(ARCHIVES.read_text(encoding="utf-8"))
        recorded = r.pop("receipt_sha256")
        r["records"][0]["archive_sha256"] = "0" * 64
        self.assertNotEqual(digest(r), recorded)


if __name__ == "__main__":
    unittest.main()
