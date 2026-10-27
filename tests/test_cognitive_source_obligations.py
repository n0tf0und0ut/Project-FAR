"""Source-motivated hostile follow-ups, separately from the frozen 71 cases."""
import copy
import json
from pathlib import Path
import unittest
from jsonschema import Draft202012Validator
from mechanization.far_mechanization.cognitive import CognitiveDocument, audit

ROOT = Path(__file__).resolve().parents[1]


class SourceObligationTests(unittest.TestCase):
    def test_open_scheme_vocabulary_cannot_impose_closed_membership(self):
        open_schema = {'type':'object','required':['scheme'],'additionalProperties':False,'properties':{'scheme':{'type':'string'}}}
        closed = copy.deepcopy(open_schema)
        closed['properties']['scheme'] = {'enum':['deduction','induction','abduction']}
        graph = {'scheme':'supports_somehow'}
        self.assertFalse(list(Draft202012Validator(open_schema).iter_errors(graph)))
        self.assertTrue(list(Draft202012Validator(closed).iter_errors(graph)))

    def test_negative_status_does_not_assert_the_failure_as_an_observation(self):
        rows = json.loads((ROOT/'research/cognitive-audit/frozen-v1/cases.json').read_text())['cases']
        for row in rows:
            with self.subTest(case=row['id']):
                result = audit(CognitiveDocument.from_dict(row['input']))['diagnoses'][0]
                self.assertTrue(result['observation'].startswith('Submitted coding: '))
                self.assertEqual(json.loads(result['observation'].removeprefix('Submitted coding: ')),row['input']['probes'][0]['facts'])
                self.assertIsInstance(result['scoped_predicate'],str)


if __name__ == '__main__': unittest.main()
