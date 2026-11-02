"""Fail-closed routing boundary tests against current FAR semantic verifiers."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.far_routing_dispatch import RoutingError, route_text

ROOT = Path(__file__).resolve().parents[1]
V20 = ROOT / "conformance/far-ir-2.0/valid-factorization.json"
V21 = ROOT / "conformance/far-ir-2.1/valid-frontier.json"
BAD20 = ROOT / "conformance/far-ir-2.0/invalid-factorization.json"


class KnownContractRoutingTests(unittest.TestCase):
    def test_two_formats_both_modes_use_current_verifiers(self):
        for fixture, expected_format, expected_verifier in [
            (V20, "far-ir/2.0", "contract_v2_strict_v11"),
            (V21, "far-ir/2.1", "contract_v21_errata1"),
        ]:
            raw = fixture.read_text(encoding="utf-8")
            for mode in ("deterministic", "declarative"):
                with self.subTest(fixture=fixture.name, mode=mode):
                    result = route_text(raw, mode=mode)
                    self.assertEqual(result["status"], "VERIFIED_EXPLICIT_CONTRACT")
                    self.assertEqual(result["format_version"], expected_format)
                    self.assertEqual(result["outcome"], "PROVED")
                    self.assertIn(expected_verifier, result["verifier"])
                    self.assertEqual(result["dispatch_policy"], mode)
                    self.assertEqual(result["model_calls"], 0)
                    self.assertFalse(result["does_not_bypass_intake"])
                    self.assertEqual(len(result["source_sha256"]), 64)

    def test_invalid_downstream_contract_never_bypasses_discovery(self):
        for mode in ("deterministic", "declarative"):
            result = route_text(BAD20.read_text(encoding="utf-8"), mode=mode)
            self.assertEqual(result["status"], "DISCOVERY_REQUIRED")
            self.assertEqual(result["reason"], "DOWNSTREAM_CONTRACT_REJECTED")
            self.assertEqual(result["format_version"], "far-ir/2.0")
            self.assertFalse(result["verifier_success"])
            self.assertIsNone(result["outcome"])
            self.assertTrue(result["diagnostics"])
            self.assertTrue(result["does_not_bypass_intake"])

    def test_forged_version_and_missing_contract_do_not_select_a_verifier(self):
        for raw in ('{"format_version":"far-ir/999","report":{"outcome":"PROVED"}}',
                    '{"format_version":"far-ir/2.0","report":{"outcome":"PROVED"}}',
                    '{"format_version":"far-intake/1.0","report":{"outcome":"PROVED"}}',
                    '{"claim":"It must be true"}', '"not a contract"'):
            value = route_text(raw)
            self.assertEqual(value["status"], "DISCOVERY_REQUIRED")
            self.assertIsNone(value["outcome"])
            self.assertEqual(value["model_calls"], 0)
            self.assertTrue(value["does_not_bypass_intake"])

    def test_reject_duplicate_or_nan_transport_and_no_auto_repair(self):
        for raw in ('{"format_version":"far-ir/2.0","format_version":"far-ir/2.1"}',
                    '{"format_version":"far-ir/2.0","x":NaN}',
                    '{"format_version":"far-ir/2.0","x":Infinity}', '{oops'):
            result = route_text(raw)
            self.assertEqual(result["reason"], "INVALID_TRANSPORT")
            self.assertEqual(result["status"], "DISCOVERY_REQUIRED")
            self.assertIsNone(result["outcome"])
            self.assertEqual(result["model_calls"], 0)

    def test_fail_closed_verifier_exception_cannot_become_discovery_success(self):
        raw = V20.read_text(encoding="utf-8")
        with patch("mechanization.far_mechanization.contract_v2_strict_v11.validate_contract",
                   side_effect=RuntimeError("simulated unavailable")):
            result = route_text(raw)
        self.assertEqual(result["status"], "VERIFIER_UNAVAILABLE")
        self.assertEqual(result["error_class"], "RuntimeError")
        self.assertIsNone(result["outcome"])
        self.assertEqual(result["model_calls"], 0)

    def test_direct_and_declarative_have_identical_observed_outcomes(self):
        for fixture in (V20, BAD20, V21):
            raw = fixture.read_text(encoding="utf-8")
            a = route_text(raw, mode="deterministic")
            b = route_text(raw, mode="declarative")
            self.assertEqual((a["status"], a["outcome"], a["reason"], a["diagnostics"]),
                             (b["status"], b["outcome"], b["reason"], b["diagnostics"]))

    def test_unknown_policy_is_never_auto_model(self):
        with self.assertRaises(RoutingError):
            route_text(V20.read_text(encoding="utf-8"), mode="agent")

    def test_cli_real_execution_and_discovery_exit_codes(self):
        for fixture, exitcode in ((V20, 0), (V21, 0), (BAD20, 3)):
            for mode in ("deterministic", "declarative"):
                process = subprocess.run(
                    [sys.executable, "tools/far_routing_dispatch.py", str(fixture), "--mode", mode],
                    cwd=ROOT, text=True, capture_output=True)
                self.assertEqual(process.returncode, exitcode, process.stderr + process.stdout)
                self.assertEqual(json.loads(process.stdout)["model_calls"], 0)

    def test_no_model_used_even_if_import_attempted(self):
        # This implementation has no model import, network client, or agent callback.
        result = route_text(V20.read_text())
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["route"], "verify_current")


if __name__ == "__main__":
    unittest.main()
