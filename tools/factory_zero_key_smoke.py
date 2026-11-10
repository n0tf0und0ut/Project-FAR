#!/usr/bin/env python3
"""One-shot, read-only Research smoke of the existing zero-key local coding model.

Only proposes a patch to one exact Git worktree path. It cannot write a GitHub
branch, approve its own result, or claim a registered factory/control outcome.
Its candidate code is executed only inside a credential-free, network-disabled,
read-only Docker container, never on the host Python interpreter.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import selectors
import signal
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import subprocess
import tempfile
import time
import urllib.request

SCHEMA = "far-factory-zero-key-smoke/1"
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA1 = re.compile(r"[0-9a-f]{40}\Z")
CHECK = re.compile(r"test_[A-Za-z0-9_]+\Z")
MODEL = "qwen2.5-coder:1.5b"
MODEL_DIGEST = "d7372fd828518a4d38b1eb196c673c31a85f2ed302b3d1e406c4c2d1b64a0668"
IMAGE = "far-zero-key-grader:648-v1"
MAX_RESPONSE_BYTES = 65536
MAX_SOURCE_BYTES = 120000
MAX_TASK_BYTES = 20000
MAX_OUTPUT_TOKENS = 1800
MAX_TEST_SECONDS = 120
MAX_TEST_STREAM_BYTES = 1024 * 1024
MAX_MODEL_SECONDS = 180


class SmokeError(ValueError):
    pass


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    p = subprocess.run(["git", *args], cwd=repo, stdin=subprocess.DEVNULL,
                       capture_output=True, timeout=30, check=False)
    if check and p.returncode:
        raise SmokeError("Git operation failed: " + " ".join(args[:2]))
    return p


def _unique(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise SmokeError("duplicate JSON key")
        obj[k] = v
    return obj


def strict_json(raw: bytes) -> object:
    if not raw or len(raw) > MAX_RESPONSE_BYTES:
        raise SmokeError("empty or oversized JSON")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(SmokeError("non-finite JSON")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SmokeError("invalid JSON") from exc


def manifest(raw: bytes) -> dict:
    if len(raw) > MAX_TASK_BYTES:
        raise SmokeError("oversized task manifest")
    m = strict_json(raw)
    keys = {"schema", "task_id", "issue_number", "base_sha", "source_git_blob",
            "allowed_path", "task_text", "test_module"}
    if type(m) is not dict or set(m) != keys or m["schema"] != SCHEMA:
        raise SmokeError("invalid task manifest schema")
    if (not isinstance(m["base_sha"], str) or SHA40.fullmatch(m["base_sha"]) is None
            or not isinstance(m["source_git_blob"], str) or SHA1.fullmatch(m["source_git_blob"]) is None):
        raise SmokeError("unbound source identity")
    if (type(m["issue_number"]) is not int or m["issue_number"] < 1
            or type(m["task_id"]) is not str or not re.fullmatch(r"[A-Z0-9_-]{1,64}", m["task_id"])):
        raise SmokeError("invalid task identifier")
    if type(m["allowed_path"]) is not str:
        raise SmokeError("invalid file path")
    pure = PurePosixPath(m["allowed_path"])
    if (pure.is_absolute() or not pure.parts or str(pure) != m["allowed_path"]
            or any(part in (".", "..") for part in pure.parts)
            or "\\" in m["allowed_path"] or pure.suffix != ".py"):
        raise SmokeError("unsafe or unsupported file path")
    if (type(m["task_text"]) is not str or not m["task_text"].strip()
            or len(m["task_text"].encode()) > 10000):
        raise SmokeError("invalid task text")
    if type(m["test_module"]) is not str or not CHECK.fullmatch(m["test_module"]):
        raise SmokeError("invalid public test module")
    return m


def patch_text(raw: bytes, path: str) -> str:
    """Accept one ordinary unified Git diff; reject alternate paths and modes."""
    obj = strict_json(raw)
    if type(obj) is not dict or set(obj) != {"patch"} or type(obj["patch"]) is not str:
        raise SmokeError("expected one JSON patch property")
    patch = obj["patch"]
    if not patch.endswith("\n"):
        raise SmokeError("patch must terminate with newline")
    if not 50 <= len(patch.encode("utf-8")) <= 50000 or "\x00" in patch:
        raise SmokeError("empty/oversized/binary patch")
    lines = patch.splitlines()
    headers = [line for line in lines if line.startswith("diff --git ")]
    if headers != [f"diff --git a/{path} b/{path}"]:
        raise SmokeError("patch must alter exactly one declared path")
    if [line for line in lines if line.startswith("--- ")] != [f"--- a/{path}"]:
        raise SmokeError("invalid old path")
    if [line for line in lines if line.startswith("+++ ")] != [f"+++ b/{path}"]:
        raise SmokeError("invalid new path")
    if any(line.startswith(("GIT binary patch", "Binary files", "new file mode", "deleted file mode",
                             "old mode", "new mode", "rename ", "copy ", "similarity index"))
           for line in lines):
        raise SmokeError("binary/mode/rename operations forbidden")
    if not any(line.startswith("@@ ") for line in lines):
        raise SmokeError("patch must contain a hunk")
    return patch


def model_reply(prompt: str) -> tuple[bytes, bytes, dict]:
    payload = {
        "model": MODEL, "stream": False, "keep_alive": "5m",
        "options": {"temperature": 0, "seed": 0, "num_ctx": 16384, "num_predict": MAX_OUTPUT_TOKENS},
        "messages": [
            {"role": "system", "content": (
                "You are a bounded software repair worker. Return exactly one JSON object "
                "with key 'patch' containing a valid unified Git diff string. "
                "Do not include Markdown, commentary, commands, or any other keys. "
                "Modify only the file named in the request. A failed attempt is acceptable.")},
            {"role": "user", "content": prompt},
        ],
    }
    req = urllib.request.Request("http://127.0.0.1:11434/api/chat",
                                 data=json.dumps(payload, separators=(",", ":")).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    start = time.monotonic()
    with urllib.request.urlopen(req, timeout=MAX_MODEL_SECONDS) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise SmokeError("oversized local model transport reply")
    result = strict_json(raw)
    if (type(result) is not dict or result.get("done") is not True
            or type(result.get("message")) is not dict
            or type(result["message"].get("content")) is not str
            or type(result.get("eval_count")) is not int or result["eval_count"] < 1
            or type(result.get("prompt_eval_count")) is not int or result["prompt_eval_count"] < 1):
        raise SmokeError("local model reply lacks completed positive generation evidence")
    return result["message"]["content"].encode(), raw, {
        "response_sha256": sha(raw), "output_tokens": result["eval_count"],
        "input_tokens": result["prompt_eval_count"], "elapsed_seconds": round(time.monotonic() - start, 4),
        "api_model": result.get("model"),
    }


def apply_candidate(worktree: Path, patch: str, path: str) -> str:
    target = worktree / path
    if (not target.is_file() or not target.resolve().is_relative_to(worktree.resolve())
            or any((worktree.joinpath(*PurePosixPath(path).parts[:i])).is_symlink()
                   for i in range(1, len(PurePosixPath(path).parts) + 1))):
        raise SmokeError("target is not a regular in-tree source file")
    cp = subprocess.run(["git", "apply", "--check", "--"], input=patch.encode(),
                        cwd=worktree, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    if cp.returncode:
        raise SmokeError("candidate patch fails git apply --check")
    cp = subprocess.run(["git", "apply", "--"], input=patch.encode(), cwd=worktree,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
    if cp.returncode:
        raise SmokeError("candidate patch fails git apply")
    modified = git(worktree, "diff", "--name-only", "HEAD").stdout.decode().splitlines()
    if modified != [path]:
        raise SmokeError("candidate modified paths beyond declared scope")
    blob = git(worktree, "hash-object", path).stdout.decode().strip()
    if not SHA1.fullmatch(blob):
        raise SmokeError("candidate blob invalid")
    return blob


def prepare_test_checkout(source: Path, scratch: Path) -> Path:
    """Copy only exact source bytes into a standalone, clean Git repository.

    A Git-linked worktree's .git file points to a host absolute path and is not
    usable inside a separately mounted Docker /app. A self-contained disposable
    Git repository preserves public tests of git status without exposing the
    host repository's Git administration directory or authenticated remotes.
    """
    destination = scratch / "checkout"
    shutil.copytree(source, destination, symlinks=True,
                    ignore=shutil.ignore_patterns(".git"))
    git(destination, "init", "-q")
    git(destination, "add", "-A")
    git(destination, "-c", "user.name=FAR Research",
        "-c", "user.email=research@example.invalid", "commit", "--no-gpg-sign",
        "-qm", "isolated public-test snapshot")
    if git(destination, "status", "--porcelain").stdout.strip():
        raise SmokeError("public test snapshot must begin with a clean Git status")
    return destination


def grader_image_id() -> str:
    cp = subprocess.run(["docker", "image", "inspect", IMAGE, "--format", "{{.Id}}"],
                        capture_output=True, text=True, timeout=15, check=False)
    image_id = cp.stdout.strip()
    if cp.returncode or re.fullmatch(r"sha256:[0-9a-f]{64}", image_id) is None:
        raise SmokeError("unavailable or non-addressed grader image")
    return image_id


def grade_in_docker(worktree: Path, module: str, out: Path, label: str) -> dict:
    """Run the public tests from a temporary standalone Git snapshot."""
    with tempfile.TemporaryDirectory(prefix="far-smoke-public-test-") as td:
        isolated = prepare_test_checkout(worktree, Path(td))
        return _run_docker_public_tests(isolated, module, out, label)


def _run_docker_public_tests(worktree: Path, module: str, out: Path, label: str) -> dict:
    """Bound the untrusted test process, and preserve its output/exit state."""
    name = "far-smoke-" + secrets.token_hex(8)
    cmd = ["docker", "run", "--rm", "--name", name, "--network", "none", "--read-only",
           "--cap-drop", "ALL", "--pids-limit", "64", "--memory", "2g", "--cpus", "2",
           "--security-opt", "no-new-privileges", "--user", "65534:65534",
           "--tmpfs", "/tmp:rw,nosuid,nodev,size=128m", "--mount",
           f"type=bind,src={worktree.resolve()},dst=/app,readonly", "-w", "/app",
           "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "HOME=/tmp",
           "-e", "GIT_OPTIONAL_LOCKS=0", "-e", "GIT_CONFIG_GLOBAL=/dev/null",
           "-e", "GIT_CONFIG_COUNT=1", "-e", "GIT_CONFIG_KEY_0=safe.directory",
           "-e", "GIT_CONFIG_VALUE_0=/app", IMAGE,
           "python", "-m", "unittest", "-v", f"tests.{module}"]
    started = time.monotonic()
    result: dict = {"state": "UNKNOWN", "exit_code": None, "elapsed_seconds": None,
                    "output_truncated": False}
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    exceeded = timed_out = False
    proc = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, start_new_session=True)
    try:
        with selectors.DefaultSelector() as selector:
            for channel, stream in (("stdout", proc.stdout), ("stderr", proc.stderr)):
                assert stream is not None
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, channel)
            deadline = started + MAX_TEST_SECONDS
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    timed_out = True
                    break
                for key, _ in selector.select(timeout=min(remaining, 0.2)):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                        continue
                    dest = buffers[key.data]
                    free = MAX_TEST_STREAM_BYTES - len(dest)
                    dest.extend(chunk[:free])
                    if len(chunk) > free:
                        exceeded = True
                        break
                if exceeded:
                    break
        if not timed_out and not exceeded:
            try:
                proc.wait(timeout=max(0.001, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                timed_out = True
    finally:
        if os.name == "posix":
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        elif proc.poll() is None:
            proc.kill()
        try:
            proc.wait(timeout=5)
        finally:
            for stream in (proc.stdout, proc.stderr):
                if stream is not None:
                    stream.close()
        if timed_out or exceeded:
            # Killing the Docker CLI does not necessarily kill the container.
            subprocess.run(["docker", "rm", "--force", name], capture_output=True,
                           stdin=subprocess.DEVNULL, timeout=15, check=False)
    for channel in ("stdout", "stderr"):
        data = bytes(buffers[channel])
        (out / f"{label}.{channel}").write_bytes(data)
        result[channel + "_sha256"] = sha(data)
    stderr = bytes(buffers["stderr"])
    counts = re.findall(rb"\bRan ([0-9]+) tests? in ", stderr)
    test_count = int(counts[-1]) if counts else 0
    result["test_count_reported"] = test_count
    result["elapsed_seconds"] = round(time.monotonic() - started, 4)
    result["exit_code"] = proc.returncode
    result["output_truncated"] = exceeded
    result["state"] = ("TIMEOUT" if timed_out else "UNKNOWN" if exceeded
                       else "UNKNOWN" if not test_count else "PASS" if proc.returncode == 0 else "FAIL")
    return result


def run(repo: Path, taskfile: Path, output: Path) -> dict:
    repo, output = repo.resolve(), output.resolve()
    if output.exists() or output.is_relative_to(repo):
        raise SmokeError("artifact directory must be new and outside repository")
    mbytes = taskfile.read_bytes()
    m = manifest(mbytes)
    if git(repo, "rev-parse", "--show-toplevel").stdout.decode().strip() != str(repo):
        raise SmokeError("repository must be checkout root")
    if git(repo, "cat-file", "-t", m["base_sha"]).stdout.strip() != b"commit":
        raise SmokeError("source SHA does not resolve to commit")
    if git(repo, "merge-base", "--is-ancestor", m["base_sha"], "HEAD", check=False).returncode:
        raise SmokeError("source base not ancestor of inspected candidate")
    # Initialize an artifact before contacting a runtime that may be absent or
    # return an unexpected model identity. Availability failures still require
    # an auditable, fail-closed receipt rather than an uncaught exception.
    output.mkdir(parents=True, mode=0o700)
    receipt = {"schema": SCHEMA, "status": "Research / provider smoke / NOT REGISTERED FACTORY TRIAL",
               "manifest_sha256": sha(mbytes), "task_id": m["task_id"],
               "base_sha": m["base_sha"], "source_git_blob": m["source_git_blob"],
               "model": MODEL, "model_digest": None, "grader_image_id": None,
               "provider_cost_usd": 0,
               "limitations": ["One constrained local model request is not autonomous PR delivery.",
                               "Model response/visible tests cannot certify correctness or withheld holdout.",
                               "Docker and worktrees do not establish complete host-side sandbox isolation.",
                               "This is excluded from the registered eight-task factory/control study."],
               "verdict": "UNKNOWN", "before": None, "after": None, "generation": None}
    scratch = tempfile.TemporaryDirectory(prefix="far-worker-smoke-")
    worktree = None
    try:
        # Reuse the previously verified provider contract. Its import and
        # registry query may fail when the model is unavailable; preserve that
        # failure in the receipt without executing untrusted source.
        from tools.workflow_efficacy_free_agent import local_model_digest
        digest = local_model_digest()
        receipt["model_digest"] = digest
        if digest != MODEL_DIGEST:
            raise SmokeError("unpinned model digest")
        receipt["grader_image_id"] = grader_image_id()
        worktree = Path(scratch.name) / "checkout"
        git(repo, "worktree", "add", "--detach", str(worktree), m["base_sha"])
        path = m["allowed_path"]
        file = worktree / path
        if file.is_symlink() or not file.is_file() or file.stat().st_size > MAX_SOURCE_BYTES:
            raise SmokeError("unavailable or unsafe bounded source")
        if git(worktree, "hash-object", path).stdout.decode().strip() != m["source_git_blob"]:
            raise SmokeError("source blob mismatch")
        receipt["before"] = grade_in_docker(worktree, m["test_module"], output, "before")
        # A failed baseline is an invalid evaluation environment, not a repair
        # opportunity. Avoid a wasteful model call that would be uninterpretable.
        if receipt["before"]["state"] != "PASS":
            raise SmokeError("baseline public tests not passing in frozen grader environment")
        source = file.read_text(encoding="utf-8")
        prompt = ("Task ID: " + m["task_id"] + "\nIssue #" + str(m["issue_number"]) +
                  "\nRequirement: " + m["task_text"] + "\nOnly allowed file: " + path +
                  "\nComplete current source:\n" + source + "\nReturn a JSON Git diff for this single file.")
        raw, response, metrics = model_reply(prompt)
        (output / "model-content.json").write_bytes(raw)
        (output / "model-transport-response.json").write_bytes(response)
        receipt["generation"] = {**metrics, "prompt_sha256": sha(prompt.encode("utf-8"))}
        patch = patch_text(raw, path)
        (output / "candidate.patch").write_text(patch, encoding="utf-8")
        blob = apply_candidate(worktree, patch, path)
        receipt["candidate_git_blob"] = blob
        receipt["candidate_patch_sha256"] = sha(patch.encode())
        receipt["after"] = grade_in_docker(worktree, m["test_module"], output, "after")
        receipt["verdict"] = ("VISIBLE_TESTS_PASSED_NOT_INDEPENDENTLY_VERIFIED"
                              if receipt["after"]["state"] == "PASS"
                              else "MODEL_PATCH_UNVERIFIED")
    except (SmokeError, OSError, subprocess.SubprocessError, TimeoutError, ValueError,
            RuntimeError, ImportError) as exc:
        receipt["verdict"] = "BLOCKED_OR_MODEL_OUTPUT_INVALID"
        receipt["error_type"] = type(exc).__name__
        receipt["error"] = str(exc)[:200]
    finally:
        try:
            if worktree is not None:
                git(repo, "worktree", "remove", "--force", str(worktree), check=False)
        finally:
            scratch.cleanup()
        receipt["artifact_sha256"] = {
            file.name: sha(file.read_bytes()) for file in sorted(output.iterdir()) if file.is_file()
        }
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repository", type=Path, required=True)
    p.add_argument("--task-file", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        result = run(args.repository, args.task_file, args.output)
    except (SmokeError, OSError, subprocess.SubprocessError) as exc:
        print("PREFLIGHT_BLOCKED: " + str(exc))
        return 2
    print(result["verdict"] + " receipt=" + str(args.output / "receipt.json"))
    # Unverified outcomes are not interpreted as a green smoke.
    return 0 if result["verdict"] == "VISIBLE_TESTS_PASSED_NOT_INDEPENDENTLY_VERIFIED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
