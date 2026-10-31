"""ForecastBench export contract tests; mock results never count as forecasts."""
from __future__ import annotations

from datetime import datetime, timezone
import copy
import unittest

from evaluation.forecastbench_export import export_sets
from evaluation.prospective_forecast_runner import ProspectiveError, run_round

def sample():
    questions = {"question_set": "2026-11-08-llm.json",
                 "forecast_due_date": "2026-11-08",
                 "questions": [
                    {"source": "metaculus", "id": "A", "question": "Question?",
                     "resolution_criteria": "Published outcome"},
                    {"source": "fred", "id": "B", "question": "Indicator?",
                     "resolution_criteria": "Published data",
                     "resolution_dates": ["2026-11-15"]}
                 ]}
    return run_round(questions, lambda _:'{"probability":0.5,"reasoning":"unknown"}',
                     "test-model", datetime(2026,11,8,12,tzinfo=timezone.utc),
                     finished_at=datetime(2026,11,8,12,1,tzinfo=timezone.utc))

class ExportTests(unittest.TestCase):
    def test_three_official_format_files(self):
        result = export_sets(sample(),organization="FAR",model_organization="TestProvider")
        self.assertEqual(set(result), {"neutral", "orthodox", "placebo"})
        for arm, val in result.items():
            self.assertEqual(set(val),
                             {"organization","model","model_organization",
                              "question_set","forecasts"})
            self.assertEqual(val["organization"],"FAR")
            self.assertEqual(len(val["forecasts"]), 2)
            self.assertIn(arm, val["model"])
            self.assertEqual({x["forecast"] for x in val["forecasts"]},{0.5})
            self.assertEqual(set(val["forecasts"][0]),
                             {"id","source","forecast","resolution_date","reasoning"})

    def test_partial_and_rehearsal_are_never_submittable(self):
        for bad in ("REHEARSAL_NOT_PROSPECTIVE", "PARTIAL_NOT_SUBMITTABLE"):
            d=sample()
            d["status"]=bad
            with self.assertRaises(ProspectiveError):
                export_sets(d,organization="FAR",model_organization="provider")

    def test_duplicate_arms_and_missing_units_fail_closed(self):
        doc=sample()
        doc["predictions"][0]=copy.deepcopy(doc["predictions"][1])
        with self.assertRaises(ProspectiveError):
            export_sets(doc,organization="FAR",model_organization="provider")
        doc=sample()
        doc["predictions"].pop()
        with self.assertRaises(ProspectiveError):
            export_sets(doc,organization="FAR",model_organization="provider")

    def test_unsafe_organization_names_and_bad_probability(self):
        for bad in ("", "../outside", "team/subfolder"):
            with self.assertRaises(ProspectiveError):
                export_sets(sample(),organization=bad,model_organization="provider")
        doc=sample()
        doc=sample()
        doc["predictions"][0]["source"] = "untrusted"
        with self.assertRaises(ProspectiveError):
            export_sets(doc,organization="FAR",model_organization="provider")
        doc=sample()
        doc["predictions"][0]["probability"] = float("nan")
        with self.assertRaises(ProspectiveError):
            export_sets(doc,organization="FAR",model_organization="provider")


if __name__=="__main__":
    unittest.main()
