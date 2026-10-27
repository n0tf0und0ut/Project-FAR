"""Exposed hostile follow-ups: missing observations cannot prove a negative."""
import copy
import json
from pathlib import Path
import tempfile
import hashlib
import subprocess
import sys
import unittest
from mechanization.far_mechanization.cognitive import CognitiveDocument, CognitiveValidationError, audit
from mechanization.far_mechanization.cli import _cognitive
from argparse import Namespace

ROOT = Path(__file__).resolve().parents[1]


class MissingCognitiveDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {x['id']:x['input'] for x in json.loads((ROOT/'research/cognitive-audit/frozen-v1/cases.json').read_text())['cases']}

    def verdict(self, data):
        return audit(CognitiveDocument.from_dict(data))['diagnoses'][0]['status']

    def test_missing_confidence_does_not_prove_no_sensitivity(self):
        data = copy.deepcopy(self.cases['user_stance-stable'])
        data['traces'][1]['confidence'] = None
        self.assertEqual(self.verdict(data),'UNKNOWN')
        data['traces'][1]['position'] = 'YES'
        self.assertEqual(self.verdict(data),'SUPPORTED')

    def test_unknown_locator_cannot_be_silently_treated_as_resolved(self):
        data = copy.deepcopy(self.cases['citation-supported'])
        data['probes'][0]['facts']['locator_state'] = 'UNKNOWN'
        self.assertEqual(self.verdict(data),'UNKNOWN')
        data['probes'][0]['facts']['passage_support'] = 'CONTRADICTED'
        self.assertEqual(self.verdict(data),'SUPPORTED')

    def test_unknown_upstream_lineage_propagates_to_derived_source(self):
        data = copy.deepcopy(self.cases['lineage-copy'])
        data['source_lineage'][0]['relationship'] = 'unknown'
        data['probes'][0]['facts']['source_refs'] = ['copy']
        self.assertEqual(self.verdict(data),'UNKNOWN')

    def test_malformed_json_has_contract_error_and_cli_exit_two(self):
        for raw in ('{','[] trailing','{"format_version":'):
            with self.subTest(raw=raw),self.assertRaises(CognitiveValidationError):CognitiveDocument.loads(raw)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'invalid.json';path.write_text('{')
            code,out,err=_cognitive(Namespace(file=str(path),cognitive_command='audit'))
            self.assertEqual(code,2);self.assertFalse(json.loads(out)['valid']);self.assertFalse(err)

    def test_dense_lineage_dag_finishes_without_revisiting_every_path(self):
        data=copy.deepcopy(self.cases['lineage-copy'])
        ids=['s','copy']
        for i in range(35):
            name='node-'+str(i)
            data['sources'].append({'id':name,'text':name,'sha256':hashlib.sha256(name.encode()).hexdigest()})
            data['source_lineage'].append({'schema':'far-source-lineage/1.0','source_id':name,'relationship':'derived','root_lineage_ids':['root'],'upstream_source_ids':ids.copy()})
            ids.append(name)
        data['probes'][0]['facts']['source_refs']=[ids[-1]]
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'dense.json';path.write_text(json.dumps(data))
            result=subprocess.run([sys.executable,'-m','mechanization.far_mechanization.cli','cognitive','audit',str(path)],cwd=ROOT,capture_output=True,text=True,timeout=5)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['diagnoses'][0]['status'],'SUPPORTED')


if __name__ == '__main__':unittest.main()
