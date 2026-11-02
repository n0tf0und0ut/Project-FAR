"""Run isolated Codex-instruction pilot tasks via a keyless OpenCode agent.

This is an exploratory, authored synthetic pilot, NOT the 30 historical FAR PR
tasks and NOT independent evidence. No keys or model credentials are required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from tools.workflow_efficacy_internal_fixtures import (
    task, fingerprint, public_test_code, hidden_test_code,
)

CONTROL_SHA = "38e6c8e8b3b1f0a7c75795c9eac8c1c6189cf7ab"
TREATMENT_SHA = "dc290674b755977378d6170a0128c1540f0a2b6a"
MODEL = "ollama/qwen2.5-coder:1.5b"
OPENCODE_VERSION = "1.19.3"
MODEL_DIGEST_PREFIX = "d7372fd82851"
MAX_SECONDS = 240
ARMS = ("control", "treatment")
ROOT = Path(__file__).resolve().parents[1]
SAFE_CONFIG = {
    "$schema": "https://opencode.ai/config.json",
    "model": MODEL,
    "provider": {
        "ollama": {
            "npm": "@ai-sdk/openai-compatible",
            "name": "Pinned locally hosted Ollama",
            "options": {"baseURL": "http://127.0.0.1:11434/v1"},
            "models": {"qwen2.5-coder:1.5b": {
                "name": "Qwen2.5 Coder 1.5B Q4_K_M",
                "limit": {"context": 16384, "output": 2048}
            }},
        },
    },
    "permission": {
        "read": "allow", "edit": "allow", "glob": "allow",
        "grep": "allow", "list": "allow", "external_directory": "deny",
        "webfetch": "deny", "websearch": "deny", "task": "deny",
        "question": "deny", "bash": {"*": "deny", "python -m unittest*": "allow"},
    },
    "agent": {"build": {"steps": 10}},
}


def local_model_digest():
    """Read the real local Ollama registry, never infer a model ID from a tag."""
    with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=10) as response:
        tags = json.load(response)
    matches = [m for m in tags.get("models", []) if m.get("name") == "qwen2.5-coder:1.5b"]
    if len(matches) != 1:
        raise RuntimeError("expected exactly one installed local model")
    value = matches[0].get("digest")
    if not isinstance(value, str) or not value.startswith(MODEL_DIGEST_PREFIX):
        raise RuntimeError("unpinned or unexpected local model digest")
    return value


def sha256(data: bytes):
    return hashlib.sha256(data).hexdigest()


def git_show(revision: str, path: str) -> bytes:
    return subprocess.check_output(["git", "show", revision+":"+path], cwd=ROOT,
                                   timeout=20)


def instructions(arm: str):
    if arm not in ARMS:
        raise ValueError(arm)
    commit = CONTROL_SHA if arm == "control" else TREATMENT_SHA
    body = git_show(commit, "AGENTS.md")
    if arm == "treatment":
        body += b"\n\n" + git_show(commit, "docs/maintenance/agent-workflow-orchestration.md")
    return body


def order_for(index: int):
    # Balanced, deterministic prospective assignment: exactly 15 of each first arm.
    if index < 0 or index >= 30:
        raise ValueError(index)
    keys = sorted((hashlib.sha256(("fwe-free-v0.2|" + task(i)["task_id"]).encode()).hexdigest(), i)
                  for i in range(30))
    control_first = {i for _, i in keys[:15]}
    return ARMS if index in control_first else tuple(reversed(ARMS))


def setup_workspace(index: int, arm: str, root: Path):
    t = task(index)
    folder = root / ("case-" + t["task_id"] + "-" + arm)
    folder.mkdir()
    source = t["source"].encode()
    (folder / "solution.py").write_bytes(source)
    (folder / "test_public.py").write_text(public_test_code(t))
    (folder / "README.md").write_text(
        "Task ID: " + t["task_id"] + "\n\n" + t["spec"]
        + "\n\nImplement transform(payload) in solution.py, preserving Python 3.12 semantics."
        + " The visible tests are examples; address nontrivial edge cases.\n")
    (folder / "opencode.json").write_text(json.dumps(SAFE_CONFIG, sort_keys=True))
    (folder / ".gitignore").write_text("__pycache__/\n*.pyc\n")
    # One agent uses Codex's exact pre/post instruction content. No Claude mixing.
    instruction_bytes = instructions(arm)
    (folder / "AGENTS.md").write_bytes(instruction_bytes)
    subprocess.run(["git", "init", "-q"], cwd=folder, check=True, timeout=15)
    subprocess.run(["git", "add", "."], cwd=folder, check=True, timeout=15)
    subprocess.run(["git", "-c", "user.name=FAR Pilot", "-c",
                    "user.email=far-pilot@example.invalid",
                    "commit", "-qm", "frozen agent task"], cwd=folder, check=True, timeout=15)
    return folder, sha256(instruction_bytes)


def grade(source_path: Path, t: dict, scratch: Path):
    """Grade both public and hidden tests in a fresh no-network container."""
    grade_dir = scratch / "grade"
    grade_dir.mkdir(exist_ok=True)
    shutil.copyfile(source_path, grade_dir / "solution.py")
    (grade_dir / "test_hidden.py").write_text(hidden_test_code(t))
    (grade_dir / "test_public.py").write_text(public_test_code(t))
    cmd = [
        "docker", "run", "--rm", "--network", "none", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges", "--memory", "384m",
        "--pids-limit", "64", "-v", str(grade_dir)+":/app:ro",
        "-w", "/app", "python:3.12-slim",
        "python", "-m", "unittest", "-q", "test_public", "test_hidden",
    ]
    try:
        p = subprocess.run(cmd, text=True, capture_output=True, timeout=60)
        trace = (p.stdout + p.stderr)[:1_000_000]
        # The test command must genuinely execute, not merely return a status.
        executed = p.returncode in (0, 1) and "Ran 2 tests" in trace
        return executed and p.returncode == 0, p.returncode, sha256(trace.encode()), trace, executed
    except (subprocess.TimeoutExpired, OSError) as exc:
        return False, None, None, type(exc).__name__, False


def parse_events(raw: str):
    calls, input_tokens, output_tokens, reported_cost, error_events = 0, 0, 0, 0.0, 0
    for line in raw.splitlines():
        try:
            obj = json.loads(line)
        except (ValueError, TypeError):
            continue
        if obj.get("type") == "error":
            error_events += 1
        part = obj.get("part")
        if not isinstance(part, dict):
            part = obj.get("properties", {}).get("part", {})
        if not isinstance(part, dict) or part.get("type") != "step-finish":
            continue
        calls += 1
        tok = part.get("tokens") or {}
        input_tokens += int(tok.get("input") or 0)
        output_tokens += int(tok.get("output") or 0)
        reported_cost += float(part.get("cost") or 0)
    return {"model_steps": calls, "input_tokens": input_tokens,
            "output_tokens": output_tokens, "reported_cost_usd": reported_cost,
            "error_events": error_events}


def unauthorized_file_changes(folder: Path, allowed: set[str]):
    modified = subprocess.check_output(
        ["git", "diff", "--name-only"], cwd=folder, timeout=15
    ).decode().splitlines()
    untracked = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard"], cwd=folder, timeout=15
    ).decode().splitlines()
    return sorted((set(modified) | set(untracked)) - allowed)


def execute_agent_process(command, folder: Path, env: dict, timeout: float):
    """Execute an agent in its own process group and reap descendants on timeout.

    SIGTERM is issued to the entire group first; SIGKILL is then issued to
    any survivors before the workspace is inspected or graded.
    """
    try:
        proc = subprocess.Popen(command, cwd=folder, env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                start_new_session=True)
    except OSError:
        return None, "", False
    try:
        stdout, _stderr = proc.communicate(timeout=timeout)
        return proc.returncode, (stdout or "")[:2_000_000], False
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            stdout, _stderr = proc.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            stdout = ""
        finally:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            # The process must have terminated before any grading occurs.
            stdout, _stderr = proc.communicate(timeout=10)
        return None, (stdout or "")[:2_000_000], True


def run_arm(index: int, arm: str, root: Path, evidence_root: Path):
    t = task(index)
    digest = local_model_digest()
    folder, instruction_hash = setup_workspace(index, arm, root)
    agent_home = root / ("isolated-home-" + t["task_id"] + "-" + arm)
    agent_home.mkdir()
    env = {k: os.environ[k] for k in ("PATH", "LANG", "LC_ALL", "TERM", "NODE_PATH")
           if k in os.environ}
    env.update({"HOME": str(agent_home), "XDG_CONFIG_HOME": str(agent_home/"config"),
                "XDG_DATA_HOME": str(agent_home/"data"),
                "XDG_CACHE_HOME": str(agent_home/"cache"),
                "OPENCODE_DISABLE_AUTOUPDATE": "1", "CI": "true",
                "PYTHONDONTWRITEBYTECODE": "1"})
    prompt = ("Follow AGENTS.md exactly. Read README.md and solution.py; fix the "
              "implementation to satisfy the specification. Run the public "
              "tests with python -m unittest -q test_public, do not edit tests. "
              "Stop after verifying and describe the outcome.")
    command = ["opencode", "run", "-m", MODEL, "--format", "json", prompt]
    start = time.monotonic()
    exit_code, raw, timed_out = execute_agent_process(command, folder, env, MAX_SECONDS)
    metrics = parse_events(raw)
    unauthorized = unauthorized_file_changes(folder, {"solution.py"})
    success, grader_code, grader_hash, grader_trace, graded = grade(folder / "solution.py", t, root)
    evidence_path = evidence_root / (t["task_id"] + "-" + arm)
    evidence_path.mkdir(parents=True, exist_ok=False)
    (evidence_path / "submitted-solution.py").write_bytes((folder / "solution.py").read_bytes())
    (evidence_path / "agent-events.ndjson").write_text(raw)
    (evidence_path / "grader-trace.txt").write_text(grader_trace)
    success = bool(success and graded and (folder/"solution.py").read_bytes() != t["source"].encode()
                   and not unauthorized and not timed_out and
                   exit_code == 0 and metrics["model_steps"] > 0 and
                   metrics["error_events"] == 0 and
                   metrics["reported_cost_usd"] == 0)
    return {
        "schema": "far-workflow-free-agent-observation/0.2",
        "task_id": t["task_id"], "arm": arm,
        "model_alias": MODEL, "model_digest": digest,
        "opencode_version": OPENCODE_VERSION,
        "corpus_hash": fingerprint(), "instructions_sha256": instruction_hash,
        "source_before_sha256": sha256(t["source"].encode()),
        "source_after_sha256": sha256((folder/"solution.py").read_bytes()),
        "elapsed_seconds": round(time.monotonic()-start, 3),
        "cli_exit_code": exit_code, "timeout": timed_out,
        "unauthorized_changes": unauthorized,
        "grader_exit_code": grader_code, "grader_trace_hash": grader_hash,
        "grader_status": "EXECUTED" if graded else "INFRA_FAILURE",
        "outcome": "SUCCESS" if success else "FAILURE",
        "raw_event_stream_sha256": sha256(raw.encode()), **metrics,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("schedule", "run-pair", "contract"))
    parser.add_argument("--index", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.action == "contract":
        payload = {"model_alias": MODEL, "model_digest": MODEL_DIGEST_PREFIX,
                   "opencode_version": OPENCODE_VERSION,
                   "corpus_hash": fingerprint(), "max_seconds_per_arm": MAX_SECONDS,
                   "arm_shas": {"control": CONTROL_SHA, "treatment": TREATMENT_SHA},
                   "free_alias_not_immutable_provider_snapshot": True}
    elif args.action == "schedule":
        payload = [{"task_id": task(i)["task_id"], "arm_order": order_for(i)}
                   for i in range(30)]
    else:
        if args.index is None or not 0 <= args.index < 30 or args.output is None:
            parser.error("run-pair requires --index 0..29 and --output")
        with tempfile.TemporaryDirectory(prefix="fwe-") as tmp:
            root = Path(tmp)
            evidence_root = args.output.parent / "evidence"
            payload = [run_arm(args.index, arm, root, evidence_root) for arm in order_for(args.index)]
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
