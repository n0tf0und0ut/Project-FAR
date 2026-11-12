#!/usr/bin/env python3
"""Read-only, source-bound replay of the PR #630 deep-DAG maintenance defect.

Internal regression control only: this runs no coding agent and does not score
maintainer competence, human understanding, or a blinded treatment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

SOURCE = "tools/software_factory.py"
PINS = {
    "before": ("23893f0c45ab3afb038c401f4b1d53295009f2c1", "7d622ec33ed367d7335ab5318519635a251e1c10"),
    "after": ("66047a9e61b615063d4ef62aeb09be10b13a8112", "6a395d71cc049e9b2cceacbc0b971e2523ac06d2"),
}
EXPECTED = {
    "before": {"small_dag": "accepted", "small_cycle": "structured_cycle", "deep_dag": "recursion_error", "deep_cycle": "recursion_error"},
    "after": {"small_dag": "accepted", "small_cycle": "structured_cycle", "deep_dag": "accepted", "deep_cycle": "structured_cycle"},
}

# The observer executes only the pinned trusted source, in a child interpreter.
# No hidden oracle or working solution is delivered to a coding agent because
# this retrospective replay has no coding-agent participant.
CHILD = r'''
import json,runpy,sys
sys.setrecursionlimit(900)
m=runpy.run_path(sys.argv[1])
FactoryError=m['FactoryError']; validate=m['validate_order']; schema=m['SCHEMA']
def task_graph(n,cycle=False):
    data={'schema':schema,'id':'deepchain','repository':'n0tf0und0ut/Project-FAR',
          'base_sha':'a'*40,'tasks':[
          {'id':f'task-{i:04d}','objective':'Maintain workflow',
           'acceptance':['Verified'],'depends_on':[f'task-{i-1:04d}'] if i else []}
          for i in reversed(range(n))]}
    if cycle: data['tasks'][-1]['depends_on']=[f'task-{n-1:04d}']
    return data
out={}
for name,n,cyclic in [('small_dag',3,False),('small_cycle',3,True),
                      ('deep_dag',1250,False),('deep_cycle',1250,True)]:
    source=task_graph(n,cyclic)
    try:
        actual=validate(source)
        out[name]='accepted' if actual is source and not cyclic else 'incorrect_acceptance'
    except FactoryError as e:
        out[name]='structured_cycle' if cyclic and 'cyclic' in str(e).lower() else 'unexpected_factory_error'
    except RecursionError:
        out[name]='recursion_error'
    except Exception as e:
        out[name]='unexpected_'+type(e).__name__
print(json.dumps(out,sort_keys=True,separators=(',',':')))
'''


def git_blob_sha(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def source_at(repo: Path, commit: str, expected_blob: str) -> bytes:
    if len(commit) != 40 or len(expected_blob) != 40 or any(c not in "0123456789abcdef" for c in commit + expected_blob):
        raise ValueError("invalid immutable Git identity")
    env = os.environ.copy()
    env.update({"GIT_NO_REPLACE_OBJECTS": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"})
    cp = subprocess.run(["git", "show", f"{commit}:{SOURCE}"], cwd=repo, env=env,
                        capture_output=True, timeout=20, check=False)
    if cp.returncode != 0:
        raise RuntimeError(f"historical source unavailable at {commit}; fetch the pinned PR branch, then retry")
    if git_blob_sha(cp.stdout) != expected_blob:
        raise ValueError("historical Git blob does not match frozen identity")
    return cp.stdout


def execute_source(raw: bytes) -> dict[str, str]:
    # A disposable child prevents a historical validation failure from crashing
    # or modifying the evaluator process. This is process, not OS sandbox isolation.
    with tempfile.TemporaryDirectory(prefix="far-maintenance-replay-") as tmp:
        file = Path(tmp) / "module.py"
        file.write_bytes(raw)
        cp = subprocess.run([sys.executable, "-I", "-S", "-c", CHILD, str(file)],
                            cwd=tmp, env={"PATH": os.environ.get("PATH", ""),
                                          "PYTHONIOENCODING": "utf-8"},
                            capture_output=True, text=True, timeout=20, check=False)
    if cp.returncode != 0 or len(cp.stdout) > 4096:
        raise RuntimeError(f"observer failed with exit {cp.returncode}: {cp.stderr[-600:]}")
    value = json.loads(cp.stdout)
    if not isinstance(value, dict) or set(value) != set(EXPECTED["before"]):
        raise ValueError("observer did not return the complete four-case outcome")
    if any(not isinstance(v, str) for v in value.values()):
        raise ValueError("invalid observer outcome")
    return value


def replay(repo: Path) -> dict:
    actual = {arm: execute_source(source_at(repo, *pins)) for arm, pins in PINS.items()}
    return {
        "schema": "far-maintenance-recovery-historical-replay/1",
        "status": "INTERNAL_RETROSPECTIVE_REPLAY",
        "repository": "n0tf0und0ut/Project-FAR",
        "source_path": SOURCE,
        "source_pins": {arm: {"commit": commit, "git_blob": blob} for arm, (commit, blob) in PINS.items()},
        "recursion_limit": 900,
        "cases": actual,
        "expected": EXPECTED,
        "replay_passed": actual == EXPECTED,
        "coding_agent_executions": 0,
        "blind_trial_status": "NOT_EXECUTED_NO_ISOLATED_AGENT_RUNTIME",
        "nonclaims": ["not independent model or human repair", "not blinded", "not maintainability effectiveness evidence"],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--output", type=Path, help="optional JSON evidence output path")
    args = parser.parse_args(argv)
    try:
        result = replay(args.repo.resolve())
    except (RuntimeError, ValueError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"REPLAY_NOT_VERIFIED: {exc}", file=sys.stderr)
        return 2
    encoded = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        sys.stdout.write(encoded)
    return 0 if result["replay_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
