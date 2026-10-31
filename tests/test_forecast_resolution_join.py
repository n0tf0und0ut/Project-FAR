"""Integration tests for the real-format forecast -> external resolution -> scorer path."""
from __future__ import annotations

from datetime import datetime, timezone
import copy
import json
import unittest

from evaluation.prospective_forecast_runner import run_round
from evaluation.forecast_resolution_join import join_resolutions
from evaluation.worldview_truth_discovery_ablation import AblationError


NOW = datetime(2026, 11, 8, 10, tzinfo=timezone.utc)
DONE = datetime(2026, 11, 8, 10, 1, tzinfo=timezone.utc)
REGISTERED = "2026-11-07T00:00:00Z"
PROTOCOL = "f" * 64


def question_set():
    return {
        "forecast_due_date": "2026-11-08",
        "question_set": "2026-11-08-llm.json",
        "questions": [
            {"id": "M1", "source": "metaculus", "question": "Will the event occur?",
             "resolution_criteria": "Published after closing", "resolution_dates": "N/A"},
            {"id": "D1", "source": "fred", "question": "Will statistic exceed threshold?",
             "resolution_criteria": "Published statistic", "resolution_dates": ["2026-11-15"]}
        ]
    }


def forecasts():
    return run_round(question_set(), lambda _: '{"probability": 0.5, "reasoning": "mock"}',
                     "mock", NOW, finished_at=DONE)


def resolutions(forecast):
    return {
        "version": "FAR-WORLD-RESOLVE/0.1",
        "question_set_sha256": forecast["question_set_sha256"],
        "events": [
            {"source": "metaculus", "id": "M1", "resolution_date": None,
             "value": True, "observed_at": "2026-11-16T00:00:00Z",
             "source_uri": "urn:synthetic:market"},
            {"source": "fred", "id": "D1", "resolution_date": "2026-11-15",
             "value": False, "observed_at": "2026-11-16T00:00:00Z",
             "source_uri": "urn:synthetic:dataset"}
        ]
    }


class ResolutionJoinTests(unittest.TestCase):
    def test_complete_three_arm_forecasts_score_only_after_outcomes(self):
        f = forecasts()
        doc, score = join_resolutions(f, resolutions(f),
                                      registered_at=REGISTERED,
                                      protocol_sha256=PROTOCOL)
        self.assertEqual(len(doc["cases"]), 2)
        self.assertEqual(score["n"], 2)
        self.assertEqual(score["status"], "SYNTHETIC_TEST_ONLY")
        self.assertEqual(score["brier"]["neutral"], "0.25")
        self.assertEqual(score["brier"]["orthodox"], "0.25")
        self.assertEqual(score["brier"]["placebo"], "0.25")
        self.assertEqual(score["changed_forecast_counts"]["orthodox_vs_neutral"], 0)

    def test_future_events_can_be_pending(self):
        f = forecasts()
        o = resolutions(f)
        o["events"].pop()
        doc, result = join_resolutions(f, o, registered_at=REGISTERED,
                                       protocol_sha256=PROTOCOL)
        self.assertEqual(result["n"], 1)
        self.assertEqual(len(doc["cases"]), 1)

    def test_never_score_result_predating_forecast(self):
        f = forecasts()
        o = resolutions(f)
        o["events"][0]["observed_at"] = "2026-11-07T12:00:00Z"
        with self.assertRaises(AblationError):
            join_resolutions(f, o, registered_at=REGISTERED,
                             protocol_sha256=PROTOCOL)

    def test_question_snapshot_mismatch_and_unknown_result_rejected(self):
        f = forecasts()
        o = resolutions(f)
        o["question_set_sha256"] = "0" * 64
        with self.assertRaises(AblationError):
            join_resolutions(f, o, registered_at=REGISTERED, protocol_sha256=PROTOCOL)
        o = resolutions(f)
        o["events"][0]["id"] = "other"
        with self.assertRaises(AblationError):
            join_resolutions(f, o, registered_at=REGISTERED, protocol_sha256=PROTOCOL)

    def test_partial_and_rehearsal_forecasts_never_promoted(self):
        from evaluation.prospective_forecast_runner import run_round
        q = question_set()
        mock = lambda _: '{"probability": 0.5, "reasoning": "mock"}'
        for kw in ({"rehearsal": True}, {"limit": 1}):
            f = run_round(q, mock, "mock", NOW, finished_at=DONE, **kw)
            with self.assertRaises(AblationError):
                join_resolutions(f, resolutions(f),
                                 registered_at=REGISTERED, protocol_sha256=PROTOCOL)

    def test_tampered_arm_or_response_rejected(self):
        f = forecasts()
        o = resolutions(f)
        f["predictions"][0]["raw_response_sha256"] = "bad"
        with self.assertRaises(AblationError):
            join_resolutions(f, o, registered_at=REGISTERED, protocol_sha256=PROTOCOL)
        f = forecasts()
        f["predictions"].append(copy.deepcopy(f["predictions"][0]))
        with self.assertRaises(AblationError):
            join_resolutions(f, resolutions(f),
                             registered_at=REGISTERED, protocol_sha256=PROTOCOL)

    def test_data_class_prospective_is_still_unverified(self):
        f = forecasts()
        _, result = join_resolutions(f, resolutions(f), registered_at=REGISTERED,
                                     protocol_sha256=PROTOCOL, data_class="prospective")
        self.assertEqual(result["status"], "INSUFFICIENT_PROSPECTIVE_CASES")
        self.assertIn("NOT_THEOLOGICAL_OR_CAUSAL_PROOF", result["assurance"])

    def test_registration_must_precede_predictions(self):
        f = forecasts()
        with self.assertRaises(AblationError):
            join_resolutions(f, resolutions(f),
                             registered_at="2026-11-09T00:00:00Z",
                             protocol_sha256=PROTOCOL)


if __name__ == "__main__":
    unittest.main()
