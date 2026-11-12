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


def pr(n, draft=False, *, branch=None, head_repo=None):
    if branch is None:
        branch = workboard.PERMANENT_INBOX_BRANCH if n in (490, 653) else "feature/ordinary"
    if head_repo is None:
        head_repo = workboard.DEFAULT_REPO
    return {
        "number": n, "title": f"PR {n} | escaped", "html_url": f"https://github.com/x/y/pull/{n}",
        "head": {"sha": "b" * 40, "ref": branch, "repo": {"full_name": head_repo}},
        "base": {"ref": "main"}, "draft": draft,
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
    def __init__(self, change_head=False, many=False, duplicate=False, change_default=False):
        self.paths = []
        self.change_head = change_head
        self.many = many
        self.duplicate = duplicate
        self.change_default = change_default
        self.branch_reads = 0
        self.meta_reads = 0

    def get(self, path):
        self.paths.append(path)
        if path.lower() == "/repos/n0tf0und0ut/project-far":
            self.meta_reads += 1
            return {
                "default_branch": "develop" if self.change_default and self.meta_reads > 1 else "main",
                "full_name": workboard.DEFAULT_REPO,
            }
        if path.endswith("/branches/main"):
            self.branch_reads += 1
            return {"commit": {"sha": ("c" * 40) if self.change_head and self.branch_reads > 1 else SHA}}
        if "/pulls?" in path:
            if self.many:
                if "&page=1" in path:
                    return [pr(i) for i in range(1, 101)]
                return [pr(100, True)] if self.duplicate else [pr(653, True)]
            return [pr(653, True), pr(615)]
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
        self.assertEqual(next(p for p in doc["prs"] if p["number"] == 653)["state"],
                         "PERMANENT INBOX — DO NOT MERGE")
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

    def test_duplicate_identity_between_pages_fails_closed(self):
        with self.assertRaisesRegex(workboard.WorkboardError, "Duplicate item #100"):
            workboard.collect(StubAPI(many=True, duplicate=True))

    def test_invalid_page_item_identity_fails_closed(self):
        class Invalid:
            def get(self, path):
                return [{"number": True}]
        with self.assertRaisesRegex(workboard.WorkboardError, "Invalid item number"):
            workboard.pages(Invalid(), "/repos/x/y/pulls")

    def test_default_branch_switch_without_sha_drift_fails_closed(self):
        with self.assertRaisesRegex(workboard.WorkboardError, "Default branch or repository identity changed"):
            workboard.collect(StubAPI(change_default=True))

    def test_case_insensitive_far_identity_preserves_inbox_exclusion(self):
        doc = workboard.collect(StubAPI(), repo="n0tf0und0ut/project-far")
        self.assertEqual(doc["repo"], workboard.DEFAULT_REPO)
        self.assertEqual(doc["counts"]["permanent_inbox_prs"], 1)
        self.assertEqual(next(p for p in doc["prs"] if p["number"] == 653)["state"],
                         "PERMANENT INBOX — DO NOT MERGE")

    def test_successor_and_future_rolling_inbox_are_not_actionable(self):
        for n in (653, 700):
            row = pr(n, False, branch=workboard.PERMANENT_INBOX_BRANCH)
            self.assertEqual(workboard._pr(row, workboard.DEFAULT_REPO)["state"],
                             "PERMANENT INBOX — DO NOT MERGE")
            self.assertEqual(workboard._pr(row, "someone/else")["state"], "OPEN")
            row["head"]["repo"]["full_name"] = "someone/else"
            if n == 700:
                self.assertEqual(workboard._pr(row, workboard.DEFAULT_REPO)["state"], "OPEN")
        historical = pr(490, False, branch="retired/other")
        self.assertEqual(workboard._pr(historical, workboard.DEFAULT_REPO)["state"],
                         "PERMANENT INBOX — DO NOT MERGE")
        historical_653 = pr(653, False, branch="unexpected/rewrite")
        self.assertEqual(workboard._pr(historical_653, workboard.DEFAULT_REPO)["state"],
                         "PERMANENT INBOX — DO NOT MERGE")

    def test_ambiguous_active_rolling_inbox_fails_closed(self):
        class DuplicateSources(StubAPI):
            def get(self, path):
                if "/pulls?" in path:
                    return [pr(653, True),
                            pr(700, True, branch=workboard.PERMANENT_INBOX_BRANCH)]
                return super().get(path)
        with self.assertRaisesRegex(workboard.WorkboardError, "Multiple active permanent inbox"):
            workboard.collect(DuplicateSources())

    def test_only_matching_owner_branch_and_base_are_special(self):
        candidate = pr(700, True, branch=workboard.PERMANENT_INBOX_BRANCH)
        candidate["base"]["ref"] = "develop"
        self.assertEqual(workboard._pr(candidate, workboard.DEFAULT_REPO)["state"], "DRAFT")
        candidate["base"]["ref"] = "main"
        candidate["head"]["ref"] = "other/branch"
        self.assertEqual(workboard._pr(candidate, workboard.DEFAULT_REPO)["state"], "DRAFT")

    def test_untrusted_markdown_metadata_is_inert(self):
        doc = workboard.collect(StubAPI())
        doc["prs"][0]["title"] = "safe](https://example.invalid/phishing) ![remote](https://example.invalid/pixel) [rest"
        doc["issues"][0]["title"] = "<img src=x> *bold* [link](https://example.invalid/issue)"
        doc["issues"][0]["labels"] = ["<img src=x>", "[click](https://example.invalid/label)", "*bold*"]
        output = workboard.markdown(doc)
        self.assertIn(r"safe\]\(https://example\.invalid/phishing\)", output)
        self.assertIn(r"\!\[remote\]\(https://example\.invalid/pixel\)", output)
        self.assertIn("&lt;img src=x&gt;", output)
        self.assertIn(r"\[click\]\(https://example\.invalid/label\)", output)
        self.assertIn(r"\*bold\*", output)
        self.assertNotIn("](https://example.invalid/", output)
        self.assertNotIn("![remote]", output)
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
