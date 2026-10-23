"""Tenth-review controls: unsupported numbers, generated limits and lane identity."""
import copy
from contextlib import redirect_stderr, redirect_stdout
from http.client import HTTPResponse
from io import BytesIO, StringIO
import pathlib
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import InvalidBundle, audit, canonical, digest
from full_cli import main, verify_package, write_package
from independent_check import IndependentCheckError, check_report
from proposals import heuristic_proposal
from test_independent_evidence import evidence_bundle
from test_review_578_cycle9 import numeric_bundle
from workflow import investigate


def rehash(report, source=None):
    if source is not None:
        report['input_sha256'] = digest(canonical(source))
    report['report_sha256'] = digest(canonical(
        {k: v for k, v in report.items() if k != 'report_sha256'}))


class TenthReviewRegressions(unittest.TestCase):
    def test_fraction_group_and_identifier_fragments_fail_in_both_checkers(self):
        for token, value, start in (('1/2', '2', 2), ('1 / 2', '2', 4),
                                    ('1⁄2', '2', 2), ('1:2', '2', 2),
                                    ('1_234', '234', 2), ('1_234', '1', 0),
                                    ('item2', '2', 4), ('2items', '2', 0)):
            report = audit(numeric_bundle(value + ' dollars received.', value))
            case = numeric_bundle(token + ' dollars received.', value, start)
            with self.subTest(token=token), self.assertRaisesRegex(
                    InvalidBundle, 'complete numeric literal'):
                audit(case)
            forged = copy.deepcopy(report)
            rehash(forged, case)
            with self.subTest(independent=token), self.assertRaisesRegex(
                    IndependentCheckError, 'numeric literal'):
                check_report(case, forged)

    def test_primary_and_evidence_omit_overlong_candidates_without_losing_good_claims(self):
        long_sentence = 'The observation ' + 'remains relevant and ' * 60 + '.'
        primary = 'A short valid sentence. ' + long_sentence
        evidence = 'A short valid sentence has corroborating context. ' + long_sentence
        proposal = heuristic_proposal(primary, {'ev1': evidence})
        self.assertTrue(all(len(c['quote']) <= 1000 for c in proposal['claims']))
        self.assertTrue(all(len(e['quote']) <= 1000 for e in proposal['evidence']))
        self.assertTrue(any('primary' in note and 'overlong sentence' in note
                            for note in proposal['unknowns']))
        self.assertTrue(any('ev1' in note and 'overlong sentence' in note
                            for note in proposal['unknowns']))
        result = investigate({'source': {'kind': 'text', 'text': primary},
                              'evidence_sources': [{'kind': 'text', 'text': evidence}]})
        self.assertEqual(len(result['bundle']['claims']), 1)
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / 'package'
            write_package(path, result)
            self.assertTrue(verify_package(path)['replay_match'])

    def test_all_overlong_primary_candidates_have_an_explicit_bounded_error(self):
        with self.assertRaisesRegex(InvalidBundle, 'no bounded sentence candidates'):
            investigate({'source': {'kind': 'text', 'text': 'Long text ' * 110 + '.'}})

    def test_generated_quotation_limit_is_inclusive_and_offsets_remain_original(self):
        exact = 'A' * 999 + '.'
        overlong = 'B' * 1000 + '.'
        text = overlong + ' ' + exact
        result = investigate({'source': {'kind': 'text', 'text': text}})
        self.assertEqual(len(result['bundle']['claims']), 1)
        claim = result['bundle']['claims'][0]
        self.assertEqual(claim['span']['quote'], exact)
        self.assertEqual(claim['span']['start'], len(overlong) + 1)
        self.assertTrue(any('1 overlong sentence' in note for note in result['audit']['unknowns']))

    def test_fabricated_numeric_lane_annotations_are_rejected(self):
        case = evidence_bundle({'atom': 'P'})
        for annotation in ({'structured_check': {'status': 'STRUCTURED_VALUE_MATCH'}},
                           {'structured_temporal_eligibility': 'IN_WINDOW'},
                           {'assessment_disagrees_with_structured_check': False}):
            report = audit(case)
            report['claims']['c1']['evidence'][0].update(annotation)
            if 'structured_check' in annotation:
                summary = report['claims']['c1']['structured_value_checks']
                summary.update(status='STRUCTURED_VALUE_MATCH_CONDITIONALLY', matches=1)
            rehash(report)
            with self.subTest(annotation=annotation), self.assertRaisesRegex(
                    IndependentCheckError, 'structured.*lane'):
                check_report(case, report)

    def test_real_http_protocol_failures_remain_redacted_cli_errors_and_close_connection(self):
        # Exercise the real HTTP parser; no provider or network request occurs.
        for raw in (b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\na\r\nabc',
                    b'not an HTTP response\r\n\r\n'):
            closed = []
            def response():
                sock = SimpleNamespace(makefile=lambda *a: BytesIO(raw))
                parsed = HTTPResponse(sock)
                parsed.begin()
                return parsed
            conn = SimpleNamespace(request=lambda *a, **kw: None, getresponse=response,
                                   close=lambda: closed.append(True))
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as folder:
                root = pathlib.Path(folder)
                request = root / 'request.json'
                request.write_bytes(canonical({'source': {'kind': 'text', 'text': 'A bounded claim.'},
                    'discovery': 'tavily', 'queries': ['bounded query']}))
                error, output = StringIO(), StringIO()
                with patch.dict('os.environ', {'TAVILY_API_KEY': 'synthetic-secret'}), \
                        patch('discovery.resolve_public', return_value=['93.184.216.34']), \
                        patch('discovery._PinnedHTTPS', return_value=conn), \
                        patch.object(sys, 'argv', ['full_cli', str(request), '--output',
                                                  str(root / 'package'), '--allow-network']), \
                        redirect_stderr(error), redirect_stdout(output):
                    self.assertEqual(main(), 2)
                self.assertIn('FAR_END_TO_END_INVALID: discovery unavailable:', error.getvalue())
                self.assertNotIn('synthetic-secret', error.getvalue())
                self.assertNotIn('Traceback', error.getvalue())
                self.assertEqual(closed, [True])
                self.assertFalse((root / 'package').exists())


if __name__ == '__main__':
    unittest.main()
