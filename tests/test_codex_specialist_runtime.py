import json
import tempfile
import unittest
from pathlib import Path
from threading import Thread
from time import sleep
from unittest.mock import patch

from tools.codex_specialist_runtime import (
    NativeCodexMailbox,
    RESPONSE_SCHEMA,
    publish_once,
    run_native_codex,
)
from tools.subagent_orchestration import ContextArtifact, RunStatus, canonical_json, sha256_text


class NativeCodexRuntimeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.mailbox = NativeCodexMailbox(Path(temporary.name) / "run", timeout=2)

    def _respond(self, agent, task, prompt, *, native="worker-1", digest=None):
        request = {
            "schema": "far-native-codex-request/1", "agent_id": agent,
            "task_id": task, "prompt": prompt,
        }
        publish_once(self.mailbox.directory / f"{sha256_text(task)}.response.json", {
            "schema": RESPONSE_SCHEMA,
            "request_sha256": digest or sha256_text(canonical_json(request)),
            "native_agent_id": native,
            "report": "exact report\n",
        })

    def test_response_binding_and_agent_reuse(self):
        self._respond("a", "task-a", "prompt")
        self.assertEqual(self.mailbox.exchange("a", "prompt", "task-a"), "exact report\n")
        self._respond("b", "task-b", "prompt")
        with self.assertRaisesRegex(ValueError, "already used"):
            self.mailbox.exchange("b", "prompt", "task-b")
        self._respond("c", "task-c", "prompt", digest="0" * 64)
        with self.assertRaisesRegex(ValueError, "not bound"):
            self.mailbox.exchange("c", "prompt", "task-c")

    def test_timeout_preserves_request_and_does_not_create_report(self):
        self.mailbox.timeout = 0.01
        with self.assertRaises(TimeoutError):
            self.mailbox.exchange("a", "prompt", "task-a")
        self.assertEqual(len(list(self.mailbox.directory.glob("*.request.json"))), 1)
        self.assertFalse(list(self.mailbox.directory.glob("*.response.json")))

    def test_response_read_finishing_at_deadline_is_not_accepted(self):
        self._respond("a", "task-a", "prompt")
        with patch("tools.codex_specialist_runtime.time.monotonic",
                   side_effect=[10, 10.1, 12, 12]), self.assertRaises(TimeoutError):
            self.mailbox.exchange("a", "prompt", "task-a")
        self.assertIsNotNone(self.mailbox.receipts[0].response_sha256)
        self.assertIsNone(self.mailbox.receipts[0].native_agent_id)

    def test_publication_does_not_replace_evidence(self):
        path = self.mailbox.directory / "evidence.json"
        publish_once(path, {"original": True})
        with self.assertRaises(FileExistsError):
            publish_once(path, {"original": False})
        self.assertEqual(json.loads(path.read_bytes()), {"original": True})

    def test_all_fourteen_roles_route_through_mailbox(self):
        # This is a structural fixture, not evidence of native model execution.
        def controller():
            consumed = set()
            while len(consumed) < 14:
                for request_path in self.mailbox.directory.glob("*.request.json"):
                    if request_path in consumed:
                        continue
                    request_bytes = request_path.read_bytes()
                    request = json.loads(request_bytes)
                    task = json.loads(request["prompt"])["task"]
                    report = {
                        "contract": "far-subagent-report/1.0", "agent_id": request["agent_id"],
                        "task_id": request["task_id"], "input_sha256": task["input_sha256"],
                        "status": "completed", "findings": [], "limitations": [], "error": None,
                    }
                    publish_once(request_path.with_name(request_path.name.replace("request", "response")), {
                        "schema": RESPONSE_SCHEMA, "request_sha256": sha256_text(request_bytes.decode()),
                        "native_agent_id": f"fixture-{request['agent_id']}", "report": canonical_json(report),
                    })
                    consumed.add(request_path)
                sleep(0.01)

        worker = Thread(target=controller, daemon=True)
        worker.start()
        result = run_native_codex(Path.cwd(), self.mailbox, "Bounded routing fixture",
                                  (ContextArtifact.from_text("fixture", "Synthetic input."),))
        worker.join(timeout=1)
        self.assertEqual(result.status, RunStatus.COMPLETED)
        self.assertEqual(len(result.reports), 14)
        self.assertEqual(len(result.invocation_receipts), 14)
        self.assertEqual(len(self.mailbox.receipts), 14)
        for receipt in self.mailbox.receipts:
            stem = sha256_text(receipt.task_id)
            request = (self.mailbox.directory / f"{stem}.request.json").read_text()
            response = (self.mailbox.directory / f"{stem}.response.json").read_text()
            self.assertEqual(receipt.request_sha256, sha256_text(request))
            self.assertEqual(receipt.response_sha256, sha256_text(response))
            self.assertEqual(receipt.native_agent_id, f"fixture-{receipt.agent_id}")
        self.assertFalse(any(cap.isolation_verified for _, cap in result.runtime_capabilities))
