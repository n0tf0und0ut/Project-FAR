"""No-network structural tests for the 30-pair free-agent runner."""
import unittest
import os
import sys
import time
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from tools.workflow_efficacy_free_agent import grade, unauthorized_file_changes, execute_agent_process
from tools.workflow_efficacy_internal_fixtures import task
from tools.workflow_efficacy_free_agent import (
    ARMS, CONTROL_SHA, TREATMENT_SHA, MAX_SECONDS, MODEL,
    SAFE_CONFIG, order_for, parse_events, MODEL_DIGEST_PREFIX, local_model_digest,
)
class RunnerTests(unittest.TestCase):
    def test_schedule_balance_and_contract(self):
        orders = [order_for(i) for i in range(30)]
        self.assertEqual(len(orders), 30)
        self.assertEqual(sum(order[0] == "control" for order in orders), 15)
        self.assertEqual(sum(order[0] == "treatment" for order in orders), 15)
        self.assertTrue(all(set(x) == set(ARMS) for x in orders))
        self.assertEqual(len(CONTROL_SHA), 40)
        self.assertEqual(len(TREATMENT_SHA), 40)
        self.assertGreater(MAX_SECONDS, 0)
        self.assertEqual(MODEL, "ollama/qwen2.5-coder:1.5b")
    def test_local_provider_configuration_is_credential_free(self):
        self.assertEqual(SAFE_CONFIG["provider"]["ollama"]["options"]["baseURL"],
                         "http://127.0.0.1:11434/v1")
        self.assertEqual(SAFE_CONFIG["model"], MODEL)
        self.assertTrue(MODEL_DIGEST_PREFIX.startswith("d7372fd8"))
    def test_digest_rejects_unpinned_downloads(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self): return b'{"models":[{"name":"qwen2.5-coder:1.5b","digest":"wrong"}]}'
        with patch("tools.workflow_efficacy_free_agent.urllib.request.urlopen",
                   return_value=Response()):
            with self.assertRaises(RuntimeError):
                local_model_digest()
    def test_no_external_access_allowed(self):
        p = SAFE_CONFIG["permission"]
        self.assertEqual(p["external_directory"], "deny")
        self.assertEqual(p["websearch"], "deny")
        self.assertEqual(p["bash"]["*"], "deny")
    def test_model_event_metadata_parsing(self):
        raw = '{"type":"step-finish","part":{"type":"step-finish","tokens":{"input":12,"output":7},"cost":0}}\n'
        result = parse_events(raw)
        self.assertEqual(result["model_steps"], 1)
        self.assertEqual(result["input_tokens"], 12)
        self.assertEqual(result["output_tokens"], 7)
        self.assertEqual(result["reported_cost_usd"], 0)
    def test_independent_grader_runs_public_and_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            candidate = base / "submission.py"
            candidate.write_text("def transform(d):\n    return d.get('value')\n")
            def fake_run(cmd, **kwargs):
                self.assertIn("test_public", cmd)
                self.assertIn("test_hidden", cmd)
                self.assertTrue((base / "grade" / "test_public.py").is_file())
                self.assertTrue((base / "grade" / "test_hidden.py").is_file())
                return SimpleNamespace(returncode=1, stdout="", stderr="Ran 2 tests in 0.01s\nFAILED (failures=1)\n")
            with patch("tools.workflow_efficacy_free_agent.subprocess.run", side_effect=fake_run):
                success, code, digest, trace, executed = grade(candidate, task(0), base)
        self.assertFalse(success)
        self.assertEqual(code, 1)
        self.assertTrue(executed)
        self.assertEqual(len(digest), 64)
        self.assertIn("FAILED", trace)
    def test_created_file_is_unauthorized(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=folder, check=True)
            (folder / "solution.py").write_text("x=1\n")
            subprocess.run(["git", "add", "solution.py"], cwd=folder, check=True)
            subprocess.run(["git", "-c", "user.name=Test", "-c",
                            "user.email=test@example.invalid", "commit", "-qm", "base"],
                           cwd=folder, check=True)
            (folder / "solution.py").write_text("x=2\n")
            (folder / "test_extra.py").write_text("assert True\n")
            (folder / ".gitignore").write_text("__pycache__/\n*.pyc\n")
            (folder / "__pycache__").mkdir()
            (folder / "__pycache__" / "solution.cpython-312.pyc").write_bytes(b"expected runtime cache")
            result = unauthorized_file_changes(folder, {"solution.py"})
            self.assertEqual(result, [".gitignore", "test_extra.py"])

    def test_grader_transport_failure_is_ungraded(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            candidate = base / "submission.py"
            candidate.write_text("def transform(d): return 1\n")
            with patch("tools.workflow_efficacy_free_agent.subprocess.run", side_effect=OSError("docker unavailable")):
                success, code, digest, trace, executed = grade(candidate, task(0), base)
        self.assertFalse(success)
        self.assertIsNone(code)
        self.assertFalse(executed)

    @unittest.skipUnless(os.name == "posix", "process groups require POSIX")
    def test_timeout_kills_spawned_agent_descendant(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            started, leaked = root / "child-started", root / "child-continued"
            child = ("from pathlib import Path;import time;"
                     f"Path({str(started)!r}).write_text('started');"
                     "time.sleep(1.0);"
                     f"Path({str(leaked)!r}).write_text('escaped')")
            parent = ("import subprocess,sys,time;"
                      f"subprocess.Popen([sys.executable,'-c',{child!r}]);"
                      "time.sleep(15)")
            code, raw, timed_out = execute_agent_process(
                [sys.executable, "-c", parent], root, dict(os.environ), 0.7)
            self.assertTrue(timed_out)
            self.assertIsNone(code)
            self.assertTrue(started.exists(), "child must start for termination test")
            time.sleep(1.2)
            self.assertFalse(leaked.exists(), "surviving child modified workspace")

    def test_invalid_json_is_not_model_execution(self):
        self.assertEqual(parse_events("noise")["model_steps"], 0)
if __name__ == "__main__":
    unittest.main()
