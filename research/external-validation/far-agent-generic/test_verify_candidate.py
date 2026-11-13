"""Adversarial contract tests. Synthetic log bytes never constitute an agent run."""
from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys
import unittest

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("far_generic_contract", HERE / "verify_candidate.py")
assert spec is not None and spec.loader is not None
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def raw(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sample_receipt(arm="far", activated=True):
    payloads = {
        "raw_request_b64": b'{"cases":["a","b"]}',
        "raw_response_b64": b'{"success":false}',
        "raw_continuation_b64": b"agent inspected verifier result",
        "pre_state_b64": b"pre-state",
        "post_state_b64": b"post-state",
    }
    events = ([{"index": 0, "tool_id": v.TOOLS[arm],
                **{k: base64.b64encode(val).decode() for k, val in payloads.items()}}]
              if activated else [])
    log = {"schema": "far-agent-tool-log/1", "run_id": "run-001", "arm": arm,
           "blind_task_id": "TASK-000001", "repetition": 1,
           "configuration_root_sha256": "1" * 64, "events": events}
    log_bytes = raw(log)
    receipt = {
        "schema": "far-agent-mechanism-receipt/1", "run_id": "run-001", "arm": arm,
        "blind_task_id": "TASK-000001", "repetition": 1,
        "configuration_root_sha256": "1" * 64,
        "raw_event_log_sha256": digest(log_bytes), "tool_event_index": 0 if activated else None,
        "raw_request_sha256": digest(payloads["raw_request_b64"]) if activated else None,
        "raw_response_sha256": digest(payloads["raw_response_b64"]) if activated else None,
        "raw_continuation_sha256": digest(payloads["raw_continuation_b64"]) if activated else None,
        "pre_state_sha256": digest(payloads["pre_state_b64"]) if activated else None,
        "post_state_sha256": digest(payloads["post_state_b64"]) if activated else None,
        "mechanism_status": "activated" if activated else "not_triggered",
        "runtime_attestation_root_sha256": "2" * 64,
    }
    return receipt, log


class ResearchCandidateTests(unittest.TestCase):
    def test_candidate_frozen_bytes_read_back(self):
        result = v.check_candidate(v.PROTOCOL.read_bytes(), v.LAUNCH.read_bytes())
        self.assertEqual(result["status"], "RESEARCH_CANDIDATE_VERIFIED_LAUNCH_BLOCKED")
        self.assertFalse(result["model_calls_authorized"])
        self.assertEqual(result["external_prerequisites_supplied"], 0)
        self.assertEqual(result["external_prerequisites_required"], 16)

    def test_require_launch_denied(self):
        p = subprocess.run([sys.executable, str(HERE / "verify_candidate.py"), "--require-launch"],
                           capture_output=True, text=True, check=False)
        self.assertEqual(p.returncode, 3)
        self.assertIn("DENIED:", p.stdout)

    def test_no_inheritance_of_v3_execution_grants(self):
        data = v.exact_json(v.PROTOCOL.read_bytes())
        self.assertTrue(data["prior_evidence"]["no_inheritance_of_launch_authorization"])
        self.assertEqual(data["primary_contrast"], "far_minus_generic_checker")
        self.assertEqual([x["id"] for x in data["arms"]], ["generic_checker", "far"])

    def test_any_protocol_edit_requires_new_review(self):
        tampered = v.PROTOCOL.read_bytes().replace(
            b"far_minus_generic_checker", b"far_minus_placebo", 1)
        with self.assertRaisesRegex(ValueError, "preregistration changed"):
            v.check_candidate(tampered, v.LAUNCH.read_bytes())

    def test_authorization_mutation_fails_closed(self):
        gate = v.LAUNCH.read_bytes().replace(b'"launch_authorization": false',
                                             b'"launch_authorization": true')
        with self.assertRaisesRegex(ValueError, "launch state changed"):
            v.check_candidate(v.PROTOCOL.read_bytes(), gate)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON"):
            v.exact_json(b'{"a":1,"a":2}')

    def test_nonfinite_json_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-finite"):
            v.exact_json(b'{"n":NaN}')


class ReceiptBindingTests(unittest.TestCase):
    def checked(self, receipt, log):
        return v.check_receipt(receipt, raw(log))

    def test_structure_bound_is_not_authenticated_execution(self):
        for arm in ("far", "generic_checker"):
            receipt, log = sample_receipt(arm)
            self.assertIn("UNATTESTED", self.checked(receipt, log))

    def test_nonactivation_retained(self):
        receipt, log = sample_receipt(activated=False)
        self.assertEqual(self.checked(receipt, log),
                         "STRUCTURALLY_BOUND_UNATTESTED_NO_TRIGGER")

    def test_missing_required_evidence_rejected(self):
        receipt, log = sample_receipt()
        del receipt["raw_continuation_sha256"]
        with self.assertRaisesRegex(ValueError, "keys"):
            self.checked(receipt, log)

    def test_altered_trusted_log_rejected(self):
        receipt, log = sample_receipt()
        log["events"][0]["tool_id"] = "other"
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            self.checked(receipt, log)

    def test_changing_hash_to_match_wrong_tool_does_not_help(self):
        receipt, log = sample_receipt()
        log["events"][0]["tool_id"] = "generic_checker"
        receipt["raw_event_log_sha256"] = digest(raw(log))
        with self.assertRaisesRegex(ValueError, "wrong tool"):
            self.checked(receipt, log)

    def test_wrong_arm_identity_rejected(self):
        receipt, log = sample_receipt()
        receipt["arm"] = "generic_checker"
        with self.assertRaisesRegex(ValueError, "run identity mismatch"):
            self.checked(receipt, log)

    def test_forged_output_hash_rejected(self):
        receipt, log = sample_receipt()
        receipt["raw_response_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "tool evidence digest mismatch"):
            self.checked(receipt, log)

    def test_forged_continuation_hash_rejected(self):
        receipt, log = sample_receipt()
        receipt["raw_continuation_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "tool evidence digest mismatch"):
            self.checked(receipt, log)

    def test_out_of_order_event_rejected(self):
        receipt, log = sample_receipt()
        log["events"][0]["index"] = 1
        receipt["raw_event_log_sha256"] = digest(raw(log))
        with self.assertRaisesRegex(ValueError, "ordering"):
            self.checked(receipt, log)

    def test_bool_repetition_not_accepted(self):
        receipt, log = sample_receipt()
        receipt["repetition"] = True
        with self.assertRaisesRegex(ValueError, "repetition"):
            self.checked(receipt, log)

    def test_nontrigger_cannot_hide_invocation(self):
        receipt, log = sample_receipt()
        receipt["mechanism_status"] = "not_triggered"
        receipt["tool_event_index"] = None
        for field in v.DIGEST_FIELDS:
            receipt[field] = None
        with self.assertRaisesRegex(ValueError, "conceals checker invocation"):
            self.checked(receipt, log)

    def test_activated_without_real_event_rejected(self):
        receipt, log = sample_receipt(activated=False)
        receipt["mechanism_status"] = "activated"
        receipt["tool_event_index"] = 0
        with self.assertRaisesRegex(ValueError, "missing actual tool event"):
            self.checked(receipt, log)

    def test_empty_observation_not_a_tool_receipt(self):
        receipt, log = sample_receipt()
        log["events"][0]["raw_response_b64"] = ""
        receipt["raw_event_log_sha256"] = digest(raw(log))
        with self.assertRaisesRegex(ValueError, "empty"):
            self.checked(receipt, log)

    def test_noncanonical_or_malformed_base64_rejected(self):
        receipt, log = sample_receipt()
        log["events"][0]["raw_request_b64"] = "@@@@"
        receipt["raw_event_log_sha256"] = digest(raw(log))
        with self.assertRaisesRegex(ValueError, "base64"):
            self.checked(receipt, log)

    def test_duplicate_log_key_rejected(self):
        receipt, log = sample_receipt(activated=False)
        text = raw(log)
        self.assertRaises(ValueError, v.check_receipt, receipt,
                          text.replace(b'"run_id":', b'"run_id":"fake","run_id":', 1))


if __name__ == "__main__":
    unittest.main()
