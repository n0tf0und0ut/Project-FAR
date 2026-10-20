"""Validate the non-authoritative, source-bounded scheduled research intake.

No network, source auto-promotion, canonical claim edits, or protected pins.
"""
from __future__ import annotations

import copy
import json
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
README_STATUS = (
    "**Status: Research intake, non-authoritative. No scientific acceptance, "
    "v0.5 amendment, FAR-CORE/FARA/EFR status change, or commercial-performance determination.**"
)
NONPROMOTION_LIMIT = (
    "No automatic change to FAR-CORE, FARA, EFR, v0.5, project status, accepted "
    "evidence, feature scope, or benchmark results."
)
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
        self.assert_nonpromotion(self.data, self.readme)

    def assert_nonpromotion(self, data, readme):
        self.assertEqual(data["schema_version"], "1.0")
        self.assertEqual(data["status"], "RESEARCH_INTAKE_UNREVIEWED_NO_PROMOTION")
        self.assertEqual(data["generated_date"], "2026-10-20")
        self.assertIn("No complete per-run task output archive", data["source_scope"])
        self.assertTrue(data["coverage_limits"])
        self.assertTrue(any("missed runs" in line for line in data["coverage_limits"]))
        self.assertIn(NONPROMOTION_LIMIT, data["coverage_limits"])
        self.assertTrue(any("provisional v0.5" in line.lower() and
                            "not a proof of saturation" in line.lower()
                            for line in data["coverage_limits"]))
        self.assertEqual(readme.splitlines()[0],
            "# Scheduled FAR research streams — bounded reconciliation (2026-10-20)")
        self.assertIn("complete historical run outputs, frozen raw pages, notifications, "
                      "and all prior manual catch-up files were not accessible together",
                      readme.lower())
        status_lines = [line for line in readme.splitlines() if line.startswith("**Status:")]
        self.assertEqual(status_lines, [README_STATUS])
        self.assertIn("research/living/README.md", readme)

    def test_stream_inventory_is_complete_but_not_mislabelled_as_run_archive(self):
        self.assert_stream_inventory(self.data)

    def assert_stream_inventory(self, data):
        streams = data["task_streams"]
        self.assertEqual({t["name"] for t in streams}, EXPECTED_TASKS)
        self.assertEqual(len(streams), len(EXPECTED_TASKS))
        for stream in streams:
            self.assertIs(stream["results_exhaustive"], False)
            stamp = stream["last_run_metadata_utc"]
            self.assertRegex(stamp, r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
            try:
                parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            except ValueError as exc:
                self.fail(f"Invalid scheduler timestamp: {stamp}: {exc}")
            self.assertEqual(parsed.utcoffset(), timezone.utc.utcoffset(parsed))
            self.assertEqual(parsed.date(), date.fromisoformat(data["generated_date"]))

    def test_each_source_has_primary_link_explicit_limit_and_falsifier(self):
        self.assert_sources(self.data, self.readme)

    def assert_sources(self, data, readme):
        entries = data["entries"]
        self.assertEqual(len(entries), len(EXPECTED_SOURCES))
        self.assertEqual(len({e["id"] for e in entries}), len(entries))
        self.assertEqual(len({e["primary_url"] for e in entries}), len(entries))
        self.assertEqual({e["id"] for e in entries}, set(EXPECTED_SOURCES))
        for e in entries:
            # Do not use subTest here: mutation regressions must observe the
            # failed assertion rather than having unittest consume it.
            self.assertEqual(set(e), REQUIRED_ENTRY_FIELDS)
            self.assertRegex(e["id"], r"^SR-\d{3}$")
            self.assertEqual(urlparse(e["primary_url"]).scheme, "https")
            self.assertTrue(urlparse(e["primary_url"]).hostname)
            self.assertEqual((e["primary_url"], e["evidence_class"]),
                             EXPECTED_SOURCES[e["id"]])
            self.assertIs(e["architecture_change_required"], False)
            self.assertEqual(e["v05_classification"], "REPRESENTABLE_WITH_EXISTING_INTERFACE")
            self.assertEqual(e["repository_disposition"], "RESEARCH_LEAD_UNPROMOTED")
            self.assertGreater(len(e["source_reported_observation"]), 25)
            self.assertGreater(len(e["inference_limit"]), 25)
            self.assertGreater(len(e["single_falsification_or_comparison_test"]), 25)
            self.assertIn(e["id"], readme)
            self.assertIn(e["primary_url"], readme)
            self.assertEqual(e["checked_on"], data["generated_date"])
            if e["publication_or_event_date"] is not None:
                self.assertLessEqual(
                    date.fromisoformat(e["publication_or_event_date"]),
                    date.fromisoformat(e["checked_on"]),
                )
    def test_vendor_claims_are_not_promoted_to_independent_replication(self):
        vendor = [e for e in self.data["entries"] if e["evidence_class"] == "vendor_benchmark_self_report"]
        self.assertEqual([e["id"] for e in vendor], ["SR-009"])
        self.assertIn("self", vendor[0]["inference_limit"].lower())
        self.assertIn("no new v0.5 capability class", self.readme.lower())

    def test_mutations_cannot_promote_readme_or_remove_coverage_boundary(self):
        promoted = self.readme.replace(README_STATUS,
            "**Status: Accepted authoritative evidence and scientific promotion.**")
        with self.assertRaises(AssertionError):
            self.assert_nonpromotion(self.data, promoted)
        changed = copy.deepcopy(self.data)
        changed["coverage_limits"].remove(NONPROMOTION_LIMIT)
        with self.assertRaises(AssertionError):
            self.assert_nonpromotion(changed, self.readme)

    def test_mutations_cannot_substitute_or_misclassify_sources(self):
        for field, value in (("primary_url", "https://example.com/unrelated"),
                             ("evidence_class", "author_report")):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.data)
                entry = next(e for e in changed["entries"] if e["id"] == "SR-010")
                readme = self.readme.replace(entry["primary_url"], value) if field == "primary_url" else self.readme
                entry[field] = value
                with self.assertRaises(AssertionError):
                    self.assert_sources(changed, readme)

    def test_mutations_cannot_pass_invalid_scheduler_datetimes(self):
        for stamp in ("2026-10-20T99:99:99Z", "2026-02-30T12:00:00Z",
                      "2026-10-19T12:00:00Z", "2026-10-20T12:00:00+01:00"):
            with self.subTest(timestamp=stamp):
                changed = copy.deepcopy(self.data)
                changed["task_streams"][0]["last_run_metadata_utc"] = stamp
                with self.assertRaises(AssertionError):
                    self.assert_stream_inventory(changed)

    def test_vendor_subset_denominators_remain_explicit(self):
        vendor = next(e for e in self.data["entries"] if e["id"] == "SR-009")
        self.assertIn("96.6% on 1,063", vendor["source_reported_observation"])
        self.assertIn("exact subset denominator undisclosed", vendor["source_reported_observation"])
        self.assertIn("**1,063**", self.readme)
        self.assertIn("**exact subset denominator undisclosed**", self.readme)


if __name__ == "__main__":
    unittest.main()
