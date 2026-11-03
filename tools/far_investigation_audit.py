"""Offline integrity reconstruction for Research investigation transcripts.

Hashes are self-signed consistency evidence, not external authenticity, source
truth, semantic adequacy, independent evaluation, or protection from an author
rewriting a whole history. No network or model is invoked by this audit.
"""
from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime
from urllib.parse import urlsplit

from mechanization.far_mechanization.intake_v1 import aggregate_manifest, sha256_json, validate_manifest
from tools.far_investigation_retrieval import bind_quote, parse_receipt, receipt_bytes
from tools.far_investigation_verifiers import verify
from tools.far_routing_dispatch import _parse, route_text


def audit(state) -> dict:
    errors = []
    counters = {}

    def fail(path, reason):
        errors.append(path + ': ' + reason)

    def guarded(path, function):
        try:
            return function()
        except Exception as exc:
            fail(path, 'malformed or invalid ' + type(exc).__name__)
            return None

    def equal(path, actual, expected):
        if sha256_json(actual) != sha256_json(expected):
            fail(path, 'reconstruction mismatch')

    def timestamp(value):
        if type(value) is not str:
            raise ValueError('timestamp must be text')
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            raise ValueError('timestamp must name timezone')
        return parsed

    def envelope_tree(node, path='state', depth=0):
        if depth > 128:
            fail(path, 'nesting exceeds audit bound')
            return
        if type(node) is dict:
            if {'raw_base64', 'sha256', 'observed_bytes'} <= node.keys():
                guarded(path + '.receipt', lambda: receipt_bytes(node))
                if node.get('status') == 'RETRIEVED':
                    if node.get('http_status') != 200 or node.get('truncated') or not node['observed_bytes']:
                        fail(path, 'successful receipt has failed/empty/truncated transport')
                    destination = urlsplit(node['request']['url'])
                    if (destination.scheme != 'https' or destination.hostname not in state['policy']['allowed_hosts']
                            or destination.username is not None or destination.password is not None
                            or destination.port not in (None, 443) or destination.fragment
                            or node['request'].get('method') != 'GET'):
                        fail(path, 'successful receipt exceeds recorded read-only destination policy')
            for raw_key in ('response_base64', 'raw_response_base64'):
                if raw_key in node:
                    encoded, declared = node[raw_key], node.get('response_sha256')
                    if encoded is None:
                        if declared is not None:
                            fail(path, 'absent response has a declared hash')
                    else:
                        raw = guarded(path + '.' + raw_key, lambda: base64.b64decode(encoded, validate=True))
                        if raw is not None:
                            equal(path + '.response_sha256', hashlib.sha256(raw).hexdigest(), declared)
                            if 'response_bytes_retained' in node:
                                equal(path + '.response_bytes_retained', len(raw), node['response_bytes_retained'])
                            if node.get('response_truncated') and node.get('response_complete'):
                                fail(path, 'truncated response marked complete')
                            if node.get('response_truncated') and node.get('response_hash_scope') == 'complete_body':
                                fail(path, 'prefix hash represented as full-body hash')
            if 'request_sha256' in node:
                raw = guarded(path + '.request', lambda: json.dumps(
                    node['request'], sort_keys=True, separators=(',', ':'), allow_nan=False).encode())
                if raw is not None:
                    equal(path + '.request_sha256', hashlib.sha256(raw).hexdigest(), node['request_sha256'])
            for key, child in node.items():
                envelope_tree(child, path + '.' + str(key), depth + 1)
        elif type(node) is list:
            for index, child in enumerate(node):
                envelope_tree(child, path + '[' + str(index) + ']', depth + 1)

    def inspect():
        if type(state) is not dict or state.get('schema') != 'far-investigation-engine/0.1':
            raise ValueError('unsupported transcript')
        # Reject Python-only/non-finite/cyclic objects before walking them.
        _parse(json.dumps(state, allow_nan=False))
        events = state['events']
        if type(events) is not list or not events:
            raise ValueError('event list required')
        envelope_tree(state)
        question = state['question']
        if state['mode'] not in ('agent', 'deterministic', 'declarative'):
            fail('mode', 'unsupported mode')
        if state['status'] not in ('INCOMPLETE', 'FAILED_OR_INCOMPLETE', 'BOUNDED_PIPELINE_COMPLETED'):
            fail('status', 'unsupported execution status')
        equal('question_sha256', hashlib.sha256(question.encode()).hexdigest(), state['question_sha256'])
        sources, evidence = state['sources'], state['evidence']
        previous, previous_at = None, timestamp(state['started_at'])
        tool_pending, model_pending = None, None
        model_proposals, model_observations, actual_proposals = [], [], []
        tool_results, source_rechecks, native_requests = [], [], []
        http_requests, search_requests, reservation_order, rejections, tokens = [], [], [], 0, 0
        discovery_results, freeze_events = [], []
        for index, event in enumerate(events, 1):
            path = 'events[' + str(index - 1) + ']'
            body = {k: v for k, v in event.items() if k != 'sha256'}
            equal(path + '.sequence', event['sequence'], index)
            equal(path + '.previous_sha256', event['previous_sha256'], previous)
            equal(path + '.sha256', sha256_json(body), event['sha256'])
            at = timestamp(event['at'])
            if at < previous_at:
                fail(path, 'event chronology moves backwards')
            previous, previous_at = event['sha256'], at
            kind, payload = event['kind'], event['payload']
            if kind == 'MODEL_OBSERVATION':
                model_observations.append(payload)
            elif kind == 'MODEL_PROPOSAL':
                if model_pending is not None:
                    fail(path, 'previous model proposal never dispatched')
                model_pending = payload['proposal']
                model_proposals.append(payload)
                count = payload['metadata']['tokens']
                if type(count) is not int or count < 1:
                    fail(path, 'invalid model token telemetry')
                else:
                    tokens += count
                env = payload['metadata'].get('envelope')
                if env and not env.get('fixture') and env.get('response_base64'):
                    response = _parse(base64.b64decode(env['response_base64']).decode())
                    message = response['choices'][0]['message']
                    calls = message.get('tool_calls', [])
                    if calls:
                        if type(calls) is not list or len(calls) != 1:
                            raise ValueError('one recorded function call required')
                        function = calls[0]['function']
                        parsed_proposal = {'tool': function['name'], 'args': _parse(function['arguments'])}
                    else:
                        parsed_proposal = _parse(message['content'])
                    equal(path + '.parsed_proposal', parsed_proposal, payload['proposal'])
                    equal(path + '.tokens', response['usage']['total_tokens'], count)
                    equal(path + '.model', response.get('model'), payload['metadata'].get('model'))
            elif kind == 'TOOL_PROPOSAL':
                if tool_pending is not None:
                    fail(path, 'previous tool proposal has no recorded outcome')
                if state['mode'] == 'agent':
                    equal(path + '.model_to_tool', payload, model_pending)
                model_pending = None
                tool_pending = payload
                actual_proposals.append(payload)
            elif kind == 'HTTP_REQUEST':
                http_requests.append(payload)
                reservation_order.append(payload['call'])
            elif kind == 'SEARCH_REQUEST':
                search_requests.append(payload)
                reservation_order.append(payload['call'])
            elif kind == 'SOURCE_RECHECK':
                original = sources[payload['source_id']]
                equal(path + '.request', payload['receipt']['request']['url'], original['request']['url'])
                stable = parse_receipt(payload['receipt'])['projection_sha256'] == parse_receipt(original)['projection_sha256']
                equal(path + '.unchanged_projection', payload['unchanged_projection'], stable)
                source_rechecks.append((index, payload))
            elif kind == 'NATIVE_VERIFIER_REQUEST':
                if (type(tool_pending) is not dict or tool_pending.get('tool') != 'verify'
                        or tool_pending.get('args', {}).get('candidate_id') != payload['candidate']['id']):
                    fail(path, 'native verifier invocation differs from actual proposal')
                native_requests.append((index, payload))
            elif kind in ('TOOL_RESULT', 'TOOL_REJECTED'):
                if tool_pending is None:
                    fail(path, 'tool outcome lacks a proposal')
                elif kind == 'TOOL_RESULT':
                    equal(path + '.tool', payload['tool'], tool_pending.get('tool'))
                    tool_results.append((index, tool_pending, payload['result']))
                    if payload['tool'] == 'discover':
                        discovery_results.append((index, payload['result']))
                    elif payload['tool'] == 'freeze':
                        freeze_events.append((index, payload['result']))
                else:
                    rejections += 1
                tool_pending = None
        equal('START.kind', events[0]['kind'], 'START')
        equal('START.question_sha256', events[0]['payload']['question_sha256'], state['question_sha256'])
        equal('START.policy', events[0]['payload']['policy'], state['policy'])
        seals = [event for event in events if event['kind'] == 'FINAL_STATE_SEAL']
        if len(seals) != 1 or events[-1]['kind'] != 'FINAL_STATE_SEAL':
            fail('final_state_seal', 'exactly one terminal seal required')
        else:
            equal('final_state_seal', seals[0]['payload']['state_sha256'],
                  sha256_json({k: v for k, v in state.items() if k != 'events'}))
        if tool_pending is not None:
            fail('events', 'unfinished tool proposal')
        equal('model_tokens', state['model_tokens'], tokens)
        equal('rejected_calls', state['rejected_calls'], rejections)
        equal('controller_substitutions', state['controller_substitutions'], 0)
        reserved_http = len(http_requests) + len(search_requests)
        equal('http_calls', state['http_calls'], reserved_http)
        equal('HTTP_REQUEST/SEARCH_REQUEST.call', reservation_order, list(range(1, reserved_http + 1)))
        budget = state['policy']['budget']
        if len(actual_proposals) > budget['max_steps'] or state['http_calls'] > budget['max_http_calls']:
            fail('budget', 'tool/HTTP reservation limit exceeded')
        if state['mode'] != 'agent' and (model_proposals or state['model_calls']):
            fail('mode', 'workflow contains model decisions')
        if state['mode'] == 'agent':
            calls = state['model_calls']
            if len(calls) not in (len(model_proposals), len(model_proposals) + 1):
                fail('model_calls', 'attempt count differs from successful proposals and one possible failure')
            for index, call in enumerate(calls):
                if call != {'status': 'STARTED'} and call not in model_observations:
                    fail('model_calls[' + str(index) + ']', 'final envelope absent from model observations')
        for ident, receipt in sources.items():
            if ident in state['projections']:
                equal('projections.' + ident, state['projections'][ident], parse_receipt(receipt))
        for ident, row in evidence.items():
            binding = bind_quote(sources[row['source_id']], row['quote'], start=row['start'])
            for key, value in binding.items():
                equal('evidence.' + ident + '.' + key, row.get(key), value)
        for index, proposal, result in tool_results:
            tool, args = proposal['tool'], proposal['args']
            if tool == 'retrieve':
                equal('retrieve.source', sources[result['source_id']]['request']['url'], args['url'])
            elif tool == 'extract':
                equal('extract.evidence', {k: v for k, v in result.items() if k != 'evidence_id'}, evidence[result['evidence_id']])
            elif tool == 'compare' and result not in state['comparisons']:
                fail('compare', 'recorded comparison absent from final state')
            elif tool == 'finish':
                equal('finish.report', result, state['report'])
        if len(discovery_results) != len(state['discovery_history']):
            fail('discovery_history', 'successful discovery count mismatch')
        for (_, result), snapshot in zip(discovery_results, state['discovery_history']):
            equal('discovery_history.intake_sha256', result['intake_sha256'], sha256_json(snapshot))
            equal('discovery_history.candidate_ids', result['candidate_ids'],
                  [c['id'] for c in snapshot['discovery']['contract_candidates']])
            if validate_manifest(snapshot, require_complete=True):
                fail('discovery_history', 'invalid draft discovery snapshot')
        intake = state['intake']
        if intake:
            for error in validate_manifest(intake):
                fail('intake', error)
            if not any(a.get('id') == 'asm.semantic' and a.get('status') == 'Unknown'
                       for a in intake['discovery']['assumptions']):
                fail('intake.assumptions', 'semantic-correspondence Unknown obligation was removed or promoted')
            available = dict(sources)
            available.update({'searchsrc.' + str(i): row['receipt'] for i, row in enumerate(state['searches'], 1)})
            for declared in intake['discovery']['sources']:
                receipt = available[declared['id']]
                for key, expected in (('sha256', receipt['sha256']), ('locator', receipt['request']['url']),
                                      ('retrieved_at', receipt['retrieved_at'])):
                    equal('intake.source.' + declared['id'] + '.' + key, declared[key], expected)
            candidates = {c['id']: c for c in intake['discovery']['contract_candidates']}
            for candidate in candidates.values():
                equal('candidate.' + candidate['id'], candidate['sha256'], sha256_json(candidate['contract']))
            native_successes, native_failures = {}, 0
            for request_index, payload in native_requests:
                ident = payload['candidate']['id']
                if ident not in candidates:
                    fail('native_request', 'candidate absent from frozen family')
                    continue
                equal('native_request.contract', payload['candidate'], candidates[ident])
                equal('native_request.freeze', payload['freeze'], intake['freeze'])
                expected = verify(candidates[ident]['contract']['plan'], question, sources, evidence)
                terminal = next((e for e in events[request_index:]
                                 if e['kind'] in ('TOOL_RESULT', 'TOOL_REJECTED')), None)
                if terminal is None:
                    fail('native_request', 'attempt lacks recorded result or failure')
                elif terminal['kind'] == 'TOOL_REJECTED':
                    # A transient execution failure can recompute successfully;
                    # its recorded failure remains a failure and supplies no proof.
                    native_failures += 1
                else:
                    equal('native_request.result.tool', terminal['payload']['tool'], 'verify')
                    equal('native_request.result', terminal['payload']['result']['result'], expected)
                    native_successes[request_index] = ident
            counters.update(native_attempts_recomputed=len(native_requests),
                            native_failed_attempts=native_failures)
            equal('intake.evaluations', intake['evaluations'], [{k: v for k, v in row.items() if k != 'result'} for row in state['evaluations']])
            seen = set()
            for row in state['evaluations']:
                ident = row['contract_id']
                if ident in seen:
                    fail('evaluations', 'duplicate candidate')
                seen.add(ident)
                candidate = candidates[ident]
                equal('evaluation.contract_sha256', row['contract_sha256'], candidate['sha256'])
                equal('evaluation.freeze_sha256', row['freeze_sha256'], intake['freeze']['freeze_sha256'])
                expected = verify(candidate['contract']['plan'], question, sources, evidence)
                equal('evaluation.native_result.' + ident, row['result'], expected)
                equal('evaluation.outcome.' + ident, row['outcome'], expected['outcome'])
                if timestamp(row['evaluated_at']) < timestamp(intake['freeze']['frozen_at']):
                    fail('evaluation', 'evaluation predates freeze')
                matching = [(i, p) for i, p in native_requests if native_successes.get(i) == ident]
                if len(matching) != 1:
                    fail('evaluation', 'one exact native request required per evaluated candidate')
                else:
                    equal('native_request.candidate', matching[0][1]['candidate'], candidate)
                    equal('native_request.freeze', matching[0][1]['freeze'], intake['freeze'])
            if intake['freeze']['status'] == 'FROZEN':
                if len(freeze_events) != 1:
                    fail('freeze', 'one successful freeze event required')
                else:
                    equal('freeze.event', freeze_events[0][1], intake['freeze'])
                    frozen_index = freeze_events[0][0]
                    if any(i <= frozen_index for i, _ in native_requests):
                        fail('native_request', 'native evaluation request predates successful freeze')
                    discovery_index = discovery_results[-1][0] if discovery_results else frozen_index
                    passes = [(i, p, r) for i, p, r in tool_results if p['tool'] == 'recheck' and discovery_index < i < frozen_index]
                    if not passes:
                        fail('freeze', 'terminal recheck must follow final discovery')
                    if len(state['rechecks']) != len(sources) or any(not r['unchanged_projection'] for r in state['rechecks']):
                        fail('freeze', 'all source projections require unchanged terminal receipts')
                    for record in state['rechecks']:
                        if not any(record == p for _, p in source_rechecks):
                            fail('freeze', 'terminal source record absent from event history')
        elif state['evaluations'] or native_requests:
            fail('evaluations', 'native execution without intake')
        for row in state['far_verifications']:
            matching = [r for r in sources.values() if r['sha256'] == row['source_sha256']]
            if not matching:
                fail('far_verifications', 'unknown source hash')
            else:
                equal('far_verifications.result', row['result'], route_text(receipt_bytes(matching[0]).decode()))
        report = state['report']
        if report:
            if not intake:
                fail('report', 'report without frozen intake')
            else:
                equal('report.aggregate', report['aggregate'], aggregate_manifest(intake))
            equal('report.native_results', report['native_results'], state['evaluations'])
            equal('report.investigation_closure', report['investigation_closure'], 'Incomplete')
            if any(i not in evidence for i in report['evidence_ids']):
                fail('report', 'nonexistent evidence reference')
        if state['status'] == 'BOUNDED_PIPELINE_COMPLETED':
            if not report or not intake or aggregate_manifest(intake)['outcome'] in ('INCOMPLETE', 'INVALID'):
                fail('completion', 'completed pipeline lacks complete frozen evaluated report')
            if not any(p['tool'] == 'finish' for _, p, _ in tool_results):
                fail('completion', 'completed pipeline lacks successful finish event')
            if state['elapsed_seconds'] > budget['max_seconds'] or state['model_tokens'] > budget['max_model_tokens']:
                fail('completion', 'completed pipeline exceeded declared time/token budget')
        counters.update(tool_proposals=len(actual_proposals), model_proposals=len(model_proposals),
                        model_tokens=tokens, http_reservations=reserved_http, rejected_calls=rejections)

    guarded('transcript', inspect)
    return {'schema': 'far-investigation-integrity/0.1', 'errors': errors, 'valid': not errors,
            'reconstructed_counters': counters,
            'assurance': 'Internal mechanical consistency and native recomputation only. Self-signed hashes establish no external authenticity, source truth, semantic adequacy or independent evaluation.'}
