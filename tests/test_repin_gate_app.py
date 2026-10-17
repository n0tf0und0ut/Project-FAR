"""The protected-repin-gate GitHub App: identity, deployment integrity, evaluation, and publication.

GitHub's required-status-check matching is by check name plus, optionally, the App that set it
("If the status is set by any other person or integration, merging won't be allowed"). A check
named ``protected-repin-gate`` from a candidate's GitHub Actions job therefore satisfies nothing
once branch protection binds the name to this App's ID; ``check_protection`` verifies that
binding. The live behaviour is confirmed by the bootstrap probe (see the procedure document).

The end-to-end tests run ``Gate.run_once`` against a real git "remote" holding main and several
pull-request heads, a fake GitHub API, a real RSA App key (JWT signed by ``openssl``), and real
owner SSH signatures. The App keeps no state between cycles (a free CI host starts cold every
time), so the fake API also serves the App's own earlier check runs.
"""
from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
import unittest.mock
from datetime import datetime, timedelta, timezone
from pathlib import Path

from far_validation import repin
from far_validation import repin_gate_app as app
from far_validation import repin_signature as sig

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "notfoundout/Project-FAR"
REPOSITORY_ID = 1283452680
POLICY = "validation/runtime-policy.json"
# Keep real-clock integration paths inside the same authorization window as the fixture.
NOW = datetime.now(timezone.utc).replace(microsecond=0)
APP_ID = 424242
GATE_REPOSITORY_ID = 99887766
ACTIONS_APP_ID = 15368


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(*args: str, cwd: Path | None = None) -> str:
    return subprocess.run(list(args), cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class Fixture:
    """A remote repository with main and pull-request heads, an owner key, and an App key."""

    def __init__(self, root: Path) -> None:
        self.root = root
        subprocess.run(["ssh-keygen", "-q", "-t", "ecdsa", "-b", "256", "-N", "", "-C", "", "-f", str(root / "owner")], check=True)
        kind, blob = (root / "owner.pub").read_text().split()[:2]
        self.signers = f'{sig.PRINCIPAL} namespaces="{sig.NAMESPACE}" {kind} {blob}\n'.encode()
        (root / "allowed_signers").write_bytes(self.signers)
        run("openssl", "genrsa", "-out", str(root / "app.pem"), "2048")
        (root / "app.pem").chmod(0o600)
        self.remote = root / "remote"
        self.remote.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "t@example.invalid")
        self.git("config", "user.name", "t")
        self.write(POLICY, b'{"network_policy": "deny"}\n')
        for name in app.DEPLOYMENT_FILES:  # main pins the same evaluator the App is deployed with
            self.write(name, (ROOT / name).read_bytes())
        self.write(sig.ALLOWED_SIGNERS_PATH, self.signers)
        self.write_lock()
        self.write(repin.CONSUMPTIONS_PATH, b'{"schema_version": "2.0", "consumptions": []}\n')
        self.main = self.commit("main")

    def git(self, *args: str) -> str:
        return run("git", "-C", str(self.remote), *args)

    def write(self, rel: str, data: bytes) -> None:
        target = self.remote / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def write_lock(self) -> None:
        files = {p: sha256((self.remote / p).read_bytes()) for p in (POLICY, *app.DEPLOYMENT_FILES, sig.ALLOWED_SIGNERS_PATH)}
        self.write(repin.ASSURANCE_LOCK_PATH, (json.dumps({"schema_version": "1.0", "files": files}, indent=2) + "\n").encode())

    def commit(self, message: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-qm", message)
        return self.git("rev-parse", "HEAD")

    def pull(self, number: int, change) -> str:
        """Create refs/pull/<number>/head from main with ``change`` applied."""
        self.git("checkout", "-q", "-B", f"pr{number}", self.main)
        change(self)
        head = self.commit(f"pr {number}")
        self.git("update-ref", f"refs/pull/{number}/head", head)
        self.git("checkout", "-q", "main")
        return head

    def signed(self, path: str, old: str, new: str, target_pr: int) -> dict:
        payload = {
            "schema": sig.SCHEMA, "domain": sig.DOMAIN, "id": sha256(f"{path}{target_pr}{new}".encode())[:32], "repository": REPOSITORY,
            "repository_id": REPOSITORY_ID,
            "path": path, "old_sha256": old, "new_sha256": new, "target_pr": target_pr, "base_sha": self.main,
            "reason": "owner-reviewed replacement of this exact protected artifact",
            "issued_at": (NOW - timedelta(hours=1)).strftime(sig.TIME_FORMAT),
            "expires_at": (NOW + timedelta(days=7)).strftime(sig.TIME_FORMAT),
        }
        message = self.root / "payload"
        message.write_bytes(sig.canonical_bytes(payload))
        subprocess.run(["ssh-keygen", "-q", "-Y", "sign", "-f", str(self.root / "owner"), "-n", sig.NAMESPACE, str(message)],
                       check=True, capture_output=True)
        signature = (self.root / "payload.sig").read_text()
        (self.root / "payload.sig").unlink()
        return {"payload": message.read_text(), "signature": signature}

    def repin_policy(self, target_pr: int | None, content: bytes = b'{"network_policy": "deny", "timeout": 60}\n'):
        def change(fixture: "Fixture") -> None:
            old = sha256((fixture.remote / POLICY).read_bytes())
            fixture.write(POLICY, content)
            fixture.write_lock()
            if target_pr is not None:
                ledger = json.loads((fixture.remote / repin.CONSUMPTIONS_PATH).read_text())
                ledger["consumptions"].append(fixture.signed(POLICY, old, sha256(content), target_pr))
                fixture.write(repin.CONSUMPTIONS_PATH, (json.dumps(ledger, indent=2) + "\n").encode())
        return change


class FakeGitHub:
    def __init__(self, pulls: list[dict]) -> None:
        self.pulls = pulls
        self.checks: list[dict] = []
        self.token_requests: list[dict] = []
        self.jwts: list[str] = []
        self.repository_id = REPOSITORY_ID
        self.foreign_checks: list[dict] = []  # check runs other Apps posted
        self.protection: dict = {}
        self.main_sha = "0" * 40

    def runs_on(self, head_sha: str) -> list[dict]:
        own = [{"id": i + 1, "name": c["name"], "status": c["status"], "external_id": c.get("external_id"),
                "app": {"id": APP_ID}, "head_sha": c["head_sha"]} for i, c in enumerate(self.checks)]
        return [r for r in own + self.foreign_checks if r["head_sha"] == head_sha]

    def __call__(self, method: str, url: str, headers: dict[str, str], body):
        path = url.split("https://api.test", 1)[1]
        if method == "GET" and path.startswith(f"/repos/{REPOSITORY}/commits/") and "/check-runs?" in path:
            assert headers["Authorization"] == "Bearer ghs_installation"
            head, query = path.split("/commits/", 1)[1].split("/check-runs?", 1)
            name = dict(q.split("=", 1) for q in query.split("&"))["check_name"]
            return {"check_runs": [r for r in self.runs_on(head) if r["name"] == name]}
        if path == f"/repos/{REPOSITORY}/branches/main/protection":
            return self.protection
        if path in (f"/repos/{REPOSITORY}/rulesets?includes_parents=true", f"/repos/{REPOSITORY}/rules/branches/main"):
            return []
        if path == f"/repos/{REPOSITORY}/commits/main":
            return {"sha": self.main_sha}
        if path == f"/repos/{REPOSITORY}":
            return {"id": self.repository_id, "full_name": REPOSITORY}
        if path == f"/repos/{REPOSITORY}/installation":
            self.jwts.append(headers["Authorization"].split(" ", 1)[1])
            return {"id": 77}
        if path == "/app/installations/77/access_tokens":
            self.token_requests.append(body)
            return {"token": "ghs_installation"}
        if path.startswith(f"/repos/{REPOSITORY}/pulls?"):
            return self.pulls if "page=1" in path else []
        if path == f"/repos/{REPOSITORY}/check-runs":
            assert headers["Authorization"] == "Bearer ghs_installation"
            self.checks.append(body)
            return {"id": len(self.checks)}
        raise AssertionError(f"unexpected API call {method} {path}")


class GateAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.fx = Fixture(self.dir)
        self.deploy = self.dir / "deploy"
        (self.deploy / "far_validation").mkdir(parents=True)
        for name in app.DEPLOYMENT_FILES:
            shutil.copy(ROOT / name, self.deploy / name)
        run("git", "init", "-q", cwd=self.deploy)
        run("git", "-c", "user.email=t@x", "-c", "user.name=t", "add", "-A", cwd=self.deploy)
        run("git", "-c", "user.email=t@x", "-c", "user.name=t", "commit", "-qm", "deploy", cwd=self.deploy)
        self.deployed = run("git", "rev-parse", "HEAD", cwd=self.deploy)

    def config(self, **overrides) -> app.Config:
        values = dict(app_id=APP_ID, private_key=self.dir / "app.pem", repository=REPOSITORY, repository_id=REPOSITORY_ID,
                      allowed_signers=self.dir / "allowed_signers", state_dir=self.dir / "state",
                      deployed_commit=self.deployed, api_url="https://api.test", git_url=str(self.fx.remote))
        values.update(overrides)
        return app.Config(**values)

    def gate(self, pulls: list[dict], **overrides) -> tuple[app.Gate, FakeGitHub]:
        github = FakeGitHub(pulls)
        return app.Gate(self.config(**overrides), http=github, now=lambda: NOW, checkout=self.deploy, environ={}), github

    @staticmethod
    def pr(number: int, head: str) -> dict:
        return {"number": number, "head": {"sha": head}, "base": {"ref": "main"}}

    def conclusions(self, github: FakeGitHub) -> dict[str, str]:
        return {c["head_sha"]: c["conclusion"] for c in github.checks}

    def test_end_to_end_decisions(self) -> None:
        good = self.fx.pull(538, self.fx.repin_policy(538))
        unsigned = self.fx.pull(539, self.fx.repin_policy(None))
        wrong_pr = self.fx.pull(540, self.fx.repin_policy(538, b'{"network_policy": "deny", "timeout": 61}\n'))

        def rewrite_evaluator(fixture: Fixture) -> None:  # a candidate "fixes" the gate to always pass
            fixture.write("far_validation/repin.py", b"def evaluate(*a, **k):\n    return True\n")
            fixture.write_lock()
        evaluator = self.fx.pull(541, rewrite_evaluator)

        def shadow_check(fixture: Fixture) -> None:  # a candidate Actions job named like the gate
            fixture.write(".github/workflows/shadow.yml", b"on: pull_request\njobs:\n  protected-repin-gate:\n"
                                                          b"    runs-on: ubuntu-latest\n    steps: [{run: 'true'}]\n")
            fixture.repin_policy(None)(fixture)
        shadow = self.fx.pull(542, shadow_check)

        gate, github = self.gate([self.pr(538, good), self.pr(539, unsigned), self.pr(540, wrong_pr),
                                  self.pr(541, evaluator), self.pr(542, shadow)])
        gate.run_once()
        self.assertEqual(self.conclusions(github), {good: "success", unsigned: "failure", wrong_pr: "failure",
                                                    evaluator: "failure", shadow: "failure"})
        self.assertTrue(all(c["name"] == app.CHECK_NAME and c["status"] == "completed" for c in github.checks))
        self.assertIn(self.deployed, github.checks[0]["output"]["summary"])
        self.assertEqual(github.token_requests, [{"repositories": ["Project-FAR"], "permissions": {
            "checks": "write", "contents": "read", "pull_requests": "read", "metadata": "read"}}])
        self.assertEqual(run("git", "-C", str(self.dir / "state" / "mirror.git"), "rev-parse", "--is-bare-repository"), "true")

        gate.run_once()  # nothing changed: nothing is re-posted
        self.assertEqual(len(github.checks), 5)
        self.assertTrue(all(c["external_id"].endswith(":" + str(c["conclusion"] == "success")) for c in github.checks))

    def test_cold_start_is_stateless_and_never_suppresses_a_changed_decision(self) -> None:
        """A free CI host starts from nothing each run: the decision key lives on GitHub, not on disk."""
        good = self.fx.pull(538, self.fx.repin_policy(538))
        gate, github = self.gate([self.pr(538, good)])
        gate.run_once()
        shutil.rmtree(self.dir / "state")  # restart on a fresh runner
        cold = app.Gate(self.config(), http=github, now=lambda: NOW, checkout=self.deploy, environ={})
        cold.run_once()
        self.assertEqual(len(github.checks), 1)  # the same decision is not re-posted
        # The authorization expires: the decision changes and is posted, even though a run exists.
        later = app.Gate(self.config(), http=github, now=lambda: NOW + timedelta(days=30), checkout=self.deploy, environ={})
        later.run_once()
        self.assertEqual([c["conclusion"] for c in github.checks], ["success", "failure"])

    def test_only_the_apps_own_completed_runs_count_as_already_posted(self) -> None:
        good = self.fx.pull(538, self.fx.repin_policy(538))
        gate, github = self.gate([self.pr(538, good)])
        key = f"538:{good}:{self.fx.main}:{self.deployed}:True"
        github.foreign_checks = [  # another App (e.g. a candidate Actions job) copies the decision key
            {"id": 900, "name": app.CHECK_NAME, "status": "completed", "external_id": key,
             "app": {"id": ACTIONS_APP_ID}, "head_sha": good}]
        gate.run_once()
        self.assertEqual(self.conclusions(github), {good: "success"})
        self.assertEqual(github.checks[0]["external_id"], key)
    def test_every_process_the_app_runs_is_read_only_object_access(self) -> None:
        """Record the real commands of a full cycle: no checkout, no candidate file executed."""
        good = self.fx.pull(538, self.fx.repin_policy(538))
        evaluator = self.fx.pull(541, lambda fx: (fx.write("far_validation/repin.py", b"raise SystemExit('ran')\n"), fx.write_lock()))
        gate, github = self.gate([self.pr(538, good), self.pr(541, evaluator)])
        seen: list[list[str]] = []
        real_run = subprocess.run

        def recording_run(args, *a, **k):
            seen.append([str(x) for x in args])
            return real_run(args, *a, **k)

        with unittest.mock.patch.object(subprocess, "run", recording_run):
            gate.run_once()
        self.assertEqual(self.conclusions(github), {good: "success", evaluator: "failure"})
        allowed = {"rev-parse", "ls-tree", "cat-file", "merge-base", "fetch", "init", "status"}
        for argv in seen:
            self.assertIn(Path(argv[0]).name, {"git", "ssh-keygen", "openssl"}, argv)
            if Path(argv[0]).name == "git":
                rest, command = argv[1:], None
                while rest:
                    token = rest.pop(0)
                    if token in ("-C", "-c"):
                        rest.pop(0)
                    elif not token.startswith("-"):
                        command = token
                        break
                self.assertIn(command, allowed, argv)
                if command == "fetch":
                    self.assertIn("--no-recurse-submodules", argv)
            if Path(argv[0]).name == "ssh-keygen":
                self.assertEqual(argv[1:3], ["-Y", "verify"], argv)
            self.assertFalse(any(str(self.fx.remote) in x and x.endswith(".py") for x in argv), argv)

    def test_moving_main_forces_reevaluation(self) -> None:
        good = self.fx.pull(538, self.fx.repin_policy(538))
        gate, github = self.gate([self.pr(538, good)])
        gate.run_once()
        self.fx.write("docs/other.md", b"main moved\n")
        self.fx.main = self.fx.commit("main moves")
        gate.run_once()
        self.assertEqual([c["head_sha"] for c in github.checks], [good, good])

    def test_a_head_open_as_two_pull_requests_is_decided_once_and_must_pass_as_both(self) -> None:
        """Check runs belong to commits. Deciding per pull request would post success (as #538) and
        failure (as #544) on the same commit every cycle, so each would supersede the other, and #544
        could briefly carry #538's success. One decision per head, over every PR that points at it."""
        good = self.fx.pull(538, self.fx.repin_policy(538))
        self.fx.git("update-ref", "refs/pull/544/head", good)  # the same commit opened again as #544
        gate, github = self.gate([self.pr(538, good), self.pr(544, good)])
        gate.run_once()
        gate.run_once()
        self.assertEqual([(c["head_sha"], c["conclusion"]) for c in github.checks], [(good, "failure")])
        summary = github.checks[0]["output"]["summary"]
        self.assertIn("as #544: ", summary)
        self.assertIn("is bound to pull request 538, not 544", summary)
        self.assertTrue(github.checks[0]["external_id"].startswith("538,544:"))
        gate, github2 = self.gate([self.pr(538, good)])  # the duplicate is closed: the decision changes
        github2.checks = list(github.checks)
        gate.run_once()
        self.assertEqual([c["conclusion"] for c in github2.checks], ["failure", "success"])

    def test_nothing_is_posted_before_main_carries_the_evaluator(self) -> None:
        """Deploying the gate ahead of the bootstrap merge posts no decision on any open pull request."""
        for name in app.DEPLOYMENT_FILES:
            self.fx.git("rm", "-q", name)
        self.fx.main = self.fx.commit("main before bootstrap")
        head = self.fx.pull(538, lambda fx: fx.write("docs/x.md", b"x\n"))
        gate, github = self.gate([self.pr(538, head)])
        with self.assertRaisesRegex(app.GateError, "before the bootstrap merge"):
            gate.run_once()
        self.assertEqual(github.checks, [])

    def test_head_that_moved_during_evaluation_is_not_reported(self) -> None:
        self.fx.pull(538, self.fx.repin_policy(538))
        gate, github = self.gate([self.pr(538, "0" * 40)])
        results = gate.run_once()
        self.assertEqual(github.checks, [])
        self.assertIn("skipped", results[0])

    def test_deployment_key_not_matching_main_fails_closed(self) -> None:
        good = self.fx.pull(538, self.fx.repin_policy(538))
        other = self.dir / "other_signers"
        subprocess.run(["ssh-keygen", "-q", "-t", "ecdsa", "-b", "256", "-N", "", "-C", "", "-f", str(self.dir / "other")], check=True)
        kind, blob = (self.dir / "other.pub").read_text().split()[:2]
        other.write_text(f'{sig.PRINCIPAL} namespaces="{sig.NAMESPACE}" {kind} {blob}\n')
        gate, github = self.gate([self.pr(538, good)], allowed_signers=other)
        gate.run_once()
        self.assertEqual(self.conclusions(github), {good: "failure"})
        self.assertIn("trusted key differs", github.checks[0]["output"]["summary"])

    def test_modified_or_wrong_deployment_refuses_to_run(self) -> None:
        gate, github = self.gate([])
        (self.deploy / "far_validation/repin.py").write_text("# tampered\n")
        with self.assertRaises(app.GateError):
            gate.run_once()
        run("git", "checkout", "--", "far_validation/repin.py", cwd=self.deploy)
        gate, _ = self.gate([], deployed_commit="f" * 40)
        with self.assertRaises(app.GateError):
            gate.run_once()
        self.assertEqual(github.checks, [])

    def test_deployed_evaluator_must_equal_mains_evaluator(self) -> None:
        good = self.fx.pull(538, self.fx.repin_policy(538))
        (self.deploy / "far_validation/repin_signature.py").write_text("# an older or newer evaluator\n")
        run("git", "-c", "user.email=t@x", "-c", "user.name=t", "commit", "-qam", "other version", cwd=self.deploy)
        gate, github = self.gate([self.pr(538, good)], deployed_commit=run("git", "rev-parse", "HEAD", cwd=self.deploy))
        gate.run_once()
        self.assertEqual(self.conclusions(github), {good: "failure"})
        self.assertIn("redeploy the App", github.checks[0]["output"]["summary"])

    def test_repository_identity_must_match_the_immutable_id(self) -> None:
        good = self.fx.pull(538, self.fx.repin_policy(538))
        gate, github = self.gate([self.pr(538, good)])
        github.repository_id = REPOSITORY_ID + 1  # the name now denotes another repository
        with self.assertRaises(app.GateError):
            gate.run_once()
        self.assertEqual(github.checks, [])

    def test_a_cycle_inside_github_actions_refuses_before_any_decision(self) -> None:
        good = self.fx.pull(538, self.fx.repin_policy(538))
        github = FakeGitHub([self.pr(538, good)])
        gate = app.Gate(self.config(), http=github, now=lambda: NOW, checkout=self.deploy, environ={"GITHUB_ACTIONS": "true"})
        with self.assertRaises(app.GateError):
            gate.run_once()
        self.assertEqual((github.checks, github.jwts), ([], []))

    def test_host_guards_keep_the_app_key_out_of_ci_and_shared_files(self) -> None:
        config = self.config()
        app.verify_host(config, {})
        for env in ({"GITHUB_ACTIONS": "true"}, {"CI": "true"}):
            with self.subTest(env=env), self.assertRaisesRegex(app.GateError, "unless gate_repository_id"):
                app.verify_host(config, env)
        (self.dir / "app.pem").chmod(0o644)
        with self.assertRaises(app.GateError):
            app.verify_host(config, {})

    def test_ci_is_allowed_only_as_the_gate_repositorys_main_schedule_or_dispatch(self) -> None:
        config = self.config(gate_repository_id=GATE_REPOSITORY_ID)
        good = {"GITHUB_ACTIONS": "true", "CI": "true", "GITHUB_REPOSITORY_ID": str(GATE_REPOSITORY_ID),
                "GITHUB_REF": "refs/heads/main", "GITHUB_EVENT_NAME": "schedule"}
        app.verify_host(config, good)
        app.verify_host(config, {**good, "GITHUB_EVENT_NAME": "workflow_dispatch"})
        cases = {
            "protected repository's own workflow": {**good, "GITHUB_REPOSITORY_ID": str(REPOSITORY_ID)},
            "another repository": {**good, "GITHUB_REPOSITORY_ID": "1"},
            "pull_request event": {**good, "GITHUB_EVENT_NAME": "pull_request"},
            "pull_request_target event": {**good, "GITHUB_EVENT_NAME": "pull_request_target"},
            "workflow_run event": {**good, "GITHUB_EVENT_NAME": "workflow_run"},
            "push event": {**good, "GITHUB_EVENT_NAME": "push"},
            "another branch": {**good, "GITHUB_REF": "refs/heads/feature"},
            "a pull request ref": {**good, "GITHUB_REF": "refs/pull/1/merge"},
            "CI without GITHUB_ACTIONS": {k: v for k, v in good.items() if k != "GITHUB_ACTIONS"},
        }
        for name, env in cases.items():
            with self.subTest(case=name), self.assertRaises(app.GateError):
                app.verify_host(config, env)
        with self.assertRaisesRegex(app.GateError, "never run in the protected repository"):
            app.verify_host(config, cases["protected repository's own workflow"])
        (self.dir / "app.pem").chmod(0o644)  # the key-file guard still applies in CI
        with self.assertRaises(app.GateError):
            app.verify_host(config, good)
        with self.assertRaises(app.GateError):  # the gate repository can never be the protected one
            self.config(gate_repository_id=REPOSITORY_ID)

    def actions_env(self, **overrides: str) -> dict[str, str]:
        env = {"GITHUB_ACTIONS": "true", "CI": "true", "GITHUB_REPOSITORY_ID": str(GATE_REPOSITORY_ID),
               "GITHUB_REF": "refs/heads/main", "GITHUB_EVENT_NAME": "schedule", "RUNNER_TEMP": str(self.dir / "runner"),
               "FAR_APP_ID": str(APP_ID), "FAR_APP_PRIVATE_KEY": (self.dir / "app.pem").read_text(),
               "FAR_REPOSITORY": REPOSITORY, "FAR_REPOSITORY_ID": str(REPOSITORY_ID),
               "FAR_DEPLOYED_COMMIT": self.deployed, "FAR_GATE_REPOSITORY_ID": str(GATE_REPOSITORY_ID)}
        env.update(overrides)
        (self.dir / "runner").mkdir(exist_ok=True)
        return env

    def deploy_signers(self) -> None:
        (self.deploy / "validation_bootstrap").mkdir(exist_ok=True)
        (self.deploy / sig.ALLOWED_SIGNERS_PATH).write_bytes(self.fx.signers)
        run("git", "-c", "user.email=t@x", "-c", "user.name=t", "add", "-A", cwd=self.deploy)
        run("git", "-c", "user.email=t@x", "-c", "user.name=t", "commit", "-qm", "key", cwd=self.deploy)
        self.deployed = run("git", "rev-parse", "HEAD", cwd=self.deploy)

    def test_actions_cycle_uses_the_deployed_key_file_and_leaves_no_app_key_behind(self) -> None:
        self.deploy_signers()
        good = self.fx.pull(538, self.fx.repin_policy(538))
        unsigned = self.fx.pull(539, self.fx.repin_policy(None))
        github = FakeGitHub([self.pr(538, good), self.pr(539, unsigned)])
        modes: list[int] = []
        real_jwt = app.app_jwt

        def observing_jwt(app_id, private_key, now=None):
            modes.append(private_key.stat().st_mode & 0o777)
            return real_jwt(app_id, private_key, now)

        with unittest.mock.patch.object(app, "app_jwt", observing_jwt):
            code = app.run_actions("evaluate", self.actions_env(), http=github, checkout=self.deploy,
                                   api_url="https://api.test", git_url=str(self.fx.remote))
        self.assertEqual(code, 0)
        self.assertEqual(self.conclusions(github), {good: "success", unsigned: "failure"})
        self.assertEqual(modes, [0o600])
        self.assertFalse((self.dir / "runner" / "far-repin-gate" / "app.pem").exists())
        self.assertIn(self.deployed, github.checks[0]["output"]["summary"])

    def test_actions_cycle_fails_closed_on_any_misconfiguration(self) -> None:
        self.deploy_signers()
        good = self.fx.pull(538, self.fx.repin_policy(538))
        cases = {
            "no key secret": {"FAR_APP_PRIVATE_KEY": ""},
            "run from the protected repository": {"GITHUB_REPOSITORY_ID": str(REPOSITORY_ID)},
            "pull-request trigger": {"GITHUB_EVENT_NAME": "pull_request"},
            "placeholder deployment": {"FAR_DEPLOYED_COMMIT": "REPLACE_WITH_40_HEX_MAIN_COMMIT"},
            "placeholder App id": {"FAR_APP_ID": "REPLACE_WITH_APP_ID"},
        }
        for name, override in cases.items():
            with self.subTest(case=name):
                github = FakeGitHub([self.pr(538, good)])
                code = app.run_actions("evaluate", self.actions_env(**override), http=github, checkout=self.deploy,
                                       api_url="https://api.test", git_url=str(self.fx.remote))
                self.assertEqual((code, github.checks), (1, []))
                self.assertFalse((self.dir / "runner" / "far-repin-gate" / "app.pem").exists())

    def test_audit_records_live_protection_as_an_app_check_on_main(self) -> None:
        self.deploy_signers()
        github = FakeGitHub([])
        github.main_sha = self.fx.main
        github.protection = ProtectionTests().protection()
        env = self.actions_env(GITHUB_EVENT_NAME="workflow_dispatch")
        code = app.run_actions("audit", env, http=github, checkout=self.deploy, api_url="https://api.test")
        self.assertEqual(code, 0)
        self.assertEqual(github.token_requests[-1]["permissions"], app.AUDIT_TOKEN_PERMISSIONS)
        audit = github.checks[-1]
        self.assertEqual((audit["name"], audit["head_sha"], audit["conclusion"]), (app.AUDIT_CHECK_NAME, self.fx.main, "success"))
        self.assertIn('"enforce_admins"', audit["output"]["summary"])
        github.protection = ProtectionTests().protection(enforce_admins={"enabled": False})
        self.assertEqual(app.run_actions("audit", env, http=github, checkout=self.deploy, api_url="https://api.test"), 1)
        self.assertEqual((github.checks[-1]["conclusion"], github.checks[-1]["output"]["title"]), ("neutral", "protection audit FAIL"))
        self.assertIn("enforce_admins must be enabled", github.checks[-1]["output"]["summary"])

    def test_audit_refuses_outside_the_gate_repository_before_minting_a_token(self) -> None:
        self.deploy_signers()
        for name, override in {"protected repository's own workflow": {"GITHUB_REPOSITORY_ID": str(REPOSITORY_ID)},
                               "pull-request trigger": {"GITHUB_EVENT_NAME": "pull_request"}}.items():
            with self.subTest(case=name):
                github = FakeGitHub([])
                code = app.run_actions("audit", self.actions_env(**override), http=github, checkout=self.deploy,
                                       api_url="https://api.test")
                self.assertEqual((code, github.checks, github.jwts, github.token_requests), (1, [], [], []))

    def test_check_summary_publishes_every_transition_in_full_for_the_owner(self) -> None:
        unsigned = self.fx.pull(539, self.fx.repin_policy(None))
        gate, github = self.gate([self.pr(539, unsigned)])
        gate.run_once()
        summary = github.checks[0]["output"]["summary"]
        old = sha256(b'{"network_policy": "deny"}\n')
        new = sha256(b'{"network_policy": "deny", "timeout": 60}\n')
        for line in (f"- path: {POLICY}", f"  old_sha256: {old}", f"  new_sha256: {new}",
                     f"repository_id {REPOSITORY_ID}, target_pr 539"):
            self.assertIn(line, summary)

    def test_app_jwt_is_rs256_signed_by_the_app_key(self) -> None:
        token = app.app_jwt(APP_ID, self.dir / "app.pem", now=1_800_000_000)
        header, claims, signature = token.split(".")
        pad = lambda s: base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
        self.assertEqual(json.loads(pad(header)), {"alg": "RS256", "typ": "JWT"})
        self.assertEqual(json.loads(pad(claims)), {"iat": 1_800_000_000 - 60, "exp": 1_800_000_000 + 540, "iss": APP_ID})
        run("openssl", "rsa", "-in", str(self.dir / "app.pem"), "-pubout", "-out", str(self.dir / "app.pub.pem"))
        (self.dir / "jwt.sig").write_bytes(pad(signature))
        (self.dir / "jwt.in").write_bytes(f"{header}.{claims}".encode())
        run("openssl", "dgst", "-sha256", "-verify", str(self.dir / "app.pub.pem"), "-signature",
            str(self.dir / "jwt.sig"), str(self.dir / "jwt.in"))


class WorkflowTemplateTests(unittest.TestCase):
    """The gate-repository workflow the owner copies: nothing in it may widen who reaches the App key."""

    def setUp(self) -> None:
        import yaml
        self.text = (ROOT / "far_validation/repin_gate_workflow.yml").read_text(encoding="utf-8")
        self.workflow = yaml.safe_load(self.text)
        self.triggers = self.workflow.get("on", self.workflow.get(True))

    def test_only_owner_triggers_and_no_token_permissions(self) -> None:
        self.assertEqual(set(self.triggers), {"schedule", "workflow_dispatch"})
        self.assertEqual(self.workflow["permissions"], {})
        self.assertEqual(self.workflow["concurrency"]["cancel-in-progress"], False)

    def test_single_job_in_the_protected_environment_without_third_party_code(self) -> None:
        (job,) = self.workflow["jobs"].values()
        self.assertEqual(job["environment"], "far-repin-gate")
        self.assertEqual(job["runs-on"], "ubuntu-24.04")
        self.assertNotIn("uses:", self.text)
        self.assertTrue(all(set(step) <= {"name", "run", "env"} for step in job["steps"]))
        self.assertEqual(job["env"]["FAR_REPOSITORY"], REPOSITORY)
        self.assertEqual(job["env"]["FAR_REPOSITORY_ID"], str(REPOSITORY_ID))
        env_names = set(job["env"]) | {k for step in job["steps"] for k in step.get("env", {})}
        self.assertEqual(env_names - {"FAR_MODE"}, set(app.ACTIONS_ENV) - {"RUNNER_TEMP"})

    def test_secret_reaches_only_the_gate_step_and_no_expression_is_spliced_into_a_script(self) -> None:
        (job,) = self.workflow["jobs"].values()
        self.assertEqual(self.text.count("secrets."), 1)
        holders = [step for step in job["steps"] if "FAR_APP_PRIVATE_KEY" in step.get("env", {})]
        self.assertEqual(len(holders), 1)
        self.assertEqual(holders[0]["run"], (
            'set -euo pipefail\n'
            'if [[ "$FAR_MODE" == "audit" ]]; then\n'
            '  python3 deploy/far_validation/repin_protection_audit.py\n'
            'else\n'
            '  python3 deploy/far_validation/repin_gate_app.py actions --mode evaluate\n'
            'fi\n'))
        for step in job["steps"]:
            self.assertNotIn("${{", step["run"])
        checkout = job["steps"][0]["run"]
        self.assertIn("--no-recurse-submodules", checkout)
        self.assertIn('test "$(git -C deploy rev-parse HEAD)" = "$FAR_DEPLOYED_COMMIT"', checkout)


class CandidateAsDataTests(unittest.TestCase):
    def test_no_dynamic_execution_constructs(self) -> None:
        for name in app.DEPLOYMENT_FILES:
            source = (ROOT / name).read_text(encoding="utf-8")
            for forbidden in ("os.system", "shell=True", "eval(", "exec(", "runpy", "__import__", "pickle"):
                self.assertNotIn(forbidden, source, f"{name} contains {forbidden}")


class ProtectionTests(unittest.TestCase):
    def protection(self, **overrides) -> dict:
        body = {
            "required_status_checks": {"strict": True, "contexts": [app.CHECK_NAME],
                                       "checks": [{"context": app.CHECK_NAME, "app_id": APP_ID}]},
            "enforce_admins": {"enabled": True}, "allow_force_pushes": {"enabled": False},
            "allow_deletions": {"enabled": False},
        }
        body.update(overrides)
        return body

    def test_app_bound_protection_passes(self) -> None:
        self.assertEqual(app.check_protection(self.protection(), APP_ID), [])
        extra = self.protection(required_status_checks={
            "strict": True, "contexts": [app.CHECK_NAME, "merge-authority"],
            "checks": [{"context": app.CHECK_NAME, "app_id": APP_ID}, {"context": "merge-authority", "app_id": ACTIONS_APP_ID}]})
        self.assertEqual(app.check_protection(extra, APP_ID), [])

    def test_weaker_bindings_are_rejected(self) -> None:
        def checks(*entries: dict, strict: bool = True) -> dict:
            return {"strict": strict, "contexts": [e["context"] for e in entries], "checks": list(entries)}
        cases = {
            "bound to GitHub Actions (candidate jobs share this App)": self.protection(
                required_status_checks=checks({"context": app.CHECK_NAME, "app_id": ACTIONS_APP_ID})),
            "any source": self.protection(required_status_checks=checks({"context": app.CHECK_NAME, "app_id": None})),
            "also required from any source": self.protection(required_status_checks=checks(
                {"context": app.CHECK_NAME, "app_id": APP_ID}, {"context": app.CHECK_NAME, "app_id": None})),
            "not required": self.protection(required_status_checks=checks({"context": "merge-authority", "app_id": ACTIONS_APP_ID})),
            "not strict": self.protection(required_status_checks=checks({"context": app.CHECK_NAME, "app_id": APP_ID}, strict=False)),
            "admins bypass": self.protection(enforce_admins={"enabled": False}),
            "force pushes": self.protection(allow_force_pushes={"enabled": True}),
            "deletions": self.protection(allow_deletions={"enabled": True}),
        }
        for name, body in cases.items():
            with self.subTest(case=name):
                self.assertTrue(app.check_protection(body, APP_ID))


if __name__ == "__main__":
    unittest.main()
