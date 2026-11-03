"""Archive integrity, frozen-score, timing-order, and regression mutations.

Tests validate finite submitted evidence, never general reliability or authority.
"""
from __future__ import annotations
import base64
import copy
import importlib.util
import json
from pathlib import Path
import unittest

from tools import model_architecture_external as m
from tools import check_model_architecture_external_archive as audit

ROOT=Path(__file__).resolve().parents[1]
ARCHIVE=ROOT/'research/model-architecture-search/archive-v0.3.zip.b64'


class ArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ARCHIVE.is_file():
            raise unittest.SkipTest('original v0.3 evidence archive not available')
        cls.raw=base64.b64decode(ARCHIVE.read_bytes())

    def test_archived_member_integrity_and_original_source(self):
        if not importlib.util.find_spec('sklearn') or not importlib.util.find_spec('torch'):
            self.skipTest('optional ML dependencies unavailable for score reconstruction')
        res=audit.parse_archive(self.raw)
        self.assertEqual(res['n_scored'],96)
        self.assertFalse(res['primary_pass'])
        self.assertTrue(res['full_replay_receipt'])

    def test_one_byte_mutant_fails_closed(self):
        with self.assertRaises((ValueError, Exception)):
            audit.parse_archive(self.raw[:-20]+b'altered',require_replay=False)

    @unittest.skipUnless(importlib.util.find_spec('sklearn'), 'optional scikit-learn missing')
    def test_substituted_score_and_missing_trial_both_fail(self):
        import zipfile,io
        with zipfile.ZipFile(io.BytesIO(self.raw)) as z:
            original=json.loads(z.read('RESULTS-V0.3.json'))
        cases=[]
        r=copy.deepcopy(original)
        r['records'][0]['test_metrics']['accuracy']=1.0
        cases.append(r)
        r=copy.deepcopy(original)
        r['records'].pop()
        cases.append(r)
        for changed in cases:
            changed['report_sha256']=m.sha(m.canonical({k:v for k,v in changed.items() if k!='report_sha256'}))
            with self.assertRaises(ValueError):
                m.verify(changed)

    def test_archived_manifest_matches_source_and_protocol(self):
        import zipfile,io
        with zipfile.ZipFile(io.BytesIO(self.raw)) as z:
            source=z.read('model_architecture_external.py')
            protocol=z.read('protocol-v0.3.json')
            manifest=json.loads(z.read('manifest.json'))
            self.assertEqual(manifest['model_architecture_external.py'],m.sha(source))
            self.assertEqual(manifest['protocol-v0.3.json'],m.sha(protocol))
            self.assertEqual(json.loads(protocol)['precommit_source_sha256'],m.sha(source))

if __name__=='__main__':
    unittest.main()
