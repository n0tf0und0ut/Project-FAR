"""Full offline/optional-online workflow and immutable audit-package writer."""
from __future__ import annotations
import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from engine import InvalidBundle, canonical, digest
from acquire import AcquisitionError
from workflow import investigate
from review import verify_review

MAX_CONFIG = 450_000


def write_package(destination: Path, package: dict, *, review: dict | None = None) -> dict:
    if destination.exists():
        raise InvalidBundle("output directory already exists; will not overwrite audit history")
    parent = destination.resolve().parent
    parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=".far-stage-", dir=parent))
    try:
        files = {"input.json": canonical(package["bundle"]) + b"\n",
                 "audit.json": canonical(package["audit"]) + b"\n",
                 "report.md": package["report_md"].encode("utf-8"),
                 "acquisition.json": canonical(package["acquisition"]) + b"\n",
                 "proposal.json": canonical(package["proposal"]) + b"\n",
                 "critical_questions.json": canonical(package["critical_questions"]) + b"\n"}
        if package.get("discovery"):
            files["discovery.json"] = canonical(package["discovery"]) + b"\n"
        if review is not None:
            files["review.json"] = canonical(review) + b"\n"
            files["review_verification.json"] = canonical(verify_review(review, package["audit"])) + b"\n"
        for name, content in files.items():
            (tmp / name).write_bytes(content)
        manifest = {**package["manifest"], "files_sha256": {name: digest(content) for name,content in sorted(files.items())},
                    "self_digest_scope": "manifest.json intentionally excluded"}
        (tmp / "manifest.json").write_bytes(canonical(manifest) + b"\n")
        os.replace(tmp, destination)
        return manifest
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise


def verify_package(directory: Path) -> dict:
    from engine import audit
    from independent_check import check_report, IndependentCheckError
    root = directory.resolve()
    if not root.is_dir():
        raise InvalidBundle("audit directory missing")
    manifest = json.loads((root / "manifest.json").read_bytes())
    if manifest.get("schema") != "far-investigation-delivery/0.3":
        raise InvalidBundle("unexpected manifest version")
    stored = manifest.get("files_sha256")
    if not isinstance(stored, dict) or not {"input.json", "audit.json", "report.md", "acquisition.json", "proposal.json", "critical_questions.json"}.issubset(stored):
        raise InvalidBundle("manifest required files missing")
    for name, expected in stored.items():
        if not isinstance(name, str) or name in {"", ".", ".."} or "/" in name or "\\" in name:
            raise InvalidBundle("unsafe file path in manifest")
        path = root / name
        if path.is_symlink():
            raise InvalidBundle("symlink audit artifact forbidden")
        if not path.is_file() or path.stat().st_size > 6_000_000 or digest(path.read_bytes()) != expected:
            raise InvalidBundle("audit artifact hash mismatch: " + name)
    # Detect extra files and checks that were removed, not just files in manifest.
    if {p.name for p in root.iterdir()} != {*stored, "manifest.json"}:
        raise InvalidBundle("untracked audit-package files")
    bundle = json.loads((root / "input.json").read_bytes())
    reported = json.loads((root / "audit.json").read_bytes())
    recalc = audit(bundle)
    if recalc != reported or manifest.get("input_sha256") != recalc.get("input_sha256") or manifest.get("report_sha256") != recalc.get("report_sha256"):
        raise InvalidBundle("auditor replay mismatch")
    if manifest.get("report_md_sha256") != digest((root / "report.md").read_bytes()):
        raise InvalidBundle("report digest mismatch")
    try:
        independent = check_report(bundle, recalc)
    except IndependentCheckError as exc:
        raise InvalidBundle("design-diverse formal cross-check failed: " + str(exc)) from exc
    from diagnostics import critical_questions
    advisory=json.loads((root / "critical_questions.json").read_bytes())
    if advisory != critical_questions(bundle["claims"]):
        raise InvalidBundle("critical question advisory mismatch")
    if "review.json" in stored:
        reviewed = verify_review(json.loads((root / "review.json").read_bytes()), recalc)
        if reviewed != json.loads((root / "review_verification.json").read_bytes()):
            raise InvalidBundle("review verification mismatch")
    return {"replay_match": True, "algorithm_cross_check": independent, "manifest_files_verified": len(stored),
            "report_sha256": recalc["report_sha256"], "external_truth_verified": False}


def main() -> int:
    p = argparse.ArgumentParser(description="Investigate a source with explicit uncertainty and replayable evidence")
    p.add_argument("request", nargs="?", type=Path, help="JSON configuration including source and proposed claims")
    p.add_argument("--output", type=Path, help="new directory for immutable audit output")
    p.add_argument("--allow-network", action="store_true", help="opt in to remote HTTPS/YouTube/discovery access")
    p.add_argument("--allow-model", action="store_true", help="authorize sending source material to external model for proposals/transcription")
    p.add_argument("--review", type=Path, help="optional signed third-party review record")
    p.add_argument("--verify", type=Path, help="verify an already-produced package directory")
    args = p.parse_args()
    try:
        if args.verify:
            print(json.dumps(verify_package(args.verify), sort_keys=True))
            return 0
        if args.request is None or args.output is None:
            p.error("request and --output required unless --verify is specified")
        raw = args.request.read_bytes()
        if len(raw) > MAX_CONFIG:
            raise InvalidBundle("config size limit exceeded")
        config = json.loads(raw)
        result = investigate(config, permit_network=args.allow_network, permit_model=args.allow_model, permit_files=True)
        rev = json.loads(args.review.read_bytes()) if args.review else None
        manifest = write_package(args.output, result, review=rev)
        print(json.dumps({"output": str(args.output), "report_sha256": manifest["report_sha256"],
                          "claims": len(result["bundle"]["claims"]), "readings": len(result["audit"]["interpretations"]),
                          "semantic_fidelity_verified": False}, sort_keys=True))
        return 0
    except (InvalidBundle, AcquisitionError, OSError, UnicodeError, ValueError, TypeError) as exc:
        print("FAR_END_TO_END_INVALID: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
