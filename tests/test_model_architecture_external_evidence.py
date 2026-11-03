"""Archive integrity, frozen-score, timing-order, and regression mutations.

Tests validate finite submitted evidence, never general reliability or authority.
"""
from __future__ import annotations
import base64
import copy
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

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

    def rewrite_archive(self,change):
        """Coordinate mutable checksums so rejection must check cross-record bindings."""
        with zipfile.ZipFile(io.BytesIO(self.raw)) as z:
            members={name:z.read(name) for name in z.namelist()}
        report=json.loads(members['RESULTS-V0.3.json'])
        change(report,members)
        report['report_sha256']=m.sha(m.canonical({k:v for k,v in report.items() if k!='report_sha256'}))
        members['RESULTS-V0.3.json']=m.canonical(report)+b'\n'
        receipt=json.loads(members['v0.3-replay-full.json'])
        receipt['original_report_sha256']=report['report_sha256']
        receipt['original_journal_sha256']=report['journal_sha256']
        members['v0.3-replay-full.json']=m.canonical(receipt)+b'\n'
        members['manifest.json']=m.canonical({name:m.sha(members[name]) for name in audit.REQUIRED})+b'\n'
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
            for name,data in members.items():
                z.writestr(name,data)
        return out.getvalue(),report,members

    def test_embedded_execution_protocol_cannot_diverge_from_registered_bytes(self):
        for key,value in (('learning_rate',.008),('batch_size',128),
                          ('training_threads',2),('study_id','SUBSTITUTED-STUDY')):
            def change(report,members):
                report['protocol'][key]=value
            raw,_,_=self.rewrite_archive(change)
            with self.subTest(field=key),self.assertRaisesRegex(ValueError,'protocol'):
                audit.parse_archive(raw)

    def test_coordinated_protocol_hashes_cannot_erase_original_journal_binding(self):
        def change(report,members):
            report['protocol']['learning_rate']=.008
            raw=m.canonical(report['protocol'])+b'\n'
            report['environment']['protocol_sha256']=m.sha(raw)
            members['protocol-v0.3.json']=raw
        raw,_,_=self.rewrite_archive(change)
        with self.assertRaisesRegex(ValueError,'journal start environment'):
            audit.parse_archive(raw)

    def test_registered_protocol_still_binds_a_coherently_rewritten_report_history(self):
        def change(report,members):
            report['protocol']['learning_rate']=.008
            report['environment']['protocol_sha256']=m.sha(m.canonical(report['protocol'])+b'\n')
            events=[json.loads(row) for row in members['RESULTS-V0.3.json.journal.jsonl'].splitlines()]
            events[0]['environment']=copy.deepcopy(report['environment'])
            journal=b''.join(m.canonical(event)+b'\n' for event in events)
            members['RESULTS-V0.3.json.journal.jsonl']=journal
            report['journal_sha256']=m.sha(journal)
        _,report,members=self.rewrite_archive(change)
        with self.assertRaisesRegex(ValueError,'differs from registered protocol'):
            audit.verify_report(report,members['RESULTS-V0.3.json.journal.jsonl'],members['protocol-v0.3.json'])

    def test_report_environment_and_study_must_match_execution_configuration(self):
        for key,value in (('device','cuda'),('threads',4),('torch','SUBSTITUTED-RUNTIME'),
                          ('study_id','SUBSTITUTED-STUDY')):
            def change(report,members):
                if key=='study_id':
                    report[key]=value
                else:
                    report['environment'][key]=value
            raw,_,_=self.rewrite_archive(change)
            with self.subTest(field=key),self.assertRaisesRegex(ValueError,'configuration|environment|study'):
                audit.parse_archive(raw)

    @unittest.skipUnless(importlib.util.find_spec('sklearn') and importlib.util.find_spec('torch'),
                         'optional scikit-learn/PyTorch missing; saved replay score reconstruction not executed')
    def test_saved_replay_identity_must_match_the_original_execution(self):
        for key,value in (('study_id','SUBSTITUTED-STUDY'),('source_sha256','0'*64),
                          ('threads_restored',4),('records',[])):
            def change(report,members):
                receipt=json.loads(members['v0.3-replay-full.json'])
                receipt[key]=value
                members['v0.3-replay-full.json']=m.canonical(receipt)+b'\n'
            raw,_,_=self.rewrite_archive(change)
            with self.subTest(field=key),self.assertRaisesRegex(ValueError,'replay'):
                audit.parse_archive(raw)

    def test_journal_start_study_cannot_be_substituted_with_coordinated_hashes(self):
        def change(report,members):
            events=[json.loads(row) for row in members['RESULTS-V0.3.json.journal.jsonl'].splitlines()]
            events[0]['study_id']='SUBSTITUTED-STUDY'
            journal=b''.join(m.canonical(event)+b'\n' for event in events)
            members['RESULTS-V0.3.json.journal.jsonl']=journal
            report['journal_sha256']=m.sha(journal)
        raw,_,_=self.rewrite_archive(change)
        with self.assertRaisesRegex(ValueError,'journal start study'):
            audit.parse_archive(raw)

    def test_standalone_and_replay_reject_protocol_drift_before_training(self):
        from tools import model_architecture_external_replay as replay
        for rebind_digest in (False,True):
            def change(report,members):
                report['protocol']['learning_rate']=.008
                if rebind_digest:
                    report['environment']['protocol_sha256']=m.sha(m.canonical(report['protocol'])+b'\n')
            _,report,members=self.rewrite_archive(change)
            journal=members['RESULTS-V0.3.json.journal.jsonl']
            with self.subTest(rebound_digest=rebind_digest),mock.patch.object(m,'train_one') as train:
                for verify in (audit.verify_report,replay.replay):
                    with self.subTest(boundary=verify.__name__),self.assertRaisesRegex(ValueError,'protocol|journal start environment'):
                        verify(report,journal)
                train.assert_not_called()

    def test_current_standalone_command_rejects_substituted_protocol(self):
        def change(report,members):
            report['protocol']['learning_rate']=.008
        _,report,members=self.rewrite_archive(change)
        with tempfile.TemporaryDirectory() as folder:
            folder=Path(folder)
            result=folder/'report.json'
            journal=folder/'journal.jsonl'
            result.write_bytes(m.canonical(report)+b'\n')
            journal.write_bytes(members['RESULTS-V0.3.json.journal.jsonl'])
            checked=subprocess.run([sys.executable,str(ROOT/'tools/check_model_architecture_external_archive.py'),
                                    '--report',str(result),'--journal',str(journal),
                                    '--protocol',str(ROOT/'research/model-architecture-search/protocol-v0.3.json')],
                                   capture_output=True,text=True)
        self.assertNotEqual(checked.returncode,0)
        self.assertIn('embedded protocol digest mismatch',checked.stderr)

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

    @unittest.skipUnless(importlib.util.find_spec('sklearn') and importlib.util.find_spec('torch'),
                         'optional scikit-learn/PyTorch missing; score reconstruction not executed')
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
                audit.verify_report(changed)

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
