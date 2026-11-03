"""Campaign integrity controls, not empirical autonomy evidence."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.far_investigation_campaign import audit_directory, summarize


class CampaignTests(unittest.TestCase):
    def test_summary_never_invents_semantic_success_from_completion(self):
        row = {'mode': 'agent', 'metrics': {'pipeline_completed': True, 'integrity_valid': True,
            'frozen_valid_family': True, 'rejected_calls': 0, 'controller_substitutions': 0,
            'http_calls': 4, 'model_tokens': 100}}
        result = summarize([row])
        self.assertEqual(result['agent']['pipeline_completed'], 1)
        self.assertIsNone(result['agent']['semantic_successes'])
        self.assertEqual(result['agent']['superiority'], 'NOT_ESTABLISHED')
        self.assertEqual(result['deterministic']['attempted'], 0)

    def test_missing_and_mutated_evidence_bytes_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'source.json').write_text('{}')
            manifest = {'files': [{'path': 'source.json', 'sha256': hashlib.sha256(b'{}').hexdigest()}]}
            (root / 'evidence-manifest.json').write_text(json.dumps(manifest))
            self.assertTrue(audit_directory(root)['valid'])
            (root / 'source.json').write_text('{"changed":true}')
            self.assertFalse(audit_directory(root)['valid'])
            (root / 'source.json').unlink()
            self.assertFalse(audit_directory(root)['valid'])

    def test_archive_cannot_hide_missing_campaign_transcript(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / 'run.zip'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('campaign.json', json.dumps({'rows': [{'transcript': 'missing.json', 'transcript_sha256': '0'*64}]}))
            (root / 'evidence-manifest.json').write_text(json.dumps({'files': [{'path': 'run.zip',
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'audit_transcripts': True}]}))
            self.assertFalse(audit_directory(root)['valid'])

    def test_manifest_cannot_read_outside_its_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'evidence-manifest.json').write_text(json.dumps({'files': [{'path': '../outside', 'sha256': '0'*64}]}))
            self.assertFalse(audit_directory(root)['valid'])


if __name__ == '__main__':
    unittest.main()
