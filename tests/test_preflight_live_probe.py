"""Ephemeral CI-only cutover probe. Never merge this test-only file."""
import unittest


def probe_classify(value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError("integer required")
    return "positive" if value > 0 else "nonpositive"


class PreflightLiveProbe(unittest.TestCase):
    def test_rejects_text_input(self):
        with self.assertRaises(TypeError):
            probe_classify("1")

    def test_rejects_boolean_input(self):
        with self.assertRaises(TypeError):
            probe_classify(True)

    def test_positive_integer(self):
        self.assertEqual(probe_classify(1), "positive")

    def test_nonpositive_integer(self):
        self.assertEqual(probe_classify(0), "nonpositive")
