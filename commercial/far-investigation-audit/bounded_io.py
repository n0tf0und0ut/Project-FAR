"""Bound regular-file input before allocation, including a growing-file race."""
from __future__ import annotations

import os
import stat
from pathlib import Path


class BoundedInputError(ValueError):
    pass


def read_bounded(path: Path, limit: int) -> bytes:
    path = Path(path)
    if path.is_symlink():
        raise BoundedInputError("symlink input forbidden: " + path.name)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
            raise BoundedInputError("input size/type limit exceeded: " + path.name)
        # fstat alone cannot protect against growth after the check. Never
        # request an unbounded allocation, even from a checked descriptor.
        with os.fdopen(fd, "rb", closefd=False) as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise BoundedInputError("input size limit exceeded: " + path.name)
        return raw
    finally:
        os.close(fd)
