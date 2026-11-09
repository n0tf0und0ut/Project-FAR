"""Hostile offline transcript controls; fixtures are not autonomy measurements."""
import base64
import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from mechanization.far_mechanization.intake_v1 import sha256_json
from tools.far_investigation_audit import audit
from tools.far_investigation_engine import Budget, CheckpointPersistenceError, EngineError, Investigation
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


class NativeFunctionFixtureModel(ScriptedFixtureModel):
    """Native response shape only; explicit scripted fixture, no inference."""
    def __call__(self, prompt, checkpoint):
        proposal = next(self.actions)
        response = {'model': 'NATIVE_FUNCTION_FIXTURE', 'usage': {'total_tokens': 1},
            'choices': [{'message': {'tool_calls': [{'function': {
                'name': proposal['tool'], 'arguments': json.dumps(proposal['args'])}}]}}]}
        raw = json.dumps(response).encode()
        envelope = {'response_base64': base64.b64encode(raw).decode(),
                    'response_sha256': hashlib.sha256(raw).hexdigest(), 'status': 200}
        checkpoint(envelope)
        return proposal, {'tokens': 1, 'model': response['model'], 'envelope': envelope}


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

    def test_baseline_mode_cannot_claim_agent_selected_verification_plans(self):
        agent = self.runtime().run_agent(NativeFunctionFixtureModel(full_script()))
        self.assertEqual(agent['status'], 'BOUNDED_PIPELINE_COMPLETED')
        self.assertTrue(audit(agent)['valid'], audit(agent))
        for mode in ('deterministic', 'declarative'):
            with self.subTest(mode=mode):
                forged = copy.deepcopy(agent)
                forged['mode'] = mode
                forged['model_calls'] = []
                forged['model_tokens'] = 0
                forged['events'] = [e for e in forged['events']
                    if e['kind'] not in ('MODEL_OBSERVATION', 'MODEL_PROPOSAL')]
                forged['events'].insert(1, {
                    'sequence': 2, 'at': forged['events'][0]['at'],
                    'kind': 'DETERMINISTIC_PLAN' if mode == 'deterministic' else 'DECLARATIVE_PLAN',
                    'payload': [action('retrieve', url=URL_A), action('retrieve', url=URL_B)],
                    'previous_sha256': None, 'sha256': None})
                for index, event in enumerate(forged['events'], 1):
                    event['sequence'] = index
                reseal(forged)
                self.assert_rejected(forged, 'workflow.proposals')

    def test_baseline_plan_and_failed_fixed_prefix_are_enforced(self):
        for mode in ('deterministic', 'declarative'):
            with self.subTest(mode=mode):
                state = self.complete(mode)
                self.assertTrue(audit(state)['valid'], audit(state))
                forged = copy.deepcopy(state)
                plan = next(e for e in forged['events'] if e['kind'].endswith('_PLAN'))
                plan['payload'][0]['args']['url'] = URL_B
                reseal(forged)
                self.assert_rejected(forged, 'workflow.plan')
                limited = self.runtime(mode=mode, budget=Budget(max_steps=1)).run_workflow()
                self.assertEqual(limited['status'], 'FAILED_OR_INCOMPLETE')
                self.assertTrue(audit(limited)['valid'], audit(limited))

    def test_baseline_keeps_retained_extraction_ids_after_checkpoint_rejection(self):
        from tests.test_far_investigation_retrieval import Response, dns
        from tools.far_investigation_retrieval import retrieve

        def fetch(url, policy, checkpoint):
            client = unittest.mock.Mock()
            client.open.return_value = Response(
                (BODY_A if url == URL_A else BODY_B).encode(), url=url)
            return retrieve(url, policy, checkpoint=checkpoint, opener=client)

        for mode in ('deterministic', 'declarative'):
            rejected = [False]
            def checkpoint(state):
                event = state['events'][-1]
                if (not rejected[0] and event['kind'] == 'TOOL_PROPOSAL'
                        and event['payload']['tool'] == 'extract'):
                    rejected[0] = True
                    raise OSError('one controlled extract proposal checkpoint failure')

            with self.subTest(mode=mode):
                runtime = Investigation(QUESTION,
                    RetrievalPolicy(('example.org', 'independent.example.org'), resolver=dns),
                    mode=mode, seeds=[URL_A, URL_B], fetcher=fetch, checkpoint=checkpoint)
                state = runtime.run_workflow()
                self.assertTrue(rejected[0])
                self.assertEqual(state['status'], 'BOUNDED_PIPELINE_COMPLETED')
                self.assertEqual(state['rejected_calls'], 1)
                self.assertEqual(list(state['evidence']), ['ev.1'])
                self.assertEqual(state['comparisons'][0]['evidence_ids'], ['ev.1'])
                self.assertTrue(audit(state)['valid'], audit(state))

    def test_changed_source_baseline_keeps_draft_verify_and_finish_attempts(self):
        from tests.test_far_investigation_retrieval import Response, dns
        from tools.far_investigation_retrieval import retrieve

        for mode in ('deterministic', 'declarative'):
            requested = {}
            def fetch(url, policy, checkpoint):
                count = requested.get(url, 0)
                requested[url] = count + 1
                body = BODY_A if url == URL_A else BODY_B
                if url == URL_A and count:
                    body += ' Source changed on the terminal recheck.'
                client = unittest.mock.Mock()
                client.open.return_value = Response(body.encode(), url=url)
                return retrieve(url, policy, checkpoint=checkpoint, opener=client)

            with self.subTest(mode=mode):
                state = Investigation(QUESTION,
                    RetrievalPolicy(('example.org', 'independent.example.org'), resolver=dns),
                    mode=mode, seeds=[URL_A, URL_B], fetcher=fetch).run_workflow()
                self.assertEqual(state['status'], 'FAILED_OR_INCOMPLETE')
                self.assertEqual(state['intake']['freeze']['status'], 'DRAFT')
                proposals = [e['payload']['tool'] for e in state['events']
                             if e['kind'] == 'TOOL_PROPOSAL']
                self.assertIn('verify', proposals)
                self.assertIn('finish', proposals)
                self.assertGreaterEqual(state['rejected_calls'], 4)
                self.assertTrue(audit(state)['valid'], audit(state))

    def test_native_success_rejects_resealed_nonpublic_preflight_addresses(self):
        from tests.test_far_investigation_retrieval import Response, dns
        from tools.far_investigation_retrieval import retrieve

        def fetch(url, policy, checkpoint):
            client = unittest.mock.Mock()
            client.open.return_value = Response(
                (BODY_A if url == URL_A else BODY_B).encode(), url=url)
            return retrieve(url, policy, checkpoint=checkpoint, opener=client)

        original = Investigation(QUESTION,
            RetrievalPolicy(('example.org', 'independent.example.org'), resolver=dns),
            mode='deterministic', seeds=[URL_A, URL_B], fetcher=fetch).run_workflow()
        self.assertTrue(audit(original)['valid'], audit(original))
        for field, value in (('addresses', ['127.0.0.1']),
                             ('addresses', ['93.184.216.34', '169.254.169.254']),
                             ('addresses', []), ('dns_mode', 'proxy'),
                             ('host', 'unregistered.example.org')):
            state = copy.deepcopy(original)
            changed = [0]
            def rewrite(node):
                if isinstance(node, dict):
                    if node.get('schema') == 'far-source-receipt/0.1' and 'destination' in node:
                        node['destination'][field] = value
                        changed[0] += 1
                    for child in node.values():
                        rewrite(child)
                elif isinstance(node, list):
                    for child in node:
                        rewrite(child)
            rewrite(state)
            self.assertGreater(changed[0], 0)
            reseal(state)
            with self.subTest(field=field, value=value):
                self.assert_rejected(state, 'destination')

    def test_native_json_document_envelope_lookalikes_are_untrusted_data(self):
        from tests.test_far_investigation_retrieval import Response, dns
        from tools.far_investigation_retrieval import retrieve

        body = json.dumps({'timing_scope': 'domain-defined interval',
            'requested_at': 'not a transport timestamp',
            'received_at': 'unrelated to any HTTP event',
            'raw_base64': 'not base64', 'sha256': 'not a digest',
            'observed_bytes': 7, 'request_sha256': 'not a request checksum',
            'nested': {'timing_scope': 'geological epoch', 'assertion': BODY_A}})
        def fetch(url, policy, checkpoint):
            client = unittest.mock.Mock()
            raw = body if url == URL_A else BODY_B
            kind = 'application/json' if url == URL_A else 'text/plain'
            client.open.return_value = Response(raw.encode(), kind=kind, url=url)
            return retrieve(url, policy, checkpoint=checkpoint, opener=client)

        for mode in ('agent', 'deterministic', 'declarative'):
            with self.subTest(mode=mode):
                runtime = Investigation(QUESTION,
                    RetrievalPolicy(('example.org', 'independent.example.org'), resolver=dns),
                    mode=mode, seeds=[URL_A, URL_B], fetcher=fetch)
                state = (runtime.run_agent(NativeFunctionFixtureModel(full_script()))
                         if mode == 'agent' else runtime.run_workflow())
                self.assertEqual(state['status'], 'BOUNDED_PIPELINE_COMPLETED')
                self.assertEqual(state['projections']['src.1']['document']['timing_scope'],
                                 'domain-defined interval')
                self.assertTrue(audit(state)['valid'], audit(state))

    def test_native_model_transport_is_bound_to_local_post_even_on_failure(self):
        from tools.far_investigation_engine import LocalModel
        from tests.test_far_investigation_usage import envelope
        response = {'model': 'CONTROLLED_FIXTURE', 'usage': {'total_tokens': 10},
                    'choices': [{'message': None}]}
        native = envelope(response)
        native['transport'].update(
            request_url='http://127.0.0.1:8085/v1/chat/completions',
            request_method='POST',
            response_url='http://127.0.0.1:8085/v1/chat/completions')
        raw = base64.b64decode(native['response_base64'])
        with patch('tools.far_investigation_engine.read_bounded_response',
                   return_value=(raw, native['transport'])):
            original = self.runtime(budget=Budget(max_steps=1)).run_agent(LocalModel())
        self.assertEqual(original['status'], 'FAILED_OR_INCOMPLETE')
        self.assertTrue(audit(original)['valid'], audit(original))
        for method, url in (
                ('GET', 'http://127.0.0.1:8085/v1/chat/completions'),
                ('POST', 'https://remote.example/chat')):
            state = copy.deepcopy(original)
            touched = [0]
            def rewrite(node):
                if isinstance(node, dict):
                    if (isinstance(node.get('transport'), dict)
                            and 'request_url' in node['transport']):
                        t = node['transport']
                        t['request_method'] = method
                        t['request_url'] = url
                        t['response_url'] = url
                        touched[0] += 1
                    for child in node.values():
                        rewrite(child)
                elif isinstance(node, list):
                    for child in node:
                        rewrite(child)
            rewrite(state)
            self.assertGreater(touched[0], 0)
            reseal(state)
            with self.subTest(method=method, url=url):
                self.assert_rejected(state, 'model_calls[0].transport')

    def test_model_pre_response_transport_failure_has_no_invented_response_url(self):
        from tools.far_investigation_engine import LocalModel
        from tools.far_uncertain_routing_pilot import ResponseTransportError
        endpoint = 'http://127.0.0.1:8085/v1/chat/completions'
        transport = {
            'request_url': endpoint, 'request_method': 'POST', 'http_status': None,
            'response_complete': False, 'response_truncated': False,
            'response_hash_scope': 'retained_prefix',
            'raw_response_base64': '',
            'response_sha256': hashlib.sha256(b'').hexdigest(),
            'response_bytes_retained': 0, 'transport_error': 'URLError',
            'requested_at': '2026-11-09T18:00:00Z',
            'received_at': '2026-11-09T18:00:01Z',
            'timing_scope': 'request_start_to_body_read_or_transport_failure'
        }
        with patch('tools.far_investigation_engine.read_bounded_response',
                   side_effect=ResponseTransportError('network unavailable', transport)):
            state = self.runtime(budget=Budget(max_steps=1)).run_agent(LocalModel())
        self.assertEqual(state['status'], 'FAILED_OR_INCOMPLETE')
        self.assertEqual(state['http_calls'], 0)
        self.assertTrue(audit(state)['valid'], audit(state))

    def test_rejected_extra_model_argument_named_request_sha256_is_source_data(self):
        # The invalid model tool argument must be rejected by dispatch rather
        # than misinterpreted as a journal request checksum.
        choices = [action('retrieve', url=URL_A, request_sha256='not-a-hash'),
                   *full_script()]
        state = self.runtime().run_agent(NativeFunctionFixtureModel(choices))
        self.assertEqual(state['status'], 'BOUNDED_PIPELINE_COMPLETED')
        self.assertEqual(state['rejected_calls'], 1)
        self.assertTrue(audit(state)['valid'], audit(state))

    def test_native_failed_retrieve_receipt_requires_its_http_reservation(self):
        from tests.test_far_investigation_retrieval import Response, dns
        from tools.far_investigation_retrieval import retrieve
        attempts = {}
        def fetch(url, policy, checkpoint):
            count = attempts.get(url, 0)
            attempts[url] = count + 1
            client = unittest.mock.Mock()
            status = 500 if url == URL_A and count == 0 else 200
            client.open.return_value = Response(
                (BODY_A if url == URL_A else BODY_B).encode(),
                status=status, url=url)
            return retrieve(url, policy, checkpoint=checkpoint, opener=client)

        state = Investigation(QUESTION,
            RetrievalPolicy(('example.org', 'independent.example.org'), resolver=dns),
            seeds=[URL_A, URL_B], fetcher=fetch).run_agent(
                NativeFunctionFixtureModel([action('retrieve', url=URL_A), *full_script()]))
        self.assertEqual(state['status'], 'BOUNDED_PIPELINE_COMPLETED')
        self.assertEqual(state['rejected_calls'], 1)
        self.assertEqual(state['http_calls'], 5)
        self.assertTrue(audit(state)['valid'], audit(state))
        forged = copy.deepcopy(state)
        events = forged['events']
        rejected_index = next(i for i, e in enumerate(events)
            if e['kind'] == 'TOOL_REJECTED' and
            isinstance(e['payload'].get('receipt'), dict) and
            e['payload']['receipt'].get('schema') == 'far-source-receipt/0.1')
        # A bounded native reader emits progressive HTTP_OBSERVATION
        # checkpoints. Remove its one reservation and *all* corresponding
        # progressive/final observations, not just a single observation.
        start = max(i for i, e in enumerate(events[:rejected_index])
                    if e['kind'] == 'TOOL_PROPOSAL')
        prior = [i for i in range(start, rejected_index)
                 if events[i]['kind'] in ('HTTP_REQUEST', 'HTTP_OBSERVATION')]
        self.assertEqual(sum(events[i]['kind'] == 'HTTP_REQUEST' for i in prior), 1)
        self.assertGreaterEqual(
            sum(events[i]['kind'] == 'HTTP_OBSERVATION' for i in prior), 1)
        forged['events'] = [e for i, e in enumerate(events) if i not in prior]
        forged['http_calls'] -= 1
        for i, e in enumerate(forged['events'], 1):
            e['sequence'] = i
            if e['kind'] in ('HTTP_REQUEST', 'SEARCH_REQUEST'):
                e['payload']['call'] -= 1
        reseal(forged)
        self.assert_rejected(forged, 'failed_retrieve.reservation')

    def test_resealed_new_transport_timestamps_cannot_move_backwards(self):
        from tests.test_far_investigation_retrieval import Response, dns
        from tools.far_investigation_retrieval import retrieve
        def fetch(url, policy, checkpoint):
            client = unittest.mock.Mock()
            client.open.return_value = Response(
                (BODY_A if url == URL_A else BODY_B).encode(), url=url)
            return retrieve(url, policy, checkpoint=checkpoint, opener=client)
        state = Investigation(QUESTION,
            RetrievalPolicy(('example.org', 'independent.example.org'), resolver=dns),
            mode='deterministic', seeds=[URL_A, URL_B], fetcher=fetch).run_workflow()
        self.assertTrue(audit(state)['valid'], audit(state))
        altered = [0]
        def rewrite(node):
            if isinstance(node, dict):
                if (node.get('schema') == 'far-source-receipt/0.1'
                        and isinstance(node.get('transport'), dict)):
                    node['transport']['timing_scope'] = 'request_start_to_body_read_or_transport_failure'
                    node['transport']['requested_at'] = '2026-11-03T01:00:01Z'
                    node['transport']['received_at'] = '2026-11-03T01:00:00Z'
                    altered[0] += 1
                for child in node.values():
                    rewrite(child)
            elif isinstance(node, list):
                for child in node:
                    rewrite(child)
        rewrite(state)
        self.assertGreater(altered[0], 0)
        reseal(state)
        self.assert_rejected(state, 'transport_time')

    def test_native_source_transport_cannot_claim_post_instead_of_get(self):
        from tests.test_far_investigation_retrieval import Response, dns
        from tools.far_investigation_retrieval import retrieve

        def fetch(url, policy, checkpoint):
            client = unittest.mock.Mock()
            client.open.return_value = Response(
                (BODY_A if url == URL_A else BODY_B).encode(), url=url)
            return retrieve(url, policy, checkpoint=checkpoint, opener=client)

        state = Investigation(QUESTION,
            RetrievalPolicy(('example.org', 'independent.example.org'), resolver=dns),
            mode='deterministic', seeds=[URL_A, URL_B], fetcher=fetch).run_workflow()
        self.assertTrue(audit(state)['valid'], audit(state))
        changed = [0]
        def mutate(node):
            if isinstance(node, dict):
                if (node.get('schema') == 'far-source-receipt/0.1'
                        and isinstance(node.get('transport'), dict)):
                    node['transport']['request_method'] = 'POST'
                    changed[0] += 1
                for child in node.values():
                    mutate(child)
            elif isinstance(node, list):
                for child in node:
                    mutate(child)
        mutate(state)
        self.assertGreater(changed[0], 0)
        reseal(state)
        self.assert_rejected(state, 'request_method')

    def test_verifier_observed_json_objects_do_not_become_transport_metadata(self):
        from tests.test_far_investigation_retrieval import Response, dns
        from tools.far_investigation_retrieval import retrieve

        raw = json.dumps({'statement': '2 + 2 = 4',
            'value': {'timing_scope': 'domain-specific interval',
                      'requested_at': 'not a transport timestamp',
                      'raw_response_base64': 'not-a-transport-envelope',
                      'request_sha256': 'not-a-hash'}}).encode()
        def fetch(url, policy, checkpoint):
            client = unittest.mock.Mock()
            body = raw if url == URL_A else BODY_B.encode()
            kind = 'application/json' if url == URL_A else 'text/plain'
            client.open.return_value = Response(body, kind=kind, url=url)
            return retrieve(url, policy, checkpoint=checkpoint, opener=client)

        claims = [{'statement': 'Declared source value equals 4',
            'type': 'quantitative', 'interpretations': [{
                'statement': 'The pointed value should be exactly 4',
                'evidence_ids': ['ev.1'],
                'plan': {'kind': 'source_json', 'source_id': 'src.1',
                    'pointer': '/value', 'operator': 'eq',
                    'expected': 4, 'expected_quote': '4'}}]}]
        state = Investigation(QUESTION,
            RetrievalPolicy(('example.org', 'independent.example.org'), resolver=dns),
            seeds=[URL_A, URL_B], fetcher=fetch).run_agent(
                NativeFunctionFixtureModel(full_script(claims)))
        self.assertEqual(state['status'], 'BOUNDED_PIPELINE_COMPLETED')
        self.assertEqual(state['evaluations'][0]['outcome'], 'REFUTED')
        self.assertEqual(state['evaluations'][0]['result']['projection']['observed']['timing_scope'],
                         'domain-specific interval')
        self.assertTrue(audit(state)['valid'], audit(state))

    def test_failed_model_attempts_still_consume_agent_step_budget(self):
        from tests.test_far_investigation_usage import envelope
        from tools.far_investigation_engine import LocalModel

        response1 = {'model': 'CONTROLLED_FIXTURE',
            'usage': {'total_tokens': 10}, 'choices': [{
                'message': {'tool_calls': [{'function': {
                    'name': 'inspect', 'arguments': '{"source_id":"absent"}'}}]}}]}
        response2 = {'model': 'CONTROLLED_FIXTURE',
            'usage': {'total_tokens': 11}, 'choices': [{'message': None}]}
        values = [envelope(response1), envelope(response2)]
        pairs = [(base64.b64decode(v['response_base64']), v['transport']) for v in values]
        with patch('tools.far_investigation_engine.read_bounded_response',
                   side_effect=pairs) as reader:
            state = self.runtime(budget=Budget(max_steps=2)).run_agent(LocalModel())
        self.assertEqual(reader.call_count, 2)
        self.assertEqual(state['status'], 'FAILED_OR_INCOMPLETE')
        self.assertEqual(len(state['model_calls']), 2)
        self.assertEqual(state['model_tokens'], 21)
        self.assertTrue(audit(state)['valid'], audit(state))

        forged = copy.deepcopy(state)
        forged['policy']['budget']['max_steps'] = 1
        forged['events'][0]['payload']['policy']['budget']['max_steps'] = 1
        reseal(forged)
        self.assert_rejected(forged, 'budget.model_attempts')

    def test_resealed_orphan_source_is_rejected_even_without_intake(self):
        runtime = self.runtime(budget=Budget(max_steps=1))
        state = runtime.run_agent(ScriptedFixtureModel([action('inspect', source_id='absent')]))
        self.assertTrue(audit(state)['valid'], audit(state))
        state['sources']['src.1'] = receipt(URL_A, 'orphan retained')
        reseal(state)
        self.assert_rejected(state, 'transport observation')

    def test_parse_failure_source_requires_its_exact_retrieval_observation(self):
        runtime = Investigation(QUESTION, RetrievalPolicy(('example.org',)),
            fetcher=FixtureRetriever({URL_A: ('{"broken":', 'application/json')}),
            budget=Budget(max_steps=1))
        original = runtime.run_agent(ScriptedFixtureModel([action('retrieve', url=URL_A)]))
        self.assertIn('src.1', original['sources'])
        self.assertNotIn('src.1', original['projections'])
        self.assertTrue(audit(original)['valid'], audit(original))
        for mutation in ('remove_observation', 'change_source', 'change_request'):
            state = copy.deepcopy(original)
            if mutation == 'remove_observation':
                state['events'] = [e for e in state['events'] if e['kind'] != 'HTTP_OBSERVATION']
            elif mutation == 'change_source':
                state['sources']['src.1'] = receipt(URL_A, '{"different":', 'application/json')
            else:
                event = next(e for e in state['events'] if e['kind'] == 'HTTP_REQUEST')
                event['payload']['url'] = URL_B
            for index, event in enumerate(state['events'], 1):
                event['sequence'] = index
            reseal(state)
            with self.subTest(mutation=mutation):
                self.assert_rejected(state, 'transport observation')

    def test_resealed_extraction_copies_cannot_override_requested_arguments(self):
        original = self.complete()
        for field, value in (('relation', 'CONTRADICT'), ('claim', 'Different claim'),
                             ('source_id', 'src.2')):
            state = copy.deepcopy(original)
            state['evidence']['ev.1'][field] = value
            result = next(e['payload']['result'] for e in state['events']
                          if e['kind'] == 'TOOL_RESULT' and e['payload']['tool'] == 'extract')
            result[field] = value
            reseal(state)
            with self.subTest(field=field):
                self.assert_rejected(state, 'extract')

    def test_resealed_comparison_copies_are_reconstructed_from_the_proposal(self):
        from tools.far_investigation_campaign import metrics
        original = self.complete()
        self.assertEqual(metrics(original)['analyst_declared_conflicts'], 1)
        mutations = {'asserted_conflict': False, 'publisher_host_groups': {'forged.example.org': ['src.1', 'src.2']},
            'alternatives': ['A fabricated alternative'], 'evidence_ids': ['ev.1'],
            'independence': 'ESTABLISHED', 'conflict_assurance': 'mechanically proved'}
        for field, value in mutations.items():
            state = copy.deepcopy(original)
            state['comparisons'][0][field] = copy.deepcopy(value)
            result = next(e['payload']['result'] for e in state['events']
                if e['kind'] == 'TOOL_RESULT' and e['payload']['tool'] == 'compare')
            result[field] = copy.deepcopy(value)
            reseal(state)
            with self.subTest(field=field):
                self.assert_rejected(state, 'compare')

    def test_discovery_request_cannot_silently_select_a_different_native_contract(self):
        state = self.complete()
        for event in state['events']:
            if event['kind'] in ('MODEL_PROPOSAL', 'TOOL_PROPOSAL'):
                proposal = event['payload'].get('proposal', event['payload'])
                if proposal.get('tool') == 'discover':
                    proposal['args']['claims'][0]['interpretations'][0]['plan']['expected'] = '2'
        # Keep every retained fixture response consistent with the changed
        # proposal; only the downstream produced discovery is left substituted.
        def change(node):
            if isinstance(node, dict):
                if node.get('fixture') and node.get('response_base64'):
                    proposal = json.loads(base64.b64decode(node['response_base64']))
                    if proposal.get('tool') == 'discover':
                        proposal['args']['claims'][0]['interpretations'][0]['plan']['expected'] = '2'
                        raw = json.dumps(proposal, sort_keys=True).encode()
                        node.update(response_base64=base64.b64encode(raw).decode(), response_sha256=hashlib.sha256(raw).hexdigest())
                for child in node.values():
                    change(child)
            elif isinstance(node, list):
                for child in node:
                    change(child)
        change(state)
        reseal(state)
        self.assert_rejected(state, 'discover')

    def test_source_recheck_must_consume_its_exact_http_observation(self):
        state = self.complete()
        rechecking = False
        for event in state['events']:
            if event['kind'] == 'TOOL_PROPOSAL':
                rechecking = event['payload']['tool'] == 'recheck'
            if rechecking and event['kind'] == 'HTTP_OBSERVATION':
                event['payload'] = receipt(event['payload']['request']['url'], 'Changed terminal text')
        reseal(state)
        self.assert_rejected(state, 'recheck')

    def test_valid_finish_changes_follow_args_and_unproduced_reports_are_rejected(self):
        script = full_script()
        script[-1]['args'].update(notes='Different bounded analyst narrative', next_evidence=[])
        state = self.runtime().run_agent(ScriptedFixtureModel(script))
        self.assertTrue(audit(state)['valid'], audit(state))
        self.assertEqual(state['report']['analyst_notes'], script[-1]['args']['notes'])
        failed = self.runtime(budget=Budget(max_steps=len(script)-1)).run_agent(ScriptedFixtureModel(script[:-1]))
        self.assertTrue(audit(failed)['valid'], audit(failed))
        failed['report'] = copy.deepcopy(state['report'])
        failed['report']['native_results'] = copy.deepcopy(failed['evaluations'])
        reseal(failed)
        self.assert_rejected(failed, 'finish.coverage')

    def test_native_search_results_and_recheck_receipts_have_exact_producers(self):
        from tools.far_investigation_retrieval import project_public_search, public_search_url
        def searcher(query, provider, policy, checkpoint):
            row = receipt(public_search_url(query, provider), json.dumps({'message': {'items': [
                {'URL': 'https://example.org/article', 'title': ['Actual metadata title']}]}}), 'application/json')
            checkpoint(copy.deepcopy(row))
            return project_public_search(query, provider, row)
        original = Investigation(QUESTION, RetrievalPolicy(('example.org', 'independent.example.org', 'api.crossref.org')),
            fetcher=FixtureRetriever(), searcher=searcher).run_agent(ScriptedFixtureModel([
                action('search', query='bounded claim', provider='crossref'), *full_script()]))
        self.assertTrue(audit(original)['valid'], audit(original))
        for target in ('projection_copies', 'recheck_observation', 'orphan_search', 'proposal_query'):
            state = copy.deepcopy(original)
            if target == 'projection_copies':
                def forge(node):
                    if isinstance(node, dict):
                        if node.get('title') == 'Actual metadata title':
                            node['title'] = 'Fabricated metadata title'
                        for child in node.values():
                            forge(child)
                    elif isinstance(node, list):
                        for child in node:
                            forge(child)
                forge(state)
            elif target == 'recheck_observation':
                event = next(e for e in state['events'] if e['kind'] == 'SEARCH_RECHECK_OBSERVATION')
                event['payload'] = receipt(event['payload']['request']['url'], '{"message":{"items":[]}}', 'application/json')
            elif target == 'orphan_search':
                state['searches'].append(copy.deepcopy(state['searches'][0]))
            else:
                event = next(e for e in state['events'] if e['kind'] == 'SEARCH_REQUEST')
                event['payload']['query'] = 'Different requested query'
            reseal(state)
            with self.subTest(target=target):
                self.assert_rejected(state, 'search')

    def test_shared_discovery_and_native_records_survive_canonical_object_sorting(self):
        script = full_script()
        script[5:5] = [action('extract', source_id='src.1', quote='2 + 2 = 4', relation='context',
                             claim='Distinct context ' + str(i)) for i in range(10)]
        # Nested plan object key order differs from canonical JSON; provenance
        # rows retain their original path enumeration order in the archive.
        state = self.runtime().run_agent(ScriptedFixtureModel(script))
        self.assertEqual(len(state['evidence']), 12)
        self.assertTrue(audit(state)['valid'], audit(state))
        restored = json.loads(json.dumps(state, sort_keys=True))
        self.assertTrue(audit(restored)['valid'], audit(restored))

    def test_early_discovery_and_freeze_rejections_can_be_corrected_later(self):
        script = full_script()
        for position, early in ((0, next(p for p in script if p['tool'] == 'discover')),
                                (6, action('freeze'))):
            choices = copy.deepcopy(script)
            choices.insert(position, copy.deepcopy(early))
            with self.subTest(tool=early['tool']):
                state = self.runtime().run_agent(ScriptedFixtureModel(choices))
                self.assertEqual(state['status'], 'BOUNDED_PIPELINE_COMPLETED')
                self.assertEqual(state['rejected_calls'], 1)
                self.assertTrue(audit(state)['valid'], audit(state))

    def test_inspection_reconstruction_preserves_runtime_scalar_guards(self):
        script = full_script()
        script.insert(2, action('inspect', source_id='src.1', start=1))
        state = self.runtime().run_agent(ScriptedFixtureModel(script))
        def mutate(node):
            if isinstance(node, dict):
                if node.get('tool') == 'inspect' and 'args' in node:
                    node['args']['start'] = True
                if node.get('fixture') and node.get('response_base64'):
                    proposal = json.loads(base64.b64decode(node['response_base64']))
                    if proposal.get('tool') == 'inspect':
                        proposal['args']['start'] = True
                        raw = json.dumps(proposal, sort_keys=True).encode()
                        node.update(response_base64=base64.b64encode(raw).decode(), response_sha256=hashlib.sha256(raw).hexdigest())
                if node.get('source_id') == 'src.1' and node.get('start') == 1 and 'source_length' in node:
                    node['start'] = True
                for child in node.values():
                    mutate(child)
            elif isinstance(node, list):
                for child in node:
                    mutate(child)
        mutate(state)
        reseal(state)
        self.assert_rejected(state, 'proposal')

    def test_failed_recheck_clears_the_previous_stability_pass_without_new_record(self):
        first = receipt(URL_A, BODY_A)
        def fetch(url, policy, checkpoint):
            if url == URL_A and fetch.count >= 2:
                row = receipt(url, '{"broken":', 'application/json')
            else:
                row = receipt(url, BODY_A if url == URL_A else BODY_B)
            if url == URL_A:
                fetch.count += 1
            checkpoint(copy.deepcopy(row))
            return row
        fetch.count = 0
        script = full_script()[:7] + [action('recheck')]
        state = Investigation(QUESTION, RetrievalPolicy(('example.org', 'independent.example.org')),
            fetcher=fetch, budget=Budget(max_steps=len(script))).run_agent(ScriptedFixtureModel(script))
        self.assertEqual(state['rechecks'], [])
        self.assertEqual(state['rejected_calls'], 1)
        self.assertTrue(audit(state)['valid'], audit(state))

    def test_identical_failed_search_observation_cannot_consume_a_later_retry(self):
        fixed = receipt(URL_A, BODY_A)
        count = 0
        def searcher(query, provider, policy, checkpoint):
            nonlocal count
            count += 1
            checkpoint(copy.deepcopy(fixed))
            if count == 1:
                raise ToolError('temporary adapter parse failure', fixed)
            return {'query': query, 'provider': provider, 'receipt': copy.deepcopy(fixed),
                    'hits': [], 'status': 'SEARCH_COMPLETED'}
        choices = [action('search', query='claim', provider='wikimedia')] * 2 + full_script()
        state = self.runtime(searcher=searcher).run_agent(ScriptedFixtureModel(choices))
        self.assertEqual(state['status'], 'BOUNDED_PIPELINE_COMPLETED')
        self.assertEqual(state['rejected_calls'], 1)
        self.assertEqual(len(state['searches']), 1)
        self.assertTrue(audit(state)['valid'], audit(state))

    def test_projection_inventory_has_exact_source_producers(self):
        original = self.complete()
        for target in ('orphan', 'missing'):
            state = copy.deepcopy(original)
            if target == 'orphan':
                state['projections']['src.orphan'] = copy.deepcopy(state['projections']['src.1'])
            else:
                del state['projections']['src.1']
            reseal(state)
            with self.subTest(target=target):
                self.assert_rejected(state, 'projections.coverage')

    def test_finish_cannot_borrow_native_evaluations_from_later_attempts(self):
        state = self.complete()
        events = state['events']
        def segment(tool):
            proposal = next(i for i, e in enumerate(events)
                if e['kind'] == 'TOOL_PROPOSAL' and e['payload']['tool'] == tool)
            start = max(i for i in range(proposal) if events[i]['kind'] == 'TOOL_RESULT') + 1
            end = next(i for i in range(proposal, len(events)) if events[i]['kind'] == 'TOOL_RESULT') + 1
            return start, end
        verify_start, _ = segment('verify')
        finish_start, finish_end = segment('finish')
        state['events'] = [*events[:verify_start], *events[finish_start:finish_end],
                           *events[verify_start:finish_start], *events[finish_end:]]
        state['model_calls'] = [copy.deepcopy(e['payload']['metadata']['envelope']) for e in state['events']
                                if e['kind'] == 'MODEL_PROPOSAL']
        stamp = events[-1]['at']
        def retime(node):
            if isinstance(node, dict):
                if 'evaluated_at' in node:
                    node['evaluated_at'] = stamp
                for child in node.values():
                    retime(child)
            elif isinstance(node, list):
                for child in node:
                    retime(child)
        retime(state)
        for index, event in enumerate(state['events'], 1):
            event['sequence'], event['at'] = index, stamp
        reseal(state)
        self.assert_rejected(state, 'finish')

    def test_source_checkpoint_failure_before_parse_retains_no_projection(self):
        raised = False
        def checkpoint(state):
            nonlocal raised
            if state['sources'] and not state['projections'] and not raised:
                raised = True
                raise OSError('one-time checkpoint persistence failure before parse')
        state = self.runtime(checkpoint=checkpoint, budget=Budget(max_steps=1)).run_agent(
            ScriptedFixtureModel([action('retrieve', url=URL_A)]))
        self.assertEqual(state['status'], 'FAILED_OR_INCOMPLETE')
        self.assertEqual(len(state['sources']), 1)
        self.assertEqual(state['projections'], {})
        self.assertTrue(audit(state)['valid'], audit(state))

    def test_transient_tool_result_checkpoint_failure_keeps_one_accepted_outcome(self):
        failed = False
        persisted = []
        def checkpoint(state):
            nonlocal failed
            if not failed and state['events'][-1]['kind'] == 'TOOL_RESULT':
                failed = True
                raise OSError('one-time accepted-result checkpoint failure')
            persisted.append(state)
        state = self.runtime(checkpoint=checkpoint).run_agent(NativeFunctionFixtureModel(full_script()))
        self.assertTrue(failed)
        self.assertEqual(state['status'], 'BOUNDED_PIPELINE_COMPLETED')
        self.assertEqual(state['rejected_calls'], 0)
        self.assertEqual(sum(e['kind'] == 'TOOL_PROPOSAL' for e in state['events']),
                         sum(e['kind'] == 'TOOL_RESULT' for e in state['events']))
        self.assertFalse(any(e['kind'] == 'TOOL_REJECTED' for e in state['events']))
        self.assertTrue(any(e['events'][-1]['kind'] == 'TOOL_RESULT' for e in persisted))
        self.assertTrue(audit(state)['valid'], audit(state))

    def test_persistent_tool_result_checkpoint_failure_cannot_claim_completion(self):
        def checkpoint(state):
            if state['events'][-1]['kind'] == 'TOOL_RESULT':
                raise OSError('persistent accepted-result persistence failure')
        runtime = self.runtime(checkpoint=checkpoint)
        with self.assertRaisesRegex(CheckpointPersistenceError, 'could not be checkpointed'):
            runtime.run_agent(NativeFunctionFixtureModel(full_script()))
        self.assertEqual(runtime.state['status'], 'INCOMPLETE')
        self.assertFalse(any(e['kind'] == 'TOOL_REJECTED' for e in runtime.state['events']))
        self.assertFalse(any(e['kind'] == 'FINAL_STATE_SEAL' for e in runtime.state['events']))

    def test_accepted_producers_are_reserved_before_transient_failed_retries(self):
        from tools import far_investigation_engine as engine
        for tool, operation, position in (('extract', 'bind_quote', 2),
                ('discover', 'build_discovery', 5), ('verify_far', 'route_text', 2)):
            script = full_script()
            if tool == 'verify_far':
                script.insert(position, action('verify_far', source_id='src.1'))
            script.insert(position, copy.deepcopy(script[position]))
            actual = getattr(engine, operation)
            count = 0
            def interrupted(*args, **kwargs):
                nonlocal count
                count += 1
                if count == 1:
                    raise OSError('controlled transient operation interruption')
                return actual(*args, **kwargs)
            with self.subTest(tool=tool), patch.object(engine, operation, side_effect=interrupted):
                state = self.runtime().run_agent(ScriptedFixtureModel(script))
            self.assertEqual(state['status'], 'BOUNDED_PIPELINE_COMPLETED')
            self.assertEqual(state['rejected_calls'], 1)
            self.assertTrue(audit(state)['valid'], audit(state))

    def test_recheck_clears_previous_pass_before_first_http_budget_check(self):
        clock, count = [0.0], 0
        def checkpoint(state):
            nonlocal count
            event = state['events'][-1]
            if event['kind'] == 'TOOL_PROPOSAL' and event['payload']['tool'] == 'recheck':
                count += 1
                if count == 2:
                    clock[0] = .3
        with patch('tools.far_investigation_engine.time.monotonic', side_effect=lambda: clock[0]):
            state = self.runtime(checkpoint=checkpoint, budget=Budget(max_seconds=.2)).run_agent(
                ScriptedFixtureModel(full_script()[:7] + [action('recheck')]))
        self.assertEqual(state['status'], 'FAILED_OR_INCOMPLETE')
        self.assertEqual(state['rechecks'], [])
        self.assertEqual(state['http_calls'], 4)
        self.assertTrue(audit(state)['valid'], audit(state))

    def test_invalidation_checkpoint_failure_cannot_leave_a_stale_draft_usable(self):
        for corrected in (False, True):
            raised = False
            def checkpoint(state):
                nonlocal raised
                if state['events'][-1]['kind'] == 'DISCOVERY_INVALIDATED' and not raised:
                    raised = True
                    raise OSError('one-time invalidation checkpoint persistence failure')
            script = full_script()
            script.insert(6, action('extract', source_id='src.1', quote='2 + 2 = 4',
                                   relation='context', claim='Additional context after draft'))
            if corrected:
                script.insert(7, copy.deepcopy(script[5]))
            with self.subTest(corrected=corrected):
                state = self.runtime(checkpoint=checkpoint, budget=Budget(max_steps=len(script))).run_agent(ScriptedFixtureModel(script))
                self.assertEqual(len(state['evidence']), 3)
                self.assertEqual(state['status'], 'BOUNDED_PIPELINE_COMPLETED' if corrected else 'FAILED_OR_INCOMPLETE')
                if not corrected:
                    self.assertIsNone(state['intake'])
                    self.assertIsNone(state['report'])
                self.assertTrue(audit(state)['valid'], audit(state))

    def test_failed_later_search_recheck_revokes_earlier_full_completion(self):
        from tools.far_investigation_retrieval import project_public_search, public_search_url
        count, saved = 0, None
        def searcher(query, provider, policy, checkpoint):
            nonlocal count
            count += 1
            title = 'Original title' if count <= 2 else 'Changed title'
            row = receipt(public_search_url(query, provider), json.dumps({'message': {'items': [
                {'URL': 'https://example.org/article', 'title': [title]}]}}), 'application/json')
            checkpoint(copy.deepcopy(row))
            return project_public_search(query, provider, row)
        def checkpoint(state):
            nonlocal saved
            event = state['events'][-1]
            if event['kind'] == 'TOOL_RESULT' and event['payload']['tool'] == 'recheck':
                saved = state['recheck_completed_at']
            elif event['kind'] == 'TOOL_REJECTED' and 'search hits changed' in event['payload']['reason']:
                # Adversarial intervention restores only the obsolete marker;
                # all native receipts/observations retain their actual values.
                runtime.state['recheck_completed_at'] = saved
        runtime = Investigation(QUESTION, RetrievalPolicy(('example.org', 'independent.example.org', 'api.crossref.org')),
            fetcher=FixtureRetriever(), searcher=searcher, checkpoint=checkpoint)
        script = full_script()
        state = runtime.run_agent(ScriptedFixtureModel([action('search', query='claim', provider='crossref'),
            *script[:7], action('recheck'), *script[7:]]))
        self.assertEqual(state['status'], 'BOUNDED_PIPELINE_COMPLETED')
        self.assertEqual(state['rejected_calls'], 1)
        self.assert_rejected(state, 'recheck')

    def test_source_recheck_checkpoint_failure_preserves_preappend_diagnostic_state(self):
        raised = False
        def checkpoint(state):
            nonlocal raised
            if state['events'][-1]['kind'] == 'SOURCE_RECHECK' and not raised:
                raised = True
                raise OSError('one-time source recheck checkpoint failure before append')
        state = self.runtime(checkpoint=checkpoint, budget=Budget(max_steps=7)).run_agent(
            ScriptedFixtureModel(full_script()[:7]))
        self.assertEqual(state['status'], 'FAILED_OR_INCOMPLETE')
        self.assertEqual(state['rechecks'], [])
        self.assertEqual(state['rejected_calls'], 1)
        self.assertTrue(audit(state)['valid'], audit(state))

    def test_terminal_recheck_checkpoint_failure_retains_diagnostics_without_readiness(self):
        for retry in (False, True):
            raised = False
            def checkpoint(state):
                nonlocal raised
                if state['events'][-1]['kind'] == 'DISCOVERY_TERMINAL_RECHECK' and not raised:
                    raised = True
                    raise OSError('one-time terminal recheck checkpoint failure')
            script = full_script()[:7]
            if retry:
                script += full_script()[6:]
            state = self.runtime(checkpoint=checkpoint, budget=Budget(max_steps=len(script))).run_agent(
                ScriptedFixtureModel(script))
            with self.subTest(retry=retry):
                self.assertEqual(state['status'], 'BOUNDED_PIPELINE_COMPLETED' if retry else 'FAILED_OR_INCOMPLETE')
                self.assertEqual('recheck_completed_at' in state, retry)
                self.assertEqual(len(state['rechecks']), 2)
                self.assertTrue(audit(state)['valid'], audit(state))

    def test_frozen_or_malformed_recheck_rejection_preserves_earlier_valid_completion(self):
        for proposal in (action('recheck'), action('recheck', extra='unsupported')):
            script = full_script()
            script.insert(8, proposal)
            with self.subTest(proposal=proposal):
                state = self.runtime().run_agent(ScriptedFixtureModel(script))
                self.assertEqual(state['status'], 'BOUNDED_PIPELINE_COMPLETED')
                self.assertEqual(state['rejected_calls'], 1)
                self.assertIn('recheck_completed_at', state)
                self.assertTrue(audit(state)['valid'], audit(state))

    def test_failed_search_recheck_can_be_replaced_by_a_later_complete_pass(self):
        from tools.far_investigation_retrieval import project_public_search, public_search_url
        count = 0
        def searcher(query, provider, policy, checkpoint):
            nonlocal count
            count += 1
            title = 'Changed title' if count == 3 else 'Original title'
            row = receipt(public_search_url(query, provider), json.dumps({'message': {'items': [
                {'URL': 'https://example.org/article', 'title': [title]}]}}), 'application/json')
            checkpoint(copy.deepcopy(row))
            return project_public_search(query, provider, row)
        runtime = Investigation(QUESTION, RetrievalPolicy(('example.org', 'independent.example.org', 'api.crossref.org')),
            fetcher=FixtureRetriever(), searcher=searcher)
        script = full_script()
        state = runtime.run_agent(ScriptedFixtureModel([action('search', query='claim', provider='crossref'),
            *script[:7], action('recheck'), action('recheck'), *script[7:]]))
        self.assertEqual(state['status'], 'BOUNDED_PIPELINE_COMPLETED')
        self.assertEqual(state['rejected_calls'], 1)
        self.assertTrue(audit(state)['valid'], audit(state))

    def test_unavailable_tool_rejection_cannot_become_an_accepted_operation(self):
        state = self.runtime().run_agent(ScriptedFixtureModel([action('execute_shell', command='echo impossible'), *full_script()]))
        self.assertTrue(audit(state)['valid'], audit(state))
        event = next(e for e in state['events'] if e['kind'] == 'TOOL_REJECTED')
        event.update(kind='TOOL_RESULT', payload={'tool': 'execute_shell', 'result': {'output': 'impossible success'}})
        state['rejected_calls'] -= 1
        reseal(state)
        self.assert_rejected(state, 'proposal')

    def test_accepted_verify_requires_its_own_frozen_native_producer(self):
        state = self.runtime().run_agent(NativeFunctionFixtureModel([
            action('verify', candidate_id='nonexistent'), *full_script()]))
        self.assertEqual(state['status'], 'BOUNDED_PIPELINE_COMPLETED')
        self.assertEqual(state['rejected_calls'], 1)
        self.assertTrue(audit(state)['valid'], audit(state))
        event = next(e for e in state['events'] if e['kind'] == 'TOOL_REJECTED')
        event.update(kind='TOOL_RESULT', payload={'tool': 'verify', 'result': copy.deepcopy(state['evaluations'][0])})
        state['rejected_calls'] -= 1
        reseal(state)
        self.assert_rejected(state, 'verify')

    def test_native_success_cannot_borrow_future_or_repeated_evaluation_producers(self):
        for position, ident in ((0, 'contract.1.1'), (8, 'contract.1.1'),
                                (8, 'nonexistent'), (9, 'contract.1.1')):
            script = full_script()
            script.insert(position, action('verify', candidate_id=ident))
            # At position eight a valid candidate actually runs first; the
            # duplicate original request is rejected afterward. Preserve that
            # genuine failure as a positive before forging its success.
            state = self.runtime().run_agent(NativeFunctionFixtureModel(script))
            self.assertEqual(state['rejected_calls'], 1)
            self.assertTrue(audit(state)['valid'], audit(state))
            rejected = next(e for e in state['events'] if e['kind'] == 'TOOL_REJECTED')
            rejected.update(kind='TOOL_RESULT', payload={'tool': 'verify', 'result': copy.deepcopy(state['evaluations'][0])})
            state['rejected_calls'] -= 1
            reseal(state)
            with self.subTest(position=position, candidate=ident):
                self.assert_rejected(state, 'verify')

    def test_existing_frozen_verify_requires_one_own_request_and_retained_result(self):
        original = self.runtime().run_agent(NativeFunctionFixtureModel(full_script()))
        for target in ('remove_request', 'duplicate_request', 'remove_evaluation'):
            state = copy.deepcopy(original)
            position = next(i for i, e in enumerate(state['events']) if e['kind'] == 'NATIVE_VERIFIER_REQUEST')
            if target == 'remove_request':
                state['events'].pop(position)
            elif target == 'duplicate_request':
                state['events'].insert(position, copy.deepcopy(state['events'][position]))
            else:
                state['evaluations'] = []
                state['intake']['evaluations'] = []
            for i, event in enumerate(state['events'], 1):
                event['sequence'] = i
            reseal(state)
            with self.subTest(target=target):
                self.assert_rejected(state, 'verify')

    def test_source_ids_follow_the_actual_retrieval_allocator(self):
        state = self.runtime(budget=Budget(max_steps=1)).run_agent(
            NativeFunctionFixtureModel([action('retrieve', url=URL_A)]))
        self.assertTrue(audit(state)['valid'], audit(state))
        state['sources']['src.0'] = state['sources'].pop('src.1')
        state['projections']['src.0'] = state['projections'].pop('src.1')
        next(e['payload']['result'] for e in state['events'] if e['kind'] == 'TOOL_RESULT')['source_id'] = 'src.0'
        reseal(state)
        self.assert_rejected(state, 'sources.allocation')
        state = self.runtime(budget=Budget(max_steps=2)).run_agent(
            NativeFunctionFixtureModel(full_script()[:2]))
        self.assertTrue(audit(state)['valid'], audit(state))
        def swapped(node):
            if isinstance(node, dict):
                return {swapped(key): swapped(value) for key, value in node.items()}
            if isinstance(node, list):
                return [swapped(value) for value in node]
            return {'src.1': 'src.2', 'src.2': 'src.1'}.get(node, node) if isinstance(node, str) else node
        state = swapped(state)
        reseal(state)
        self.assert_rejected(state, 'sources.allocation')

    def test_recheck_cannot_invent_an_unparsed_original_projection(self):
        url_c = 'https://independent.example.org/third'
        raised = False
        def checkpoint(state):
            nonlocal raised
            if 'src.3' in state['sources'] and 'src.3' not in state['projections'] and not raised:
                raised = True
                raise OSError('one-time raw-only source checkpoint failure')
        script = [*full_script()[:5], action('retrieve', url=url_c), action('recheck')]
        runtime = Investigation(QUESTION, RetrievalPolicy(('example.org', 'independent.example.org')),
            fetcher=FixtureRetriever({URL_A: BODY_A, URL_B: BODY_B, url_c: 'Third bounded source'}),
            checkpoint=checkpoint, budget=Budget(max_steps=len(script)))
        state = runtime.run_agent(NativeFunctionFixtureModel(script))
        self.assertEqual(state['rejected_calls'], 2)
        self.assertEqual(len(state['rechecks']), 2)
        self.assertTrue(audit(state)['valid'], audit(state))
        observed = next(e['payload'] for e in reversed(state['events']) if e['kind'] == 'HTTP_OBSERVATION')
        record = {'source_id': 'src.3', 'receipt': copy.deepcopy(observed), 'unchanged_projection': True}
        position = max(i for i, e in enumerate(state['events']) if e['kind'] == 'TOOL_REJECTED')
        state['events'].insert(position, {'kind': 'SOURCE_RECHECK', 'payload': copy.deepcopy(record),
                                        'at': state['events'][position]['at']})
        state['events'][position+1].update(kind='TOOL_RESULT', payload={'tool': 'recheck', 'result': {
            'rechecked_sources': 3, 'rechecked_searches': 0,
            'scope': 'unchanged bounded projections only; not semantic or open-world completeness'}})
        state['rechecks'].append(record)
        state['recheck_completed_at'] = state['events'][position]['at']
        state['rejected_calls'] -= 1
        for i, event in enumerate(state['events'], 1):
            event['sequence'] = i
        reseal(state)
        self.assert_rejected(state, 'projection')

    def test_all_supported_tools_reconstruct_their_complete_accepted_outputs(self):
        from tools.far_investigation_engine import TOOLS
        def searcher(query, provider, policy, checkpoint):
            row = receipt(URL_A, BODY_A)
            checkpoint(copy.deepcopy(row))
            return {'query': query, 'provider': provider, 'receipt': row,
                    'hits': [], 'status': 'SEARCH_COMPLETED'}
        script = full_script()
        choices = [action('search', query='bounded fixture', provider='wikimedia'), *script[:2],
            action('inspect', source_id='src.1'), action('verify_far', source_id='src.1'), *script[2:]]
        original = self.runtime(searcher=searcher).run_agent(NativeFunctionFixtureModel(choices))
        self.assertTrue(audit(original)['valid'], audit(original))
        covered = {e['payload']['tool'] for e in original['events'] if e['kind'] == 'TOOL_RESULT'}
        self.assertEqual(covered, set(TOOLS))
        for tool in covered:
            state = copy.deepcopy(original)
            result = next(e['payload']['result'] for e in state['events']
                          if e['kind'] == 'TOOL_RESULT' and e['payload']['tool'] == tool)
            result['invented_result_field'] = 'unproduced observation'
            reseal(state)
            with self.subTest(tool=tool):
                self.assert_rejected(state)

    def test_invalid_accepted_argument_copies_cannot_bypass_dispatch_validation(self):
        cases = [('finish', 'notes', {'claim': 'universal proof'}),
            ('finish', 'next_evidence', 'No further evidence needed'), ('finish', 'evidence_ids', ''),
            ('discover', 'missing_evidence', {'claim': 'none'}), ('discover', 'assumptions', {}),
            ('compare', 'execute_shell', 'impossible'), ('verify', 'execute_shell', 'impossible'),
            ('finish', 'execute_shell', 'impossible')]
        for tool, field, value in cases:
            state = self.complete()
            def mutate(node):
                if isinstance(node, dict):
                    if node.get('tool') == tool and 'args' in node:
                        node['args'][field] = copy.deepcopy(value)
                    if node.get('fixture') and node.get('response_base64'):
                        proposal = json.loads(base64.b64decode(node['response_base64']))
                        if proposal.get('tool') == tool:
                            proposal['args'][field] = copy.deepcopy(value)
                            raw = json.dumps(proposal, sort_keys=True).encode()
                            node.update(response_base64=base64.b64encode(raw).decode(), response_sha256=hashlib.sha256(raw).hexdigest())
                    for child in node.values():
                        mutate(child)
                elif isinstance(node, list):
                    for child in node:
                        mutate(child)
            mutate(state)
            if tool == 'finish' and field in ('notes', 'next_evidence', 'evidence_ids'):
                key = 'analyst_notes' if field == 'notes' else field
                state['report'][key] = copy.deepcopy(value)
                next(e['payload']['result'] for e in state['events']
                    if e['kind'] == 'TOOL_RESULT' and e['payload']['tool'] == 'finish')[key] = copy.deepcopy(value)
            if tool == 'discover' and field == 'missing_evidence':
                state['missing_evidence'] = copy.deepcopy(value)
                state['report']['missing_evidence'] = copy.deepcopy(value)
                next(e['payload']['result'] for e in state['events']
                    if e['kind'] == 'TOOL_RESULT' and e['payload']['tool'] == 'finish')['missing_evidence'] = copy.deepcopy(value)
            reseal(state)
            with self.subTest(tool=tool, field=field):
                self.assert_rejected(state, 'proposal')

    def test_invalid_rejected_proposal_cannot_acquire_retained_transport_effects(self):
        from tools.far_investigation_retrieval import parse_receipt
        proposal = action('retrieve', url=URL_A, extra='unsupported')
        state = self.runtime(budget=Budget(max_steps=1)).run_agent(ScriptedFixtureModel([proposal]))
        self.assertTrue(audit(state)['valid'], audit(state))
        row = receipt(URL_A, BODY_A)
        state['sources']['src.1'], state['projections']['src.1'] = row, parse_receipt(row)
        state['http_calls'] = 1
        position = next(i for i, event in enumerate(state['events']) if event['kind'] == 'TOOL_REJECTED')
        state['events'][position:position] = [
            {'kind': 'HTTP_REQUEST', 'payload': {'url': URL_A, 'call': 1}, 'at': state['events'][position]['at']},
            {'kind': 'HTTP_OBSERVATION', 'payload': row, 'at': state['events'][position]['at']}]
        for index, event in enumerate(state['events'], 1):
            event['sequence'] = index
        reseal(state)
        self.assert_rejected(state, 'transport observation')

    def test_finish_entire_report_is_derived_from_the_actual_proposal(self):
        original = self.complete()
        for field, value in (('analyst_notes', 'Fabricated notes'), ('next_evidence', []),
                ('scope', 'Universal truth and external independent verification'),
                ('notes_assurance', 'PROVED'), ('missing_evidence', []), ('closure_reason', 'All obligations proved')):
            state = copy.deepcopy(original)
            state['report'][field] = copy.deepcopy(value)
            result = next(e['payload']['result'] for e in state['events']
                if e['kind'] == 'TOOL_RESULT' and e['payload']['tool'] == 'finish')
            result[field] = copy.deepcopy(value)
            reseal(state)
            with self.subTest(field=field):
                self.assert_rejected(state, 'finish')

    def test_postdispatch_native_budget_failure_retains_evaluation_without_success(self):
        clock = [0.0]
        with patch('tools.far_investigation_engine.time.monotonic', side_effect=lambda: clock[0]):
            runtime = self.runtime(budget=Budget(max_seconds=.2))
            dispatch = runtime._dispatch
            def expire(tool, args):
                result = dispatch(tool, args)
                if tool == 'verify':
                    clock[0] = .3
                return result
            with patch.object(runtime, '_dispatch', side_effect=expire):
                state = runtime.run_agent(ScriptedFixtureModel(full_script()))
        self.assertEqual(state['status'], 'FAILED_OR_INCOMPLETE')
        self.assertEqual(len(state['evaluations']), 1)
        self.assertFalse(any(e['kind'] == 'TOOL_RESULT' and e['payload']['tool'] == 'verify' for e in state['events']))
        self.assertTrue(audit(state)['valid'], audit(state))

    def test_other_postdispatch_mutable_failures_preserve_exact_diagnostic_effects(self):
        for delayed in ('discover', 'recheck', 'freeze', 'verify_far', 'search'):
            clock = [0.0]
            script = full_script()
            if delayed == 'verify_far':
                script.insert(2, action('verify_far', source_id='src.1'))
            def searcher(query, provider, policy, checkpoint):
                row = receipt(URL_A, BODY_A)
                checkpoint(copy.deepcopy(row))
                return {'query': query, 'provider': provider, 'receipt': row, 'hits': [], 'status': 'SEARCH_COMPLETED'}
            if delayed == 'search':
                script.insert(0, action('search', query='claim', provider='wikimedia'))
            with self.subTest(tool=delayed), patch('tools.far_investigation_engine.time.monotonic', side_effect=lambda: clock[0]):
                runtime = self.runtime(budget=Budget(max_seconds=.2), searcher=searcher)
                dispatch = runtime._dispatch
                def expire(tool, args):
                    result = dispatch(tool, args)
                    if tool == delayed:
                        clock[0] = .3
                    return result
                with patch.object(runtime, '_dispatch', side_effect=expire):
                    state = runtime.run_agent(ScriptedFixtureModel(script))
            self.assertEqual(state['status'], 'FAILED_OR_INCOMPLETE')
            self.assertTrue(audit(state)['valid'], audit(state))

    def test_orphan_and_duplicate_final_evidence_and_comparisons_are_rejected(self):
        original = self.complete()
        for target in ('orphan_evidence', 'duplicate_comparison'):
            state = copy.deepcopy(original)
            if target == 'orphan_evidence':
                state['evidence']['ev.orphan'] = copy.deepcopy(state['evidence']['ev.1'])
            else:
                state['comparisons'].append(copy.deepcopy(state['comparisons'][0]))
            reseal(state)
            with self.subTest(target=target):
                self.assert_rejected(state, 'coverage')

    def test_valid_extra_extraction_and_postdispatch_rejected_effects_remain_auditable(self):
        script = full_script()
        script.insert(5, action('extract', source_id='src.1', quote='2 + 2 = 4',
                                relation='context', claim='A distinct recorded context'))
        state = self.runtime().run_agent(ScriptedFixtureModel(script))
        self.assertTrue(audit(state)['valid'], audit(state))
        for delayed in ('extract', 'compare'):
            clock = [0.0]
            with self.subTest(delayed=delayed), patch('tools.far_investigation_engine.time.monotonic', side_effect=lambda: clock[0]):
                runtime = self.runtime(budget=Budget(max_seconds=.2))
                dispatch = runtime._dispatch
                def expire(tool, args):
                    result = dispatch(tool, args)
                    if tool == delayed:
                        clock[0] = .3
                    return result
                with patch.object(runtime, '_dispatch', side_effect=expire):
                    state = runtime.run_agent(ScriptedFixtureModel(full_script()))
                self.assertTrue(state['evidence'])
                self.assertEqual(bool(state['comparisons']), delayed == 'compare')
                self.assertEqual(state['status'], 'FAILED_OR_INCOMPLETE')
                self.assertTrue(audit(state)['valid'], audit(state))

    def test_retrieve_and_inspect_results_cannot_change_the_source_projection(self):
        choices = full_script()
        choices.insert(2, action('inspect', source_id='src.1', query='calculation'))
        original = self.runtime().run_agent(ScriptedFixtureModel(choices))
        self.assertTrue(audit(original)['valid'], audit(original))
        for tool in ('retrieve', 'inspect'):
            state = copy.deepcopy(original)
            result = next(e['payload']['result'] for e in state['events']
                if e['kind'] == 'TOOL_RESULT' and e['payload']['tool'] == tool)
            result['text'] = 'Forged observation presented to the model'
            reseal(state)
            with self.subTest(tool=tool):
                self.assert_rejected(state, tool)

    def test_elapsed_and_budget_scalars_have_runtime_types_bounds_and_completion_limits(self):
        original = self.complete()
        mutations = [('elapsed_seconds', -10), ('elapsed_seconds', True),
            ('max_seconds', True), ('max_seconds', 3601), ('max_steps', 32.5),
            ('max_steps', 101), ('max_http_calls', 101), ('max_model_tokens', 200001),
            ('elapsed_seconds', original['policy']['budget']['max_seconds'])]
        for field, value in mutations:
            state = copy.deepcopy(original)
            if field == 'elapsed_seconds':
                state[field] = value
            else:
                state['policy']['budget'][field] = value
                state['events'][0]['payload']['policy']['budget'][field] = value
            reseal(state)
            with self.subTest(field=field, value=value):
                self.assert_rejected(state, 'budget' if field != 'elapsed_seconds' else 'elapsed')

    def test_successful_receipts_cannot_contradict_their_optional_transport(self):
        from tests.test_far_investigation_retrieval import Response, dns
        from tools.far_investigation_retrieval import retrieve
        def fetch(url, policy, checkpoint):
            client = unittest.mock.Mock()
            client.open.return_value = Response((BODY_A if url == URL_A else BODY_B).encode(), url=url)
            return retrieve(url, policy, checkpoint=checkpoint, opener=client)
        state = Investigation(QUESTION, RetrievalPolicy(('example.org', 'independent.example.org'), resolver=dns),
            fetcher=fetch).run_agent(ScriptedFixtureModel(full_script()))
        self.assertTrue(audit(state)['valid'], audit(state))
        def contradict(node):
            if isinstance(node, dict):
                if node.get('status') == 'RETRIEVED' and isinstance(node.get('transport'), dict):
                    node['transport'].update(response_complete=False, response_hash_scope='retained_prefix',
                                              framing_error='ContentLengthMismatch')
                for child in node.values():
                    contradict(child)
            elif isinstance(node, list):
                for child in node:
                    contradict(child)
        contradict(state)
        reseal(state)
        self.assert_rejected(state, 'transport')

    def test_native_receipt_content_type_and_encoding_bind_to_transport(self):
        from tests.test_far_investigation_retrieval import Response, dns
        from tools.far_investigation_retrieval import retrieve

        def fetch(url, policy, checkpoint):
            client = unittest.mock.Mock()
            raw = ('<script>' + BODY_A + '</script>') if url == URL_A else BODY_B
            client.open.return_value = Response(raw.encode(), url=url)
            return retrieve(url, policy, checkpoint=checkpoint, opener=client)

        original = Investigation(
            QUESTION, RetrievalPolicy(('example.org', 'independent.example.org'), resolver=dns),
            fetcher=fetch).run_agent(NativeFunctionFixtureModel(full_script()))
        self.assertTrue(audit(original)['valid'], audit(original))
        self.assertIn(BODY_A, original['projections']['src.1']['text'])

        for header, replacement in (('content-type', 'text/html'),
                                    ('content-encoding', 'gzip')):
            state = copy.deepcopy(original)
            mutated = 0
            def rewrite(node):
                nonlocal mutated
                if isinstance(node, dict):
                    if node.get('status') == 'RETRIEVED' and isinstance(node.get('transport'), dict):
                        headers = node['transport']['response_headers']
                        for key in list(headers):
                            if key.lower() == header:
                                headers[key] = replacement
                                mutated += 1
                        if header not in (key.lower() for key in headers):
                            headers[header] = replacement
                            mutated += 1
                    for child in node.values():
                        rewrite(child)
                elif isinstance(node, list):
                    for child in node:
                        rewrite(child)
            rewrite(state)
            self.assertGreater(mutated, 0)
            reseal(state)
            with self.subTest(header=header):
                self.assert_rejected(state, 'transport.' + header.replace('-', '_'))

    def test_accepted_model_proposal_requires_a_coherent_optional_transport(self):
        state = self.complete()
        def transport(node, complete):
            if isinstance(node, dict):
                if node.get('fixture') is True and node.get('response_base64'):
                    raw = base64.b64decode(node['response_base64'])
                    node['transport'] = {'http_status': 200, 'response_complete': complete,
                        'response_truncated': False,
                        'response_hash_scope': 'complete_body' if complete else 'retained_prefix',
                        'raw_response_base64': node['response_base64'],
                        'response_sha256': node['response_sha256'], 'response_bytes_retained': len(raw)}
                for child in node.values():
                    transport(child, complete)
            elif isinstance(node, list):
                for child in node:
                    transport(child, complete)
        transport(state, True)
        reseal(state)
        self.assertTrue(audit(state)['valid'], audit(state))
        transport(state, False)
        reseal(state)
        self.assert_rejected(state, 'model_transport')

    def test_far_verification_results_and_final_inventory_are_bound_to_dispatch(self):
        choices = full_script()
        choices.insert(2, action('verify_far', source_id='src.1'))
        original = self.runtime().run_agent(ScriptedFixtureModel(choices))
        self.assertTrue(audit(original)['valid'], audit(original))
        for target in ('tool_result', 'orphan_final_result'):
            state = copy.deepcopy(original)
            if target == 'tool_result':
                result = next(e['payload']['result'] for e in state['events']
                    if e['kind'] == 'TOOL_RESULT' and e['payload']['tool'] == 'verify_far')
                result['status'] = 'VERIFIED_EXPLICIT_CONTRACT'
            else:
                state['far_verifications'].append(copy.deepcopy(state['far_verifications'][0]))
            reseal(state)
            with self.subTest(target=target):
                self.assert_rejected(state, 'verify_far' if target == 'tool_result' else 'coverage')

    def test_rejected_source_dependent_proposals_can_retry_after_actual_retrieval(self):
        script = full_script()
        extract = next(p for p in script if p['tool'] == 'extract')
        for early, later in ((extract, script),
                (action('inspect', source_id='src.1'), [*script[:2], action('inspect', source_id='src.1'), *script[2:]]),
                (action('verify_far', source_id='src.1'), [*script[:2], action('verify_far', source_id='src.1'), *script[2:]])):
            with self.subTest(tool=early['tool']):
                state = self.runtime().run_agent(ScriptedFixtureModel([early, *later]))
                self.assertEqual(state['status'], 'BOUNDED_PIPELINE_COMPLETED')
                self.assertEqual(state['rejected_calls'], 1)
                self.assertTrue(audit(state)['valid'], audit(state))

    def test_successful_outputs_cannot_use_sources_that_arrive_in_later_attempts(self):
        script = full_script()
        script[2:2] = [action('inspect', source_id='src.1'), action('verify_far', source_id='src.1')]
        original = self.runtime().run_agent(ScriptedFixtureModel(script))
        self.assertTrue(audit(original)['valid'], audit(original))
        for tool in ('extract', 'inspect', 'verify_far'):
            state = copy.deepcopy(original)
            events = state['events']
            proposal = next(i for i, e in enumerate(events)
                if e['kind'] == 'TOOL_PROPOSAL' and e['payload']['tool'] == tool)
            start = max(i for i in range(proposal) if events[i]['kind'] in ('TOOL_RESULT', 'TOOL_REJECTED')) + 1
            end = next(i for i in range(proposal, len(events)) if events[i]['kind'] == 'TOOL_RESULT') + 1
            moved = events[start:end]
            state['events'] = [events[0], *moved, *events[1:start], *events[end:]]
            # Remove incidental hash/chronology objections so this mutation
            # specifically tests the availability of the requested source.
            for index, event in enumerate(state['events'], 1):
                event['sequence'], event['at'] = index, state['started_at']
            reseal(state)
            with self.subTest(tool=tool):
                self.assert_rejected(state, tool)

    def test_parse_failure_and_postdispatch_retrieval_keep_only_observed_sources_available(self):
        runtime = Investigation(QUESTION, RetrievalPolicy(('example.org',)),
            fetcher=FixtureRetriever({URL_A: ('{"broken":', 'application/json')}), budget=Budget(max_steps=2))
        state = runtime.run_agent(ScriptedFixtureModel([
            action('retrieve', url=URL_A), action('verify_far', source_id='src.1')]))
        self.assertEqual(state['rejected_calls'], 1)
        self.assertEqual(len(state['far_verifications']), 1)
        self.assertNotIn('src.1', state['projections'])
        self.assertTrue(audit(state)['valid'], audit(state))

        clock = [0.0]
        with patch('tools.far_investigation_engine.time.monotonic', side_effect=lambda: clock[0]):
            runtime = self.runtime(budget=Budget(max_seconds=.2))
            dispatch = runtime._dispatch
            def expire_after_source(tool, args):
                result = dispatch(tool, args)
                clock[0] = .3
                return result
            with patch.object(runtime, '_dispatch', side_effect=expire_after_source):
                state = runtime.run_agent(ScriptedFixtureModel([action('retrieve', url=URL_A)]))
        self.assertIn('src.1', state['sources'])
        self.assertIn('src.1', state['projections'])
        self.assertEqual(state['status'], 'FAILED_OR_INCOMPLETE')
        self.assertTrue(audit(state)['valid'], audit(state))

    def test_identical_failed_receipts_keep_source_order_after_canonical_serialization(self):
        fixed = receipt(URL_A, '{"broken":', 'application/json')
        def fetch(url, policy, checkpoint):
            checkpoint(copy.deepcopy(fixed))
            return copy.deepcopy(fixed)
        runtime = Investigation(QUESTION, RetrievalPolicy(('example.org',)),
            fetcher=fetch, budget=Budget(max_steps=11))
        choices = [action('retrieve', url=URL_A), action('retrieve', url=URL_A),
                   action('verify_far', source_id='src.2'),
                   *[action('retrieve', url=URL_A) for _ in range(8)]]
        state = runtime.run_agent(ScriptedFixtureModel(choices))
        self.assertEqual(len(state['sources']), 10)
        self.assertTrue(audit(state)['valid'], audit(state))
        restored = json.loads(json.dumps(state, sort_keys=True))
        self.assertTrue(audit(restored)['valid'], audit(restored))
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
        rejected = next(e for e in state['events'] if e['kind'] == 'TOOL_REJECTED')
        rejected.update(kind='TOOL_RESULT', payload={'tool': 'verify', 'result': copy.deepcopy(state['evaluations'][0])})
        state['rejected_calls'] -= 1
        reseal(state)
        self.assert_rejected(state, 'verify')

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
