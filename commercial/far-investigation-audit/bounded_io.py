"""Bounded single-read snapshots of operator-supplied regular files."""
from __future__ import annotations

import os
from pathlib import Path
import stat


class BoundedInputError(ValueError):
    pass


def read_bounded(path: Path, limit: int, label: str | None = None) -> bytes:
    """Check the opened file before allocation, then limit reads despite growth.

    A snapshot records exactly the bytes read; it does not authenticate the
    external file or assert an atomic historical filesystem version.
    Nonblocking open plus fstat rejects pipes/devices without waiting on them.
    """
    path = Path(path)
    label = label or path.name
    if path.is_symlink():
        raise BoundedInputError("symlink input forbidden: " + path.name)
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise BoundedInputError(f"{label} input size/type limit exceeded")
        raw = bytearray()
        with os.fdopen(descriptor, "rb", buffering=0, closefd=False) as stream:
            while len(raw) <= limit:
                chunk = stream.read(min(65_536, limit + 1 - len(raw)))
                if not chunk:
                    return bytes(raw)
                raw.extend(chunk)
        raise BoundedInputError(f"{label} input size limit exceeded during read")
    finally:
        os.close(descriptor)
