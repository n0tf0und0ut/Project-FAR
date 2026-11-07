"""Raw-usage accounting regressions; no model or network is invoked."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import unittest
import zipfile

from tools.far_investigation_usage import model_usage_report, model_usage_tokens


def envelope(response, *, transport=True):
    raw = response if isinstance(response, bytes) else json.dumps(response).encode()
    encoded, digest = base64.b64encode(raw).decode(), hashlib.sha256(raw).hexdigest()
    result = {'response_base64': encoded, 'response_sha256': digest}
    if transport:
        result['transport'] = {'http_status': 200, 'response_complete': True,
            'response_truncated': False, 'response_hash_scope': 'complete_body',
            'raw_response_base64': encoded, 'response_sha256': digest,
            'response_bytes_retained': len(raw), 'transport_error': None, 'framing_error': None}
    return result


class ModelUsageTests(unittest.TestCase):
    def test_valid_usage_survives_rejected_multiple_actions_or_missing_action(self):
        for message in ({'tool_calls': [{}, {}]}, {'content': '{malformed action'}, {}):
            with self.subTest(message=message):
                observed = envelope({'choices': [{'message': message}], 'usage': {'total_tokens': 1234}})
                observed['error'] = {'class': 'EngineError', 'reason': 'action parsing failed'}
                self.assertEqual(model_usage_tokens(observed), 1234)

    def test_legacy_response_without_framing_fields_has_only_legacy_scope(self):
        self.assertEqual(model_usage_tokens(envelope({'usage': {'total_tokens': 1234}}, transport=False)), 1234)

    def test_invalid_or_missing_telemetry_is_unknown_instead_of_zero(self):
        for tokens in (None, False, True, 0, -1, 1.5, '1234', {}, []):
            with self.subTest(tokens=tokens):
                self.assertIsNone(model_usage_tokens(envelope({'usage': {'total_tokens': tokens}})))
        for response in ({}, {'usage': None}, {'usage': []}, [], None,
                         b'{"usage":{"total_tokens":1,"total_tokens":2}}',
                         b'{"usage":{"total_tokens":NaN}}', b'{"usage":'):
            with self.subTest(response=response):
                self.assertIsNone(model_usage_tokens(envelope(response)))

    def test_complete_json_prefix_cannot_count_with_failed_transport_evidence(self):
        original = envelope({'usage': {'total_tokens': 1234}})
        mutations = {'http_status': 503, 'response_complete': False, 'response_truncated': True,
            'response_hash_scope': 'retained_prefix', 'transport_error': 'TimeoutError',
            'framing_error': 'ContentLengthMismatch', 'error': 'failed',
            'raw_response_base64': '', 'response_sha256': '0' * 64,
            'response_bytes_retained': True}
        for key, value in mutations.items():
            with self.subTest(key=key):
                changed = copy.deepcopy(original)
                changed['transport'][key] = value
                self.assertIsNone(model_usage_tokens(changed))
        for key, value in (('response_base64', '%%%'), ('response_sha256', '0' * 64),
                           ('transport', None), ('fixture', True)):
            with self.subTest(key=key):
                changed = copy.deepcopy(original)
                changed[key] = value
                self.assertIsNone(model_usage_tokens(changed))

    def test_attempts_count_once_despite_duplicate_journal_copies(self):
        observed = envelope({'usage': {'total_tokens': 1234}})
        state = {'model_calls': [observed, copy.deepcopy(observed), {'status': 'STARTED'}],
            'model_tokens': 0, 'events': [{'kind': 'MODEL_OBSERVATION', 'payload': observed}] * 8}
        before = copy.deepcopy(state)
        report = model_usage_report(state)
        self.assertEqual(report['validated_response_tokens_lower_bound'], 2468)
        self.assertEqual(report['recorded_model_tokens'], 0)
        self.assertEqual(report['attempts_with_usage'], 2)
        self.assertEqual(report['attempts_without_usage'], 1)
        self.assertEqual(report['missing_usage_attempt_indices'], [2])
        self.assertFalse(report['all_attempts_have_usage'])
        self.assertEqual(state, before)

    def test_original_archive_counters_and_corrected_raw_lower_bound_are_separate(self):
        archive_path = Path(__file__).resolve().parents[1] / 'research/investigation-engine/hosted-recovery-v0.1.zip'
        digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        self.assertEqual(digest, 'ac45229fda1e7a38fe23b5127cfd361fc938601bc5b6db94bd5d9a95268473e9')
        reports = []
        with zipfile.ZipFile(archive_path) as archive:
            for ident in range(201, 209):
                state = json.loads(archive.read(f'H{ident}-agent.json'))
                report = model_usage_report(state)
                reports.append(report)
                if ident == 205:
                    self.assertEqual(report['recorded_model_tokens'], 0)
                    self.assertEqual(report['validated_response_tokens_lower_bound'], 1090)
                    self.assertEqual(report['attempts_with_usage'], 1)
                    self.assertTrue(report['all_attempts_have_usage'])
                else:
                    self.assertEqual(report['attempts_without_usage'], 1)
        self.assertEqual(sum(r['recorded_model_tokens'] for r in reports), 141481)
        self.assertEqual(sum(r['validated_response_tokens_lower_bound'] for r in reports), 142571)
        self.assertEqual(sum(r['attempts_with_usage'] for r in reports), 29)
        self.assertEqual(sum(r['attempts_without_usage'] for r in reports), 7)
        self.assertEqual(hashlib.sha256(archive_path.read_bytes()).hexdigest(), digest)


if __name__ == '__main__':
    unittest.main()
