"""Canonical runner coverage for the isolated numeric-grounding research module.

Also checks that submitted source rows cannot stand in for original raw traces.
No new inference calls, causal comparison or general reliability claim.
"""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "research/numeric-grounding"
spec = importlib.util.spec_from_file_location("far_numeric_source_replay", SOURCE / "source_replay.py")
source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(source)
mg = source.mg


class OriginalTraceCorrespondenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = source.reconstruct_events()

    def test_frozen_original_traces_supply_all_72_eligible_outcomes(self):
        self.assertEqual(len(self.data["registered_slots"]), 72)
        self.assertEqual(len(self.data["observations"]), 72)
        self.assertEqual({x["outcome"] for x in self.data["observations"]}, {"success"})
        self.assertEqual(len({x["slot_id"] for x in self.data["observations"]}), 72)

    def test_guarded_report_requires_replay_and_retains_boundaries(self):
        result = source.grounded_report(asserted_value="100.0000")
        self.assertEqual(result["value"], "100.0000")
        self.assertEqual(result["groups"]["control"], {"success": 72, "registered": 72})
        self.assertEqual(result["source_correspondence"]["external_attestation"], "NOT_ESTABLISHED")
        self.assertEqual(result["source_correspondence"]["independent_ground_truth"], "NOT_ESTABLISHED")

    def test_fabricated_outcome_with_self_consistent_count_is_rejected(self):
        forged = copy.deepcopy(self.data)
        forged["observations"][0]["outcome"] = "failure"
        # The original guard would accept the arithmetically consistent forged table.
        self.assertEqual(mg.answer(source.metric_catalog(), forged,
                                   metric_id="v03_registered_success", arm="control")["value"], "98.6111")
        with self.assertRaises(mg.GroundingError) as ctx:
            source.verify_events(forged)
        self.assertEqual(ctx.exception.code, "SOURCE_CORRESPONDENCE_FAILURE")

    def test_fabricated_denominator_is_rejected(self):
        forged = copy.deepcopy(self.data)
        forged["observations"].pop()
        forged["registered_slots"].pop()
        with self.assertRaises(mg.GroundingError) as ctx:
            source.verify_events(forged)
        self.assertEqual(ctx.exception.code, "SOURCE_CORRESPONDENCE_FAILURE")

    def test_fabricated_source_digest_is_rejected(self):
        forged = copy.deepcopy(self.data)
        forged["sources"][0]["sha256"] = "f" * 64
        with self.assertRaises(mg.GroundingError) as ctx:
            source.verify_events(forged)
        self.assertEqual(ctx.exception.code, "SOURCE_CORRESPONDENCE_FAILURE")

    def test_wrong_claim_fails_closed(self):
        with self.assertRaises(mg.GroundingError) as ctx:
            source.grounded_report(asserted_value="99.0000")
        self.assertEqual(ctx.exception.code, "NUMERIC_CLAIM_MISMATCH")

    def test_source_archive_maintains_recorded_identity(self):
        self.assertEqual(self.data["sources"][0]["sha256"], source.ARCHIVE_SHA256)
        self.assertEqual(self.data["study_id"], "FAR-TOOL-AGENT-001-v03")


def load_tests(loader, tests, pattern):
    """Load research suite under the canonical test runner instead of omitting it."""
    spec = importlib.util.spec_from_file_location("far_original_metric_tests", SOURCE / "test_metric_grounding.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tests.addTests(loader.loadTestsFromModule(module))
    return tests
