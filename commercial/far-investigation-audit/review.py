"""Verify third-party review *attestations* without treating signatures as truth.

Ed25519 establishes possession of a private key over exact audit bytes. Identity,
expertise, honesty, full source coverage and review quality remain unknown.
"""
from __future__ import annotations
import base64
import binascii
from engine import InvalidBundle, canonical, digest


def _decode(x: str, length: int) -> bytes:
    try:
        out = base64.b64decode(x, validate=True)
    except (ValueError, binascii.Error, TypeError) as exc:
        raise InvalidBundle("malformed base64 review field") from exc
    if len(out) != length:
        raise InvalidBundle("review field length incorrect")
    return out


def verify_review(payload: dict, audit: dict) -> dict:
    if not isinstance(payload, dict) or not isinstance(payload.get("review"), dict):
        raise InvalidBundle("review document missing")
    record = payload["review"]
    if record.get("schema") != "far-review-attestation/1.0":
        raise InvalidBundle("unsupported review attestation format")
    if record.get("input_sha256") != audit.get("input_sha256") or record.get("report_sha256") != audit.get("report_sha256"):
        raise InvalidBundle("review attestation not bound to supplied audit")
    reviewer = record.get("reviewer")
    if not isinstance(reviewer, str) or not 1 <= len(reviewer) <= 120:
        raise InvalidBundle("reviewer label missing/invalid")
    verdicts = record.get("decisions", [])
    if not isinstance(verdicts, list) or not 1 <= len(verdicts) <= 300:
        raise InvalidBundle("review decisions missing/over cap")
    allowed = {"agree", "disagree", "not_reviewed", "requires_more_evidence"}
    if any(not isinstance(v, dict) or v.get("decision") not in allowed or
           not isinstance(v.get("object_id"), str) or not 1 <= len(v["object_id"]) <= 80 or
           not isinstance(v.get("notes", ""), str) or len(v.get("notes", "")) > 1000 for v in verdicts):
        raise InvalidBundle("invalid review decision")
    if len({v["object_id"] for v in verdicts}) != len(verdicts):
        raise InvalidBundle("duplicate review object")
    # A flat review ID must identify exactly one object. Audit IDs are
    # namespace-local, so claim/citation/reading names can legitimately
    # collide. Reject ambiguous attestations rather than attributing a signed
    # decision to an unidentifiable object. A future typed schema can express
    # review decisions on both colliding records.
    objects = [("claim", cid) for cid in audit.get("claims", {})]
    objects.extend(("interpretation", item["id"])
                   for item in audit.get("interpretations", []))
    for item in audit.get("claims", {}).values():
        objects.extend(("evidence", e["evidence_id"])
                       for e in item.get("evidence", []))
    counts = {}
    for _, object_id in objects:
        counts[object_id] = counts.get(object_id, 0) + 1
    for decision in verdicts:
        object_id = decision["object_id"]
        if object_id not in counts:
            raise InvalidBundle("review claims to assess an unknown audit object")
        if counts[object_id] != 1:
            raise InvalidBundle("ambiguous review object: " + object_id)
    key = _decode(payload.get("public_key_b64"), 32)
    signature = _decode(payload.get("signature_b64"), 64)
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        Ed25519PublicKey.from_public_bytes(key).verify(signature, canonical(record))
    except ImportError as exc:
        raise InvalidBundle("optional cryptography package required for Ed25519 verification") from exc
    except Exception as exc:
        raise InvalidBundle("review signature invalid") from exc
    return {"signature_valid": True, "payload_sha256": digest(canonical(record)),
            "public_key_sha256": digest(key), "reviewer_claimed_name": reviewer,
            "decisions": verdicts, "independent_reviewer_identity_verified": False,
            "semantic_fidelity_verified_by_signature_alone": False,
            "note": "Signature authenticates a key over a recorded review; it does not establish expertise, correspondence, accuracy or independence."}


def main() -> int:
    """Sign a review against an exact report using an operator-owned Ed25519 key."""
    import argparse
    import json
    import sys
    from pathlib import Path
    p=argparse.ArgumentParser(description="Sign an independent review *record*, not an assertion of objective truth")
    p.add_argument("review",type=Path,help="unsigned JSON record with schema far-review-attestation/1.0")
    p.add_argument("--private-key",type=Path,required=True,help="operator-controlled Ed25519 PEM key")
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        unsigned=json.loads(args.review.read_bytes())
        if not isinstance(unsigned,dict) or unsigned.get("schema") != "far-review-attestation/1.0":
            raise InvalidBundle("invalid review document schema")
        private=serialization.load_pem_private_key(args.private_key.read_bytes(),password=None)
        if not isinstance(private,Ed25519PrivateKey):
            raise InvalidBundle("Ed25519 PEM key required")
        public=private.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        signed={"review":unsigned,"public_key_b64":base64.b64encode(public).decode(),
                "signature_b64":base64.b64encode(private.sign(canonical(unsigned))).decode()}
        if args.output.exists():raise InvalidBundle("signed review output already exists")
        args.output.write_bytes(canonical(signed)+b"\n")
        print("Review record signed; identity/accuracy/independence NOT established")
        return 0
    except (OSError,ValueError,TypeError) as exc:
        print("FAR_REVIEW_INVALID: "+str(exc),file=sys.stderr)
        return 2

if __name__=="__main__":raise SystemExit(main())
