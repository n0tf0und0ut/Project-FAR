"""Deterministic source-bound tests for the optional factory advisory adapter."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from tools.factory_fargraph import evaluate, main


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


class FactoryFargraphTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "repo"
        self.root.mkdir()
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "tests@example.invalid")
        git(self.root, "config", "user.name", "Test")
        (self.root / "a.py").write_text("def f():\n    return 1\n")
        (self.root / "b.py").write_text("from a import f\nf()\n")
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "base")
        self.base = git(self.root, "rev-parse", "HEAD")
        (self.root / "a.py").write_text("def f():\n    return 2\n")
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "candidate")
        self.head = git(self.root, "rev-parse", "HEAD")
        self.order = Path(self.tmp.name) / "order.json"
        self.order.write_text(json.dumps({"schema": "far-software-factory/work-order/1",
                            "id": "pilot", "repository": "n0tf0und0ut/Project-FAR",
                            "base_sha": self.base, "tasks": [{"id":"task", "objective":"review changes",
                            "acceptance":["verified"],"depends_on":[]}]}))
        # Reuse the factory parser at runtime; this test shim avoids importing
        # unrelated queue implementation into the standalone prototype checkout.
        fake = types.ModuleType("tools.software_factory")
        def parse(raw):
            data = json.loads(raw)
            if set(data) != {"schema", "id", "repository", "base_sha", "tasks"}:
                raise ValueError("Malformed work order")
            return data
        fake.parse_order_text = parse
        self.stub = patch.dict(sys.modules, {"tools.software_factory": fake})
        self.stub.start()
        self.addCleanup(self.stub.stop)

    def run_eval(self, **changes):
        kw = dict(root=self.root, work_order=self.order, head_sha=self.head,
                  repository="n0tf0und0ut/Project-FAR")
        kw.update(changes)
        return evaluate(**kw)

    def test_graph_is_bound_to_exact_work_order_and_head(self):
        result = self.run_eval()
        self.assertEqual(result["head_sha"], self.head)
        self.assertEqual(result["base_sha"], self.base)
        self.assertEqual(result["impact"]["changed"], ["a.py"])
        self.assertIn("b.py", [e["path"] for e in result["impact"]["possibly_affected"]])
        self.assertTrue(result["index_freshness"]["fresh"])
        self.assertEqual(result["status"], "ADVISORY_ONLY_NO_MERGE_AUTHORITY")

    def test_fails_closed_on_nonmatching_candidate(self):
        with self.assertRaisesRegex(ValueError, "HEAD differs"):
            self.run_eval(head_sha=self.base)

    def test_fails_closed_on_dirty_checkout(self):
        (self.root / "a.py").write_text("print('dirty')\n")
        with self.assertRaisesRegex(ValueError, "dirty"):
            self.run_eval()

    def test_fails_closed_on_new_untracked_file(self):
        (self.root / "new.py").write_text("pass\n")
        with self.assertRaisesRegex(ValueError, "dirty"):
            self.run_eval()

    def test_clean_checkout_transform_cannot_supply_exact_head_hash(self):
        git(self.root, "config", "core.autocrlf", "true")
        (self.root / "a.py").unlink()
        git(self.root, "checkout", "--", "a.py")
        self.assertEqual(git(self.root, "status", "--porcelain"), "")
        self.assertIn(b"\r\n", (self.root / "a.py").read_bytes())
        with self.assertRaisesRegex(ValueError, "differs from committed Git blob"):
            self.run_eval()

    def test_fails_closed_on_wrong_repository(self):
        with self.assertRaisesRegex(ValueError, "identity"):
            self.run_eval(repository="other/repo")

    def test_fails_closed_on_invalid_base(self):
        payload = json.loads(self.order.read_text())
        payload["base_sha"] = "e"*40
        self.order.write_text(json.dumps(payload))
        with self.assertRaises(ValueError):
            self.run_eval()

    def test_deleted_file_is_reported_as_unresolved(self):
        git(self.root, "rm", "b.py")
        git(self.root, "commit", "-qm", "delete caller")
        deleted_head = git(self.root, "rev-parse", "HEAD")
        result = self.run_eval(head_sha=deleted_head)
        self.assertEqual(result["deleted_paths_with_unknown_prior_edges"], ["b.py"])
        self.assertIn("b.py", result["impact"]["missing"])

    def test_rename_preserves_deleted_path_independent_of_git_configuration(self):
        git(self.root, "mv", "b.py", "caller.py")
        git(self.root, "commit", "-qm", "rename caller")
        self.head = git(self.root, "rev-parse", "HEAD")
        for renames in ("true", "false"):
            with self.subTest(renames=renames):
                git(self.root, "config", "diff.renames", renames)
                result = self.run_eval()
                self.assertEqual(result["deleted_paths_with_unknown_prior_edges"], ["b.py"])
                self.assertIn("caller.py", result["impact"]["changed"])

    def test_replace_ref_cannot_change_exact_head_ancestry(self):
        tree = git(self.root, "rev-parse", "HEAD^{tree}")
        alternate = git(self.root, "commit-tree", tree, "-m", "unrelated parentless commit")
        git(self.root, "replace", self.head, alternate)
        self.assertEqual(self.run_eval()["impact"]["changed"], ["a.py"])
        git(self.root, "replace", "-d", self.head)
        git(self.root, "replace", self.base, alternate)
        self.assertEqual(self.run_eval()["impact"]["changed"], ["a.py"])

    def test_ignored_supported_local_file_cannot_enter_exact_head_graph(self):
        (self.root / ".gitignore").write_text("local.py\n")
        git(self.root,"add",".gitignore")
        git(self.root,"commit","-qm","ignore local")
        self.head=git(self.root,"rev-parse","HEAD")
        (self.root/"local.py").write_text("from a import f\n")
        result=self.run_eval()
        self.assertNotIn("local.py",result["indexed_source_hashes"])
        self.assertTrue(result["index_freshness"]["fresh"])
        self.assertEqual(result["status"],"ADVISORY_ONLY_NO_MERGE_AUTHORITY")

    def test_unicode_deleted_paths_are_reported_without_git_quoting(self):
        (self.root/"café.py").write_text("value = 1\n")
        git(self.root,"add","café.py")
        git(self.root,"commit","-qm","unicode base")
        self.base=git(self.root,"rev-parse","HEAD")
        order=json.loads(self.order.read_text())
        order["base_sha"]=self.base
        self.order.write_text(json.dumps(order))
        git(self.root,"rm","café.py")
        git(self.root,"commit","-qm","delete unicode")
        self.head=git(self.root,"rev-parse","HEAD")
        result=self.run_eval()
        self.assertEqual(result["deleted_paths_with_unknown_prior_edges"],["café.py"])
        self.assertIn("café.py",result["impact"]["missing"])

    def test_cli_success_and_failure_codes(self):
        from contextlib import redirect_stdout, redirect_stderr
        from io import StringIO
        args = ["--root",str(self.root),"--work-order",str(self.order),
                "--head-sha", self.head, "--repository", "n0tf0und0ut/Project-FAR"]
        out = StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(args), 0)
        self.assertEqual(json.loads(out.getvalue())["status"], "ADVISORY_ONLY_NO_MERGE_AUTHORITY")
        with redirect_stderr(StringIO()):
            self.assertEqual(main(args[:-1] + ["wrong/repo"]), 2)


if __name__ == "__main__":
    unittest.main()

class FactoryParserContractTest(unittest.TestCase):
    def test_live_factory_parser_rejects_duplicate_json_keys(self):
        try:
            from tools.software_factory import FactoryError, parse_order_text
        except ImportError:
            self.skipTest("Standalone prototype has no Project FAR software_factory module")
        with self.assertRaises(FactoryError):
            parse_order_text('{"schema":"a","schema":"b"}')
