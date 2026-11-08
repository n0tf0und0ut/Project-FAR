from __future__ import annotations

from pathlib import Path

from .model import DecisionPackage, PackageValidationError
from .strict_json import loads_strict


def load_package(path: str | Path) -> DecisionPackage:
    source = Path(path)
    try:
        payload = loads_strict(source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise PackageValidationError(f"unable to read decision package {source}: {exc}") from exc
    except ValueError as exc:
        raise PackageValidationError(
            f"decision package {source} is not valid JSON: {exc}"
        ) from exc
    return DecisionPackage.from_dict(payload)
