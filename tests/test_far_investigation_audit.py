"""Hostile offline transcript controls; fixtures are not autonomy measurements."""
import base64
import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from mechanization.far_mechanization.intake_v1 import sha256_json
from tools.far_investigation_audit import audit
from tools.far_investigation_engine import Budget, EngineError, Investigation
from tools.far_investigation_retrieval import RetrievalPolicy, ToolError
from tests.test_far_investigation_engine import (
    BODY_A, BODY_B, QUESTION, URL_A, URL_B, FixtureRetriever,
    ScriptedFixtureModel, action, full_script, receipt,
)


def reseal(state):
    """Adversary can rewrite self-signed seals; internal invariants still apply."""
    seal = state['events'][-1]
    seal['payload']['state_sha256'] = sha256_json({k: v for k, v in state.items() if k != 'events'})
    previous = None
    for event in state['events']:
        event['previous_sha256'] = previous
        event['sha256'] = sha256_json({k: v for k, v in event.items() if k != 'sha256'})
        previous = event['sha256']


class OfflineInvestigationAuditTests(unittest.TestCase):
    def runtime(self, mode='agent', **kwargs):
        return Investigation(QUESTION, RetrievalPolicy(('example.org', 'independent.example.org')),
                             mode=mode, seeds=[URL_A, URL_B], fetcher=FixtureRetriever(), **kwargs)

    def complete(self, mode='agent'):
        runtime = self.runtime(mode)
        return runtime.run_agent(ScriptedFixtureModel(full_script())) if mode == 'agent' else runtime.run_workflow()

    def assert_rejected(self, state, fragment=None):
        outcome = audit(state)
        self.assertFalse(outcome['valid'], outcome)
        if fragment:
            self.assertTrue(any(fragment in e for e in outcome['errors']), outcome)

    def test_valid_agent_and_both_workflows_reconstruct_without_network_or_model(self):
        for mode in ('agent', 'deterministic', 'declarative'):
            with self.subTest(mode=mode):
                outcome = audit(self.complete(mode))
                self.assertTrue(outcome['valid'], outcome)
                self.assertEqual(outcome['reconstructed_counters']['http_reservations'], 4)
                self.assertIn('no external authenticity', outcome['assurance'])

    def test_simple_hash_chain_and_seal_mutations_are_rejected(self):
        original = self.complete()
        for mutation in ('source', 'event', 'seal', 'missing_seal'):
            state = copy.deepcopy(original)
            if mutation == 'source':
                state['sources']['src.1']['raw_base64'] = base64.b64encode(b'altered').decode()
            elif mutation == 'event':
                state['events'][1]['payload'] = {'forged': True}
            elif mutation == 'seal':
                state['events'][-1]['payload']['state_sha256'] = '0' * 64
            else:
                state['events'].pop()
            with self.subTest(mutation=mutation):
                self.assert_rejected(state)

    def test_self_consistent_seal_does_not_hide_recheck_hash_corruption(self):
        state = self.complete()
        state['rechecks'][0]['receipt']['raw_base64'] = base64.b64encode(b'forged terminal receipt').decode()
        reseal(state)
        self.assert_rejected(state, 'receipt')

    def test_self_consistent_seal_does_not_hide_model_response_or_request_hash_corruption(self):
        original = self.complete()
        for mutate_request in (False, True):
            state = copy.deepcopy(original)
            env = state['model_calls'][0]
            if mutate_request:
                env.update(request={'messages': []}, request_sha256='0' * 64)
            else:
                env['response_sha256'] = '0' * 64
            reseal(state)
            with self.subTest(request=mutate_request):
                self.assert_rejected(state, 'sha256')

    def test_source_projection_quote_offset_and_intake_source_identity_are_recomputed(self):
        original = self.complete()
        for target in ('projection', 'offset', 'source_identity'):
            state = copy.deepcopy(original)
            if target == 'projection':
                state['projections']['src.1']['text'] = 'changed projection'
            elif target == 'offset':
                state['evidence']['ev.1']['start'] += 1
            else:
                state['intake']['discovery']['sources'][0]['sha256'] = '0' * 64
            reseal(state)
            with self.subTest(target=target):
                self.assert_rejected(state)

    def test_native_result_and_outer_outcome_cannot_disagree_after_resealing(self):
        original = self.complete()
        for target in ('result', 'outcome', 'intake_evaluation', 'report_results', 'report_aggregate'):
            state = copy.deepcopy(original)
            if target == 'result':
                state['evaluations'][0]['result']['calculation']['actual'] = '999'
            elif target == 'outcome':
                state['evaluations'][0]['outcome'] = 'REFUTED'
            elif target == 'intake_evaluation':
                state['intake']['evaluations'][0]['outcome'] = 'REFUTED'
            elif target == 'report_results':
                state['report']['native_results'] = []
            else:
                state['report']['aggregate']['outcome'] = 'INVARIANTLY_PROVED'
            reseal(state)
            with self.subTest(target=target):
                self.assert_rejected(state)

    def test_model_and_actual_tool_proposals_must_match_without_substitution(self):
        original = self.complete()
        for target in ('actual', 'substitutions', 'tokens', 'http', 'rejections'):
            state = copy.deepcopy(original)
            if target == 'actual':
                event = next(e for e in state['events'] if e['kind'] == 'TOOL_PROPOSAL')
                event['payload']['args']['url'] = URL_B
            elif target == 'substitutions':
                state['controller_substitutions'] = 1
            elif target == 'tokens':
                state['model_tokens'] += 1
            elif target == 'http':
                state['http_calls'] += 1
            else:
                state['rejected_calls'] += 1
            reseal(state)
            with self.subTest(target=target):
                self.assert_rejected(state)

    def test_valid_search_receipts_and_rechecks_are_included_in_hash_audit(self):
        def searcher(query, provider, policy, checkpoint=None):
            row = receipt(URL_A, BODY_A)
            if checkpoint:
                checkpoint(copy.deepcopy(row))
            return {'query': query, 'provider': provider, 'receipt': row,
                    'hits': [{'url': URL_A, 'title': 'A source'}], 'status': 'SEARCH_COMPLETED'}
        runtime = self.runtime(searcher=searcher)
        state = runtime.run_agent(ScriptedFixtureModel([action('search', query='claim', provider='wikimedia'), *full_script()]))
        outcome = audit(state)
        self.assertTrue(outcome['valid'], outcome)
        self.assertEqual(outcome['reconstructed_counters']['http_reservations'], 6)
        state['searches'][0]['receipt']['sha256'] = '0' * 64
        reseal(state)
        self.assert_rejected(state, 'receipt')

    def test_failed_source_and_model_calls_remain_valid_auditable_failures(self):
        raw_receipt = receipt(URL_A, 'provider error')
        raw_receipt.update(status='FAILED', http_status=503)
        failed = FixtureRetriever({URL_A: ToolError('unavailable', raw_receipt)})
        runtime = Investigation(QUESTION, RetrievalPolicy(('example.org',)), fetcher=failed,
                                budget=Budget(max_steps=1))
        state = runtime.run_agent(ScriptedFixtureModel([action('retrieve', url=URL_A)]))
        self.assertTrue(audit(state)['valid'], audit(state))
        def broken_model(prompt, checkpoint):
            raw = b'incomplete model body'
            checkpoint({'response_base64': base64.b64encode(raw).decode(),
                        'response_sha256': hashlib.sha256(raw).hexdigest(), 'error': 'connection closed'})
            raise EngineError('model unavailable')
        state = self.runtime().run_agent(broken_model)
        self.assertTrue(audit(state)['valid'], audit(state))

    def test_failed_native_attempt_is_recomputed_but_never_counted_as_proof(self):
        from tools import far_investigation_engine as engine
        native = engine.verify
        calls = 0
        def interrupted(*args):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OSError('temporary verifier interruption')
            return native(*args)
        choices = full_script()
        position = next(i for i, c in enumerate(choices) if c['tool'] == 'verify')
        choices.insert(position, copy.deepcopy(choices[position]))
        with patch.object(engine, 'verify', side_effect=interrupted):
            state = self.runtime().run_agent(ScriptedFixtureModel(choices))
        outcome = audit(state)
        self.assertTrue(outcome['valid'], outcome)
        self.assertEqual(outcome['reconstructed_counters']['native_attempts_recomputed'], 2)
        self.assertEqual(outcome['reconstructed_counters']['native_failed_attempts'], 1)
        self.assertEqual(len(state['evaluations']), 1)

    def test_live_shaped_single_function_call_envelope_reconstructs_actual_arguments(self):
        class FunctionEnvelopeFixture:
            """Raw API-shape test double; no live inference is claimed."""
            def __init__(self):
                self.choices = iter(full_script())
            def __call__(self, prompt, checkpoint):
                proposal = next(self.choices)
                request = {'model': 'API_SHAPE_FIXTURE', 'messages': [{'role': 'user', 'content': prompt}]}
                response = {'model': 'API_SHAPE_FIXTURE', 'choices': [{'message': {
                    'content': None, 'tool_calls': [{'id': 'fixture-call', 'type': 'function', 'function': {
                        'name': proposal['tool'], 'arguments': json.dumps(proposal['args'])}}]}}],
                    'usage': {'total_tokens': 1}}
                raw = json.dumps(response).encode()
                env = {'request': request, 'request_sha256': hashlib.sha256(json.dumps(
                    request, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                    'response_base64': base64.b64encode(raw).decode(),
                    'response_sha256': hashlib.sha256(raw).hexdigest(), 'status': 200}
                checkpoint(env)
                return proposal, {'tokens': 1, 'model': 'API_SHAPE_FIXTURE', 'envelope': env}
        state = self.runtime().run_agent(FunctionEnvelopeFixture())
        self.assertTrue(audit(state)['valid'], audit(state))
        event = next(e for e in state['events'] if e['kind'] == 'MODEL_PROPOSAL')
        env = event['payload']['metadata']['envelope']
        response = json.loads(base64.b64decode(env['response_base64']))
        response['choices'][0]['message']['tool_calls'] *= 2
        raw = json.dumps(response).encode()
        env.update(response_base64=base64.b64encode(raw).decode(), response_sha256=hashlib.sha256(raw).hexdigest())
        reseal(state)
        self.assert_rejected(state)

    def test_repeated_nonadvancing_success_is_rejected_without_duplicate_retrieval(self):
        fetcher = FixtureRetriever()
        runtime = Investigation(QUESTION, RetrievalPolicy(('example.org', 'independent.example.org')),
                                fetcher=fetcher)
        choices = full_script()
        choices.insert(1, copy.deepcopy(choices[0]))
        state = runtime.run_agent(ScriptedFixtureModel(choices))
        self.assertEqual(state['status'], 'BOUNDED_PIPELINE_COMPLETED')
        self.assertEqual(state['rejected_calls'], 1)
        self.assertEqual(state['controller_substitutions'], 0)
        self.assertEqual(state['http_calls'], 4)
        self.assertEqual(fetcher.calls, [URL_A, URL_B, URL_A, URL_B])
        rejections = [e for e in state['events'] if e['kind'] == 'TOOL_REJECTED']
        self.assertIn('nonadvancing', rejections[0]['payload']['reason'])
        self.assertTrue(audit(state)['valid'], audit(state))

    def test_malformed_inputs_return_errors_without_crashing(self):
        malformed = [None, [], {}, {'schema': 'far-investigation-engine/0.1'},
                     {'schema': 'far-investigation-engine/0.1', 'events': [None]}]
        cyclic = {'schema': 'far-investigation-engine/0.1'}
        cyclic['cycle'] = cyclic
        malformed.append(cyclic)
        for value in malformed:
            with self.subTest(value=type(value).__name__):
                self.assert_rejected(value)


if __name__ == '__main__':
    unittest.main()
