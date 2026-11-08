"""Adversarial intake regressions; synthetic controls, never live forecasts."""
import io
import json
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation.prospective_forecast_runner import (
    OpenAICompatible, ProspectiveError, probability, run_round,
)
from evaluation.factual_investigation_runner import answer
from evaluation.worldview_truth_discovery_ablation import loads, AblationError
from tests.test_prospective_forecast_runner import packet, NOW, END
from tests.test_factual_investigation_runner import packet as factual_packet, answer_key


class WorldviewIntakeConvergenceTests(unittest.TestCase):
    def test_forecast_runner_preserves_both_established_cli_forms(self):
        root=Path(__file__).resolve().parents[1]
        for invocation in (["evaluation/prospective_forecast_runner.py"], ["-m","evaluation.prospective_forecast_runner"]):
            result=subprocess.run([sys.executable,*invocation,"--help"],cwd=root,text=True,capture_output=True,timeout=15)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn("--rehearsal",result.stdout)

    def test_duplicate_completion_keys_cannot_choose_a_scored_prediction(self):
        for raw in ('{"probability":0.1,"probability":0.9,"reasoning":"ambiguous"}',
                    '{"probability":0.5,"reasoning":"first","reasoning":"second"}'):
            with self.subTest(raw=raw), self.assertRaises(ProspectiveError):
                probability(raw)
        for field, values in (("status", '"SUPPORTED","status":"REFUTED"'),
                              ("cited_source_ids", '["s1"],"cited_source_ids":[]'),
                              ("rationale", '"first","rationale":"second"')):
            data={"status":"SUPPORTED","cited_source_ids":["s1"],"rationale":"given"}
            raw=json.dumps(data)
            raw=raw.replace(json.dumps(field)+": "+json.dumps(data[field]), json.dumps(field)+": "+values)
            with self.subTest(field=field), self.assertRaises(ProspectiveError):
                answer(raw,{"s1"})

    def test_strict_loader_rejects_nonfinite_numbers_and_non_utf8_strings_recursively(self):
        for raw in ('{"nested":[1e999]}', '{"nested":[NaN]}', '{"nested":["\\ud800"]}',
                    '['*12000+'0'+']'*12000):
            with self.subTest(raw_prefix=raw[:60],length=len(raw)), self.assertRaises(AblationError):
                loads(raw)

    def test_backend_envelope_rejects_duplicate_nested_completion_fields(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self,limit):
                return b'{"choices":[{"message":{"content":"first","content":"second"}}]}'
        backend=OpenAICompatible("http://127.0.0.1:11434/v1/chat/completions","mock")
        with patch("evaluation.prospective_forecast_runner.urlopen",return_value=Response()), self.assertRaises(ValueError):
            backend([])

    def test_invalid_dataset_horizons_refuse_before_any_inference(self):
        for horizons in ([None], ["2026-11-15", "2026-11-15"], [42], [{"date":"2026-11-15"}]):
            data=packet();data["questions"][1]["resolution_dates"]=horizons
            calls=[]
            with self.subTest(horizons=horizons), self.assertRaises(ProspectiveError):
                run_round(data,lambda messages:calls.append(messages),"mock",NOW,finished_at=END)
            self.assertEqual(calls,[])

    def test_all_excluded_questions_cannot_produce_complete_empty_run(self):
        data=packet();data["questions"]=data["questions"][:1]
        data["questions"][0]["id"]=["A","B"]
        with self.assertRaisesRegex(ProspectiveError,"eligible"):
            run_round(data,lambda _:None,"mock",NOW,finished_at=END)

    def test_forecast_and_factual_cli_reject_ambiguous_files_before_backend_creation(self):
        from evaluation.prospective_forecast_runner import main as forecast_main
        from evaluation.factual_investigation_runner import main as factual_main
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for command,data in ((forecast_main,packet()),(factual_main,factual_packet())):
                text=json.dumps(data)
                field="question_set" if command is forecast_main else "study_id"
                raw=text[:-1]+','+json.dumps(field)+':'+json.dumps(data[field])+'}'
                source=root/"input.json";source.write_text(raw)
                output=root/"out.json"
                with patch("evaluation.prospective_forecast_runner.OpenAICompatible") as backend, redirect_stderr(io.StringIO()):
                    self.assertEqual(command([str(source),str(output),"--model","mock"]),1)
                    backend.assert_not_called()
                self.assertFalse(output.exists())

    def test_scoring_export_and_confirmation_clis_refuse_ambiguous_files(self):
        from evaluation.forecast_resolution_join import main as join_main
        from evaluation.forecastbench_export import main as export_main
        from evaluation.worldview_confirmatory import main as confirm_main
        from evaluation.score_factual_investigation import main as factual_score_main
        from tests.test_forecast_resolution_join import forecasts, resolutions, REGISTERED, PROTOCOL
        from evaluation.factual_investigation_runner import investigate
        from tests.test_factual_investigation_runner import mocked
        forecast=forecasts()
        from evaluation.forecast_resolution_join import join_resolutions
        study,_=join_resolutions(forecast,resolutions(forecast),registered_at=REGISTERED,protocol_sha256=PROTOCOL)
        clusters={case["id"]:case["id"] for case in study["cases"]}
        factual=factual_packet()
        responses=investigate(factual,mocked,"mock",NOW)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            objects={"forecast":forecast,"resolution":resolutions(forecast),"packet":factual,
                     "responses":responses,"key":answer_key(),"study":study,"clusters":clusters}
            paths={}
            for name,data in objects.items():
                paths[name]=root/(name+".json");paths[name].write_text(json.dumps(data))
            variants=[
                (join_main,[str(paths["forecast"]),str(paths["resolution"]),str(root/"joined.json"),"--registered-at",REGISTERED,"--protocol-sha256",PROTOCOL],"resolution","version"),
                (export_main,[str(paths["forecast"]),str(root/"exports"),"--organization","test","--model-organization","test"],"forecast","status"),
                (factual_score_main,[str(paths["packet"]),str(paths["responses"]),str(paths["key"])],"key","data_class"),
                (confirm_main,[str(paths["study"]),str(paths["clusters"])],"clusters",next(iter(clusters))),
            ]
            for command,args,name,field in variants:
                raw=json.dumps(objects[name])
                paths[name].write_text(raw[:-1]+','+json.dumps(field)+':'+json.dumps(objects[name][field])+'}')
                with self.subTest(command=command.__module__),redirect_stderr(io.StringIO()),redirect_stdout(io.StringIO()):
                    self.assertEqual(command(args),1)
                paths[name].write_text(raw)


if __name__=="__main__":
    unittest.main()
