"""Regression tests for the bounded three-arm research comparison."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.far_architecture_routing import (
    PilotError, analyze, blob_sha, execute, load, plan, replay, smoke, source_document,
)


class ArchitectureRoutingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = load()

    def test_git_blob_identity_algorithm(self):
        self.assertEqual(blob_sha(b"hello\n"), "ce013625030ba8dba906f756967f9e9ca394464a")

    def test_frozen_source_bytes_and_counterbalanced_plan(self):
        for c in self.p["cases"]:
            self.assertEqual(source_document(c)["format_version"], "far-ir/2.0")
        rows = plan(self.p)
        self.assertEqual(len(rows), 36)
        self.assertEqual(len({(r["case_id"], r["arm"]) for r in rows}), 36)
        first = {}
        for r in rows:
            first.setdefault(r["case_id"], r["arm"])
        self.assertEqual([list(first.values()).count(a) for a in ("agent", "deterministic", "declarative")], [4, 4, 4])

    def test_replay_honors_exact_counterbalanced_schedule(self):
        result = replay(self.p, {c["id"]: "verify" for c in self.p["cases"]})
        observed = [(r["case_id"], r["arm"]) for r in result["records"]]
        expected = [(r["case_id"], r["arm"]) for r in plan(self.p)]
        self.assertEqual(observed, expected)
        first = {}
        for r in result["records"]:
            first.setdefault(r["case_id"], r["arm"])
        self.assertEqual(sorted(first.values()), ["agent"] * 4 + ["declarative"] * 4 + ["deterministic"] * 4)

    def test_smoke_honors_fixed_arm_order_from_schedule(self):
        calls = []
        def record(case, arm, protocol):
            calls.append((case["id"], arm))
            return {"correct": True}
        with patch("tools.far_architecture_routing.execute", side_effect=record):
            self.assertEqual(smoke(self.p)["correct"], 24)
        expected = [(r["case_id"], r["arm"]) for r in plan(self.p) if r["arm"] != "agent"]
        self.assertEqual(calls, expected)
        first = {}
        for case_id, arm in calls:
            first.setdefault(case_id, arm)
        self.assertEqual(sum(a == "deterministic" for a in first.values()), 6)
        self.assertEqual(sum(a == "declarative" for a in first.values()), 6)

    def test_direct_script_smoke_executes_from_repository_root(self):
        proc = subprocess.run([sys.executable, "tools/far_architecture_routing.py", "smoke"],
                              cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(result["correct"], 24)
        self.assertEqual(result["status"], "LOCAL_SMOKE_ONLY")

    def test_actual_semantic_verifier_and_two_fixed_routes(self):
        output = smoke(self.p)
        self.assertEqual(output["runs"], 24)
        self.assertEqual(output["correct"], 24, output["failures"])
        self.assertEqual(output["model_runs"], 0)
        self.assertEqual(output["claim"], "NOT_ESTABLISHED")

    def test_fixed_policy_outputs_identical(self):
        for c in self.p["cases"]:
            self.assertEqual(execute(c, "deterministic", self.p)["outcome"],
                             execute(c, "declarative", self.p)["outcome"])

    def test_scripted_agent_is_not_misreported_as_model(self):
        decisions = {c["id"]: "verify" for c in self.p["cases"]}
        output = replay(self.p, decisions)
        self.assertEqual(output["model_runs"], 0)
        scored = analyze(self.p, output["records"])
        self.assertEqual(scored["status"], "SCRIPTED_REPLAY_ONLY")
        self.assertEqual(scored["claim"], "NOT_ESTABLISHED")

    def test_abstentions_are_failures(self):
        decisions = {c["id"]: "abstain" for c in self.p["cases"]}
        report = analyze(self.p, replay(self.p, decisions)["records"])
        self.assertEqual(report["metrics"]["agent"]["correct"], 0)
        self.assertEqual(report["metrics"]["agent"]["total"], 12)

    def test_fail_closed_to_mutation_and_missing_cases(self):
        decisions = {c["id"]: "verify" for c in self.p["cases"]}
        original = replay(self.p, decisions)["records"]
        for key, value in (("source_blob_sha", "0" * 40),
                           ("correct", False),
                           ("elapsed_ms", float("nan")),
                           ("provenance", "MODEL_REPORTED")):
            mutated = copy.deepcopy(original)
            mutated[0][key] = value
            with self.assertRaises(PilotError, msg=key):
                analyze(self.p, mutated)
        with self.assertRaises(PilotError):
            analyze(self.p, original[:-1])
        with self.assertRaises(PilotError):
            analyze(self.p, original[:-1] + [original[0]])
        with self.assertRaises(PilotError):
            replay(self.p, {})
        with self.assertRaises(PilotError):
            execute(self.p["cases"][0], "agent", self.p, "arbitrary_action")

    def test_action_outcome_contradiction_cannot_forge_success(self):
        # Regression for Codex RTE-004: abstention must never score as a verdict.
        records = replay(self.p, {c["id"]: "abstain" for c in self.p["cases"]})["records"]
        fake = copy.deepcopy(records)
        labels = {c["id"]: c["expected"] for c in self.p["cases"]}
        for r in fake:
            if r["arm"] == "agent":
                r["outcome"] = labels[r["case_id"]]
                r["correct"] = True
        with self.assertRaisesRegex(PilotError, "action-outcome mismatch"):
            analyze(self.p, fake)
        fake = copy.deepcopy(records)
        next(r for r in fake if r["arm"] == "agent")["action"] = "verify"
        with self.assertRaisesRegex(PilotError, "action-outcome mismatch"):
            analyze(self.p, fake)
        fake = copy.deepcopy(records)
        next(r for r in fake if r["arm"] == "deterministic")["action"] = "abstain"
        with self.assertRaisesRegex(PilotError, "action mismatch"):
            analyze(self.p, fake)

    def test_fake_verified_outcome_rejected_even_when_correct_flag_agrees(self):
        records = replay(self.p, {c["id"]: "verify" for c in self.p["cases"]})["records"]
        fake = copy.deepcopy(records)
        target = next(r for r in fake if r["arm"] == "declarative")
        target["outcome"] = "NO_VERDICT"
        target["correct"] = False
        with self.assertRaisesRegex(PilotError, "action-outcome mismatch"):
            analyze(self.p, fake)

    def test_self_reported_model_records_remain_unverified(self):
        records = replay(self.p, {c["id"]: "verify" for c in self.p["cases"]})["records"]
        for r in records:
            if r["arm"] == "agent":
                r.update(provenance="MODEL_REPORTED", model_id="claimed-model",
                         model_response_sha256="a" * 64, total_tokens=10)
        result = analyze(self.p, records)
        self.assertEqual(result["status"], "UNVERIFIED_MODEL_REPORTS")
        self.assertEqual(result["claim"], "NOT_ESTABLISHED")
        del next(r for r in records if r["arm"] == "agent")["total_tokens"]
        with self.assertRaises(PilotError):
            analyze(self.p, records)

    def test_drift_and_traversal_blocked(self):
        for field, value in (("model_runner", "AVAILABLE"), ("source_commit", "0" * 40)):
            changed = copy.deepcopy(self.p)
            changed[field] = value
            with tempfile.TemporaryDirectory() as directory:
                location = Path(directory) / "protocol.json"
                location.write_text(json.dumps(changed), encoding="utf-8")
                with self.assertRaises(PilotError):
                    load(location)
        changed = copy.deepcopy(self.p)
        changed["cases"][0]["path"] = "../outside.json"
        with tempfile.TemporaryDirectory() as directory:
            location = Path(directory) / "protocol.json"
            location.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaises(PilotError):
                load(location)


if __name__ == "__main__":
    unittest.main()
