"""Fail-closed registration and measurement boundaries, not campaign gold labels."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('far_internal_eval', ROOT / 'tools/run_internal_investigation_evaluation.py')
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


class InternalCampaignTests(unittest.TestCase):
    def corpus(self):
        return {'schema': 'far-internal-exploratory-corpus/1',
                'source_to_report': [{'case_id': 'control', 'reference': {'label_origin': 'PROJECT_AUTHORED_CONTROL_NOT_EXTERNAL_GOLD'},
                    'config': {'source': {'kind': 'text', 'text': 'Developer control.'}, 'proposal_mode': 'supplied'}}],
                'formal_comparison': [{'case_id': 'formal-control'}], 'raw_comparison_case_ids': ['control']}

    def test_duplicate_or_escaping_case_identity_is_rejected(self):
        for mutate in ('duplicate', 'escape'):
            corpus = self.corpus()
            if mutate == 'duplicate': corpus['source_to_report'].append(copy.deepcopy(corpus['source_to_report'][0]))
            else: corpus['source_to_report'][0]['case_id'] = '../escape'
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): evaluation.validate_cases(corpus)

    def test_network_model_or_external_gold_promotion_is_rejected(self):
        for mutate in ('network', 'provider', 'model', 'gold'):
            corpus = self.corpus(); row = corpus['source_to_report'][0]
            if mutate == 'network': row['config']['source']['kind'] = 'url'
            elif mutate == 'provider': row['config']['discovery'] = 'tavily'
            elif mutate == 'model': row['config']['proposal_mode'] = 'openai'
            else: row['reference']['label_origin'] = 'INDEPENDENT_GOLD'
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): evaluation.validate_cases(corpus)

    def test_unknown_comparator_case_is_rejected(self):
        corpus = self.corpus(); corpus['raw_comparison_case_ids'].append('unregistered')
        with self.assertRaises(ValueError): evaluation.validate_cases(corpus)

    def test_json_duplicate_keys_never_silently_replace_registration(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'record.json'; path.write_text('{"status":"frozen","status":"forged"}')
            with self.assertRaises(ValueError): evaluation.read(path)

    def test_known_frozen_record_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'freeze.json'; path.write_text('retained')
            with self.assertRaisesRegex(ValueError, 'preserve history'): evaluation.freeze(path, d)
            self.assertEqual(path.read_text(), 'retained')

    def test_registration_cannot_promote_external_verification(self):
        with patch.object(evaluation, 'read', return_value={'schema': 'far-internal-exploratory-registration/1',
                     'external_verification': 'VERIFIED', 'reference_independence': True}):
            with self.assertRaisesRegex(ValueError, 'boundary'): evaluation.validate_registration('unused')

    def test_missing_bound_source_is_rejected_before_any_execution(self):
        record = {'schema': 'far-internal-exploratory-registration/1', 'external_verification': 'DEFERRED_BY_USER',
                  'reference_independence': False, 'files': {}}
        with patch.object(evaluation, 'read', return_value=record):
            with self.assertRaisesRegex(ValueError, 'incomplete'): evaluation.validate_registration('unused')

    def test_changed_bound_bytes_fail_closed(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as d:
            path = Path(d) / 'control.txt'; path.write_text('original')
            name = str(path.relative_to(ROOT))
            record = {'schema': 'far-internal-exploratory-registration/1', 'external_verification': 'DEFERRED_BY_USER',
                      'reference_independence': False, 'files': {name: evaluation.sha(path.read_bytes())}}
            path.write_text('changed')
            with patch.object(evaluation, 'bound_files', return_value=[path]), patch.object(evaluation, 'read', return_value=record):
                with self.assertRaisesRegex(ValueError, 'drifted'): evaluation.validate_registration('unused')

    def test_child_process_environment_does_not_inherit_keys(self):
        with patch.dict(evaluation.os.environ, {'OPENAI_API_KEY': 'synthetic', 'TAVILY_API_KEY': 'synthetic',
                        'NOESIS_JEV_ENABLED': 'true', 'GH_TOKEN': 'synthetic'}):
            env = evaluation.clean_environment()
        self.assertNotIn('OPENAI_API_KEY', env); self.assertNotIn('GH_TOKEN', env)
        self.assertNotIn('TAVILY_API_KEY', env); self.assertEqual(env['NOESIS_JEV_ENABLED'], 'false')
        self.assertEqual(env['HF_HUB_OFFLINE'], '1')

    def test_workspace_exclusion_is_relative_to_the_run_not_host_root(self):
        with tempfile.TemporaryDirectory(prefix='workspace-') as d:
            root = Path(d); (root/'receipt.json').write_text('retained')
            (root/'workspace').mkdir(); (root/'workspace'/'db').write_text('generated')
            files = evaluation.artifact_inventory(root)
            self.assertEqual(set(files), {'receipt.json'})
            self.assertEqual(files['receipt.json'], evaluation.sha(b'retained'))

    def test_relative_run_path_becomes_absolute_before_subprocess_adapters(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / 'case'
            relative = Path(evaluation.os.path.relpath(target, Path.cwd()))
            seen = []
            def far(config, destination):
                seen.append(destination); return {'claim_quotes': []}
            def noesis(config, question, destination, cli):
                seen.append(destination); return {'claim_quotes': []}
            case = {'case_id': 'path-control', 'config': {'source': {'kind': 'text', 'text': 'A control.'}}}
            with patch.object(evaluation, 'raw_far', side_effect=far), patch.object(evaluation, 'raw_noesis', side_effect=noesis):
                evaluation.raw_pair(case, relative, Path('/unused/cli'))
            self.assertTrue(all(path.is_absolute() for path in seen))
            self.assertEqual(seen, [target/'far', target/'noesis'])
            self.assertTrue((target/'common-input.json').is_file())

    def test_retained_history_import_binds_read_once_bytes_to_verified_manifest(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as d:
            prior=Path(d); package=prior/'far/package';package.mkdir(parents=True)
            payload={'sources':[{'id':'primary','text':'retained control','sha256':evaluation.sha(b'retained control')}]}
            raw=evaluation.canonical(payload);(package/'input.json').write_bytes(raw)
            proof={'_verified_manifest':{'files_sha256':{'input.json':evaluation.sha(raw)}}}
            verifier=SimpleNamespace(verify_package=lambda *a,**kw:proof)
            with patch.object(evaluation,'modules',return_value=(None,None,verifier,None,None,None)):
                state=evaluation.retained_history_state(prior)
                self.assertEqual(state['prior_text'],'retained control')
                proof['_verified_manifest']['files_sha256']['input.json']='0'*64
                with self.assertRaisesRegex(ValueError,'across verification'):evaluation.retained_history_state(prior)

    def test_history_treatment_reuses_prior_warehouse_and_verified_source_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            calls=[]
            def arm(case,destination,cli,**kwargs):
                calls.append((case,kwargs));return {'far':{'elapsed_seconds':1.0},'noesis':{}}
            state={'prior_text':'verified retained bytes','source_hashes':['a'*64], 'noesis_workspace':'/fixed/prior/warehouse'}
            pair={'id':'history-control','prior_text':'original control','followup_text':'later control','question':'control?'}
            with patch.object(evaluation,'raw_pair',side_effect=arm),patch.object(evaluation,'retained_history_state',return_value=state):
                result=evaluation.history_comparison(pair,Path(d)/'case',Path('/unused'))
            self.assertEqual(len(calls),3)
            self.assertEqual(calls[1][0]['config']['source']['text'],'original control')
            self.assertEqual(calls[2][0]['config']['evidence_sources'][0]['text'],'verified retained bytes')
            self.assertEqual(calls[2][1]['history_state']['noesis_workspace'],'/fixed/prior/warehouse')
            self.assertFalse(result['customer_value_established'])

    def test_far_elapsed_time_includes_replay_and_field_adapter(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as d:
            destination=Path(d);package=destination/'package';package.mkdir()
            (package/'input.json').write_text(json.dumps({'claims':[{'span':{'quote':'control'}}],'sources':[]}))
            phases=[]
            def clock():
                if not phases:return 0.0
                self.assertEqual(phases,['cli','replay','field']);return 9.0
            def command(*a,**kw):phases.append('cli');return {'elapsed_seconds':2.0}
            def replay(*a,**kw):phases.append('replay');return {'replay_match':True}
            def predictions(*a,**kw):phases.append('field');return [{'verdict':'ABSTAIN'}]
            with patch.object(evaluation,'time',SimpleNamespace(perf_counter=clock)),patch.object(evaluation,'command',side_effect=command),patch.object(evaluation,'modules',return_value=(None,None,SimpleNamespace(verify_package=replay),SimpleNamespace(predictions_from_far_bundle=predictions),None,None)):
                result=evaluation.raw_far({'source':{'kind':'text','text':'control'}},destination)
            self.assertEqual(result['elapsed_seconds'],9.0)
            self.assertEqual(result['cli_elapsed_seconds'],2.0)

    def test_runtime_logic_bound_and_frozen_study_bytes_are_not_changed(self):
        # This exploratory harness does not modify engine, field adapter or frozen study contracts.
        source = (ROOT / 'tools/run_internal_investigation_evaluation.py').read_text()
        self.assertNotIn('permit_model=True', source)
        self.assertNotIn('shell=True', source)
        protocol = evaluation.read(evaluation.CASE_DIR / 'protocol-v1.json')
        self.assertEqual(protocol['external_verification'], 'DEFERRED_BY_USER')
        self.assertEqual(protocol['budgets']['external_api_calls'], 0)
        self.assertIn('customer benefit', protocol['metrics']['unmeasured'])


if __name__ == '__main__': unittest.main()
