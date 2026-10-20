"""Validate the non-authoritative, source-bounded scheduled research intake.

No network, source auto-promotion, canonical claim edits, or protected pins.
"""
from __future__ import annotations

import json
import re
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "research" / "scheduled-task-reconciliation"
EXPECTED_TASKS = {
    "Project FAR Research Brief",
    "FAR Research Watch",
    "Project FAR Competitive Brief",
    "FAR Saturation Watch",
}
# Source identities and trust categories are contractual, not any-HTTPS links.
EXPECTED_SOURCES = {
    "SR-001": ("https://arxiv.org/abs/2610.04888", "author_report"),
    "SR-002": ("https://arxiv.org/abs/2610.05355", "author_report"),
    "SR-003": ("https://arxiv.org/abs/2610.07459", "author_report"),
    "SR-004": ("https://arxiv.org/abs/2610.12788", "author_report"),
    "SR-005": ("https://arxiv.org/abs/2610.20457", "author_report"),
    "SR-006": ("https://arxiv.org/abs/2610.20328", "author_report"),
    "SR-007": ("https://arxiv.org/abs/2610.21046", "author_report"),
    "SR-008": ("https://arxiv.org/abs/2610.21063", "author_report"),
    "SR-009": ("https://fact.engineering/benchmarks", "vendor_benchmark_self_report"),
    "SR-010": ("https://github.com/minerval-ai/minerval", "public_repository_documentation"),
    "SR-011": ("https://github.com/Ikey168/Noesis", "public_repository_documentation"),
}
REQUIRED_ENTRY_FIELDS = {
    "id", "title", "primary_url", "publication_or_event_date", "checked_on",
    "evidence_class", "topic", "source_reported_observation", "inference_limit",
    "single_falsification_or_comparison_test", "v05_classification",
    "architecture_change_required", "repository_disposition",
}


class ScheduledIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((FOLDER / "intake-2026-10-20.json").read_text(encoding="utf-8"))
        cls.readme = (FOLDER / "README.md").read_text(encoding="utf-8")

    def test_intake_is_unpromoted_with_explicit_coverage_limits(self):
        data = self.data
        self.assertEqual(data["schema_version"], "1.0")
        self.assertEqual(data["status"], "RESEARCH_INTAKE_UNREVIEWED_NO_PROMOTION")
        self.assertEqual(data["generated_date"], "2026-10-20")
        self.assertIn("No complete per-run task output archive", data["source_scope"])
        self.assertTrue(data["coverage_limits"])
        self.assertTrue(any("missed runs" in line for line in data["coverage_limits"]))
        self.assertTrue(any("architectur" in line.lower() for line in data["coverage_limits"]))
        lines = self.readme.splitlines()
        self.assertEqual(lines[0], "# Scheduled FAR research streams — bounded reconciliation (2026-10-20)")
        self.assertEqual(lines[2], "**Status: Research intake, non-authoritative. No scientific acceptance, v0.5 amendment, FAR-CORE/FARA/EFR status change, or commercial-performance determination.**")
        self.assertIn("no complete per-run task output archive", self.readme.lower())
        self.assertIn("research/living/README.md", self.readme)

    def test_stream_inventory_is_complete_but_not_mislabelled_as_run_archive(self):
        streams = self.data["task_streams"]
        self.assertEqual({t["name"] for t in streams}, EXPECTED_TASKS)
        self.assertEqual(len(streams), len(EXPECTED_TASKS))
        for stream in streams:
            self.assertIs(stream["results_exhaustive"], False)
            stamp = stream["last_run_metadata_utc"]
            self.assertTrue(stamp.endswith("Z"))
            parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            self.assertEqual(parsed.tzinfo, timezone.utc)
            self.assertEqual(parsed.date().isoformat(), self.data["generated_date"])

    def test_each_source_has_primary_link_explicit_limit_and_falsifier(self):
        entries = self.data["entries"]
        self.assertEqual(len(entries), len(EXPECTED_SOURCES))
        self.assertEqual({e["id"] for e in entries}, set(EXPECTED_SOURCES))
        self.assertEqual(len({e["id"] for e in entries}), len(entries))
        self.assertEqual(len({e["primary_url"] for e in entries}), len(entries))
        for e in entries:
            with self.subTest(source=e["id"]):
                self.assertEqual(set(e), REQUIRED_ENTRY_FIELDS)
                self.assertRegex(e["id"], r"^SR-\d{3}$")
                self.assertEqual(urlparse(e["primary_url"]).scheme, "https")
                self.assertTrue(urlparse(e["primary_url"]).hostname)
                self.assertEqual((e["primary_url"], e["evidence_class"]), EXPECTED_SOURCES[e["id"]])
                self.assertIs(e["architecture_change_required"], False)
                self.assertEqual(e["v05_classification"], "REPRESENTABLE_WITH_EXISTING_INTERFACE")
                self.assertEqual(e["repository_disposition"], "RESEARCH_LEAD_UNPROMOTED")
                self.assertGreater(len(e["source_reported_observation"]), 25)
                self.assertGreater(len(e["inference_limit"]), 25)
                self.assertGreater(len(e["single_falsification_or_comparison_test"]), 25)
                self.assertIn(e["id"], self.readme)
                self.assertIn(e["primary_url"], self.readme)
                self.assertEqual(e["checked_on"], self.data["generated_date"])
                if e["publication_or_event_date"] is not None:
                    self.assertLessEqual(
                        date.fromisoformat(e["publication_or_event_date"]),
                        date.fromisoformat(e["checked_on"]),
                    )

    def test_vendor_claims_are_not_promoted_to_independent_replication(self):
        vendor = [e for e in self.data["entries"] if e["evidence_class"] == "vendor_benchmark_self_report"]
        self.assertEqual([e["id"] for e in vendor], ["SR-009"])
        self.assertIn("self", vendor[0]["inference_limit"].lower())
        self.assertIn("1,063", vendor[0]["source_reported_observation"])
        self.assertIn("subset denominator undisclosed", vendor[0]["source_reported_observation"])
        self.assertIn("1,063", self.readme)
        self.assertIn("denominator undisclosed", self.readme)
        self.assertIn("no new v0.5 capability class", self.readme.lower())


if __name__ == "__main__":
    unittest.main()
