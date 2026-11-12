#!/usr/bin/env python3
"""Verify the pinned upstream Cloudflare security-audit source snapshot.

Git blob identity proves file provenance only, not that the source is safe.
No vendored code or target-controlled process is executed by this checker.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "docs/maintenance/cloudflare-security-audit-source-lock.json"
SKILL_DIR = ROOT / ".agents/skills/security-audit"
BASE = ".agents/skills/security-audit"
UPSTREAM = "cloudflare/security-audit-skill"
COMMIT = "c1c8a8c1471069fb0e188eeaff69b8e8db6564a8"
LOCK_GIT_BLOB = "cb281cf41c9c9ccd50e1df450b2e292b4e68e94b"


def git_blob_sha(content: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(content)).encode("ascii") + b"\0" + content
    ).hexdigest()


def verify_manifest_bytes(payload: bytes):
    """A changed manifest cannot silently rebaseline vendored source blobs."""
    if git_blob_sha(payload) != LOCK_GIT_BLOB:
        return ["modified source-lock manifest (requires separately reviewed re-pin)"]
    return []


def verify(manifest, skill_dir=SKILL_DIR):
    errors = []
    required = {
        "schema": "far-cloudflare-security-audit-source-lock/1",
        "upstream_repository": UPSTREAM,
        "upstream_commit": COMMIT,
        "upstream_skill_path": "skills/security-audit",
        "installed_skill_path": BASE,
        "license": "MIT",
    }
    if not isinstance(manifest, dict):
        return ["manifest is not an object"]
    for name, expected in required.items():
        if manifest.get(name) != expected:
            errors.append(f"wrong pinned {name}")
    files = manifest.get("files")
    if not isinstance(files, list) or len(files) != 21:
        return errors + ["expected exactly 21 locked upstream files"]
    locked = {}
    for item in files:
        if not isinstance(item, dict):
            errors.append("malformed lock entry")
            continue
        path, digest = item.get("path"), item.get("git_blob_sha1")
        if not isinstance(path, str) or not path.startswith(BASE + "/"):
            errors.append("file outside installed directory")
            continue
        name = path[len(BASE) + 1:]
        if not name or "/" in name or name in (".", "..") or name in locked:
            errors.append(f"duplicate or invalid file name {name}")
            continue
        if not isinstance(digest, str) or len(digest) != 40 or any(
            c not in "0123456789abcdef" for c in digest
        ):
            errors.append(f"invalid blob digest {name}")
            continue
        locked[name] = digest
    if not skill_dir.is_dir() or skill_dir.is_symlink():
        return errors + ["installed skill directory missing or symlinked"]
    seen = set()
    for path in skill_dir.iterdir():
        if path.is_symlink() or not path.is_file():
            errors.append(f"not a regular source file: {path.name}")
            continue
        seen.add(path.name)
        if path.name not in locked:
            errors.append(f"unlisted vendor file: {path.name}")
        elif git_blob_sha(path.read_bytes()) != locked[path.name]:
            errors.append(f"modified vendor file: {path.name}")
    for name in sorted(set(locked) - seen):
        errors.append(f"missing vendor file: {name}")
    if "SKILL.md" in seen:
        if not (skill_dir / "SKILL.md").read_text(
            encoding="utf-8"
        ).startswith("---\nname: security-audit\n"):
            errors.append("invalid skill discovery frontmatter")
    if "LICENSE" in seen and "MIT License" not in (
        skill_dir / "LICENSE"
    ).read_text(encoding="utf-8"):
        errors.append("MIT license attribution missing")
    return errors


def main():
    try:
        payload = LOCK.read_bytes()
        manifest = json.loads(payload.decode("utf-8"))
        errors = verify_manifest_bytes(payload) + verify(manifest)
    except (ValueError, OSError, UnicodeError) as exc:
        print("FAIL Cloudflare source lock:", exc)
        return 1
    for error in errors:
        print("FAIL", error)
    if errors:
        return 1
    print("Cloudflare security-audit source lock verified (21 files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
