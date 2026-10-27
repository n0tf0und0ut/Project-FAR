"""Retained primary and adverse observations must remain hash-bound and complete."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'commercial/far-investigation-audit/evaluation/internal-001'


class RecordedInternalEvidenceTests(unittest.TestCase):
    def test_portable_archives_retain_every_bound_output_and_no_database(self):
        summary=json.loads((FOLDER/'summary-v1.json').read_text())
        for artifact in summary['artifacts']:
            with self.subTest(run=artifact['run']):
                archive=FOLDER/artifact['archive']
                self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(),artifact['archive_sha256'])
                with zipfile.ZipFile(archive) as z:
                    prefix=artifact['run']+'/'
                    names=z.namelist()
                    self.assertEqual(len(names),len(set(names)))
                    self.assertTrue(all(n.startswith(prefix) and '..' not in PurePosixPath(n).parts and not n.startswith('/') for n in names))
                    self.assertFalse(any('workspace' in PurePosixPath(n).parts for n in names))
                    manifest=json.loads(z.read(prefix+'artifact-manifest.json'))
                    self.assertEqual(set(names),{prefix+n for n in manifest['files']}|{prefix+'artifact-manifest.json'})
                    for name,digest in manifest['files'].items():
                        self.assertEqual(hashlib.sha256(z.read(prefix+name)).hexdigest(),digest,name)
                    self.assertEqual(hashlib.sha256(z.read(prefix+'results.json')).hexdigest(),artifact['result_sha256'])
                    self.assertEqual(z.read(prefix+'results.json'),(FOLDER/(artifact['run']+'-results.json')).read_bytes())

    def test_frozen_cases_have_exactly_the_registered_outputs(self):
        cases=json.loads((FOLDER/'cases-v1.json').read_text())
        source_ids=[x['case_id'] for x in cases['source_to_report']]
        formal_ids=[x['case_id'] for x in cases['formal_comparison']]
        for number in (1,2,3):
            result=json.loads((FOLDER/f'run-{number:03d}-results.json').read_text())
            registration=json.loads((FOLDER/f'registration-v{number}.json').read_text())
            self.assertEqual([x['case_id'] for x in result['source_to_report']],source_ids)
            self.assertEqual([x['case_id'] for x in result['formal']],formal_ids)
            self.assertEqual(registration['source_case_ids'],source_ids)
            self.assertEqual(registration['formal_case_ids'],formal_ids)
            self.assertFalse(registration['reference_independence'])
            self.assertEqual(registration['external_verification'],'DEFERRED_BY_USER')

    def test_initial_adapter_failure_is_not_erased_or_called_a_competitor_loss(self):
        failed=json.loads((FOLDER/'run-001-results.json').read_text())
        self.assertEqual(failed['status'],'COMPLETED_WITH_RECORDED_FAILURES')
        self.assertEqual(len(failed['failures']),10)
        self.assertFalse(failed['raw_comparison'])
        repaired=json.loads((FOLDER/'registration-v2.json').read_text())
        self.assertTrue(repaired['same_case_bytes_as_predecessor'])
        self.assertEqual(repaired['repair_of_registration_sha256'],hashlib.sha256((FOLDER/'registration-v1.json').read_bytes()).hexdigest())

    def test_summary_cannot_hide_semantic_gap_abstention_or_solver_bound(self):
        summary=json.loads((FOLDER/'summary-v1.json').read_text())
        result=json.loads((FOLDER/'run-003-results.json').read_text())
        self.assertEqual(summary['run_003_result_sha256'],hashlib.sha256((FOLDER/'run-003-results.json').read_bytes()).hexdigest())
        self.assertEqual(summary['source_to_report']['deliberately_unfaithful_interpretations_with_formally_valid_inference'],sum(x['unfaithful_mapping_can_pass_formal_check'] for x in result['source_to_report']))
        self.assertEqual(summary['formal']['far_bound_abstentions'],sum(x['far_abstained'] for x in result['formal']))
        self.assertFalse(summary['commercial_advantage_established'])
        self.assertIsNone(summary['independent_factual_accuracy'])
        for row in result['source_to_report']:
            self.assertFalse(row['observations']['semantic_mapping_verified'])
            self.assertTrue(all(v=='ABSTAIN' for v in row['observations']['factual_verdicts']))
        for pair in result['history']:
            self.assertTrue(pair['conditions'][1]['noesis']['reused_prior_warehouse'])
            self.assertTrue(pair['retained_state_binding']['prior_input_sha256'])
            self.assertFalse(pair['customer_value_established'])


if __name__=='__main__':unittest.main()
