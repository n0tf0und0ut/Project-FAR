"""Artifact runtime paths do not exempt ordinary source path references."""
import contextlib
import io
import runpy
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml


CHECKER = Path(__file__).resolve().parents[1] / "tools/check_repository_hygiene.py"


class RuntimePathTests(unittest.TestCase):
    def check(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, payload in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(yaml.safe_dump(payload), encoding="utf-8")
            common = types.ModuleType("common_health")
            common.ROOT = root
            common.iter_files = lambda suffixes: (p for p in root.rglob("*") if p.is_file() and p.suffix in suffixes)
            common.rel = lambda p: p.relative_to(root).as_posix()
            output = io.StringIO()
            code = 0
            with patch.dict(sys.modules, {"common_health": common}), contextlib.redirect_stdout(output):
                try:
                    runpy.run_path(str(CHECKER), run_name="__main__")
                except SystemExit as exc:
                    code = exc.code
            return code, output.getvalue()

    @staticmethod
    def workflow(action, inputs):
        return {"jobs": {"test": {"steps": [{"uses": action, "with": inputs}]}}}

    def test_official_upload_and_download_runtime_paths_need_not_exist(self):
        for action in ("actions/upload-artifact@v4", "actions/download-artifact@" + "a"*40):
            with self.subTest(action=action):
                code, output = self.check({".github/workflows/check.yml": self.workflow(action, {"path": "runtime-evidence/"})})
                self.assertEqual(code, 0, output)
                self.assertIn("Repository hygiene OK", output)

    def test_other_official_action_inputs_still_require_source_paths(self):
        for action in ("actions/upload-artifact@v4", "actions/download-artifact@v4"):
            for key in ("report", "file", "source", "fixture", "schema_path", "config_file"):
                with self.subTest(action=action, key=key):
                    code, output = self.check({".github/workflows/check.yml": self.workflow(action, {"path": "runtime/", key: "missing/source.json"})})
                    self.assertEqual(code, 1)
                    self.assertIn("referenced path missing: missing/source.json", output)
                    self.assertNotIn("referenced path missing: runtime/", output)

    def test_ordinary_and_lookalike_actions_are_not_exempt(self):
        actions = ("actions/checkout@v4", "someone/upload-artifact@v4", "actions/upload-artifact-extra@v4", "actions/upload-artifact/subdir@v4", "actions/download-artifact-lookalike@v4", "actions/upload-artifact@", "actions/upload-artifact@v4 extra")
        for action in actions:
            with self.subTest(action=action):
                code, output = self.check({".github/workflows/check.yml": self.workflow(action, {"path": "missing/source.txt"})})
                self.assertEqual(code, 1, output)
                self.assertIn("missing/source.txt", output)

    def test_nonworkflow_data_and_composite_actions_are_not_exempt(self):
        for path in ("research/sample.yml", ".github/actions/example/action.yml", ".github/workflows/subdirectory/example.yml"):
            with self.subTest(path=path):
                code, output = self.check({path: self.workflow("actions/upload-artifact@v4", {"path": "missing/source.txt"})})
                self.assertEqual(code, 1, output)
                self.assertIn("missing/source.txt", output)

    def test_uses_outside_a_real_workflow_job_step_does_not_exempt(self):
        examples = (
            {"uses": "actions/upload-artifact@v4", "with": {"path": "missing/source.txt"}},
            {"jobs": {"test": {"uses": "actions/upload-artifact@v4", "with": {"path": "missing/source.txt"}}}},
            {"jobs": {"test": {"steps": {"uses": "actions/upload-artifact@v4", "with": {"path": "missing/source.txt"}}}}},
        )
        for value in examples:
            with self.subTest(value=value):
                code, output = self.check({".github/workflows/check.yml": value})
                self.assertEqual(code, 1, output)
                self.assertIn("missing/source.txt", output)

    def test_exemption_applies_only_to_direct_literal_with_path(self):
        value = self.workflow("actions/upload-artifact@v4", {"path": "runtime/", "other": {"path": "missing/nested.txt"}})
        value["jobs"]["test"]["steps"][0]["path"] = "missing/step.txt"
        code, output = self.check({".github/workflows/check.yml": value})
        self.assertEqual(code, 1, output)
        self.assertIn("missing/nested.txt", output)
        self.assertIn("missing/step.txt", output)
        self.assertNotIn("referenced path missing: runtime/", output)

    def test_existing_source_references_remain_valid(self):
        value = self.workflow("actions/checkout@v4", {"path": "source/config.yml"})
        code, output = self.check({".github/workflows/check.yml": value, "source/config.yml": {"name": "present"}})
        self.assertEqual(code, 0, output)


if __name__ == "__main__":
    unittest.main()
