"""Adversarial deterministic, source-blocking, power and promotion-gate tests."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import unittest

from evaluation.worldview_confirmatory import analyze, recommended_minimum
from evaluation.worldview_truth_discovery_ablation import AblationError

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "evaluation/fixtures/worldview-ablation-synthetic-v0.1.json"


def sample():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def clustered(doc, group_size=1):
    return {case["id"]: "source-" + str(i // group_size)
            for i, case in enumerate(doc["cases"])}


class ConfirmatoryTests(unittest.TestCase):
    def test_no_difference_yields_exact_zero_bound(self):
        doc = sample()
        result = analyze(doc, clustered(doc), bootstrap=512)
        self.assertEqual(result["status"], "SYNTHETIC_TEST_ONLY")
        self.assertEqual(set(result["paired_mean_brier_difference"].values()), {0.0})
        self.assertEqual(set(result["simultaneous_95pct_upper_bound"].values()), {0.0})
        self.assertFalse(result["statistical_candidate"])

    def test_perfect_oracle_synthetic_cannot_be_promoted(self):
        doc = sample()
        for case in doc["cases"]:
            case["forecasts"]["orthodox"]["p"] = "1" if case["outcome"]["value"] else "0"
        result = analyze(doc, clustered(doc), bootstrap=512, minimum_independent_clusters=2)
        self.assertFalse(result["statistical_candidate"])
        self.assertEqual(result["status"], "SYNTHETIC_TEST_ONLY")
        self.assertLess(result["paired_mean_brier_difference"]["neutral"], 0)
        self.assertLess(result["simultaneous_95pct_upper_bound"]["placebo"], 0)

    def test_claimed_prospective_oracle_only_candidate_not_verified(self):
        doc = sample()
        doc["data_class"] = "prospective"
        for case in doc["cases"]:
            case["forecasts"]["orthodox"]["p"] = "1" if case["outcome"]["value"] else "0"
        result = analyze(doc, clustered(doc), bootstrap=512,
                         minimum_independent_clusters=2)
        self.assertTrue(result["statistical_candidate"])
        self.assertIn("UNVERIFIED", result["status"])
        self.assertIn("UNVERIFIED", result["assurance"])

    def test_source_clusters_detect_pseudoreplication(self):
        doc = sample()
        doc["data_class"] = "prospective"
        for case in doc["cases"]:
            case["forecasts"]["orthodox"]["p"] = "1" if case["outcome"]["value"] else "0"
        result = analyze(doc, clustered(doc, group_size=8), bootstrap=512,
                         minimum_independent_clusters=2)
        self.assertEqual(result["independent_clusters_claimed"], 1)
        self.assertFalse(result["statistical_candidate"])

    def test_equal_effect_against_neutral_not_placebo_is_not_benefit(self):
        doc = sample()
        doc["data_class"] = "prospective"
        for case in doc["cases"]:
            right = "1" if case["outcome"]["value"] else "0"
            case["forecasts"]["orthodox"]["p"] = right
            case["forecasts"]["placebo"]["p"] = right
        result = analyze(doc, clustered(doc), bootstrap=512,
                         minimum_independent_clusters=2)
        self.assertFalse(result["statistical_candidate"])
        self.assertEqual(result["paired_mean_brier_difference"]["placebo"], 0)

    def test_bootstrap_is_deterministic(self):
        doc = sample()
        self.assertEqual(analyze(doc, clustered(doc), bootstrap=512),
                         analyze(doc, clustered(doc), bootstrap=512))

    def test_clustering_is_required_exhaustively(self):
        doc = sample()
        clusters = clustered(doc)
        clusters.pop(next(iter(clusters)))
        with self.assertRaises(AblationError):
            analyze(doc, clusters, bootstrap=512)
        clusters = clustered(doc)
        clusters[doc["cases"][0]["id"]] = ""
        with self.assertRaises(AblationError):
            analyze(doc, clusters, bootstrap=512)

    def test_invalid_parameters_rejected(self):
        doc = sample()
        for kwargs in ({"bootstrap": 32}, {"bootstrap": True},
                       {"bootstrap": 50000}, {"minimum_independent_clusters": 1},
                       {"effect_threshold": float("nan")},
                       {"effect_threshold": 0.0}):
            with self.subTest(kwargs=kwargs), self.assertRaises(AblationError):
                analyze(doc, clustered(doc), **kwargs)

    def test_power_minimum_exceeds_200_for_moderate_variance(self):
        self.assertGreater(recommended_minimum(paired_sd=0.2), 200)
        self.assertGreater(recommended_minimum(paired_sd=0.25),
                           recommended_minimum(paired_sd=0.15))
        self.assertGreater(recommended_minimum(delta=0.01),
                           recommended_minimum(delta=0.02))

    def test_invalid_power_inputs_rejected(self):
        for kw in ({"delta": 0}, {"paired_sd": float("nan")},
                   {"familywise_alpha": 1.5}, {"comparisons": True}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                recommended_minimum(**kw)

    def test_outcome_timestamp_sanity_inherited(self):
        doc = sample()
        doc["cases"][0]["forecasts"]["neutral"]["locked_at"] = "2026-11-01T00:00:00Z"
        with self.assertRaises(AblationError):
            analyze(doc, clustered(doc), bootstrap=512)


if __name__ == "__main__":
    unittest.main()
