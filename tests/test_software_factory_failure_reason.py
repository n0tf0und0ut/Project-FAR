"""Regression tests for factory failure-report validation and lease integrity.

Frozen original acceptance oracle: tests/test_fail_reason_contract.py (local
provenance package); these are the independent integration and mutation checks.
"""
import tempfile
import unittest
from pathlib import Path

from tools.software_factory import Factory, FactoryError


BASE = "aa5cb8faf36b5e033bb96bf6e9f7f3f351387913"


def work_order():
    return {
        "schema": "far-software-factory/work-order/1", "id": "factoryreason",
        "repository": "n0tf0und0ut/Project-FAR", "base_sha": BASE,
        "tasks": [{"id": "repair", "objective": "Validate failure reason inputs",
                   "acceptance": ["Malformed failures preserve active lease"], "depends_on": []}],
    }


class TestFailureReasonValidation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.factory = Factory(Path(self.temp.name) / "factory.sqlite")
        self.factory.submit(work_order())
        self.claim = self.factory.claim("factoryreason", "worker", now=100)

    def test_non_string_failure_reasons_rejected_atomically(self):
        before = self.factory.snapshot("factoryreason")
        for reason in (None, [], {}, 0):
            with self.subTest(reason=repr(reason)):
                with self.assertRaisesRegex(FactoryError, "failure reason"):
                    self.factory.fail("factoryreason", "repair", self.claim["token"], reason, now=101)
                self.assertEqual(self.factory.snapshot("factoryreason"), before)

    def test_empty_failure_reason_rejected_atomically(self):
        before = self.factory.snapshot("factoryreason")
        for reason in ("", "  \t"):
            with self.subTest(reason=repr(reason)):
                with self.assertRaisesRegex(FactoryError, "failure reason"):
                    self.factory.fail("factoryreason", "repair", self.claim["token"], reason, now=101)
                self.assertEqual(self.factory.snapshot("factoryreason"), before)

    def test_valid_failure_reason_preserves_bounded_retry(self):
        result = self.factory.fail("factoryreason", "repair", self.claim["token"], "worker crashed", now=101)
        self.assertEqual(result, {"state": "queued", "attempts": 1})
        next_claim = self.factory.claim("factoryreason", "otherworker", now=102)
        self.assertNotEqual(next_claim["token"], self.claim["token"])
        with self.assertRaisesRegex(FactoryError, "stale"):
            self.factory.fail("factoryreason", "repair", self.claim["token"], "stale worker", now=103)
        self.assertEqual(self.factory.fail("factoryreason", "repair", next_claim["token"],
                                           "retry failed", now=103)["state"], "queued")

    def test_invalid_reason_then_valid_worker_recovery(self):
        before = self.factory.snapshot("factoryreason")
        for reason in (None, []):
            with self.assertRaises(FactoryError):
                self.factory.fail("factoryreason", "repair", self.claim["token"], reason, now=101)
        self.assertEqual(self.factory.snapshot("factoryreason"), before)
        self.assertEqual(self.factory.fail("factoryreason", "repair", self.claim["token"],
                                           "worker failed", now=102)["state"], "queued")
        history = self.factory.snapshot("factoryreason")["tasks"][0]["history"]
        self.assertEqual([event["event"] for event in history], ["claimed", "failed"])
        self.assertEqual(history[-1]["reason"], "worker failed")


if __name__ == "__main__":
    unittest.main()
