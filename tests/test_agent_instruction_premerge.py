"""Offline checks for the preregistered Ponytail instruction comparison."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools import agent_instruction_premerge as b


class ContractTests(unittest.TestCase):
    def test_prereg_contract_and_frozen_corpus(self):
        protocol,tasks,schedule=b.load_contract()
        self.assertEqual(protocol['status'],'PREREGISTERED_NOT_EXECUTED')
        self.assertEqual(len(tasks),10)
        self.assertEqual(len(schedule['slots']),40)
        self.assertEqual(len({t['id'] for t in tasks}),10)
        self.assertEqual(len({s['slot_id'] for s in schedule['slots']}),40)
        self.assertEqual(sum(s['arm']=='control' for s in schedule['slots'][::2]),10)
        self.assertEqual(sum(s['arm']=='treatment' for s in schedule['slots'][::2]),10)
        for task in tasks:
            self.assertEqual(len(task['public']),2)
            self.assertEqual(len(task['hidden']),4)
            for repeat in (1,2):
                cells=[s for s in schedule['slots'] if s['task_id']==task['id'] and s['repetition']==repeat]
                self.assertEqual({s['arm'] for s in cells},{'control','treatment'})

    def test_corpus_change_invalidates_freeze(self):
        corpus=b.TASKS.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'tasks.json'
            p.write_bytes(corpus+b' ')
            with patch.object(b,'TASKS',p),self.assertRaisesRegex(b.ContractError,'digest'):
                b.load_contract()

    def test_schedule_mutation_invalidates_freeze(self):
        o=json.loads(b.SCHEDULE.read_bytes())
        o['slots'][0]['arm']='treatment' if o['slots'][0]['arm']=='control' else 'control'
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'schedule.json'
            p.write_text(json.dumps(o))
            with patch.object(b,'SCHEDULE',p),self.assertRaisesRegex(b.ContractError,'schedule'):
                b.load_contract()

    def test_reject_ambiguous_json_and_untrusted_path(self):
        for payload in ('{"a":1,"a":2}','{"a":NaN}','{"a":Infinity}'):
            with self.subTest(payload=payload),self.assertRaises(b.ContractError):
                b.strict_load(payload)
        for path in ('../escape','/abs','a\\b','','a//b','a/./b','a/../b'):
            with self.subTest(path=path),self.assertRaises(b.ContractError):
                b.safe_path(path)

    def test_baseline_fails_at_least_one_case_in_each_task(self):
        _,tasks,_=b.load_contract()
        for task in tasks:
            failures=0
            with tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                for name,content in task['files'].items():
                    (root/name).write_text(content)
                for case in task['public']+task['hidden']:
                    if failures:
                        break
                    raw=subprocess.run([sys.executable,'-I','-B','-c',
                            "import json,sys,runpy;sys.path.insert(0,sys.argv[1]);f=runpy.run_path(sys.argv[1]+'/solution.py')['transform']; print(json.dumps(f(json.loads(sys.argv[2])),allow_nan=False))",
                            str(root),json.dumps(case['input'])],text=True,capture_output=True,timeout=3)
                    try:
                        actual=json.loads(raw.stdout)
                        if raw.returncode or b.canonical(actual)!=b.canonical(case['expected']):failures+=1
                    except ValueError:failures+=1
            self.assertGreater(failures,0,task['id']+' contains no baseline defect')

    def test_output_parser_rejects_forged_partial_success(self):
        expected=b.START+'\n{"ok":true}\n'+b.FINISH+'\n'
        self.assertEqual(b._strict_json_output(expected),{'ok':True})
        for invalid in (expected.removesuffix('\n'+b.FINISH+'\n'),
                        b.START+'\n{"ok":true,"ok":false}\n'+b.FINISH+'\n',
                        'Ran tests: OK\n'+expected):
            with self.subTest(invalid=invalid),self.assertRaises((b.ContractError,ValueError)):
                b._strict_json_output(invalid)

    def test_no_results_cannot_be_reported_as_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=b.analyze(Path(tmp))
        self.assertEqual(report['decision'],'NOT_EXECUTED')
        self.assertEqual(report['valid_slots'],0)
        self.assertEqual(report['required_slots'],40)

    def test_analyzer_rejects_forged_passing_grader_output(self):
        _,tasks,schedule=b.load_contract()
        cell=schedule['slots'][0]
        case=next(t for t in tasks if t['id']==cell['task_id'])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'evidence').mkdir()
            evidence=root/'evidence'/cell['slot_id']
            evidence.mkdir()
            (evidence/'agent-events.ndjson').write_text('{"type":"turn.completed"}\n')
            stdout=b.START+'\nnull\n'+b.FINISH+'\n'
            compares=[{'status':'PASS','stdout':stdout,'stderr':'',
                       'stdout_sha256':b.digest(stdout.encode()),'stderr_sha256':b.digest(b''),
                       'exit_code':0,'timed_out':False,'output_limited':False} for _ in range(6)]
            source_sha={}
            for name,src in case['files'].items():
                (evidence/name).write_text(src)
                source_sha[name]=b.digest(src.encode())
            manifest={'slots':[{**cell,'instructions_sha256':'a'*64,'source_sha256':source_sha,
                                'prompt_sha256':'b'*64}]}
            (root/'prepared-manifest.json').write_text(json.dumps(manifest))
            rec={**cell,'schema':'far-agent-instruction-observation/1',
                 'graded':True,'outcome':'SUCCESS','unauthorized':[],
                 'comparisons':compares,'raw_event_sha256':b.digest((evidence/'agent-events.ndjson').read_bytes()),
                 'instruction_sha256':'a'*64,'sources_sha256':source_sha,'changed_files':[],
                 'execution_exit_code':0,'execution_timed_out':False}
            (root/'evidence'/(cell['slot_id']+'.json')).write_text(json.dumps(rec))
            r=b.analyze(root)
        self.assertEqual(r['decision'],'INVALID_EVIDENCE')
        self.assertTrue(any('INVALID:'+cell['slot_id'] in e for e in r['errors']))

    def test_missing_git_history_fails_before_workspace_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'workspaces'
            with patch.object(b,'pinned_instructions',side_effect=b.ContractError('missing pinned object')):
                with self.assertRaisesRegex(b.ContractError,'missing pinned object'):
                    b.prepare(out)
            self.assertFalse(out.exists())

    def test_unsupported_agent_command_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(b.ContractError,'unavailable'):
                b.run_slot(Path(tmp),b.load_contract()[2]['slots'][0]['slot_id'],
                           '/unavailable/nonexistent --model gpt-6')

    def test_infrastructure_failure_not_a_model_failure(self):
        # Never infer Docker absence from the executing host: CI has Docker.
        # Inject a real transport-launch error independently of host capability.
        _,tasks,_=b.load_contract()
        cleanup=subprocess.CompletedProcess(args=['docker','rm'],returncode=0,
                                            stdout='',stderr='')
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(b,'capture_candidate_process',
                             side_effect=OSError('docker transport unavailable')) as invoke, \
                patch.object(b.subprocess,'run',return_value=cleanup) as cleanup_run:
            result=b._grade_case(Path(tmp),tasks[0]['public'][0])
        invoke.assert_called_once()
        cleanup_run.assert_called_once()
        self.assertEqual(result['status'],'INFRA_FAILURE')
        self.assertEqual(result['error'],'OSError')

    def test_candidate_did_not_start_is_infrastructure_failure(self):
        _,tasks,_=b.load_contract()
        evidence={'stdout':'','stderr':'docker: image pull denied',
                  'stdout_bytes_observed':0,'stderr_bytes_observed':25,
                  'exit_code':125,'timed_out':False,'output_limited':False}
        cleanup=subprocess.CompletedProcess(args=['docker','rm'],returncode=0,
                                            stdout='',stderr='')
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(b,'capture_candidate_process',return_value=evidence), \
                patch.object(b.subprocess,'run',return_value=cleanup):
            result=b._grade_case(Path(tmp),tasks[0]['public'][0])
        self.assertEqual(result['status'],'INFRA_FAILURE')

if __name__=='__main__': unittest.main()
