"""Operational source identity, missingness and no-promotion invariants."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import reconcile_scheduled_research as ops


class OperationalSourceTests(unittest.TestCase):
    def record(self, ids=('SR-001',)):
        return {'schema':'far-research-operations/1','status':'Research','scientific_promotion_authority':False,
                'external_verification':'DEFERRED_BY_USER','entries':[{'source_id':i,'owner_role':'internal maintainer',
                'classification':'RESEARCH_SIGNAL','disposition':'UNVERIFIED','next_test':'Reconstruct exact primary claim.',
                'exit_condition':'Exact assumptions and counterexample checked or UNKNOWN.',
                'evidence_limit':'No independent evidence.','source_evidence_promoted':False} for i in ids]}

    def test_arxiv_abs_pdf_doi_aliases_preserve_versions_and_unknown(self):
        variants=['https://arxiv.org/abs/2610.04888v2','https://arxiv.org/pdf/2610.04888v2.pdf',
                  'https://doi.org/10.48550/arXiv.2610.04888v2','arxiv:2610.04888v2']
        self.assertEqual({ops.identity(x) for x in variants}, {('arxiv:2610.04888','v2')})
        self.assertEqual(ops.identity('https://arxiv.org/abs/2610.04888'), ('arxiv:2610.04888',None))
        self.assertNotEqual(ops.identity(variants[0]), ops.identity('arxiv:2610.04888v1'))

    def test_doi_normalization_reuses_existing_case_insensitive_identifier(self):
        self.assertEqual(ops.identity('https://doi.org/10.1000/Example'), ops.identity('doi:10.1000/example'))

    def test_url_locator_hint_preserves_semantic_query_and_distinguishes_schemes(self):
        a=ops.identity('https://example.org/paper?version=2&utm_source=watch#section')
        self.assertEqual(a,ops.identity('https://example.org/paper?version=2'))
        self.assertNotEqual(a,ops.identity('https://example.org/paper?version=1'))
        self.assertNotEqual(a,ops.identity('http://example.org/paper?version=2'))

    def test_github_repository_aliases_are_not_new_sources(self):
        self.assertEqual(ops.identity('https://github.com/Ikey168/Noesis.git'),ops.identity('https://github.com/ikey168/noesis/'))

    def test_invalid_urls_do_not_become_public_source_proof(self):
        for value in ('', 'file:///private', 'https://user:password@example.org/a', 'doi:', 'doi:garbage', 'arxiv:garbage', 'arxiv:2610.04888v0'):
            with self.subTest(value=value),self.assertRaises(ValueError):ops.identity(value)

    def test_source_set_is_exact_and_missing_owner_or_test_rejected(self):
        for field in ('owner_role','disposition','next_test','exit_condition','evidence_limit'):
            record=self.record();record['entries'][0].pop(field)
            with self.subTest(field=field),self.assertRaises(ValueError):ops.validate_operations(record,['SR-001'])
        record=self.record();record['entries'].append(copy.deepcopy(record['entries'][0]))
        with self.assertRaises(ValueError):ops.validate_operations(record,['SR-001'])
        with self.assertRaises(ValueError):ops.validate_operations(self.record(),['SR-001','SR-002'])

    def test_operational_classification_cannot_promote_evidence_or_resume_external_verification(self):
        for key,value in [('scientific_promotion_authority',True),('external_verification','ACTIVE')]:
            record=self.record();record[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):ops.validate_operations(record,['SR-001'])
        record=self.record();record['entries'][0]['source_evidence_promoted']=True
        with self.assertRaises(ValueError):ops.validate_operations(record,['SR-001'])

    def test_architectural_counterexample_requires_exact_failed_representation_contract(self):
        record=self.record();row=record['entries'][0];row['classification']='ARCHITECTURAL_COUNTEREXAMPLE'
        required=['baseline_anchor','failed_representation','extension_point_insufficiency','strongest_counterargument','reproducer']
        row['architectural_witness']={key:'explicit bounded record' for key in required}
        self.assertEqual(len(ops.validate_operations(record,['SR-001'])),1)
        for field in required:
            changed=copy.deepcopy(record);changed['entries'][0]['architectural_witness'].pop(field)
            with self.subTest(field=field),self.assertRaises(ValueError):ops.validate_operations(changed,['SR-001'])

    def test_alias_join_retains_distinct_observations_and_untrusted_candidate_status(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);folder=root/ops.FOLDER;folder.mkdir(parents=True)
            sources=[{'id':'SR-001','primary_url':'https://arxiv.org/abs/2610.04888v1','evidence_class':'author_report'},
                     {'id':'SR-002','primary_url':'https://doi.org/10.48550/arxiv.2610.04888v2','evidence_class':'author_report'}]
            (folder/'intake-2026-10-20.json').write_text(json.dumps({'entries':sources}))
            (folder/'operations-v1.json').write_text(json.dumps(self.record(('SR-001','SR-002'))))
            corpus=root/'research/corpus';corpus.mkdir(parents=True)
            (corpus/'corpus-v1.0.json').write_text(json.dumps({'sources':[]}))
            candidates=root/'research/living/inbox/candidates';candidates.mkdir(parents=True)
            (candidates/'FAR-LIT-EXAMPLE.json').write_text(json.dumps({'source_key':'doi:10.48550/arxiv.2610.04888'}))
            result=ops.compile_register(root)
            self.assertEqual(len(result['groups']),1)
            group=result['groups'][0]
            self.assertEqual([v['version'] for v in group['version_observations']],['v1','v2'])
            self.assertEqual(len(group['operational_observations']),2)
            self.assertEqual(group['existing_identity_links'][0]['kind'],'untrusted_living_candidate')
            self.assertFalse(result['scientific_promotion_authority'])
            self.assertFalse(result['coverage']['complete_historical_scheduler_outputs'])

    def test_monitoring_snapshot_has_one_monday_brief_and_one_urgent_watch(self):
        state=ops.read(ROOT/ops.FOLDER/'monitoring-state-v1.json')
        tasks={x['title']:x for x in state['tasks']}
        self.assertEqual(set(tasks),{'FAR Decision Brief','FAR Research Watch'})
        self.assertIn('BYDAY=MO',tasks['FAR Decision Brief']['schedule'])
        self.assertIn('BYHOUR=8',tasks['FAR Decision Brief']['schedule'])
        self.assertIn('FREQ=HOURLY',tasks['FAR Research Watch']['schedule'])
        for task in tasks.values():
            self.assertEqual(task['timezone'],'America/New_York')
            self.assertIn('operations-index-v1.json',task['prompt'])
            self.assertIn('explicitly deferred external scientific verification',task['prompt'])
        self.assertTrue(all(not x['is_enabled'] for x in state['overlapping_tasks_left_paused']))
        self.assertFalse(state['scientific_promotion_authority'])

    def test_committed_index_rebuilds_from_one_operational_source(self):
        expected=ops.encoded(ops.compile_register())
        self.assertEqual((ROOT/ops.FOLDER/'operations-index-v1.json').read_bytes(),expected)
        self.assertEqual(ops.compile_register()['coverage']['intake_sources'],15)


if __name__=='__main__':unittest.main()
