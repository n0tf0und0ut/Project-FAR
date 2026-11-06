"""Replays of native length and model-budget failure cases."""
import copy
import unittest
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
