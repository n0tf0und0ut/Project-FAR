"""Adversarial verification of immutable factory-queue retrospective ZIP evidence.

Archived observations from exact hosted workflow 42799062260. They are NOT
prospectively randomized autonomous factory-vs-control outcomes.
"""
from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path
import unittest
import zipfile

from tools.factory_evaluation_registration import strict_json

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "research/factory-evaluation"
RECORD = FOLDER / "queue-lock-retrospective-20261110.json"
ARCHIVE = FOLDER / "queue-lock-retrospective-20261110.zip"
EXPECTED_ZIP_SHA256 = "db4ea051f37c2eb271974d9612ee212d1972d8eb849cf4f96621d61e816c98c7"
EXPECTED_BLOB_SHA1 = "d8890747d4e6af8d7b654398efbc56f5d2a2a123"
EXPECTED_FILES = {"receipt.json", "before.stdout", "before.stderr", "after.stdout", "after.stderr"}
EXPECTED_SOURCE = {
    "before_commit": "e2648ea204d033756c8185fc3cea82ce9f26d125",
    "after_commit": "6a7d5eb2864bb3440a34b0bcbdb041a452996d44",
    "test_oracle_path": "tests/test_software_factory.py",
    "test_oracle_sha256": "cc1d5e04edd20863ce9ebed97390d0436ac94bb2154e27510d4d4ba2fdb35c5b",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\x00" + data).hexdigest()


def verify(manifest: dict, archive: bytes) -> dict:
    if not isinstance(manifest, dict) or manifest.get("schema") != "far-factory-retrospective-evidence/1":
        raise ValueError("incorrect retrospective manifest schema")
    if manifest.get("status") != "Research":
        raise ValueError("retrospective cannot promote its claim status")
    if manifest.get("study_context") != "FAR-FACTORY-SELF-EVAL-001":
        raise ValueError("incorrect study context")
    if manifest.get("observation_scope") != "retrospective software-factory queue regression, not registered factory-vs-control pilot":
        raise ValueError("not the registered prospective trial")
    if manifest.get("source") != {"repository": "n0tf0und0ut/Project-FAR", **EXPECTED_SOURCE}:
        raise ValueError("historical source identities do not match")
    collector = manifest.get("collector")
    if not isinstance(collector, dict) or type(collector.get("workflow_run_id")) is not int or collector["workflow_run_id"] != 42799062260 or collector.get("artifact_id") != 13754088960:
        raise ValueError("source run provenance mismatch")
    meta = manifest.get("archive")
    if not isinstance(meta, dict):
        raise ValueError("missing archive descriptor")
    if meta.get("path") != "research/factory-evaluation/queue-lock-retrospective-20261110.zip":
        raise ValueError("archive path mismatch")
    if (type(meta.get("size_bytes")) is not int or meta["size_bytes"] != len(archive)
            or sha(archive) != EXPECTED_ZIP_SHA256 or meta.get("sha256") != EXPECTED_ZIP_SHA256
            or blob_sha1(archive) != EXPECTED_BLOB_SHA1 or meta.get("git_blob_sha1") != EXPECTED_BLOB_SHA1):
        raise ValueError("historical ZIP byte identity mismatch")
    if len(archive) > 65536:
        raise ValueError("historical ZIP unexpectedly large")
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        infos = z.infolist()
        if (len(infos) != len(EXPECTED_FILES) or {info.filename for info in infos} != EXPECTED_FILES
                or len({info.filename for info in infos}) != len(infos)):
            raise ValueError("incorrect or duplicate ZIP members")
        if any(info.is_dir() or info.file_size > 65536 or
               info.compress_size > 65536 or
               ((info.external_attr >> 16) & 0o170000) == 0o120000
               for info in infos):
            raise ValueError("unsafe or oversized ZIP member")
        if z.testzip() is not None:
            raise ValueError("ZIP CRC mismatch")
        data = {info.filename: z.read(info.filename) for info in infos}
    receipt = strict_json(data["receipt.json"])
    if not isinstance(receipt, dict) or receipt.get("schema") != "far-factory-before-after-execution/1":
        raise ValueError("missing observed experiment receipt")
    if (receipt.get("baseline_sha") != EXPECTED_SOURCE["before_commit"] or
            receipt.get("candidate_sha") != EXPECTED_SOURCE["after_commit"] or
            receipt.get("oracle_path") != EXPECTED_SOURCE["test_oracle_path"] or
            receipt.get("registered_oracle_sha256") != EXPECTED_SOURCE["test_oracle_sha256"] or
            receipt.get("observed_oracle_sha256") != {"before": EXPECTED_SOURCE["test_oracle_sha256"],
                                                      "after": EXPECTED_SOURCE["test_oracle_sha256"]}):
        raise ValueError("receipt source/oracle substitution")
    if receipt.get("verdict") != "OBSERVED_EXIT_STATUS_IMPROVEMENT" or manifest.get("observed", {}).get("verdict") != receipt["verdict"]:
        raise ValueError("unsupported retrospective verdict")
    for side, expected_code in (("before", 1), ("after", 0)):
        outcome = receipt.get(side)
        asserted = manifest["observed"].get(side)
        expected_status = "FAIL" if side == "before" else "PASS"
        if not isinstance(outcome, dict) or not isinstance(asserted, dict):
            raise ValueError("missing before/after result")
        if (outcome.get("status") != expected_status or outcome.get("exit_code") != expected_code
                or outcome.get("test_count_reported") != 14
                or outcome.get("tracked_checkout_modified") is not False
                or asserted.get("status") != expected_status or asserted.get("exit_code") != expected_code
                or asserted.get("test_count") != 14):
            raise ValueError("changed observed test outcome")
        for stream in ("stdout", "stderr"):
            evidence = outcome.get(stream)
            raw = data[side + "." + stream]
            if not isinstance(evidence, dict) or evidence.get("path") != side + "." + stream or evidence.get("size") != len(raw) or evidence.get("sha256") != sha(raw):
                raise ValueError("receipt raw log digest or size mismatch")
    if b"sqlite3.OperationalError: database is locked" not in data["before.stderr"]:
        raise ValueError("missing documented negative baseline failure")
    if b"FAILED (errors=1)" not in data["before.stderr"] or b"\nOK" not in data["after.stderr"]:
        raise ValueError("missing source-exact test runner outcome")
    return receipt


class QueueRetrospectiveEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = strict_json(RECORD.read_bytes())
        cls.archive = ARCHIVE.read_bytes()

    def test_exact_archive_and_all_member_hashes(self):
        receipt = verify(copy.deepcopy(self.manifest), self.archive)
        self.assertEqual(receipt["verdict"], "OBSERVED_EXIT_STATUS_IMPROVEMENT")

    def test_modified_archive_is_rejected(self):
        archive = self.archive[:-1] + bytes([self.archive[-1] ^ 1])
        with self.assertRaisesRegex(ValueError, "ZIP byte identity"):
            verify(copy.deepcopy(self.manifest), archive)

    def test_modified_manifest_archive_hash_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["archive"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "ZIP byte identity"):
            verify(manifest, self.archive)

    def test_downgraded_source_identity_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["source"]["before_commit"] = "0" * 40
        with self.assertRaisesRegex(ValueError, "source identities"):
            verify(manifest, self.archive)

    def test_promoted_claim_status_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["status"] = "Accepted"
        with self.assertRaisesRegex(ValueError, "promote"):
            verify(manifest, self.archive)

    def test_no_factory_superiority_claim_is_admitted(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["observation_scope"] = "proof of superior autonomous factory"
        with self.assertRaisesRegex(ValueError, "prospective trial"):
            verify(manifest, self.archive)

    def test_missing_hosted_provenance_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["collector"]["workflow_run_id"] = None
        with self.assertRaisesRegex(ValueError, "provenance"):
            verify(manifest, self.archive)

    def test_forged_manifest_pass_result_is_rejected(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["observed"]["before"]["status"] = "PASS"
        with self.assertRaisesRegex(ValueError, "changed observed"):
            verify(manifest, self.archive)


if __name__ == "__main__":
    unittest.main()
