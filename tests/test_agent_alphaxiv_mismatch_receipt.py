"""Replay executed AgentAlphaXiv mismatch triage against preserved byte receipts."""
import json
from pathlib import Path
import sys
import unittest
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from agent_alphaxiv_source_screen import digest

OLD = ROOT / "research/external-validation/agent-alphaxiv-002/archive-byte-receipt-v0.1.json"
TRIAGE = ROOT / "research/external-validation/agent-alphaxiv-002/mismatch-triage-receipt-v0.1.json"


class ReplayMismatchReceipt(unittest.TestCase):
    def test_full_digest_and_pinned_source_identity(self):
        r = json.loads(TRIAGE.read_text(encoding="utf-8"))
        declared = r.pop("receipt_sha256")
        self.assertEqual(declared, "eb7d54b6767d37550d2392d4db559555c2696aaccb00e9e144e7611c6caabcf3")
        self.assertEqual(digest(r), declared)
        self.assertEqual(r["original_byte_receipt_sha256"], "dd0375ea74c91ca65cc19eb6bf03ea3dea24c6ff338b90fbcba0c73c5911ad86")

    def test_second_pass_matches_all_original_archives(self):
        old = json.loads(OLD.read_text(encoding="utf-8"))
        new = json.loads(TRIAGE.read_text(encoding="utf-8"))
        self.assertEqual(len(old["records"]), len(new["records"]))
        for before, after in zip(old["records"], new["records"]):
            self.assertEqual(before["project_id"], after["project_id"])
            self.assertEqual(before["archive_sha256"], after["archive_sha256"])
            self.assertEqual(before["members_mismatched_inventory_hash"], len(after["mismatches"]))
        self.assertEqual(new["summary"]["archives_reverified_identical"], 60)

    def test_exact_category_and_size_aggregates(self):
        new = json.loads(TRIAGE.read_text(encoding="utf-8"))
        details = [d for row in new["records"] for d in row["mismatches"]]
        summary = new["summary"]
        self.assertEqual(len(details), 116)
        self.assertEqual(sum(d["size_changed"] for d in details), 100)
        self.assertEqual(dict(sorted(Counter(d["artifact_kind"] for d in details).items())),
                         summary["mismatches_by_artifact_kind"])
        self.assertEqual(sum(summary["mismatches_by_artifact_kind"].values()), 116)
        self.assertEqual(summary["scientific_errors_adjudicated"], 0)
        self.assertEqual(summary["publisher_redaction_causes_proven"], 0)
        self.assertTrue(all(len(d["logical_path_sha256"]) == 64 for d in details))

    def test_mutated_triage_member_fails_digest(self):
        value = json.loads(TRIAGE.read_text(encoding="utf-8"))
        old = value.pop("receipt_sha256")
        next(r for r in value["records"] if r["mismatches"])["mismatches"][0]["released_sha256"] = "0"*64
        self.assertNotEqual(digest(value), old)


if __name__ == "__main__":
    unittest.main()
