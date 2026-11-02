"""No-network structural tests for the 30-pair free-agent runner."""
import unittest
from tools.workflow_efficacy_free_agent import (
    ARMS, CONTROL_SHA, TREATMENT_SHA, MAX_SECONDS, MODEL,
    SAFE_CONFIG, order_for, parse_events,
)
class RunnerTests(unittest.TestCase):
    def test_schedule_balance_and_contract(self):
        orders = [order_for(i) for i in range(30)]
        self.assertEqual(len(orders), 30)
        self.assertTrue(all(set(x) == set(ARMS) for x in orders))
        self.assertEqual(len(CONTROL_SHA), 40)
        self.assertEqual(len(TREATMENT_SHA), 40)
        self.assertGreater(MAX_SECONDS, 0)
        self.assertEqual(MODEL, "opencode/big-pickle")
    def test_no_external_access_allowed(self):
        p = SAFE_CONFIG["permission"]
        self.assertEqual(p["external_directory"], "deny")
        self.assertEqual(p["websearch"], "deny")
        self.assertEqual(p["bash"]["*"], "deny")
    def test_model_event_metadata_parsing(self):
        raw = '{"type":"step-finish","part":{"type":"step-finish","tokens":{"input":12,"output":7},"cost":0}}\n'
        result = parse_events(raw)
        self.assertEqual(result["model_steps"], 1)
        self.assertEqual(result["input_tokens"], 12)
        self.assertEqual(result["output_tokens"], 7)
        self.assertEqual(result["reported_cost_usd"], 0)
    def test_invalid_json_is_not_model_execution(self):
        self.assertEqual(parse_events("noise")["model_steps"], 0)
if __name__ == "__main__":
    unittest.main()
