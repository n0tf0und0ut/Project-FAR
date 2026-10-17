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
    if not isinstance(manifest, dict) or manifest.get("schema") != "far-investigation-delivery/0.3":
        raise InvalidBundle("unexpected manifest version")
    if (manifest.get("semantic_mapping_independently_verified") is not False or
        manifest.get("open_world_completeness") != "UNESTABLISHED" or
        manifest.get("end_to_end_production_quality") != "UNESTABLISHED"):
        raise InvalidBundle("manifest assurance boundary was changed")
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
    if ("review.json" in stored) != ("review_verification.json" in stored):
        raise InvalidBundle("incomplete signed-review record pair")
    bundle = json.loads((root / "input.json").read_bytes())
    reported = json.loads((root / "audit.json").read_bytes())
    recalc = audit(bundle)
    if recalc != reported or manifest.get("input_sha256") != recalc.get("input_sha256") or manifest.get("report_sha256") != recalc.get("report_sha256"):
        raise InvalidBundle("auditor replay mismatch")
    # Every interpretive and human-readable output is recomputed from the
    # recorded inputs. A file hash inside an unsigned, freely editable manifest
    # is NOT enough to establish the contents of the report.
    from proposals import compile_proposal
    from presentation import render_markdown
    from diagnostics import critical_questions
    sources = {s["id"]: s for s in bundle["sources"]}
    if len(sources) != len(bundle["sources"]):
        raise InvalidBundle("duplicate source identity in report")
    acquisition = json.loads((root / "acquisition.json").read_bytes())
    proposal = json.loads((root / "proposal.json").read_bytes())
    questions = json.loads((root / "critical_questions.json").read_bytes())
    discovery = json.loads((root / "discovery.json").read_bytes()) if "discovery.json" in stored else None
    if not isinstance(acquisition, list) or any(not isinstance(a, dict) or
            a.get("source_id") not in sources for a in acquisition):
        raise InvalidBundle("invalid acquisition source identity")
    if len(acquisition) != len(sources) or {a["source_id"] for a in acquisition} != set(sources):
        raise InvalidBundle("acquisition does not account for every source exactly once")
    if not isinstance(proposal, dict):
        raise InvalidBundle("malformed proposal artifact")
    # Replay source extraction when the original UTF-8 capture bytes are
    # available. Recording only a raw digest cannot independently verify the
    # transformation from downloaded HTML/captions to extracted text.
    from acquire import normalize_html, parse_captions
    independently_extracted = 0
    not_replayable = []
    replayable_methods = {"text_provided_v1", "utf8_identity_v1",
        "html_provided_v1", "html_visible_text_v1", "srt_provided_v1",
        "vtt_provided_v1", "yt_dlp_caption_vtt_v1"}
    for item in acquisition:
        sid = item["source_id"]
        raw = item.get("raw_snapshot_utf8")
        method = item.get("extraction")
        if raw is None:
            if method in replayable_methods:
                raise InvalidBundle("raw snapshot required for replayable extraction: " + sid)
            not_replayable.append(sid)
            continue
        if not isinstance(raw, str) or len(raw.encode("utf-8")) > 1_000_000:
            raise InvalidBundle("invalid archived raw source")
        if item.get("raw_sha256") != digest(raw.encode("utf-8")):
            raise InvalidBundle("raw source snapshot digest mismatch: " + sid)
        if method in {"text_provided_v1", "utf8_identity_v1"}:
            extracted = {"text": raw}
        elif method in {"html_provided_v1", "html_visible_text_v1"}:
            extracted = {"text": normalize_html(raw)}
        elif method in {"srt_provided_v1", "vtt_provided_v1", "yt_dlp_caption_vtt_v1"}:
            extracted = parse_captions(raw)
        else:
            raise InvalidBundle("unknown replayable extraction method: " + str(method))
        if extracted["text"] != sources[sid]["text"]:
            raise InvalidBundle("raw-to-extracted source transformation mismatch: " + sid)
        if "cues" in extracted and extracted["cues"] != item.get("cues"):
            raise InvalidBundle("caption cue anchor mismatch: " + sid)
        independently_extracted += 1
    rebuilt = compile_proposal(proposal, {k:v["text"] for k,v in sources.items()},
        investigation_id=bundle["investigation_id"], captured_at=bundle["as_of"],
        published_at_by_source={k:v.get("published_at") for k,v in sources.items()},
        source_meta={k:{"origin_id":v.get("origin_id"),
            "publication_date_verified":v.get("publication_date_verified",False),
            "origin_verified":v.get("origin_verified",False)} for k,v in sources.items()})
    if canonical(rebuilt) != canonical(bundle):
        raise InvalidBundle("proposal-to-audit input reconstruction mismatch")
    expected_questions = critical_questions(bundle["claims"])
    if questions != expected_questions:
        raise InvalidBundle("critical question advisory mismatch")
    expected_md = render_markdown(bundle, recalc, acquisition=acquisition,
                                 discovery=discovery, questions=expected_questions)
    if (root / "report.md").read_bytes() != expected_md.encode("utf-8"):
        raise InvalidBundle("human-readable report does not replay from source artifacts")
    if manifest.get("report_md_sha256") != digest(expected_md.encode("utf-8")):
        raise InvalidBundle("report digest mismatch")
    if manifest.get("source_snapshots_sha256") != {k:v["sha256"] for k,v in sources.items()}:
        raise InvalidBundle("manifest source snapshot identities mismatch")
    if (manifest.get("investigation_id") != bundle["investigation_id"] or
        manifest.get("generated_at") != bundle["as_of"] or
        manifest.get("method") != proposal.get("method", "supplied")):
        raise InvalidBundle("manifest and investigation identity mismatch")
    try:
        independent = check_report(bundle, recalc)
    except IndependentCheckError as exc:
        raise InvalidBundle("design-diverse formal cross-check failed: " + str(exc)) from exc
    if "review.json" in stored:
        reviewed = verify_review(json.loads((root / "review.json").read_bytes()), recalc)
        if reviewed != json.loads((root / "review_verification.json").read_bytes()):
            raise InvalidBundle("review verification mismatch")
    return {"replay_match": True, "algorithm_cross_check": independent, "manifest_files_verified": len(stored),
            "extraction_replayed": independently_extracted,
            "extraction_not_replayable": not_replayable,
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
