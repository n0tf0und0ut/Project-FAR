"""CLI for independently replayable bounded investigation audits."""
import argparse
import sys
from pathlib import Path
from engine import audit, canonical, InvalidBundle
from bounded_io import read_bounded
from full_cli import parse_json_artifact


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit cited premises and formal inference without claiming external truth")
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        raw = read_bounded(args.bundle, 2_000_000)
        if len(raw) > 2_000_000:
            raise InvalidBundle("input size limit exceeded")
        result = audit(parse_json_artifact(raw, args.bundle.name))
        serialized = canonical(result) + b"\n"
        if args.output:
            args.output.write_bytes(serialized)
        else:
            sys.stdout.buffer.write(serialized)
    except (InvalidBundle, ValueError, OSError, UnicodeError, RecursionError, TypeError) as exc:
        print(f"FAR_AUDIT_INVALID: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
