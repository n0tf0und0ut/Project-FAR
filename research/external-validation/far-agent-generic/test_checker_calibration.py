"""Calibrate both real checker implementations on previously exposed W4 evidence.

These are internal known-label fixtures. They are NOT independent tasks,
not an agent efficacy experiment, and do not satisfy launch preconditions.
"""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import subprocess
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))
import checker_calibration as adapter
from tools.check_pca_w6_empirical_audit_utility import EXPECTED_W4_RECORDS

def compact(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()

class RealCheckerCalibrationTests(unittest.TestCase):
    def test_every_original_w4_record_has_matching_collision_label(self):
        labels = []
        for rec in EXPECTED_W4_RECORDS:
            original = (REPO / rec["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(original).hexdigest(), rec["sha256"])
            expected = "LOSS" if rec["variant"] == "lossy" else "NO_LOSS"
            for arm in ("generic_checker", "far"):
                observed = adapter.evaluate(arm, original)
                self.assertEqual(observed["classification"], expected, (rec["path"], arm, observed))
                self.assertEqual(observed["mode"], "CALIBRATION_ONLY_NO_AGENT")
                labels.append((arm, expected))
        self.assertEqual(len(labels), 24)

    def test_integrity_corruption_remains_specific_to_far(self):
        source = next(r for r in EXPECTED_W4_RECORDS if r["variant"] == "repaired")
        original = json.loads((REPO / source["path"]).read_bytes())
        changed = copy.deepcopy(original)
        changed["freeze"]["contract_sha256"] = "0" * 64
        raw = compact(changed)
        generic = adapter.evaluate("generic_checker", raw)
        far = adapter.evaluate("far", raw)
        self.assertEqual(generic["classification"], "NO_LOSS")
        self.assertEqual(far["classification"], "INVALID")
        self.assertEqual(generic["mode"], far["mode"])

    def test_bad_arm_rejected_even_for_valid_fixture(self):
        fixture = (REPO / EXPECTED_W4_RECORDS[0]["path"]).read_bytes()
        with self.assertRaisesRegex(ValueError, "unregistered"):
            adapter.evaluate("baseline", fixture)

    def test_duplicate_keys_rejected_for_both_arms(self):
        raw = b'{"contract":{},"contract":{}}'
        for arm in ("generic_checker", "far"):
            with self.subTest(arm=arm), self.assertRaisesRegex(ValueError, "duplicate"):
                adapter.evaluate(arm, raw)

    def test_nonfinite_json_rejected_for_both_arms(self):
        for arm in ("generic_checker", "far"):
            with self.subTest(arm=arm), self.assertRaisesRegex(ValueError, "non-finite"):
                adapter.evaluate(arm, b'{"some":Infinity}')

    def test_input_size_bound(self):
        with self.assertRaisesRegex(ValueError, "oversized"):
            adapter.evaluate("far", b"x" * (adapter.MAX_INPUT_BYTES + 1))

    def test_excessive_nesting_rejected(self):
        nested = (b"[" * 70) + b"0" + (b"]" * 70)
        with self.assertRaisesRegex(ValueError, "nesting"):
            adapter.evaluate("generic_checker", nested)

    def test_missing_tables_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "finite tables"):
            adapter.evaluate("generic_checker", b'{"contract":{}}')

    def test_command_never_advertises_live_agent_execution(self):
        fixture = (REPO / EXPECTED_W4_RECORDS[1]["path"]).read_bytes()
        cmd = [sys.executable, str(HERE / "checker_calibration.py"),
               "--calibration-only", "--arm", "generic_checker"]
        run = subprocess.run(cmd, input=fixture, capture_output=True, check=False)
        self.assertEqual(run.returncode, 0, run.stderr.decode())
        obj = json.loads(run.stdout)
        self.assertEqual(obj["mode"], "CALIBRATION_ONLY_NO_AGENT")
        self.assertEqual(obj["classification"], "NO_LOSS")
        self.assertNotIn("execution_authorized", obj)
        self.assertNotIn("receipt_verified", obj)

    def test_cli_requires_calibration_flag(self):
        result = subprocess.run([sys.executable, str(HERE / "checker_calibration.py"),
                                 "--arm", "far"], input=b"{}", capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(b"CALIBRATION_ONLY_NO_AGENT", result.stdout)

if __name__ == "__main__":
    unittest.main()
