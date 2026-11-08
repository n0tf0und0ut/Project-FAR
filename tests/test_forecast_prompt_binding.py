"""Local forecast attribution controls; no authenticated execution is claimed."""
from contextlib import redirect_stderr, redirect_stdout
import copy
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation.forecastbench_export import export_sets
from evaluation.forecast_resolution_join import join_resolutions
from evaluation.prospective_forecast_runner import (
    CONDITIONS, ProspectiveError, digest, parse_question_set, prompt, run_round,
)
from evaluation.worldview_truth_discovery_ablation import AblationError
from tests.test_forecast_resolution_join import (
    DONE, NOW, PROTOCOL, REGISTERED, question_set, resolutions,
)


def arm_sensitive(messages):
    unit = json.loads(messages[-1]["content"].split("\n", 1)[1])
    outcome = unit["source"] == "metaculus"
    orthodox = messages[0]["content"].endswith(CONDITIONS["orthodox"])
    probability = 0.9 if outcome == orthodox else 0.1
    return json.dumps({"probability": probability, "reasoning": "synthetic"})


def forecasts():
    return run_round(question_set(), arm_sensitive, "scripted", NOW, finished_at=DONE)


class ForecastPromptBindingTests(unittest.TestCase):
    def assert_rejected_by_both_consumers(self, run):
        with self.subTest(consumer="join"), self.assertRaises(AblationError):
            join_resolutions(run, resolutions(run), registered_at=REGISTERED,
                             protocol_sha256=PROTOCOL)
        with self.subTest(consumer="export"), self.assertRaises(ProspectiveError):
            export_sets(run, organization="FAR", model_organization="scripted")

    def test_4507161039_swapped_arms_cannot_change_attributed_scores_or_exports(self):
        run = forecasts()
        _, result = join_resolutions(run, resolutions(run), registered_at=REGISTERED,
                                     protocol_sha256=PROTOCOL)
        self.assertEqual(result["brier"], {"neutral": "0.81", "orthodox": "0.01",
                                          "placebo": "0.81"})
        exported = export_sets(run, organization="FAR", model_organization="scripted")
        self.assertEqual([row["forecast"] for row in exported["orthodox"]["forecasts"]],
                         [0.1, 0.9])
        changed = copy.deepcopy(run)
        for row in changed["predictions"]:
            row["arm"] = {"neutral": "orthodox", "orthodox": "neutral",
                          "placebo": "placebo"}[row["arm"]]
            self.assertEqual(hashlib.sha256(row["raw_response"].encode()).hexdigest(),
                             row["raw_response_sha256"])
        self.assert_rejected_by_both_consumers(changed)

    def test_snapshot_is_captured_before_backend_and_detached_from_input(self):
        questions = question_set()
        original = copy.deepcopy(questions)

        def mutating_backend(messages):
            questions["questions"][0]["question"] = "changed after prompt preparation"
            return arm_sensitive(messages)

        run = run_round(questions, mutating_backend, "scripted", NOW, finished_at=DONE)
        self.assertEqual(run.get("question_set_snapshot"), original)
        self.assertEqual(run["question_set_sha256"], digest(original))
        questions["questions"].clear()
        self.assertEqual(run["question_set_snapshot"], original)
        export_sets(run, organization="FAR", model_organization="scripted")

    def test_missing_malformed_or_recommitted_changed_snapshot_is_rejected(self):
        mutations = [
            lambda r: r.pop("question_set_snapshot", None),
            lambda r: r.update(question_set_snapshot=None),
            lambda r: r.update(question_set_snapshot=[]),
            lambda r: r.update(question_set_sha256="0" * 64),
            lambda r: r.update(record_contract="unknown-profile"),
            lambda r: r.pop("record_contract", None),
        ]
        for mutate in mutations:
            run = forecasts()
            mutate(run)
            with self.subTest(mutate=mutate):
                self.assert_rejected_by_both_consumers(run)
        for recommit in (False, True):
            run = forecasts()
            # Explicit setup also makes the regression meaningful on the old
            # producer, which never retained a snapshot and ignored this field.
            run.setdefault("question_set_snapshot", question_set())
            run["question_set_snapshot"]["questions"][0]["question"] = "Different question?"
            if recommit:
                run["question_set_sha256"] = digest(run["question_set_snapshot"])
            with self.subTest(recommit=recommit):
                self.assert_rejected_by_both_consumers(run)

    def test_each_row_binds_prompt_and_question_to_its_own_unit_and_arm(self):
        run = forecasts()
        units = parse_question_set(question_set())[1]
        for index, row in enumerate(run["predictions"]):
            unit = next(u for u in units if u["id"] == row["id"])
            other = next(u for u in units if u["id"] != row["id"])
            other_arm = next(a for a in CONDITIONS if a != row["arm"])
            mutations = [
                lambda r: r.pop("prompt_sha256", None),
                lambda r: r.update(prompt_sha256=None),
                lambda r: r.update(prompt_sha256="0" * 64),
                lambda r: r.update(prompt_sha256=digest(prompt(unit, other_arm))),
                lambda r: r.update(prompt_sha256=digest(prompt(other, r["arm"]))),
                lambda r: r.update(question_sha256=digest(other)),
                lambda r: r.update(question_sha256="0" * 64),
                lambda r: r.update(id="unknown-question"),
            ]
            for mutate in mutations:
                changed = copy.deepcopy(run)
                mutate(changed["predictions"][index])
                with self.subTest(index=index, mutate=mutate):
                    self.assert_rejected_by_both_consumers(changed)

    def test_counts_metadata_and_complete_snapshot_coverage_are_bound(self):
        for field, value in (("dataset", "different-llm.json"),
                             ("forecast_due_date", "2026-11-09"),
                             ("units_selected", True), ("units_total", True),
                             ("units_selected", 1), ("units_total", 3)):
            run = forecasts()
            run[field] = value
            with self.subTest(field=field, value=value):
                self.assert_rejected_by_both_consumers(run)
        run = forecasts()
        run["predictions"] = [row for row in run["predictions"] if row["source"] == "fred"]
        run["units_selected"] = run["units_total"] = 1
        # Even if every retained unit has all three arms and outcomes are
        # restricted to them, the committed source snapshot requires both units.
        self.assert_rejected_by_both_consumers(run)

    def test_valid_row_reordering_and_all_existing_cli_paths(self):
        from evaluation.prospective_forecast_runner import main as collect_main
        from evaluation.forecastbench_export import main as export_main
        from evaluation.forecast_resolution_join import main as join_main

        class Clock(datetime):
            @classmethod
            def now(cls, tz=None):
                return cls(2026, 11, 8, 10, 0, tzinfo=tz)

        run = forecasts()
        original = export_sets(run, organization="FAR", model_organization="scripted")
        run["predictions"].reverse()
        self.assertEqual(export_sets(run, organization="FAR", model_organization="scripted"),
                         original)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "questions.json"
            source.write_text(json.dumps(question_set()))
            output = root / "forecasts.json"
            with patch("evaluation.prospective_forecast_runner.OpenAICompatible",
                       return_value=arm_sensitive), \
                    patch("evaluation.prospective_forecast_runner.datetime", Clock), \
                    redirect_stdout(io.StringIO()):
                self.assertEqual(collect_main([str(source), str(output), "--model", "scripted"]), 0)
            collected = json.loads(output.read_text())
            outcomes = root / "resolutions.json"
            outcomes.write_text(json.dumps(resolutions(collected)))
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(export_main([str(output), str(root / "exports"),
                                              "--organization", "FAR", "--model-organization", "scripted"]), 0)
                self.assertEqual(join_main([str(output), str(outcomes), str(root / "scored.json"),
                                           "--registered-at", REGISTERED,
                                           "--protocol-sha256", PROTOCOL]), 0)
            self.assertEqual(len(list((root / "exports").glob("*.json"))), 3)
            self.assertTrue((root / "scored.json").exists())


if __name__ == "__main__":
    unittest.main()
