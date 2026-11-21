"""Fail-closed prelaunch checks; deterministic fixtures are NOT agent-run evidence."""
import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import replanning_study_gate as gate

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "research/workflow-efficacy/replanning-candidate-cohort-v1.json"


class StudyGateTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(CANDIDATE.read_text())

    def save(self, data):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        path = Path(d.name) / "candidate.json"
        path.write_text(json.dumps(data, sort_keys=True) + "\n")
        return path

    def test_registered_candidate_is_unsealed_not_execution(self):
        result = gate.check_candidate()
        self.assertEqual(result["status"], "CANDIDATE_NOT_FROZEN")
        self.assertFalse(result["scored_execution_authorized"])
        self.assertEqual(len(result["task_rows"]), 12)
        self.assertEqual(len(set(r["task_id"] for r in result["task_rows"])), 12)
        self.assertEqual(sum(r["interrupted"] for r in result["task_rows"]), 6)
        self.assertTrue(all(len(r["oracle_sha256"]) == 64 for r in result["task_rows"]))

    def test_selector_has_public_deterministic_unbiased_order(self):
        self.assertEqual(gate.task_selection(), [11, 15, 4, 28, 10, 14, 1, 19, 26, 12, 29, 25])
        self.assertEqual([f"FWE-{x+1:03d}" for x in gate.task_selection()],
                         ["FWE-012", "FWE-016", "FWE-005", "FWE-029", "FWE-011", "FWE-015",
                          "FWE-002", "FWE-020", "FWE-027", "FWE-013", "FWE-030", "FWE-026"])

    def test_missing_launch_manifest_fails_closed(self):
        with self.assertRaisesRegex(gate.GateError, "SCORING_BLOCKED"):
            gate.require_launch_manifest(gate.check_candidate(), None)

    def test_candidate_cannot_self_mark_frozen_or_authorized(self):
        for key in ("independent_oracle_approved", "independent_cohort_approved",
                    "cohort_frozen", "provider_currently_attested", "scored_run_authorized"):
            with self.subTest(key=key):
                v = copy.deepcopy(self.data)
                v[key] = True
                with self.assertRaises(gate.GateError):
                    gate.check_candidate(self.save(v))

    def test_candidate_cannot_claim_scored_runs(self):
        for count in (1, 24, True, -1):
            with self.subTest(count=count):
                v = copy.deepcopy(self.data)
                v["scored_runs_executed"] = count
                with self.assertRaises(gate.GateError):
                    gate.check_candidate(self.save(v))

    def test_reject_duplicate_indices_and_selection_mutations(self):
        for new in (self.data["selected_indices"][:-1],
                    self.data["selected_indices"][::-1],
                    self.data["selected_indices"][:-1] + [11],
                    self.data["selected_indices"][:-1] + [True],
                    self.data["selected_indices"][:-1] + [999]):
            v = copy.deepcopy(self.data)
            v["selected_indices"] = new
            with self.assertRaises(gate.GateError):
                gate.check_candidate(self.save(v))

    def test_reject_interruption_mutations(self):
        for new in ([], self.data["interrupted_indices"][::-1],
                    self.data["interrupted_indices"][:-1] + [False],
                    self.data["interrupted_indices"][:-1] + [16]):
            v = copy.deepcopy(self.data)
            v["interrupted_indices"] = new
            with self.assertRaises(gate.GateError):
                gate.check_candidate(self.save(v))

    def test_candidate_oracle_and_source_byte_drift_fails(self):
        v = copy.deepcopy(self.data)
        v["source_git_blob_sha1"] = "0"*40
        with self.assertRaisesRegex(gate.GateError, "underlying fixture source changed"):
            gate.check_candidate(self.save(v))
        v = copy.deepcopy(self.data)
        v["reference_code"] = "untrusted/grader.py"
        with self.assertRaises(gate.GateError):
            gate.check_candidate(self.save(v))

    def test_duplicate_json_keys_fail(self):
        path = self.save(self.data)
        path.write_text('{"schema":"a","schema":"b"}')
        with self.assertRaisesRegex(gate.GateError, "duplicate JSON key"):
            gate.check_candidate(path)

    def test_nonfinite_json_rejected(self):
        path = self.save(self.data)
        path.write_text('{"value":NaN}')
        with self.assertRaisesRegex(gate.GateError, "nonfinite JSON"):
            gate.check_candidate(path)

    def test_invalid_utf8_and_oversize_fail(self):
        path = self.save(self.data)
        path.write_bytes(b'\xff')
        with self.assertRaises(gate.GateError):
            gate.check_candidate(path)
        path.write_bytes(b'x'*131073)
        with self.assertRaises(gate.GateError):
            gate.check_candidate(path)

    def test_candidate_requires_exact_schema_and_limitation_disclosure(self):
        for key, value in (("limitations", []), ("origin", "brand new"),
                           ("model_candidate", "unknown"), ("study_id", "other")):
            v = copy.deepcopy(self.data)
            v[key] = value
            with self.assertRaises(gate.GateError):
                gate.check_candidate(self.save(v))

    def test_source_git_blob_checksum_reproduces_hash_object(self):
        raw = (ROOT / self.data["source_path"]).read_bytes()
        expected = gate.git_blob_sha(raw)
        self.assertEqual(expected, self.data["source_git_blob_sha1"])
        self.assertEqual(gate.git_blob_sha(raw + b'\n'),
                         hashlib.sha1(b'blob ' + str(len(raw)+1).encode() + b'\0' + raw + b'\n').hexdigest())
        self.assertNotEqual(expected, gate.git_blob_sha(raw + b'\n'))

    def test_integrity_hashes_change_with_task_edit(self):
        unchanged = gate.check_candidate()
        # Mutating an oracle in-memory must change the byte-bound digest.
        items = [{"input": {"a": 1}, "expected": True}]
        original = gate.digest(gate.canonical(items))
        items[0]["expected"] = False
        self.assertNotEqual(original, gate.digest(gate.canonical(items)))
        self.assertEqual(len(unchanged["cohort_content_sha256"]), 64)

    def test_manifest_that_claims_ready_without_registered_fields_fails(self):
        c = gate.check_candidate()
        path = self.save({"schema":"far-replanning-launch/1", "status":"READY"})
        with self.assertRaisesRegex(gate.GateError, "keys differ"):
            gate.require_launch_manifest(c, path)

    def test_launch_does_not_accept_fake_unsigned_reviewer_strings(self):
        c = gate.check_candidate()
        path = self.save({"schema":"far-replanning-launch/1", "independent_reviewer_identity":"myself"})
        with self.assertRaises(gate.GateError):
            gate.require_launch_manifest(c, path)

    def test_cli_not_run_output_is_explicit(self):
        with patch("sys.argv", ["replanning_study_gate"]):
            self.assertEqual(gate.main([]), 0)


if __name__ == "__main__":
    unittest.main()
