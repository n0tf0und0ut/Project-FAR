"""Replays of native length and model-budget failure cases."""
import copy
import json
import importlib
import re
import unittest
from pathlib import Path
from unittest.mock import Mock

from tools.far_investigation_audit import audit
from tools.far_investigation_engine import Investigation
from tools.far_investigation_retrieval import RetrievalPolicy, retrieve
from tests.test_far_investigation_audit import NativeFunctionFixtureModel, reseal
from tests.test_far_investigation_engine import BODY_A, BODY_B, QUESTION, URL_A, URL_B, full_script, FixtureRetriever, ScriptedFixtureModel
from tests.test_far_investigation_retrieval import Response, dns


class InvestigationReviewerRegressionTests(unittest.TestCase):
    def test_proposal_checkpoint_failure_records_rejection_before_any_dispatch(self):
        for tool in ('retrieve', 'discover', 'freeze', 'finish'):
            with self.subTest(tool=tool):
                failed = False
                def checkpoint(state):
                    nonlocal failed
                    event = state['events'][-1]
                    if not failed and event['kind'] == 'TOOL_PROPOSAL' and event['payload']['tool'] == tool:
                        failed = True
                        raise OSError('transient proposal checkpoint failure')
                choices = full_script()
                position = next(index for index, proposal in enumerate(choices) if proposal['tool'] == tool)
                choices.insert(position, copy.deepcopy(choices[position]))
                state = Investigation(QUESTION,
                    RetrievalPolicy(('example.org', 'independent.example.org')),
                    seeds=[URL_A, URL_B], fetcher=FixtureRetriever(), checkpoint=checkpoint,
                ).run_agent(NativeFunctionFixtureModel(choices))
                self.assertTrue(failed)
                self.assertEqual(state['status'], 'BOUNDED_PIPELINE_COMPLETED')
                self.assertEqual(state['rejected_calls'], 1)
                rejected = next(index for index, event in enumerate(state['events'])
                                if event['kind'] == 'TOOL_REJECTED')
                self.assertEqual(state['events'][rejected - 1]['kind'], 'TOOL_PROPOSAL')
                self.assertEqual(state['http_calls'], 4)
                self.assertEqual(len(state['evaluations']), 1)
                self.assertTrue(audit(state)['valid'], audit(state))

    def native_source_state(self):
        def fetch(url, policy, checkpoint):
            client = Mock()
            body = ('<script>'+BODY_A+'</script>') if url == URL_A else BODY_B
            response = Response(body.encode(), url=url)
            response.headers['Content-Length'] = str(len(body.encode()))
            client.open.return_value = response
            return retrieve(url, policy, checkpoint=checkpoint, opener=client)

        state = Investigation(QUESTION,
            RetrievalPolicy(('example.org', 'independent.example.org'), resolver=dns),
            fetcher=fetch).run_agent(NativeFunctionFixtureModel(full_script()))
        self.assertTrue(audit(state)['valid'], audit(state))
        return state


    def test_resealed_native_receipt_cannot_claim_redirect_or_compression(self):
        original = self.native_source_state()
        for defect in ('redirect', 'compression'):
            with self.subTest(defect=defect):
                state = copy.deepcopy(original)
                touched = [0]

                def rewrite(node):
                    if isinstance(node, dict):
                        if (node.get('status') in ('RETRIEVED', 'RECEIVED')
                                and isinstance(node.get('request'), dict)
                                and 'raw_base64' in node):
                            if defect == 'redirect':
                                node['response_url'] = 'https://unregistered.example/answer'
                                if isinstance(node.get('transport'), dict):
                                    node['transport']['response_url'] = node['response_url']
                            else:
                                node['content_encoding'] = 'gzip'
                                if isinstance(node.get('transport'), dict):
                                    node['transport']['response_headers']['Content-Encoding'] = 'gzip'
                            touched[0] += 1
                        for child in node.values():
                            rewrite(child)
                    elif isinstance(node, list):
                        for child in node:
                            rewrite(child)

                rewrite(state)
                self.assertGreater(touched[0], 0)
                reseal(state)
                result = audit(state)
                self.assertFalse(result['valid'], result)
                expected = 'response_url' if defect == 'redirect' else 'content_encoding'
                self.assertTrue(any(expected in error for error in result['errors']), result)

    def test_undispatched_recheck_checkpoint_failure_preserves_terminal_readiness(self):
        actions = full_script()
        actions.insert(7, {'tool': 'recheck', 'args': {}})
        seen = [0]

        def checkpoint(state):
            event = state['events'][-1]
            if event['kind'] == 'TOOL_PROPOSAL' and event['payload']['tool'] == 'recheck':
                seen[0] += 1
                if seen[0] == 2:
                    raise OSError('second proposal persistence unavailable')

        state = Investigation(
            QUESTION, RetrievalPolicy(('example.org', 'independent.example.org')),
            seeds=[URL_A, URL_B], fetcher=FixtureRetriever(), checkpoint=checkpoint,
        ).run_agent(NativeFunctionFixtureModel(actions))
        self.assertEqual(seen[0], 2)
        self.assertEqual(state['status'], 'BOUNDED_PIPELINE_COMPLETED')
        self.assertEqual(state['rejected_calls'], 1)
        self.assertEqual(state['http_calls'], 4)
        self.assertEqual(len(state['rechecks']), 2)
        self.assertTrue(audit(state)['valid'], audit(state))

    def test_large_permitted_source_has_bounded_progressive_journal(self):
        raw = b'x' * 1_500_000
        client = Mock()
        client.open.return_value = Response(raw, url=URL_A)
        observations = []
        result = retrieve(
            URL_A, RetrievalPolicy(('example.org',), max_bytes=2_000_000, resolver=dns),
            checkpoint=observations.append, opener=client)
        self.assertEqual(result['status'], 'RETRIEVED')
        self.assertEqual(result['observed_bytes'], len(raw))
        self.assertGreaterEqual(len(observations), 2)
        # The old per-chunk accumulated-body snapshots exceeded 64 MB
        # for this legal response; geometric checkpoints stay far below it.
        journal_bytes = len(json.dumps(observations))
        self.assertLess(journal_bytes, 24_000_000)
        self.assertEqual(observations[-1]['raw_base64'], result['raw_base64'])

    def test_native_framing_lists_must_match_headers_and_runtime_rules(self):
        def missing_length_list(transport):
            transport['content_length_values'] = []

        def changed_length_header(transport):
            transport['response_headers']['Content-Length'] = '9999'

        def ambiguous_transfer(transport):
            transport['response_headers']['Transfer-Encoding'] = 'chunked'
            transport['transfer_encoding_values'] = ['chunked']

        def unsupported_transfer(transport):
            transport['response_headers'].pop('Content-Length')
            transport['content_length_values'] = []
            transport['response_headers']['Transfer-Encoding'] = 'gzip'
            transport['transfer_encoding_values'] = ['gzip']

        def missing_transfer_list(transport):
            transport['response_headers'].pop('Content-Length')
            transport['content_length_values'] = []
            transport['response_headers']['Transfer-Encoding'] = 'chunked'
            transport['transfer_encoding_values'] = []

        original = self.native_source_state()
        for mutate in (missing_length_list, changed_length_header, ambiguous_transfer,
                       unsupported_transfer, missing_transfer_list):
            with self.subTest(mutation=mutate.__name__):
                state = copy.deepcopy(original)
                def walk(node):
                    if isinstance(node, dict):
                        if node.get('status') == 'RETRIEVED' and isinstance(node.get('transport'), dict):
                            mutate(node['transport'])
                        for value in node.values():
                            walk(value)
                    elif isinstance(node, list):
                        for value in node:
                            walk(value)
                walk(state)
                reseal(state)
                result = audit(state)
                self.assertFalse(result['valid'], result)
                self.assertTrue(any('framing' in error for error in result['errors']), result)

    def test_successful_sources_cannot_exceed_recorded_byte_ceiling(self):
        original = self.native_source_state()
        largest = max(row['observed_bytes'] for row in original['sources'].values())
        for ceiling, valid in ((largest, True), (largest - 1, False), (1, False),
                               (True, False), (0, False), (20_000_001, False)):
            with self.subTest(ceiling=ceiling):
                state = copy.deepcopy(original)
                state['policy']['max_bytes'] = ceiling
                state['events'][0]['payload']['policy']['max_bytes'] = ceiling
                reseal(state)
                result = audit(state)
                self.assertEqual(result['valid'], valid, result)
                if not valid:
                    self.assertTrue(any('byte' in error or 'policy' in error for error in result['errors']), result)

    def test_legacy_headers_without_lists_still_enforce_declared_length(self):
        state = self.native_source_state()
        def walk(node, mismatch=False):
            if isinstance(node, dict):
                if node.get('status') == 'RETRIEVED' and isinstance(node.get('transport'), dict):
                    transport = node['transport']
                    transport.pop('content_length_values', None)
                    transport.pop('transfer_encoding_values', None)
                    if mismatch:
                        transport['response_headers']['Content-Length'] = '9999'
                for value in node.values():
                    walk(value, mismatch)
            elif isinstance(node, list):
                for value in node:
                    walk(value, mismatch)
        walk(state)
        reseal(state)
        self.assertTrue(audit(state)['valid'], audit(state))
        walk(state, mismatch=True)
        reseal(state)
        result = audit(state)
        self.assertFalse(result['valid'], result)
        self.assertTrue(any('content_length' in error for error in result['errors']), result)

    def test_complete_native_body_must_match_declared_length(self):
        def fetch(url, policy, checkpoint):
            client = Mock()
            body = ('<script>'+BODY_A+'</script>') if url == URL_A else BODY_B
            client.open.return_value = Response(body.encode(), url=url)
            return retrieve(url, policy, checkpoint=checkpoint, opener=client)

        state=Investigation(QUESTION,
            RetrievalPolicy(('example.org','independent.example.org'),resolver=dns),
            fetcher=fetch).run_agent(NativeFunctionFixtureModel(full_script()))
        self.assertTrue(audit(state)['valid'])
        copy_state=copy.deepcopy(state)
        mutated=[0]
        def walk(node):
            if isinstance(node,dict):
                if node.get('status')=='RETRIEVED' and isinstance(node.get('transport'),dict):
                    node['transport']['content_length_values']=['9999']
                    node['transport']['response_headers']['Content-Length']='9999'
                    mutated[0]+=1
                for value in node.values():
                    walk(value)
            elif isinstance(node,list):
                for value in node:
                    walk(value)
        walk(copy_state)
        self.assertGreater(mutated[0],0)
        reseal(copy_state)
        errors=audit(copy_state)['errors']
        self.assertTrue(any('content_length' in e for e in errors),errors)

    def test_known_failure_class_index_is_complete_and_controls_exist(self):
        """A new ledger finding cannot silently lack a failure class and test references.

        This is *structural* coverage verification only: behavior and defect
        sensitivity require separately executed positive/negative controls.
        """
        ledger = (Path(__file__).resolve().parents[1] /
                  'research/investigation-engine/finding-ledger.md').read_text(encoding='utf-8')
        header = '## Known review-failure-class coverage index (2026-11-10)'
        begin = '<!-- BEGIN FAR-INVESTIGATION-FAILURE-CLASS-COVERAGE/1 -->'
        end = '<!-- END FAR-INVESTIGATION-FAILURE-CLASS-COVERAGE/1 -->'
        self.assertEqual(ledger.count(begin), 1)
        self.assertEqual(ledger.count(end), 1)
        earlier, tail = ledger.split(header, 1)
        payload = tail.split(begin, 1)[1].split(end, 1)[0].strip()
        self.assertTrue(payload.startswith('```json') and payload.endswith('```'), payload[:80])
        catalog = json.loads(payload[len('```json'):-len('```')].strip())
        self.assertEqual(catalog['schema'], 'far-investigation-failure-class-coverage/1')
        ledger_ids = set(re.findall(r'\\b(?:ENG|RC608|HIST-608|HTTP-FRAMING)-[A-Z0-9-]+\\b', earlier))
        allocated = [finding for group in catalog['classes']
                     for finding in group['finding_ids']]
        self.assertEqual(len(allocated), len(set(allocated)), 'duplicate finding assignment')
        self.assertEqual(set(allocated), ledger_ids, 'unclassified or invented finding IDs')
        self.assertGreaterEqual(len(catalog['classes']), 9)
        names = [group['name'] for group in catalog['classes']]
        self.assertEqual(len(names), len(set(names)), 'duplicate class name')
        for group in catalog['classes']:
            with self.subTest(failure_class=group['name']):
                self.assertTrue(group['purpose'].strip())
                self.assertTrue(group['finding_ids'])
                self.assertTrue(group['negative_controls'])
                self.assertTrue(group['positive_controls'])
                for kind in ('negative_controls', 'positive_controls'):
                    for name in group[kind]:
                        module_name, class_name, method_name = name.rsplit('.', 2)
                        module = importlib.import_module(module_name)
                        case = getattr(module, class_name)
                        self.assertTrue(issubclass(case, unittest.TestCase), name)
                        self.assertTrue(method_name.startswith('test_'), name)
                        self.assertTrue(callable(getattr(case, method_name)), name)

    def test_no_tools_can_follow_exhausted_model_budget(self):
        original=Investigation(QUESTION,
            RetrievalPolicy(('example.org','independent.example.org')),
            seeds=[URL_A,URL_B],fetcher=FixtureRetriever()
        ).run_agent(ScriptedFixtureModel(full_script()))
        self.assertTrue(audit(original)['valid'])
        state=copy.deepcopy(original)
        state['policy']['budget']['max_model_tokens']=1
        state['events'][0]['payload']['policy']['budget']['max_model_tokens']=1
        state['status']='FAILED_OR_INCOMPLETE'
        reseal(state)
        errors=audit(state)['errors']
        self.assertTrue(any('token_budget' in e for e in errors),errors)


if __name__=='__main__':
    unittest.main()
