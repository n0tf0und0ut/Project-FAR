"""Adversarial regression coverage for the Cloudflare-to-FAR advisory handoff."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools import cloudflare_security_audit_ledger as bridge

ROOT = Path(__file__).resolve().parents[1]
TRACE = {
    "kind": "entrypoint",
    "file": "tools/cloudflare_security_audit_ledger.py",
    "line": 1,
    "scope": "isolated test fixture",
    "description": "source exists at pinned head",
}
EVIDENCE = {
    "file": "tools/cloudflare_security_audit_ledger.py",
    "line": 1,
    "description": "source reference for parser contract",
}


def sample(verdict):
    base = {
        "verdict": verdict,
        "fingerprint": "safe-001",
        "title": "Dummy local check",
        "description": "Harmless fixture only",
        "trace": [copy.deepcopy(TRACE)],
        "evidence": [copy.deepcopy(EVIDENCE)],
    }
    if verdict == "needs_validation":
        base.update({
            "claimed_root_cause": "Unknown deployment control",
            "blockers": ["Local fixture lacks network topology"],
            "validation_plan": {"local": "Inspect isolated fixture"},
        })
    elif verdict == "rejected":
        base.update({
            "claimed_root_cause": "Claimed misrouting",
            "reason": "Source check demonstrates routing is correct",
        })
    else:
        base.update({
            "root_cause": "Missing dummy authorization check",
            "intended_behavior": "Deny invalid dummy access",
            "conditions": [{
                "kind": "authentication_level",
                "description": "Dummy unauthenticated principal",
            }],
            "execution": {
                "attacker_perspective": "Dummy unauthenticated principal",
                "payloads": ["dummy secret value"],
                "instructions": ["Check local fixture only"],
                "observed_result": "Wrong dummy return value",
            },
            "remediation": {"strategy": "Require dummy authorization"},
            "severity": {
                "likelihood": {"score": "low", "reason": "Fixture only"},
                "impact": {"score": "low", "reason": "No real impact"},
                "overall_severity": "low",
            },
            "confidence": {"score": "low", "reason": "Fixture only"},
        })
    return base


class SecurityLedgerHandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run_dir = Path(self.temp.name)
        self.head = bridge.current_head(ROOT)
        self.meta = {
            "run_id": "unit-001",
            "repo": "Project-FAR",
            "source_ref": self.head,
            "run_status": "complete",
            "execution_policy": "sandboxed-source-and-local-only",
        }
        self.findings = [sample("needs_validation")]
        self.persist()

    def persist(self):
        for name, obj in (
            ("run-metadata.json", self.meta),
            ("coverage-ledger.json", {"units": []}),
            ("findings.json", self.findings),
        ):
            (self.run_dir / name).write_text(
                json.dumps(obj, ensure_ascii=False), encoding="utf-8"
            )

    def test_needs_validation_is_open_and_has_no_severity(self):
        result = bridge.build_report(self.run_dir, self.head)
        self.assertIn("needs_validation", result)
        self.assertIn("OPEN / NOT ADJUDICATED", result)
        self.assertNotIn("reported severity", result)
        self.assertIn(self.head, result)

    def test_confirmed_is_not_promoted_and_payload_is_not_exported(self):
        self.findings = [sample("confirmed")]
        self.persist()
        result = bridge.build_report(self.run_dir, self.head)
        self.assertIn("Cloudflare-reported severity (not FAR-verified): low", result)
        self.assertIn("OPEN / NOT ADJUDICATED", result)
        self.assertNotIn("dummy secret value", result)
        self.assertNotIn("Check local fixture only", result)

    def test_rejected_cannot_disprove_another_review(self):
        self.findings = [sample("rejected")]
        self.persist()
        report = bridge.build_report(self.run_dir, self.head)
        self.assertIn("rejected", report)
        self.assertIn("OPEN / NOT ADJUDICATED", report)

    def test_incomplete_run_remains_explicitly_incomplete(self):
        self.meta["run_status"] = "incomplete"
        self.persist()
        self.assertIn("Audit incomplete:", bridge.build_report(self.run_dir, self.head))

    def test_exact_head_mismatch_and_missing_sandbox_fails(self):
        self.meta["source_ref"] = "0" * 40
        self.persist()
        with self.assertRaisesRegex(bridge.HandoffError, "source SHA"):
            bridge.build_report(self.run_dir, self.head)
        self.meta["source_ref"] = self.head
        self.meta["execution_policy"] = "unrestricted"
        self.persist()
        with self.assertRaisesRegex(bridge.HandoffError, "execution policy"):
            bridge.build_report(self.run_dir, self.head)

    def test_duplicate_fingerprint_and_unsafe_paths_fail(self):
        self.findings = [sample("rejected"), sample("rejected")]
        self.persist()
        with self.assertRaisesRegex(bridge.HandoffError, "duplicate vulnerability"):
            bridge.build_report(self.run_dir, self.head)
        self.findings = [sample("rejected")]
        self.findings[0]["trace"][0]["file"] = "../AGENTS.md"
        self.persist()
        with self.assertRaisesRegex(bridge.HandoffError, "unsafe source"):
            bridge.build_report(self.run_dir, self.head)

    def test_duplicate_json_key_fails_closed(self):
        (self.run_dir / "findings.json").write_text(
            '{"a": 1, "a": 2}', encoding="utf-8"
        )
        with self.assertRaisesRegex(bridge.HandoffError, "duplicate JSON"):
            bridge.build_report(self.run_dir, self.head)

    def test_output_must_be_outside_repository(self):
        process = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools/cloudflare_security_audit_ledger.py"),
                "--run-dir", str(self.run_dir),
                "--expected-head", self.head,
                "--output", str(ROOT / "FAR-UNSAFE-OUTPUT.md"),
            ],
            capture_output=True, text=True, timeout=20, cwd=ROOT
        )
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("outside the source repository", process.stdout)
        self.assertFalse((ROOT / "FAR-UNSAFE-OUTPUT.md").exists())


if __name__ == "__main__":
    unittest.main()
