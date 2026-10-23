"""Thirteenth-review controls for parser context and independent source anchors."""
import copy
import pathlib
import sys
import tempfile
import unittest
from decimal import InvalidOperation, localcontext

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import audit, canonical, digest
from full_cli import verify_package, write_package
from independent_check import IndependentCheckError, check_report
from workflow import investigate
from test_independent_evidence import evidence_bundle
from test_review_578_cycle9 import numeric_bundle, config_for


def rehash(bundle, report):
    report['input_sha256'] = digest(canonical(bundle))
    report['report_sha256'] = digest(canonical(
        {k: v for k, v in report.items() if k != 'report_sha256'}))


class ThirteenthReviewRegressions(unittest.TestCase):
    def test_source_number_failure_is_independent_of_decimal_exception_traps(self):
        for token in ('1e9999999999999999999999999', '1e-9999999999999999999999999'):
            case = numeric_bundle('1 row.', '1', snapshot='{"rows":[{"amount":' + token + '}]}')
            case['evidence'][0]['data_check'] = {'operation': 'count_rows', 'pointer': '/rows'}
            baseline = audit(case)
            with self.subTest(token=token), localcontext() as ctx:
                ctx.traps[InvalidOperation] = False
                result = audit(case)
                finding = result['claims']['c1']['evidence'][0]['structured_check']
                self.assertEqual(finding['status'], 'STRUCTURED_UNVERIFIABLE')
                self.assertEqual(result, baseline)
                self.assertTrue(check_report(case, baseline)['independent_algorithm_agrees'])

    def test_relaxed_parser_context_package_replays_under_default_context(self):
        snapshot = '{"rows":[{"amount":1e9999999999999999999999999}]}'
        config = config_for(snapshot)
        config['source']['text'] = '1 row.'
        claim = config['proposal']['claims'][0]
        claim['quote'] = '1 row.'
        claim['quantity'] = {'value': '1', 'number_span': {'start': 0, 'end': 1}, 'unit': 'rows'}
        config['proposal']['evidence'][0]['data_check'] = {'operation': 'count_rows', 'pointer': '/rows'}
        with tempfile.TemporaryDirectory() as folder:
            target = pathlib.Path(folder) / 'package'
            with localcontext() as ctx:
                ctx.traps[InvalidOperation] = False
                write_package(target, investigate(config))
            self.assertTrue(verify_package(target)['replay_match'])

    def test_oracle_requires_integer_in_range_nonempty_claim_and_evidence_spans(self):
        original = evidence_bundle({'atom': 'P'})
        report = audit(original)
        for lane in ('claims', 'evidence'):
            for kind in ('negative_start', 'negative_end', 'oversized_end', 'bool_start', 'bool_end', 'empty', 'reversed'):
                case, forged = copy.deepcopy(original), copy.deepcopy(report)
                item = case[lane][0]
                source = next(s for s in case['sources'] if s['id'] == item['source_id'])['text']
                start, end = 0, len(source)
                if kind == 'negative_start': start = -len(source)
                elif kind == 'negative_end': end = -1
                elif kind == 'oversized_end': end += 100
                elif kind == 'bool_start': start = False
                elif kind == 'bool_end': end = True
                elif kind == 'empty': end = 0
                elif kind == 'reversed': start, end = 2, 1
                item['span'] = {'start': start, 'end': end, 'quote': source[start:end]}
                rehash(case, forged)
                with self.subTest(lane=lane, kind=kind), self.assertRaises(IndependentCheckError):
                    check_report(case, forged)

    def test_negative_evidence_cannot_evade_self_corroboration_overlap(self):
        case = evidence_bundle({'atom': 'P'})
        report = audit(case)
        text = case['sources'][0]['text']
        ev = case['evidence'][0]
        ev['source_id'] = 'primary'
        ev['span'] = {'start': -len(text), 'end': -1, 'quote': text[:-1]}
        finding = report['claims']['c1']['evidence'][0]
        finding['source_id'] = 'primary'
        finding['origin_id'] = case['sources'][0]['origin_id']
        report['claims']['c1']['support_sources_with_unknown_origin'] = ['primary']
        rehash(case, report)
        with self.assertRaises(IndependentCheckError):
            check_report(case, report)
        ev['span'] = {'start': 0, 'end': len(text) - 1, 'quote': text[:-1]}
        corrected = audit(case)
        self.assertEqual(corrected['claims']['c1']['evidence'][0]['formal_relation'],
                         'SELF_REFERENCE_NOT_CORROBORATION')
        self.assertTrue(check_report(case, corrected)['independent_algorithm_agrees'])


if __name__ == '__main__':
    unittest.main()
