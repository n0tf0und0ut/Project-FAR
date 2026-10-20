"""Freeze locally supplied UTF-8 text or JSON snapshots without making truth claims.

The timestamp is a record of intake into this process, not authentication of
an earlier publication or provenance, and external URLs are not fetched.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from engine import InvalidBundle, canonical, digest, timestamp
from bounded_io import read_bounded

MAX_SOURCE_BYTES = 200_000


def capture_source(raw: bytes, *, source_id: str, captured_at: str,
                   published_at: str | None = None, origin_id: str | None = None) -> dict[str, object]:
    if not isinstance(source_id, str) or re.fullmatch(r"[a-zA-Z0-9_.:-]{1,80}", source_id) is None:
        raise InvalidBundle("capture: invalid source_id")
    if not 0 < len(raw) <= MAX_SOURCE_BYTES:
        raise InvalidBundle("capture: invalid source byte length")
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise InvalidBundle("capture: source not valid UTF-8") from exc
    capture_time = timestamp(captured_at, "captured_at")
    if published_at is not None:
        publication = timestamp(published_at, "published_at")
        if publication > capture_time:
            raise InvalidBundle("capture: publication later than captured_at")
    if origin_id is not None and (not isinstance(origin_id, str) or not origin_id.strip()):
        raise InvalidBundle("capture: invalid origin_id")
    return {"id": source_id, "text": text, "sha256": digest(raw),
            "published_at": published_at, "captured_at": captured_at,
            "origin_id": origin_id, "capture_method": "local_unauthenticated_utf8_snapshot",
            "publication_date_verified": False, "origin_verified": False}


def exact_anchor(source_text: str, quotation: str, *, start: int | None = None) -> dict[str, object]:
    if not quotation:
        raise InvalidBundle("capture: nonempty quote required")
    if start is None:
        first = source_text.find(quotation)
        if first < 0:
            raise InvalidBundle("capture: quote not in snapshot")
        if source_text.find(quotation, first + 1) >= 0:
            raise InvalidBundle("capture: ambiguous repeated quote; specify --start")
        start = first
    if type(start) is not int or start < 0 or source_text[start:start + len(quotation)] != quotation:
        raise InvalidBundle("capture: quoted span does not match supplied offset")
    return {"start": start, "end": start + len(quotation), "quote": quotation}


def main() -> int:
    p = argparse.ArgumentParser(description="Capture a local source, not fetch a URL or verify its publication")
    p.add_argument("path", type=Path)
    p.add_argument("--id", required=True)
    p.add_argument("--published-at", help="declared source publication time (unverified)")
    p.add_argument("--origin-id", help="reported origin identity (unverified)")
    p.add_argument("--quote", help="optional exact quotation to anchor")
    p.add_argument("--start", type=int, help="offset in decoded Unicode characters for repeated quote")
    try:
        args = p.parse_args()
        if args.start is not None and args.quote is None:
            raise InvalidBundle("capture: --start requires --quote")
        raw = read_bounded(args.path, MAX_SOURCE_BYTES)
        now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        source = capture_source(raw, source_id=args.id, captured_at=now,
                                published_at=args.published_at, origin_id=args.origin_id)
        out: dict[str, object] = {"source": source}
        if args.quote is not None:
            out["span"] = exact_anchor(source["text"], args.quote, start=args.start)
        sys.stdout.buffer.write(canonical(out) + b"\n")
        return 0
    except (InvalidBundle, OSError, ValueError, UnicodeError) as exc:
        print(f"FAR_CAPTURE_INVALID: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
