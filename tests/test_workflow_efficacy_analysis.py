"""Contract tests for the workflow efficacy analyzer: no fabricated causal evidence."""
import unittest
from tools.workflow_efficacy_analysis import analyze, load_protocol, planned_runs


class WorkflowEfficacyAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = load_protocol()

    def test_pool_and_balanced_schedule(self):
        plan = planned_runs(self.protocol)
        self.assertEqual(len(plan), 60)
        self.assertEqual(len({x["run_id"] for x in plan}), 60)
        first = {}
        for x in plan:
            first.setdefault(x["task_id"], x["arm"])
        self.assertEqual(list(first.values()).count("control"), 15)
        self.assertEqual(list(first.values()).count("treatment"), 15)

    def test_missing_runs_cannot_prove_improvement(self):
        self.assertEqual(analyze(self.protocol, [])["status"], "INCOMPLETE_OR_DUPLICATE")

    def sample(self):
        out = []
        for item in planned_runs(self.protocol):
            out.append({**item, "model_id": "frozen-test-model",
                "runtime_hash": "identical-runtime", "tool_config_hash": "identical-tools",
                "task_bundle_hash": "bundle-"+item["task_id"], "evaluator_id": "oracle-v1",
                "provenance_verified": True, "isolation_verified": True,
                "success": item["arm"] == "treatment",
                "elapsed_seconds": 100.0, "total_tokens": 1000,
                "provider_cost_usd": 1.0, "new_regressions": 0, "rework_count": 0})
        return out

    def test_synthetic_pair_arithmetic_only(self):
        result = analyze(self.protocol, self.sample())
        self.assertEqual(result["status"], "COMPLETE_PAIRED_INTERNAL_EVIDENCE")
        self.assertEqual(result["paired_success_delta"], 1.0)
        self.assertEqual(result["discordant_improvements"], 30)
        self.assertEqual(result["discordant_regressions"], 0)
        self.assertAlmostEqual(result["exact_sign_test_two_sided_p"], 2/(2**30))

    def test_tampering_fails_closed(self):
        items = self.sample()
        items[0]["isolation_verified"] = False
        self.assertEqual(analyze(self.protocol, items)["status"], "UNVERIFIED_ISOLATION_OR_PROVENANCE")

    def test_unmatched_model_fails_closed(self):
        items = self.sample()
        items[0]["model_id"] = "different-model"
        self.assertEqual(analyze(self.protocol, items)["status"], "UNMATCHED_CONDITIONS")

    def test_invalid_or_missing_outcome_fails_closed(self):
        items = self.sample()
        items[0]["success"] = None
        self.assertEqual(analyze(self.protocol, items)["status"], "UNVERIFIED_OR_MISSING_OUTCOME")

    def test_duplicate_record_cannot_inflate_results(self):
        items = self.sample()
        items[1] = items[0].copy()
        self.assertEqual(analyze(self.protocol, items)["status"], "INCOMPLETE_OR_DUPLICATE")


if __name__ == "__main__":
    unittest.main()
