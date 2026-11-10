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
