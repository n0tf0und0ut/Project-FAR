"""Post-execution replay controls; the prospectively frozen scorer stays intact."""
from pathlib import Path
import json
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import verify_live_commercial_evaluation as verifier


class LiveCommercialVerifierTests(unittest.TestCase):
    def test_unchanged_portable_copy_verifies(self):
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / 'copy'
            shutil.copytree(verifier.DATA, copied)
            self.assertEqual(verifier.verify(copied, replay=False)['verified_retrieval_receipts'], 12)

    def test_forged_inventory_cannot_omit_a_corrupted_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / 'copy'
            shutil.copytree(verifier.DATA, copied)
            manifest = copied / 'artifact-manifest-v2.json'
            value = json.loads(manifest.read_text())
            value['files'].pop('README.md')
            manifest.write_text(json.dumps(value))
            (copied / 'README.md').write_text('Changed evidence interpretation')
            with self.assertRaisesRegex(ValueError, 'manifest identity'):
                verifier.verify(copied, replay=False)

    def test_recomputed_manifest_cannot_rebind_registered_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / 'copy'
            shutil.copytree(verifier.DATA, copied)
            target = copied / 'protocol-v1.json'
            target.write_text('{}')
            manifest = copied / 'artifact-manifest-v2.json'
            value = json.loads(manifest.read_text())
            value['files']['protocol-v1.json'] = verifier.digest(target.read_bytes())
            manifest.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, 'manifest identity'):
                verifier.verify(copied, replay=False)


if __name__ == '__main__':
    unittest.main()
