import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools import run_living_research_promotion_ci as ci


HEAD = "1" * 40
BRANCH = "automation/living-promotion-" + "2" * 40 + "-" + "3" * 40
REPO = "notfoundout/Project-FAR"


class PromotionCIAdapterTests(unittest.TestCase):
    def test_token_env_injects_only_requested_token_and_drops_legacy_token(self):
        with patch.dict(os.environ, {"GH_TOKEN": "ambient", ci.core.PR_TOKEN_ENV: "legacy"}, clear=False):
            env = ci._token_env("bounded")
        self.assertEqual("bounded", env["GH_TOKEN"])
        self.assertNotIn(ci.core.PR_TOKEN_ENV, env)

    def test_safe_local_push_config_accepts_only_canonical_origin(self):
        def git(*args):
            if args == ("config", "--local", "--name-only", "--list"):
                return "core.repositoryformatversion\nremote.origin.url\nuser.name\nuser.email\n"
            if args == ("config", "--local", "--get-all", "remote.origin.url"):
                return "https://github.com/notfoundout/Project-FAR\n"
            raise AssertionError(args)

        with patch.dict(os.environ, {"GITHUB_REPOSITORY": REPO}, clear=False):
            ci._assert_safe_local_push_config(git)

    def test_safe_local_push_config_rejects_redirect_or_injection_keys(self):
        def git(*args):
            if args == ("config", "--local", "--name-only", "--list"):
                return "remote.origin.url\nurl.https://evil.invalid/.insteadof\ncore.hooksPath\n"
            raise AssertionError(args)

        with patch.dict(os.environ, {"GITHUB_REPOSITORY": REPO}, clear=False):
            with self.assertRaisesRegex(ci.AdapterError, "unsafe local Git configuration"):
                ci._assert_safe_local_push_config(git)

    def test_existing_successful_merge_authority_suppresses_duplicate_dispatch(self):
        pr = {"state": "OPEN", "baseRefName": "main", "headRefName": BRANCH, "headRefOid": HEAD}
        with (
            patch.dict(os.environ, {"GITHUB_REPOSITORY": REPO}, clear=False),
            patch.object(ci, "_remote_head", return_value=HEAD),
            patch.object(ci, "_check_runs", return_value=[{"status": "completed", "conclusion": "success"}]),
            patch.object(ci.core, "run", return_value=SimpleNamespace(stdout=json.dumps(pr), returncode=0)) as run,
            patch.object(ci, "_validator_runs") as validator_runs,
        ):
            ci.ensure_merge_authority(BRANCH, 700, "token")
        run.assert_called_once()
        validator_runs.assert_not_called()

    def test_existing_active_merge_authority_suppresses_duplicate_dispatch(self):
        pr = {"state": "OPEN", "baseRefName": "main", "headRefName": BRANCH, "headRefOid": HEAD}
        with (
            patch.dict(os.environ, {"GITHUB_REPOSITORY": REPO}, clear=False),
            patch.object(ci, "_remote_head", return_value=HEAD),
            patch.object(ci, "_check_runs", return_value=[{"status": "in_progress", "conclusion": None}]),
            patch.object(ci.core, "run", return_value=SimpleNamespace(stdout=json.dumps(pr), returncode=0)) as run,
            patch.object(ci, "_validator_runs") as validator_runs,
        ):
            ci.ensure_merge_authority(BRANCH, 700, "token")
        run.assert_called_once()
        validator_runs.assert_not_called()

    def test_existing_failed_merge_authority_fails_closed_without_redispatch(self):
        pr = {"state": "OPEN", "baseRefName": "main", "headRefName": BRANCH, "headRefOid": HEAD}
        with (
            patch.dict(os.environ, {"GITHUB_REPOSITORY": REPO}, clear=False),
            patch.object(ci, "_remote_head", return_value=HEAD),
            patch.object(ci, "_check_runs", return_value=[{"status": "completed", "conclusion": "failure"}]),
            patch.object(ci.core, "run", return_value=SimpleNamespace(stdout=json.dumps(pr), returncode=0)) as run,
            patch.object(ci, "_validator_runs") as validator_runs,
        ):
            with self.assertRaisesRegex(ci.AdapterError, "refusing automatic rerun"):
                ci.ensure_merge_authority(BRANCH, 700, "token")
        run.assert_called_once()
        validator_runs.assert_not_called()

    def test_pr_exact_head_mismatch_fails_before_check_or_dispatch(self):
        pr = {"state": "OPEN", "baseRefName": "main", "headRefName": BRANCH, "headRefOid": "4" * 40}
        with (
            patch.dict(os.environ, {"GITHUB_REPOSITORY": REPO}, clear=False),
            patch.object(ci, "_remote_head", return_value=HEAD),
            patch.object(ci.core, "run", return_value=SimpleNamespace(stdout=json.dumps(pr), returncode=0)),
            patch.object(ci, "_check_runs") as checks,
        ):
            with self.assertRaisesRegex(ci.AdapterError, "exact-head invariant failed"):
                ci.ensure_merge_authority(BRANCH, 700, "token")
        checks.assert_not_called()

    def test_queued_workflow_without_a_check_run_suppresses_duplicate_dispatch(self):
        pr = {"state": "OPEN", "baseRefName": "main", "headRefName": BRANCH, "headRefOid": HEAD}
        for status in ("queued", "in_progress", "waiting", "requested", "pending"):
            with (
                self.subTest(status=status),
                patch.dict(os.environ, {"GITHUB_REPOSITORY": REPO}, clear=False),
                patch.object(ci, "_remote_head", return_value=HEAD),
                patch.object(ci, "_check_runs", return_value=[]),
                patch.object(ci, "_validator_runs", return_value=[
                    {"databaseId": 10, "headSha": HEAD, "status": status, "conclusion": None}
                ]),
                patch.object(ci.core, "run", return_value=SimpleNamespace(stdout=json.dumps(pr), returncode=0)) as run,
                patch.object(ci.time, "sleep"),
            ):
                ci.ensure_merge_authority(BRANCH, 700, "token")
                run.assert_called_once()

    def test_failed_workflow_without_a_check_run_is_not_automatically_retried(self):
        pr = {"state": "OPEN", "baseRefName": "main", "headRefName": BRANCH, "headRefOid": HEAD}
        with (
            patch.dict(os.environ, {"GITHUB_REPOSITORY": REPO}, clear=False),
            patch.object(ci, "_remote_head", return_value=HEAD),
            patch.object(ci, "_check_runs", return_value=[]),
            patch.object(ci, "_validator_runs", return_value=[
                {"databaseId": 10, "headSha": HEAD, "status": "completed", "conclusion": "failure"}
            ]),
            patch.object(ci.core, "run", return_value=SimpleNamespace(stdout=json.dumps(pr), returncode=0)) as run,
            patch.object(ci.time, "sleep"),
        ):
            with self.assertRaisesRegex(ci.AdapterError, "refusing automatic rerun"):
                ci.ensure_merge_authority(BRANCH, 700, "token")
        run.assert_called_once()

    def test_absent_authority_dispatches_validator_and_binds_new_exact_head_run(self):
        pr = {"state": "OPEN", "baseRefName": "main", "headRefName": BRANCH, "headRefOid": HEAD}
        before = [{"databaseId": 10, "headSha": HEAD, "status": "completed", "conclusion": "success"}]
        after = before + [{"databaseId": 11, "headSha": HEAD, "status": "queued", "conclusion": None}]
        with (
            patch.dict(os.environ, {"GITHUB_REPOSITORY": REPO}, clear=False),
            patch.object(ci, "_remote_head", return_value=HEAD),
            patch.object(ci, "_check_runs", return_value=[]),
            patch.object(ci, "_validator_runs", side_effect=[before, after]),
            patch.object(ci.time, "sleep"),
            patch.object(ci.core, "run", side_effect=[
                SimpleNamespace(stdout=json.dumps(pr), returncode=0),
                SimpleNamespace(stdout="", returncode=0),
            ]) as run,
        ):
            ci.ensure_merge_authority(BRANCH, 700, "token")
        self.assertEqual(2, run.call_count)
        dispatch_args = run.call_args_list[1].args
        self.assertEqual(("gh", "workflow", "run", ci.VALIDATOR_WORKFLOW, "--repo", REPO, "--ref", BRANCH), dispatch_args)

    def test_dispatch_must_materialize_as_a_new_exact_head_run(self):
        pr = {"state": "OPEN", "baseRefName": "main", "headRefName": BRANCH, "headRefOid": HEAD}
        existing = [{"databaseId": 10, "headSha": HEAD, "status": "completed", "conclusion": "success"}]
        with (
            patch.dict(os.environ, {"GITHUB_REPOSITORY": REPO}, clear=False),
            patch.object(ci, "_remote_head", return_value=HEAD),
            patch.object(ci, "_check_runs", return_value=[]),
            patch.object(ci, "_validator_runs", side_effect=[existing] + [existing] * 20),
            patch.object(ci.time, "sleep"),
            patch.object(ci.core, "run", side_effect=[
                SimpleNamespace(stdout=json.dumps(pr), returncode=0),
                SimpleNamespace(stdout="", returncode=0),
            ]),
        ):
            with self.assertRaisesRegex(ci.AdapterError, "no new exact-head run appeared"):
                ci.ensure_merge_authority(BRANCH, 700, "token")


if __name__ == "__main__":
    unittest.main()
