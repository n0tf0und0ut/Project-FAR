"""Cold historical replay and adversarial controls, never new model evidence."""
import copy
import base64
import io
import json
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path

from tools import agent_reliability_evidence as evidence
from tools import tool_agent_reliability as runner


class ReliabilityEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scored = evidence.build_historical()
        cls.failed = evidence.build_historical(cohort="tool-agent-v02-preflight")

    def test_original_success_and_negative_outcomes_replay_without_pooling(self):
        self.assertTrue(evidence.verify_historical(self.scored)["complete"])
        self.assertEqual(self.scored["summary"]["outcomes"]["success"], 72)
        self.assertEqual(self.failed["summary"]["outcomes"], {"success": 2, "failure": 1, "partial_success": 0, "abstention": 0, "unknown": 0})
        self.assertEqual(self.failed["summary"]["failure_fraction"], {"numerator": 1, "denominator": 3})
        self.assertEqual(sum(r["safety"]["unauthorized_write_count"] for r in self.failed["runs"]), 1)
        self.assertEqual(self.scored["summary"]["independent_behavioral_samples"], "NOT_ESTABLISHED")
        self.assertEqual(self.scored["summary"]["distinct_action_observation_trajectories"], 25)

    def test_existing_evidence_envelope_is_reused_without_schema_change(self):
        import jsonschema
        schema = json.loads((evidence.ROOT / "schemas/far-evidence-package-v1.schema.json").read_text())
        self.assertEqual(list(jsonschema.Draft202012Validator(schema).iter_errors(self.scored["evidence_package"])), [])
        self.assertEqual(list(jsonschema.Draft202012Validator(schema).iter_errors(self.failed["evidence_package"])), [])

    def test_common_shape_is_model_independent_but_shape_is_not_replay(self):
        value = copy.deepcopy(self.failed)
        value["runs"][0]["identities"]["model"] = {"provider": "another-provider", "name": "another-model", "version": "opaque-release"}
        self.assertTrue(evidence.validate_profile(value))
        with self.assertRaisesRegex(ValueError, "differs from replayed"):
            evidence.verify_historical(value)

    def test_billing_provenance_and_profile_identities_are_bounded_strings(self):
        for source in (True, 123, {}, ["invoice"], "", " ", "x" * 2049):
            for status in ("observed", "estimated"):
                with self.subTest(source=type(source).__name__, status=status):
                    value = copy.deepcopy(self.failed)
                    value["runs"][0]["resources"]["billing"] = {"status": status, "amount": "0", "currency": "USD", "source": source}
                    with self.assertRaises(ValueError): evidence.validate_profile(value)
        for field in ("cohort_id", "adapter"):
            for bad in (True, 123, {}, "", " ", "x" * 257):
                value = copy.deepcopy(self.failed); value[field] = bad
                with self.subTest(field=field, bad=type(bad).__name__):
                    with self.assertRaises(ValueError): evidence.validate_profile(value)
        for source in (True, 123, "citation", {}, {"path": "x", "members": [], "sha256": "wrong"}):
            value = copy.deepcopy(self.failed)
            value["runs"][0]["ground_truth"].update(independence="EXTERNALLY_DOCUMENTED", independence_evidence=["independent-rater-record"], source=source)
            with self.assertRaises(ValueError): evidence.validate_profile(value)

    def test_unknown_telemetry_requires_explicit_reasons_but_preserves_verified_outcome(self):
        names = ("input_tokens", "output_tokens", "model_calls", "tool_actions", "elapsed_seconds", "provider_seconds", "setup_seconds", "human_review_seconds")
        for name in names:
            with self.subTest(name=name):
                value = copy.deepcopy(self.scored)
                resources = value["runs"][0]["resources"]
                resources[name] = None
                resources["unknown_measurements"].pop(name, None)
                with self.assertRaises(ValueError): evidence.validate_profile(value)
                resources["unknown_measurements"][name] = {"reason": "Provider did not retain this measurement.", "evidence": []}
                self.assertTrue(evidence.validate_profile(value))
                self.assertEqual(value["summary"]["outcomes"]["success"], 72)
                self.assertEqual(value["summary"]["success_fraction"], {"numerator": 1, "denominator": 1})
                with self.assertRaisesRegex(ValueError, "differs from replayed"):
                    evidence.verify_historical(value)
                for bad in (True, -1, float("nan"), float("inf")):
                    resources[name] = bad
                    resources["unknown_measurements"].pop(name)
                    with self.assertRaises(ValueError): evidence.validate_profile(value)
                    resources["unknown_measurements"][name] = {"reason": "Unavailable", "evidence": []}

    def test_unknown_safety_is_never_treated_as_safe_zero(self):
        value = copy.deepcopy(self.scored)
        safety = value["runs"][0]["safety"]
        for name in ("unauthorized_action_count", "unauthorized_write_count"):
            safety[name] = None
            safety["unknown_measurements"][name] = {"reason": "An incomplete log cannot establish an authorization count.", "evidence": []}
        with self.assertRaisesRegex(ValueError, "fabricated success"):
            evidence.validate_profile(value)
        value["runs"][0]["outcome"].update(grade="unknown", valid=False)
        value["runs"][0]["trace"]["complete"] = False
        value["summary"] = evidence.summarize(value["exposure"], value["runs"])
        self.assertTrue(evidence.validate_profile(value))
        self.assertIsNone(value["summary"]["success_fraction"])
        for name in ("unauthorized_action_count", "unauthorized_write_count"):
            for bad in (True, -1, float("nan"), float("inf")):
                changed = copy.deepcopy(value)
                changed["runs"][0]["safety"][name] = bad
                changed["runs"][0]["safety"]["unknown_measurements"].pop(name)
                with self.assertRaises(ValueError): evidence.validate_profile(changed)

    def test_unknown_elapsed_cannot_hide_impossible_provider_wall_time(self):
        value = copy.deepcopy(self.failed)
        resources = value["runs"][0]["resources"]
        resources["elapsed_seconds"] = None
        resources["unknown_measurements"]["elapsed_seconds"] = {"reason": "Monotonic total was not recorded.", "evidence": []}
        self.assertTrue(evidence.validate_profile(value))
        resources["provider_seconds"] = 10**9
        with self.assertRaisesRegex(ValueError, "exceeds observed wall interval"):
            evidence.validate_profile(value)

    def test_incidents_and_missing_exposures_cannot_become_rates(self):
        incident = evidence.summarize({"kind": "incidents_only", "eligible_slots": []}, self.failed["runs"])
        self.assertIsNone(incident["failure_fraction"])
        self.assertIsNone(incident["eligible_exposures"])
        missing = evidence.summarize(self.scored["exposure"], self.scored["runs"][:-1])
        self.assertFalse(missing["complete"])
        self.assertIsNone(missing["success_fraction"])
        self.assertEqual(len(missing["missing_slots"]), 1)
        with self.assertRaisesRegex(ValueError, "invent exposure"):
            evidence.summarize({"kind": "incidents_only", "eligible_slots": ["invented"]}, [])

    def test_duplicate_runs_duplicate_slots_and_unregistered_slots_rejected(self):
        for changed in (copy.deepcopy(self.failed["runs"][0]), copy.deepcopy(self.failed["runs"][1])):
            changed["run_id"] += "/copy"
            with self.assertRaisesRegex(ValueError, "duplicate run or slot"):
                evidence.summarize(self.failed["exposure"], self.failed["runs"] + [changed])
        changed = copy.deepcopy(self.failed["runs"][0]); changed["slot_id"] = "other-slot"
        with self.assertRaisesRegex(ValueError, "unregistered"):
            evidence.summarize(self.failed["exposure"], [changed])

    def test_removed_record_and_changed_denominator_fail_historical_reconstruction(self):
        value = copy.deepcopy(self.failed)
        value["runs"].pop()
        value["summary"] = evidence.summarize(value["exposure"], value["runs"])
        self.assertTrue(evidence.validate_profile(value))
        with self.assertRaisesRegex(ValueError, "differs from replayed"):
            evidence.verify_historical(value)
        value["exposure"]["eligible_slots"].pop()
        value["summary"] = evidence.summarize(value["exposure"], value["runs"])
        with self.assertRaisesRegex(ValueError, "differs from replayed"):
            evidence.verify_historical(value)

    def test_fabricated_success_and_invented_independence_rejected(self):
        value = copy.deepcopy(self.failed)
        bad = next(r for r in value["runs"] if r["outcome"]["grade"] == "failure")
        bad["outcome"]["grade"] = "success"
        value["summary"] = evidence.summarize(value["exposure"], value["runs"])
        with self.assertRaisesRegex(ValueError, "fabricated success"):
            evidence.validate_profile(value)
        value = copy.deepcopy(self.scored)
        value["summary"]["independent_behavioral_samples"] = 72
        with self.assertRaisesRegex(ValueError, "summary"):
            evidence.validate_profile(value)

    def test_forged_action_or_observation_cannot_hide_behind_new_digest(self):
        value = copy.deepcopy(self.scored)
        value["runs"][0]["trace"]["model_actions"][0]["observation"] = {"ok": True, "result": "invented"}
        value["runs"][0]["trace"]["trajectory_sha256"] = evidence.sha(evidence.canonical(value["runs"][0]["trace"]["model_actions"]))
        value["summary"] = evidence.summarize(value["exposure"], value["runs"])
        with self.assertRaisesRegex(ValueError, "differs from replayed"):
            evidence.verify_historical(value)

    def test_timestamp_inversion_naivety_and_elapsed_fabrication_rejected(self):
        for timestamps, elapsed in (({"started_at": "2026-11-03T10:00:00+00:00", "finished_at": "2026-11-03T09:00:00+00:00"}, 1),
                                    ({"started_at": "2026-11-03T10:00:00", "finished_at": "2026-11-03T10:00:01"}, 1),
                                    ({"started_at": "2026-11-03T10:00:00+00:00", "finished_at": "2026-11-03T10:00:01+00:00"}, 1000)):
            value = copy.deepcopy(self.failed)
            value["runs"][0]["timestamps"] = timestamps
            value["runs"][0]["resources"]["elapsed_seconds"] = elapsed
            with self.assertRaises(ValueError):
                evidence.validate_profile(value)

    def test_missing_dimension_bad_counters_and_unattested_cost_claims_rejected(self):
        for key in ("ground_truth", "failure", "safety", "resources", "limitations", "identities"):
            value = copy.deepcopy(self.failed); del value["runs"][0][key]
            with self.assertRaises(ValueError): evidence.validate_profile(value)
        for key, bad in (("input_tokens", True), ("output_tokens", -1), ("provider_seconds", float("inf"))):
            value = copy.deepcopy(self.failed); value["runs"][0]["resources"][key] = bad
            with self.assertRaises(ValueError): evidence.validate_profile(value)
        for bill in ({"status": "unknown", "amount": "0", "currency": "USD", "source": None},
                     {"status": "observed", "amount": "0.50", "currency": "USD", "source": None},
                     {"status": "estimated", "amount": -1, "currency": "USD", "source": "invented"}):
            value = copy.deepcopy(self.failed); value["runs"][0]["resources"]["billing"] = bill
            with self.assertRaises(ValueError): evidence.validate_profile(value)
        value = copy.deepcopy(self.failed)
        value["runs"][0]["resources"]["billing"] = {"status": "estimated", "amount": "0.50", "currency": "USD", "source": "hypothetical-estimator"}
        self.assertTrue(evidence.validate_profile(value))
        with self.assertRaisesRegex(ValueError, "differs from replayed"):
            evidence.verify_historical(value)

    def test_every_nested_required_measurement_rejects_omission(self):
        for dimension in ("task", "identities", "trace", "outcome", "ground_truth", "failure", "safety", "resources", "timestamps"):
            for key in self.failed["runs"][0][dimension]:
                with self.subTest(dimension=dimension, key=key):
                    value = copy.deepcopy(self.failed); del value["runs"][0][dimension][key]
                    with self.assertRaises((ValueError, KeyError)):
                        evidence.validate_profile(value)
        for dimension in ("first_consequential_error", "recovery", "diagnosis", "human_interventions"):
            for key in self.failed["runs"][0]["failure"][dimension]:
                with self.subTest(dimension=dimension, key=key):
                    value = copy.deepcopy(self.failed); del value["runs"][0]["failure"][dimension][key]
                    with self.assertRaises(ValueError):
                        evidence.validate_profile(value)

    def test_localization_intervention_safety_and_timing_are_typed_and_bounded(self):
        mutations = [
            (("failure", "first_consequential_error", "status"), "made-up"),
            (("failure", "first_consequential_error", "event_index"), 0),
            (("failure", "human_interventions", "count"), -1),
            (("failure", "provider_retries"), True),
            (("failure", "diagnosis", "causal_attribution"), "PROVED"),
            (("failure", "recovery", "causal_repair_verified"), True),
            (("safety", "unauthorized_action_count"), -1),
            (("safety", "unauthorized_write_count"), 0.5),
            (("safety", "severity"), "severe-without-rubric"),
            (("resources", "provider_seconds"), 10**8),
            (("ground_truth", "independence"), "EXTERNALLY_DOCUMENTED"),
        ]
        for path, bad in mutations:
            with self.subTest(path=path):
                value = copy.deepcopy(self.failed); target = value["runs"][0]
                for key in path[:-1]: target = target[key]
                target[path[-1]] = bad
                with self.assertRaises(ValueError): evidence.validate_profile(value)
        for position in (-1, len(self.failed["runs"][0]["trace"]["model_actions"]), True):
            value = copy.deepcopy(self.failed)
            first = value["runs"][0]["failure"]["first_consequential_error"]
            first.update(status="observed", event_index=position)
            with self.assertRaises(ValueError): evidence.validate_profile(value)

    def test_malformed_existing_evidence_envelope_is_not_a_valid_profile(self):
        value = copy.deepcopy(self.failed)
        value["evidence_package"]["claims"][0]["status"] = "PROVED"
        with self.assertRaises(ValueError): evidence.validate_profile(value)
        value = copy.deepcopy(self.failed)
        value["evidence_package"]["claims"] = []
        with self.assertRaises(ValueError): evidence.validate_profile(value)

    def test_incomplete_trace_is_representable_only_with_unknown_outcome_and_no_rate(self):
        value = copy.deepcopy(self.failed)
        value["runs"][0]["trace"]["complete"] = False
        value["runs"][0]["outcome"].update(grade="unknown", valid=False)
        value["summary"] = evidence.summarize(value["exposure"], value["runs"])
        self.assertTrue(evidence.validate_profile(value))
        self.assertIsNone(value["summary"]["success_fraction"])
        with self.assertRaisesRegex(ValueError, "differs from replayed"):
            evidence.verify_historical(value)

    def test_hidden_oracle_in_request_rejected_even_with_recomputed_request_hash(self):
        run = self.failed["runs"][0]
        record = runner.strict_json(evidence.read_artifact(evidence.ROOT, run["trace"]["artifact"]))
        protocol = runner.strict_json(evidence.read_artifact(evidence.ROOT, run["identities"]["configuration"]))
        task = next(t for t in protocol["tasks"] if t["id"] == run["task"]["id"])
        request = runner.strict_json(record["events"][0]["request_utf8"])
        request["messages"].append({"role": "user", "content": json.dumps(task["oracle"])})
        record["events"][0]["request_utf8"] = evidence.canonical(request).decode()
        record["events"][0]["request_sha256"] = evidence.sha(evidence.canonical(request))
        with self.assertRaisesRegex(ValueError, "request/prompt drift"):
            evidence.project_run(task, record, run["trace"]["artifact"], run["identities"]["configuration"], record["source"])

    def test_original_grade_mutation_and_source_mutation_rejected(self):
        run = next(r for r in self.failed["runs"] if r["outcome"]["grade"] == "failure")
        record = runner.strict_json(evidence.read_artifact(evidence.ROOT, run["trace"]["artifact"]))
        protocol = runner.strict_json(evidence.read_artifact(evidence.ROOT, run["identities"]["configuration"]))
        task = next(t for t in protocol["tasks"] if t["id"] == run["task"]["id"])
        record["grade"]["passed"] = True
        with self.assertRaisesRegex(ValueError, "terminal state/outcome mismatch"):
            evidence.project_run(task, record, run["trace"]["artifact"], run["identities"]["configuration"], record["source"])
        source = copy.deepcopy(record["source"]); source["files"]["tools/tool_agent_reliability.py"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "source bytes mismatch"):
            evidence.verify_source(evidence.ROOT, source, evidence.V02_SOURCE)

    def test_raw_provider_action_forgery_fails_after_hash_is_updated(self):
        run = self.failed["runs"][0]
        record = runner.strict_json(evidence.read_artifact(evidence.ROOT, run["trace"]["artifact"]))
        protocol = runner.strict_json(evidence.read_artifact(evidence.ROOT, run["identities"]["configuration"]))
        task = next(t for t in protocol["tasks"] if t["id"] == run["task"]["id"])
        raw = base64.b64decode(record["events"][0]["response_base64"])
        envelope = runner.strict_json(raw)
        envelope["message"]["content"] = json.dumps({"tool": "finish", "args": {"answer": "forged"}})
        changed = evidence.canonical(envelope)
        record["events"][0]["response_base64"] = base64.b64encode(changed).decode()
        record["events"][0]["response_sha256"] = evidence.sha(changed)
        with self.assertRaisesRegex(ValueError, "action/tool receipt mismatch"):
            evidence.project_run(task, record, run["trace"]["artifact"], run["identities"]["configuration"], record["source"])

    def test_mutated_artifacts_and_unsafe_paths_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); (root / "x").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                evidence.read_artifact(root, evidence.artifact("x", b"original"))
            for path in ("../x", "/x", "a/../x", "a\\x", "a//x"):
                with self.assertRaises(ValueError): evidence.read_artifact(root, evidence.artifact(path, b"x"))
            (root / "escape").symlink_to("/etc/hosts")
            with self.assertRaisesRegex(ValueError, "escapes root"):
                evidence.read_artifact(root, evidence.artifact("escape", b"x"))

    def test_duplicate_zip_members_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            raw = io.BytesIO()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(raw, "w") as archive:
                    archive.writestr("run.json", b"first")
                    archive.writestr("run.json", b"second")
            Path(td, "evidence.zip").write_bytes(raw.getvalue())
            with self.assertRaisesRegex(ValueError, "duplicate archive member"):
                evidence.read_artifact(td, evidence.artifact("evidence.zip", b"second", ["run.json"]))

    def test_small_audit_receipt_reconstructs_both_profiles(self):
        audit = evidence.historical_audit()
        self.assertEqual(audit["audit_source_sha256"], evidence.sha(Path(evidence.__file__).read_bytes()))
        self.assertEqual(audit["cohorts"][0]["profile_canonical_sha256"], evidence.sha(evidence.canonical(self.scored)))
        self.assertEqual(audit["cohorts"][1]["profile_canonical_sha256"], evidence.sha(evidence.canonical(self.failed)))
        committed = runner.strict_json((evidence.ROOT / "research/tool-agent-reliability/evidence-contract-validation-v0.1.json").read_bytes())
        self.assertEqual(committed, audit)

    def test_nested_zip_raw_record_hash_and_trace_presence_checked(self):
        run = self.scored["runs"][0]
        raw = evidence.read_artifact(evidence.ROOT, run["trace"]["artifact"])
        self.assertEqual(runner.strict_json(raw)["task_id"], run["task"]["id"])
        wrong = copy.deepcopy(run["trace"]["artifact"]); wrong["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            evidence.read_artifact(evidence.ROOT, wrong)
        value = copy.deepcopy(self.scored); value["runs"][0]["trace"]["complete"] = False
        with self.assertRaisesRegex(ValueError, "trace assurance"):
            evidence.validate_profile(value)


if __name__ == "__main__":
    unittest.main()
