"""Source-bound regression tests for Factory.fail retry-bound validation.

The original independently pinned FAR-MAINT-003 research holdout remains
unchanged. These are ordinary software regression controls, not new research data.
"""
import tempfile
import unittest
from pathlib import Path
from tools.software_factory import Factory, FactoryError

BASE = "5253a45ac7f5bfbda1278cf3b8fbf4b9b22136f8"


class RetryBoundRegression(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.f = Factory(Path(self.tmp.name) / "queue.sqlite")
        self.f.submit({"schema":"far-software-factory/work-order/1", "id":"bounds",
            "repository":"n0tf0und0ut/Project-FAR", "base_sha":BASE,
            "tasks":[{"id":"repair", "objective":"Retry bound regression",
                      "acceptance":["Never consume lease for invalid bounds"], "depends_on":[]}]})
        self.claim = self.f.claim("bounds", "builder", now=100)

    def test_non_integer_bounds_fail_closed(self):
        before = self.f.snapshot("bounds")
        for value in (None, "3", [], {}):
            with self.subTest(value=repr(value)):
                with self.assertRaisesRegex(FactoryError, "retry bound"):
                    self.f.fail("bounds", "repair", self.claim["token"], "worker failed",
                                now=101, max_attempts=value)
                self.assertEqual(self.f.snapshot("bounds"), before)

    def test_bool_bounds_fail_closed_without_consuming_lease(self):
        before = self.f.snapshot("bounds")
        for value in (True, False):
            with self.subTest(value=value):
                with self.assertRaisesRegex(FactoryError, "retry bound"):
                    self.f.fail("bounds", "repair", self.claim["token"], "worker failed",
                                now=101, max_attempts=value)
                self.assertEqual(self.f.snapshot("bounds"), before)

    def test_positive_integer_retries_unchanged(self):
        first = self.f.fail("bounds", "repair", self.claim["token"], "worker failed",
                            now=101, max_attempts=3)
        self.assertEqual(first["state"], "queued")
        nxt = self.f.claim("bounds", "builder", now=102)
        self.assertEqual(self.f.fail("bounds", "repair", nxt["token"],
                                    "worker failed", now=103, max_attempts=2)["state"], "failed")

    def test_invalid_then_valid_failure_preserves_history(self):
        before = self.f.snapshot("bounds")
        with self.assertRaises(FactoryError):
            self.f.fail("bounds", "repair", self.claim["token"], "worker failed",
                        now=101, max_attempts=None)
        self.assertEqual(before, self.f.snapshot("bounds"))
        self.assertEqual(self.f.fail("bounds", "repair", self.claim["token"],
                                    "worker failed", now=102, max_attempts=3)["state"], "queued")
        self.assertEqual([x["event"] for x in self.f.snapshot("bounds")["tasks"][0]["history"]],
                         ["claimed", "failed"])


if __name__ == "__main__":
    unittest.main()
