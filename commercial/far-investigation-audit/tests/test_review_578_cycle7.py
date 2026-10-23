"""Seventh-review controls for unambiguous, bounded package replay."""
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from engine import InvalidBundle, audit, canonical, digest
from independent_check import IndependentCheckError, check_report
from full_cli import write_package, verify_package
from workflow import investigate
from test_review_578 import bundle


class SeventhReviewRegressions(unittest.TestCase):
    def package(self):
        return investigate({"source": {"kind": "text", "text": "Every source makes a bounded claim."}})

    def test_writer_rejects_oversized_manifest_without_publishing(self):
        package = self.package()
        package["manifest"]["large_metadata"] = "x" * 6_000_000
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d) / "package"
            with self.assertRaisesRegex(InvalidBundle, "manifest.*size"):
                write_package(root, package)
            self.assertFalse(root.exists())
            self.assertEqual(list(pathlib.Path(d).iterdir()), [])

    def test_rehashed_duplicate_keys_are_rejected_in_every_json_artifact(self):
        for name in ("manifest.json", "input.json", "audit.json", "acquisition.json",
                     "proposal.json", "critical_questions.json"):
            with self.subTest(artifact=name), tempfile.TemporaryDirectory() as d:
                root = pathlib.Path(d) / "package"
                write_package(root, self.package())
                p = root / name
                raw = p.read_text()
                # Nested duplicates also matter in list-valued artifacts.
                at = raw.index("{")
                first_object, _ = json.JSONDecoder().raw_decode(raw[at:])
                key = next(iter(first_object))
                raw = raw[:at + 1] + json.dumps(key) + ':"attacker-first-value",' + raw[at + 1:]
                p.write_text(raw)
                if name != "manifest.json":
                    manifest_path = root / "manifest.json"
                    manifest = json.loads(manifest_path.read_bytes())
                    manifest["files_sha256"][name] = digest(p.read_bytes())
                    manifest_path.write_bytes(canonical(manifest))
                with self.assertRaisesRegex(InvalidBundle, "invalid.*JSON"):
                    verify_package(root)

    def test_timestamp_precision_is_never_silently_truncated(self):
        original = bundle()
        report = audit(original)
        altered = json.loads(json.dumps(original))
        source = altered["sources"][0]
        source["published_at"] = "2026-10-16T12:00:00.0000002Z"
        source["captured_at"] = "2026-10-16T12:00:00.0000001Z"
        source["publication_date_verified"] = True
        with self.assertRaises(InvalidBundle):
            audit(altered)
        report["input_sha256"] = digest(canonical(altered))
        report.pop("report_sha256", None)
        report["report_sha256"] = digest(canonical(report))
        with self.assertRaises(IndependentCheckError):
            check_report(altered, report)

    def test_untracked_entries_stop_enumeration_at_first_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d) / "package"
            write_package(root, self.package())
            (root / "untracked").touch()
            with patch.object(pathlib.Path, "iterdir", side_effect=AssertionError("unbounded directory listing")):
                with self.assertRaisesRegex(InvalidBundle, "untracked"):
                    verify_package(root)
