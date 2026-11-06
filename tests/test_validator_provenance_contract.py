"""Verify that cache provenance documentation does not claim a non-existent attestation.

This is a structural workflow/documentation contract, not evidence that the GitHub
artifact service or an external issuer has been independently verified.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/validator-assurance.yml"
DOCUMENT = ROOT / "docs/architecture/validator-assurance-hardening.md"


def provenance_contract_errors(document: str, workflow: dict) -> list[str]:
    jobs = workflow["jobs"]
    producer = jobs["signed-cache-producer"]["steps"]
    consumer = jobs["signed-cache-consumer"]["steps"]
    producing = "\n".join(str(step.get("run", "")) for step in producer)
    consuming = "\n".join(str(step.get("run", "")) for step in consumer)
    combined_steps = [*producer, *consumer]
    commands = "\n".join(str(step.get("run", "")) for step in combined_steps)
    actions = "\n".join(str(step.get("uses", "")) for step in combined_steps)

    issues = []
    key_is_copacked = "signed-cache.tar.gz .far/cache .far/cache-signing-key" in producing
    key_is_reloaded = '$(cat .far/cache-signing-key)' in consuming
    same_bundle_digest = "sha256sum signed-cache.tar.gz > signed-cache.tar.gz.sha256" in producing
    digest_verified = "sha256sum -c signed-cache.tar.gz.sha256" in consuming
    attested = bool(re.search(r"actions/attest-[\w-]+@", actions)) or "gh attestation attest" in commands
    attest_verified = "gh attestation verify" in commands or "cosign verify-attestation" in commands

    # The current described trust mode is not origin authentication. If that
    # mode changes, the documentation and these assertions must change together.
    if not all((key_is_copacked, key_is_reloaded, same_bundle_digest, digest_verified)):
        issues.append("documented co-packed-key and digest transport differs from workflow")
    if attested != attest_verified:
        issues.append("provenance issuance and verification are not both enforced")
    if "No GitHub Sigstore attestation is issued or verified" in document:
        if attested or attest_verified:
            issues.append("documentation denies attestation that workflow implements")
    elif not (attested and attest_verified):
        issues.append("document does not disclose absent independent attestation")
    if "not independent producer provenance" not in document:
        issues.append("missing explicit boundary on provenance assurance")
    if "generating a GitHub Sigstore artifact attestation" in document and not (attested and attest_verified):
        issues.append("unsupported positive Sigstore attestation claim")
    return issues


class CacheProvenanceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = DOCUMENT.read_text(encoding="utf-8")
        cls.workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))

    def test_real_workflow_and_documentation_match(self):
        self.assertEqual([], provenance_contract_errors(self.document, self.workflow))

    def test_old_false_attestation_claim_fails(self):
        altered = self.document.replace(
            "No GitHub Sigstore attestation is issued or verified",
            "The workflow is generating a GitHub Sigstore artifact attestation",
            1,
        )
        self.assertNotEqual(altered, self.document)
        self.assertTrue(provenance_contract_errors(altered, self.workflow))

    def test_missing_provenance_boundary_fails(self):
        altered = self.document.replace("not independent producer provenance", "verified producer provenance", 1)
        self.assertNotEqual(altered, self.document)
        self.assertTrue(provenance_contract_errors(altered, self.workflow))

    def test_copacked_hmac_key_cannot_authenticate_the_archive_origin(self):
        # Logic demonstration, not a claim that GitHub's artifact service
        # permits an attacker to replace this archive.
        original_payload = b"bootstrap.manifest: pass"
        original_key = b"original-ephemeral-key"
        original_signature = hmac.new(original_key, original_payload, hashlib.sha256).digest()
        self.assertTrue(hmac.compare_digest(
            original_signature, hmac.new(original_key, original_payload, hashlib.sha256).digest()))
        attacker_payload = b"bootstrap.manifest: forged-pass"
        attacker_key = b"replacement-ephemeral-key"
        attacker_signature = hmac.new(attacker_key, attacker_payload, hashlib.sha256).digest()
        self.assertTrue(hmac.compare_digest(
            attacker_signature, hmac.new(attacker_key, attacker_payload, hashlib.sha256).digest()))
        self.assertFalse(hmac.compare_digest(
            attacker_signature, hmac.new(original_key, attacker_payload, hashlib.sha256).digest()))


if __name__ == "__main__":
    unittest.main()
