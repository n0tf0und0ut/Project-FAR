"""Adversarial tests of exact-head review-convergence metadata policy."""
import copy
import json
import sys
import unittest
import yaml
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

    def test_human_approval_cannot_mask_explicit_codex_unresolved_findings(self):
        result = evaluate(copy.deepcopy(PR), [approval()], [], [], HEAD,
                          [self.codex_comment(unresolved=True)])
        self.assertFalse(result["review_metadata_converged"])
        self.assertIn("authenticated exact-head Codex review reports unresolved findings",
                      result["blockers"])

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

    def test_pending_rerun_preserves_unresolved_codex_with_human_approval(self):
        first = self.codex_comment(unresolved=True)
        pending = self.codex_comment(status="running", unresolved=None, ident=2,
                                     updated="2026-10-21T00:00:00Z")
        result = evaluate(copy.deepcopy(PR), [approval()], [], [], HEAD,
                          [first, pending])
        self.assertFalse(result["review_metadata_converged"])
        self.assertTrue(result["trusted_codex_review_on_exact_head"]["unresolved"])
        self.assertIn("authenticated exact-head Codex review reports unresolved findings",
                      result["blockers"])
        self.assertIn("authenticated exact-head Codex review is incomplete",
                      result["blockers"])

    def test_pending_codex_alone_blocks_prior_human_approval(self):
        result = evaluate(copy.deepcopy(PR), [approval()], [], [], HEAD,
                          [self.codex_comment(status="running", unresolved=None)])
        self.assertFalse(result["review_metadata_converged"])

    def test_latest_completed_clean_review_supersedes_prior_unresolved(self):
        first = self.codex_comment(unresolved=True)
        done = self.codex_comment(unresolved=False, ident=3,
                                  updated="2026-10-21T00:00:00Z")
        record = evaluate(copy.deepcopy(PR), [], [], [], HEAD, [first, done])
        self.assertTrue(record["review_metadata_converged"])
        codex = record["trusted_codex_review_on_exact_head"]
        self.assertEqual(codex["source_comment_id"], 3)
        self.assertEqual(len(codex["review_state_sources"]), 2)
        self.assertFalse(codex["unresolved"])

    def test_ambiguous_double_codex_marker_fails_closed(self):
        comment = self.codex_comment(unresolved=False)
        comment["body"] += "\\n" + self.codex_comment(unresolved=True)["body"]
        with self.assertRaises(EvidenceError):
            evaluate(copy.deepcopy(PR), [], [], [], HEAD, [comment])

    def test_malformed_completed_codex_not_validated_by_human(self):
        comment = self.codex_comment(unresolved=None)
        with self.assertRaises(EvidenceError):
            evaluate(copy.deepcopy(PR), [approval()], [], [], HEAD, [comment])

    def test_review_metadata_preserves_source_ids_and_all_threads(self):
        threads = [{"id": "t1", "resolved": True, "outdated": False,
                    "root_comment_id": 11}]
        result = evaluate(copy.deepcopy(PR), [approval(number=42)], threads, [], HEAD, [])
        self.assertTrue(result["review_metadata_converged"])
        self.assertEqual(result["active_review_sources"][0]["review_id"], 42)
        self.assertEqual(result["active_review_sources"][0]["commit_id"], HEAD)
        self.assertEqual(result["all_thread_states"], threads)

    def test_additional_codex_html_comments_do_not_break_single_state(self):
        comment = self.codex_comment()
        comment["body"] += "\\n<!-- unrelated advisory note -->"
        result = evaluate(copy.deepcopy(PR), [], [], [], HEAD, [comment])
        self.assertTrue(result["review_metadata_converged"])

    def test_trusted_codex_summary_identifiers_are_reconstructible(self):
        comment = self.codex_comment(ident=789, updated="2026-10-25T02:00:00Z")
        result = evaluate(copy.deepcopy(PR), [], [], [], HEAD, [comment])
        code = result["trusted_codex_review_on_exact_head"]
        self.assertEqual(code["source_comment_id"], 789)
        self.assertEqual(code["updated_at"], "2026-10-25T02:00:00Z")

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

    def test_workflow_uses_supported_events_and_head_bound_check(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/pr-review-convergence.yml").read_text()
        self.assertNotIn("  pull_request_review_thread:", workflow)
        self.assertIn("  pull_request_review_comment:", workflow)
        self.assertIn("  schedule:", workflow)
        self.assertIn("  issue_comment:", workflow)
        self.assertIn("checks: write", workflow)
        self.assertNotIn('name: pr-review-convergence-observation', workflow)
        self.assertIn('name:"pr-review-convergence-scheduled-observation"', workflow)
        self.assertIn('--expected-head "$sha"', workflow)
        self.assertIn('current" == "$sha"', workflow)
        self.assertIn("ref: main", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertNotIn("ref: ${{ github.event.pull_request.head.sha }}", workflow)

    def test_polling_updates_review_state_without_re_requesting_reviews(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/pr-review-convergence.yml").read_text()
        self.assertIn("gh api --paginate", workflow)
        self.assertIn("pulls?state=open&base=main", workflow)
        self.assertIn("cancel-in-progress: true", workflow)
        self.assertNotIn("@codex review", workflow)
        self.assertNotIn("/requested_reviewers", workflow)

    def test_candidate_events_never_hold_a_write_token(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/pr-review-convergence.yml").read_text()
        publishing = workflow.split("  review-convergence:\n", 1)[1].split("  review-evidence:\n", 1)[0]
        observational = workflow.split("  review-evidence:\n", 1)[1]
        self.assertIn("checks: write", publishing)
        self.assertIn("if: (github.event_name == 'schedule' && github.ref == 'refs/heads/main') || (github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main')",
                      publishing)
        self.assertNotIn("checks: write", observational)
        self.assertIn("pull-requests: read", observational)
        self.assertIn("--mode report", observational)
        self.assertIn("--mode enforce", publishing)

    def test_identity_restrictions(self):
        self.assertIsNone(REPO.fullmatch("../x"))
        self.assertIsNone(SHA.fullmatch("a" * 39))

    def assert_required_workflow_boundary(self, workflow):
        jobs = workflow["jobs"]
        job = jobs["required-review"]
        self.assertEqual(job["name"], "pr-review-convergence-observation")
        self.assertEqual(set(workflow["on"]), {"pull_request"})
        self.assertEqual(workflow["on"]["pull_request"]["branches"], ["main"])
        self.assertNotIn("if", job)
        # No dependency may turn failure of another job into a skipped success.
        self.assertNotIn("needs", job)
        self.assertNotIn("strategy", job)
        self.assertEqual(job["permissions"], {"contents": "read", "pull-requests": "read", "issues": "read"})
        checkout = next(step for step in job["steps"] if step.get("uses", "").startswith("actions/checkout@"))
        self.assertEqual(checkout["with"]["ref"], "main")
        self.assertEqual(checkout["with"]["persist-credentials"], "false")
        script = next(step for step in job["steps"] if "run" in step)
        self.assertEqual(script["env"]["EVENT_HEAD"], "${{ github.event.pull_request.head.sha }}")
        self.assertIn('"$sha" == "$EVENT_HEAD"', script["run"])
        self.assertIn('"$current" == "$sha"', script["run"])
        self.assertIn('--expected-head "$sha"', script["run"])
        self.assertIn("--mode enforce", script["run"])
        self.assertNotIn("gh api --method POST", script["run"])

    def test_required_check_is_a_native_eligible_read_only_job(self):
        path = Path(__file__).resolve().parents[1] / ".github/workflows/required-pr-review-convergence.yml"
        self.assert_required_workflow_boundary(yaml.load(path.read_text(), Loader=yaml.BaseLoader))
        advisory = path.with_name("pr-review-convergence.yml")
        other_jobs = yaml.load(advisory.read_text(), Loader=yaml.BaseLoader)["jobs"]
        self.assertFalse(any(job.get("name") == "pr-review-convergence-observation"
                             for job in other_jobs.values()))

    def test_required_job_rejects_ineligible_event_or_privileged_candidate_mutations(self):
        path = Path(__file__).resolve().parents[1] / ".github/workflows/required-pr-review-convergence.yml"
        source = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
        for mutation in ("event", "review_event", "permissions", "checkout", "head", "dependency"):
            with self.subTest(mutation=mutation):
                changed = copy.deepcopy(source)
                job = changed["jobs"]["required-review"]
                if mutation == "event":
                    changed["on"] = {"schedule": [{"cron": "13 * * * *"}]}
                elif mutation == "review_event":
                    changed["on"]["pull_request_review"] = {"types": ["submitted"]}
                elif mutation == "permissions":
                    job["permissions"]["checks"] = "write"
                elif mutation == "checkout":
                    job["steps"][0]["with"]["ref"] = "${{ github.event.pull_request.head.sha }}"
                elif mutation == "head":
                    job["steps"][1]["run"] = job["steps"][1]["run"].replace('[[ "$sha" == "$EVENT_HEAD" ]]', "true")
                else:
                    job["needs"] = "discover"
                with self.assertRaises(AssertionError):
                    self.assert_required_workflow_boundary(changed)


if __name__ == "__main__":
    unittest.main()
