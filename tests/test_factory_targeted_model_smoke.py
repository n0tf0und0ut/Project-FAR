"""Controls for constrained model-output parser and source-exact one-line repair."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.factory_zero_key_smoke import SmokeError
from tools.factory_targeted_model_smoke import (
    candidate_source, guard_window, local_model_line, run,
)


SOURCE = '''class Factory:
    def fail(self, order_id, task_id, token, reason, now=None, max_attempts=3):
        if not isinstance(reason, str) or not reason.strip() or max_attempts < 1:
            raise ValueError("failure reason and retry bound required")
        return {"state": "queued"}
'''
GOOD_LINE = ("        if not isinstance(reason, str) or not reason.strip() "
             "or type(max_attempts) is not int or max_attempts < 1:")


class Response:
    def __init__(self, body):
        self.body = body
    def read(self, size):
        return self.body[:size]
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False


class TargetedModelTests(unittest.TestCase):
    def test_ast_locates_existing_guard_exactly(self):
        n, old, snippet = guard_window(SOURCE)
        self.assertEqual(n, 3)
        self.assertIn("max_attempts < 1", old)
        self.assertTrue(snippet.startswith("    def fail"))

    def test_single_line_mutation_preserves_all_other_bytes(self):
        result = candidate_source(SOURCE, GOOD_LINE)
        self.assertEqual(result.count("\n"), SOURCE.count("\n"))
        self.assertEqual(result.splitlines()[2], GOOD_LINE)
        self.assertEqual(result.splitlines()[:2] + result.splitlines()[3:],
                         SOURCE.splitlines()[:2] + SOURCE.splitlines()[3:])

    def test_rejects_non_line_replacement_and_multiline_attack(self):
        for repl in (None, [], {}, "", "if True:", "        if True:\n        evil()",
                     "        import os", "        if True:\x00", "        if +++:"):
            with self.subTest(repl=repr(repl)), self.assertRaises(SmokeError):
                candidate_source(SOURCE, repl)

    def test_cannot_replace_another_function_or_multiline_guard(self):
        with self.assertRaises(SmokeError):
            guard_window(SOURCE.replace("class Factory:", "class Other:"))
        multi = SOURCE.replace("or max_attempts < 1:", "or (\n            max_attempts < 1):")
        with self.assertRaises(SmokeError):
            guard_window(multi)

    def test_model_json_transport_and_response_identity(self):
        body = json.dumps({"model": "qwen2.5-coder:1.5b", "done": True,
            "eval_count": 33, "prompt_eval_count": 123,
            "message": {"content": json.dumps({"line": GOOD_LINE})}}).encode()
        def response(req, timeout):
            request = json.loads(req.data)
            self.assertEqual(request["format"], "json")
            self.assertEqual(request["options"]["temperature"], 0)
            self.assertEqual(request["options"]["num_predict"], 180)
            self.assertEqual(timeout, 150)
            self.assertIn('qwen2.5-coder:1.5b', request["model"])
            return Response(body)
        with patch("tools.factory_targeted_model_smoke.urllib.request.urlopen", side_effect=response):
            line, raw, metrics = local_model_line("repair retry bound")
        self.assertEqual(line, GOOD_LINE)
        self.assertEqual(raw, body)
        self.assertEqual(metrics["output_tokens"], 33)

    def test_model_invalid_identity_or_output_never_passes(self):
        scenarios = [
            {"model":"other", "done":True, "eval_count":2, "prompt_eval_count":1,
             "message":{"content":json.dumps({"line":GOOD_LINE})}},
            {"model":"qwen2.5-coder:1.5b", "done":True, "eval_count":2,
             "prompt_eval_count":1,"message":{"content":json.dumps({"line":GOOD_LINE,"other":1})}},
            {"model":"qwen2.5-coder:1.5b", "done":False, "eval_count":2,
             "prompt_eval_count":1,"message":{"content":json.dumps({"line":GOOD_LINE})}},
        ]
        for case in scenarios:
            with self.subTest(model=case["model"], content=case["message"]["content"]):
                with patch("tools.factory_targeted_model_smoke.urllib.request.urlopen",
                           return_value=Response(json.dumps(case).encode())):
                    with self.assertRaises(SmokeError):
                        local_model_line("repair retry bound")

    def test_queued_proposal_never_claims_real_github_build(self):
        """Actual SQLite lease protocol; fake model is only a negative control."""
        from tools.factory_queue_zero_key import run as run_queue
        from tools.software_factory import Factory
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "repo"; repo.mkdir()
            task_text = "Repair Factory.fail invalid retry bounds"
            task = {"schema":"far-factory-zero-key-smoke/1", "task_id":"FAR-MAINT-003",
                    "issue_number":629, "base_sha":"5253a45ac7f5bfbda1278cf3b8fbf4b9b22136f8",
                    "source_git_blob":"3217647b5ca09ed40ab79a849952aa29f7c033ab",
                    "allowed_path":"tools/software_factory.py", "task_text":task_text,
                    "test_module":"test_software_factory"}
            order = {"schema":"far-software-factory/work-order/1", "id":"far-maint-003",
                "repository":"n0tf0und0ut/Project-FAR", "base_sha":task["base_sha"],
                "tasks":[{"id":"far-maint-003", "objective":task_text,
                          "acceptance":["Produce a properly sourced change"], "depends_on":[]}]}
            tf, of = root / "model.json", root / "order.json"
            tf.write_text(json.dumps(task))
            of.write_text(json.dumps(order))
            def simulated_model(repo, taskfile, output):
                output.mkdir()
                (output / "receipt.json").write_text('{"verdict":"MODEL_PATCH_PASSED_VISIBLE_AND_FROZEN_TESTS_NOT_PR_DELIVERY"}')
                (output / "candidate.patch").write_bytes(b"fake untrusted source patch")
                return {"verdict":"MODEL_PATCH_PASSED_VISIBLE_AND_FROZEN_TESTS_NOT_PR_DELIVERY"}
            result = run_queue(root / "queue.db", of, repo, tf, root / "out", invoke=simulated_model)
            self.assertEqual(result["queue_outcome"], "queued")
            self.assertEqual(result["queue_snapshot"]["tasks"][0]["stage"], "build")
            self.assertEqual([x["event"] for x in result["queue_snapshot"]["tasks"][0]["history"]],
                             ["claimed", "failed"])

    def test_frozen_manifest_and_holdout_rejected_before_model(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "repo"; repo.mkdir()
            work = root / "task.json"; work.write_text('{"fake":true}')
            holdout = root / "holdout.py"; holdout.write_text("altered holdout")
            with patch("tools.factory_targeted_model_smoke.local_model_line") as model:
                with self.assertRaises(SmokeError):
                    run(repo, work, root / "out", holdout=holdout)
                self.assertFalse(model.called)
                self.assertFalse((root / "out").exists())


if __name__ == "__main__":
    unittest.main()
