#!/usr/bin/env python3
"""Opt-in targeted Qwen model attempt through the existing durable factory queue.

No PR is created here. A passing model patch remains a *proposal* and is
recorded as a failed build-stage lease until an authenticated GitHub PR exists.
"""
from __future__ import annotations

import argparse
from functools import partial
import json
from pathlib import Path
import sys

from tools.software_factory import FactoryError
from tools.factory_zero_key_smoke import SmokeError
from tools.factory_queue_zero_key import run as run_queue
from tools.factory_targeted_model_smoke import run as run_targeted


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--order", required=True, type=Path)
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--task-file", required=True, type=Path)
    parser.add_argument("--holdout", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = run_queue(args.db, args.order, args.repository, args.task_file, args.output,
                           invoke=partial(run_targeted, holdout=args.holdout))
    except (FactoryError, SmokeError, OSError, ValueError, UnicodeError) as exc:
        print("TARGETED_MODEL_ATTEMPT_BLOCKED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps({k: result[k] for k in
                      ("order_id", "task_id", "worker_verdict", "queue_outcome", "status")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
