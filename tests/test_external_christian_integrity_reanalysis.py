"""Regression coverage for independent exact-count replication of ICMI-016."""
import unittest

from evaluation.external_christian_integrity_reanalysis import fisher_two_sided, report


class ExternalChristianIntegrityTests(unittest.TestCase):
    def test_christian_versus_unconditioned(self):
        self.assertAlmostEqual(float(fisher_two_sided(5, 59, 16, 71)), 0.033500,
                               delta=0.000001)

    def test_secular_versus_unconditioned(self):
        self.assertAlmostEqual(float(fisher_two_sided(4, 60, 16, 71)), 0.014372,
                               delta=0.000001)

    def test_christian_versus_secular_not_distinguishable(self):
        self.assertGreater(float(fisher_two_sided(5, 59, 4, 60)), 0.7)

    def test_within_christian_pool(self):
        self.assertAlmostEqual(float(fisher_two_sided(2, 118, 5, 59)), 0.041995,
                               delta=0.000001)

    def test_within_secular_pool(self):
        self.assertGreater(float(fisher_two_sided(12, 120, 4, 60)), 0.58)

    def test_identical_and_zero_events(self):
        self.assertEqual(fisher_two_sided(0, 10, 0, 10), 1)
        self.assertEqual(fisher_two_sided(4, 10, 4, 10), 1)

    def test_invalid_counts(self):
        for counts in [(3, 2, 1, 4), (-1, 3, 1, 4),
                       (2, 2, 1, 0), (1.0, 5, 1, 5)]:
            with self.subTest(counts=counts), self.assertRaises(ValueError):
                fisher_two_sided(*counts)

    def test_no_accuracy_claim_from_integrity(self):
        output = report()
        self.assertIn("not raw traces", output["disclaimer"])
        self.assertIn("shortcut cheating", output["interpretation"])


if __name__ == "__main__":
    unittest.main()
