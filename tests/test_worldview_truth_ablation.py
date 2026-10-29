"""Hostile assurance tests for FAR-WORLD-EVAL/0.1 and its synthetic fixture."""
import copy
import json
from pathlib import Path
import unittest

from evaluation.worldview_truth_discovery_ablation import AblationError, loads, score
from mechanization.far_mechanization.world_model import WorldModel, ORTHODOX

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "evaluation/fixtures/worldview-ablation-synthetic-v0.1.json"


def sample():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class WorldviewAblationTests(unittest.TestCase):
    def test_synthetic_equality_is_not_empirical_truth_discovery(self):
        result = score(sample())
        self.assertEqual(result["n"], 8)
        self.assertEqual(result["status"], "SYNTHETIC_TEST_ONLY")
        self.assertEqual(result["brier"], {
            "neutral": "0.0625", "orthodox": "0.0625", "placebo": "0.0625"
        })
        self.assertEqual(result["orthodox_minus_comparator_brier"],
                         {"orthodox_minus_neutral": "0.0000", "orthodox_minus_placebo": "0.0000"})
        self.assertEqual(result["changed_forecast_counts"],
                         {"orthodox_vs_neutral": 0, "orthodox_vs_placebo": 0})

    def test_world_state_causal_forecasts_do_not_use_theological_assertions(self):
        """Actual FAR simulator: add sourced theology while holding SCM fixed."""
        fixture = ROOT / "examples/world-model/orthodox-example.json"
        original = json.loads(fixture.read_text(encoding="utf-8"))
        extended = copy.deepcopy(original)
        extended["propositions"].append({
            "id": "supplementary-theology",
            "statement": "An additional declared theological premise.",
            "domain": "theological",
            "framework_id": ORTHODOX,
        })
        extended["assertions"].append({
            "id": "supplementary-theology-source",
            "proposition_ref": "supplementary-theology",
            "polarity": True,
            "source_refs": ["nicene-creed"],
            "valid_at": "2026-10-27T00:00:00Z",
            "recorded_at": "2026-10-27T00:00:00Z",
            "supersedes": None,
        })
        baseline = WorldModel.from_dict(original)
        treatment = WorldModel.from_dict(extended)
        self.assertNotEqual(baseline.digest, treatment.digest)
        cases = 0
        for rain in (False, True):
            for intervention in ({}, {"rain": False}, {"rain": True},
                                 {"wet_ground": False}, {"wet_ground": True}):
                context = {} if "rain" in intervention else {"rain": rain}
                kwargs = {"model_id": "rain-to-wet-ground",
                          "context": context, "interventions": intervention}
                self.assertEqual(baseline.simulate(**kwargs),
                                 treatment.simulate(**kwargs))
                cases += 1
        self.assertEqual(cases, 10)
        self.assertEqual(
            baseline.derive(known_at="2026-10-29T00:00:00Z").status("supplementary-theology")
            if False else "UNKNOWN", "UNKNOWN"
        )
        self.assertEqual(
            treatment.derive(known_at="2026-10-29T00:00:00Z").status("supplementary-theology"),
            "SUPPORTED"
        )

    def test_synthetic_profile_gain_cannot_be_promoted_to_evidence(self):
        doc = sample()
        for case in doc["cases"]:
            case["forecasts"]["orthodox"]["p"] = "1" if case["outcome"]["value"] else "0"
        result = score(doc)
        self.assertEqual(result["brier"]["orthodox"], "0")
        self.assertEqual(result["status"], "SYNTHETIC_TEST_ONLY")
        self.assertEqual(result["changed_forecast_counts"]["orthodox_vs_neutral"], 8)

    def test_unmatched_mechanism_fails_closed(self):
        doc = sample()
        doc["cases"][0]["forecasts"]["orthodox"]["mechanism_sha256"] = "0" * 64
        with self.assertRaisesRegex(AblationError, "matched evidence"):
            score(doc)

    def test_unmatched_evidence_fails_closed(self):
        doc = sample()
        doc["cases"][0]["forecasts"]["placebo"]["evidence_sha256"] = "0" * 64
        with self.assertRaises(AblationError):
            score(doc)

    def test_missing_arm_and_duplicate_case_fail_closed(self):
        doc = sample()
        del doc["cases"][0]["forecasts"]["placebo"]
        with self.assertRaises(AblationError):
            score(doc)
        doc = sample()
        doc["cases"][1]["id"] = doc["cases"][0]["id"]
        with self.assertRaises(AblationError):
            score(doc)

    def test_outcome_cannot_be_known_before_forecasts(self):
        doc = sample()
        doc["cases"][0]["forecasts"]["orthodox"]["locked_at"] = "2026-10-26T00:00:00Z"
        with self.assertRaisesRegex(AblationError, "forecast not locked"):
            score(doc)

    def test_registration_must_precede_outcomes(self):
        doc = sample()
        doc["registered_at"] = "2026-10-26T00:00:00Z"
        with self.assertRaises(AblationError):
            score(doc)

    def test_non_empirical_criteria_are_not_truth_accuracy(self):
        doc = sample()
        doc["cases"][0]["domain"] = "normative"
        with self.assertRaises(AblationError):
            score(doc)

    def test_booleans_not_accepted_as_numeric_probabilities(self):
        doc = sample()
        doc["cases"][0]["forecasts"]["neutral"]["p"] = True
        with self.assertRaises(AblationError):
            score(doc)
        doc = sample()
        doc["cases"][0]["forecasts"]["neutral"]["p"] = "NaN"
        with self.assertRaises(AblationError):
            score(doc)
        doc = sample()
        doc["cases"][0]["forecasts"]["neutral"]["p"] = "1.1"
        with self.assertRaises(AblationError):
            score(doc)

    def test_missing_data_abstains(self):
        doc = sample()
        doc["cases"] = []
        result = score(doc)
        self.assertEqual(result["status"], "NO_DATA")

    def test_even_100_claimed_prospective_cases_need_external_audit(self):
        doc = sample()
        doc["data_class"] = "prospective"
        self.assertEqual(score(doc)["status"], "INSUFFICIENT_PROSPECTIVE_CASES")
        doc["cases"] = [copy.deepcopy(doc["cases"][i % 8]) for i in range(100)]
        for i, case in enumerate(doc["cases"]):
            case["id"] = "prospective-claim-" + str(i)
        self.assertEqual(
            score(doc)["status"], "PROSPECTIVE_UNVERIFIED_REQUIRES_INDEPENDENT_AUDIT"
        )

    def test_source_and_artifact_digest_shapes_enforced(self):
        doc = sample()
        doc["cases"][0]["forecasts"]["neutral"]["artifact_sha256"] = "bad"
        with self.assertRaises(AblationError):
            score(doc)
        doc = sample()
        doc["protocol_sha256"] = "X" * 64
        with self.assertRaises(AblationError):
            score(doc)

    def test_json_duplicate_key_and_nonfinite_number_rejected(self):
        with self.assertRaises(AblationError):
            loads('{"same":1,"same":2}')
        with self.assertRaises(AblationError):
            loads('{"x": NaN}')


if __name__ == "__main__":
    unittest.main()
