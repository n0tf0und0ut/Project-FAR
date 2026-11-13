"""Offline adversarial contracts only; mocking a model does NOT prove model autonomy."""
import json
import re
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

from tools.factory_autonomous_one_pr import (
    ORACLE_SHA256, REPO, SOURCE, TEST, SmokeError,
    ask_model, attempt, check_oracle, claim_guard, replace_claim_guard, work_order,
    publish, pinned_model_digest, MODEL_DIGEST, MODEL,
)

BASE = Path(__file__).resolve().parents[1]


def sh(repo, *argv):
    subprocess.run(['git', *argv], cwd=repo, check=True, capture_output=True)


# Fixture is pinned to the historical defect, not the live implementation.
# Its content must remain valid even after the generated PR fixes main.
DEFECTIVE_CLAIM_GUARD = (
    '        if not isinstance(worker, str) or not IDENT.fullmatch(worker) '
    'or ttl < 1 or ttl > 86400 or max_attempts < 1:'
)


def frozen_defective_source(source: str) -> str:
    guard, _ = claim_guard(source)
    if guard.rstrip('\r\n') == DEFECTIVE_CLAIM_GUARD:
        return source
    lines = source.splitlines(keepends=True)
    positions = [i for i, line in enumerate(lines) if line == guard]
    if len(positions) != 1:
        raise AssertionError('ambiguous claim guard in regression fixture')
    lines[positions[0]] = DEFECTIVE_CLAIM_GUARD + ('\r\n' if guard.endswith('\r\n') else '\n')
    restored = ''.join(lines)
    __import__('ast').parse(restored)
    return restored


class FactoryAutonomousProofContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'repo'
        self.repo.mkdir()
        for path in (SOURCE, 'research/factory-evaluation/claim-parameter-holdout.py.txt',
                     'research/factory-evaluation/claim-preservation-oracle.py.txt'):
            dst = self.repo / path
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes((BASE / path).read_bytes())
        (self.repo / 'tests').mkdir()
        source_path = self.repo / SOURCE
        source_path.write_text(frozen_defective_source(source_path.read_text(encoding='utf-8')), encoding='utf-8')
        sh(self.repo, 'init', '-q')
        sh(self.repo, 'config', 'user.name', 'test')
        sh(self.repo, 'config', 'user.email', 'test@example.invalid')
        sh(self.repo, 'add', '-A')
        sh(self.repo, 'commit', '-qm', 'baseline')
        self.base_sha = subprocess.check_output(['git','rev-parse','HEAD'],cwd=self.repo,text=True).strip()
        github_event = patch.dict(os.environ, {'GITHUB_EVENT_NAME':'push',
            'GITHUB_REF':'refs/heads/main', 'GITHUB_REPOSITORY':REPO,
            'GITHUB_SHA':self.base_sha})
        github_event.start()
        self.addCleanup(github_event.stop)
        self.out = Path(self.temp.name) / 'out'
        self.db = Path(self.temp.name) / 'store.sqlite'
        self.source = (self.repo / SOURCE).read_text()
        self.old, _ = claim_guard(self.source)
        self.new = ("if not isinstance(worker, str) or not IDENT.fullmatch(worker) "
                    "or type(ttl) is not int or ttl < 1 or ttl > 86400 "
                    "or type(max_attempts) is not int or max_attempts < 1:")

    def test_full_model_manifest_pin_and_rejection(self):
        class Response:
            def __init__(self, data):
                self.data = data
            def __enter__(self):
                return self
            def __exit__(self, *_):
                return False
            def read(self, n):
                return self.data[:n]
        def response(rows):
            return Response(json.dumps({'models': rows}).encode('utf-8'))
        valid = {'name': MODEL, 'digest': MODEL_DIGEST}
        with patch('tools.factory_autonomous_one_pr.urllib.request.urlopen',
                   return_value=response([valid])):
            self.assertEqual(pinned_model_digest(), MODEL_DIGEST)
        for rows in ([], [valid, valid], [{'name': MODEL, 'digest': '0'*64}],
                     [{'name': 'qwen2.5-coder:1.5b', 'digest': MODEL_DIGEST}]):
            with self.subTest(rows=rows):
                with patch('tools.factory_autonomous_one_pr.urllib.request.urlopen',
                           return_value=response(rows)):
                    with self.assertRaisesRegex(SmokeError, 'digest mismatch'):
                        pinned_model_digest()

    def test_wrong_model_digest_releases_lease_without_patch(self):
        with patch('tools.factory_autonomous_one_pr.pinned_model_digest',
                   side_effect=SmokeError('pinned coding model digest mismatch')):
            self.assertFalse(attempt(self.repo, self.db, self.out))
        receipt = json.loads((self.out / 'attempt-receipt.json').read_text())
        self.assertEqual(receipt['verdict'], 'MODEL_ATTEMPT_FAILED')
        self.assertEqual(receipt['failure_stage'], 'pinned coding model digest mismatch')
        self.assertEqual([event['event'] for event in receipt['queue_snapshot']['tasks'][0]['history']],
                         ['claimed', 'failed'])
        self.assertFalse((self.out / 'candidate.patch').exists())

    def test_defective_fixture_is_stable_after_valid_repair(self):
        # Simulates a later protected-main checkout containing the intended fix.
        repaired = replace_claim_guard(self.source, self.new)
        self.assertNotEqual(repaired, self.source)
        self.assertEqual(frozen_defective_source(repaired), self.source)
        self.assertEqual(frozen_defective_source(self.source), self.source)

    def test_frozen_oracle_hash_and_red_baseline(self):
        raw = check_oracle(self.repo)
        self.assertEqual(__import__('hashlib').sha256(raw).hexdigest(), ORACLE_SHA256)
        self.assertIn('ttl < 1', self.old)

    def test_work_order_binding_and_schema(self):
        a = work_order('a' * 40)
        self.assertEqual(a['repository'], REPO)
        self.assertEqual(a['tasks'][0]['id'], 'repair')
        with self.assertRaises(SmokeError):
            work_order('not-a-sha')

    def test_source_single_line_guard_positive_control(self):
        updated = replace_claim_guard(self.source, self.new)
        self.assertEqual(len(updated.splitlines()), len(self.source.splitlines()))
        self.assertEqual(updated.count('type(ttl) is not int'), 1)
        self.assertNotEqual(updated, self.source)
        self.assertEqual(len([x for x,y in zip(updated.splitlines(), self.source.splitlines()) if x != y]),1)
        __import__('ast').parse(updated)

    def test_forbidden_model_text_does_not_modify_source(self):
        for x in (None, '', 'if True:\n    pass',
                  '        if True:; import os', 8, '        if False:\r',
                  self.old.strip('\n'), 'x'*700):
            with self.subTest(value=repr(x)[:30]):
                with self.assertRaises((SmokeError, SyntaxError)):
                    replace_claim_guard(self.source, x)

    def test_syntactically_valid_but_wrong_guard_is_only_a_proposal(self):
        # Semantic rejection belongs to the frozen oracle, not a heuristic gate.
        updated = replace_claim_guard(self.source, 'if True:')
        self.assertIn('        if True:', updated)

    def test_reject_mismatched_trusted_main_event(self):
        with patch.dict(os.environ, {'GITHUB_SHA':'f'*40}):
            with self.assertRaisesRegex(SmokeError,'runner checkout differs'):
                attempt(self.repo, self.db, self.out)
        self.assertFalse(self.db.exists())

    def test_reject_holdout_tampering(self):
        p = self.repo / 'research/factory-evaluation/claim-parameter-holdout.py.txt'
        p.write_bytes(p.read_bytes()+b'\n')
        with self.assertRaisesRegex(SmokeError, 'oracle SHA-256'):
            check_oracle(self.repo)

    def test_preservation_oracle_rejects_reviewed_counterexample(self):
        from tools.factory_autonomous_one_pr import check_preservation
        original = check_preservation(self.repo)
        self.assertEqual(__import__('hashlib').sha256(original).hexdigest(),
                         '104f24eeaede44a6f25bf16e2910c2512a7c21150646c1ebd66f06d88901cb51')
        bad = replace_claim_guard(self.source,
            'if type(ttl) is not int or type(max_attempts) is not int or ttl > 86400:')
        (self.repo / SOURCE).write_text(bad)
        (self.repo / 'tools/__init__.py').touch()
        (self.repo / 'tests/__init__.py').touch()
        (self.repo / 'tests/test_factory_claim_preservation.py').write_bytes(original)
        proc = subprocess.run(['python','-m','unittest','tests.test_factory_claim_preservation','-v'],
                              cwd=self.repo,capture_output=True,text=True)
        self.assertNotEqual(proc.returncode,0)
        self.assertIn('FAILED',proc.stderr)

    def test_mocked_model_lease_generates_advisory_patch_but_not_pr(self):
        # This is a structural test; no real model or Docker is invoked.
        def grader(*a, **kw):
            return {'state': 'PASS', 'test_count_reported': 44}
        def oracle(*a, **kw):
            return {'state': 'FAIL' if a[3] == 'before' else 'PASS',
                    'test_count_reported': 3 if a[3].startswith('preservation-') else 4}
        with patch('tools.factory_autonomous_one_pr.pinned_model_digest',return_value=MODEL_DIGEST), \
             patch('tools.factory_autonomous_one_pr.grader_image_id',return_value='sha256:'+'a'*64), \
             patch('tools.factory_autonomous_one_pr.ask_model',return_value=(self.new,{'model':MODEL})), \
             patch('tools.factory_autonomous_one_pr.grade_in_docker',side_effect=grader), \
             patch('tools.factory_autonomous_one_pr.grade_with_oracle',side_effect=oracle):
            eligible = attempt(self.repo,self.db,self.out)
        self.assertTrue(eligible)
        receipt = json.loads((self.out/'attempt-receipt.json').read_text())
        self.assertEqual(receipt['verdict'],'MODEL_PATCH_ELIGIBLE_FOR_INDEPENDENT_GITHUB_PR')
        self.assertEqual(receipt['queue_snapshot']['tasks'][0]['state'],'running')
        self.assertEqual(receipt['queue_snapshot']['tasks'][0]['stage'],'build')
        self.assertIsNone(receipt['queue_snapshot']['tasks'][0].get('pr_number'))
        self.assertTrue((self.out/'candidate.patch').exists())
        self.assertNotIn('token', json.dumps(receipt['queue_snapshot']).lower())

    def test_failed_oracle_drives_second_model_proposal_with_source_bound_feedback(self):
        import tools.factory_autonomous_one_pr as module
        unsafe = ('if not isinstance(worker, str) or not IDENT.fullmatch(worker) '
                  'or not isinstance(ttl, int) or ttl < 1 or ttl > 86400 '
                  'or not isinstance(max_attempts, int) or max_attempts < 1:')
        prompts = []
        def model(prompt, output):
            prompts.append(prompt)
            return (unsafe if len(prompts) == 1 else self.new), {'model': MODEL}
        def oracle(*a, **kw):
            label = a[3]
            if label == 'before':
                return {'state': 'FAIL', 'test_count_reported': 4}
            if label == 'after-1':
                # Docker emits source-bound test output into its artifact.
                (self.out / 'after-1.stderr').write_text(
                    "FAIL: test_bad_ttl_does_not_consume_lease (value='True') "
                    "FROZEN_ORACLE_SOURCE_DO_NOT_LEAK\n")
                return {'state': 'FAIL', 'test_count_reported': 4}
            return {'state': 'PASS', 'test_count_reported': 3 if label.startswith('preservation-') else 4}
        with patch('tools.factory_autonomous_one_pr.pinned_model_digest', return_value=MODEL_DIGEST), \
             patch('tools.factory_autonomous_one_pr.grader_image_id', return_value='sha256:'+'a'*64), \
             patch('tools.factory_autonomous_one_pr.ask_model', side_effect=model), \
             patch('tools.factory_autonomous_one_pr.grade_in_docker',
                   return_value={'state':'PASS', 'test_count_reported':44}), \
             patch('tools.factory_autonomous_one_pr.grade_with_oracle', side_effect=oracle):
            self.assertTrue(attempt(self.repo, self.db, self.out))
        receipt = json.loads((self.out/'attempt-receipt.json').read_text())
        self.assertEqual(receipt['verdict'], 'MODEL_PATCH_ELIGIBLE_FOR_INDEPENDENT_GITHUB_PR')
        self.assertEqual([trial['acceptance']['state'] for trial in receipt['model_trials']],
                         ['FAIL', 'PASS'])
        self.assertIn('isinstance(True, int)', prompts[1])
        self.assertIn('FAIL (4 frozen acceptance tests)', prompts[1])
        self.assertNotIn('FROZEN_ORACLE_SOURCE_DO_NOT_LEAK', prompts[1])
        self.assertNotIn("value='True'", prompts[1])
        self.assertTrue((self.out/'model-round-1/candidate.patch').is_file())
        self.assertTrue((self.out/'model-round-2/candidate.patch').is_file())
        self.assertTrue((self.out/'candidate.patch').is_file())
        self.assertIn('model-round-1/candidate.patch', receipt['artifacts_sha256'])
        self.assertEqual(receipt['queue_snapshot']['tasks'][0]['stage'], 'build')
        self.assertEqual([event['event'] for event in receipt['queue_snapshot']['tasks'][0]['history']],
                         ['claimed'])

    def test_both_failed_model_candidates_preserved_without_queue_promotion(self):
        unsafe = ('if not isinstance(worker, str) or not IDENT.fullmatch(worker) '
                  'or not isinstance(ttl, int) or ttl < 1 or ttl > 86400 '
                  'or not isinstance(max_attempts, int) or max_attempts < 1:')
        calls = []
        def model(prompt, output):
            calls.append(prompt)
            return unsafe, {'model':MODEL}
        def oracle(*a, **kw):
            label = a[3]
            if label.startswith('preservation-'):
                return {'state':'PASS','test_count_reported':3}
            return {'state':'FAIL','test_count_reported':4}
        with patch('tools.factory_autonomous_one_pr.pinned_model_digest', return_value=MODEL_DIGEST), \
             patch('tools.factory_autonomous_one_pr.grader_image_id', return_value='sha256:'+'a'*64), \
             patch('tools.factory_autonomous_one_pr.ask_model', side_effect=model), \
             patch('tools.factory_autonomous_one_pr.grade_with_oracle', side_effect=oracle):
            self.assertFalse(attempt(self.repo, self.db, self.out))
        receipt = json.loads((self.out/'attempt-receipt.json').read_text())
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(receipt['model_trials']), 2)
        self.assertEqual(receipt['failure_stage'],
                         'model candidate failed frozen acceptance oracle after two distinct proposals')
        self.assertFalse((self.out/'candidate.patch').exists())
        self.assertTrue((self.out/'model-round-1/candidate.patch').is_file())
        self.assertTrue((self.out/'model-round-2/candidate.patch').is_file())
        self.assertEqual([event['event'] for event in receipt['queue_snapshot']['tasks'][0]['history']],
                         ['claimed', 'failed'])
        self.assertEqual(receipt['queue_snapshot']['tasks'][0]['stage'], 'build')
        self.assertEqual(receipt['queue_snapshot']['tasks'][0]['state'], 'queued')

    def test_mocked_worker_rejection_does_not_complete_factory(self):
        with patch('tools.factory_autonomous_one_pr.pinned_model_digest',return_value=MODEL_DIGEST), \
             patch('tools.factory_autonomous_one_pr.grader_image_id',return_value='sha256:'+'a'*64), \
             patch('tools.factory_autonomous_one_pr.ask_model',return_value=(self.old.strip(),{'model':MODEL})), \
             patch('tools.factory_autonomous_one_pr.grade_with_oracle',return_value={'state':'FAIL','test_count_reported':4}):
            result=attempt(self.repo,self.db,self.out)
        self.assertFalse(result)
        receipt=json.loads((self.out/'attempt-receipt.json').read_text())
        self.assertEqual(receipt['queue_snapshot']['tasks'][0]['state'],'queued')
        self.assertEqual([x['event'] for x in receipt['queue_snapshot']['tasks'][0]['history']],['claimed','failed'])
        self.assertFalse((self.out/'candidate.patch').exists())

    def test_publisher_rejects_invalid_proposal_without_credentials(self):
        self.out.mkdir()
        (self.out/'attempt-receipt.json').write_text(json.dumps({'schema':'other','verdict':'MODEL_PATCH_ELIGIBLE_FOR_INDEPENDENT_GITHUB_PR'}))
        with self.assertRaisesRegex(SmokeError,'no eligible genuine'):
            publish(self.repo,self.db,self.out)


    def test_mocked_valid_patch_reaches_publisher_and_real_queue_build_record(self):
        # No real model, GitHub API, or push here. This validates the *complete*
        # local state transition and Git diff handling with explicit host mocks.
        import tools.factory_autonomous_one_pr as module
        def grade(*args, **kwargs):
            return {'state': 'PASS', 'test_count_reported': 44}
        def hold(*args, **kwargs):
            return {'state': 'FAIL' if args[3] == 'before' else 'PASS',
                    'test_count_reported': 3 if args[3].startswith('preservation-') else 4}
        with patch('tools.factory_autonomous_one_pr.pinned_model_digest',return_value=MODEL_DIGEST), \
             patch('tools.factory_autonomous_one_pr.grader_image_id', return_value='sha256:'+'a'*64), \
             patch('tools.factory_autonomous_one_pr.ask_model', return_value=(self.new, {'model':MODEL})), \
             patch('tools.factory_autonomous_one_pr.grade_in_docker', side_effect=grade), \
             patch('tools.factory_autonomous_one_pr.grade_with_oracle', side_effect=hold):
            self.assertTrue(attempt(self.repo, self.db, self.out))

        actual = module._run
        actions = []
        def fake_cli(*args, cwd):
            if args[:3] == ('gh','auth','setup-git'):
                actions.append('auth')
                return ''
            if args[:2] == ('git','push'):
                actions.append('push')
                return ''
            if args[:3] == ('gh','pr','create'):
                actions.append('create-pr')
                return 'https://github.com/'+REPO+'/pull/999'
            if args[:3] == ('gh','pr','view'):
                actions.append('view-pr')
                return '999'
            return actual(*args, cwd=cwd)
        with patch.dict(os.environ, {'GH_TOKEN':'fake-not-a-real-token',
                                      'GITHUB_REPOSITORY': REPO,
                                      'GITHUB_RUN_ID':'123'}), \
             patch('tools.factory_autonomous_one_pr._run', side_effect=fake_cli):
            result = publish(self.repo, self.db, self.out)
        self.assertEqual(actions, ['auth','push','create-pr','view-pr'])
        self.assertEqual(result['pr_number'], 999)
        self.assertEqual(result['queue_snapshot']['tasks'][0]['stage'],'test')
        self.assertEqual(result['queue_snapshot']['tasks'][0]['state'],'queued')
        self.assertEqual([h['event'] for h in result['queue_snapshot']['tasks'][0]['history']],
                         ['claimed','completed'])
        self.assertEqual(result['queue_snapshot']['tasks'][0]['history'][-1]['evidence']['pr_number'], 999)
        self.assertIn('type(ttl) is not int', (self.repo / SOURCE).read_text())
        self.assertEqual((self.repo / TEST).read_bytes(),check_oracle(self.repo))
        from tools.factory_autonomous_one_pr import PRESERVATION_TEST, check_preservation
        self.assertEqual((self.repo / PRESERVATION_TEST).read_bytes(),check_preservation(self.repo))
        body=(self.out/'pr-body.md').read_text()
        block=re.search(r'<!-- FAR-INVARIANTS-V1\n(.*?)\nFAR-INVARIANTS-END -->',body,re.S)
        self.assertIsNotNone(block)
        inv=json.loads(block.group(1))
        self.assertEqual(set(inv),{'version','scope','invariants','limitations'})
        self.assertEqual(inv['version'],1)
        self.assertTrue(inv['limitations'])
        row=inv['invariants'][0]
        self.assertEqual(set(row),{'id','statement','boundary','changed_paths',
            'failure_modes','positive_control','integration_control','assurance_limit'})
        self.assertEqual(set(row['changed_paths']),{SOURCE,TEST,PRESERVATION_TEST})
        self.assertGreaterEqual(len(row['failure_modes']),2)
        refs=[x['test'] for x in row['failure_modes']]+[row['positive_control'],row['integration_control']]
        self.assertEqual(len(set(refs)),len(refs))


if __name__ == '__main__':
    unittest.main()
