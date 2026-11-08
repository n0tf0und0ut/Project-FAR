"""Mutation controls for the research metric-grounding sidecar (no model runs)."""
import copy
import json
import unittest
from pathlib import Path
from importlib.util import module_from_spec, spec_from_file_location

HERE = Path(__file__).resolve().parent
spec = spec_from_file_location("metric_grounding", HERE / "metric_grounding.py")
mg = module_from_spec(spec)
spec.loader.exec_module(mg)


def catalog():
    return {"format": mg.CATALOG_FORMAT, "status": "Research", "metrics": [
        {"id": "rate", "operator": "registered_success_rate", "unit": "percent",
         "formula": "success / registered", "definition": "Successful tasks divided by registered eligible tasks, including failures and abstentions.",
         "review_status": "UNREVIEWED_RESEARCH"},
        {"id": "delta", "operator": "paired_success_delta_pp", "unit": "percentage_points",
         "formula": "100 * (treatment_success / treatment_registered - control_success / control_registered)",
         "definition": "Paired treatment-minus-control registered success-rate difference.",
         "review_status": "UNREVIEWED_RESEARCH"},
    ]}


def events():
    slots, observations = [], []
    for arm, successful in (("control", 11), ("treatment", 10)):
        for i in range(30):
            sid = f"{arm}-{i:02d}"
            slots.append({"id": sid, "case_id": f"case-{i:02d}", "arm": arm})
            observations.append({"slot_id": sid,
                                 "outcome": "success" if i < successful else "failure",
                                 "source_id": "synthetic"})
    return {"format": mg.DATA_FORMAT, "study_id": "demonstration", "scope": "authored_fixture",
            "sources": [{"id": "synthetic", "uri": "file:authored-simulation",
                         "sha256": "0" * 64,
                         "assurance": "DECLARED_NOT_INDEPENDENTLY_VERIFIED"}],
            "registered_slots": slots, "observations": observations}


class MetricGroundingTests(unittest.TestCase):
    def setUp(self):
        self.c = catalog()
        self.e = events()

    def check(self, code, c=None, e=None, **params):
        with self.assertRaises(mg.GroundingError) as ctx:
            mg.answer(c if c is not None else self.c,
                      e if e is not None else self.e, metric_id=params.pop("metric_id", "delta"), **params)
        self.assertEqual(ctx.exception.code, code)

    def test_correct_registered_rates_and_paired_difference(self):
        c = mg.answer(self.c, self.e, metric_id="rate", arm="control")
        t = mg.answer(self.c, self.e, metric_id="rate", arm="treatment")
        d = mg.answer(self.c, self.e, metric_id="delta")
        self.assertEqual((c["value"], t["value"], d["value"]),
                         ("36.6667", "33.3333", "-3.3333"))
        self.assertEqual(d["exact_fraction"], {"numerator": -10, "denominator": 3})
        self.assertEqual(d["status"], "DERIVED_FROM_DECLARED_EVENTS")
        self.assertEqual(d["groups"]["treatment"]["registered"], 30)

    def test_wrong_answer_rejected(self):
        self.check("NUMERIC_CLAIM_MISMATCH", asserted_value="3.3333")
        self.check("NUMERIC_CLAIM_MISMATCH", asserted_value="-3.33")
        self.assertEqual(mg.answer(self.c, self.e, metric_id="delta", asserted_value="-3.3333")["value"], "-3.3333")

    def test_wrong_denominator_is_not_accepted(self):
        e = copy.deepcopy(self.e)
        e["observations"].pop()
        self.check("MISSING_OBSERVATION", e=e)

    def test_missing_cohort_pair(self):
        e = copy.deepcopy(self.e)
        e["registered_slots"][30]["case_id"] = "different"
        self.check("UNPAIRED_EXPOSURE", e=e)

    def test_unknown_outcome_not_failure(self):
        e = copy.deepcopy(self.e)
        e["observations"][0]["outcome"] = "unknown"
        self.check("UNKNOWN_OUTCOME", e=e)

    def test_abstention_counts_against_registered_exposure(self):
        e = copy.deepcopy(self.e)
        e["observations"][11]["outcome"] = "abstain"
        self.assertEqual(mg.answer(self.c, e, metric_id="delta")["value"], "-3.3333")

    def test_duplicate_slot_rejected(self):
        e = copy.deepcopy(self.e)
        e["registered_slots"][1]["id"] = e["registered_slots"][0]["id"]
        self.check("DUPLICATE_OR_INVALID_SLOT", e=e)

    def test_duplicate_observation_rejected(self):
        e = copy.deepcopy(self.e)
        e["observations"].append(copy.deepcopy(e["observations"][0]))
        self.check("INVALID_OBSERVATION", e=e)

    def test_unrecognized_metric_rejected(self):
        self.check("UNANSWERABLE_METRIC", metric_id="nonexistent")

    def test_metric_redefinition_rejected(self):
        c = copy.deepcopy(self.c)
        c["metrics"][0]["formula"] = "success / observed"
        self.check("METRIC_REDEFINITION", c=c)

    def test_false_certification_rejected(self):
        c = copy.deepcopy(self.c)
        c["metrics"][1]["review_status"] = "CERTIFIED"
        self.check("FALSE_CERTIFICATION", c=c)

    def test_unknown_source_rejected(self):
        e = copy.deepcopy(self.e)
        e["observations"][1]["source_id"] = "not-registered"
        self.check("INVALID_OBSERVATION", e=e)

    def test_wrong_scope_and_numeric_scale_rejected(self):
        self.check("WRONG_QUERY_SCOPE", arm="control")
        self.check("SCALE", digits=12)

    def test_malformed_type_rejected_without_crashing(self):
        e = copy.deepcopy(self.e)
        e["registered_slots"][0]["arm"] = []
        self.check("DUPLICATE_OR_INVALID_SLOT", e=e)
        c = copy.deepcopy(self.c)
        c["metrics"][1]["operator"] = []
        self.check("UNKNOWN_OPERATOR", c=c)
        e = copy.deepcopy(self.e)
        e["sources"][0]["sha256"] = 5
        self.check("BAD_SOURCE", e=e)

    def test_duplicate_json_keys_and_binary_float_rejected(self):
        with self.assertRaises(mg.GroundingError) as cm:
            mg.strict_load(b'{"a":1,"a":2}')
        self.assertEqual(cm.exception.code, "DUPLICATE_JSON_KEY")
        with self.assertRaises(mg.GroundingError) as cm:
            mg.strict_load(b'{"x":0.5}')
        self.assertEqual(cm.exception.code, "FLOAT_FORBIDDEN")

    def test_input_hashes_change_on_mutation(self):
        c = json.dumps(self.c, sort_keys=True).encode()
        e = json.dumps(self.e, sort_keys=True).encode()
        initial = mg.evaluate(c, e, metric_id="delta")
        altered = copy.deepcopy(self.e)
        altered["observations"][0]["outcome"] = "failure"
        second = mg.evaluate(c, json.dumps(altered, sort_keys=True).encode(), metric_id="delta")
        self.assertNotEqual(initial["events_sha256"], second["events_sha256"])
        self.assertNotEqual(initial["value"], second["value"])


if __name__ == "__main__":
    unittest.main()
