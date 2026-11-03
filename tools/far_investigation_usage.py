"""Raw model-usage reconstruction without accepting an action or rewriting history.

Usage is retained model-server telemetry, not an external billing measurement.
A missing value remains unknown; it never establishes that an attempt used zero
tokens. Repeated journal copies of a response are not separate model attempts.
"""
from __future__ import annotations

import base64
import hashlib

from tools.far_routing_dispatch import _parse


def model_usage_tokens(envelope):
    """Return validated total-token telemetry, or None when it is unavailable.

    Action shape and outer action-parsing errors are deliberately irrelevant.
    Historical envelopes without framing fields retain their original scope;
    envelopes that do carry framing evidence must establish a complete response.
    """
    if type(envelope) is not dict or envelope.get('fixture'):
        return None
    encoded, digest = envelope.get('response_base64'), envelope.get('response_sha256')
    if type(encoded) is not str or type(digest) is not str:
        return None
    try:
        raw = base64.b64decode(encoded, validate=True)
        if hashlib.sha256(raw).hexdigest() != digest:
            return None
        if 'transport' in envelope:
            transport = envelope['transport']
            if (type(transport) is not dict or type(transport.get('http_status')) is not int
                    or transport['http_status'] != 200
                    or transport.get('response_complete') is not True
                    or transport.get('response_truncated') is not False
                    or transport.get('response_hash_scope') != 'complete_body'
                    or any(transport.get(key) is not None for key in ('transport_error', 'framing_error', 'error'))
                    or transport.get('raw_response_base64') != encoded
                    or transport.get('response_sha256') != digest
                    or type(transport.get('response_bytes_retained')) is not int
                    or transport['response_bytes_retained'] != len(raw)):
                return None
        response = _parse(raw.decode('utf-8'))
        if type(response) is not dict or type(response.get('usage')) is not dict:
            return None
        tokens = response['usage'].get('total_tokens')
        return tokens if type(tokens) is int and tokens > 0 else None
    except (ValueError, TypeError, UnicodeError, RecursionError):
        return None


def model_usage_report(state):
    """Report known raw usage once per retained model-call attempt.

    This is additive audit output. The original state/campaign counters remain
    original observations even when they omitted usage from a rejected action.
    """
    attempts = state['model_calls']
    counts = [model_usage_tokens(envelope) for envelope in attempts]
    missing = [index for index, count in enumerate(counts) if count is None]
    return {
        'schema': 'far-investigation-raw-usage-audit/1',
        'recorded_model_tokens': state['model_tokens'],
        'validated_response_tokens_lower_bound': sum(count for count in counts if count is not None),
        'attempts_with_usage': len(attempts) - len(missing),
        'attempts_without_usage': len(missing),
        'missing_usage_attempt_indices': missing,
        'all_attempts_have_usage': not missing,
        'scope': 'Validated retained response telemetry once per model attempt; missing or incomplete responses leave usage unknown. No billing, external authentication or unobserved timed-out work is reconstructed.',
    }
