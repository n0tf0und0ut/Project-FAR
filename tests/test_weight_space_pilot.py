"""Offline fixtures exercise infrastructure only; no model-performance evidence."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import tempfile
import unittest
from tools import weight_space_pilot as pilot
from tools.weight_space_grading import grade, repeated_suffix
from tools.weight_space_replay import independent_grade, summarize, replay


class ProtocolTests(unittest.TestCase):
    def test_frozen_schedule_complete_and_unique(self):
        p,t=pilot.load_protocol(pilot.DEFAULT)
        plan=pilot.schedule(p,t)
        self.assertEqual(len(plan),432)
        self.assertEqual(len(set(plan)),432)
        self.assertEqual(len([x for x in t if x['split']=='development']),6)
        self.assertEqual(len([x for x in t if x['split']=='heldout']),12)
        self.assertTrue(all(not x[0].startswith('D') for x in plan))
        self.assertEqual(plan,pilot.schedule(p,t))

    def test_duplicate_json_and_nonfinite_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'x.json'
            for text in ['{"a":1,"a":2}','{"a":NaN}']:
                file.write_text(text)
                with self.assertRaises(ValueError): pilot.read(file)

    def test_oracle_and_tasks_hash_drift_rejected(self):
        p,t=pilot.load_protocol(pilot.DEFAULT)
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'protocol.json'
            p['tasks']['sha256']='0'*64
            file.write_text(json.dumps(p))
            with self.assertRaisesRegex(ValueError,'task drift'):pilot.load_protocol(file)

    def test_evidence_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'evidence.json'
            pilot.write(file,{'raw':'first'})
            with self.assertRaises(FileExistsError):pilot.write(file,{'raw':'changed'})
            self.assertEqual(pilot.read(file),{'raw':'first'})

    def test_all_grades_independently_agree_and_mutations_fail(self):
        p,t=pilot.load_protocol(pilot.DEFAULT)
        for task in t:
            good=json.dumps(task['gold']) if task['grader']=='json' else task['gold']
            for text in [good,'wrong','',good+' irrelevant text','{"done":1}','{"ready":true,"ready":true}']:
                a=grade(task,text,[1,2,3],False)
                b=independent_grade(task,text,[1,2,3],False)
                self.assertEqual(a,b)
                if text==good:self.assertTrue(a['correct'])
            if task['grader']=='json' and 'true' in good:
                self.assertFalse(grade(task,good.replace('true','1'),[],False)['correct'])

    def test_repetition_proxy_is_explicit_and_bounded(self):
        self.assertTrue(repeated_suffix([3,4,3,4,3,4]))
        self.assertFalse(repeated_suffix([3,4,3,4]))
        self.assertFalse(repeated_suffix([1,2,3,4,5,6]))

    def test_incomplete_and_simulated_never_reported_as_performance(self):
        p,t=pilot.load_protocol(pilot.DEFAULT)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            registration={'observations':'SYNTHETIC_TEST'}
            pilot.write(root/'registration.json',registration)
            with self.assertRaisesRegex(ValueError,'synthetic'):replay(pilot.DEFAULT,root)

    def test_checkpoint_symlink_or_wrong_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'config.json').write_bytes(b'123')
            manifest={'files':[{'name':'config.json','size':3,'sha256':pilot.sha(b'123')}]}
            pilot.verify_checkpoint(root,manifest)
            (root/'config.json').write_bytes(b'321')
            with self.assertRaisesRegex(ValueError,'mismatch'):pilot.verify_checkpoint(root,manifest)
            manifest['files'][0]['name']='../outside'
            with self.assertRaisesRegex(ValueError,'path'):pilot.verify_checkpoint(root,manifest)

    def test_checkpoint_rejects_unmanifested_loader_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'config.json').write_bytes(b'123')
            manifest={'files':[{'name':'config.json','size':3,'sha256':pilot.sha(b'123')}]}
            for name in ['chat_template.jinja','tokenizer.model','extra-config.json']:
                with self.subTest(name=name):
                    extra=root/name;extra.write_text('unregistered override')
                    with self.assertRaisesRegex(ValueError,'unmanifested'):
                        pilot.verify_checkpoint(root,manifest)
                    extra.unlink()

    def test_checkpoint_rejects_extra_directory_and_root_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'model';root.mkdir()
            (root/'config.json').write_bytes(b'123')
            manifest={'files':[{'name':'config.json','size':3,'sha256':pilot.sha(b'123')}]}
            extra=root/'extra';extra.mkdir()
            with self.assertRaisesRegex(ValueError,'unmanifested'):pilot.verify_checkpoint(root,manifest)
            extra.rmdir()
            alias=Path(tmp)/'alias';alias.symlink_to(root,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'directory'):pilot.verify_checkpoint(alias,manifest)

    def test_adoption_cannot_be_inferred_from_perfect_fixture(self):
        p,t=pilot.load_protocol(pilot.DEFAULT)
        rows=[]
        for task_id,seed,arm in pilot.schedule(p,t):
            task=next(task for task in t if task['id']==task_id)
            text=json.dumps(task['gold']) if task['grader']=='json' else task['gold']
            rows.append(dict(task_id=task_id,seed=seed,arm=arm,
                grade=grade(task,text,[1],False),input_tokens=1,output_tokens=1,
                elapsed_seconds=1.0,cpu_seconds=1.0,hit_token_limit=False))
        result=summarize(p,t,rows)
        self.assertFalse(result['production_eligible'])
        self.assertFalse(result['screen']['minimum_gain_met'])
        self.assertEqual(result['general_agent_reliability'],'NOT_ESTABLISHED')
        self.assertTrue(all(a['correct']==54 for a in result['arms'].values()))

if __name__=='__main__': unittest.main()

class ReplayTrustBoundaryTests(unittest.TestCase):
    def test_actual_token_ids_must_decode_to_graded_text(self):
        from tools.weight_space_replay import validate_token_trace
        class Tokenizer:
            eos_token_id=2
            def apply_chat_template(self,*a,**k): return [1,4]
            def decode(self,tokens,**k): return '' if tokens==[2] else 'wrong'
        row={'request':{'messages':[{'role':'user','content':'x'}],'input_ids':[1,4],
                        'generation':{'max_new_tokens':64}},'output_ids':[2],
             'text':'fabricated correct answer','hit_token_limit':False}
        with self.assertRaisesRegex(ValueError,'decoded output'):validate_token_trace(row,Tokenizer())
        row['text']='';row['request']['input_ids']=[1]
        with self.assertRaisesRegex(ValueError,'tokenized request'):validate_token_trace(row,Tokenizer())
        row['request']['input_ids']=[1,4];row['hit_token_limit']=True
        with self.assertRaisesRegex(ValueError,'token-limit'):validate_token_trace(row,Tokenizer())

    def test_new_untracked_source_cannot_pass_freeze(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            import subprocess
            subprocess.run(['git','init','-q',str(root)],check=True)
            (root/'new.py').write_text('uncommitted')
            with patch.object(pilot,'ROOT',root):
                with self.assertRaisesRegex(ValueError,'not committed'):
                    pilot.verify_source_committed({'new.py':pilot.sha(b'uncommitted')})

    def test_failure_in_early_phase_has_durable_receipt(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'attempt'
            with patch.object(pilot,'_run',side_effect=ValueError('checkpoint mismatch')):
                with self.assertRaisesRegex(ValueError,'checkpoint mismatch'):
                    pilot.run(pilot.DEFAULT,Path('/not-used'),output)
            self.assertTrue((output/'attempt.json').exists())
            self.assertEqual(pilot.read(output/'failure-attempt.json')['error_type'],'ValueError')
            with self.assertRaisesRegex(ValueError,'overwrite'):
                pilot.run(pilot.DEFAULT,Path('/not-used'),output)
