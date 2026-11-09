"""Adversarial negative controls for the future-PR invariant-contract preflight."""
import copy
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import pr_invariant_preflight as check

HEAD = 'a' * 40
BASE = 'b' * 40
FILES = [
    {'filename': 'tools/reader.py', 'status': 'modified'},
    {'filename': 'tools/auditor.py', 'status': 'modified'},
    {'filename': 'tests/test_reader.py', 'status': 'modified'},
    {'filename': 'tests/test_end_to_end.py', 'status': 'added'},
]
TESTS = {
    'tests/test_reader.py': '''
class ReaderTests:
    def test_complete_response(self): pass
    def test_trickle_deadline(self): pass
    def test_mismatched_transport(self): pass
''',
    'tests/test_end_to_end.py': '''
class IntegrationTests:
    async def test_native_recheck(self): pass
''',
}


def contract():
    return {
        'version': 1,
        'scope': 'Native HTTP observation and recorded evidence boundary',
        'limitations': ['Structural traceability is not behavioral correctness or independent review'],
        'invariants': [
            {
                'id': 'HTTP-EVIDENCE-01',
                'statement': 'Every native HTTP retrieval preserves observed bytes and bounded execution.',
                'boundary': 'Remote socket to bounded transport receipt and stored journal',
                'changed_paths': ['tools/reader.py', 'tools/auditor.py'],
                'failure_modes': [
                    {'case': 'A trickle past the absolute deadline must be rejected.',
                     'test': 'tests/test_reader.py::test_trickle_deadline'},
                    {'case': 'A forged transport prefix must not validate against the receipt.',
                     'test': 'tests/test_reader.py::test_mismatched_transport'},
                ],
                'positive_control': 'tests/test_reader.py::test_complete_response',
                'integration_control': 'tests/test_end_to_end.py::test_native_recheck',
                'assurance_limit': 'Static test-symbol checks do not establish test quality.',
            },
        ],
    }


def pr(body=None, created='2026-11-10T10:00:00Z', draft=False):
    if body is None:
        body = check.START + json.dumps(contract()) + check.END
    return {'number': 800, 'state': 'open', 'created_at': created, 'draft': draft,
            'head': {'sha': HEAD}, 'base': {'ref': 'main', 'sha': BASE},
            'changed_files': len(FILES), 'body': body}


def verify(p=None, files=None, content=None):
    return check.evaluate(p if p is not None else pr(), FILES if files is None else files,
                          lambda path, sha: (TESTS if content is None else content).get(path))


class PreflightContractTests(unittest.TestCase):
    def test_removed_and_renamed_sources_require_coverage(self):
        for changed in ([{'filename': 'tools/reader.py', 'status': 'removed'}],
                        [{'filename': 'tools/auditor.py', 'previous_filename': 'tools/reader.py', 'status': 'renamed'}]):
            p = pr()
            p['changed_files'] = len(changed)
            x = verify(p, changed)
            self.assertFalse(x['valid'])
            self.assertIn('implementation paths', ' '.join(x['errors']))

    def test_same_negative_or_positive_control_cannot_be_reused(self):
        for change in ('duplicate_negative', 'duplicate_positive'):
            data = contract()
            row = data['invariants'][0]
            if change == 'duplicate_negative':
                row['failure_modes'][1]['test'] = row['failure_modes'][0]['test']
            else:
                row['positive_control'] = row['integration_control']
            x = verify(pr(check.START + json.dumps(data) + check.END))
            self.assertFalse(x['valid'], change)
            self.assertIn('distinct', ' '.join(x['errors']))

    def test_nested_test_directory_is_valid_reference(self):
        self.assertEqual(('commercial/feature/tests/test_case.py', 'test_edge'),
                         check._valid_test_ref('commercial/feature/tests/test_case.py::test_edge'))

    def test_moving_base_fails_even_with_identical_head(self):
        p = pr()
        moved = pr()
        moved['base']['sha'] = 'c' * 40
        replies = iter([p, moved])
        def fake_api(url, token):
            if url.endswith('/pulls/800'):
                return next(replies)
            if '/contents/tests/' in url:
                source = TESTS[url.split('/contents/', 1)[1].split('?', 1)[0]].encode()
                return {'encoding': 'base64', 'content': __import__('base64').b64encode(source).decode(), 'size': len(source)}
            raise AssertionError(url)
        with patch.object(check, 'api', side_effect=fake_api), \
             patch.object(check, 'paginate', return_value=FILES):
            with self.assertRaisesRegex(ValueError, 'head or base moved'):
                check.check_live('owner/repo', 800, HEAD, 'fake-token')

    def test_required_context_preserves_trusted_checkout_and_no_skip(self):
        workflow = (Path(__file__).resolve().parents[1] / '.github/workflows/required-pr-review-convergence.yml').read_text()
        self.assertIn('name: pr-review-convergence-observation', workflow)
        self.assertIn('ref: main', workflow)
        self.assertIn('persist-credentials: false', workflow)
        self.assertLess(workflow.index('Check invariant-first contract before independent review'),
                        workflow.index("Enforce review evidence for this event's exact PR head"))
        self.assertIn('python3 tools/pr_invariant_preflight.py', workflow)
        self.assertIn('pr-invariant-preflight.json', workflow)

    def test_valid_contract_is_only_structural_not_correctness(self):
        output = verify()
        self.assertTrue(output['valid'], output)
        self.assertEqual(output['head_sha'], HEAD)
        self.assertEqual(output['contracts_checked'], 1)
        self.assertEqual(output['test_references_checked'], 4)
        self.assertFalse(output['software_correctness_verified'])
        self.assertFalse(output['independent_review_verified'])
        self.assertFalse(output['required_protected_checks_verified'])

    def test_cutover_respects_existing_open_prs(self):
        self.assertEqual('historical-pr', verify(pr(created='2026-11-09T23:59:59Z', body=''))['mode'])
        self.assertFalse(verify(pr(created='2026-11-10T00:00:00Z', body=''))['valid'])

    def test_non_implementation_changes_do_not_gain_false_claim(self):
        files = [{'filename': 'docs/overview.md', 'status': 'modified'}]
        p = pr(body='')
        p['changed_files'] = len(files)
        x = verify(p, files)
        self.assertTrue(x['valid'])
        self.assertEqual('documentation-only', x['mode'])
        self.assertFalse(x['software_correctness_verified'])

    def test_draft_deferred_until_ready_for_review(self):
        x = verify(pr(body='', draft=True))
        self.assertEqual('draft-deferred', x['mode'])
        self.assertTrue(x['valid'])
        p = pr(body='')
        self.assertFalse(verify(p)['valid'])

    def test_missing_or_duplicate_contract_fails_closed(self):
        body = pr()['body']
        for candidate in ('', body + '\n' + body, check.START + '{}' + check.END):
            with self.subTest(candidate=candidate[:30]):
                self.assertFalse(verify(pr(body=candidate))['valid'])

    def test_duplicate_json_keys_fails_closed(self):
        body = check.START + '{"version":1,"version":1}' + check.END
        self.assertIn('duplicate', ' '.join(verify(pr(body=body))['errors']))

    def test_uncovered_changed_source_fails(self):
        data = contract()
        data['invariants'][0]['changed_paths'] = ['tools/reader.py']
        x = verify(pr(check.START + json.dumps(data) + check.END))
        self.assertFalse(x['valid'])
        self.assertIn('tools/auditor.py', ' '.join(x['errors']))

    def test_borrowing_unchanged_source_is_not_coverage(self):
        data = contract()
        data['invariants'][0]['changed_paths'].append('tools/unrelated.py')
        self.assertFalse(verify(pr(check.START + json.dumps(data) + check.END))['valid'])

    def test_missing_negative_modes_fail(self):
        data = contract()
        data['invariants'][0]['failure_modes'] = []
        output = verify(pr(check.START + json.dumps(data) + check.END))
        self.assertFalse(output['valid'])
        self.assertTrue(any('two distinct' in x for x in output['errors']))

    def test_duplicate_mode_and_id_fail(self):
        data = contract()
        data['invariants'][0]['failure_modes'].append(dict(data['invariants'][0]['failure_modes'][0]))
        data['invariants'].append(copy.deepcopy(data['invariants'][0]))
        x = verify(pr(check.START + json.dumps(data) + check.END))
        self.assertFalse(x['valid'])
        self.assertIn('duplicate invariant ID', ' '.join(x['errors']))
        self.assertIn('duplicate failure case', ' '.join(x['errors']))

    def test_missing_named_test_fails_even_if_file_exists(self):
        data = contract()
        data['invariants'][0]['failure_modes'][0]['test'] = 'tests/test_reader.py::test_fabricated'
        x = verify(pr(check.START + json.dumps(data) + check.END))
        self.assertFalse(x['valid'])
        self.assertIn('test_fabricated', ' '.join(x['errors']))

    def test_missing_test_file_fails_even_when_declared(self):
        x = verify(content={})
        self.assertFalse(x['valid'])
        self.assertIn('test symbol not present', ' '.join(x['errors']))

    def test_rejects_test_ref_traversal(self):
        data = contract()
        data['invariants'][0]['positive_control'] = 'tests/../evil.py::test_succeeds'
        x = verify(pr(check.START + json.dumps(data) + check.END))
        self.assertFalse(x['valid'])
        self.assertIn('invalid test reference', ' '.join(x['errors']))

    def test_rejects_incomplete_diff(self):
        p = pr()
        p['changed_files'] += 1
        with self.assertRaisesRegex(ValueError, 'count mismatch'):
            verify(p)

    def test_implementation_path_classifier_covers_code_config_and_governance(self):
        for name in ('tools/a.py', 'mechanization/a.lean', '.github/workflows/ci.yml',
                     'schemas/a.json', 'AGENTS.md', 'requirements-dev.txt'):
            self.assertTrue(check.is_implementation_path(name), name)
        for name in ('docs/README.md', 'tests/test_a.py', 'research/snapshot.json',
                     'docs/notes.md'):
            self.assertFalse(check.is_implementation_path(name), name)

    def test_no_untrusted_python_execution(self):
        # A test file is scanned as text; no user Python is imported or executed.
        file_content = {'tests/test_reader.py': 'raise RuntimeError("MUST_NOT_EXECUTE")\n'
                        + TESTS['tests/test_reader.py'],
                        'tests/test_end_to_end.py': TESTS['tests/test_end_to_end.py']}
        self.assertTrue(verify(content=file_content)['valid'])

    def test_no_pr_movement_can_pass_live(self):
        old = pr()
        moved = pr()
        moved['head']['sha'] = 'c' * 40
        replies = iter([old, moved])
        def fake_api(url, token):
            if url.endswith('/pulls/800'):
                return next(replies)
            if '/contents/tests/' in url:
                path = url.split('/contents/', 1)[1].split('?', 1)[0]
                source = TESTS[path].encode()
                return {'encoding': 'base64', 'content': __import__('base64').b64encode(source).decode(), 'size': len(source)}
            raise AssertionError(url)
        with patch.object(check, 'api', side_effect=fake_api), \
             patch.object(check, 'paginate', return_value=FILES):
            with self.assertRaisesRegex(ValueError, 'moved during'):
                check.check_live('owner/repo', 800, HEAD, 'fake-token')

    def test_historical_live_does_not_require_file_api(self):
        prior = pr(created='2026-11-09T22:00:00Z', body='')
        with patch.object(check, 'api', side_effect=[prior, prior]), \
             patch.object(check, 'paginate', side_effect=AssertionError('must not list files')):
            result = check.check_live('owner/repo', 800, HEAD, 'fake-token')
        self.assertTrue(result['valid'])
        self.assertEqual(result['mode'], 'historical-pr')

    def test_live_uses_exact_commit_when_reading_test_sources(self):
        p = pr()
        calls = []
        def fake_api(url, token):
            calls.append(url)
            if url.endswith('/pulls/800'):
                return copy.deepcopy(p)
            if '/contents/tests/' in url:
                self.assertTrue(url.endswith('?ref=' + HEAD))
                path = url.split('/contents/', 1)[1].split('?', 1)[0]
                source = TESTS[path].encode()
                return {'encoding': 'base64', 'content': __import__('base64').b64encode(source).decode(), 'size': len(source)}
            raise AssertionError(url)
        with patch.object(check, 'api', side_effect=fake_api), \
             patch.object(check, 'paginate', return_value=FILES):
            result = check.check_live('owner/repo', 800, HEAD, 'fake-token')
        self.assertTrue(result['valid'], result)
        self.assertEqual(len([u for u in calls if '/pulls/800' in u]), 2)


if __name__ == '__main__':
    unittest.main()
