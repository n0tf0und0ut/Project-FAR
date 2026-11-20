"""Adversarial tests for AgentAlphaXiv source-availability intake (synthetic only)."""
import importlib.util
import json
from pathlib import Path
import unittest

SRC = Path(__file__).resolve().parents[1] / "tools" / "agent_alphaxiv_source_screen.py"
spec = importlib.util.spec_from_file_location("source_screen", SRC)
screen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(screen)


def fixture():
    selected = [{"project_id": f"p{i:02}", "latest_version_id": f"v{i:02}",
                 "selection_digest": f"d{i:02}", "screening_status": "UNSCREENED"}
                for i in range(60)]
    receipt = {"manifest_canonical_sha256": screen.MANIFEST,
               "dataset_revision": screen.REVISION, "sample_size": 60, "selected": selected}
    papers = [{"project_id": f"p{i:02}", "text": f"paper text {i}"} for i in range(60)]
    versions = [{"project_id": f"p{i:02}", "version_id": f"v{i:02}", "is_latest": True}
                for i in range(60)]
    artifacts = [{"project_id": f"p{i:02}", "version_id": f"v{i:02}",
                  "kind": "code", "sha256": "a" * 64, "byte_size": 40,
                  "in_release_tar": True} for i in range(60)]
    listing = {f"papers/p{i:02}.pdf" for i in range(60)}
    listing |= {f"artifacts/p{i:02}.tar" for i in range(60)}
    return receipt, papers, artifacts, versions, listing


class ScreenTest(unittest.TestCase):
    def test_full_source_presence_and_determinism(self):
        args = fixture()
        a = screen.audit_source(*args, strict_counts=False)
        b = screen.audit_source(*args, strict_counts=False)
        self.assertEqual(a, b)
        self.assertEqual(a["summary"]["selected"], 60)
        self.assertEqual(a["summary"]["paper_text_present"], 60)
        self.assertEqual(a["summary"]["pdf_paths_listed"], 60)
        self.assertEqual(a["summary"]["tar_paths_listed"], 60)
        self.assertEqual(a["summary"]["paired_far_checker_runs"], 0)
        self.assertEqual(a["records"][0]["scientific_eligibility"], "NOT_ADJUDICATED")
        digest = a.pop("receipt_sha256")
        self.assertEqual(screen.digest(a), digest)

    def test_missing_text_is_not_a_defect(self):
        r, p, a, v, listing = fixture()
        p.pop()
        listing.discard("artifacts/p59.tar")
        o = screen.audit_source(r, p, a, v, listing, strict_counts=False)
        self.assertEqual((o["summary"]["paper_text_present"], o["summary"]["tar_paths_listed"]), (59, 59))
        self.assertIsNone(o["records"][-1]["source_text_sha256"])
        self.assertEqual(o["records"][-1]["scientific_eligibility"], "NOT_ADJUDICATED")

    def test_version_mismatch_fails_closed(self):
        r, p, a, v, listing = fixture()
        v[0]["version_id"] = "unregistered"
        with self.assertRaisesRegex(ValueError, "latest-version"):
            screen.audit_source(r, p, a, v, listing, strict_counts=False)

    def test_duplicate_text_and_malformed_artifact_fail(self):
        r, p, a, v, listing = fixture()
        with self.assertRaisesRegex(ValueError, "identity violation"):
            screen.audit_source(r, p + [p[0]], a, v, listing, strict_counts=False)
        a[0]["sha256"] = "not a checksum"
        with self.assertRaisesRegex(ValueError, "sha256"):
            screen.audit_source(r, p, a, v, listing, strict_counts=False)

    def test_revised_source_or_modified_selection_rejected(self):
        r, p, a, v, listing = fixture()
        r["dataset_revision"] = "current"
        with self.assertRaisesRegex(ValueError, "frozen selection"):
            screen.audit_source(r, p, a, v, listing, strict_counts=False)
        r["dataset_revision"] = screen.REVISION
        r["selected"][0]["screening_status"] = "ELIGIBLE"
        with self.assertRaisesRegex(ValueError, "unadjudicated"):
            screen.audit_source(r, p, a, v, listing, strict_counts=False)

    def test_registered_counts_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "source count"):
            screen.audit_source(*fixture())

    def test_excluded_member_not_misreported_as_released(self):
        r, p, a, v, listing = fixture()
        a[0]["in_release_tar"] = False
        o = screen.audit_source(r, p, a, v, listing, strict_counts=False)
        self.assertEqual(o["summary"]["marked_latest_unreleased_members"], 1)
        self.assertEqual(o["summary"]["marked_latest_release_members"], 59)
        self.assertEqual(o["records"][0]["latest_marked_excluded_bytes"], 40)


if __name__ == "__main__":
    unittest.main()
