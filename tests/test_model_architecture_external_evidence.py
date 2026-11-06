"""Archive integrity, frozen-score, timing-order, and regression mutations.

Tests validate finite submitted evidence, never general reliability or authority.
"""
from __future__ import annotations
import base64
import copy
import importlib.util
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile
from concurrent.futures import ThreadPoolExecutor

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

    def reanalyze(self,report):
        recorded=audit._recorded_functions(report['environment']['python'])
        report['analysis']=recorded['finish_analysis'](report['records'],report['protocol'],report['simple_baselines'])

    def test_recorded_arithmetic_matches_all_original_means_grades_and_analysis(self):
        with zipfile.ZipFile(io.BytesIO(self.raw)) as z:
            report=json.loads(z.read('RESULTS-V0.3.json'))
            events=[json.loads(row) for row in z.read('RESULTS-V0.3.json.journal.jsonl').splitlines()]
        recorded=audit._recorded_functions(report['environment']['python'])
        original=copy.deepcopy(report['analysis'])
        self.reanalyze(report)
        self.assertEqual(m.canonical(report['analysis']),m.canonical(original))
        changed=0
        means=0
        for event in events:
            if event['event']!='selection_locked':
                continue
            for family in report['protocol']['comparison']:
                values=[r['validation_metrics']['accuracy'] for r in report['records']
                        if all(r[k]==event[k] for k in ('dataset','scale','steps')) and r['family']==family]
                expected=event['average_validation_accuracies'][family]
                self.assertEqual((recorded['sum'](values)/len(values)).hex(),expected.hex())
                changed+=audit._left_sum(values)/len(values)!=expected
                means+=1
        self.assertEqual((means,changed),(32,4))
        outcomes=report['records']+[r for values in report['simple_baselines'].values() for r in values.values()]
        grades=0
        for outcome in outcomes:
            for split in ('validation','test'):
                metric=outcome[split+'_metrics']
                recall=recorded['sum'](v['correct']/v['count'] for v in metric['per_class'].values())/len(metric['per_class'])
                self.assertEqual(recall.hex(),metric['macro_recall'].hex())
                grades+=1
        self.assertEqual(grades,204)

    def test_recorded_float_sum_preserves_integer_branch_and_cancellation(self):
        vectors=[([float(2**53),1.,1.],float(2**53+2)),
                 ([float(2**53),1,1],float(2**53)),
                 ([float(2**53),1.,1,1.],float(2**53+2)),
                 ([2**63,1024.,1024.],float(2**63)),
                 ([1.,2**63,1024.,1024.],float(2**63)),
                 ([1e16,1.,-1e16],1.),([2**100,1,-2**100],1)]
        for values,expected in vectors:
            with self.subTest(values=values):
                actual=audit._sum313(values)
                self.assertEqual(m.canonical(actual),m.canonical(expected))
        self.assertEqual(audit._recorded_functions('3.11.17')['sum']([1e16,1.,-1e16]),0.)

    def test_recorded_function_namespaces_are_isolated_from_frozen_module(self):
        _,report,_=self.rewrite_archive(lambda report,members:None)
        originals={name:getattr(m,name) for name in ('grade','finish_analysis','verify')}
        previous_sum=vars(m).get('sum')
        def compute(version):
            functions=audit._recorded_functions(version)
            return functions['finish_analysis'](report['records'],report['protocol'],report['simple_baselines'])
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(compute,['3.13.5','3.11.17']*4))
        for i,result in enumerate(results):
            expected=report['analysis'] if i%2==0 else compute('3.11.17')
            self.assertEqual(m.canonical(result),m.canonical(expected))
        self.assertTrue(all(getattr(m,name) is original for name,original in originals.items()))
        self.assertIs(vars(m).get('sum'),previous_sum)

    def test_one_ulp_selection_mean_forgery_is_rejected_without_tolerance(self):
        def change(report,members):
            def change_events(events):
                event=next(e for e in events if e['event']=='selection_locked')
                value=event['average_validation_accuracies']['conv']
                event['average_validation_accuracies']['conv']=math.nextafter(value,math.inf)
            self.update_journal(report,members,change_events)
        self.assert_rejected_at_current_boundaries(change,'validation selection evidence mismatch')

    @unittest.skipUnless(importlib.util.find_spec('sklearn') and importlib.util.find_spec('torch'),
                         'optional scikit-learn/PyTorch missing; exact analysis regrading not executed')
    def test_one_ulp_derived_cost_mean_forgery_is_rejected_without_tolerance(self):
        def change(report,members):
            comparison=report['analysis']['digits/width-48/steps-80']['comparison']['conv']
            comparison['time_seconds_mean']=math.nextafter(comparison['time_seconds_mean'],math.inf)
        self.assert_rejected_at_current_boundaries(change,'selection/metric analysis mismatch')

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
        return self.pack_members(members),report,members

    def pack_members(self,members):
        members['manifest.json']=m.canonical({name:m.sha(members[name]) for name in audit.REQUIRED})+b'\n'
        out=io.BytesIO()
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
            for name,data in members.items():
                z.writestr(name,data)
        return out.getvalue()

    def assert_rejected_at_current_boundaries(self,change,pattern='.'):
        raw,report,members=self.rewrite_archive(change)
        with self.subTest(boundary='archive'),self.assertRaisesRegex(ValueError,pattern):
            audit.parse_archive(raw)
        with self.subTest(boundary='standalone'),self.assertRaisesRegex(ValueError,pattern):
            audit.verify_report(report,members['RESULTS-V0.3.json.journal.jsonl'])

    def update_journal(self,report,members,change):
        events=[json.loads(row) for row in members['RESULTS-V0.3.json.journal.jsonl'].splitlines()]
        change(events)
        journal=b''.join(m.canonical(e)+b'\n' for e in events)
        members['RESULTS-V0.3.json.journal.jsonl']=journal
        report['journal_sha256']=m.sha(journal)

    def test_dataset_and_cohort_matrix_cannot_omit_or_recount_cases(self):
        for operation in ('missing_dataset','extra_dataset','missing_comparator_dataset',
                          'missing_cohort','recount_cohort','truncate_control','truncate_neural'):
            def change(report,members):
                if operation=='missing_dataset':
                    report['datasets'].pop('digits')
                elif operation=='extra_dataset':
                    report['datasets']['substituted']=copy.deepcopy(report['datasets']['digits'])
                elif operation=='missing_comparator_dataset':
                    report['simple_baselines'].pop('digits')
                elif operation=='missing_cohort':
                    report['datasets']['digits']['split_indices'].pop('validation')
                elif operation=='recount_cohort':
                    report['datasets']['digits']['split_sizes']['validation']-=1
                elif operation=='truncate_control':
                    report['simple_baselines']['digits']['knn5']['test_predictions'].pop()
                else:
                    report['records'][0]['validation_predictions'].pop()
            with self.subTest(operation=operation):
                self.assert_rejected_at_current_boundaries(change)

    def test_neural_exposure_and_journal_stage_matrices_are_complete(self):
        for operation in ('omit_trial','duplicate_trial','relabel_trial','omit_train_start',
                          'duplicate_training','alter_train_spec','alter_selection','recount_completion','omit_control'):
            def change(report,members):
                if operation=='omit_trial':
                    report['records'].pop()
                elif operation=='duplicate_trial':
                    report['records'][-1]=copy.deepcopy(report['records'][0])
                elif operation=='relabel_trial':
                    report['records'][0]['seed']=523
                else:
                    def change_events(events):
                        start=next(e for e in events if e['event']=='train_started')
                        if operation=='omit_train_start':
                            events.remove(start)
                        elif operation=='duplicate_training':
                            events.insert(-1,copy.deepcopy(next(e for e in events if e['event']=='training_completed')))
                        elif operation=='alter_train_spec':
                            start['spec']['width']+=1
                        elif operation=='alter_selection':
                            next(e for e in events if e['event']=='selection_locked')['average_validation_accuracies']['conv']=1.
                        elif operation=='recount_completion':
                            events[-1]['records']=95
                        else:
                            events.remove(next(e for e in events if e['event']=='simple_baselines_completed'))
                    self.update_journal(report,members,change_events)
            with self.subTest(operation=operation):
                self.assert_rejected_at_current_boundaries(change)

    @unittest.skipUnless(importlib.util.find_spec('sklearn') and importlib.util.find_spec('torch'),
                         'optional scikit-learn/PyTorch missing; actual prediction regrading not executed')
    def test_coordinated_control_prediction_and_score_forgeries_fail_real_regrading(self):
        for operation in ('prediction','score','swap_equal_sized_cohorts'):
            def change(report,members):
                name='breast_cancer' if operation=='swap_equal_sized_cohorts' else 'digits'
                control=report['simple_baselines'][name]['logistic_regression']
                if operation=='prediction':
                    _,data=m.read_dataset(name,report['protocol']['split_seed'])
                    truth=data['test'][1].tolist()
                    i=next(i for i,pred in enumerate(control['test_predictions']) if pred==truth[i])
                    control['test_predictions'][i]=(truth[i]+1)%10
                elif operation=='score':
                    control['test_metrics']['accuracy']=0. if control['test_metrics']['accuracy']==1. else 1.
                else:
                    self.assertEqual(len(control['test_predictions']),len(control['validation_predictions']))
                    self.assertNotEqual(control['test_predictions'],control['validation_predictions'])
                    for suffix in ('predictions','metrics'):
                        a,b='test_'+suffix,'validation_'+suffix
                        control[a],control[b]=control[b],control[a]
                self.reanalyze(report)
                def change_events(events):
                    next(e for e in events if e['event']=='simple_baselines_completed' and e['dataset']==name)['results']=copy.deepcopy(report['simple_baselines'][name])
                self.update_journal(report,members,change_events)
            with self.subTest(operation=operation):
                self.assert_rejected_at_current_boundaries(change,'incorrect simple comparator score')

    def test_duplicate_json_fields_cannot_hide_comparator_or_journal_substitution(self):
        _,_,members=self.rewrite_archive(lambda report,members:None)
        members['RESULTS-V0.3.json']=members['RESULTS-V0.3.json'].replace(b'"simple_baselines":',b'"simple_baselines":{},"simple_baselines":',1)
        with self.assertRaisesRegex(ValueError,'duplicate JSON key'):
            audit.parse_archive(self.pack_members(members))
        def change(report,members):
            journal=members['RESULTS-V0.3.json.journal.jsonl'].replace(b'"results":',b'"results":{},"results":',1)
            members['RESULTS-V0.3.json.journal.jsonl']=journal
            report['journal_sha256']=m.sha(journal)
        raw,report,members=self.rewrite_archive(change)
        with self.assertRaisesRegex(ValueError,'duplicate JSON key'):
            audit.parse_archive(raw)
        with self.assertRaisesRegex(ValueError,'duplicate JSON key'):
            audit.verify_report(report,members['RESULTS-V0.3.json.journal.jsonl'])

    def test_current_verification_requires_the_execution_journal(self):
        _,report,_=self.rewrite_archive(lambda report,members:None)
        with self.assertRaisesRegex(ValueError,'requires the original execution journal'):
            audit.verify_report(report)

    def duration_mutation(self,kind,value):
        def change(report,members):
            if kind=='neural':
                record=report['records'][0]
                record['train_seconds']=value
                key=tuple(record[k] for k in audit.TRIAL_FIELDS)
                def change_events(events):
                    for event in events:
                        if event['event'] in ('training_completed','test_completed'):
                            row=event['record_without_test' if event['event']=='training_completed' else 'record']
                            if tuple(row[k] for k in audit.TRIAL_FIELDS)==key:
                                row['train_seconds']=value
            else:
                report['simple_baselines']['digits']['knn5']['training_seconds']=value
                def change_events(events):
                    next(e for e in events if e['event']=='simple_baselines_completed' and e['dataset']=='digits')['results']=copy.deepcopy(report['simple_baselines']['digits'])
            self.update_journal(report,members,change_events)
            self.reanalyze(report)
        return change

    def test_coherently_resigned_negative_and_boolean_durations_are_rejected(self):
        for kind in ('neural','reference'):
            for value in (-100 if kind=='neural' else -10,True,False):
                with self.subTest(kind=kind,value=value):
                    self.assert_rejected_at_current_boundaries(self.duration_mutation(kind,value),'duration')

    def test_duration_domain_rejects_wrong_types_and_nonfinite_api_values(self):
        for kind in ('neural','reference'):
            for value in ('1.0',None,[],float('nan'),float('inf'),-float('inf')):
                _,report,members=self.rewrite_archive(lambda report,members:None)
                if kind=='neural':
                    report['records'][0]['train_seconds']=value
                else:
                    report['simple_baselines']['digits']['knn5']['training_seconds']=value
                # Nonfinite numbers cannot be canonically signed. Require the domain
                # rejection itself, before checksum or journal-disagreement rejection.
                with self.subTest(kind=kind,value=repr(value)),self.assertRaisesRegex(ValueError,'duration'):
                    audit.verify_report(report,members['RESULTS-V0.3.json.journal.jsonl'])

    @unittest.skipUnless(importlib.util.find_spec('sklearn') and importlib.util.find_spec('torch'),
                         'optional scikit-learn/PyTorch missing; valid zero-duration score reconstruction not executed')
    def test_zero_integer_and_float_durations_remain_valid(self):
        for kind in ('neural','reference'):
            for value in (0,0.):
                raw,report,members=self.rewrite_archive(self.duration_mutation(kind,value))
                with self.subTest(kind=kind,value=repr(value)):
                    audit.verify_report(report,members['RESULTS-V0.3.json.journal.jsonl'])
                    self.assertFalse(audit.parse_archive(raw)['primary_pass'])

    def test_registered_references_cannot_be_omitted_or_relabelled(self):
        for operation in ('keep_only_knn5','replace_logistic_with_knn5'):
            def change(report,members):
                for values in report['simple_baselines'].values():
                    if operation=='keep_only_knn5':
                        values.pop('logistic_regression');values.pop('rbf_svm')
                    else:
                        values['logistic_regression']=copy.deepcopy(values['knn5'])
                self.reanalyze(report)
            raw,report,members=self.rewrite_archive(change)
            if operation=='keep_only_knn5':
                self.assertTrue(report['analysis']['primary_screen']['by_dataset']['breast_cancer']['passes_internal_screen'])
            for boundary in ('archive','standalone'):
                with self.subTest(operation=operation,boundary=boundary),self.assertRaisesRegex(ValueError,'comparator|baseline'):
                    if boundary=='archive':
                        audit.parse_archive(raw)
                    else:
                        audit.verify_report(report,members['RESULTS-V0.3.json.journal.jsonl'])

    def test_baseline_journal_results_cannot_be_changed_or_duplicated(self):
        for operation in ('alter_results','duplicate_event'):
            def change(report,members):
                events=[json.loads(row) for row in members['RESULTS-V0.3.json.journal.jsonl'].splitlines()]
                event=next(e for e in events if e['event']=='simple_baselines_completed')
                if operation=='alter_results':
                    event['results']['knn5']['training_seconds']+=1
                else:
                    events.insert(-1,copy.deepcopy(event))
                journal=b''.join(m.canonical(e)+b'\n' for e in events)
                members['RESULTS-V0.3.json.journal.jsonl']=journal
                report['journal_sha256']=m.sha(journal)
            raw,report,members=self.rewrite_archive(change)
            for boundary in ('archive','standalone'):
                with self.subTest(operation=operation,boundary=boundary),self.assertRaisesRegex(ValueError,'baseline|control'):
                    if boundary=='archive':
                        audit.parse_archive(raw)
                    else:
                        audit.verify_report(report,members['RESULTS-V0.3.json.journal.jsonl'])

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
            journal=z.read('RESULTS-V0.3.json.journal.jsonl')
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
                audit.verify_report(changed,journal)

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
