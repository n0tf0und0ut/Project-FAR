#!/usr/bin/env python3
"""One-base manual metadata repair: rename proven advisory records, never results."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

REPOSITORY = "n0tf0und0ut/Project-FAR"
ROOT = "/repos/" + REPOSITORY
MAIN = "e4d936ca0ba9770be6f72e0435220987882f4146"
TARGET = "5cd1ff7a2d1847e2f6f91c1a99550b66efd96484"
TARGET_PR = 578
TARGET_BRANCH = "feature/bounded-auditable-investigations-v01"
REPAIR_BRANCH = "repair/legacy-review-publications-20261023"
REQUIRED = "pr-review-convergence-observation"
ADVISORY = "pr-review-convergence-scheduled-observation"
MAX_BYTES = 16 * 1024 * 1024
SHA = re.compile(r"[a-f0-9]{40}\Z")
NATIVE_URL = re.compile(r"https://github\.com/" + re.escape(REPOSITORY)
                        + r"/actions/runs/([1-9][0-9]*)/job/([1-9][0-9]*)\Z")
PUBLICATION_LINE = re.compile(r'\A[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}'
                              r'(?:\.[0-9]+)?Z (\{"id":.*)\Z')
GATES = {"merge-authority": (15368, ".github/workflows/validator-assurance.yml"),
         "exact-head-assurance": (15368, ".github/workflows/exact-head-assurance.yml"),
         REQUIRED: (15368, ".github/workflows/required-pr-review-convergence.yml"),
         "protected-repin-gate": (5073230, None)}


class RepairError(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self, token):
        self.token = token
        self.opener = urllib.request.build_opener(NoRedirect())

    def request(self, path, *, rename=False):
        if not path.startswith(ROOT + "/"):
            raise RepairError("request escaped the fixed repository")
        body = None
        if rename:
            if not re.fullmatch(re.escape(ROOT) + r"/check-runs/[1-9][0-9]*", path):
                raise RepairError("write escaped the check-name operation")
            body = json.dumps({"name": ADVISORY}).encode()
        request = urllib.request.Request("https://api.github.com" + path, data=body,
            method="PATCH" if rename else "GET",
            headers={"Authorization": "Bearer " + self.token,
                     "Accept": "application/vnd.github+json",
                     "Content-Type": "application/json", "X-GitHub-Api-Version": "2022-11-28"})
        with self.opener.open(request, timeout=25) as response:
            raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise RepairError("API response exceeds the bound")
        return json.loads(raw)

    def get(self, path):
        return self.request(path)

    def rename(self, ident):
        if type(ident) is not int or ident < 1:
            raise RepairError("invalid check identity")
        return self.request(ROOT + "/check-runs/" + str(ident), rename=True)

    def log(self, job_id):
        # GitHub returns a signed Azure URL. Never forward the API bearer token
        # to that host, and never follow a second redirect or print the signed URL.
        path = ROOT + "/actions/jobs/" + str(job_id) + "/logs"
        request = urllib.request.Request("https://api.github.com" + path,
                    headers={"Authorization": "Bearer " + self.token})
        try:
            response = self.opener.open(request, timeout=25)
        except urllib.error.HTTPError as exc:
            if exc.code != 302:
                raise RepairError("scheduled publisher log is unavailable") from None
            location = exc.headers.get("Location", "")
            parsed = urllib.parse.urlsplit(location)
            if (parsed.scheme != "https" or parsed.username or parsed.password
                    or parsed.port not in (None, 443) or not parsed.hostname
                    or not parsed.hostname.endswith(".blob.core.windows.net")):
                raise RepairError("unrecognized log download host") from None
            response = self.opener.open(urllib.request.Request(location), timeout=25)
        with response:
            raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise RepairError("publisher log exceeds the bound")
        return raw.decode("utf-8-sig")


def collection(client, path, key=None, pages=10):
    records = []
    for page in range(1, pages + 1):
        value = client.get(path + ("&" if "?" in path else "?")
                           + "per_page=100&page=" + str(page))
        batch = value if key is None else value.get(key)
        if not isinstance(batch, list) or any(not isinstance(x, dict) for x in batch):
            raise RepairError("incomplete collection")
        records.extend(batch)
        if len(batch) < 100:
            ids = [x.get("id") for x in records]
            if any(type(x) is not int or x < 1 for x in ids) or len(ids) != len(set(ids)):
                raise RepairError("missing or duplicate source identities")
            return records
    raise RepairError("collection pagination bound reached")


def check_review(number, head, output_dir):
    output = output_dir / ("review-" + str(number) + ".json")
    collector = Path(__file__).with_name("pr_review_convergence.py")
    subprocess.run([sys.executable, str(collector), "--repository", REPOSITORY,
                    "--pr", str(number), "--expected-head", head,
                    "--output", str(output), "--mode", "enforce"], check=True, timeout=180)
    record = json.loads(output.read_text())
    if (record.get("exact_head_sha") != head or record.get("pr_number") != number
            or record.get("review_metadata_converged") is not True
            or record.get("draft") is not False):
        raise RepairError("review preflight did not converge")
    return record


def identity(client):
    branch = client.get(ROOT + "/branches/main")
    pr = client.get(ROOT + "/pulls/578")
    if (branch.get("commit", {}).get("sha") != MAIN or branch.get("protected") is not True
            or pr.get("head", {}).get("sha") != TARGET or pr.get("state") != "open"
            or pr.get("draft") is not False or pr.get("base", {}).get("sha") != MAIN
            or pr.get("base", {}).get("ref") != "main"):
        raise RepairError("fixed main/PR identity changed")
    required = branch.get("protection", {}).get("required_status_checks", {})
    bindings = required.get("checks", [])
    expected = {(REQUIRED, 15368), ("merge-authority", 15368), ("protected-repin-gate", 5073230)}
    if (required.get("enforcement_level") != "everyone"
            or {(x.get("context"), x.get("app_id")) for x in bindings} != expected):
        raise RepairError("protection bindings changed or are incomplete")


def gate_evidence(client, checks, *, head=TARGET, gates=None):
    gates = GATES if gates is None else gates
    evidence = {}
    for name, (app, workflow) in gates.items():
        candidates = sorted((x for x in checks if x.get("name") == name
                             and x.get("app", {}).get("id") == app
                             and x.get("head_sha") == head), key=lambda x: x["id"], reverse=True)
        # API publications cannot masquerade as eligible native assurance jobs.
        if workflow:
            candidates = [x for x in candidates if NATIVE_URL.fullmatch(x.get("details_url", ""))]
        if (not candidates or candidates[0].get("status") != "completed"
                or candidates[0].get("conclusion") != "success"):
            raise RepairError("latest native engineering/review gate is not successful: " + name)
        check = candidates[0]
        if workflow:
            match = NATIVE_URL.fullmatch(check["details_url"])
            run = client.get(ROOT + "/actions/runs/" + match[1])
            jobs = collection(client, ROOT + "/actions/runs/" + match[1] + "/jobs", "jobs")
            if (int(match[2]) != check["id"] or run.get("head_sha") != head
                    or run.get("event") not in ("pull_request", "pull_request_review")
                    or run.get("path") != workflow or run.get("status") != "completed"
                    or run.get("conclusion") != "success"
                    or not any(j["id"] == check["id"] and j.get("name") == name
                               and j.get("status") == "completed"
                               and j.get("conclusion") == "success" for j in jobs)):
                raise RepairError("gate provenance does not match the fixed PR workflow")
        evidence[name] = check["id"]
    return evidence


def legacy_record(check, *, allow_renamed=False):
    ident = check.get("id")
    valid_names = (REQUIRED, ADVISORY) if allow_renamed else (REQUIRED,)
    return (type(ident) is int and ident > 0 and check.get("name") in valid_names
            and check.get("app", {}).get("id") == 15368 and check.get("head_sha") == TARGET
            and check.get("details_url") == f"https://github.com/{REPOSITORY}/runs/{ident}"
            and check.get("status") == "completed" and check.get("conclusion") in ("success", "failure"))


def fingerprint(check):
    return {key: check.get(key) for key in
            ("id", "head_sha", "status", "conclusion", "details_url", "output", "started_at", "completed_at")}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RepairError("duplicate publication JSON key")
        result[key] = value
    return result


def publication_proofs(client, legacy):
    wanted = {x["id"]: x for x in legacy}
    proofs = {}
    if not wanted:
        return proofs
    # Query only the verified publisher workflow. Repository-wide scheduled jobs
    # exhaust a small page window within hours and cannot prove older receipts.
    # Bound the search to 10,000 publisher runs; fail closed beyond that limit.
    for page in range(1, 101):
        response = client.get(ROOT + "/actions/workflows/pr-review-convergence.yml/runs"
                              + "?event=schedule&per_page=100&page=" + str(page))
        batch = response.get("workflow_runs")
        if not isinstance(batch, list) or any(not isinstance(x, dict) for x in batch):
            raise RepairError("incomplete publisher workflow run search")
        for run in batch:
            if (run.get("event") != "schedule" or run.get("head_sha") != MAIN
                    or run.get("head_branch") != "main"
                    or run.get("path") != ".github/workflows/pr-review-convergence.yml"):
                continue
            jobs = collection(client, ROOT + "/actions/runs/" + str(run["id"]) + "/jobs", "jobs")
            for job in jobs:
                if job.get("name") != "review-convergence (578)" or job.get("status") != "completed":
                    continue
                for line in client.log(job["id"]).splitlines():
                    match = PUBLICATION_LINE.fullmatch(line)
                    if not match:
                        continue
                    try:
                        posted = json.loads(match[1], object_pairs_hook=unique_object)
                    except ValueError:
                        continue
                    ident = posted.get("id") if isinstance(posted, dict) else None
                    # The publisher receipt MUST show the original required name.
                    # The live record may already be renamed from a partial retry;
                    # all immutable result fields must still match the original.
                    if (ident in wanted and legacy_record(posted)
                            and fingerprint(posted) == fingerprint(wanted[ident])):
                        proofs[ident] = {"run_id": run["id"], "job_id": job["id"]}
            if set(proofs) == set(wanted):
                return proofs
        if len(batch) < 100:
            break
    raise RepairError("not every legacy check has a protected-main scheduled publication receipt")


def persist_journal(path, record):
    """Durably stage a redacted write-ahead journal before any Checks API PATCH."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)

def execute(client, source_sha, output_dir, *, apply=False, reviewer=check_review):
    if not SHA.fullmatch(source_sha):
        raise RepairError("invalid immutable repair source")
    identity(client)
    prs = collection(client, ROOT + "/pulls?state=open")
    authorizations = [p for p in prs if p.get("head", {}).get("sha") == source_sha
                      and p.get("head", {}).get("ref") == REPAIR_BRANCH
                      and p.get("head", {}).get("repo", {}).get("full_name") == REPOSITORY
                      and p.get("base", {}).get("ref") == TARGET_BRANCH
                      and p.get("base", {}).get("sha") == TARGET and p.get("draft") is False]
    if len(authorizations) != 1:
        raise RepairError("missing unique exact-source operation review PR")
    reviews = [reviewer(authorizations[0]["number"], source_sha, output_dir),
               reviewer(TARGET_PR, TARGET, output_dir)]
    operation_checks = collection(client, ROOT + "/commits/" + source_sha
                                  + "/check-runs?filter=all", "check_runs")
    operation_tests = gate_evidence(client, operation_checks, head=source_sha, gates={
        "convergence-contract": (15368, ".github/workflows/pr-review-convergence-contract.yml")})
    checks = collection(client, ROOT + "/commits/" + TARGET + "/check-runs?filter=all", "check_runs")
    gates = gate_evidence(client, checks)
    # Include previously renamed records only when their original required-name
    # publication receipt is proven. This makes crash recovery auditable.
    legacy = [x for x in checks if legacy_record(x, allow_renamed=True)]
    proofs = publication_proofs(client, legacy)
    plan = [{"check_id": x["id"], "old_name": x["name"], "new_name": ADVISORY,
             "preserved": fingerprint(x), "source": proofs[x["id"]]} for x in legacy]
    # Complete all provenance/readiness checks before preparing any write.
    identity(client)
    operations = [{"check_id": x["id"], "state": "PREVIOUSLY_RENAMED"
                   if x["name"] == ADVISORY else "PLANNED"} for x in legacy]
    report = {"schema": "far-legacy-review-name-repair/1", "repository": REPOSITORY,
              "target_pr": TARGET_PR, "target_head": TARGET, "protected_main": MAIN,
              "operation_source": source_sha, "authorization_pr": authorizations[0]["number"],
              "review_artifacts": [r["pr_number"] for r in reviews], "gates": gates,
              "operation_tests": operation_tests, "plan": plan, "operations": operations,
              "renamed_check_ids": [], "applied": False, "state": "PREPARED",
              "conclusions_modified": False, "protection_modified": False,
              "merge_performed": False}
    journal_path = output_dir / "legacy-review-name-repair.json"
    # Persist the complete authorized plan before attempting the first write.
    persist_journal(journal_path, report)
    try:
        for index, before in enumerate(legacy):
            op = operations[index]
            latest = client.get(ROOT + "/check-runs/" + str(before["id"]))
            if (not legacy_record(latest, allow_renamed=True)
                    or latest["name"] != before["name"]
                    or fingerprint(latest) != fingerprint(before)):
                raise RepairError("publication changed after preflight")
            if before["name"] == ADVISORY:
                op["state"] = "PREVIOUSLY_RENAMED_VERIFIED"
                persist_journal(journal_path, report)
            elif apply:
                # Unknown outcome after a network interruption is not "failed":
                # document the attempted write before issuing the PATCH.
                op["state"] = "PATCH_IN_FLIGHT"
                persist_journal(journal_path, report)
                result = client.rename(before["id"])
                op["state"] = "PATCH_RETURNED"
                persist_journal(journal_path, report)
                after = client.get(ROOT + "/check-runs/" + str(before["id"]))
                if (result.get("name") != ADVISORY or after.get("name") != ADVISORY
                        or fingerprint(after) != fingerprint(before)
                        or after.get("app", {}).get("id") != 15368):
                    raise RepairError("readback did not preserve the original result")
                op["state"] = "READBACK_VERIFIED"
                report["renamed_check_ids"].append(before["id"])
                persist_journal(journal_path, report)
            identity(client)
    except Exception as exc:
        report["state"] = "INCOMPLETE"
        report["error_type"] = type(exc).__name__
        persist_journal(journal_path, report)
        raise
    report["state"] = "COMPLETE"
    report["applied"] = apply
    persist_journal(journal_path, report)
    return report

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    event = os.environ.get("GITHUB_EVENT_NAME")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
    activated = (event == "workflow_dispatch" or (event == "push"
                 and re.fullmatch(r"[1-9][0-9]*", attempt) and int(attempt) > 1))
    if (os.environ.get("GITHUB_REPOSITORY") != REPOSITORY or not activated
            or os.environ.get("GITHUB_REF") != "refs/heads/" + REPAIR_BRANCH
            or os.environ.get("GITHUB_SHA") != args.source_sha or not os.environ.get("GH_TOKEN")):
        parser.error("only the fixed, explicitly activated repair workflow may run")
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        report = execute(Client(os.environ["GH_TOKEN"]), args.source_sha, args.output.parent,
                         apply=args.apply)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except (RepairError, OSError, ValueError, KeyError, TypeError, AttributeError, IndexError,
            subprocess.SubprocessError) as exc:
        # Do not print signed download URLs, API headers or credential values.
        print("LEGACY_REVIEW_NAME_REPAIR_FAILED: " + type(exc).__name__, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
