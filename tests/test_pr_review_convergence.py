"""Adversarial tests of exact-head review-convergence metadata policy."""
import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from pr_review_convergence import EvidenceError, evaluate, REPO, SHA

HEAD = "a" * 40
OLD = "b" * 40
PR = {"number": 7, "draft": False, "head": {"sha": HEAD},
      "base": {"sha": OLD}, "user": {"login": "author", "type": "User"}}


def approval(user="reviewer", state="APPROVED", sha=HEAD, number=1, kind="User"):
    return {"id": number, "submitted_at": "2026-10-20T00:00:00Z",
            "state": state, "commit_id": sha,
            "user": {"login": user, "type": kind}}


def scan(reviews=None, threads=None, comments=None, pr=None):
    return evaluate(copy.deepcopy(PR) if pr is None else pr,
                    [] if reviews is None else reviews,
                    [] if threads is None else threads,
                    [] if comments is None else comments,
                    HEAD)


class ConvergenceTests(unittest.TestCase):
    def test_clean_exact_head_approval(self):
        result = scan([approval()])
        self.assertTrue(result["review_metadata_converged"])
        self.assertFalse(result["substantive_review_verified"])
        self.assertFalse(result["software_correctness_proven"])
        self.assertFalse(result["merge_authorization_verified"])

    def test_no_approval_fails(self):
        self.assertFalse(scan()["review_metadata_converged"])

    def test_stale_approval_does_not_pass(self):
        result = scan([approval(sha=OLD)])
        self.assertFalse(result["review_metadata_converged"])
        self.assertEqual(result["stale_or_nonhuman_approvals"], ["reviewer"])

    def test_bots_and_author_cannot_approve(self):
        result = scan([approval("author"), approval("bot", number=2, kind="Bot")])
        self.assertFalse(result["review_metadata_converged"])

    def test_commented_does_not_clear_changes_requested(self):
        first = approval(state="CHANGES_REQUESTED")
        second = approval(state="COMMENTED", number=2)
        second["submitted_at"] = "2026-10-21T00:00:00Z"
        result = scan([first, second])
        self.assertEqual(result["active_changes_requested"], ["reviewer"])

    def test_new_approval_clears_changes_requested(self):
        first = approval(state="CHANGES_REQUESTED")
        second = approval(number=2)
        second["submitted_at"] = "2026-10-21T00:00:00Z"
        self.assertTrue(scan([first, second])["review_metadata_converged"])

    def test_dismissed_approval_no_longer_counts(self):
        first = approval()
        second = approval(state="DISMISSED", number=2)
        second["submitted_at"] = "2026-10-21T00:00:00Z"
        self.assertFalse(scan([first, second])["review_metadata_converged"])

    def test_outdated_unresolved_thread_blocks(self):
        result = scan([approval()], [{"id": "t1", "resolved": False,
                                     "outdated": True, "root_comment_id": 9}])
        self.assertFalse(result["review_metadata_converged"])
        self.assertEqual(len(result["unresolved_threads"]), 1)

    def test_resolved_thread_not_blocking(self):
        self.assertTrue(scan([approval()], [{"id": "t1", "resolved": True,
                                             "outdated": False, "root_comment_id": 9}])
                        ["review_metadata_converged"])

    def test_exact_text_candidates_not_root_cause_claims(self):
        data = [{"id": 1, "path": "src/a.py", "body": "Bad invariant"},
                {"id": 2, "path": "src/a.py", "body": "  bad   invariant "},
                {"id": 3, "path": "src/b.py", "body": "bad invariant"}]
        result = scan([approval()], comments=data)
        self.assertEqual(len(result["exact_text_duplicate_candidates"]), 1)
        self.assertEqual(result["exact_text_duplicate_candidates"][0]["comment_ids"], [1, 2])


    def codex_comment(self, sha=HEAD, status="completed", unresolved=False,
                      author="chatgpt-codex-connector[bot]", app="chatgpt-codex-connector",
                      ident=1, updated="2026-10-20T00:00:00Z"):
        state = {"code_review": {"commit_sha": sha, "status": status,
                                 "has_unresolved_findings": unresolved}}
        return {"id": ident, "updated_at": updated,
                "user": {"login": author},
                "performed_via_github_app": {"slug": app},
                "body": "<!-- codex-review-state:v1 " + json.dumps(state) + " -->"}

    def test_authenticated_codex_clean_review_counts_for_metadata(self):
        result = evaluate(copy.deepcopy(PR), [], [], [], HEAD,
                          [self.codex_comment()])
        self.assertTrue(result["review_metadata_converged"])
        self.assertTrue(result["trusted_codex_review_on_exact_head"]["passed"])
        self.assertFalse(result["substantive_review_verified"])

    def test_spoofed_codex_comment_cannot_qualify(self):
        for kwargs in ({"author": "attacker"}, {"app": "attacker-app"}):
            result = evaluate(copy.deepcopy(PR), [], [], [], HEAD,
                              [self.codex_comment(**kwargs)])
            self.assertFalse(result["review_metadata_converged"])

    def test_codex_stale_running_or_unresolved_cannot_qualify(self):
        for kwargs in ({"sha": OLD}, {"status": "running", "unresolved": None},
                       {"unresolved": True}):
            result = evaluate(copy.deepcopy(PR), [], [], [], HEAD,
                              [self.codex_comment(**kwargs)])
            self.assertFalse(result["review_metadata_converged"])

    def test_later_codex_running_state_invalidates_earlier_completed(self):
        completed = self.codex_comment()
        running = self.codex_comment(status="running", unresolved=None, ident=2,
                                     updated="2026-10-21T00:00:00Z")
        result = evaluate(copy.deepcopy(PR), [], [], [], HEAD, [completed, running])
        self.assertFalse(result["review_metadata_converged"])

    def test_codex_review_does_not_override_unresolved_threads(self):
        result = evaluate(copy.deepcopy(PR), [], [
            {"id": "t", "resolved": False, "outdated": False, "root_comment_id": 4}
        ], [], HEAD, [self.codex_comment()])
        self.assertFalse(result["review_metadata_converged"])

    def test_head_drift_fails_closed(self):
        changed = copy.deepcopy(PR)
        changed["head"]["sha"] = OLD
        with self.assertRaises(EvidenceError):
            scan([approval()], pr=changed)

    def test_unknown_state_fails_closed(self):
        with self.assertRaises(EvidenceError):
            scan([approval(state="NOT_A_STATE")])

    def test_invalid_thread_fails_closed(self):
        with self.assertRaises(EvidenceError):
            scan([approval()], [{"id": "t", "resolved": "false"}])

    def test_draft_is_not_converged(self):
        changed = copy.deepcopy(PR)
        changed["draft"] = True
        self.assertFalse(scan([approval()], pr=changed)["review_metadata_converged"])

    def test_identity_restrictions(self):
        self.assertIsNone(REPO.fullmatch("../x"))
        self.assertIsNone(SHA.fullmatch("a" * 39))


if __name__ == "__main__":
    unittest.main()
