#!/usr/bin/env python3
"""Provider-neutral, fail-closed software-factory work queue.

Operational Research prototype. Recorded worker evidence is not an independent
review, live GitHub check, protected merge authorization, or scientific result.
The factory never writes source code, pushes, reviews, or merges on its own.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
import sqlite3
import sys
import time
import os
import urllib.request
from pathlib import Path

SCHEMA = "far-software-factory/work-order/1"
STAGES = ("build", "test", "review")
SHA = re.compile(r"[0-9a-f]{40}\Z")
IDENT = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")


class FactoryError(ValueError):
    pass


def canonical(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(obj: object) -> str:
    return hashlib.sha256(canonical(obj).encode("utf-8")).hexdigest()


def validate_order(data: object) -> dict:
    if not isinstance(data, dict) or set(data) != {"schema", "id", "repository", "base_sha", "tasks"}:
        raise FactoryError("work order must have exactly schema, id, repository, base_sha, tasks")
    if data["schema"] != SCHEMA or not isinstance(data["id"], str) or not IDENT.fullmatch(data["id"]):
        raise FactoryError("unsupported schema or invalid order id")
    if not isinstance(data["repository"], str) or not REPO.fullmatch(data["repository"]):
        raise FactoryError("invalid owner/repository")
    if not isinstance(data["base_sha"], str) or not SHA.fullmatch(data["base_sha"]):
        raise FactoryError("base_sha must be exact Git SHA")
    tasks = data["tasks"]
    if not isinstance(tasks, list) or not tasks:
        raise FactoryError("tasks must be a nonempty list")
    by_id = {}
    for task in tasks:
        if not isinstance(task, dict) or set(task) != {"id", "objective", "acceptance", "depends_on"}:
            raise FactoryError("task keys must be id, objective, acceptance, depends_on")
        key = task["id"]
        if not isinstance(key, str) or not IDENT.fullmatch(key) or key in by_id:
            raise FactoryError("duplicate or invalid task id")
        if not isinstance(task["objective"], str) or not task["objective"].strip():
            raise FactoryError("task objective is required")
        if (not isinstance(task["acceptance"], list) or not task["acceptance"]
                or any(not isinstance(x, str) or not x.strip() for x in task["acceptance"])):
            raise FactoryError("acceptance must contain testable nonempty statements")
        deps = task["depends_on"]
        if not isinstance(deps, list) or len(deps) != len(set(map(str, deps))):
            raise FactoryError("task depends_on must be unique")
        if any(not isinstance(x, str) or not IDENT.fullmatch(x) for x in deps):
            raise FactoryError("invalid dependency id")
        by_id[key] = task
    for task in tasks:
        if any(dep not in by_id or dep == task["id"] for dep in task["depends_on"]):
            raise FactoryError("unknown or self dependency")
    visiting, visited = set(), set()
    def visit(key):
        if key in visiting:
            raise FactoryError("cyclic dependency")
        if key not in visited:
            visiting.add(key)
            for dep in by_id[key]["depends_on"]:
                visit(dep)
            visiting.remove(key)
            visited.add(key)
    for key in by_id:
        visit(key)
    return data


def parse_order_text(raw: str) -> dict:
    """Parse one unambiguous RFC 8259 JSON work order before hashing or storage.

    json.loads normally accepts duplicate object members and NaN/Infinity tokens;
    both would make the claimed input provenance ambiguous or nonstandard.
    Reject them at the raw intake boundary, including nested object members.
    The in-memory submit API continues to accept already validated Python dicts.
    """
    if not isinstance(raw, str):
        raise FactoryError("work order source must be UTF-8 text")

    def unique_members(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise FactoryError(f"duplicate JSON object key: {key!r}")
            result[key] = value
        return result

    def reject_constant(value):
        raise FactoryError(f"non-finite JSON token is prohibited: {value}")

    try:
        parsed = json.loads(raw, object_pairs_hook=unique_members,
                            parse_constant=reject_constant)
    except json.JSONDecodeError as exc:
        raise FactoryError(f"malformed JSON: {exc.msg}") from exc
    return validate_order(parsed)


class Factory:
    def __init__(self, path: str | Path):
        self.db = sqlite3.connect(path, timeout=30, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA busy_timeout=30000")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS orders(
                id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS tasks(
                order_id TEXT NOT NULL, id TEXT NOT NULL,
                stage INTEGER NOT NULL DEFAULT 0, state TEXT NOT NULL DEFAULT 'queued',
                attempts INTEGER NOT NULL DEFAULT 0, token TEXT, worker TEXT,
                lease_until REAL, history TEXT NOT NULL DEFAULT '[]',
                PRIMARY KEY(order_id,id), FOREIGN KEY(order_id) REFERENCES orders(id));
        """)

    def _tx(self, fn):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            result = fn()
            self.db.execute("COMMIT")
            return result
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def submit(self, order: dict) -> dict:
        validate_order(order)
        h = digest(order)
        def apply():
            old = self.db.execute("SELECT sha256 FROM orders WHERE id=?", (order["id"],)).fetchone()
            if old:
                if old["sha256"] != h:
                    raise FactoryError("existing order id has different immutable content")
                return {"order_id": order["id"], "sha256": h, "idempotent": True}
            self.db.execute("INSERT INTO orders VALUES(?,?,?)", (order["id"], h, canonical(order)))
            for task in order["tasks"]:
                self.db.execute("INSERT INTO tasks(order_id,id) VALUES (?,?)", (order["id"], task["id"]))
            return {"order_id": order["id"], "sha256": h, "idempotent": False}
        return self._tx(apply)

    def snapshot(self, order_id: str) -> dict:
        row = self.db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        if row is None:
            raise FactoryError("unknown order")
        order = json.loads(row["data"])
        rows = self.db.execute("SELECT * FROM tasks WHERE order_id=? ORDER BY id", (order_id,)).fetchall()
        return {"order_id": order_id, "sha256": row["sha256"], "repository": order["repository"],
                "authority": "ADVISORY_ONLY", "tasks": [{"id": t["id"], "stage": STAGES[t["stage"]] if t["stage"] < len(STAGES) else "awaiting_protected_merge",
                "state": t["state"], "attempts": t["attempts"], "worker": t["worker"],
                "history": json.loads(t["history"])} for t in rows]}

    def claim(self, order_id: str, worker: str, now: float | None = None, ttl: int = 900,
              max_attempts: int = 3) -> dict | None:
        if not isinstance(worker, str) or not IDENT.fullmatch(worker) or ttl < 1 or ttl > 86400 or max_attempts < 1:
            raise FactoryError("invalid worker or lease duration")
        moment = time.time() if now is None else now
        def apply():
            row = self.db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
            if not row:
                raise FactoryError("unknown order")
            data = json.loads(row["data"])
            task_by_id = {x["id"]: x for x in data["tasks"]}
            rows = {t["id"]: t for t in self.db.execute("SELECT * FROM tasks WHERE order_id=?", (order_id,))}
            for task_id in sorted(rows):
                t = rows[task_id]
                if t["stage"] >= len(STAGES) or t["state"] == "failed":
                    continue
                if any(rows[d]["state"] != "delivered" for d in task_by_id[task_id]["depends_on"]):
                    continue
                if t["state"] == "running" and t["lease_until"] > moment:
                    continue
                if t["attempts"] >= max_attempts:
                    history = json.loads(t["history"])
                    history.append({"event": "lease_retries_exhausted", "stage": STAGES[t["stage"]], "at": moment})
                    self.db.execute("""UPDATE tasks SET state='failed', token=NULL, worker=NULL,
                                    lease_until=NULL, history=? WHERE order_id=? AND id=?""",
                                    (canonical(history), order_id, task_id))
                    continue
                token = secrets.token_urlsafe(32)
                history = json.loads(t["history"])
                history.append({"event": "claimed", "stage": STAGES[t["stage"]], "worker": worker,
                                "at": moment, "attempt": t["attempts"] + 1})
                self.db.execute("""UPDATE tasks SET state='running', token=?, worker=?, lease_until=?,
                               attempts=attempts+1, history=? WHERE order_id=? AND id=?""",
                                (token, worker, moment + ttl, canonical(history), order_id, task_id))
                return {"order_id": order_id, "task_id": task_id, "stage": STAGES[t["stage"]],
                        "token": token, "expires_at": moment + ttl, "work_order_sha256": row["sha256"],
                        "task": task_by_id[task_id], "repository": data["repository"], "base_sha": data["base_sha"]}
            return None
        return self._tx(apply)

    def record(self, order_id: str, task_id: str, token: str, evidence: dict, now: float | None = None) -> dict:
        moment = time.time() if now is None else now
        if not isinstance(evidence, dict):
            raise FactoryError("evidence must be a JSON object")
        def apply():
            t = self.db.execute("SELECT * FROM tasks WHERE order_id=? AND id=?", (order_id, task_id)).fetchone()
            if not t or t["state"] != "running" or not secrets.compare_digest(str(t["token"]), str(token)):
                raise FactoryError("invalid or stale work lease")
            if t["lease_until"] <= moment:
                raise FactoryError("lease expired")
            stage = STAGES[t["stage"]]
            history = json.loads(t["history"])
            if stage == "build":
                if set(evidence) != {"head_sha", "pr_number", "branch"}:
                    raise FactoryError("build evidence needs head_sha, pr_number, branch")
                if (not isinstance(evidence["head_sha"], str) or not SHA.fullmatch(evidence["head_sha"])
                    or type(evidence["pr_number"]) is not int or evidence["pr_number"] < 1
                    or not isinstance(evidence["branch"], str) or not evidence["branch"].strip()):
                    raise FactoryError("invalid build evidence")
            elif stage == "test":
                build = next((e["evidence"] for e in history if e["event"] == "completed" and e["stage"] == "build"), None)
                if set(evidence) != {"head_sha", "checks", "result"} or evidence.get("head_sha") != build["head_sha"]:
                    raise FactoryError("tests must be bound to built exact head")
                if (evidence["result"] != "passed" or not isinstance(evidence["checks"], list)
                    or not evidence["checks"] or any(not isinstance(x, str) or not x for x in evidence["checks"])):
                    raise FactoryError("positive test evidence required")
            else:
                build = next(e["evidence"] for e in history if e["event"] == "completed" and e["stage"] == "build")
                if set(evidence) != {"head_sha", "reviewer", "review_url", "result", "unresolved"}:
                    raise FactoryError("review evidence fields invalid")
                builder = next(e["worker"] for e in history if e["event"] == "completed" and e["stage"] == "build")
                if (evidence["head_sha"] != build["head_sha"]
                    or evidence["reviewer"] in {t["worker"], builder}
                    or not isinstance(evidence["reviewer"], str) or not evidence["reviewer"].strip()
                    or not isinstance(evidence["review_url"], str) or not evidence["review_url"].startswith("https://github.com/")
                    or evidence["result"] != "clean" or evidence["unresolved"] != 0
                    or type(evidence["unresolved"]) is not int):
                    raise FactoryError("review not exact-head, independent, and clean")
            history.append({"event": "completed", "stage": stage, "worker": t["worker"],
                            "at": moment, "evidence_sha256": digest(evidence), "evidence": evidence})
            advanced = t["stage"] + 1
            new_state = "awaiting_protected_merge" if advanced == len(STAGES) else "queued"
            self.db.execute("""UPDATE tasks SET stage=?, state=?, attempts=0, token=NULL, worker=NULL,
                            lease_until=NULL, history=? WHERE order_id=? AND id=?""",
                            (advanced, new_state, canonical(history), order_id, task_id))
            return {"stage_completed": stage, "state": new_state, "evidence_sha256": digest(evidence),
                    "note": "worker-reported evidence only; independent live GitHub verification still required"}
        return self._tx(apply)

    def reconcile_delivery(self, order_id: str, task_id: str, fetch_json=None) -> dict:
        """Observe a merged PR on protected main. Never creates or authorizes a merge.

        This records observed GitHub state only; it does not reconstruct historical
        independent reviews, protected App checks, or the merge's authorization.
        """
        def apply():
            row = self.db.execute("SELECT data FROM orders WHERE id=?", (order_id,)).fetchone()
            t = self.db.execute("SELECT * FROM tasks WHERE order_id=? AND id=?", (order_id, task_id)).fetchone()
            if not row or not t or t["state"] != "awaiting_protected_merge":
                raise FactoryError("task has not completed recorded review stages")
            order = json.loads(row["data"])
            repo = order["repository"]
            history = json.loads(t["history"])
            build = next(e["evidence"] for e in history if e["event"] == "completed" and e["stage"] == "build")
            if fetch_json is None:
                def read(url):
                    headers = {"Accept": "application/vnd.github+json", "User-Agent": "far-software-factory/0.1"}
                    if os.environ.get("GITHUB_TOKEN"):
                        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
                    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=15) as response:
                        return json.load(response)
                lookup = read
            else:
                lookup = fetch_json
            root = "https://api.github.com/repos/" + repo
            pr = lookup(f"{root}/pulls/{build['pr_number']}")
            if (pr.get("state") != "closed" or pr.get("merged") is not True
                    or not pr.get("merged_at") or (pr.get("head") or {}).get("sha") != build["head_sha"]
                    or (pr.get("base") or {}).get("ref") != "main"
                    or ((pr.get("base") or {}).get("repo") or {}).get("full_name") != repo):
                raise FactoryError("GitHub PR not merged on intended main from recorded exact head")
            merge_sha = pr.get("merge_commit_sha")
            if not isinstance(merge_sha, str) or not SHA.fullmatch(merge_sha):
                raise FactoryError("invalid merge commit identity")
            branch = lookup(f"{root}/branches/main")
            current = (branch.get("commit") or {}).get("sha")
            if not isinstance(current, str) or not SHA.fullmatch(current):
                raise FactoryError("invalid live main SHA")
            ancestry = lookup(f"{root}/compare/{merge_sha}...{current}")
            if ancestry.get("status") not in {"ahead", "identical"}:
                raise FactoryError("merged commit not an ancestor of current main")
            evidence = {"pr_number": build["pr_number"], "head_sha": build["head_sha"],
                        "merge_commit_sha": merge_sha, "main_sha": current}
            history.append({"event": "github_merge_observed", "stage": "delivery", "at": time.time(),
                            "evidence": evidence, "evidence_sha256": digest(evidence)})
            self.db.execute("UPDATE tasks SET state='delivered', history=? WHERE order_id=? AND id=?",
                            (canonical(history), order_id, task_id))
            return {"state": "delivered", "observation": evidence,
                    "note": "read-only GitHub merge and ancestry observation; historical gate provenance not evaluated"}
        return self._tx(apply)

    def fail(self, order_id: str, task_id: str, token: str, reason: str, now: float | None = None,
             max_attempts: int = 3) -> dict:
        moment = time.time() if now is None else now
        if not reason.strip() or max_attempts < 1:
            raise FactoryError("failure reason and retry bound required")
        def apply():
            t = self.db.execute("SELECT * FROM tasks WHERE order_id=? AND id=?", (order_id, task_id)).fetchone()
            if not t or t["state"] != "running" or not secrets.compare_digest(str(t["token"]), str(token)):
                raise FactoryError("invalid or stale work lease")
            if t["lease_until"] <= moment:
                raise FactoryError("lease expired")
            state = "failed" if t["attempts"] >= max_attempts else "queued"
            hist = json.loads(t["history"])
            hist.append({"event": "failed", "stage": STAGES[t["stage"]], "worker": t["worker"],
                         "at": moment, "reason": reason})
            self.db.execute("""UPDATE tasks SET state=?, token=NULL, worker=NULL, lease_until=NULL,
                            history=? WHERE order_id=? AND id=?""",
                            (state, canonical(hist), order_id, task_id))
            return {"state": state, "attempts": t["attempts"]}
        return self._tx(apply)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", required=True, help="SQLite database path")
    sub = p.add_subparsers(dest="action", required=True)
    s = sub.add_parser("submit"); s.add_argument("order_file")
    s = sub.add_parser("status"); s.add_argument("order_id")
    s = sub.add_parser("claim"); s.add_argument("order_id"); s.add_argument("worker")
    s = sub.add_parser("record"); s.add_argument("order_id"); s.add_argument("task_id"); s.add_argument("token"); s.add_argument("evidence_file")
    s = sub.add_parser("fail"); s.add_argument("order_id"); s.add_argument("task_id"); s.add_argument("token"); s.add_argument("reason")
    s = sub.add_parser("reconcile-delivery"); s.add_argument("order_id"); s.add_argument("task_id")
    args = p.parse_args(argv)
    try:
        store = Factory(args.db)
        if args.action == "submit":
            value = store.submit(parse_order_text(Path(args.order_file).read_text(encoding="utf-8")))
        elif args.action == "status":
            value = store.snapshot(args.order_id)
        elif args.action == "claim":
            value = store.claim(args.order_id, args.worker)
        elif args.action == "record":
            value = store.record(args.order_id, args.task_id, args.token, json.loads(Path(args.evidence_file).read_text()))
        elif args.action == "reconcile-delivery":
            value = store.reconcile_delivery(args.order_id, args.task_id)
        else:
            value = store.fail(args.order_id, args.task_id, args.token, args.reason)
        print(json.dumps(value, sort_keys=True, indent=2))
        return 0
    except (FactoryError, OSError, ValueError, sqlite3.Error, urllib.error.URLError) as exc:
        print(f"software-factory: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
