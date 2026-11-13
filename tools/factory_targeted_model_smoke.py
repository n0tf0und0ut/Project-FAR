#!/usr/bin/env python3
"""Source-exact one-line repair probe through the existing pinned local model.

Research-only: restricted semantic editing and Docker grading, no PR publishing,
no claim of successful end-to-end factory delivery. One model call per attempt.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request

from tools.factory_zero_key_smoke import (
    MODEL, MODEL_DIGEST, SmokeError, git, grade_in_docker,
    grader_image_id, manifest, sha, strict_json,
)

SCHEMA = "far-factory-targeted-model-probe/1"
REQUEST_MAX = 8000
REPLY_MAX = 12000
MODEL_SECONDS = 150
FROZEN_MANIFEST_SHA256 = "52d2d22c5fb0f708ace2a331e91a8d0558b86b41132b19679f8c7bd2d86ff308"
FROZEN_HOLDOUT_SHA256 = "45b73d2b4a0f2092ae82e79e5c137aaecd0c5e8537f2820b1e0c96819f61c67e"


def guard_window(source: str) -> tuple[int, str, str]:
    """Choose the precise already-existing guard by AST, not a line substring search."""
    tree = ast.parse(source)
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Factory"]
    if len(cls) != 1:
        raise SmokeError("ambiguous Factory class")
    fn = [n for n in cls[0].body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "fail"]
    if len(fn) != 1 or not fn[0].body or not isinstance(fn[0].body[0], ast.If):
        raise SmokeError("ambiguous failure guard")
    first = fn[0].body[0]
    if first.test.end_lineno != first.test.lineno or first.lineno != first.test.lineno:
        raise SmokeError("multiline guard cannot be source-exactly replaced")
    rows = source.splitlines(keepends=True)
    old = rows[first.lineno - 1]
    if not old.startswith("        if ") or not old.rstrip("\r\n").endswith(":"):
        raise SmokeError("unsupported guard formatting")
    segment = "".join(rows[fn[0].lineno - 1:fn[0].end_lineno])
    if len(segment.encode()) > REQUEST_MAX:
        raise SmokeError("oversized target function")
    return first.lineno, old, segment


def candidate_source(source: str, replacement: object) -> str:
    """Single physical line change; parse only, never execute model code on host."""
    lineno, original, _ = guard_window(source)
    if (type(replacement) is not str or len(replacement) > 400 or "\n" in replacement
            or "\r" in replacement or "\x00" in replacement):
        raise SmokeError("non-single-line model replacement")
    # Ollama JSON mode sometimes omits indentation. Restore only the known
    # AST-derived prefix; never rewrite the generated condition expression.
    if replacement.startswith("if "):
        replacement = "        " + replacement
    if not replacement.startswith("        if ") or not replacement.endswith(":"):
        raise SmokeError("not a single Python guard replacement")
    if replacement + "\n" == original:
        raise SmokeError("model did not change guard")
    rows = source.splitlines(keepends=True)
    lineending = "\r\n" if original.endswith("\r\n") else "\n"
    rows[lineno - 1] = replacement + lineending
    result = "".join(rows)
    try:
        ast.parse(result)
    except (SyntaxError, ValueError, RecursionError) as exc:
        raise SmokeError("replacement is invalid Python syntax") from exc
    return result


def local_model_line(prompt: str, *, output: Path | None = None) -> tuple[object, bytes, dict]:
    """Ollama JSON mode; records real transport, rejects absent generation metrics."""
    raw_prompt = prompt.encode("utf-8")
    if len(raw_prompt) > REQUEST_MAX:
        raise SmokeError("oversized model request")
    payload = {
        "model": MODEL, "stream": False, "format": "json", "keep_alive": "5m",
        "options": {"temperature": 0, "seed": 0, "num_ctx": 2048, "num_predict": 180},
        "messages": [
            {"role": "system", "content": "You are a Python repair agent. Reply ONLY with JSON {\"line\":\"the corrected complete Python if guard line with its 8 leading spaces\"}. No other keys, Markdown, commentary, or code fences. Keep all other source unchanged."},
            {"role": "user", "content": prompt},
        ],
    }
    req = urllib.request.Request("http://127.0.0.1:11434/api/chat",
            data=json.dumps(payload, separators=(",", ":")).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
    begin = time.monotonic()
    with urllib.request.urlopen(req, timeout=MODEL_SECONDS) as response:
        transport = response.read(REPLY_MAX + 1)
    # Preserve bounded bytes BEFORE any transport or generated-content parsing.
    # A malformed *completed* model response is a negative finding, not missing
    # evidence; do not discard it when the parser rejects its contents.
    if output is not None:
        (output / "model-transport-response.json").write_bytes(transport)
    if len(transport) > REPLY_MAX:
        raise SmokeError("oversized model transport")
    decoded = strict_json(transport)
    if (type(decoded) is not dict or decoded.get("done") is not True
            or type(decoded.get("message")) is not dict
            or type(decoded["message"].get("content")) is not str
            or type(decoded.get("eval_count")) is not int or decoded["eval_count"] < 1
            or type(decoded.get("prompt_eval_count")) is not int or decoded["prompt_eval_count"] < 1
            or decoded.get("model") != MODEL):
        raise SmokeError("invalid or unpinned model transport receipt")
    content = decoded["message"]["content"].encode()
    metadata = {
        "model": decoded["model"], "prompt_sha256": sha(raw_prompt),
        "transport_sha256": sha(transport), "response_sha256": sha(content),
        "input_tokens": decoded["prompt_eval_count"], "output_tokens": decoded["eval_count"],
        "elapsed_seconds": round(time.monotonic() - begin, 3),
    }
    if output is not None:
        (output / "model-content.txt").write_bytes(content)
        (output / "model-generation-metadata.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    data = strict_json(content)
    if type(data) is not dict or set(data) != {"line"}:
        raise SmokeError("model must return only line")
    return data["line"], transport, metadata


def run(repo: Path, taskfile: Path, output: Path, *, invoke=None, holdout: Path | None = None) -> dict:
    """A deliberately restricted patch producer for one frozen task only."""
    repo, output = repo.resolve(), output.resolve()
    if output.exists() or output.is_relative_to(repo):
        raise SmokeError("artifact directory must be fresh and outside repository")
    data = taskfile.read_bytes()
    m = manifest(data)
    if sha(data) != FROZEN_MANIFEST_SHA256:
        raise SmokeError("model task differs from separately frozen manifest")
    if holdout is None or not holdout.is_file() or sha(holdout.read_bytes()) != FROZEN_HOLDOUT_SHA256:
        raise SmokeError("missing or altered independently held-out oracle")
    if m["task_id"] != "FAR-MAINT-003" or m["allowed_path"] != "tools/software_factory.py":
        raise SmokeError("unsupported targeted research task")
    if git(repo, "rev-parse", "--show-toplevel").stdout.decode().strip() != str(repo):
        raise SmokeError("not checkout root")
    if git(repo, "cat-file", "-t", m["base_sha"]).stdout.strip() != b"commit":
        raise SmokeError("missing exact source base")
    if git(repo, "merge-base", "--is-ancestor", m["base_sha"], "HEAD", check=False).returncode:
        raise SmokeError("source base moved outside inspected checkout")
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    receipt = {"schema": SCHEMA, "source_manifest_sha256": sha(data),
        "base_sha": m["base_sha"], "source_git_blob": m["source_git_blob"],
        "task_id": m["task_id"], "model": MODEL, "model_digest": None,
        "grader_image_id": None, "before": None, "after": None, "holdout": None,
        "generation": None, "verdict": "UNKNOWN",
        "limitations": ["This is one constrained model attempt, not an authenticated coding PR.",
                        "Model-asserted identity is not external attestation.",
                        "Container grading does not prove complete host isolation."]}
    tree = None
    with tempfile.TemporaryDirectory(prefix="far-targeted-worker-") as td:
        try:
            from tools.workflow_efficacy_free_agent import local_model_digest
            receipt["model_digest"] = local_model_digest()
            if receipt["model_digest"] != MODEL_DIGEST:
                raise SmokeError("unpinned model digest")
            image = grader_image_id()
            receipt["grader_image_id"] = image
            tree = Path(td) / "base"
            git(repo, "worktree", "add", "--detach", str(tree), m["base_sha"])
            target = tree / m["allowed_path"]
            if target.is_symlink() or not target.is_file() or target.stat().st_size > 120000:
                raise SmokeError("unsafe source path")
            if git(tree, "hash-object", m["allowed_path"]).stdout.decode().strip() != m["source_git_blob"]:
                raise SmokeError("source blob mismatch")
            source = target.read_text(encoding="utf-8")
            _, old, snippet = guard_window(source)
            receipt["before"] = grade_in_docker(tree, m["test_module"], output, "before", image_id=image)
            if receipt["before"]["state"] != "PASS":
                raise SmokeError("baseline public tests not passing")
            engineering_goal = m["task_text"].split("Work on tools/software_factory.py only.", 1)[0]
            prompt = ("Frozen task: " + engineering_goal + "\nThe ONLY editable location is the first if guard of Factory.fail. "
                      "The original guard crashes on nonnumeric max_attempts such as None, "
                      "and Python accepts bool True as 1. Add an explicit validation that "
                      "max_attempts is an int but NOT bool BEFORE the numeric comparison. "
                      "Keep the existing reason validation and valid integer retry behavior. "
                      "Return a CHANGED corrected guard line as JSON with key line.\n"
                      "Current exact function:\n" + snippet)
            chosen, transport, metrics = (local_model_line(prompt, output=output)
                                          if invoke is None else invoke(prompt))
            (output / "model-transport-response.json").write_bytes(transport)
            receipt["generation"] = metrics
            result = candidate_source(source, chosen)
            target.write_text(result, encoding="utf-8")
            patch = git(tree, "diff", "--no-ext-diff", "--", m["allowed_path"]).stdout
            if not patch or len(patch) > 15000:
                raise SmokeError("no bounded candidate patch")
            (output / "candidate.patch").write_bytes(patch)
            receipt["candidate_patch_sha256"] = sha(patch)
            changed = git(tree, "diff", "--name-only", "HEAD").stdout.decode().splitlines()
            if changed != [m["allowed_path"]]:
                raise SmokeError("candidate changed wrong file")
            receipt["candidate_git_blob"] = git(tree, "hash-object", m["allowed_path"]).stdout.decode().strip()
            receipt["after"] = grade_in_docker(tree, m["test_module"], output, "after", image_id=image)
            if receipt["after"]["state"] != "PASS":
                raise SmokeError("candidate failed public tests")
            if holdout is not None:
                # Append independently frozen oracle only *after* model generation.
                p = tree / "tests" / "test_factory_targeted_holdout.py"
                if p.exists() or p.is_symlink():
                    raise SmokeError("holdout path collision")
                p.write_bytes(holdout.read_bytes())
                try:
                    receipt["holdout"] = grade_in_docker(tree, "test_factory_targeted_holdout", output,
                                                          "holdout", image_id=image)
                finally:
                    p.unlink()
                if receipt["holdout"]["state"] != "PASS":
                    raise SmokeError("candidate failed independently frozen holdout")
            receipt["verdict"] = "MODEL_PATCH_PASSED_VISIBLE_AND_FROZEN_TESTS_NOT_PR_DELIVERY"
        except (SmokeError, OSError, RuntimeError, ImportError, ValueError, TimeoutError, subprocess.SubprocessError) as exc:
            preserved_metrics = output / "model-generation-metadata.json"
            if receipt["generation"] is None and preserved_metrics.is_file():
                receipt["generation"] = json.loads(preserved_metrics.read_text(encoding="utf-8"))
            receipt["verdict"] = "BLOCKED_OR_MODEL_OUTPUT_INVALID"
            receipt["error_type"] = type(exc).__name__
            receipt["error"] = str(exc)[:170]
        finally:
            if tree is not None:
                git(repo, "worktree", "remove", "--force", str(tree), check=False)
            receipt["artifacts_sha256"] = {p.name: sha(p.read_bytes()) for p in output.iterdir() if p.is_file()}
            (output / "receipt.json").write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n")
    return receipt
