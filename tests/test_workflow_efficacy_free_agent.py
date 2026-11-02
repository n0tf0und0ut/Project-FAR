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
from tools.workflow_efficacy_free_agent import (
    grade, unauthorized_file_changes, execute_agent_process, capture_candidate_process,
)
from tools.workflow_efficacy_internal_fixtures import task
from tools.workflow_efficacy_free_agent import (
    ARMS, CONTROL_SHA, TREATMENT_SHA, MAX_SECONDS, MODEL,
    SAFE_CONFIG, order_for, parse_events, MODEL_DIGEST_PREFIX, local_model_digest,
)

def local_grader_transport(cmd, payload):
    """Exercise real candidate Python; replace only Docker transport in tests."""
    mount = cmd[cmd.index("-v") + 1].rsplit(":/app:ro", 1)[0]
    start = next(i for i, arg in enumerate(cmd) if arg.startswith("python:3.12-slim")) + 1
    child = cmd[start:]
    child[0] = sys.executable
    child = [arg.replace("/app/solution.py", str(Path(mount) / "solution.py")) for arg in child]
    return capture_candidate_process(child, payload)

class RunnerTests(unittest.TestCase):
    def check_candidate(self, source):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            candidate = base / "submission.py"
            candidate.write_text(source)
            with patch("tools.workflow_efficacy_free_agent.capture_candidate_process",
                       side_effect=local_grader_transport), patch(
                           "tools.workflow_efficacy_free_agent.subprocess.run",
                           return_value=SimpleNamespace(returncode=0, stdout="", stderr="")):
                return grade(candidate, task(0), base)

    def test_skiptest_is_a_measured_failure(self):
        result = self.check_candidate(
            "def transform(d): raise __import__('unittest').SkipTest('unimplemented')\n")
        self.assertFalse(result[0])
        self.assertTrue(result[4])

    def test_candidate_cannot_disable_the_assertions(self):
        result = self.check_candidate(
            "import unittest\nunittest.TestCase.assertEqual = lambda *a, **kw: None\n"
            "def transform(d): return None\n")
        self.assertFalse(result[0])
        self.assertTrue(result[4])

    def test_candidate_cannot_forge_a_unittest_success(self):
        result = self.check_candidate(
            "import os\nprint('Ran 2 tests in 0.01s\\nOK', flush=True)\nos._exit(0)\n"
            "def transform(d): return None\n")
        self.assertFalse(result[0])
        self.assertTrue(result[4])

    def test_correct_candidate_passes_all_six_comparisons(self):
        result = self.check_candidate(
            "def transform(d): return min(d['high'], max(d['low'], d['value']))\n")
        self.assertTrue(result[0])
        self.assertTrue(result[4])

    def test_invalid_candidate_bytes_are_a_measured_failure(self):
        result = self.check_candidate(
            "import os\nos.write(1,b'\\xff'); os._exit(0)\n"
            "def transform(d): return None\n")
        self.assertFalse(result[0])
        self.assertTrue(result[4])

    def test_excessive_output_is_a_measured_bounded_failure(self):
        result = self.check_candidate(
            "import sys\ndef transform(d):\n"
            "    sys.stderr.write('x'*100001)\n"
            "    return min(d['high'],max(d['low'],d['value']))\n")
        self.assertFalse(result[0])
        self.assertTrue(result[4])
        rows = __import__('json').loads(result[3])["comparisons"]
        self.assertEqual({r["status"] for r in rows}, {"OUTPUT_LIMIT"})
        self.assertTrue(all(r["stderr_bytes_observed"] > 100000 for r in rows))
        self.assertTrue(all(len(r["stderr"].encode()) <= 100000 for r in rows))

    def test_deeply_nested_candidate_json_is_a_measured_failure(self):
        result = self.check_candidate(
            "import os\nos.write(1,b'['*20000+b'0'+b']'*20000);os._exit(0)\n"
            "def transform(d): return None\n")
        self.assertFalse(result[0])
        self.assertTrue(result[4])

    def test_unbounded_candidate_print_loop_is_stopped(self):
        result = self.check_candidate(
            "import os\ndef transform(d):\n    while True: os.write(1,b'x'*8192)\n")
        self.assertFalse(result[0])
        self.assertTrue(result[4])
        rows = __import__('json').loads(result[3])["comparisons"]
        self.assertTrue(all(r["output_limited"] for r in rows))

    def test_nonfinite_and_duplicate_json_cannot_bypass_output_checks(self):
        from tools.workflow_efficacy_free_agent import candidate_output
        for output in ('NaN', 'Infinity', '{"x":1,"x":2}'):
            with self.subTest(output=output), self.assertRaises(ValueError):
                candidate_output(output)

    def test_hanging_candidate_is_a_measured_resource_failure(self):
        with patch("tools.workflow_efficacy_free_agent.GRADER_SECONDS_PER_CASE", 0.15):
            result = self.check_candidate("def transform(d):\n    while True: pass\n")
        self.assertFalse(result[0])
        self.assertEqual(result[1], 1)
        self.assertTrue(result[4])
        self.assertEqual({r["status"] for r in __import__('json').loads(result[3])["comparisons"]},
                         {"RESOURCE_LIMIT"})

    def test_container_start_timeout_is_infrastructure_failure(self):
        def stalled(cmd, payload):
            return {"stdout": "", "stderr": "", "exit_code": None,
                    "stdout_bytes_observed": 0, "stderr_bytes_observed": 0,
                    "timed_out": True, "output_limited": False}
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            source = base / "source.py"
            source.write_text("def transform(d): return 1\n")
            with patch("tools.workflow_efficacy_free_agent.capture_candidate_process", side_effect=stalled), patch(
                    "tools.workflow_efficacy_free_agent.subprocess.run",
                    return_value=SimpleNamespace(returncode=0, stdout="", stderr="")):
                result = grade(source, task(0), base)
        self.assertFalse(result[4])
        self.assertIsNone(result[1])
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
    def test_digest_rejects_a_matching_prefix_with_different_full_hash(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self):
                return __import__('json').dumps({"models": [{"name": "qwen2.5-coder:1.5b",
                    "digest": "d7372fd82851" + "0" * 52}]}).encode()
        with patch("tools.workflow_efficacy_free_agent.urllib.request.urlopen", return_value=Response()):
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
            inputs = []
            def fake_run(cmd, payload):
                self.assertEqual(sorted(p.name for p in (base / "grade").iterdir()), ["solution.py"])
                inputs.append(__import__('json').loads(payload))
                return {"exit_code": 1, "stdout": "", "stderr": "FAR_CANDIDATE_STARTED_V1\nValueError\n",
                        "stdout_bytes_observed": 0, "stderr_bytes_observed": 35,
                        "timed_out": False, "output_limited": False}
            with patch("tools.workflow_efficacy_free_agent.capture_candidate_process", side_effect=fake_run), patch(
                    "tools.workflow_efficacy_free_agent.subprocess.run",
                    return_value=SimpleNamespace(returncode=0, stdout="", stderr="")):
                success, code, digest, trace, executed = grade(candidate, task(0), base)
        self.assertFalse(success)
        self.assertEqual(code, 1)
        self.assertTrue(executed)
        self.assertEqual(len(digest), 64)
        self.assertEqual(inputs, [r["input"] for group in ("public", "hidden") for r in task(0)[group]])
        self.assertEqual(len(__import__('json').loads(trace)["comparisons"]), 6)
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

    def test_staged_forbidden_edit_remains_unauthorized(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=folder, check=True)
            (folder / "solution.py").write_text("x=1\n")
            (folder / "README.md").write_text("original\n")
            subprocess.run(["git", "add", "."], cwd=folder, check=True)
            subprocess.run(["git", "-c", "user.name=Test", "-c",
                            "user.email=test@example.invalid", "commit", "-qm", "base"],
                           cwd=folder, check=True)
            (folder / "README.md").write_text("tampered\n")
            subprocess.run(["git", "add", "README.md"], cwd=folder, check=True)
            self.assertIn("README.md", unauthorized_file_changes(folder, {"solution.py"}))
    def test_separate_arm_workspace_is_deleted_between_conditions(self):
        import tempfile
        from unittest.mock import patch
        from tools.workflow_efficacy_free_agent import run_isolated_pair
        roots = []
        def fake_run(index, arm, root, evidence_root):
            if roots:
                self.assertFalse(roots[-1].exists(), "previous arm left secrets")
            roots.append(root)
            (root / "grade").mkdir()
            (root / "grade" / "test_hidden.py").write_text("secret answer")
            return {"arm": arm}
        with tempfile.TemporaryDirectory() as tmp:
            with patch("tools.workflow_efficacy_free_agent.run_arm", side_effect=fake_run):
                output = run_isolated_pair(0, Path(tmp) / "evidence")
        self.assertEqual(len(output), 2)
        self.assertTrue(all(not root.exists() for root in roots))

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

    def test_direct_patch_parsing(self):
        from tools.workflow_efficacy_free_agent import extract_patch
        self.assertIsNone(extract_patch("A plan for how to repair the file"))
        self.assertIsNone(extract_patch("def unrelated(x): return x"))
        self.assertEqual(extract_patch("def transform(d):\n    return 3"),
                         "def transform(d):\n    return 3\n")
        self.assertEqual(extract_patch("Here:\n" + chr(96)*3 +
                         "python\ndef transform(d):\n    return 4\n" + chr(96)*3),
                         "def transform(d):\n    return 4\n")

    def test_direct_generation_is_real_mocked_local_http_only(self):
        import json
        from tools.workflow_efficacy_free_agent import local_patch_request
        class Response:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self):
                return json.dumps({"done": True, "message": {"content":
                    "def transform(d):\n    return d['value']"},
                    "prompt_eval_count": 101, "eval_count": 23}).encode()
        with patch("tools.workflow_efficacy_free_agent.urllib.request.urlopen",
                   return_value=Response()) as mocked:
            answer, raw, metrics, code, timed_out, elapsed = local_patch_request(b"rules", task(0))
        self.assertEqual(mocked.call_count, 1)
        self.assertIn("def transform", answer)
        self.assertEqual(metrics["model_steps"], 1)
        self.assertEqual(metrics["input_tokens"], 101)
        self.assertEqual(code, 0)
        self.assertFalse(timed_out)

    def test_local_provider_timeout_does_not_score_as_completed(self):
        from tools.workflow_efficacy_free_agent import local_patch_request
        with patch("tools.workflow_efficacy_free_agent.urllib.request.urlopen",
                   side_effect=TimeoutError("local stalled")):
            answer, raw, metrics, code, timed_out, elapsed = local_patch_request(b"rules", task(0))
        self.assertIsNone(answer)
        self.assertIsNone(code)
        self.assertEqual(metrics["model_steps"], 0)
        self.assertGreater(metrics["error_events"], 0)
        self.assertTrue(timed_out)

    def test_invalid_json_is_not_model_execution(self):
        self.assertEqual(parse_events("noise")["model_steps"], 0)
if __name__ == "__main__":
    unittest.main()
