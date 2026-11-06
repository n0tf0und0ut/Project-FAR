"""Post-execution replay controls; the prospectively frozen scorer stays intact."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import verify_live_commercial_evaluation as verifier


class LiveCommercialVerifierTests(unittest.TestCase):
    def historical_worktree(self):
        if not shutil.which('git') or subprocess.run(['git', 'cat-file', '-e', verifier.BASE],
                cwd=ROOT, capture_output=True).returncode:
            self.skipTest('historical Git objects are required for source-reconstruction controls')
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        copied = Path(temporary.name) / 'candidate'
        subprocess.run(['git', 'worktree', 'add', '--detach', str(copied), 'HEAD'],
                       cwd=ROOT, check=True, capture_output=True)
        self.addCleanup(lambda: subprocess.run(['git', 'worktree', 'remove', '--force', str(copied)],
                                             cwd=ROOT, check=True, capture_output=True))
        runtime = copied / 'commercial/far-investigation-audit'
        # Candidate code must not become the policy or executable for old evidence.
        (runtime / 'full_cli.py').write_text('raise RuntimeError("candidate code executed")')
        (runtime / 'new_candidate_extension.py').write_text('not valid Python')
        return copied, runtime / 'evaluation/live-001'

    def test_evolved_source_and_new_files_cannot_change_historical_replay(self):
        copied, data = self.historical_worktree()
        with patch.object(verifier, 'ROOT', copied), patch.object(verifier, 'DATA', data):
            result = verifier.verify(data)
        self.assertEqual(result['historical_runtime_sources_verified'], 19)
        self.assertTrue(result['portable_replay_executed'])
        self.assertEqual(result['runtime_base_commit'], verifier.BASE)

    def test_mismatched_recovered_git_source_fails_before_execution(self):
        copied, data = self.historical_worktree()
        false_blob = subprocess.CompletedProcess(['git', 'show'], 0, stdout=b'wrong source', stderr=b'')
        with patch.object(verifier, 'ROOT', copied), patch.object(verifier, 'DATA', data), \
             patch.object(verifier.subprocess, 'run', return_value=false_blob):
            with self.assertRaisesRegex(ValueError, 'frozen source unavailable or mismatched'):
                verifier.verify(data)

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

    def test_final_inventory_cannot_be_downgraded_to_hide_forged_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / 'copy'
            shutil.copytree(verifier.DATA, copied)
            (copied / 'artifact-manifest-v2.json').unlink()
            (copied / 'verification-evidence-v1.json').write_text('{"replays":999999}')
            with self.assertRaisesRegex(ValueError, 'final artifact manifest is required'):
                verifier.verify(copied)

    def test_verified_bytes_are_not_reread_after_file_replacement(self):
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / 'copy'
            shutil.copytree(verifier.DATA, copied)
            resolve = verifier.frozen_runtime
            def replace_after_inventory(*args):
                (copied / 'registration-v1.json').write_text('not JSON')
                (copied / 'far-deliveries-v1.zip').write_bytes(b'not ZIP')
                return resolve(*args)
            with patch.object(verifier, 'frozen_runtime', side_effect=replace_after_inventory):
                self.assertTrue(verifier.verify(copied)['portable_replay_executed'])
            # A later attempt sees changed bytes and must reject them.
            with self.assertRaisesRegex(ValueError, 'artifact bytes changed'):
                verifier.verify(copied)


if __name__ == '__main__':
    unittest.main()
