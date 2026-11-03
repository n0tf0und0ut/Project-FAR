"""Run isolated Codex-instruction tasks via one-shot local-model repair.

This is an exploratory, authored synthetic pilot, NOT the 30 historical FAR PR
tasks and NOT independent evidence. No keys or model credentials are required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import ast
import urllib.error
import signal
import selectors
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid
from pathlib import Path

from tools.workflow_efficacy_internal_fixtures import (
    task, fingerprint, public_test_code,
)

CONTROL_SHA = "38e6c8e8b3b1f0a7c75795c9eac8c1c6189cf7ab"
TREATMENT_SHA = "dc290674b755977378d6170a0128c1540f0a2b6a"
MODEL = "ollama/qwen2.5-coder:1.5b"
HARNESS_VERSION = "local-scripted-repair-v0.4"
MODEL_DIGEST = "d7372fd828518a4d38b1eb196c673c31a85f2ed302b3d1e406c4c2d1b64a0668"
MODEL_DIGEST_PREFIX = MODEL_DIGEST
MAX_SECONDS = 420
GRADER_SECONDS_PER_CASE = 10
MAX_CANDIDATE_OUTPUT_BYTES = 100_000
GRADER_IMAGE = "python:3.12-slim@sha256:b18b261e1b4974b4f321451ad5251ded85abb22c2b8b262da527dda1d031ab30"
CANDIDATE_STARTED = "FAR_CANDIDATE_STARTED_V1"
CANDIDATE_ENTRYPOINT = (
    "import json,runpy,sys\n"
    "payload=json.load(sys.stdin)\n"
    "sys.stdout.write('FAR_CANDIDATE_STARTED_V1\\n'); sys.stdout.flush()\n"
    "sys.stderr.write('FAR_CANDIDATE_STARTED_V1\\n'); sys.stderr.flush()\n"
    "candidate=runpy.run_path('/app/solution.py')\n"
    "value=candidate['transform'](payload)\n"
    "sys.stdout.write(json.dumps(value,allow_nan=False))\n"
)
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
    if value != MODEL_DIGEST:
        raise RuntimeError("unpinned or unexpected local model digest")
    return value


def sha256(data: bytes):
    return hashlib.sha256(data).hexdigest()


def candidate_output(text: str):
    """Strict JSON output: duplicate keys and nonfinite constants are errors."""
    prefix = CANDIDATE_STARTED + "\n"
    if text.startswith(prefix):
        text = text[len(prefix):]
    def reject_constant(value):
        raise ValueError(value)
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate output key")
            result[key] = value
        return result
    return json.loads(text, parse_constant=reject_constant,
                      object_pairs_hook=unique_object)


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


def capture_candidate_process(cmd, payload):
    """Bound both pipe buffers and the runtime of the Docker client."""
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    counts = {"stdout": 0, "stderr": 0}
    timed_out = output_limited = False
    deadline = time.monotonic() + GRADER_SECONDS_PER_CASE
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    try:
        proc.stdin.write(payload.encode())
        proc.stdin.close()
        with selectors.DefaultSelector() as ready:
            ready.register(proc.stdout, selectors.EVENT_READ, "stdout")
            ready.register(proc.stderr, selectors.EVENT_READ, "stderr")
            while ready.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    timed_out = True
                    break
                for key, _ in ready.select(min(remaining, 0.2)):
                    chunk = os.read(key.fileobj.fileno(), 8192)
                    if not chunk:
                        ready.unregister(key.fileobj)
                        continue
                    stream = key.data
                    counts[stream] += len(chunk)
                    buffers[stream].extend(chunk[:MAX_CANDIDATE_OUTPUT_BYTES-len(buffers[stream])])
                    if counts[stream] > MAX_CANDIDATE_OUTPUT_BYTES:
                        output_limited = True
                        break
                if output_limited:
                    break
        if not timed_out and not output_limited:
            try:
                proc.wait(timeout=max(0.001, deadline-time.monotonic()))
            except subprocess.TimeoutExpired:
                timed_out = True
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=10)
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            stream.close()
    return {"exit_code": None if timed_out or output_limited else proc.returncode,
            "stdout": buffers["stdout"].decode(errors="replace"),
            "stderr": buffers["stderr"].decode(errors="replace"),
            "stdout_bytes_observed": counts["stdout"],
            "stderr_bytes_observed": counts["stderr"],
            "timed_out": timed_out, "output_limited": output_limited}


def grade(source_path: Path, t: dict, scratch: Path):
    """Compare all six outputs outside the process running generated code.

    Only source and a single input enter each disposable container. Expected
    answers and the assertion machinery stay in this trusted host process.
    """
    grade_dir = scratch / "grade"
    grade_dir.mkdir(exist_ok=True)
    shutil.copyfile(source_path, grade_dir / "solution.py")
    comparisons = []
    for group in ("public", "hidden"):
        for index, example in enumerate(t[group]):
            name = "far-grade-" + uuid.uuid4().hex
            cmd = [
                "docker", "run", "--rm", "--name", name, "-i",
                "--network", "none", "--cap-drop", "ALL", "--read-only",
                "--security-opt", "no-new-privileges", "--memory", "384m",
                "--pids-limit", "64", "-v", str(grade_dir)+":/app:ro",
                "-w", "/app", GRADER_IMAGE,
                "python", "-I", "-B", "-c", CANDIDATE_ENTRYPOINT,
            ]
            row = {"group": group, "index": index, "status": "INFRA_FAILURE"}
            try:
                p = capture_candidate_process(cmd, json.dumps(example["input"]))
                row.update(p)
                if (p["stdout"].startswith(CANDIDATE_STARTED + "\n")
                        or CANDIDATE_STARTED in p["stderr"]):
                    row["status"] = "FAILURE"
                    if p["output_limited"]:
                        row["status"] = "OUTPUT_LIMIT"
                    elif p["timed_out"]:
                        row["status"] = "RESOURCE_LIMIT"
                    elif p["exit_code"] == 0:
                        try:
                            actual = candidate_output(p["stdout"])
                            row["status"] = "PASS" if actual == example["expected"] else "FAILURE"
                        except (ValueError, TypeError, RecursionError, OverflowError):
                            pass
            except subprocess.TimeoutExpired as exc:
                stderr = exc.stderr or b""
                if isinstance(stderr, bytes):
                    stderr = stderr.decode(errors="replace")
                row.update(stderr=stderr[:100_000], exit_code=None)
                if CANDIDATE_STARTED in stderr:
                    row["status"] = "RESOURCE_LIMIT"
            except OSError as exc:
                row["error_type"] = type(exc).__name__
            finally:
                # Killing only the Docker client does not stop a hung container.
                try:
                    cleanup = subprocess.run(["docker", "rm", "--force", name],
                                             text=True, capture_output=True, timeout=15)
                    if cleanup.returncode != 0 and "No such container" not in cleanup.stderr:
                        row["status"] = "INFRA_FAILURE"
                        row["cleanup_error"] = cleanup.stderr[:1000]
                except (OSError, subprocess.TimeoutExpired) as exc:
                    row["status"] = "INFRA_FAILURE"
                    row["cleanup_error"] = type(exc).__name__
            comparisons.append(row)
    executed = len(comparisons) == 6 and all(r["status"] != "INFRA_FAILURE" for r in comparisons)
    success = executed and all(r["status"] == "PASS" for r in comparisons)
    trace = json.dumps({"schema": "far-isolated-output-grade/1", "comparisons": comparisons,
                        "executed": executed, "success": success}, sort_keys=True)
    return success, (0 if success else 1) if executed else None, sha256(trace.encode()), trace, executed


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
        ["git", "diff", "--name-only", "HEAD"], cwd=folder, timeout=15
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


def extract_patch(text: str):
    """Accept only a full, syntactically valid transform implementation."""
    if not isinstance(text, str):
        return None
    fence = chr(96) * 3
    start = text.find(fence)
    if start >= 0:
        end = text.find(fence, start + 3)
        if end >= 0:
            body = text[start + 3:end].lstrip()
            if body.lower().startswith("python"):
                body = body[6:].lstrip()
            text = body
    code = text.strip()
    if not code.startswith(("def ", "from ", "import ", "#")) and "def transform(" in code:
        code = code[code.index("def transform("):]
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, TypeError):
        return None
    if not any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "transform"
               for n in tree.body):
        return None
    return code + "\n"


def local_patch_request(instruction_bytes: bytes, case: dict):
    """Make one genuine local generation call; no hidden expected values sent."""
    body = {
        "model": "qwen2.5-coder:1.5b", "stream": False,
        "keep_alive": "5m",
        "options": {"temperature": 0, "seed": 0, "num_ctx": 16384, "num_predict": 512},
        "messages": [
            {"role": "system", "content": instruction_bytes.decode() +
             "\nYou are an automated code-repair engine. Respond ONLY with a complete "
             "Python source file defining transform(payload). No explanations."},
            {"role": "user", "content":
             "Task: " + case["task_id"] + "\nRequirement: " + case["spec"] +
             "\nExisting solution.py:\n" + case["source"] +
             "\nPublic input/output examples:\n" +
             json.dumps(case["public"], sort_keys=True) +
             "\nReturn the corrected full Python file, and nothing else."},
        ],
    }
    request_bytes = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat", data=request_bytes,
        headers={"Content-Type": "application/json"}, method="POST")
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=MAX_SECONDS) as response:
            result = json.load(response)
        message = result.get("message") if isinstance(result, dict) else None
        answer = message.get("content") if isinstance(message, dict) else None
        input_count = result.get("prompt_eval_count") if isinstance(result, dict) else None
        output_count = result.get("eval_count") if isinstance(result, dict) else None
        valid = (isinstance(result, dict) and result.get("done") is True
                 and isinstance(answer, str) and type(input_count) is int and input_count > 0
                 and type(output_count) is int and output_count > 0)
        metrics = {"model_steps": int(valid),
                   "input_tokens": input_count if type(input_count) is int else 0,
                   "output_tokens": output_count if type(output_count) is int else 0,
                   "reported_cost_usd": 0.0,
                   "error_events": 0 if valid else 1}
        if not valid or metrics["input_tokens"] <= 0:
            return None, json.dumps(result, sort_keys=True), metrics, None, False, time.monotonic()-started
        return answer, json.dumps(result, sort_keys=True), metrics, 0, False, time.monotonic()-started
    except (TimeoutError, OSError, ValueError, KeyError) as exc:
        metrics = {"model_steps": 0, "input_tokens": 0, "output_tokens": 0,
                   "reported_cost_usd": 0.0, "error_events": 1}
        return None, json.dumps({"error_type": type(exc).__name__}), metrics, None, \
            isinstance(exc, TimeoutError), time.monotonic()-started


def run_arm(index: int, arm: str, root: Path, evidence_root: Path):
    case = task(index)
    digest = local_model_digest()
    folder, instruction_hash = setup_workspace(index, arm, root)
    answer, raw, metrics, exit_code, timed_out, elapsed = local_patch_request(
        instructions(arm), case)
    patch = extract_patch(answer)
    if patch is not None:
        (folder / "solution.py").write_text(patch)
    unauthorized = unauthorized_file_changes(folder, {"solution.py"})
    success, code, grader_hash, trace, graded = grade(folder / "solution.py", case, root)
    evidence_path = evidence_root / (case["task_id"] + "-" + arm)
    evidence_path.mkdir(parents=True, exist_ok=False)
    (evidence_path / "submitted-solution.py").write_bytes((folder / "solution.py").read_bytes())
    (evidence_path / "agent-events.ndjson").write_text(raw)
    (evidence_path / "grader-trace.txt").write_text(trace)
    success = bool(success and graded and patch is not None
                   and (folder / "solution.py").read_bytes() != case["source"].encode()
                   and not unauthorized and not timed_out
                   and exit_code == 0 and metrics["model_steps"] == 1
                   and metrics["error_events"] == 0)
    return {
        "schema": "far-workflow-scripted-repair-observation/0.4",
        "execution_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                                    timeout=15).decode().strip(),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "task_id": case["task_id"], "arm": arm,
        "model_alias": MODEL, "model_digest": digest,
        "harness_version": HARNESS_VERSION,
        "corpus_hash": fingerprint(), "instructions_sha256": instruction_hash,
        "source_before_sha256": sha256(case["source"].encode()),
        "source_after_sha256": sha256((folder / "solution.py").read_bytes()),
        "elapsed_seconds": round(elapsed, 3),
        "cli_exit_code": exit_code, "timeout": timed_out,
        "unauthorized_changes": unauthorized,
        "grader_exit_code": code, "grader_trace_hash": grader_hash,
        "grader_status": "EXECUTED" if graded else "INFRA_FAILURE",
        "outcome": "SUCCESS" if success else "FAILURE",
        "patch_parsed": patch is not None,
        "raw_event_stream_sha256": sha256(raw.encode()), **metrics,
    }


def run_isolated_pair(index: int, evidence_root: Path):
    payload = []
    for arm in order_for(index):
        with tempfile.TemporaryDirectory(prefix="fwe-isolated-" + arm + "-") as tmp:
            payload.append(run_arm(index, arm, Path(tmp), evidence_root))
    return payload


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("schedule", "run-pair", "contract"))
    parser.add_argument("--index", type=int)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.action == "contract":
        payload = {"model_alias": MODEL, "model_digest": MODEL_DIGEST,
                   "harness_version": HARNESS_VERSION,
                   "corpus_hash": fingerprint(), "max_seconds_per_arm": MAX_SECONDS,
                   "arm_shas": {"control": CONTROL_SHA, "treatment": TREATMENT_SHA},
                   "grader_image": GRADER_IMAGE,
                   "grader_seconds_per_comparison": GRADER_SECONDS_PER_CASE,
                   "generation_options": {"temperature": 0, "seed": 0, "num_ctx": 16384, "num_predict": 512},
                   "timing_scope": "model_generation_only",
                   "weights_digest_pinned": True,
                   "cross_hardware_determinism_established": False}
    elif args.action == "schedule":
        payload = [{"task_id": task(i)["task_id"], "arm_order": order_for(i)}
                   for i in range(30)]
    else:
        if args.index is None or not 0 <= args.index < 30 or args.output is None:
            parser.error("run-pair requires --index 0..29 and --output")
        evidence_root = args.output.parent / "evidence"
        payload = run_isolated_pair(args.index, evidence_root)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
