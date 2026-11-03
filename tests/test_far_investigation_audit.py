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

    def test_resealed_new_transport_timestamps_cannot_move_backwards(self):
        state=self.complete()
        state['transport_timing_test']={
            'timing_scope':'request_start_to_body_read_or_transport_failure',
            'requested_at':'2026-11-03T01:00:01Z','received_at':'2026-11-03T01:00:00Z'}
        reseal(state)
        self.assert_rejected(state,'transport_time')

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
        self.assert_rejected(state, 'inspect.proposal')

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
