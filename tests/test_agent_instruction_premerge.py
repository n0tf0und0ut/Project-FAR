"""Offline checks for the preregistered Ponytail instruction comparison."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import shlex
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
        expected=b.START+'\n{"value":{"ok":true},"input_unchanged":true}\n'+b.FINISH+'\n'
        self.assertEqual(b._strict_json_output(expected),{'value':{'ok':True},'input_unchanged':True})
        for invalid in (expected.removesuffix('\n'+b.FINISH+'\n'),
                        b.START+'\n{"value":{},"value":{},"input_unchanged":true}\n'+b.FINISH+'\n',
                        b.START+'\n{"value":{},"input_unchanged":"yes"}\n'+b.FINISH+'\n',
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
        self.assertTrue(r['errors'])

    def test_missing_git_history_fails_before_workspace_creation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'workspaces'
            with patch.object(b,'pinned_instructions',side_effect=b.ContractError('missing pinned object')):
                with self.assertRaisesRegex(b.ContractError,'missing pinned object'):
                    b.prepare(out)
            self.assertFalse(out.exists())

    def test_unsupported_agent_command_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises((b.ContractError,FileNotFoundError)):
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

    def test_direct_script_entry_point(self):
        # This is the documented invocation, not merely an import from tests.
        cmd=[sys.executable,str(b.ROOT/'tools/agent_instruction_premerge.py'),'validate']
        result=subprocess.run(cmd,cwd=b.ROOT,capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['slots'],40)

    def test_versioned_codex_event_stream_required(self):
        good=(b'{"type":"thread.started","thread_id":"session-1"}\n'
              b'{"type":"turn.started"}\n'
              b'{"type":"turn.completed","usage":{"input_tokens":10,"output_tokens":2}}\n')
        self.assertEqual(b._parse_agent_trace(good)['thread_id'],'session-1')
        invalid=(b'{"type":"turn.completed"}\n',
                 b'{"type":"thread.started","thread_id":"a"}\n'
                 b'{"type":"turn.started"}\n'
                 b'{"type":"turn.failed"}\n',
                 good[:-1],
                 good+b'{"type":"turn.completed","usage":{"input_tokens":9,"output_tokens":9}}\n')
        for value in invalid:
            with self.subTest(payload=value),self.assertRaises(b.ContractError):
                b._parse_agent_trace(value)

    def test_candidate_mutation_is_detected_by_trusted_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            script=Path(tmp)/'solution.py'
            script.write_text('def transform(d):\n    d["record"] = {"changed": True}\n    return 42\n')
            source=b.ENTRYPOINT.replace('/app/solution.py',str(script))
            res=subprocess.run([sys.executable,'-I','-B','-c',source],input='{"record":{"changed":false}}',
                               text=True,capture_output=True,timeout=5)
            self.assertEqual(res.returncode,0,res.stderr)
            out=b._strict_json_output(res.stdout)
            self.assertEqual(out['value'],42)
            self.assertFalse(out['input_unchanged'])

    def test_committed_unauthorized_edits_are_detected_from_baseline(self):
        task=next(t for t in b.load_contract()[1] if t['id']=='REUSE-06')
        with tempfile.TemporaryDirectory() as tmp:
            ws=Path(tmp)
            for n,contents in task['files'].items():(ws/n).write_text(contents)
            (ws/'AGENTS.md').write_text('pinned guidance')
            (ws/'README.md').write_text('task')
            (ws/'.gitignore').write_text('ignored')
            expected={n:b.digest(f.read_bytes()) for n in [*task['files'],'AGENTS.md','README.md','.gitignore']
                      for f in [ws/n]}
            subprocess.run(['git','init','-q'],cwd=ws,check=True)
            subprocess.run(['git','add','.'],cwd=ws,check=True)
            subprocess.run(['git','-c','user.name=Test','-c','user.email=test@example.invalid',
                            'commit','-qm','baseline'],cwd=ws,check=True)
            (ws/'shared.py').write_text(task['files']['shared.py']+'\n# unauthorized\n')
            (ws/'catalog.py').write_text(task['files']['catalog.py']+'\n# allowed edit\n')
            subprocess.run(['git','add','.'],cwd=ws,check=True)
            subprocess.run(['git','-c','user.name=Test','-c','user.email=test@example.invalid',
                            'commit','-qm','candidate changed HEAD'],cwd=ws,check=True)
            actual,violations,edits=b._workspace_snapshot(ws,{'initial_files_sha256':expected},task)
            self.assertIn('UNAUTHORIZED_EDIT:shared.py',violations)
            self.assertIn('catalog.py',edits)

    def test_unknown_file_and_changed_instructions_fail_source_integrity(self):
        _,tasks,_=b.load_contract();task=tasks[0]
        with tempfile.TemporaryDirectory() as tmp:
            ws=Path(tmp)
            for name,text in task['files'].items():(ws/name).write_text(text)
            (ws/'AGENTS.md').write_text('frozen instructions')
            (ws/'README.md').write_text('frozen prompt')
            (ws/'.gitignore').write_text('ignore')
            expected={p.name:b.digest(p.read_bytes()) for p in ws.iterdir()}
            (ws/'AGENTS.md').write_text('modified instructions')
            (ws/'secret.py').write_text('print(123)')
            source,bad,_=b._workspace_snapshot(ws,{'initial_files_sha256':expected},task)
            self.assertIn('UNAUTHORIZED_EDIT:AGENTS.md',bad)
            self.assertIn('NEW_FILE:secret.py',bad)
            self.assertIn('secret.py',source)
            replay,changes=b._classify_sources(source,expected,set(task['allowed_changes']))
            self.assertEqual(bad,replay)

    def test_scoring_freeze_prevents_post_exposure_policy_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            frozen=b.freeze_identity()
            (root/'prepared-manifest.json').write_text(json.dumps({'schema':'far-agent-instruction-prepared/2',
                  'freeze':frozen,'schedule_sha256':b.digest(b.canonical(b.load_contract()[2])),
                  'slots':b.load_contract()[2]['slots']}))
            protocol=json.loads(b.PROTOCOL.read_text())
            protocol['scoring']['guard_categories']=[]
            alt=root/'protocol.json';alt.write_text(json.dumps(protocol))
            with patch.object(b,'PROTOCOL',alt),self.assertRaisesRegex(b.ContractError,'freeze'):
                b.validate_prepared(root)

    def test_grade_snapshot_not_live_source(self):
        # A background candidate can mutate its workspace while grading occurs.
        # Grade source must instead be the controller-owned captured snapshot.
        original=b._grade_case
        _,tasks,schedule=b.load_contract()
        task=tasks[0];cell=schedule['slots'][0]
        initial=b'original AGENTS instructions\n'
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);ws=root/'workspaces'/cell['slot_id'];ws.mkdir(parents=True)
            for n,src in task['files'].items():(ws/n).write_text(src)
            (ws/'AGENTS.md').write_bytes(initial)
            (ws/'README.md').write_text('prompt')
            (ws/'.gitignore').write_text('ignore')
            filehash={p.name:b.digest(p.read_bytes()) for p in ws.iterdir()}
            (ws/'solution.py').write_text('def transform(d): return 3\n')
            manifest={'freeze':b.freeze_identity(),'slots':[{**cell,'initial_files_sha256':filehash,
                     'instructions_sha256':b.digest(initial)}]}
            (root/'evidence'/cell['slot_id']).mkdir(parents=True)
            provider={'runtime':{'schema':'far-codex-runtime/1'},'stdout_sha256':'f'*64,
                      'stderr_sha256':'e'*64,'stdout_bytes_observed':2,'stderr_bytes_observed':0,
                      'exit_code':0,'timed_out':False,'output_limited':False,
                      'validated_trace':{'thread_id':'a'},'previous_observation_sha256':None}
            used=[]
            def fake_grade(snapshot,case):
                used.append(snapshot)
                self.assertTrue(str(snapshot).endswith('/submitted'))
                self.assertEqual((snapshot/'solution.py').read_text(),'def transform(d): return 3\n')
                (ws/'solution.py').write_text('def transform(d): return -99\n')
                return {'status':'FAILURE'}
            with patch.object(b,'validate_prepared',return_value=manifest), \
                 patch.object(b,'pinned_instructions',return_value=initial), \
                 patch.object(b,'_grade_case',side_effect=fake_grade):
                r=b.grade_slot(root,cell['slot_id'],provider)
            self.assertEqual(len(used),6)
            self.assertEqual(r['outcome'],'FAILURE')
            self.assertEqual((root/'evidence'/cell['slot_id']/'submitted'/'solution.py').read_text(),
                             'def transform(d): return 3\n')

    def test_grader_cleanup_failure_retains_original_receipt(self):
        _,tasks,_=b.load_contract()
        receipt={'stdout':b.START+'\n{"value":1,"input_unchanged":true}\n'+b.FINISH+'\n',
                 'stderr':'candidate stderr','exit_code':0,'timed_out':False,
                 'output_limited':False,'stdout_bytes_observed':10,'stderr_bytes_observed':16}
        cleanup=subprocess.CompletedProcess(args=['docker','rm'],returncode=125,
                                            stdout='',stderr='cleanup refused')
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(b,'capture_candidate_process',return_value=receipt), \
             patch.object(b.subprocess,'run',return_value=cleanup):
            r=b._grade_case(Path(tmp),tasks[0]['public'][0])
        self.assertEqual(r['status'],'INFRA_FAILURE')
        self.assertEqual(r['stdout'],receipt['stdout'])
        self.assertEqual(r['stderr'],receipt['stderr'])
        self.assertIn('cleanup refused',r['cleanup_error'])

    def test_attempted_without_observation_is_not_not_executed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            _,tasks,schedule=b.load_contract()
            manifest={'schema':'far-agent-instruction-prepared/2',
                      'freeze':b.freeze_identity(),
                      'schedule_sha256':b.digest(b.canonical(b.load_contract()[2])),
                      'slots':schedule['slots']}
            (root/'prepared-manifest.json').write_text(json.dumps(manifest))
            (root/'evidence'/schedule['slots'][0]['slot_id']).mkdir(parents=True)
            decision=b.analyze(root)
            self.assertEqual(decision['decision'],'INVALID_EVIDENCE')
            self.assertTrue(any('ATTEMPTED_BUT_INCOMPLETE' in x for x in decision['errors']))

    def test_stdout_stderr_and_output_limit_receipts_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            script='import sys;print("x"*10000);sys.stderr.write("diagnostic\\n")'
            record=b._execute_traced_agent([sys.executable,'-c',script],p,{},10,200)
            self.assertTrue(record['output_limited'])
            self.assertTrue(len(record['stdout'])<=200)
            self.assertEqual(record['stdout_bytes_observed']>200,True)
            self.assertLessEqual(len(record['stderr']),200)

    def test_agent_subprocess_cannot_read_unregistered_parent_stdin(self):
        # A real redirected-input parent process must not leak its bytes into
        # the model invocation, even though the run-slot command is fixed.
        with tempfile.TemporaryDirectory() as tmp:
            script = (
                "import os,sys\n"
                "from pathlib import Path\n"
                "from tools.agent_instruction_premerge import _execute_traced_agent\n"
                "result=_execute_traced_agent("
                "[sys.executable,'-c','import sys; print(sys.stdin.read())'],"
                "Path(sys.argv[1]),os.environ.copy(),5,1000)\n"
                "sys.stdout.write(result['stdout'].decode('utf-8'))\n"
            )
            result = subprocess.run(
                [sys.executable, "-c", script, tmp], input="UNREGISTERED TASK CONTEXT",
                text=True, capture_output=True, cwd=b.ROOT, timeout=20,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "\n")
            self.assertNotIn("UNREGISTERED TASK CONTEXT", result.stdout)

    def test_schedule_blocks_out_of_order_execution_before_exposure(self):
        proto,tasks,sched=b.load_contract()
        wrong=sched['slots'][2]['slot_id']
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'evidence').mkdir()
            (root/'workspaces'/wrong).mkdir(parents=True)
            fake={'schema':'far-codex-runtime/1','requested_model':'gpt-6'}
            with patch.object(b,'validate_prepared',return_value={'freeze':b.freeze_identity()}), \
                 patch.object(b,'_command_identity',return_value=fake):
                with self.assertRaisesRegex(b.ContractError,'previous registered slot'):
                    b.run_slot(root,wrong,shlex.join(b._command_expected('gpt-6')))
            self.assertFalse((root/'evidence'/wrong).exists())

    def test_attempted_instruction_mutation_is_recorded_as_negative_observation(self):
        proto,tasks,sched=b.load_contract()
        cell=sched['slots'][0];task=next(t for t in tasks if t['id']==cell['task_id'])
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); ws=root/'workspaces'/cell['slot_id']
            ws.mkdir(parents=True);(root/'evidence').mkdir()
            for name,source in task['files'].items():(ws/name).write_text(source)
            (ws/'AGENTS.md').write_text('original instructions')
            (ws/'README.md').write_text('original prompt')
            (ws/'.gitignore').write_text('ignore')
            expected={p.name:b.digest(p.read_bytes()) for p in ws.iterdir()}
            (ws/'solution.py').write_text('def transform(d):return 100\n')
            (ws/'AGENTS.md').write_text('agent-overwrote-instructions')
            manifest={'freeze':b.freeze_identity(),'slots':[{**cell,
                      'initial_files_sha256':expected,
                      'instructions_sha256':b.digest(b'original instructions')}]}
            runtime={'schema':'far-codex-runtime/1','requested_model':'gpt-6'}
            raw=(b'{"type":"thread.started","thread_id":"s1"}\n'
                 b'{"type":"turn.started"}\n'
                 b'{"type":"turn.completed","usage":{"input_tokens":10,"output_tokens":1}}\n')
            response={'stdout':raw,'stderr':b'','stdout_bytes_observed':len(raw),
                      'stderr_bytes_observed':0,'output_limited':False,'timed_out':False,
                      'exit_code':0,'elapsed_seconds':0.1}
            with patch.object(b,'validate_prepared',return_value=manifest), \
                 patch.object(b,'_command_identity',return_value=runtime), \
                 patch.object(b,'_execute_traced_agent',return_value=response), \
                 patch.object(b,'pinned_instructions',return_value=b'original instructions'), \
                 patch.object(b,'_grade_case',return_value={'status':'FAILURE'}):
                observation=b.run_slot(root,cell['slot_id'],shlex.join(b._command_expected('gpt-6')))
                report=b.analyze(root)
            self.assertIn('UNAUTHORIZED_EDIT:AGENTS.md',observation['unauthorized'])
            self.assertEqual(observation['outcome'],'FAILURE')
            self.assertTrue((root/'evidence'/(cell['slot_id']+'.json')).is_file())
            self.assertTrue((root/'evidence'/cell['slot_id']/'agent-events.ndjson').is_file())
            self.assertNotEqual(report['decision'],'NOT_EXECUTED')

if __name__=='__main__': unittest.main()
