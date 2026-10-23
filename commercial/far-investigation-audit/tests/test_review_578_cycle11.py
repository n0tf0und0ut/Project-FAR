"""Eleventh-review controls for closed reports, strict JSON and numeric groups."""
import copy
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import InvalidBundle, audit, canonical, digest
from independent_check import IndependentCheckError, check_report
from proposals import heuristic_proposal
from test_independent_evidence import evidence_bundle
from test_review_578_cycle9 import numeric_bundle
from workflow import investigate


def rehash(report, bundle=None):
    if bundle is not None:
        report['input_sha256'] = digest(canonical(bundle))
    report['report_sha256'] = digest(canonical(
        {k: v for k, v in report.items() if k != 'report_sha256'}))


class EleventhReviewRegressions(unittest.TestCase):
    def test_mixed_fraction_space_group_expression_and_sign_fragments_are_rejected(self):
        cases = (('1 1/2', '1', 0), ('1 1/2', '1', 2), ('1 1/2', '2', 4),
                 ('1\u202f234', '234', 2), ('1\u00a0234', '1', 0), ('1 234', '234', 2),
                 ('2*3', '3', 2), ('2^3', '3', 2), ('--2', '-2', 1), ('±2', '2', 1))
        for token, value, start in cases:
            snapshot = '{"rows":[{"amount":' + value + '}]}'
            valid = numeric_bundle(value + ' dollars received.', value, snapshot=snapshot)
            report = audit(valid)
            case = numeric_bundle(token + ' dollars received.', value, start, snapshot)
            with self.subTest(primary=token, start=start), self.assertRaisesRegex(
                    InvalidBundle, 'complete numeric literal'):
                audit(case)
            rehash(report, case)
            with self.subTest(independent=token, start=start), self.assertRaisesRegex(
                    IndependentCheckError, 'numeric literal'):
                check_report(case, report)

    def test_core_enum_type_errors_are_invalid_bundles(self):
        fixture = json.loads((ROOT / 'examples/causal_jump.json').read_bytes())
        for value in ([], {}):
            for field in ('formalization_basis', 'card_origin'):
                case = copy.deepcopy(fixture)
                if field == 'formalization_basis':
                    case['interpretations'][0][field] = value
                else:
                    case['interpretations'][0]['interpretation_card'] = {
                        'subject': {'value': 'bounded subject', 'origin': value}}
                with self.subTest(field=field, value=value), self.assertRaises(InvalidBundle):
                    audit(case)

    def test_cli_invalid_enum_types_return_two_without_traceback_or_output(self):
        fixture = json.loads((ROOT / 'examples/causal_jump.json').read_bytes())
        fixture['interpretations'][0]['formalization_basis'] = []
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            source, output = root / 'invalid.json', root / 'report.json'
            source.write_bytes(canonical(fixture))
            run = subprocess.run([sys.executable, str(ROOT / 'cli.py'), str(source),
                                  '--output', str(output)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 2, run.stderr)
            self.assertIn('FAR_AUDIT_INVALID:', run.stderr)
            self.assertNotIn('Traceback', run.stderr)
            self.assertFalse(output.exists())

    def test_audit_producer_and_replay_share_duplicate_rejecting_json(self):
        original = (ROOT / 'examples/causal_jump.json').read_bytes()
        duplicates = (b'{"schema":"attacker-first",' + original.lstrip()[1:],
                      original.replace(b'"mapping_status":',
                          b'"mapping_status":"unreviewed","mapping_status":', 1))
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            source, output = root / 'bundle.json', root / 'report.json'
            source.write_bytes(original)
            good = subprocess.run([sys.executable, str(ROOT / 'cli.py'), str(source),
                                   '--output', str(output)], capture_output=True, text=True)
            self.assertEqual(good.returncode, 0, good.stderr)
            replay = subprocess.run([sys.executable, str(ROOT / 'verify.py'), str(source),
                                     str(output)], capture_output=True, text=True)
            self.assertEqual(replay.returncode, 0, replay.stderr)
            for index, raw in enumerate(duplicates):
                source.write_bytes(raw)
                bad_output = root / f'bad-report-{index}.json'
                run = subprocess.run([sys.executable, str(ROOT / 'cli.py'), str(source),
                                      '--output', str(bad_output)], capture_output=True, text=True)
                with self.subTest(duplicate=index):
                    self.assertEqual(run.returncode, 2, run.stderr)
                    self.assertIn('FAR_AUDIT_INVALID:', run.stderr)
                    self.assertFalse(bad_output.exists())

    def test_oracle_rejects_assurance_extensions_at_every_report_level(self):
        case = evidence_bundle({'atom': 'P'})
        for field in ('external_truth_verified', 'semantic_mapping_independently_verified',
                      'source_authenticity_verified'):
            for level in ('report', 'claim', 'evidence'):
                report = audit(case)
                target = (report if level == 'report' else report['claims']['c1']
                          if level == 'claim' else report['claims']['c1']['evidence'][0])
                target[field] = True
                rehash(report)
                with self.subTest(level=level, field=field), self.assertRaises(IndependentCheckError):
                    check_report(case, report)

    def test_supplied_proposal_ids_and_enums_fail_with_invalid_bundle(self):
        text = 'The observed rain is recorded. Therefore the road is wet.'
        evidence = 'The observed rain was recorded outside.'
        proposal = heuristic_proposal(text, {'ev1': evidence})
        mutations = (('arguments', 'id'), ('arguments', 'premises'),
                     ('arguments', 'conclusion'), ('arguments', 'card_origin'),
                     ('evidence', 'source_id'), ('evidence', 'claim_id'), ('evidence', 'relation'))
        for lane, field in mutations:
            config = {'source': {'kind': 'text', 'text': text},
                      'evidence_sources': [{'kind': 'text', 'text': evidence}],
                      'proposal_mode': 'supplied', 'proposal': copy.deepcopy(proposal)}
            target = config['proposal'][lane][0]
            if field == 'card_origin':
                target['interpretation_card'] = {'subject': {'value': 'rain', 'origin': []}}
            else:
                target[field] = [[]] if field == 'premises' else []
            with self.subTest(lane=lane, field=field), self.assertRaises(InvalidBundle):
                investigate(config)


if __name__ == '__main__':
    unittest.main()
