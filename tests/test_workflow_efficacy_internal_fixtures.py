"""Validate synthetic experimental tasks before any agent/provider calls."""
import unittest
from tools.workflow_efficacy_internal_fixtures import (
    fingerprint, hidden_test_code, public_test_code, task, oracle,
)

class TaskContractTests(unittest.TestCase):
    def test_thirty_distinct_tasks(self):
        tasks = [task(i) for i in range(30)]
        self.assertEqual(len({t["task_id"] for t in tasks}), 30)
        self.assertEqual(len({(t["kind"], t["mode"]) for t in tasks}), 30)
        self.assertEqual(len(fingerprint()), 64)
    def test_public_and_hidden_are_disjoint(self):
        for i in range(30):
            t = task(i)
            self.assertEqual(len(t["public"]), 2)
            self.assertEqual(len(t["hidden"]), 4)
            self.assertFalse({repr(x["input"]) for x in t["public"]} &
                             {repr(x["input"]) for x in t["hidden"]})
            self.assertNotIn("HiddenTest", public_test_code(t))
            self.assertNotIn("PublicTest", hidden_test_code(t))
    def test_all_reference_outputs_are_deterministic(self):
        for i in range(30):
            t = task(i)
            for c in t["public"] + t["hidden"]:
                self.assertEqual(c["expected"], oracle(i//3, i%3, c["input"]))
    def test_all_starters_fail_a_visible_test(self):
        for i in range(30):
            t = task(i)
            ns = {}
            exec(t["source"], ns)
            def result(entry):
                try: return ns["transform"](entry["input"]) == entry["expected"]
                except (ValueError, KeyError, IndexError, ZeroDivisionError): return False
            self.assertFalse(all(result(x) for x in t["public"]), t["task_id"])

if __name__ == "__main__":
    unittest.main()
