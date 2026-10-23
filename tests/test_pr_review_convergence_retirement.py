"""Adversarial tests for a name-only, manually dispatched legacy publication repair."""
import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import retire_legacy_review_publications as repair

SOURCE = "a" * 40


def check(ident, name, app=15368, run=None, outcome="success"):
    url = (f"https://github.com/{repair.REPOSITORY}/actions/runs/{run}/job/{ident}"
           if run else f"https://github.com/{repair.REPOSITORY}/runs/{ident}")
    return {"id": ident, "name": name, "head_sha": repair.TARGET,
            "status": "completed", "conclusion": outcome, "app": {"id": app},
            "details_url": url, "started_at": "2026-10-23T22:34:32Z",
            "completed_at": "2026-10-23T22:34:32Z",
            "output": {"title": "Original result", "summary": "Original failure evidence"}}


class FakeClient:
    def __init__(self):
        self.branch = {"commit": {"sha": repair.MAIN}, "protected": True,
                       "protection": {"required_status_checks": {
                           "enforcement_level": "everyone", "checks": [
                               {"context": repair.REQUIRED, "app_id": 15368},
                               {"context": "merge-authority", "app_id": 15368},
                               {"context": "protected-repin-gate", "app_id": 5073230}]}}}
        self.pr = {"number": 578, "head": {"sha": repair.TARGET}, "state": "open", "draft": False,
                   "base": {"sha": repair.MAIN, "ref": "main"}}
        self.authorizations = [{"id": 6000, "number": 591, "draft": False,
                                "head": {"sha": SOURCE, "ref": repair.REPAIR_BRANCH,
                                         "repo": {"full_name": repair.REPOSITORY}},
                                "base": {"sha": repair.TARGET, "ref": repair.TARGET_BRANCH}}]
        self.checks = [check(1001, repair.REQUIRED, run=501),
                       check(1002, "merge-authority", run=502),
                       check(1003, "exact-head-assurance", run=503),
                       check(1004, "protected-repin-gate", app=5073230),
                       check(2000, repair.REQUIRED, outcome="failure")]
        self.runs, self.jobs = {}, {}
        for ident, run_id, name in ((1001, 501, repair.REQUIRED), (1002, 502, "merge-authority"),
                                    (1003, 503, "exact-head-assurance")):
            self.runs[run_id] = {"id": run_id, "head_sha": repair.TARGET, "event": "pull_request",
                                 "path": repair.GATES[name][1], "status": "completed", "conclusion": "success"}
            self.jobs[run_id] = [{"id": ident, "name": name, "status": "completed", "conclusion": "success"}]
        self.schedules = [{"id": 700, "head_sha": repair.MAIN, "event": "schedule",
                           "head_branch": "main", "path": ".github/workflows/pr-review-convergence.yml"}]
        self.jobs[700] = [{"id": 701, "name": "review-convergence (578)",
                           "status": "completed", "conclusion": "failure"}]
        self.logs = {701: "2026-10-23T22:34:33Z " + json.dumps(self.checks[-1], separators=(",", ":"))}
        self.writes, self.reads = [], []
        self.alter_result = False
        self.drift_after_read = False
        self.identity_reads = 0

    def get(self, path):
        self.reads.append(path)
        route, _, query = path.removeprefix(repair.ROOT).partition("?")
        if route == "/branches/main":
            self.identity_reads += 1
            result = copy.deepcopy(self.branch)
            if self.drift_after_read and self.identity_reads > 1:
                result["commit"]["sha"] = "b" * 40
            return result
        if route == "/pulls/578":
            return copy.deepcopy(self.pr)
        if route == "/pulls":
            return copy.deepcopy(self.authorizations)
        if route == "/commits/" + repair.TARGET + "/check-runs":
            return {"check_runs": copy.deepcopy(self.checks)}
        if route == "/actions/runs":
            return {"workflow_runs": copy.deepcopy(self.schedules)}
        if route.startswith("/actions/runs/"):
            run_id = int(route.split("/")[3])
            return {"jobs": copy.deepcopy(self.jobs[run_id])} if route.endswith("/jobs") else copy.deepcopy(self.runs[run_id])
        if route.startswith("/check-runs/"):
            ident = int(route.rsplit("/", 1)[1])
            return copy.deepcopy(next(x for x in self.checks if x["id"] == ident))
        raise AssertionError(path)

    def log(self, job):
        return self.logs[job]

    def rename(self, ident):
        self.writes.append({"check_id": ident, "body": {"name": repair.ADVISORY}})
        item = next(x for x in self.checks if x["id"] == ident)
        item["name"] = repair.ADVISORY
        if self.alter_result:
            item["conclusion"] = "success"
        return copy.deepcopy(item)


def reviewer(number, head, directory):
    return {"pr_number": number, "exact_head_sha": head, "review_metadata_converged": True, "draft": False}


class RetirementTests(unittest.TestCase):
    def execute(self, client, apply=True, review=reviewer):
        with tempfile.TemporaryDirectory() as directory:
            return repair.execute(client, SOURCE, Path(directory), apply=apply, reviewer=review)

    def assert_no_write(self, client, review=reviewer):
        with self.assertRaises((repair.RepairError, KeyError, ValueError)):
            self.execute(client, review=review)
        self.assertEqual(client.writes, [])

    def test_name_only_repair_preserves_failure_and_all_result_evidence(self):
        client = FakeClient()
        before = repair.fingerprint(client.checks[-1])
        report = self.execute(client)
        self.assertEqual(client.writes, [{"check_id": 2000, "body": {"name": repair.ADVISORY}}])
        self.assertEqual(repair.fingerprint(client.checks[-1]), before)
        self.assertEqual(client.checks[-1]["conclusion"], "failure")
        self.assertFalse(report["conclusions_modified"])
        self.assertFalse(report["protection_modified"])
        self.assertFalse(report["merge_performed"])
        self.assertEqual(report["plan"][0]["source"], {"run_id": 700, "job_id": 701})

    def test_default_plan_mode_never_writes(self):
        client = FakeClient()
        report = self.execute(client, apply=False)
        self.assertEqual(client.writes, [])
        self.assertEqual(report["renamed_check_ids"], [])
        self.assertEqual(len(report["plan"]), 1)

    def test_successful_advisory_also_retains_its_original_result(self):
        client = FakeClient()
        client.checks[-1]["conclusion"] = "success"
        client.logs[701] = "2026-10-23T22:34:33Z " + json.dumps(client.checks[-1], separators=(",", ":"))
        self.execute(client)
        self.assertEqual(client.checks[-1]["conclusion"], "success")

    def test_main_head_draft_and_protection_changes_block_every_write(self):
        mutations = [lambda c: c.branch["commit"].update(sha="b" * 40),
                     lambda c: c.pr["head"].update(sha="b" * 40),
                     lambda c: c.pr.update(draft=True),
                     lambda c: c.branch.update(protected=False),
                     lambda c: c.branch["protection"]["required_status_checks"].update(enforcement_level="non_admins"),
                     lambda c: c.branch["protection"]["required_status_checks"]["checks"].pop()]
        for mutation in mutations:
            client = FakeClient()
            mutation(client)
            with self.subTest(mutation=mutation):
                self.assert_no_write(client)

    def test_source_review_must_be_unique_exact_and_from_the_canonical_branch(self):
        for mutation in (lambda c: c.authorizations.clear(),
                         lambda c: c.authorizations.append(copy.deepcopy(c.authorizations[0])),
                         lambda c: c.authorizations[0]["head"].update(sha="b" * 40),
                         lambda c: c.authorizations[0]["head"]["repo"].update(full_name="attacker/fork"),
                         lambda c: c.authorizations[0]["base"].update(sha="b" * 40)):
            client = FakeClient()
            mutation(client)
            self.assert_no_write(client)

    def test_review_failure_of_either_operation_or_target_blocks_all_writes(self):
        for fail_pr in (591, 578):
            def failed(number, head, directory):
                if number == fail_pr:
                    raise repair.RepairError("review incomplete")
                return reviewer(number, head, directory)
            self.assert_no_write(FakeClient(), failed)

    def test_every_engineering_gate_is_mandatory_on_the_exact_head(self):
        for index in range(4):
            for field, value in (("conclusion", "failure"), ("head_sha", "b" * 40),
                                 ("status", "in_progress"), ("app", {"id": 9})):
                client = FakeClient()
                client.checks[index][field] = value
                with self.subTest(index=index, field=field):
                    self.assert_no_write(client)

    def test_new_failed_native_job_cannot_be_masked_by_an_older_success(self):
        client = FakeClient()
        client.checks.append(check(1100, repair.REQUIRED, run=599, outcome="failure"))
        self.assert_no_write(client)

    def test_native_gate_provenance_excludes_schedule_and_wrong_workflow(self):
        for field, value in (("event", "schedule"), ("path", ".github/workflows/other.yml"),
                             ("head_sha", "b" * 40), ("conclusion", "failure")):
            client = FakeClient()
            client.runs[501][field] = value
            self.assert_no_write(client)
        client = FakeClient()
        client.checks[0]["details_url"] = f"https://github.com/{repair.REPOSITORY}/actions/runs/501/job/9999"
        self.assert_no_write(client)

    def test_mismatched_missing_or_only_quoted_publication_receipts_fail_closed(self):
        duplicate = ("2026-10-23T22:34:33Z " + json.dumps(FakeClient().checks[-1], separators=(",", ":")))
        duplicate = duplicate.replace('{"id":2000,', '{"id":9,"id":2000,')
        for log in ("no receipt", '{"id":2000,"name":"other"}', duplicate,
                    json.dumps(FakeClient().checks[-1]).replace('"failure"', '"success"'),
                    "> " + json.dumps(FakeClient().checks[-1])):
            client = FakeClient()
            client.logs[701] = log
            self.assert_no_write(client)

    def test_only_protected_main_scheduled_publisher_can_supply_the_proof(self):
        for field, value in (("head_sha", "b" * 40), ("event", "workflow_dispatch"),
                             ("path", ".github/workflows/other.yml"), ("head_branch", "candidate")):
            client = FakeClient()
            client.schedules[0][field] = value
            self.assert_no_write(client)
        client = FakeClient()
        client.jobs[700][0]["name"] = "other"
        self.assert_no_write(client)

    def test_unproved_second_record_prevents_even_the_first_write(self):
        client = FakeClient()
        client.checks.append(check(2001, repair.REQUIRED, outcome="failure"))
        self.assert_no_write(client)

    def test_native_foreign_app_and_other_head_checks_are_never_renamed(self):
        client = FakeClient()
        client.checks.append(check(2001, repair.REQUIRED, app=9, outcome="failure"))
        stale = check(2002, repair.REQUIRED, outcome="failure")
        stale["head_sha"] = "b" * 40
        client.checks.append(stale)
        self.execute(client)
        self.assertEqual([x["check_id"] for x in client.writes], [2000])

    def test_readback_detects_any_result_change(self):
        client = FakeClient()
        client.alter_result = True
        with self.assertRaises(repair.RepairError):
            self.execute(client)

    def test_head_movement_after_preflight_blocks_first_write(self):
        client = FakeClient()
        client.drift_after_read = True
        self.assert_no_write(client)

    def test_review_preflight_runs_fixed_collector_and_rejects_draft_or_false_output(self):
        for change in ({}, {"draft": True}, {"review_metadata_converged": False},
                       {"exact_head_sha": "b" * 40}):
            with tempfile.TemporaryDirectory() as directory:
                record = reviewer(578, repair.TARGET, directory)
                record.update(change)
                def process(command, **kwargs):
                    self.assertEqual(command[2:6], ["--repository", repair.REPOSITORY, "--pr", "578"])
                    self.assertTrue(command[1].endswith("/pr_review_convergence.py"))
                    self.assertEqual(kwargs, {"check": True, "timeout": 180})
                    Path(command[command.index("--output") + 1]).write_text(json.dumps(record))
                with patch.object(repair.subprocess, "run", side_effect=process):
                    if change:
                        with self.assertRaises(repair.RepairError):
                            repair.check_review(578, repair.TARGET, Path(directory))
                    else:
                        self.assertEqual(repair.check_review(578, repair.TARGET, Path(directory)), record)

    def test_cli_refuses_nonmanual_or_unbound_source_before_creating_a_client(self):
        with tempfile.TemporaryDirectory() as directory:
            for field, bad in (("GITHUB_EVENT_NAME", "pull_request"), ("GITHUB_REPOSITORY", "attacker/fork"),
                               ("GITHUB_REF", "refs/heads/main"), ("GITHUB_SHA", "b" * 40)):
                env = {"GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REPOSITORY": repair.REPOSITORY,
                       "GITHUB_REF": "refs/heads/" + repair.REPAIR_BRANCH, "GITHUB_SHA": SOURCE, "GH_TOKEN": "synthetic"}
                env[field] = bad
                with patch.dict(os.environ, env), patch.object(repair, "Client") as client:
                    with self.assertRaises(SystemExit):
                        repair.main(["--source-sha", SOURCE, "--output", directory + "/result.json", "--apply"])
                    client.assert_not_called()


class Response(io.BytesIO):
    pass


class TransportTests(unittest.TestCase):
    def test_patch_body_contains_only_the_advisory_name(self):
        client = repair.Client("synthetic")
        with patch.object(client.opener, "open", return_value=Response(b'{}')) as opened:
            client.rename(2000)
        request = opened.call_args.args[0]
        self.assertEqual(request.method, "PATCH")
        self.assertEqual(request.full_url, "https://api.github.com" + repair.ROOT + "/check-runs/2000")
        self.assertEqual(json.loads(request.data), {"name": repair.ADVISORY})

    def test_log_redirect_strips_authorization_and_binds_the_download_host(self):
        client = repair.Client("synthetic")
        redirect = urllib.error.HTTPError("https://api.github.com/logs", 302, "redirect",
                                         {"Location": "https://logs.blob.core.windows.net/path?sig=private"}, None)
        with patch.object(client.opener, "open", side_effect=[redirect, Response(b"public job log")]) as opened:
            self.assertEqual(client.log(701), "public job log")
        first, second = [call.args[0] for call in opened.call_args_list]
        self.assertEqual(first.get_header("Authorization"), "Bearer synthetic")
        self.assertIsNone(second.get_header("Authorization"))
        self.assertIsNone(repair.NoRedirect().redirect_request(first, None, 302, "", {}, second.full_url))

    def test_untrusted_redirect_never_receives_a_request(self):
        for url in ("http://logs.blob.core.windows.net/x", "https://attacker.example/x",
                    "https://user:secret@logs.blob.core.windows.net/x"):
            client = repair.Client("synthetic")
            redirect = urllib.error.HTTPError("https://api.github.com/logs", 302, "redirect", {"Location": url}, None)
            with patch.object(client.opener, "open", side_effect=redirect) as opened:
                with self.assertRaises(repair.RepairError):
                    client.log(701)
                self.assertEqual(opened.call_count, 1)


if __name__ == "__main__":
    unittest.main()
