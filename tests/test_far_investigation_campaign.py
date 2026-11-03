"""Campaign integrity controls, not empirical autonomy evidence."""
import hashlib
import copy
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
