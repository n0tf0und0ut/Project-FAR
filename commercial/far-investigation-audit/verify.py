"""Replay and compare an independently supplied input and report.

Uses the same open-source deterministic implementation, so it is reproducible
recomputation rather than independent code verification or source attestation.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from engine import InvalidBundle, audit, canonical
from bounded_io import read_bounded
from full_cli import parse_json_artifact

MAX_INPUT = 2_000_000
MAX_REPORT = 6_000_000


def main() -> int:
    p = argparse.ArgumentParser(description="Recompute and compare a FAR bounded audit report")
    p.add_argument("bundle", type=Path)
    p.add_argument("report", type=Path)
    args = p.parse_args()
    try:
        b, r = read_bounded(args.bundle, MAX_INPUT), read_bounded(args.report, MAX_REPORT)
        if len(b) > MAX_INPUT or len(r) > MAX_REPORT:
            raise InvalidBundle("audit replay input/report byte limit exceeded")
        supplied = parse_json_artifact(r, "report.json")
        regenerated = audit(parse_json_artifact(b, "input.json"))
        if canonical(supplied) != canonical(regenerated):
            print("FAR_REPLAY_MISMATCH: supplied report differs from audited input", file=sys.stderr)
            return 1
        print("FAR_REPLAY_MATCH: deterministic report and bundle agree")
        return 0
    except (InvalidBundle, OSError, ValueError, UnicodeError, TypeError, RecursionError) as exc:
        print(f"FAR_REPLAY_INVALID: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
