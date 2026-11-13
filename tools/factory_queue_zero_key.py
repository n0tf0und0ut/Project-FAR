#!/usr/bin/env python3
"""Execute one REAL local coding-model smoke under a durable FAR factory lease.

Research-only bridge: it calls the existing pinned Ollama/Docker worker once,
retains raw worker evidence, and records the lease outcome. The worker smoke
makes a patch proposal, not a GitHub PR; therefore this bridge NEVER records
completion of the factory's build stage, even when visible tests pass.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from tools.software_factory import Factory, FactoryError, parse_order_text
from tools.factory_zero_key_smoke import manifest, run as run_worker

SCHEMA = "far-software-factory/queued-zero-key-attempt/1"
WORKER_ID = "zero-key-model"


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _identity(order: dict, task: dict, model_task: dict) -> None:
    """Reject any controller/worker input disagreement before claiming a lease."""
    if len(order["tasks"]) != 1 or order["tasks"][0]["depends_on"]:
        raise FactoryError("queued model smoke needs exactly one independent task")
    expected_repo = os.environ.get("GITHUB_REPOSITORY")
    if expected_repo and order["repository"].casefold() != expected_repo.casefold():
        raise FactoryError("work order repository differs from runner repository")
    if (order["base_sha"] != model_task["base_sha"]
            or task["id"] != model_task["task_id"].lower()
            or task["objective"] != model_task["task_text"]):
        raise FactoryError("queue and model worker source/task identity mismatch")


def run(db: Path, order_file: Path, repo: Path, task_file: Path, output: Path,
        *, invoke=None) -> dict:
    """Consume one real queue lease, invoke worker, and preserve a fail-closed receipt.

    `invoke` is a test seam; production uses the existing genuine Ollama worker.
    No fake/injected invocation is evidence of actual model execution.
    """
    repo, db, output = repo.resolve(), db.resolve(), output.resolve()
    if (output.exists() or output.is_symlink() or output.is_relative_to(repo)
            or db.is_relative_to(repo) or db == output or db.is_relative_to(output)):
        raise FactoryError("queue database and new artifact directory must be outside checkout")
    raw_order, raw_task = order_file.read_bytes(), task_file.read_bytes()
    if len(raw_order) > 65536 or len(raw_task) > 20000:
        raise FactoryError("oversized frozen work-order or model task")
    order = parse_order_text(raw_order.decode("utf-8", "strict"))
    model_task = manifest(raw_task)
    task = order["tasks"][0]
    _identity(order, task, model_task)
    # Record the attempt before accessing a potentially unavailable model.
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    f = Factory(db)
    submitted = f.submit(order)
    before = f.snapshot(order["id"])
    if any(t["stage"] != "build" for t in before["tasks"]):
        raise FactoryError("preexisting task is outside model build stage")
    claim = f.claim(order["id"], WORKER_ID, ttl=3600)
    if not claim or claim["stage"] != "build" or claim["task_id"] != task["id"]:
        raise FactoryError("no eligible build-stage lease for the frozen task")
    receipt = {
        "schema": SCHEMA, "order_id": order["id"], "task_id": task["id"],
        "work_order_sha256": submitted["sha256"],
        "work_order_source_sha256": sha256(raw_order),
        "model_task_source_sha256": sha256(raw_task),
        "base_sha": order["base_sha"], "repository": order["repository"],
        "worker_id": WORKER_ID, "lease_token_sha256": sha256(claim["token"].encode()),
        "started_at_unix": time.time(),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_event_sha_not_source": os.environ.get("GITHUB_SHA"),
        "attempt": len([h for h in f.snapshot(order["id"])["tasks"][0]["history"]
                        if h["event"] == "claimed"]),
        "worker_receipt_sha256": None,
        "worker_verdict": "NOT_STARTED", "queue_outcome": "UNKNOWN",
        "status": "RESEARCH_ONLY_NOT_AUTONOMOUS_PR_DELIVERY",
        "limitations": [
            "The queue invoked the model worker but did not create a PR.",
            "Visible tests and worker report cannot establish independent review.",
            "Output receipts and the SQLite database remain operator-controlled.",
            "Docker worktree grading is bounded, not complete runner isolation.",
        ],
    }
    # Never hand the lease capability to the model, or expose it in receipts.
    try:
        worker = (run_worker if invoke is None else invoke)(repo, task_file, output / "worker")
        receipt["worker_verdict"] = worker.get("verdict", "MISSING_VERDICT")
        worker_receipt = output / "worker" / "receipt.json"
        if worker_receipt.is_file():
            receipt["worker_receipt_sha256"] = sha256(worker_receipt.read_bytes())
        if receipt["worker_verdict"] == "VISIBLE_TESTS_PASSED_NOT_INDEPENDENTLY_VERIFIED":
            reason = "Model patch proposal has no GitHub PR; build stage cannot complete"
        else:
            reason = "Worker produced no verified candidate PR: " + str(receipt["worker_verdict"])[:90]
    except Exception as exc:
        # Avoid leaking arbitrary provider exception strings, which may hold secrets.
        receipt["worker_verdict"] = "WORKER_EXCEPTION"
        receipt["error_type"] = type(exc).__name__
        reason = "Worker invocation error: " + type(exc).__name__
    try:
        failed = f.fail(order["id"], task["id"], claim["token"], reason)
        receipt["queue_outcome"] = failed["state"]
        receipt["queue_attempts"] = failed["attempts"]
    finally:
        receipt["queue_snapshot"] = f.snapshot(order["id"])
        receipt["finished_at_unix"] = time.time()
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--order", type=Path, required=True)
    p.add_argument("--repository", type=Path, required=True)
    p.add_argument("--task-file", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        result = run(args.db, args.order, args.repository, args.task_file, args.output)
    except (FactoryError, OSError, ValueError, UnicodeError) as exc:
        print("QUEUE_MODEL_ATTEMPT_BLOCKED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps({k: result[k] for k in ("order_id", "task_id", "worker_verdict", "queue_outcome", "status")}, sort_keys=True))
    # Success means truthful attempt recording, *not* a successful model repair.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
