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
import hashlib
import subprocess
import yaml

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
        operation = check(3001, "convergence-contract", run=801)
        operation["head_sha"] = SOURCE
        self.operation_checks = [operation]
        self.runs[801] = {"id": 801, "head_sha": SOURCE, "event": "pull_request", "status": "completed",
                          "path": ".github/workflows/pr-review-convergence-contract.yml", "conclusion": "success"}
        self.jobs[801] = [{"id": 3001, "name": "convergence-contract", "status": "completed", "conclusion": "success"}]
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
        if route == "/commits/" + SOURCE + "/check-runs":
            return {"check_runs": copy.deepcopy(self.operation_checks)}
        if route == "/actions/workflows/pr-review-convergence.yml/runs":
            params = dict(pair.split("=", 1) for pair in query.split("&") if "=" in pair)
            page = int(params.get("page", "1"))
            return {"workflow_runs": copy.deepcopy(self.schedules[(page-1)*100:page*100])}
        if route.startswith("/actions/runs/"):
            run_id = int(route.split("/")[3])
            if route.endswith("/jobs"):
                jobs = self.jobs[run_id]
                # Mimic GitHub's default newest attempt, and its explicit
                # filter=all historical proof enumeration.
                filtered = jobs if "filter=all" in query else jobs[-1:]
                return {"jobs": copy.deepcopy(filtered)}
            return copy.deepcopy(self.runs[run_id])
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

    def test_repair_source_requires_its_own_exact_head_native_contract_test(self):
        for mutation in (lambda c: c.operation_checks.clear(),
                         lambda c: c.operation_checks[0].update(conclusion="failure"),
                         lambda c: c.runs[801].update(head_sha="b" * 40)):
            client = FakeClient()
            mutation(client)
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

    def test_publisher_scoped_pagination_finds_old_receipt_on_page_three(self):
        client = FakeClient()
        originals = copy.deepcopy(client.schedules)
        client.schedules = [
            {"id": 3000 + i, "head_sha": "b" * 40,
             "head_branch": "main", "event": "schedule",
             "path": ".github/workflows/pr-review-convergence.yml"}
            for i in range(200)] + originals
        result = self.execute(client)
        self.assertEqual(result["renamed_check_ids"], [2000])
        self.assertTrue(any("/actions/workflows/pr-review-convergence.yml/runs?"
                            in path and "page=3" in path for path in client.reads))
        self.assertFalse(any(path.startswith(repair.ROOT + "/actions/runs?event=schedule")
                             for path in client.reads))

    def test_partial_patch_preserves_write_ahead_journal_and_reconciles_retry(self):
        client = FakeClient()
        original_get = client.get

        def fail_postpatch_readback(path):
            if path.endswith("/check-runs/2000") and client.writes:
                raise OSError("simulated connection loss after successful PATCH")
            return original_get(path)

        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            client.get = fail_postpatch_readback
            with self.assertRaises(OSError):
                repair.execute(client, SOURCE, directory, apply=True, reviewer=reviewer)
            journal_path = directory / "legacy-review-name-repair.json"
            self.assertTrue(journal_path.exists())
            journal = json.loads(journal_path.read_text())
            self.assertEqual(journal["state"], "INCOMPLETE")
            self.assertEqual(journal["error_type"], "OSError")
            self.assertEqual(journal["operations"][0]["state"], "PATCH_RETURNED")
            self.assertEqual(journal["plan"][0]["check_id"], 2000)
            self.assertEqual(client.checks[-1]["name"], repair.ADVISORY)
            self.assertEqual(client.checks[-1]["conclusion"], "failure")
            client.get = original_get
            recovered = repair.execute(client, SOURCE, directory, apply=True, reviewer=reviewer)
            self.assertEqual(recovered["state"], "COMPLETE")
            self.assertEqual(recovered["plan"][0]["old_name"], repair.ADVISORY)
            self.assertEqual(recovered["operations"][0]["state"],
                             "PREVIOUSLY_RENAMED_VERIFIED")
            self.assertEqual(len(client.writes), 1)

    def test_journal_write_failure_prevents_first_patch(self):
        client = FakeClient()
        with tempfile.TemporaryDirectory() as folder, patch.object(
                repair, "persist_journal", side_effect=OSError("unwritable journal")):
            with self.assertRaises(OSError):
                repair.execute(client, SOURCE, Path(folder), apply=True, reviewer=reviewer)
        self.assertEqual(client.writes, [])

    def test_scheduled_publisher_rerun_proof_in_earlier_attempt(self):
        client = FakeClient()
        # The original publication is in attempt 1 job 701. A later attempt
        # returns only job 702 through GitHub's default jobs endpoint.
        client.jobs[700].append({"id": 702, "name": "review-convergence (578)",
                                 "status": "completed", "conclusion": "failure"})
        client.logs[702] = "no matching publication"
        result = self.execute(client)
        self.assertEqual(result["plan"][0]["source"], {"run_id": 700, "job_id": 701})
        self.assertTrue(any("/actions/runs/700/jobs?filter=all" in url for url in client.reads))
        self.assertEqual([x["check_id"] for x in client.writes], [2000])

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
            for field, bad in (("GITHUB_EVENT_NAME", "pull_request"), ("GITHUB_EVENT_NAME", "push"),
                               ("GITHUB_REPOSITORY", "attacker/fork"),
                               ("GITHUB_REF", "refs/heads/main"), ("GITHUB_SHA", "b" * 40)):
                env = {"GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REPOSITORY": repair.REPOSITORY,
                       "GITHUB_REF": "refs/heads/" + repair.REPAIR_BRANCH, "GITHUB_SHA": SOURCE,
                       "GITHUB_RUN_ATTEMPT": "1", "GH_TOKEN": "synthetic"}
                env[field] = bad
                with patch.dict(os.environ, env), patch.object(repair, "Client") as client:
                    with self.assertRaises(SystemExit):
                        repair.main(["--source-sha", SOURCE, "--output", directory + "/result.json", "--apply"])
                    client.assert_not_called()

    def test_explicit_push_retry_can_reach_preflight_with_the_exact_source(self):
        env = {"GITHUB_EVENT_NAME": "push", "GITHUB_REPOSITORY": repair.REPOSITORY,
               "GITHUB_REF": "refs/heads/" + repair.REPAIR_BRANCH, "GITHUB_SHA": SOURCE,
               "GITHUB_RUN_ATTEMPT": "2", "GH_TOKEN": "synthetic"}
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, env), \
                patch.object(repair, "Client", return_value="fake-client"), \
                patch.object(repair, "execute", return_value={"applied": True}) as execute:
            self.assertEqual(repair.main(["--source-sha", SOURCE, "--output", directory + "/result.json", "--apply"]), 0)
            self.assertEqual(execute.call_args.args[:2], ("fake-client", SOURCE))
            self.assertTrue(execute.call_args.kwargs["apply"])


class Response(io.BytesIO):
    pass


class TransportTests(unittest.TestCase):
    def test_final_cli_output_preserves_prior_journal_on_replace_failure(self):
        report = {"schema": "far-legacy-review-name-repair/1", "state": "COMPLETE",
                  "operations": [{"check_id": 2000, "state": "READBACK_VERIFIED"}]}
        env = {"GITHUB_EVENT_NAME": "workflow_dispatch", "GITHUB_REPOSITORY": repair.REPOSITORY,
               "GITHUB_REF": "refs/heads/" + repair.REPAIR_BRANCH, "GITHUB_SHA": SOURCE,
               "GITHUB_RUN_ATTEMPT": "2", "GH_TOKEN": "synthetic"}
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "legacy-review-name-repair.json"
            before = '{"state":"PREPARED","operations":[{"check_id":2000,"state":"PATCH_RETURNED"}]}\n'
            target.write_text(before)
            with patch.dict(os.environ, env), patch.object(repair, "Client", return_value="fake"), \
                    patch.object(repair, "execute", return_value=report), \
                    patch.object(repair.os, "replace", side_effect=OSError("simulated atomic swap failure")):
                result = repair.main(["--source-sha", SOURCE, "--output", str(target), "--apply"])
            self.assertEqual(result, 2)
            self.assertEqual(target.read_text(), before)
            with patch.dict(os.environ, env), patch.object(repair, "Client", return_value="fake"), \
                    patch.object(repair, "execute", return_value=report):
                result = repair.main(["--source-sha", SOURCE, "--output", str(target), "--apply"])
            self.assertEqual(result, 0)
            self.assertEqual(json.loads(target.read_text()), report)

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


class ManualWorkflowTests(unittest.TestCase):
    def workflow(self):
        path = Path(__file__).resolve().parents[1] / ".github/workflows/pr-review-convergence.yml"
        return yaml.load(path.read_text(), Loader=yaml.BaseLoader)

    def boundary(self, workflow):
        jobs = workflow["jobs"]
        read = jobs["legacy-review-activation"]
        write = jobs["legacy-review-retirement"]
        self.assertEqual(workflow["on"]["push"]["branches"], [repair.REPAIR_BRANCH])
        common = "github.ref == 'refs/heads/" + repair.REPAIR_BRANCH + "'"
        self.assertEqual(read["if"], "(github.event_name == 'push' && " + common
                         + ") || (github.event_name == 'workflow_dispatch' && " + common + ")")
        self.assertEqual(write["if"], "(github.event_name == 'push' && " + common
                         + " && github.run_attempt > 1) || (github.event_name == 'workflow_dispatch' && " + common + ")")
        self.assertEqual(write.get("needs"), "legacy-review-activation")
        self.assertEqual(read["permissions"], {"contents": "read", "pull-requests": "read",
                         "issues": "read", "actions": "read", "checks": "read"})
        self.assertEqual(write["permissions"], dict(read["permissions"], checks="write"))
        for job in (read, write):
            self.assertNotIn("continue-on-error", job)
            self.assertFalse(any("checkout@" in step.get("uses", "") for step in job["steps"]))
            scripts = [step for step in job["steps"] if "run" in step]
            self.assertEqual(len(scripts), 1)
            self.assertNotIn("if", scripts[0])
            self.assertNotIn("continue-on-error", scripts[0])
            self.assertEqual(scripts[0]["env"]["SOURCE_SHA"], "${{ github.sha }}")
            script = scripts[0]["run"]
            self.assertIn("?ref=7da4d20b242fe6d327e342d61ac06094b2a5ac6b", script)
            self.assertIn("?ref=57bfc75b2af375efb1774faf0c418147097c0d10", script)
            self.assertIn("7fc2d125cf05c7f2dba80b013e25f44c45aaaceb7b019b2793a6ccce97fe64f3", script)
            self.assertIn("ff3bab0fcdc4d0eeb7e94af21eb1df2c2cde6858ca8cbfa14363b08b804644a0", script)
            self.assertEqual(script.count("sha256sum --check --status"), 2)
        read_script = read["steps"][0]["run"]
        self.assertNotIn("--apply", read_script)
        self.assertIn('"$GITHUB_RUN_ATTEMPT" == 1', read_script)
        self.assertLess(read_script.index('"$GITHUB_RUN_ATTEMPT" == 1'), read_script.index("gh api"))
        self.assertIn("--apply", write["steps"][0]["run"])

    def test_read_only_activation_and_dependent_name_writer_have_closed_boundaries(self):
        self.boundary(self.workflow())

    def test_removing_activation_source_pin_or_candidate_isolation_is_rejected(self):
        for mutation in ("needs", "event", "attempt", "permissions", "pin", "digest"):
            workflow = self.workflow()
            read, write = [workflow["jobs"][name] for name in ("legacy-review-activation", "legacy-review-retirement")]
            if mutation == "needs":
                del write["needs"]
            elif mutation == "event":
                write["if"] = "github.event_name == 'pull_request'"
            elif mutation == "attempt":
                write["if"] = write["if"].replace(" && github.run_attempt > 1", "")
            elif mutation == "permissions":
                read["permissions"]["checks"] = "write"
            elif mutation == "pin":
                write["steps"][0]["run"] = write["steps"][0]["run"].replace(
                    "?ref=7da4d20b242fe6d327e342d61ac06094b2a5ac6b", "?ref=branch")
            else:
                write["steps"][0]["run"] = write["steps"][0]["run"].replace("sha256sum --check --status", "true")
            with self.subTest(mutation=mutation), self.assertRaises(AssertionError):
                self.boundary(workflow)

    def test_initial_push_stops_before_downloading_or_executing_any_helper(self):
        script = self.workflow()["jobs"]["legacy-review-activation"]["steps"][0]["run"]
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "called"
            env = dict(os.environ, GITHUB_EVENT_NAME="push", GITHUB_RUN_ATTEMPT="1",
                       GITHUB_REPOSITORY=repair.REPOSITORY, SOURCE_SHA=SOURCE, RUNNER_TEMP=directory,
                       MOCK_MARKER=str(marker))
            stubs = 'gh() { printf called > "$MOCK_MARKER"; return 99; }\npython3() { printf called > "$MOCK_MARKER"; return 99; }\n'
            result = subprocess.run(["bash", "-c", stubs + script], env=env, text=True,
                                    capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(marker.exists())

    def test_pinned_helper_and_collector_digests_match_the_actual_files(self):
        root = Path(__file__).resolve().parents[1] / "tools"
        self.assertEqual(hashlib.sha256((root / "retire_legacy_review_publications.py").read_bytes()).hexdigest(),
                         "7fc2d125cf05c7f2dba80b013e25f44c45aaaceb7b019b2793a6ccce97fe64f3")
        self.assertEqual(hashlib.sha256((root / "pr_review_convergence_operator.py").read_bytes()).hexdigest(),
                         "ff3bab0fcdc4d0eeb7e94af21eb1df2c2cde6858ca8cbfa14363b08b804644a0")

    def test_operator_collector_preserves_native_bytes_and_authenticated_boundaries(self):
        root = Path(__file__).resolve().parents[1] / "tools"
        stable = (root / "pr_review_convergence.py").read_text()
        operator = (root / "pr_review_convergence_operator.py").read_text()
        self.assertEqual(hashlib.sha256(stable.encode()).hexdigest(),
                         "21fdbd425dcf9dbe00ee7c2798d25a92363d9b2ebe89f25e4dafa1cfb3aa9863")
        self.assertIn("Chef's kiss\\.|Keep them coming!|Nice work!", operator)
        self.assertNotIn("def codex_summary_candidates", stable)
        self.assertIn("def codex_summary_candidates", operator)
        self.assertIn("candidates[-1][2][", operator)
        self.assertIn("if (candidates and candidates[-1][2]", operator)
        self.assertIn('and candidates[-1][2]["has_unresolved_findings"] is None', operator)
        self.assertIn("ambiguous or unrecognized authenticated Codex receipt", operator)
        self.assertIn("pr_review_convergence_operator.py?ref=57bfc75b2af375efb1774faf0c418147097c0d10",
                      self.workflow()["jobs"]["legacy-review-retirement"]["steps"][0]["run"])

    def test_operation_review_base_runs_the_read_only_contract_and_token_tests(self):
        path = Path(__file__).resolve().parents[1] / ".github/workflows/pr-review-convergence-contract.yml"
        workflow = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
        self.assertIn(repair.TARGET_BRANCH, workflow["on"]["pull_request"]["branches"])
        for event in ("pull_request", "push"):
            self.assertIn("tools/retire_legacy_review_publications.py", workflow["on"][event]["paths"])
            self.assertIn("tests/test_pr_review_convergence_retirement.py", workflow["on"][event]["paths"])
            self.assertIn("tools/pr_review_convergence_operator.py", workflow["on"][event]["paths"])
        job = workflow["jobs"]["convergence-contract"]
        self.assertIn("test_workflow_token_permissions.py", "\n".join(s.get("run", "") for s in job["steps"]))
        self.assertNotIn("write", workflow["permissions"].values())
        smoke = job["steps"][2]
        self.assertEqual(smoke["env"]["PR_BASE_REF"], "${{ github.event.pull_request.base.ref }}")
        self.assertIn('"$PR_NUMBER" == 591', smoke["run"])
        self.assertIn('"$PR_BASE_REF" == feature/bounded-auditable-investigations-v01',
                      smoke["run"])
        self.assertIn("collector=tools/pr_review_convergence_operator.py", smoke["run"])
        self.assertIn("collector=tools/pr_review_convergence.py", smoke["run"])
        self.assertIn('python3 "$collector"', smoke["run"])


if __name__ == "__main__":
    unittest.main()
