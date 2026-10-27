"""The evaluator must preserve missingness and reject unmatched inputs."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('live_eval', Path(__file__).resolve().parents[1] / 'tools/run_live_commercial_evaluation.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class LiveEvaluationTests(unittest.TestCase):
    case = {'id': 'Q01', 'query': 'Which study?', 'target_doi': '10.1234/real', 'target_title': 'A Real Study'}

    def receipt(self, response):
        return {'provider': 'consensus', 'case_id': 'Q01', 'request': 'Which study?', 'elapsed_ms': 1, 'response': response}

    def test_matches_are_case_insensitive(self):
        r = mod.score_retrieval(self.receipt({'title': 'A REAL STUDY', 'doi': '10.1234/REAL'}), self.case)
        self.assertTrue(r['target_doi_present'])
        self.assertTrue(r['target_title_present'])
        self.assertFalse(r['scientific_support_verified'])
        self.assertIsNone(r['per_call_dollar_cost'])

    def test_title_without_doi_is_not_a_doi_hit(self):
        r = mod.score_retrieval(self.receipt({'title': 'A real study'}), self.case)
        self.assertTrue(r['target_title_present'])
        self.assertFalse(r['target_doi_present'])

    def test_transport_error_is_missing_not_negative(self):
        r = mod.score_retrieval(self.receipt({'isError': True, 'content': '10.1234/real'}), self.case)
        self.assertIsNone(r['target_doi_present'])
        self.assertEqual(r['status'], 'ERROR_RECORDED')

    def test_input_identity_cannot_drift(self):
        r = self.receipt({})
        r['request'] = 'A different query'
        with self.assertRaises(ValueError):
            mod.score_retrieval(r, self.case)

    def test_provider_and_case_cannot_be_relabelled(self):
        for key, value in [('provider', 'quri'), ('case_id', 'Q02')]:
            r = self.receipt({})
            r[key] = value
            with self.assertRaises(ValueError):
                mod.score_retrieval(r, self.case)

    def test_negative_time_is_not_accepted(self):
        for value in [-1, float('nan'), float('inf'), True]:
            r = self.receipt({})
            r['elapsed_ms'] = value
            with self.assertRaises(ValueError):
                mod.score_retrieval(r, self.case)


if __name__ == '__main__':
    unittest.main()
