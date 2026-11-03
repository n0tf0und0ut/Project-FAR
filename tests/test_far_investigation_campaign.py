"""Campaign integrity controls, not empirical autonomy evidence."""
import hashlib
import copy
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import socket
import subprocess
import sys
import os
import fcntl
from unittest.mock import patch

from tools.far_investigation_campaign import audit_directory, metrics, summarize, run


class CampaignTests(unittest.TestCase):
    def setUp(self):
        if self._testMethodName in (
                'test_live_child_listener_command_and_mapped_model_are_bound_together',
                'test_occupied_model_endpoint_cannot_attest_an_executable_that_exits_43'):
            # Hosted assurance can run canonical and health suites concurrently.
            # They exercise the same fixed production endpoint in one namespace.
            lock = (Path(tempfile.gettempdir()) / 'project-far-model-endpoint-8085.test.lock').open('a')
            self.addCleanup(lock.close)
            fcntl.flock(lock, fcntl.LOCK_EX)

    def test_live_child_listener_command_and_mapped_model_are_bound_together(self):
        from tools.far_investigation_campaign import _file_identity, _server_identity
        with tempfile.TemporaryDirectory() as temporary:
            model = Path(temporary) / 'fixture.gguf'
            model.write_bytes(b'explicit local process fixture, no model inference')
            code = ('import mmap,socket,sys; f=open(sys.argv[2],"rb"); '
                    'm=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ); '
                    's=socket.socket(); s.bind(("127.0.0.1",8085)); s.listen(); '
                    'print("READY",flush=True); sys.stdin.read()')
            command = [str(Path(sys.executable).resolve()), '-c', code, '--model', str(model)]
            child = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                self.assertEqual(child.stdout.readline(), b'READY\n')
                executable_identity, model_identity = _file_identity(sys.executable), _file_identity(model)
                observed = _server_identity(child, command, executable_identity, model_identity)
                self.assertEqual(observed['pid'], child.pid)
                self.assertTrue(observed['listener_inode'].isdigit())
                for altered in ('command', 'executable', 'model', 'owner'):
                    with self.subTest(altered=altered), self.assertRaises(RuntimeError):
                        if altered == 'owner':
                            other = type('WrongProcess', (), {'pid': os.getpid(), 'poll': lambda self: None})()
                            _server_identity(other, command, executable_identity, model_identity)
                        else:
                            _server_identity(child, command + ['changed'] if altered == 'command' else command,
                                (0, 0, 0, 0) if altered == 'executable' else executable_identity,
                                (0, 0, 0, 0) if altered == 'model' else model_identity)
                child.terminate()
                child.wait(timeout=5)
                with self.assertRaisesRegex(RuntimeError, 'exited'):
                    _server_identity(child, command, executable_identity, model_identity)
            finally:
                if child.poll() is None:
                    child.terminate()
                child.communicate(timeout=5)

    def test_occupied_model_endpoint_cannot_attest_an_executable_that_exits_43(self):
        # A local fixture process owns the endpoint; it is never a model run.
        with socket.socket() as listener, tempfile.TemporaryDirectory() as temporary:
            listener.bind(('127.0.0.1', 8085))
            listener.listen()
            root = Path(temporary)
            model = root / 'model.gguf'
            model.write_bytes(b'fixture weights, no inference')
            runner = root / 'exit43'
            runner.write_text('#!/bin/sh\nexit 43\n')
            runner.chmod(0o700)
            selection = root / 'selection.json'
            selection.write_text(json.dumps({'tasks': [{'id': 'test', 'question': 'test question',
                'source_hints': ['https://example.org/a']}]}))
            from tools import far_investigation_campaign as campaign
            class ExistingServerResponse:
                status = 200
                def __enter__(self): return self
                def __exit__(self, *_): pass
            # A tempting unrelated health success must never trigger a task.
            with patch.object(campaign, 'MODEL_SHA256', campaign.file_sha(model)), \
                    patch.object(campaign.urllib.request, 'urlopen', return_value=ExistingServerResponse()), \
                    patch.object(campaign.Investigation, 'run_agent', return_value={}), \
                    patch.object(campaign, 'metrics', return_value={}), \
                    patch.object(campaign, 'summarize', return_value={}):
                with self.assertRaisesRegex(RuntimeError, 'occupied'):
                    run(selection, root / 'output', model_path=model, server_path=runner, modes=('agent',))
            record = json.loads((root / 'output' / 'campaign.json').read_text())
            self.assertEqual(record['status'], 'FAILED_OR_INCOMPLETE')
            self.assertEqual(record['rows'], [])
            self.assertNotIn('server_process_identity', record)

    def test_empty_counterexample_valuation_counts_as_a_native_witness(self):
        from tools.far_investigation_engine import Investigation, RetrievalPolicy
        from tests.test_far_investigation_engine import FixtureRetriever, ScriptedFixtureModel, full_script
        claims = [{'statement': 'False follows from no premises', 'type': 'mathematical',
            'interpretations': [{'statement': 'Boolean entailment', 'evidence_ids': ['ev.1'],
                'plan': {'kind': 'truth_table', 'premises': [], 'conclusion': 'False',
                         'premise_quote': 'no premises', 'conclusion_quote': 'False'}}]}]
        runtime = Investigation('Does False follow from no premises?',
            RetrievalPolicy(('example.org', 'independent.example.org')), fetcher=FixtureRetriever())
        state = runtime.run_agent(ScriptedFixtureModel(full_script(claims)))
        result = metrics(state)
        self.assertTrue(result['pipeline_completed'], result)
        self.assertTrue(result['integrity_valid'], result)
        self.assertEqual(state['evaluations'][0]['result']['counterexample'], {})
        self.assertEqual(result['native_counterexamples'], 1)

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



class RetainedCampaignReplayTests(unittest.TestCase):
    """Mutation tests alter copies; original hosted evidence is never rewritten."""
    @classmethod
    def setUpClass(cls):
        cls.evidence=Path(__file__).resolve().parents[1]/"research/investigation-engine"
        cls.manifest=json.loads((cls.evidence/"evidence-manifest.json").read_text())
        cls.entry=next(e for e in cls.manifest["files"] if e.get("audit_transcripts"))
        with zipfile.ZipFile(cls.evidence/cls.entry["path"]) as archive:
            cls.files={name:archive.read(name) for name in archive.namelist()}
        cls.campaign=json.loads(cls.files["campaign.json"])

    def mutated(self, mutation=None, duplicate_member=False, mutate_selection=False):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            selection=(self.evidence/self.entry["selection_path"]).read_bytes()
            if mutate_selection:
                document=json.loads(selection)
                document["tasks"][0]["question"]="changed exposure"
                selection=json.dumps(document).encode()
            (root/self.entry["selection_path"]).write_bytes(selection)
            campaign=copy.deepcopy(self.campaign)
            if mutation:
                mutation(campaign)
            path=root/self.entry["path"]
            with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_DEFLATED) as archive:
                for name,raw in self.files.items():
                    archive.writestr(name,json.dumps(campaign).encode() if name=="campaign.json" else raw)
                if duplicate_member:
                    import warnings
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore",UserWarning)
                        archive.writestr("campaign.json",json.dumps(campaign))
            entry=copy.deepcopy(self.entry)
            entry["sha256"]=hashlib.sha256(path.read_bytes()).hexdigest()
            (root/"evidence-manifest.json").write_text(json.dumps({"files":[entry]}))
            return audit_directory(root)

    def test_original_exact_archive_replays_24_transcripts(self):
        result=audit_directory(self.evidence)
        self.assertTrue(result["valid"],result["errors"])
        self.assertEqual(result["audited_transcripts"],24)

    def test_original_failed_h201_transcript_cannot_gain_an_orphan_source(self):
        from tests.test_far_investigation_audit import reseal
        from tests.test_far_investigation_engine import receipt
        state = json.loads(self.files['H201-agent.json'])
        self.assertEqual(metrics(state)['retrieved_sources'], 0)
        self.assertTrue(metrics(state)['integrity_valid'])
        state['sources']['src.1'] = receipt('https://api.github.com/orphan', 'orphan retained')
        reseal(state)
        observed = metrics(state)
        self.assertFalse(observed['integrity_valid'], observed)
        self.assertTrue(any('transport observation' in e for e in observed['integrity_errors']), observed)

    def test_duplicate_exposure_fails_even_with_new_archive_hash(self):
        result=self.mutated(lambda c:c["rows"].append(copy.deepcopy(c["rows"][0])))
        self.assertFalse(result["valid"])
        self.assertTrue(any("exposure" in e for e in result["errors"]))

    def test_missing_exposure_fails(self):
        self.assertFalse(self.mutated(lambda c:c["rows"].pop())["valid"])

    def test_fabricated_completion_or_cost_is_recomputed(self):
        def change(c):
            c["rows"][0]["metrics"].update(pipeline_completed=False,billed_cost=0)
        result=self.mutated(change)
        self.assertFalse(result["valid"])
        self.assertTrue(any("metrics do not reconstruct" in e for e in result["errors"]))

    def test_summary_success_is_not_trusted(self):
        result=self.mutated(lambda c:c["summary"]["agent"].update(pipeline_completed=8))
        self.assertFalse(result["valid"])
        self.assertTrue(any("summary" in e for e in result["errors"]))

    def test_frozen_selection_mutation_fails(self):
        self.assertFalse(self.mutated(mutate_selection=True)["valid"])

    def test_source_identity_mutation_fails(self):
        result=self.mutated(lambda c:c["source_hashes"].update({"tools/far_investigation_engine.py":"0"*64}))
        self.assertFalse(result["valid"])
        self.assertTrue(any("source identity" in e for e in result["errors"]))

    def test_duplicate_zip_member_cannot_shadow_evidence(self):
        self.assertFalse(self.mutated(duplicate_member=True)["valid"])

if __name__ == '__main__':
    unittest.main()
