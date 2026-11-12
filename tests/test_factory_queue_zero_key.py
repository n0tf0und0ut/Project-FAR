"""Adversarial queue-to-model-smoke contract tests; mocks DO NOT attest a real model run."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.factory_queue_zero_key import run
from tools.software_factory import Factory, FactoryError


BASE = "5253a45ac7f5bfbda1278cf3b8fbf4b9b22136f8"
TASK = "Reject non-integer retry bounds without consuming a valid failure lease."


def mock_manifest(raw):
    return json.loads(raw)


class QueueZeroKeyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repository"
        self.repo.mkdir()
        self.order_file = self.root / "order.json"
        self.task_file = self.root / "model.json"
        self.db = self.root / "queue.sqlite"
        self.order = {"schema": "far-software-factory/work-order/1", "id": "far-maint-003",
                      "repository": "n0tf0und0ut/Project-FAR", "base_sha": BASE,
                      "tasks": [{"id": "far-maint-003", "objective": TASK,
                                 "acceptance": ["Model attempts retain queue lease history"], "depends_on": []}]}
        self.task = {"schema": "far-factory-zero-key-smoke/1", "task_id": "FAR-MAINT-003",
                     "issue_number": 629, "base_sha": BASE, "source_git_blob": "3" * 40,
                     "allowed_path": "tools/software_factory.py", "task_text": TASK,
                     "test_module": "test_software_factory"}
        self._save()
        self.model_calls = 0

    def _save(self):
        self.order_file.write_text(json.dumps(self.order), encoding="utf8")
        self.task_file.write_text(json.dumps(self.task), encoding="utf8")

    def _invoke(self, repo, taskfile, output):
        self.model_calls += 1
        output.mkdir()
        (output / "receipt.json").write_text('{"verdict":"VISIBLE_TESTS_PASSED_NOT_INDEPENDENTLY_VERIFIED"}\n')
        (output / "candidate.patch").write_text("synthetic patch: not a live model outcome\n")
        return {"verdict": "VISIBLE_TESTS_PASSED_NOT_INDEPENDENTLY_VERIFIED"}

    def invoke(self, **kwargs):
        with patch("tools.factory_queue_zero_key.manifest", side_effect=mock_manifest):
            return run(self.db, self.order_file, self.repo, self.task_file,
                       self.root / ("out" + str(kwargs.get("index", 0))),
                       invoke=kwargs.get("worker", self._invoke))

    def test_successful_mock_proposal_never_advances_build(self):
        r = self.invoke()
        self.assertEqual(self.model_calls, 1)
        self.assertEqual(r["queue_outcome"], "queued")
        self.assertEqual(r["queue_snapshot"]["tasks"][0]["stage"], "build")
        self.assertEqual([x["event"] for x in r["queue_snapshot"]["tasks"][0]["history"]],
                         ["claimed", "failed"])
        self.assertNotIn("\"token\":", json.dumps(r))
        self.assertTrue((self.root / "out0" / "worker" / "candidate.patch").exists())

    def test_frozen_order_and_model_sha_mismatch_block_before_model(self):
        for i, change in enumerate(("base", "task", "objective", "repo")):
            original_order = json.loads(json.dumps(self.order))
            original_task = json.loads(json.dumps(self.task))
            if change == "base": self.task["base_sha"] = "0" * 40
            if change == "task": self.task["task_id"] = "FAR-MAINT-999"
            if change == "objective": self.order["tasks"][0]["objective"] = "Wrong objective"
            if change == "repo": self.order["repository"] = "wrong/other"
            self._save()
            with patch("tools.factory_queue_zero_key.manifest", side_effect=mock_manifest), \
                 patch.dict("os.environ", {"GITHUB_REPOSITORY": "n0tf0und0ut/Project-FAR"}):
                with self.subTest(change=change), self.assertRaises(FactoryError):
                    run(self.db, self.order_file, self.repo, self.task_file,
                        self.root / ("nooutput" + str(i)), invoke=self._invoke)
            self.assertFalse((self.root / ("nooutput" + str(i))).exists())
            self.order, self.task = original_order, original_task
        self.assertEqual(self.model_calls, 0)

    def test_worker_exception_is_recorded_without_raw_message(self):
        def bad(*args):
            raise RuntimeError("secret token and provider error")
        r = self.invoke(worker=bad)
        self.assertEqual(r["worker_verdict"], "WORKER_EXCEPTION")
        self.assertEqual(r["error_type"], "RuntimeError")
        self.assertEqual(r["queue_outcome"], "queued")
        self.assertNotIn("secret token", json.dumps(r))

    def test_bounded_model_retries_retain_each_failed_attempt(self):
        for i in range(3):
            r = self.invoke(index=i)
        self.assertEqual(self.model_calls, 3)
        self.assertEqual(r["queue_outcome"], "failed")
        self.assertEqual([x["event"] for x in r["queue_snapshot"]["tasks"][0]["history"]],
                         ["claimed", "failed"] * 3)
        with patch("tools.factory_queue_zero_key.manifest", side_effect=mock_manifest):
            with self.assertRaisesRegex(FactoryError, "no eligible build"):
                run(self.db, self.order_file, self.repo, self.task_file, self.root / "out3", invoke=self._invoke)
        self.assertEqual(self.model_calls, 3)

    def test_prevents_outputs_or_database_inside_checkout(self):
        with patch("tools.factory_queue_zero_key.manifest", side_effect=mock_manifest):
            with self.assertRaises(FactoryError):
                run(self.db, self.order_file, self.repo, self.task_file, self.repo / "output", invoke=self._invoke)
            with self.assertRaises(FactoryError):
                run(self.repo / "queue.sqlite", self.order_file, self.repo, self.task_file,
                    self.root / "outside", invoke=self._invoke)
        self.assertEqual(self.model_calls, 0)

    def test_no_false_completed_stage_on_negative_model_result(self):
        def rejected(repo, taskfile, out):
            out.mkdir()
            (out / "receipt.json").write_text('{"verdict":"BLOCKED_OR_MODEL_OUTPUT_INVALID"}\n')
            return {"verdict": "BLOCKED_OR_MODEL_OUTPUT_INVALID"}
        r = self.invoke(worker=rejected)
        self.assertEqual(r["worker_verdict"], "BLOCKED_OR_MODEL_OUTPUT_INVALID")
        self.assertEqual(r["queue_snapshot"]["tasks"][0]["state"], "queued")
        self.assertNotIn("completed", [x["event"] for x in r["queue_snapshot"]["tasks"][0]["history"]])


if __name__ == "__main__":
    unittest.main()