"""Regression coverage for the read-only workboard's source/scope boundaries."""
from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / "tools/repository_workboard.py"
spec = importlib.util.spec_from_file_location("repository_workboard", MODULE)
workboard = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(workboard)

SHA = "a" * 40


def pr(n, draft=False):
    return {
        "number": n, "title": f"PR {n} | escaped", "html_url": f"https://github.com/x/y/pull/{n}",
        "head": {"sha": "b" * 40}, "base": {"ref": "main"}, "draft": draft,
        "updated_at": "2026-11-09T10:00:00Z", "labels": [], "assignees": [],
    }


def issue(n, is_pr=False):
    row = {
        "number": n, "title": "Issue", "html_url": f"https://github.com/x/y/issues/{n}",
        "updated_at": "2026-11-09T10:00:00Z", "labels": [], "assignees": [],
    }
    if is_pr:
        row["pull_request"] = {"url": "https://api.github.com/repos/x/y/pulls/3"}
    return row


class StubAPI:
    def __init__(self, change_head=False, many=False):
        self.paths = []
        self.change_head = change_head
        self.many = many
        self.branch_reads = 0

    def get(self, path):
        self.paths.append(path)
        if path == "/repos/n0tf0und0ut/Project-FAR":
            return {"default_branch": "main"}
        if path.endswith("/branches/main"):
            self.branch_reads += 1
            return {"commit": {"sha": ("c" * 40) if self.change_head and self.branch_reads > 1 else SHA}}
        if "/pulls?" in path:
            if self.many:
                if "&page=1" in path:
                    return [pr(i) for i in range(100)]
                return [pr(490, True)]
            return [pr(490, True), pr(615)]
        if "/issues?" in path:
            return [issue(513), issue(615, True)]
        raise AssertionError(path)


class WorkboardTests(unittest.TestCase):
    def test_counts_exclude_pr_issues_and_permanent_inbox(self):
        api = StubAPI()
        doc = workboard.collect(api, now=datetime(2026, 11, 9, tzinfo=timezone.utc))
        self.assertEqual(doc["counts"], {
            "open_prs": 2, "actionable_prs": 1, "permanent_inbox_prs": 1,
            "open_issues": 1, "unassigned_issues": 1, "unlabeled_issues": 1,
        })
        self.assertEqual(doc["prs"][-1]["state"], "PERMANENT INBOX — DO NOT MERGE")
        self.assertEqual(doc["prs"][0]["merge_readiness"], "NOT_EVALUATED")
        self.assertEqual(api.branch_reads, 2)
        output = workboard.markdown(doc)
        self.assertIn("PR 615 \\| escaped", output)
        self.assertIn("not scientific authority", output)

    def test_pagination_is_exhaustive(self):
        api = StubAPI(many=True)
        doc = workboard.collect(api)
        self.assertEqual(doc["counts"]["open_prs"], 101)
        self.assertTrue(any("page=2" in path for path in api.paths))

    def test_head_change_fails_closed(self):
        with self.assertRaisesRegex(workboard.WorkboardError, "advanced"):
            workboard.collect(StubAPI(change_head=True))

    def test_wrong_repo_does_not_inherit_far_inbox_policy(self):
        other = workboard._pr(pr(490, True), "someone/else")
        self.assertEqual(other["state"], "DRAFT")

    def test_unexpected_pagination_response_fails_closed(self):
        class Bad:
            def get(self, path):
                return {"not": "a list"}
        with self.assertRaises(workboard.WorkboardError):
            workboard.pages(Bad(), "/repos/x/y/pulls")


if __name__ == "__main__":
    unittest.main()
