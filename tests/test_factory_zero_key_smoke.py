"""Fail-closed controls for the Research-only credential-free worker smoke."""
from __future__ import annotations

import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

from tools import factory_zero_key_smoke as smoke


BASE = {
    "schema": smoke.SCHEMA,
    "task_id": "FAR-MAINT-002",
    "issue_number": 648,
    "base_sha": "a" * 40,
    "source_git_blob": "b" * 40,
    "allowed_path": "tools/example.py",
    "task_text": "Detect changes even when Git porcelain classification is unchanged.",
    "test_module": "test_health_and_runner",
}


def encode(value):
    return json.dumps(value, sort_keys=True).encode()


def example_patch(path="tools/example.py"):
    return (f"diff --git a/{path} b/{path}\n"
            f"--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@\n-x = 1\n+x = 2\n")


def run_git(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo, stderr=subprocess.DEVNULL).decode().strip()


class ManifestTests(unittest.TestCase):
    def test_accepted_canonical_manifest(self):
        self.assertEqual(smoke.manifest(encode(BASE)), BASE)

    def test_duplicate_keys_and_nonfinite_rejected(self):
        for raw in [b'{"x": 1, "x": 2}', b'{"x": NaN}', b'{"x": Infinity}', b'{} {}']:
            with self.subTest(raw=raw), self.assertRaises(smoke.SmokeError):
                smoke.manifest(raw)

    def test_invalid_source_sha_task_or_path(self):
        bad = [
            ("base_sha", "bad"), ("source_git_blob", "0" * 39),
            ("issue_number", True), ("task_id", "../../escape"),
            ("allowed_path", "../esc.py"), ("allowed_path", "/root/file.py"),
            ("allowed_path", "tools//file.py"), ("allowed_path", "tools\\file.py"),
            ("allowed_path", "tools/runner.sh"), ("test_module", "os.system"),
            ("task_text", ""),
        ]
        for key, value in bad:
            with self.subTest(key=key, value=value), self.assertRaises(smoke.SmokeError):
                smoke.manifest(encode({**BASE, key: value}))

    def test_unknown_fields_and_oversized_manifest(self):
        with self.assertRaises(smoke.SmokeError):
            smoke.manifest(encode({**BASE, "hidden_override": "allow"}))
        with self.assertRaises(smoke.SmokeError):
            smoke.manifest(b" " * (smoke.MAX_TASK_BYTES + 1))

    def test_patch_single_path_only(self):
        self.assertEqual(smoke.patch_text(encode({"patch": example_patch()}), BASE["allowed_path"]), example_patch())

    def test_patch_rejects_rogue_files_and_modes(self):
        good = example_patch()
        wrongs = [
            example_patch("tools/other.py"),
            good + example_patch("tools/other.py"),
            good.replace("--- a/tools/example.py", "--- a/etc/passwd"),
            good.replace("+++ b/tools/example.py", "+++ b/tools/other.py"),
            good.replace("@@ -1 +1 @@", "new file mode 100644\n@@ -1 +1 @@"),
            good.replace("@@ -1 +1 @@", "Binary files differ\n@@ -1 +1 @@"),
            good.replace("@@ -1 +1 @@", "rename from example.py\n@@ -1 +1 @@"),
            good.replace("@@ -1 +1 @@", "no valid hunk"),
            good.rstrip("\n"),
        ]
        for patch in wrongs:
            with self.subTest(patch=patch[:80]), self.assertRaises(smoke.SmokeError):
                smoke.patch_text(encode({"patch": patch}), BASE["allowed_path"])

    def test_patch_rejects_extra_keys_bad_json_and_oversize(self):
        for raw in [
            b'{"patch":"a","patch":"b"}',
            encode({"patch": example_patch(), "approve": True}),
            encode({"patch": example_patch() * 2000}),
            b'{"patch": "\\u0000"}',
        ]:
            with self.subTest(raw=raw[:50]), self.assertRaises(smoke.SmokeError):
                smoke.patch_text(raw, BASE["allowed_path"])


class GitAndRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "source"
        self.repo.mkdir()
        (self.repo / "tools").mkdir()
        (self.repo / "tests").mkdir()
        (self.repo / "tools/example.py").write_text("x = 1\n", encoding="utf-8")
        (self.repo / "tests/test_health_and_runner.py").write_text("pass\n", encoding="utf-8")
        run_git(self.repo, "init", "-q")
        run_git(self.repo, "config", "user.name", "Research")
        run_git(self.repo, "config", "user.email", "research@example.com")
        run_git(self.repo, "add", ".")
        run_git(self.repo, "commit", "-qm", "baseline")
        self.base = run_git(self.repo, "rev-parse", "HEAD")
        self.blob = run_git(self.repo, "rev-parse", "HEAD:tools/example.py")

    def test_standalone_grader_snapshot_has_internal_git_directory(self):
        with tempfile.TemporaryDirectory() as td:
            isolated = smoke.prepare_test_checkout(self.repo, Path(td))
            self.assertTrue((isolated / ".git").is_dir())
            self.assertEqual(run_git(isolated, "status", "--porcelain"), "")
            self.assertEqual((isolated / "tools/example.py").read_bytes(),
                             (self.repo / "tools/example.py").read_bytes())
            self.assertNotEqual(run_git(isolated, "rev-parse", "--git-dir"),
                                str(self.repo / ".git"))
            (isolated / "tools/example.py").write_text("x = 9\n")
            self.assertTrue(run_git(isolated, "status", "--porcelain"))
            self.assertEqual((self.repo / "tools/example.py").read_text(), "x = 1\n")

    def test_failed_baseline_blocks_model_and_keeps_receipt(self):
        entry = {**BASE, "base_sha": self.base, "source_git_blob": self.blob}
        path = Path(self.tmp.name) / "baseline-task.json"
        path.write_bytes(encode(entry))
        output = Path(self.tmp.name) / "baseline-failed"
        stub = types.ModuleType("tools.workflow_efficacy_free_agent")
        stub.local_model_digest = lambda: smoke.MODEL_DIGEST
        with mock.patch.dict(sys.modules, {"tools.workflow_efficacy_free_agent": stub}), \
                mock.patch.object(smoke, "grader_image_id", return_value="sha256:" + "a" * 64), \
                mock.patch.object(smoke, "grade_in_docker", return_value={"state": "FAIL", "exit_code": 1}), \
                mock.patch.object(smoke, "model_reply", side_effect=AssertionError("no model call allowed")) as model:
            result = smoke.run(self.repo, path, output)
        model.assert_not_called()
        self.assertEqual(result["before"]["state"], "FAIL")
        self.assertEqual(result["verdict"], "BLOCKED_OR_MODEL_OUTPUT_INVALID")
        self.assertIn("baseline public tests", result["error"])
        self.assertIsNone(result["generation"])
        self.assertTrue((output / "receipt.json").is_file())

    def test_unpinned_grader_image_identity_rejected(self):
        with mock.patch.object(smoke.subprocess, "run",
                               return_value=subprocess.CompletedProcess([], 0, stdout="image-tag-only\n")):
            with self.assertRaisesRegex(smoke.SmokeError, "non-addressed grader image"):
                smoke.grader_image_id()
        with mock.patch.object(smoke, "prepare_test_checkout") as prepare:
            with self.assertRaisesRegex(smoke.SmokeError, "non-addressed grader image"):
                smoke.grade_in_docker(self.repo, "test_health_and_runner", self.repo,
                                      "before", image_id=smoke.IMAGE)
        prepare.assert_not_called()

    def test_git_apply_checks_exact_allowlist(self):
        with tempfile.TemporaryDirectory() as root:
            rootpath = Path(root) / "checkout"
            run_git(self.repo, "worktree", "add", "--detach", str(rootpath), self.base)
            try:
                self.assertEqual(run_git(rootpath, "reflog", "show", "-1", "--format=%gn%n%ge", "HEAD"),
                                 "Research\nresearch@example.com")
                self.assertEqual(smoke.apply_candidate(rootpath, example_patch(), "tools/example.py"),
                                 run_git(rootpath, "hash-object", "tools/example.py"))
                self.assertEqual((rootpath / "tools/example.py").read_text(), "x = 2\n")
            finally:
                run_git(self.repo, "worktree", "remove", "--force", str(rootpath))

    def test_docker_grade_never_receives_host_credentials_or_network(self):
        # Run a real child process via the declared Python interpreter;
        # inspect the original Docker arguments and exercise bounded pipes.
        with tempfile.TemporaryDirectory() as td:
            child = [sys.executable, "-c", "import sys; sys.stdout.write('good'); sys.stderr.write('Ran 1 test in 0.1s\\nOK\\n')"]
            original = smoke.subprocess.Popen
            seen = []
            def intercept(cmd, **kwargs):
                seen.extend(cmd)
                return original(child, **kwargs)
            with mock.patch.object(smoke, "prepare_test_checkout", return_value=self.repo), \
                    mock.patch.object(smoke.subprocess, "Popen", side_effect=intercept):
                result = smoke.grade_in_docker(self.repo, "test_health_and_runner", Path(td), "before",
                                               image_id="sha256:" + "a" * 64)
            self.assertEqual(result["state"], "PASS")
            self.assertEqual(seen[:2], ["docker", "run"])
            self.assertIn("none", seen)
            self.assertIn("--read-only", seen)
            self.assertIn("no-new-privileges", seen)
            self.assertIn("readonly", " ".join(seen))
            self.assertIn("GIT_OPTIONAL_LOCKS=0", seen)
            self.assertIn("GIT_CONFIG_VALUE_0=/app", seen)
            self.assertIn("sha256:" + "a" * 64, seen)
            self.assertNotIn(smoke.IMAGE, seen)
            self.assertIn("--pull=never", seen)
            self.assertNotIn("GITHUB_TOKEN", " ".join(seen))
            self.assertEqual((Path(td) / "before.stdout").read_bytes(), b"good")

    def test_zero_test_exit_zero_is_not_success(self):
        with tempfile.TemporaryDirectory() as td:
            child = [sys.executable, "-c", "import sys; sys.stderr.write('Ran 0 tests in 0.001s\\nOK\\n')"]
            original = smoke.subprocess.Popen
            with mock.patch.object(smoke, "prepare_test_checkout", return_value=self.repo), \
                    mock.patch.object(smoke.subprocess, "Popen", side_effect=lambda cmd, **kw: original(child, **kw)):
                result = smoke.grade_in_docker(self.repo, "test_health_and_runner", Path(td), "before",
                                               image_id="sha256:" + "a" * 64)
            self.assertEqual(result["state"], "UNKNOWN")
            self.assertEqual(result["test_count_reported"], 0)

    def test_docker_output_overflow_is_bounded_and_not_green(self):
        with tempfile.TemporaryDirectory() as td:
            child = [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'x' * 2000000)"]
            original = smoke.subprocess.Popen
            with mock.patch.object(smoke, "prepare_test_checkout", return_value=self.repo), \
                    mock.patch.object(smoke.subprocess, "Popen", side_effect=lambda cmd, **kw: original(child, **kw)):
                with mock.patch.object(smoke.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)):
                    result = smoke.grade_in_docker(self.repo, "test_health_and_runner", Path(td), "before",
                                               image_id="sha256:" + "a" * 64)
            self.assertEqual(result["state"], "UNKNOWN")
            self.assertTrue(result["output_truncated"])
            self.assertEqual((Path(td) / "before.stdout").stat().st_size, smoke.MAX_TEST_STREAM_BYTES)

    def test_smoke_emits_receipt_and_cleans_worktree(self):
        entry = {**BASE, "base_sha": self.base, "source_git_blob": self.blob}
        manifest_path = Path(self.tmp.name) / "task.json"
        manifest_path.write_bytes(encode(entry))
        output = Path(self.tmp.name) / "output"
        mock_module = types.ModuleType("tools.workflow_efficacy_free_agent")
        mock_module.local_model_digest = lambda: smoke.MODEL_DIGEST
        model = (encode({"patch": example_patch()}), b'{"done":true}',
                 {"input_tokens": 21, "output_tokens": 42, "response_sha256": "c" * 64,
                  "api_model": smoke.MODEL})
        tests = {"state": "PASS", "exit_code": 0, "elapsed_seconds": 0.1}
        with mock.patch.dict(sys.modules, {"tools.workflow_efficacy_free_agent": mock_module}), \
                mock.patch.object(smoke, "model_reply", return_value=model), \
                mock.patch.object(smoke, "grader_image_id", return_value="sha256:" + "a" * 64), \
                mock.patch.object(smoke, "grade_in_docker", return_value=tests) as grade:
            receipt = smoke.run(self.repo, manifest_path, output)
        self.assertEqual(receipt["verdict"], "VISIBLE_TESTS_PASSED_NOT_INDEPENDENTLY_VERIFIED")
        self.assertRegex(receipt["candidate_git_blob"], r"^[0-9a-f]{40}$")
        self.assertEqual(receipt["before"]["state"], "PASS")
        self.assertEqual(receipt["after"]["state"], "PASS")
        self.assertEqual([call.args[3] for call in grade.call_args_list], ["before", "after"])
        self.assertEqual([call.kwargs["image_id"] for call in grade.call_args_list],
                         [receipt["grader_image_id"]] * 2)
        self.assertTrue((output / "receipt.json").is_file())
        self.assertTrue((output / "candidate.patch").is_file())
        self.assertEqual((output / "model-transport-response.json").read_bytes(), b'{"done":true}')
        self.assertEqual(len(run_git(self.repo, "worktree", "list").splitlines()), 1)
        with self.assertRaises(smoke.SmokeError):
            smoke.run(self.repo, manifest_path, output)

    def test_smoke_blocks_mismatched_or_absent_reply_model_and_preserves_response(self):
        manifest_path = Path(self.tmp.name) / "task-identity.json"
        manifest_path.write_bytes(encode({**BASE, "base_sha": self.base, "source_git_blob": self.blob}))
        stub = types.ModuleType("tools.workflow_efficacy_free_agent")
        stub.local_model_digest = lambda: smoke.MODEL_DIGEST
        for index, model_fields in enumerate(({"model": "another-model:1b"}, {})):
            with self.subTest(model_fields=model_fields):
                output = Path(self.tmp.name) / f"output-identity-{index}"
                reply = encode({
                    **model_fields, "done": True, "eval_count": 1, "prompt_eval_count": 1,
                    "message": {"content": encode({"patch": example_patch()}).decode()},
                })
                with mock.patch.dict(sys.modules, {"tools.workflow_efficacy_free_agent": stub}), \
                        mock.patch.object(smoke.urllib.request, "urlopen", return_value=io.BytesIO(reply)), \
                        mock.patch.object(smoke, "grader_image_id", return_value="sha256:" + "a" * 64), \
                        mock.patch.object(smoke, "grade_in_docker", return_value={"state": "PASS"}) as grade:
                    receipt = smoke.run(self.repo, manifest_path, output)
                self.assertEqual(receipt["verdict"], "BLOCKED_OR_MODEL_OUTPUT_INVALID")
                self.assertIn("reply model", receipt["error"])
                self.assertIsNone(receipt["after"])
                self.assertFalse((output / "candidate.patch").exists())
                self.assertEqual([call.args[3] for call in grade.call_args_list], ["before"])
                self.assertEqual((output / "model-transport-response.json").read_bytes(), reply)
                self.assertEqual(receipt["artifact_sha256"]["model-transport-response.json"], smoke.sha(reply))

    def test_missing_local_model_preserves_blocked_receipt(self):
        entry = {**BASE, "base_sha": self.base, "source_git_blob": self.blob}
        path = Path(self.tmp.name) / "task-model.json"
        path.write_bytes(encode(entry))
        output = Path(self.tmp.name) / "model-unavailable"
        stub = types.ModuleType("tools.workflow_efficacy_free_agent")
        def unavailable():
            raise RuntimeError("local model daemon unavailable")
        stub.local_model_digest = unavailable
        with mock.patch.dict(sys.modules, {"tools.workflow_efficacy_free_agent": stub}):
            result = smoke.run(self.repo, path, output)
        self.assertEqual(result["verdict"], "BLOCKED_OR_MODEL_OUTPUT_INVALID")
        self.assertEqual(result["error_type"], "RuntimeError")
        self.assertIsNone(result["model_digest"])
        self.assertTrue((output / "receipt.json").is_file())
        self.assertEqual(len(run_git(self.repo, "worktree", "list").splitlines()), 1)

    def test_source_blob_mismatch_preserves_blocked_receipt(self):
        entry = {**BASE, "base_sha": self.base, "source_git_blob": "0" * 40}
        path = Path(self.tmp.name) / "task.json"
        path.write_bytes(encode(entry))
        output = Path(self.tmp.name) / "failed-output"
        stub = types.ModuleType("tools.workflow_efficacy_free_agent")
        stub.local_model_digest = lambda: smoke.MODEL_DIGEST
        with mock.patch.dict(sys.modules, {"tools.workflow_efficacy_free_agent": stub}), \
                mock.patch.object(smoke, "grader_image_id", return_value="sha256:" + "a" * 64):
            row = smoke.run(self.repo, path, output)
        self.assertEqual(row["verdict"], "BLOCKED_OR_MODEL_OUTPUT_INVALID")
        self.assertIn("blob mismatch", row["error"])
        self.assertTrue((output / "receipt.json").is_file())
        self.assertEqual(len(run_git(self.repo, "worktree", "list").splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
