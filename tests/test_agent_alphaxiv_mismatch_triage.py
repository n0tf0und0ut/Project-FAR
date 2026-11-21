"""Tests for posthoc mismatch attribution without scientific overclaim."""
import hashlib
import importlib.util
import io
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from agent_alphaxiv_byte_audit import audit_tar
spec = importlib.util.spec_from_file_location("triage", ROOT / "tools/agent_alphaxiv_mismatch_triage.py")
triage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(triage)


def archive(path, raw):
    with tarfile.open(path, "w") as tf:
        info = tarfile.TarInfo("paper/paper.pdf")
        info.size = len(raw)
        tf.addfile(info, io.BytesIO(raw))


def metadata(raw):
    return [{"logical_path": "paper/paper.pdf", "sha256": hashlib.sha256(raw).hexdigest(),
             "byte_size": len(raw), "in_release_tar": True, "kind": "paper",
             "content_type": "application/pdf"}]


class TriageTests(unittest.TestCase):
    def test_reclassify_exact_mismatch_without_asserting_cause(self):
        with tempfile.TemporaryDirectory() as work:
            path = Path(work) / "paper.tar"
            archive(path, b"redacted source")
            meta = metadata(b"original")
            original = audit_tar(path, meta)
            original["project_id"] = "test"
            data = triage.classify_mismatches(path, meta, original)
            self.assertEqual(len(data["mismatches"]), 1)
            row = data["mismatches"][0]
            self.assertEqual(row["artifact_kind"], "paper")
            self.assertEqual(row["artifact_content_type"], "application/pdf")
            self.assertEqual(row["extension"], ".pdf")
            self.assertTrue(row["size_changed"])
            self.assertNotIn("logical_path", row)
            self.assertEqual(len(row["logical_path_sha256"]), 64)

    def test_source_archive_byte_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as work:
            path = Path(work) / "paper.tar"
            archive(path, b"first")
            original = audit_tar(path, metadata(b"first"))
            original["project_id"] = "test"
            archive(path, b"second")
            with self.assertRaisesRegex(ValueError, "original archive bytes changed"):
                triage.classify_mismatches(path, metadata(b"first"), original)

    def test_summary_refuses_changed_denominator_and_reports_zero_proofs(self):
        rec = [{"project_id": f"s{i:02}", "mismatches": []} for i in range(60)]
        s = triage.summarize(rec, 0)
        self.assertEqual(s["archives_reverified_identical"], 60)
        self.assertEqual(s["scientific_errors_adjudicated"], 0)
        self.assertEqual(s["publisher_redaction_causes_proven"], 0)
        with self.assertRaisesRegex(ValueError, "mismatch total drift"):
            triage.summarize(rec, 1)
        with self.assertRaisesRegex(ValueError, "exact 60"):
            triage.summarize(rec[:-1], 0)


if __name__ == "__main__":
    unittest.main()
