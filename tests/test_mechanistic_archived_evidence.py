"""Verify original successful/failed executions without replacing measurements."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from mechanization.far_mechanization.mechanistic_fidelity import MechanismAudit

ROOT = Path(__file__).resolve().parents[1] / "evaluation/evidence"


class PreservedExecutionTests(unittest.TestCase):
    def test_all_original_archives_are_intact_and_case_audits_recompute(self):
        manifest = json.loads((ROOT / "pretrained-originals-manifest.json").read_text())
        self.assertEqual(len(manifest["executions"]), 3)
        for item in manifest["executions"]:
            raw = (ROOT / item["archive"]).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), item["archive_sha256"])
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                self.assertEqual(set(z.namelist()), set(item["members"]))
                for name, expected in item["members"].items():
                    self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(), expected)
                with tempfile.TemporaryDirectory() as tmp:
                    trace = Path(tmp) / "trace.json"
                    trace.write_bytes(z.read("far_mech_pretrained_trace.json"))
                    result = MechanismAudit.load(trace).evaluate()
                    self.assertEqual(result, json.loads(z.read("far_mech_pretrained_result.json"))["mechanism_audit"])

    def test_engineering_regression_preserves_failure_and_full_replay_receipt(self):
        raw = (ROOT / "pretrained-replay-regression-20261103.zip").read_bytes()
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            manifest = json.loads(z.read("manifest.json"))
            self.assertEqual(set(z.namelist()), set(manifest) | {"manifest.json"})
            for name, expected in manifest.items():
                self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(), expected)
            self.assertIn(b"two-token replay mismatch heldout-03 replacement_probs", z.read("replay-original-failure.log"))
            receipt = json.loads(z.read("replay-corrected.json"))
            self.assertEqual(receipt["cases_replayed"], 32)
            self.assertEqual(receipt["distribution_pairs_replayed"], 64)
            self.assertEqual(receipt["max_absolute_full_vocabulary_kl_error"], 0)
            self.assertEqual(receipt["full_kl_tolerance"], 5e-8)


if __name__ == "__main__":
    unittest.main()
