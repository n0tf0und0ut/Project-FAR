"""Self-contained research tests, outside FAR authoritative verification.

python -m unittest discover -s research/good-view-jepa -p 'test_*.py'
"""
import copy
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import pilot


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = pilot.synthetic(per_split=(18, 6, 6))

    def test_deterministic_fixture(self):
        self.assertEqual(pilot.canonical(self.fixture), pilot.canonical(pilot.synthetic(per_split=(18, 6, 6))))

    def test_reject_family_leak(self):
        case = copy.deepcopy(self.fixture)
        case['items'][-1]['family_id'] = case['items'][0]['family_id']
        with self.assertRaisesRegex(ValueError, 'family leakage'):
            pilot.validate(case)

    def test_reject_duplicate_item(self):
        case = copy.deepcopy(self.fixture)
        case['items'][-1]['id'] = case['items'][0]['id']
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            pilot.validate(case)

    def test_reject_bad_vectors(self):
        for invalid in (float('nan'), float('inf'), '0'):
            case = copy.deepcopy(self.fixture)
            case['items'][0]['text'][0][0] = invalid
            with self.assertRaisesRegex(ValueError, 'finite'):
                pilot.validate(case)
        case = copy.deepcopy(self.fixture)
        case['items'][0]['image'][0].pop()
        with self.assertRaisesRegex(ValueError, 'dimensions'):
            pilot.validate(case)

    def test_reject_missing_source(self):
        case = copy.deepcopy(self.fixture)
        case['items'][0]['source_id'] = ''
        with self.assertRaisesRegex(ValueError, 'source_id'):
            pilot.validate(case)

    def test_declared_splits(self):
        self.assertEqual(pilot.validate(self.fixture), {'train': 36, 'calibration': 12, 'test': 12})


class ComputeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import numpy as np
            import torch
        except ImportError:
            raise unittest.SkipTest('optional numerical research dependencies absent')
        cls.np = np

    def test_pca_observes_only_first_view(self):
        np = self.np
        fixture = pilot.synthetic(per_split=(18, 6, 6))
        features = pilot.features(fixture, 'text')
        baseline, _ = pilot.train_encoder(features, 'pca', 11, 6, 4)
        modified = {split: vectors.copy() for split, vectors in features.items()}
        modified['test'][:, 1] += 123.0
        check, _ = pilot.train_encoder(modified, 'pca', 11, 6, 4)
        np.testing.assert_allclose(baseline['test'], check['test'])

    def test_pipeline_is_bounded_and_never_promotes(self):
        result = pilot.run(pilot.synthetic(per_split=(18, 6, 6)), seeds=(11,), steps=6, width=4)
        self.assertEqual(set(result['runs'][0]['conditions']), set(pilot.CONDITIONS))
        self.assertFalse(result['production_eligibility'])
        self.assertFalse(result['external_effectiveness_established'])
        for row in result['runs'][0]['conditions'].values():
            self.assertEqual(row['n_queries'], 12)
            for metric in ('recall_at_1', 'recall_at_5', 'mrr'):
                self.assertGreaterEqual(row[metric], 0)
                self.assertLessEqual(row[metric], 1)


if __name__ == '__main__':
    unittest.main()
