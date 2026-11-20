"""Adversarial archive verification tests; no external code execution."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location("byte_audit", ROOT / "tools/agent_alphaxiv_byte_audit.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def artifact(name, data, *, released=True):
    return {"logical_path": name, "sha256": hashlib.sha256(data).hexdigest(),
            "byte_size": len(data), "in_release_tar": released, "kind": "code"}


def make_tar(path, members):
    with tarfile.open(path, mode="w") as f:
        for name, contents in members:
            info = tarfile.TarInfo(name)
            info.size = len(contents)
            f.addfile(info, io.BytesIO(contents))


class ByteAuditTest(unittest.TestCase):
    def test_exact_byte_match_and_separate_missingness(self):
        with tempfile.TemporaryDirectory() as work:
            p = Path(work) / "safe.tar"
            make_tar(p, [("paper/paper.pdf", b"pdf"), ("code/run.py", b"no execution")])
            expected = [artifact("paper/paper.pdf", b"pdf"),
                        artifact("code/run.py", b"no execution"),
                        artifact("data/raw.csv", b"absent")]
            result = audit.audit_tar(p, expected)
            self.assertEqual(result["regular_members"], 2)
            self.assertEqual(result["members_matched_inventory_hash"], 2)
            self.assertEqual(result["members_mismatched_inventory_hash"], 0)
            self.assertEqual(result["members_marked_included_but_missing"], 1)
            self.assertEqual(result["integrity_status"], "BYTE_INVENTORY_DISAGREEMENT_REQUIRES_ADJUDICATION")

    def test_changed_bytes_preserve_unknown_not_scientific_fault(self):
        with tempfile.TemporaryDirectory() as work:
            p = Path(work) / "redacted.tar"
            make_tar(p, [("code/main.py", b"redacted!")])
            r = audit.audit_tar(p, [artifact("code/main.py", b"original")])
            self.assertEqual(r["members_mismatched_inventory_hash"], 1)
            self.assertEqual(r["members_mismatched_inventory_bytes"], 1)
            self.assertEqual(r["integrity_status"], "BYTE_INVENTORY_DISAGREEMENT_REQUIRES_ADJUDICATION")

    def test_tar_path_traversal_is_rejected_without_extraction(self):
        with tempfile.TemporaryDirectory() as work:
            p = Path(work) / "unsafe.tar"
            make_tar(p, [("../outside.txt", b"bad")])
            with self.assertRaisesRegex(ValueError, "unsafe tar member"):
                audit.audit_tar(p, [])

    def test_duplicate_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as work:
            p = Path(work) / "double.tar"
            make_tar(p, [("same.txt", b"a"), ("same.txt", b"b")])
            with self.assertRaisesRegex(ValueError, "duplicate"):
                audit.audit_tar(p, [])

    def test_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as work:
            p = Path(work) / "link.tar"
            with tarfile.open(p, "w") as f:
                info = tarfile.TarInfo("escape")
                info.type = tarfile.SYMTYPE
                info.linkname = "../../elsewhere"
                f.addfile(info)
            with self.assertRaisesRegex(ValueError, "unsafe or oversized"):
                audit.audit_tar(p, [])

    def test_codex_review_reproducer_charges_failed_malformed_download(self):
        """Exact P2 reproducer: one malformed 9216-byte tar, 60 IDs, one 9216-byte budget."""
        with tempfile.TemporaryDirectory() as work:
            bad = Path(work) / "malformed.tar"
            bad.write_bytes(b"not-a-tar" * 1024)  # 9216 bytes, not parseable by tarfile
            self.assertEqual(bad.stat().st_size, 9216)
            selected = [{"project_id": f"p{i:02}", "latest_version_id": f"v{i:02}",
                         "selection_digest": f"k{i:02}", "screening_status": "UNSCREENED"}
                        for i in range(60)]
            receipt = {"manifest_canonical_sha256": audit.verify_selection.__globals__["MANIFEST"],
                       "dataset_revision": audit.REVISION, "sample_size": 60, "selected": selected}
            source = [{"project_id": f"p{i:02}", "selected_version_id": f"v{i:02}",
                       "source_text_sha256": "x" * 64} for i in range(60)]
            sizes = {f"artifacts/p{i:02}.tar": 9216 for i in range(60)}
            calls = []
            def download(name):
                calls.append(name)
                return bad
            outcome = audit.audit_archive_selection(receipt, source, [], sizes, download,
                                                   max_total_bytes=9216)
            self.assertEqual(len(calls), 1)
            self.assertEqual(outcome["summary"]["archive_download_errors"], 1)
            self.assertEqual(outcome["summary"]["archive_budget_or_size_skips"], 59)
            self.assertEqual(outcome["summary"]["archives_examined"], 0)
            self.assertEqual(outcome["summary"]["paired_far_checker_executions"], 0)

    def test_underreported_failed_archive_bytes_exhaust_remaining_budget(self):
        """An understated listing cannot permit subsequent downloads after a rejected tar."""
        with tempfile.TemporaryDirectory() as work:
            bad = Path(work) / "malformed.tar"
            bad.write_bytes(b"not-a-tar" * 1024)  # 9216 actual bytes
            selected = [{"project_id": f"p{i:02}", "latest_version_id": f"v{i:02}",
                         "selection_digest": f"k{i:02}", "screening_status": "UNSCREENED"}
                        for i in range(60)]
            receipt = {"manifest_canonical_sha256": audit.verify_selection.__globals__["MANIFEST"],
                       "dataset_revision": audit.REVISION, "sample_size": 60, "selected": selected}
            source = [{"project_id": f"p{i:02}", "selected_version_id": f"v{i:02}",
                       "source_text_sha256": "x" * 64} for i in range(60)]
            sizes = {f"artifacts/p{i:02}.tar": 4608 for i in range(60)}
            calls = []
            def download(name):
                calls.append(name)
                return bad
            outcome = audit.audit_archive_selection(receipt, source, [], sizes, download,
                                                   max_total_bytes=9216)
            self.assertEqual(len(calls), 1)
            self.assertEqual(outcome["summary"]["archive_download_errors"], 1)
            self.assertEqual(outcome["summary"]["archive_budget_or_size_skips"], 59)

    def test_60_row_budget_prevents_unbounded_download_and_preserves_scientific_unknown(self):
        with tempfile.TemporaryDirectory() as work:
            p = Path(work) / "a.tar"
            make_tar(p, [("sample.txt", b"valid")])
            selected = [{"project_id": f"p{i:02}", "latest_version_id": f"v{i:02}",
                         "selection_digest": f"k{i:02}", "screening_status": "UNSCREENED"}
                        for i in range(60)]
            receipt = {"manifest_canonical_sha256": audit.verify_selection.__globals__["MANIFEST"],
                       "dataset_revision": audit.REVISION, "sample_size": 60,
                       "selected": selected}
            source = [{"project_id": f"p{i:02}", "selected_version_id": f"v{i:02}",
                       "source_text_sha256": "x" * 64} for i in range(60)]
            arts = [{"project_id": "p00", "version_id": "v00", **artifact("sample.txt", b"valid")}]
            sizes = {f"artifacts/p{i:02}.tar": p.stat().st_size for i in range(60)}
            downloads = []
            def download(name):
                downloads.append(name)
                return p
            o = audit.audit_archive_selection(receipt, source, arts, sizes, download,
                                              max_total_bytes=p.stat().st_size)
            self.assertEqual(len(downloads), 1)
            self.assertEqual(o["summary"]["archives_examined"], 1)
            self.assertEqual(o["summary"]["archive_budget_or_size_skips"], 59)
            self.assertEqual(o["summary"]["independently_adjudicated_scientific_claims"], 0)
            self.assertEqual(o["summary"]["paired_far_checker_executions"], 0)


if __name__ == "__main__":
    unittest.main()
