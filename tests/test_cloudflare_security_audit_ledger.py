"""Adversarial regression coverage for the Cloudflare-to-FAR advisory handoff."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

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
        self.coverage = []  # Exact top-level format accepted by the pinned validator.
        self.persist()

    def persist(self):
        for name, obj in (
            ("run-metadata.json", self.meta),
            ("coverage-ledger.json", self.coverage),
            ("findings.json", self.findings),
        ):
            (self.run_dir / name).write_text(
                json.dumps(obj, ensure_ascii=True), encoding="utf-8"
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
        # The pinned upstream validator now rejects this before the
        # in-process duplicate-fingerprint check. Either rejection is valid;
        # never weaken acceptance of duplicate identities.
        with self.assertRaisesRegex(
            bridge.HandoffError, "pinned Cloudflare validator|duplicate vulnerability"
        ):
            bridge.build_report(self.run_dir, self.head)
        self.findings = [sample("rejected")]
        self.findings[0]["trace"][0]["file"] = "../AGENTS.md"
        self.persist()
        # Source-path rejection may now occur in the trusted upstream
        # validator before FAR's own source-reference inspection.
        with self.assertRaisesRegex(
            bridge.HandoffError, "pinned Cloudflare validator|unsafe source"
        ):
            bridge.build_report(self.run_dir, self.head)

    def test_cloudflare_visible_content_survives_far_schema_compatibility(self):
        self.findings = [sample("rejected")]
        self.findings[0]["title"] = " \t "
        self.persist()
        with self.assertRaisesRegex(bridge.HandoffError, "pinned Cloudflare validator"):
            bridge.build_report(self.run_dir, self.head)
        source = bridge.safe_load_json(bridge.SCHEMA)
        normalized = bridge.schema_compatible_with_far(source)
        self.assertIn("visibleContent", json.dumps(source))
        self.assertNotIn("visibleContent", json.dumps(normalized))
        self.assertIn("required", json.dumps(normalized))

    def test_untracked_dotgit_path_is_not_source_evidence(self):
        self.findings = [sample("rejected")]
        self.findings[0]["trace"][0]["file"] = ".git/config"
        self.persist()
        with self.assertRaisesRegex(bridge.HandoffError, "not tracked"):
            bridge.build_report(self.run_dir, self.head)

    def test_dirty_git_checkout_cannot_bind_source_claims_to_head(self):
        with patch.object(
            bridge.subprocess, "run",
            return_value=SimpleNamespace(stdout=" M tools/something.py\n"),
        ):
            with self.assertRaisesRegex(bridge.HandoffError, "checkout is dirty"):
                bridge.source_is_clean_and_tracked(ROOT)

    def test_duplicate_json_key_fails_closed(self):
        (self.run_dir / "findings.json").write_text(
            '{"a": 1, "a": 2}', encoding="utf-8"
        )
        with self.assertRaisesRegex(bridge.HandoffError, "duplicate JSON"):
            bridge.build_report(self.run_dir, self.head)


    def test_handoff_text_sanitizer_preserves_identity_and_source_references(self):
        self.assertEqual(bridge.clean_text("safe-001"), "safe-001")
        self.assertEqual(bridge.clean_text("tools/demo.py:21"), "tools/demo.py:21")
        report = bridge.build_report(self.run_dir, self.head)
        self.assertIn("| safe-001 | needs_validation |", report)
        self.assertIn("tools/cloudflare\\_security\\_audit\\_ledger.py:1", report)
        self.assertIn("CF/safe-001: Dummy local check", report)

    def test_pinned_upstream_rejects_default_ignorable_only_title(self):
        self.findings = [sample("rejected")]
        self.findings[0]["title"] = "\u034f"
        self.persist()
        with self.assertRaisesRegex(bridge.HandoffError, "pinned Cloudflare validator"):
            bridge.build_report(self.run_dir, self.head)

    def test_pinned_upstream_rejects_unpaired_surrogate_in_visible_title(self):
        self.findings = [sample("rejected")]
        self.findings[0]["title"] = "Visible" + chr(0xD800)
        self.persist()
        with self.assertRaisesRegex(bridge.HandoffError, "pinned Cloudflare validator"):
            bridge.build_report(self.run_dir, self.head)

    def test_skip_worktree_changed_source_is_not_exact_head_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "source"
            repo.mkdir()
            def git(*args):
                return subprocess.run(
                    ["git", *args], cwd=repo, check=True, capture_output=True,
                ).stdout
            git("init", "-q")
            git("config", "user.name", "FAR source fixture")
            git("config", "user.email", "fixture@example.invalid")
            target = repo / "evidence.py"
            target.write_text("original line\n", encoding="utf-8")
            git("add", "evidence.py")
            git("commit", "-qm", "frozen source")
            references = [{"trace": [{"file": "evidence.py", "line": 1}],
                           "evidence": []}]
            bridge.inspect_source_references(references, repo, bridge.current_head(repo))
            git("update-index", "--skip-worktree", "evidence.py")
            target.write_text("original line\nforged line\n", encoding="utf-8")
            self.assertEqual(git("status", "--porcelain=v1"), b"")
            references[0]["trace"][0]["line"] = 2
            with self.assertRaisesRegex(bridge.HandoffError, "do not match requested commit"):
                bridge.inspect_source_references(references, repo, bridge.current_head(repo))

    def test_upstream_valid_unicode_snapshot_stays_within_original_byte_budget(self):
        # 900k CJK characters occupy 2.7 MiB as UTF-8, but 5.4 MiB if
        # snapshotting escapes each character to \\uXXXX. The pinned
        # validator accepts the original source record; the converter must.
        self.findings = [sample("rejected")]
        self.findings[0]["description"] = "漢" * 900_000
        direct = self.run_dir / "findings.json"
        direct.write_text(
            json.dumps(self.findings, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        self.assertLess(direct.stat().st_size, bridge.MAX_INPUT)
        original = subprocess.run(
            ["node", str(bridge.UPSTREAM_FINDINGS_VALIDATOR), str(direct)],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(original.returncode, 0, original.stdout + original.stderr)
        rendered = bridge.build_report(self.run_dir, self.head)
        self.assertIn("CF/safe-001", rendered)

    def test_coverage_ledger_matches_upstream_top_level_array(self):
        path = self.run_dir / "coverage-ledger.json"
        validated = subprocess.run(
            ["node", str(bridge.UPSTREAM_COVERAGE_VALIDATOR), str(path)],
            cwd=ROOT, capture_output=True, text=True, timeout=20,
        )
        self.assertEqual(validated.returncode, 0, validated.stdout + validated.stderr)
        self.assertIn("safe-001", bridge.build_report(self.run_dir, self.head))
        self.coverage = {"units": []}
        self.persist()
        with self.assertRaisesRegex(bridge.HandoffError, "coverage ledger container"):
            bridge.build_report(self.run_dir, self.head)

    def test_escaped_unpaired_surrogate_metadata_does_not_create_output(self):
        self.meta["run_id"] = "run-" + chr(0xD800)
        self.persist()
        with self.assertRaisesRegex(bridge.HandoffError, "invalid Unicode scalar"):
            bridge.build_report(self.run_dir, self.head)
        destination = self.run_dir / "advisory-output.md"
        result = subprocess.run(
            [sys.executable, str(ROOT / "tools/cloudflare_security_audit_ledger.py"),
             "--run-dir", str(self.run_dir), "--expected-head", self.head,
             "--output", str(destination)],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(destination.exists())

    def test_upstream_rejection_precedes_costly_local_schema_walk(self):
        self.findings = [sample("rejected")]
        self.findings[0]["trace"] = [[0] * 120 + [i] for i in range(1000)]
        self.persist()
        with patch.object(bridge, "Draft202012Validator",
                          side_effect=AssertionError("slow local schema validation invoked")):
            with self.assertRaisesRegex(bridge.HandoffError, "pinned Cloudflare validator"):
                bridge.build_report(self.run_dir, self.head)

    def test_git_replace_cannot_substitute_evidence_for_exact_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            def git(*args):
                return subprocess.run(["git", *args], cwd=repo, capture_output=True,
                                      check=True).stdout.strip()
            git("init", "-q")
            git("config", "user.name", "FAR replacement fixture")
            git("config", "user.email", "fixture@example.invalid")
            evidence = repo / "evidence.py"
            evidence.write_text("original line\\n", encoding="utf-8")
            git("add", "evidence.py")
            git("commit", "-qm", "original")
            frozen = git("rev-parse", "HEAD").decode()
            evidence.write_text("original line\\nforged line\\n", encoding="utf-8")
            git("add", "evidence.py")
            git("commit", "-qm", "replacement")
            replacement = git("rev-parse", "HEAD").decode()
            git("reset", "--hard", frozen)
            git("replace", frozen, replacement)
            git("read-tree", "--reset", "-u", "HEAD")
            self.assertEqual(
                bridge.exact_committed_source(repo, "evidence.py", frozen),
                b"original line\\n",
            )
            references = [{"trace": [{"file": "evidence.py", "line": 2}],
                           "evidence": []}]
            with self.assertRaisesRegex(bridge.HandoffError, "dirty|do not match requested commit|does not exist"):
                bridge.inspect_source_references(references, repo, bridge.current_head(repo))

    def test_checkout_switch_cannot_substitute_evidence_for_requested_sha(self):
        # An unrelated process changes HEAD after validation began but before
        # source evidence is read. The requested commit must remain the oracle.
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "checkout"
            repo.mkdir()
            def git(*args):
                return subprocess.run(
                    ["git", *args], cwd=repo, capture_output=True, check=True,
                ).stdout.strip()
            git("init", "-q")
            git("config", "user.name", "FAR race fixture")
            git("config", "user.email", "fixture@example.invalid")
            evidence = repo / "evidence.py"
            evidence.write_text("original line\n", encoding="utf-8")
            git("add", "evidence.py")
            git("commit", "-qm", "frozen evidence")
            frozen = git("rev-parse", "HEAD").decode()
            evidence.write_text("original line\nforged line\n", encoding="utf-8")
            git("add", "evidence.py")
            git("commit", "-qm", "later source")
            later = git("rev-parse", "HEAD").decode()
            git("checkout", "-q", frozen)

            self.meta["source_ref"] = frozen
            self.findings = [sample("rejected")]
            for kind in ("trace", "evidence"):
                self.findings[0][kind][0]["file"] = "evidence.py"
                self.findings[0][kind][0]["line"] = 2
            self.persist()
            original_validate = bridge.validate_with_pinned_cloudflare
            calls = [0]
            def switch_after_validation(*args, **kwargs):
                result = original_validate(*args, **kwargs)
                calls[0] += 1
                if calls[0] == 2:
                    git("checkout", "-q", later)
                return result
            with patch.object(bridge, "validate_with_pinned_cloudflare",
                              side_effect=switch_after_validation):
                with self.assertRaisesRegex(
                        bridge.HandoffError,
                        "do not match requested commit|source line does not exist|checkout changed"):
                    bridge.build_report(self.run_dir, frozen, source_root=repo)
            self.assertEqual(calls[0], 2)
            self.assertEqual(git("rev-parse", "HEAD").decode(), later)

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
