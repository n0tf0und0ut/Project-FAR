"""Offline integrity reconstruction for Research investigation transcripts.

Hashes are self-signed consistency evidence, not external authenticity, source
truth, semantic adequacy, independent evaluation, or protection from an author
rewriting a whole history. No network or model is invoked by this audit.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import math
from datetime import datetime
from urllib.parse import urlsplit

from mechanization.far_mechanization.intake_v1 import aggregate_manifest, freeze_manifest, sha256_json, validate_manifest
from tools.far_investigation_retrieval import (
    bind_quote, parse_receipt, receipt_bytes, project_public_search, public_search_url,
)
from tools.far_investigation_verifiers import verify
from tools.far_routing_dispatch import _parse, route_text
from tools.far_investigation_usage import model_usage_report, model_usage_tokens


def audit(state) -> dict:
    # Imported lazily: the runtime exposes this auditor through a lazy wrapper.
    from tools.far_investigation_engine import (
        build_discovery, build_inspection, build_report, validate_dispatch, validate_proposal,
        select_native_candidate,
    )
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

    def accepted_transport(path, transport, encoded, digest, size, request_url=None):
        if (type(transport) is not dict or transport.get('http_status') != 200
                or transport.get('response_complete') is not True
                or transport.get('response_truncated') is not False
                or transport.get('response_hash_scope') != 'complete_body'
                or any(transport.get(key) is not None for key in ('transport_error', 'framing_error', 'error'))):
            fail(path, 'accepted observation contradicts its transport completion/status/error flags')
            return
        equal(path + '.body', transport['raw_response_base64'], encoded)
        equal(path + '.hash', transport['response_sha256'], digest)
        equal(path + '.bytes', transport['response_bytes_retained'], size)
        # Completion flags cannot override the native reader's declared HTTP
        # framing. Reconstruct Content-Length from retained header metadata.
        headers = transport.get('response_headers', {})
        header_lengths = ([value for key, value in headers.items()
                           if type(key) is str and key.lower() == 'content-length']
                          if type(headers) is dict else [])
        header_encodings = ([value for key, value in headers.items()
                             if type(key) is str and key.lower() == 'transfer-encoding']
                            if type(headers) is dict else [])
        # Frozen native envelopes predate the get_all() lists. Their retained
        # headers still supply declared framing; no missing wire bytes are invented.
        lengths = transport.get('content_length_values', header_lengths)
        encodings = transport.get('transfer_encoding_values', header_encodings)
        if (type(headers) is not dict or type(lengths) is not list or type(encodings) is not list
                or any(type(k) is not str or type(v) is not str for k, v in headers.items())
                or any(type(value) is not str for value in lengths + encodings)):
            fail(path + '.framing', 'malformed HTTP framing metadata')
        else:
            # The reader records both the header map and get_all() lists. For
            # accepted framing there is at most one header of either kind;
            # omitting/changing one copy cannot erase a declared constraint.
            equal(path + '.framing.content_length_headers', lengths, header_lengths)
            equal(path + '.framing.transfer_encoding_headers', encodings, header_encodings)
            if lengths:
                if (len(lengths) != 1 or type(lengths[0]) is not str
                        or not lengths[0].isascii() or not lengths[0].strip().isdigit()
                        or len(lengths[0].strip()) > 20 or int(lengths[0].strip()) != size):
                    fail(path + '.content_length', 'completed body length contradicts HTTP Content-Length')
            if encodings and (len(encodings) != 1 or encodings[0].strip().lower() != 'chunked' or lengths):
                fail(path + '.framing.transfer_encoding', 'unsupported or ambiguous transfer framing')
        if request_url is not None:
            equal(path + '.request_url', transport['request_url'], request_url)

    def search_projection(path, row):
        # Operator-installed test/other adapters retain their explicit result
        # boundary. Native adapters are independently reprojected by the same
        # pure implementation used by their actual transport path.
        if urlsplit(row['receipt']['request']['url']).hostname in ('api.crossref.org', 'en.wikipedia.org'):
            equal(path + '.url', row['receipt']['request']['url'], public_search_url(row['query'], row['provider']))
            equal(path + '.projection', row, project_public_search(row['query'], row['provider'], row['receipt']))

    def envelope_tree(node, path='state', depth=0):
        if depth > 128:
            fail(path, 'nesting exceeds audit bound')
            return
        if type(node) is dict:
            if 'timing_scope' in node:
                def check_transport_time():
                    if node['timing_scope'] != 'request_start_to_body_read_or_transport_failure':
                        raise ValueError('unknown timing scope')
                    if timestamp(node['received_at']) < timestamp(node['requested_at']):
                        raise ValueError('transport completion predates request')
                guarded(path + '.transport_time', check_transport_time)
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
                    # Old frozen receipts have no transport framing envelope;
                    # do not fabricate one or retroactively certify framing.
                    if 'transport' in node:
                        accepted_transport(path + '.transport', node['transport'], node['raw_base64'],
                                           node['sha256'], node['observed_bytes'], node['request']['url'])
                        # A native retrieval derives parser-driving metadata
                        # from the observed response headers. A resealed trace
                        # cannot change the headers while retaining a projection
                        # computed under another content type or encoding.
                        headers = node['transport'].get('response_headers')
                        if type(headers) is not dict or any(
                                type(k) is not str or type(v) is not str
                                for k, v in headers.items()):
                            fail(path + '.transport.response_headers', 'invalid native headers')
                        else:
                            normalized = {k.lower(): v for k, v in headers.items()}
                            equal(path + '.transport.content_type', node.get('content_type'),
                                  normalized.get('content-type', ''))
                            equal(path + '.transport.content_encoding', node.get('content_encoding'),
                                  normalized.get('content-encoding', 'identity'))
                            equal(path + '.transport.response_url', node.get('response_url'),
                                  node['transport'].get('response_url', node['request']['url']))
                            equal(path + '.transport.http_status', node.get('http_status'),
                                  node['transport'].get('http_status'))
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
        elapsed, budget = state['elapsed_seconds'], state['policy']['budget']
        if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0:
            fail('elapsed_seconds', 'must be a finite nonnegative execution duration')
        limits = {'max_steps': 100, 'max_http_calls': 100, 'max_model_tokens': 200000, 'max_seconds': 3600}
        if set(budget) != set(limits):
            fail('budget', 'exact runtime budget fields required')
        for key, maximum in limits.items():
            value = budget.get(key)
            types = (int, float) if key == 'max_seconds' else (int,)
            if type(value) not in types or not math.isfinite(value) or not 0 < value <= maximum:
                fail('budget.' + key, 'invalid runtime budget type or bound')
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
        absent = object()
        tool_pending, model_pending = absent, absent
        model_proposals, actual_proposals = [], []
        model_attempt_envelopes, latest_model_observation = [], None
        model_attempt_usage, observed_attempt_usage = [], set()
        tool_results, tool_attempts, source_rechecks, native_requests = [], [], [], []
        attempt_native_requests, native_by_attempt = [], {}
        http_requests, search_requests, reservation_order, rejections, tokens = [], [], [], 0, 0
        discovery_results, freeze_events = [], []
        attempt_rechecks, attempt_searches, attempt_terminal = [], [], None
        attempt_details = {}
        attempt_search_request, attempt_search_observation = None, None
        attempt_network_started = False
        attempt_committed_rechecks = 0
        search_transports = {}
        retrieval_transports, attempt_http, attempt_observation = [], None, None
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
                latest_model_observation = payload
                count = model_usage_tokens(payload)
                if count is not None:
                    observed_attempt_usage.add(count)
            elif kind == 'MODEL_PROPOSAL':
                if model_pending is not absent:
                    fail(path, 'previous model proposal never dispatched')
                model_pending = payload['proposal']
                model_proposals.append(payload)
                model_attempt_envelopes.append(latest_model_observation or {'status': 'STARTED'})
                model_attempt_usage.append(observed_attempt_usage)
                if payload['metadata'].get('envelope') is not None:
                    equal(path + '.model_attempt_envelope', payload['metadata']['envelope'], latest_model_observation)
                latest_model_observation = None
                observed_attempt_usage = set()
                count = payload['metadata']['tokens']
                if type(count) is not int or count < 1:
                    fail(path, 'invalid model token telemetry')
                else:
                    tokens += count
                env = payload['metadata'].get('envelope')
                if env and 'transport' in env:
                    raw = base64.b64decode(env['response_base64'], validate=True)
                    accepted_transport(path + '.model_transport', env['transport'], env['response_base64'],
                                       env['response_sha256'], len(raw))
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
                # The runtime checks the token budget before journaling a new
                # proposal, even when a later operation fails. An exhausted
                # model response cannot produce downstream tool side effects.
                if state['mode'] == 'agent' and tokens >= budget['max_model_tokens']:
                    fail(path + '.token_budget', 'tool proposal follows exhausted model token budget')
                if tool_pending is not absent:
                    fail(path, 'previous tool proposal has no recorded outcome')
                if state['mode'] == 'agent':
                    equal(path + '.model_to_tool', payload, model_pending)
                model_pending = absent
                tool_pending = payload
                attempt_http, attempt_observation = None, None
                attempt_rechecks, attempt_searches, attempt_terminal = [], [], None
                attempt_search_request, attempt_search_observation = None, None
                attempt_network_started = False
                attempt_committed_rechecks = 0
                attempt_native_requests = []
                actual_proposals.append(payload)
            elif kind == 'HTTP_REQUEST':
                http_requests.append(payload)
                reservation_order.append(payload['call'])
                attempt_http = payload
                attempt_network_started = True
                attempt_committed_rechecks = len(attempt_rechecks)
            elif kind == 'HTTP_OBSERVATION':
                attempt_observation = payload
            elif kind == 'SEARCH_REQUEST':
                search_requests.append(payload)
                reservation_order.append(payload['call'])
                attempt_search_request, attempt_search_observation = payload, None
                attempt_network_started = True
                attempt_committed_rechecks = len(attempt_rechecks)
            elif kind in ('SEARCH_OBSERVATION', 'SEARCH_RECHECK_OBSERVATION'):
                attempt_search_observation = payload
            elif kind == 'SOURCE_RECHECK':
                guarded(path + '.proposal', lambda: validate_proposal(tool_pending))
                if type(tool_pending) is not dict or tool_pending.get('tool') != 'recheck':
                    fail(path + '.source_recheck', 'source recheck outside its producing attempt')
                original = sources[payload['source_id']]
                if attempt_http is None or attempt_observation is None:
                    fail(path + '.source_recheck', 'receipt lacks request-bound HTTP observation')
                else:
                    equal(path + '.source_recheck.url', attempt_http['url'], original['request']['url'])
                    equal(path + '.source_recheck.observation', attempt_observation, payload['receipt'])
                attempt_http, attempt_observation = None, None
                equal(path + '.request', payload['receipt']['request']['url'], original['request']['url'])
                if payload['source_id'] not in state['projections']:
                    fail(path + '.original_projection', 'source recheck requires its actually retained original projection')
                else:
                    stable = (parse_receipt(payload['receipt'])['projection_sha256']
                              == state['projections'][payload['source_id']]['projection_sha256'])
                    equal(path + '.unchanged_projection', payload['unchanged_projection'], stable)
                source_rechecks.append((index, payload))
                attempt_committed_rechecks = len(attempt_rechecks)
                attempt_rechecks.append(payload)
            elif kind == 'DISCOVERY_TERMINAL_RECHECK':
                if type(tool_pending) is not dict or tool_pending.get('tool') != 'recheck':
                    fail(path + '.proposal', 'terminal discovery recheck outside its producing attempt')
                guarded(path + '.proposal', lambda: validate_proposal(tool_pending))
                attempt_terminal = payload['intake']
            elif kind == 'SEARCH_RECHECK':
                original = state['searches'][payload['index']]
                if type(tool_pending) is not dict or tool_pending.get('tool') != 'recheck' or attempt_search_request is None:
                    fail(path + '.search_recheck', 'search recheck outside its request-bound attempt')
                else:
                    equal(path + '.search_recheck.index', attempt_search_request.get('recheck_index'), payload['index'])
                    for key in ('query', 'provider'):
                        equal(path + '.search_recheck.' + key, attempt_search_request[key], original[key])
                        equal(path + '.search_recheck.result.' + key, payload['result'][key], original[key])
                equal(path + '.search_recheck.observation', attempt_search_observation, payload['result']['receipt'])
                equal(path + '.search_recheck.hits', payload['result']['hits'], original['hits'])
                search_projection(path + '.search_recheck', payload['result'])
                attempt_search_request, attempt_search_observation = None, None
                attempt_searches.append(payload)
            elif kind == 'NATIVE_VERIFIER_REQUEST':
                guarded(path + '.proposal', lambda: validate_proposal(tool_pending))
                if (type(tool_pending) is not dict or tool_pending.get('tool') != 'verify'
                        or tool_pending.get('args', {}).get('candidate_id') != payload['candidate']['id']):
                    fail(path, 'native verifier invocation differs from actual proposal')
                native_requests.append((index, payload))
                attempt_native_requests.append((index, payload))
            elif kind in ('TOOL_RESULT', 'TOOL_REJECTED'):
                valid_shape = False
                if tool_pending is not absent:
                    try:
                        validate_proposal(tool_pending)
                        valid_shape = True
                    except (ValueError, TypeError):
                        if kind == 'TOOL_RESULT':
                            fail(path + '.proposal', 'accepted operation violates the runtime proposal contract')
                        if attempt_rechecks or attempt_searches or attempt_terminal is not None:
                            fail(path + '.proposal.effects', 'invalid proposal cannot produce discovery/recheck effects')
                    tool_attempts.append((index, tool_pending, kind, payload))
                    native_by_attempt[index] = attempt_native_requests
                    attempt_details[index] = (attempt_rechecks, attempt_searches, attempt_terminal,
                                              attempt_network_started, attempt_committed_rechecks)
                    if valid_shape and tool_pending['tool'] == 'search':
                        search_transports[index] = (attempt_search_request, attempt_search_observation)
                if (valid_shape and tool_pending['tool'] == 'retrieve'
                        and attempt_http is not None and attempt_observation is not None):
                    retrieval_transports.append((index, tool_pending['args'].get('url'),
                                                 attempt_http['url'], attempt_observation))
                if tool_pending is absent:
                    fail(path, 'tool outcome lacks a proposal')
                elif kind == 'TOOL_RESULT' and valid_shape:
                    equal(path + '.tool', payload['tool'], tool_pending.get('tool'))
                    tool_results.append((index, tool_pending, payload['result']))
                    if payload['tool'] == 'discover':
                        discovery_results.append((index, payload['result']))
                    elif payload['tool'] == 'freeze':
                        freeze_events.append((index, payload['result']))
                elif kind == 'TOOL_REJECTED':
                    rejections += 1
                tool_pending = absent
        equal('START.kind', events[0]['kind'], 'START')
        equal('START.question_sha256', events[0]['payload']['question_sha256'], state['question_sha256'])
        equal('START.policy', events[0]['payload']['policy'], state['policy'])
        seals = [event for event in events if event['kind'] == 'FINAL_STATE_SEAL']
        if len(seals) != 1 or events[-1]['kind'] != 'FINAL_STATE_SEAL':
            fail('final_state_seal', 'exactly one terminal seal required')
        else:
            equal('final_state_seal', seals[0]['payload']['state_sha256'],
                  sha256_json({k: v for k, v in state.items() if k != 'events'}))
        if tool_pending is not absent:
            fail('events', 'unfinished tool proposal')
        accepted_tokens = tokens
        accounting = state.get('model_token_accounting')
        if accounting is not None and accounting != 'validated-response-per-attempt/1':
            fail('model_token_accounting', 'unknown accounting rule')
        if accounting == 'validated-response-per-attempt/1':
            tokens = 0
            for attempt, call in enumerate(state['model_calls']):
                observed = model_usage_tokens(call)
                # A failed final attempt has no accepted proposal fallback.
                tokens += observed if observed is not None else (
                    model_proposals[attempt]['metadata']['tokens'] if attempt < len(model_proposals) else 0)
        equal('model_tokens', state['model_tokens'], tokens)
        usage = model_usage_report(state)
        counters.update(model_token_accounting=accounting or 'legacy-accepted-proposal-counter',
                        accepted_proposal_tokens=accepted_tokens, raw_usage_audit=usage,
                        resource_validity_scope='Recorded counter consistency only; raw_usage_audit separately reports known response usage and unknown attempts. Neither is verified total consumption or billing.')
        equal('rejected_calls', state['rejected_calls'], rejections)
        equal('controller_substitutions', state['controller_substitutions'], 0)
        reserved_http = len(http_requests) + len(search_requests)
        equal('http_calls', state['http_calls'], reserved_http)
        equal('HTTP_REQUEST/SEARCH_REQUEST.call', reservation_order, list(range(1, reserved_http + 1)))
        if len(actual_proposals) > budget['max_steps'] or state['http_calls'] > budget['max_http_calls']:
            fail('budget', 'tool/HTTP reservation limit exceeded')
        if state['mode'] != 'agent' and (model_proposals or state['model_calls']):
            fail('mode', 'workflow contains model decisions')
        if state['mode'] == 'agent':
            calls = state['model_calls']
            if len(calls) not in (len(model_proposals), len(model_proposals) + 1):
                fail('model_calls', 'attempt count differs from successful proposals and one possible failure')
            if len(calls) == len(model_proposals) + 1:
                model_attempt_envelopes.append(latest_model_observation or {'status': 'STARTED'})
                model_attempt_usage.append(observed_attempt_usage)
            equal('model_calls.attempt_order', calls, model_attempt_envelopes)
            for attempt, (call, observed) in enumerate(zip(calls, model_attempt_usage)):
                if observed and observed != {model_usage_tokens(call)}:
                    fail('model_calls[' + str(attempt) + '].usage', 'validated usage changed or disappeared within one attempt')
        source_available_at = {}
        expected_projections = {}
        successful_sources = {result['source_id']: index for index, proposal, result in tool_results
                              if proposal['tool'] == 'retrieve'}
        equal('sources.allocation', sorted(sources, key=lambda value: int(value.removeprefix('src.'))),
              ['src.' + str(i) for i in range(1, len(sources) + 1)])
        # IDs follow the runtime's allocation order. Canonical JSON sorts src.10
        # before src.2, so object iteration cannot disambiguate repeated identical
        # failure receipts. Successful retrievals additionally name their producer.
        for ident in sorted(sources, key=lambda value: int(value.removeprefix('src.'))):
            receipt = sources[ident]
            matching = next((i for i, (at, requested, observed, transport) in enumerate(retrieval_transports)
                             if requested == observed == receipt['request']['url']
                             and at == successful_sources.get(ident, at)
                             and sha256_json(transport) == sha256_json(receipt)), None)
            if matching is None:
                fail('sources.' + ident, 'retained source lacks its exact retrieval transport observation')
            else:
                source_available_at[ident] = retrieval_transports.pop(matching)[0]
            if ident in state['projections'] or ident in successful_sources:
                try:
                    expected_projections[ident] = parse_receipt(receipt)
                except (ValueError, KeyError, TypeError, UnicodeError):
                    pass  # Raw parser failures legitimately retain no projection.
        producing_order = list(source_available_at.values())
        if any(earlier >= later for earlier, later in zip(producing_order, producing_order[1:])):
            fail('sources.allocation_order', 'source IDs must follow their retained retrieval producing order')
        equal('projections.coverage', state['projections'], expected_projections)
        for ident, row in evidence.items():
            binding = guarded('evidence.' + ident, lambda: bind_quote(
                sources[row['source_id']], row['quote'], start=row['start']))
            if binding is not None:
                for key, value in binding.items():
                    equal('evidence.' + ident + '.' + key, row.get(key), value)
        def source_view(ident):
            projection = available_projections[ident]
            return {'url': available_sources[ident]['request']['url'], 'format': projection['format'],
                    'text': projection['text'][:3000], 'source_length': len(projection['text']),
                    'text_truncated_for_model': len(projection['text']) > 3000,
                    'links': projection['links'][:25], 'authority': 'UNTRUSTED_DATA'}

        def extraction(args):
            if (set(args) != {'source_id', 'quote', 'relation', 'claim'}
                    or type(args['relation']) is not str
                    or args['relation'].upper() not in ('SUPPORT', 'CONTRADICT', 'CONTEXT')
                    or type(args['claim']) is not str or not args['claim'].strip()
                    or len(args['quote']) > 4000):
                raise ValueError('invalid extraction proposal')
            return {**args, **bind_quote(available_sources[args['source_id']], args['quote']),
                    'relation': args['relation'].upper(), 'relation_assurance': 'FALLIBLE_ANALYST_JUDGMENT'}

        def comparison(args, available):
            ids = args['evidence_ids']
            alternatives = args.get('alternatives', [])
            if (type(ids) is not list or not ids or len(set(ids)) != len(ids)
                    or type(alternatives) is not list or any(type(x) is not str for x in alternatives)):
                raise ValueError('invalid comparison proposal')
            rows, groups = [available[ident] for ident in ids], {}
            for row in rows:
                host = available_projections[row['source_id']]['dependency_host']
                groups.setdefault(host, []).append(row['source_id'])
            return {'evidence_ids': ids, 'publisher_host_groups': groups,
                    'independence': 'UNESTABLISHED; different hosts do not establish independent origins',
                    'asserted_conflict': any(r['relation'] == 'SUPPORT' for r in rows)
                        and any(r['relation'] == 'CONTRADICT' for r in rows),
                    'conflict_assurance': 'relation labels are fallible; no automatic semantic entailment',
                    'alternatives': alternatives,
                    'source_evaluation': 'Quote integrity checked; truth, directness and authority require substantive review.'}

        produced_evidence, produced_comparisons, produced_far, produced_searches = {}, [], [], []
        def accepted_producers(tool, rows, projection):
            reserved = {}
            for at, proposal, result in tool_results:
                if proposal['tool'] != tool:
                    continue
                for offset, row in enumerate(rows):
                    if offset not in reserved and sha256_json(projection(row)) == sha256_json(result):
                        reserved[offset] = at
                        break
            return reserved

        successful_evidence_at = {result['evidence_id']: at for at, proposal, result in tool_results
                                  if proposal['tool'] == 'extract'}
        successful_comparison_at = accepted_producers('compare', state['comparisons'], lambda row: row)
        successful_far_at = accepted_producers('verify_far', state['far_verifications'], lambda row: row['result'])
        successful_discovery_at = {}
        for at, proposal, result in tool_results:
            if proposal['tool'] == 'discover':
                for offset, snapshot in enumerate(state['discovery_history']):
                    if offset not in successful_discovery_at and sha256_json(snapshot) == result['intake_sha256']:
                        successful_discovery_at[offset] = at
                        break
        evaluation_available_at = {}
        for row in state['evaluations']:
            accepted = [at for at, proposal, result in tool_results if proposal['tool'] == 'verify'
                        and sha256_json(result) == sha256_json(row)]
            if accepted:
                evaluation_available_at[row['contract_id']] = accepted[0]
                continue
            # A rejected native attempt may retain its completed diagnostic.
            # Prefer accepted producers above; an earlier failed retry cannot
            # borrow a row produced by a later actual native result.
            for request_index, request in native_requests:
                if request['candidate']['id'] != row['contract_id']:
                    continue
                terminal_index = next((at for at, _, _, _ in tool_attempts if at > request_index), None)
                if terminal_index is not None and (timestamp(events[request_index - 1]['at'])
                        <= timestamp(row['evaluated_at']) <= timestamp(events[terminal_index - 1]['at'])):
                    evaluation_available_at[row['contract_id']] = terminal_index
        successful_search_at = accepted_producers('search', state['searches'],
            lambda row: {k: v for k, v in row.items() if k != 'receipt'})
        replay_intake, replay_rechecks, missing_evidence = None, [], None
        replay_recheck_prefixes, replay_recheck_complete = [[]], False
        produced_freeze_index = None
        history_offset = 0
        completed = set()
        frozen_index = freeze_events[0][0] if freeze_events else len(events) + 1
        for index, proposal, kind, payload in tool_attempts:
            # Retrieval can preserve a source even when parsing or the later
            # budget check rejects the call. Its bytes/projection become usable
            # only after that producing attempt, never from the final inventory
            # while reconstructing an earlier failed or forged operation.
            available_sources = {ident: sources[ident] for ident, at in source_available_at.items() if at <= index}
            available_projections = {ident: state['projections'][ident] for ident in available_sources
                                     if ident in state['projections']}
            accepted = kind == 'TOOL_RESULT'
            result = payload['result'] if accepted else None
            try:
                tool, args = validate_dispatch(proposal, replay_intake, completed)
            except (ValueError, TypeError):
                if accepted:
                    fail('tool.proposal', 'accepted dispatch violates runtime shape/state preconditions')
                if any(at == index for at in source_available_at.values()):
                    fail('tool.proposal.effects', 'rejected dispatch precondition cannot produce retained sources')
                continue
            fingerprint = sha256_json(proposal)
            if tool == 'verify':
                requests = native_by_attempt[index]
                if accepted and len(requests) != 1:
                    fail('verify.producer', 'accepted verification requires exactly one native request in its own attempt')
                elif len(requests) > 1:
                    fail('verify.producer', 'one attempt cannot produce multiple native requests')
                if accepted or requests:
                    available_evaluations = [row for row in state['evaluations']
                        if evaluation_available_at.get(row['contract_id'], len(events) + 1) < index]
                    candidate = guarded('verify.proposal', lambda: select_native_candidate(
                        replay_intake, args, available_evaluations))
                    if candidate is not None:
                        for _, request in requests:
                            equal('verify.request.candidate', request['candidate'], candidate)
                            equal('verify.request.freeze', request['freeze'], replay_intake['freeze'])
                if accepted:
                    retained = [row for row in state['evaluations'] if sha256_json(row) == sha256_json(result)]
                    if len(retained) != 1 or evaluation_available_at.get(retained[0]['contract_id']) != index:
                        fail('verify.evaluation', 'accepted result requires its exact retained evaluation produced by this attempt')
            previous_effects = (len(produced_evidence), len(produced_comparisons))
            search_effect = False
            if tool == 'search' and index < frozen_index:
                offset = len(produced_searches)
                row = state['searches'][offset] if offset < len(state['searches']) else None
                request, observation = search_transports[index]
                if row is not None and request is not None and observation is not None:
                    bound = (row.get('query') == args.get('query') == request.get('query')
                             and row.get('provider') == args.get('provider') == request.get('provider')
                             and sha256_json(row.get('receipt')) == sha256_json(observation)
                             and successful_search_at.get(offset, index) == index)
                    if accepted or bound:
                        if not bound:
                            fail('search.producer', 'retained search differs from actual request/observation')
                        if accepted:
                            equal('search.result', result, {k: v for k, v in row.items() if k != 'receipt'})
                        search_projection('search', row)
                        produced_searches.append(row)
                        search_effect = True
                elif accepted:
                    fail('search.producer', 'successful search lacks retained request-bound observation')
            if tool in ('extract', 'compare'):
                # Effects can be retained before the post-dispatch budget check
                # rejects a call. Reconstruct those effects too, but a frozen or
                # duplicate pre-dispatch rejection cannot produce another row.
                eligible = index < frozen_index and fingerprint not in completed
                if accepted and not eligible:
                    fail(tool + '.proposal', 'accepted mutable output after freeze or duplicate completion')
                if eligible:
                    try:
                        expected = extraction(args) if tool == 'extract' else comparison(args, produced_evidence)
                    except Exception as exc:
                        if accepted:
                            fail(tool + '.proposal', 'cannot reconstruct accepted output: ' + type(exc).__name__)
                        expected = None
                    if expected is not None:
                        if tool == 'extract':
                            ident = 'ev.' + str(len(produced_evidence) + 1)
                            if accepted:
                                equal('extract.evidence_id', result['evidence_id'], ident)
                                equal('extract.proposal', {k: v for k, v in result.items() if k != 'evidence_id'}, expected)
                            if accepted or (evidence.get(ident) == expected and successful_evidence_at.get(ident, index) == index):
                                produced_evidence[ident] = expected
                        else:
                            if accepted:
                                equal('compare.proposal', result, expected)
                            offset = len(produced_comparisons)
                            if accepted or (offset < len(state['comparisons']) and state['comparisons'][offset] == expected
                                            and successful_comparison_at.get(offset, index) == index):
                                produced_comparisons.append(expected)
            # These actual mutable effects invalidate the draft and its terminal
            # stability pass even when the later budget check rejects the call.
            if (previous_effects != (len(produced_evidence), len(produced_comparisons))
                    or search_effect
                    or (tool == 'retrieve' and any(at == index and ident in available_projections
                                                  for ident, at in source_available_at.items()))):
                replay_intake, replay_rechecks = None, []
                replay_recheck_prefixes, replay_recheck_complete = [[]], False
            if tool == 'discover':
                snapshot = (state['discovery_history'][history_offset]
                            if history_offset < len(state['discovery_history']) else None)
                expected = None
                if (snapshot is not None and index < frozen_index
                        and (accepted or successful_discovery_at.get(history_offset, index) == index)):
                    context = {**state, 'sources': available_sources, 'projections': available_projections,
                               'evidence': produced_evidence, 'comparisons': produced_comparisons,
                               'searches': produced_searches}
                    try:
                        expected = build_discovery(context, args,
                            cutoff=snapshot['discovery']['search_protocol']['evidence_cutoff'])
                    except Exception as exc:
                        if accepted:
                            fail('discover.proposal', 'cannot reconstruct accepted output: ' + type(exc).__name__)
                    if expected is not None:
                        # Canonical JSON preserves list order but sorts plan
                        # object keys. Provenance is keyed by unique JSON path;
                        # reconstruct every value while preserving the original
                        # path enumeration order across that serialization.
                        for actual_candidate, expected_candidate in zip(
                                snapshot['discovery']['contract_candidates'], expected['discovery']['contract_candidates']):
                            rows = {row['path']: row for row in expected_candidate['parameter_provenance']}
                            paths = [row['path'] for row in actual_candidate['parameter_provenance']]
                            if len(paths) == len(set(paths)) and set(paths) == set(rows):
                                expected_candidate['parameter_provenance'] = [rows[path] for path in paths]
                if accepted or (expected is not None and sha256_json(snapshot) == sha256_json(expected)):
                    if expected is None:
                        fail('discover.proposal', 'no reconstructable discovery snapshot')
                    else:
                        equal('discover.snapshot', snapshot, expected)
                        if accepted:
                            equal('discover.result', result, {
                                'candidate_ids': [c['id'] for c in expected['discovery']['contract_candidates']],
                                'intake_sha256': sha256_json(expected),
                                'errors': validate_manifest(expected, require_complete=True)})
                        replay_intake, replay_rechecks = copy.deepcopy(expected), []
                        replay_recheck_prefixes, replay_recheck_complete = [[]], False
                        missing_evidence = args.get('missing_evidence', [])
                        history_offset += 1
            elif tool == 'recheck':
                records, search_records, terminal, network_started, committed = attempt_details[index]
                registered = list(available_sources)
                can_start = (not args and bool(available_sources) and bool(produced_comparisons)
                             and not (replay_intake and replay_intake['freeze']['status'] == 'FROZEN'))
                if can_start or network_started or records or accepted or terminal is not None:
                    # Starting any successor pass revokes the prior completion,
                    # even when all sources pass and a later search fails.
                    replay_recheck_complete = False
                    equal('recheck.source_order', [r['source_id'] for r in records], registered[:len(records)])
                    replay_rechecks = []
                    for record in records:
                        if not record['unchanged_projection']:
                            break
                        replay_rechecks.append(record)
                    if accepted or terminal is not None:
                        replay_recheck_prefixes = [replay_rechecks]
                    else:
                        # SOURCE_RECHECK is journaled before the state append.
                        # Progress to another request/record proves earlier
                        # appends. The interrupted final observation can still
                        # be either side of that append; neither proves a pass.
                        lower = min(committed, len(replay_rechecks))
                        replay_recheck_prefixes = [replay_rechecks[:n]
                            for n in range(lower, len(replay_rechecks) + 1)]
                if accepted or terminal is not None:
                    if args or not produced_comparisons or len(replay_rechecks) != len(registered):
                        fail('recheck.completion', 'complete stable source pass required')
                    if len(search_records) != len(produced_searches):
                        fail('recheck.searches', 'complete stable search pass required')
                    equal('recheck.search_order', [r['index'] for r in search_records], list(range(len(produced_searches))))
                    replay_recheck_complete = (accepted and not args and bool(produced_comparisons)
                        and len(replay_rechecks) == len(registered)
                        and len(search_records) == len(produced_searches))
                if terminal is not None:
                    if replay_intake is None:
                        fail('recheck.discovery', 'terminal intake lacks proposal-derived discovery')
                    else:
                        protocol = terminal['discovery']['search_protocol']
                        cutoff = timestamp(protocol['evidence_cutoff'])
                        observed_at = timestamp(protocol['saturation_observations'][-1]['observed_at'])
                        if not (timestamp(replay_intake['discovery']['search_protocol']['evidence_cutoff'])
                                <= observed_at <= cutoff <= timestamp(events[index - 1]['at'])):
                            fail('recheck.time', 'terminal observation/cutoff outside producing interval')
                        updated = copy.deepcopy(replay_intake)
                        updated['discovery']['search_protocol']['evidence_cutoff'] = protocol['evidence_cutoff']
                        updated['discovery']['search_protocol']['saturation_observations'][-1]['observed_at'] = protocol['saturation_observations'][-1]['observed_at']
                        equal('recheck.intake', terminal, updated)
                        replay_intake = updated
                elif accepted and replay_intake is not None:
                    fail('recheck.discovery', 'successful draft recheck lacks terminal intake event')
                if accepted:
                    equal('recheck.result', result, {'rechecked_sources': len(replay_rechecks),
                        'rechecked_searches': len(produced_searches),
                        'scope': 'unchanged bounded projections only; not semantic or open-world completeness'})
            elif tool == 'freeze' and (accepted or (not freeze_events and not args and state['intake']
                    and state['intake']['freeze']['status'] == 'FROZEN' and replay_intake
                    and replay_intake['freeze']['status'] == 'DRAFT'
                    and replay_recheck_complete)):
                if args or replay_intake is None or len(replay_rechecks) != len(available_sources):
                    fail('freeze.proposal', 'complete proposal-derived terminal intake required')
                elif not replay_recheck_complete:
                    fail('freeze.recheck', 'latest full source and search recheck must complete before freeze')
                else:
                    expected = guarded('freeze.proposal', lambda: freeze_manifest(replay_intake,
                        frozen_at=state['intake']['freeze']['frozen_at']))
                    if expected is not None:
                        if accepted:
                            equal('freeze.proposal', result, expected['freeze'])
                        replay_intake = expected
                        produced_freeze_index = index
            if accepted:
                completed.add(fingerprint)
                if tool == 'retrieve':
                    ident = result['source_id']
                    equal('retrieve.source_chronology', source_available_at.get(ident), index)
                    equal('retrieve.source', sources[ident]['request']['url'], args['url'])
                    equal('retrieve.projection', result, {'source_id': ident, **source_view(ident)})
                elif tool == 'inspect':
                    if args['source_id'] not in available_projections:
                        fail('inspect.source_chronology', 'source projection was unavailable at this attempt')
                    else:
                        expected = guarded('inspect.proposal', lambda: build_inspection(
                            {'projections': available_projections}, args))
                        if expected is not None:
                            equal('inspect.projection', result, expected)
                elif tool == 'finish':
                    evaluated_intake = copy.deepcopy(replay_intake)
                    available_evaluations = [row for row in state['evaluations']
                        if evaluation_available_at.get(row['contract_id'], len(events) + 1) < index]
                    if evaluated_intake is not None:
                        evaluated_intake['evaluations'] = [{k: v for k, v in row.items() if k != 'result'}
                                                           for row in available_evaluations]
                    expected = guarded('finish.proposal', lambda: build_report({**state,
                        'intake': evaluated_intake, 'evaluations': available_evaluations,
                        'evidence': produced_evidence, 'missing_evidence': missing_evidence or []}, args))
                    if expected is not None:
                        equal('finish.proposal', result, expected)
                        equal('finish.report', state['report'], expected)
            if tool == 'verify_far' and (accepted or fingerprint not in completed):
                try:
                    receipt = available_sources[args['source_id']]
                    expected = {'source_sha256': receipt['sha256'], 'result': route_text(receipt_bytes(receipt).decode())}
                except Exception as exc:
                    if accepted:
                        fail('verify_far.proposal', 'cannot reconstruct accepted output: ' + type(exc).__name__)
                else:
                    if accepted:
                        equal('verify_far.proposal', result, expected['result'])
                    offset = len(produced_far)
                    if accepted or (offset < len(state['far_verifications']) and state['far_verifications'][offset] == expected
                                    and successful_far_at.get(offset, index) == index):
                        produced_far.append(expected)
        equal('evidence.coverage', evidence, produced_evidence)
        equal('compare.coverage', state['comparisons'], produced_comparisons)
        equal('far_verifications.coverage', state['far_verifications'], produced_far)
        equal('search.coverage', state['searches'], produced_searches)
        equal('discover.coverage', history_offset, len(state['discovery_history']))
        if missing_evidence is not None:
            equal('discover.missing_evidence', state.get('missing_evidence'), missing_evidence)
        if not any(sha256_json(state['rechecks']) == sha256_json(prefix) for prefix in replay_recheck_prefixes):
            fail('recheck.coverage', 'retained rechecks differ from possible committed observation prefix')
        if replay_intake is not None:
            equal('recheck.completion_marker', 'recheck_completed_at' in state, replay_recheck_complete)
        for (_, result), snapshot in zip(discovery_results, state['discovery_history']):
            equal('discovery_history.intake_sha256', result['intake_sha256'], sha256_json(snapshot))
            equal('discovery_history.candidate_ids', result['candidate_ids'],
                  [c['id'] for c in snapshot['discovery']['contract_candidates']])
            if validate_manifest(snapshot, require_complete=True):
                fail('discovery_history', 'invalid draft discovery snapshot')
        intake = state['intake']
        if intake is None:
            equal('discover.intake', replay_intake, None)
        elif replay_intake is None:
            fail('discover.intake', 'retained intake has no reconstructed producer')
        else:
            equal('discover.intake', {k: v for k, v in intake.items() if k != 'evaluations'},
                  {k: v for k, v in replay_intake.items() if k != 'evaluations'})
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
            native_producers, native_failures, retained_native_failures = {}, 0, 0
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
                if terminal is not None:
                    # Native evaluation mutates state before call() performs its
                    # post-dispatch budget check. Bind retained diagnostic rows
                    # to the exact invocation interval; never turn rejection
                    # into a successful tool outcome or pipeline completion.
                    rows = [row for row in state['evaluations'] if row['contract_id'] == ident
                            and timestamp(events[request_index - 1]['at']) <= timestamp(row['evaluated_at'])
                            <= timestamp(terminal['at'])]
                    if rows:
                        row = rows[0]
                        record = {'contract_id': ident, 'contract_sha256': candidates[ident]['sha256'],
                            'freeze_sha256': intake['freeze']['freeze_sha256'],
                            'evaluated_at': row['evaluated_at'], 'outcome': expected['outcome'],
                            'evidence_refs': ['urn:sha256:' + sources[e['source_id']]['sha256'] for e in produced_evidence.values()],
                            'result': expected}
                        if expected['outcome'] == 'Unknown':
                            record['notes'] = 'Native evidence does not determine original source truth or semantic adequacy.'
                        equal('native_request.retained_evaluation', row, record)
                        if terminal['kind'] == 'TOOL_RESULT':
                            equal('native_request.full_result', terminal['payload']['result'], record)
                        else:
                            retained_native_failures += 1
                        native_producers[request_index] = ident
            counters.update(native_attempts_recomputed=len(native_requests),
                            native_failed_attempts=native_failures,
                            native_rejected_attempts_with_retained_evaluation=retained_native_failures)
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
                matching = [(i, p) for i, p in native_requests if native_producers.get(i) == ident]
                if len(matching) != 1:
                    fail('evaluation', 'one exact native request required per evaluated candidate')
                else:
                    equal('native_request.candidate', matching[0][1]['candidate'], candidate)
                    equal('native_request.freeze', matching[0][1]['freeze'], intake['freeze'])
            if intake['freeze']['status'] == 'FROZEN':
                if produced_freeze_index is None or len(freeze_events) > 1:
                    fail('freeze', 'one exact reconstructed freeze-producing attempt required')
                else:
                    if freeze_events:
                        equal('freeze.event', freeze_events[0][1], intake['freeze'])
                    frozen_index = produced_freeze_index
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
            if not any(p['tool'] == 'finish' for _, p, _ in tool_results):
                fail('finish.coverage', 'retained report lacks an accepted finish producer')
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
            if state['elapsed_seconds'] >= budget['max_seconds'] or state['model_tokens'] >= budget['max_model_tokens']:
                fail('completion.elapsed_seconds/model_tokens', 'completed pipeline exhausted declared time/token budget')
        counters.update(tool_proposals=len(actual_proposals), model_proposals=len(model_proposals),
                        model_tokens=tokens, http_reservations=reserved_http, rejected_calls=rejections)

    guarded('transcript', inspect)
    return {'schema': 'far-investigation-integrity/0.1', 'errors': errors, 'valid': not errors,
            'reconstructed_counters': counters,
            'assurance': 'Internal mechanical consistency and native recomputation only. Self-signed hashes establish no external authenticity, source truth, semantic adequacy or independent evaluation.'}
