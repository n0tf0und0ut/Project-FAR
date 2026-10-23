"""Twelfth-review regressions: arithmetic resources, context and caption coverage."""
import copy
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from decimal import localcontext, Inexact, Rounded

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from acquire import parse_captions
from engine import audit, canonical, digest
from full_cli import verify_package, write_package
from independent_check import check_report
from workflow import investigate
from test_review_578_cycle9 import numeric_bundle, config_for


def count_bundle(count):
    snapshot = json.dumps({'rows': [{'match': True}] * count}, separators=(',', ':'))
    result = numeric_bundle('100 matching rows.', '100', snapshot=snapshot)
    result['evidence'][0]['data_check'] = {
        'operation': 'count_where', 'pointer': '/rows',
        'where': {'field': 'match', 'equals': True}}
    return result


class TwelfthReviewRegressions(unittest.TestCase):
    def test_reported_numeric_magnitudes_are_rejected_before_rational_expansion(self):
        bundle = numeric_bundle()
        report = audit(bundle)
        program = '''import json,sys
from independent_check import check_report, IndependentCheckError
bundle, report = json.loads(sys.stdin.read())
try:
    check_report(bundle, report)
except IndependentCheckError:
    print("REJECTED")
else:
    raise SystemExit("accepted malformed computed value")
'''
        for value in ('1e1000000000', '1e-1000000000', 'NaN', 'Infinity', '9' * 5000):
            changed = copy.deepcopy(report)
            changed['claims']['c1']['evidence'][0]['structured_check']['computed_value'] = value
            changed['report_sha256'] = digest(canonical(
                {k: v for k, v in changed.items() if k != 'report_sha256'}))
            with self.subTest(value=value[:30]):
                try:
                    run = subprocess.run([sys.executable, '-c', program],
                        input=json.dumps([bundle, changed]), capture_output=True, text=True,
                        cwd=ROOT, timeout=2)
                except subprocess.TimeoutExpired:
                    self.fail('malformed reported number exhausted bounded checker time')
                self.assertEqual(run.returncode, 0, run.stderr[-500:])
                self.assertEqual(run.stdout.strip(), 'REJECTED')

    def test_largest_aggregate_and_fractional_results_remain_checkable(self):
        for term, count in (('9' * 40 + 'e40', 2000), ('1e-40', 10000)):
            snapshot = '{"rows":[' + ','.join('{"amount":' + term + '}' for _ in range(count)) + ']}'
            bundle = numeric_bundle(snapshot=snapshot)
            report = audit(bundle)
            with self.subTest(term=term):
                self.assertTrue(check_report(bundle, report)['independent_algorithm_agrees'])

    def test_metadata_prefix_cue_identifiers_preserve_every_cue_and_replay(self):
        for identifier in ('NOTEworthy', 'STYLEguide', 'REGION1', 'NOTE\u00a0identifier',
                           'NOTE\u00a0', '\u00a0NOTE', 'STYLE\u00a0', 'REGION\u00a0'):
            captions = ('WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nFirst observation is recorded.\n\n'
                        + identifier + '\n00:00:03.000 --> 00:00:04.000\n'
                        'Therefore the second conclusion follows.\n')
            with self.subTest(identifier=identifier), tempfile.TemporaryDirectory() as folder:
                parsed = parse_captions(captions)
                self.assertEqual(len(parsed['cues']), 2)
                result = investigate({'source': {'kind': 'vtt', 'text': captions}})
                self.assertEqual(len(result['acquisition'][0]['cues']), 2)
                self.assertIn('second conclusion', result['bundle']['sources'][0]['text'])
                destination = pathlib.Path(folder) / 'package'
                write_package(destination, result)
                self.assertTrue(verify_package(destination)['replay_match'])

    def test_actual_metadata_headers_remain_excluded(self):
        captions = ('WEBVTT\n\nNOTE a comment\ncomment text\n\nNOTE\tcomment\nmore text\n\n'
                    'STYLE\n::cue { color: lime; }\n\nREGION\nid:region\n\n'
                    '00:00:01.000 --> 00:00:02.000\nThe retained observation.\n')
        result = parse_captions(captions)
        self.assertEqual(result['text'], 'The retained observation.')
        self.assertEqual(len(result['cues']), 1)

    def test_filtered_counts_are_exact_under_small_decimal_precision(self):
        for count in (101, 10000):
            bundle = count_bundle(count)
            with self.subTest(count=count), localcontext() as ctx:
                ctx.prec = 2
                ctx.traps[Inexact] = True
                ctx.traps[Rounded] = True
                report = audit(bundle)
                result = report['claims']['c1']['evidence'][0]['structured_check']
                self.assertEqual(result['computed_value'], str(count))
                self.assertEqual(result['status'], 'STRUCTURED_VALUE_MISMATCH')
                self.assertTrue(check_report(bundle, report)['independent_algorithm_agrees'])

    def test_package_generation_replays_across_decimal_contexts(self):
        snapshot = json.dumps({'rows': [{'match': True}] * 101}, separators=(',', ':'))
        config = config_for(snapshot)
        claim = config['proposal']['claims'][0]
        claim['quote'] = '100 matching rows.'
        claim['quantity'] = {'value': '100', 'number_span': {'start': 0, 'end': 3}, 'unit': 'rows'}
        config['source']['text'] = claim['quote']
        config['proposal']['evidence'][0]['quote'] = snapshot[:900]
        config['proposal']['evidence'][0]['start'] = 0
        config['proposal']['evidence'][0]['data_check'] = {
            'operation': 'count_where', 'pointer': '/rows', 'where': {'field': 'match', 'equals': True}}
        with tempfile.TemporaryDirectory() as folder:
            destination = pathlib.Path(folder) / 'package'
            with localcontext() as ctx:
                ctx.prec = 2
                result = investigate(config)
                write_package(destination, result)
            self.assertTrue(verify_package(destination)['replay_match'])

    def test_sum_results_do_not_inherit_callers_exponent_or_trap_context(self):
        bundle = numeric_bundle(snapshot='{"rows":[{"amount":1e40},{"amount":1e-40}]}')
        with localcontext() as ctx:
            ctx.prec = 2
            ctx.Emax = 2
            ctx.Emin = -2
            ctx.clamp = 1
            ctx.traps[Inexact] = True
            ctx.traps[Rounded] = True
            report = audit(bundle)
        self.assertTrue(check_report(bundle, report)['independent_algorithm_agrees'])


if __name__ == '__main__':
    unittest.main()
