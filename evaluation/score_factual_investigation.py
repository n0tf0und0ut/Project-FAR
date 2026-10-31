"""Explicitly independent scoring stage; never calls the forecasting model."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from evaluation.factual_investigation_runner import score_investigation


def main(argv=None):
    ap = argparse.ArgumentParser(description="Score factual investigations against separate annotated key")
    ap.add_argument("packet", type=Path)
    ap.add_argument("responses", type=Path)
    ap.add_argument("answer_key", type=Path)
    args = ap.parse_args(argv)
    try:
        packet = json.loads(args.packet.read_text(encoding="utf-8"))
        responses = json.loads(args.responses.read_text(encoding="utf-8"))
        key = json.loads(args.answer_key.read_text(encoding="utf-8"))
        result = score_investigation(packet, responses, key)
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
