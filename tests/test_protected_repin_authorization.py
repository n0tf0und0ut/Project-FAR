"""Protected-artifact repins require authorization the candidate cannot write.

The assurance lock records the expected identity of every protected artifact.
Because the lock lives in the same tree as the artifacts, a change can edit a
protected file and refresh that file's own pin in one step. These tests fix the
governing rule: such a transition is permitted only when the *comparison base*
already authorizes that exact transition, so a candidate can never authorize
itself.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import unittest
from unittest import mock
from datetime import datetime, timedelta, timezone
from pathlib import Path

from far_validation import repin_signature, weakening


ROOT = Path(__file__).resolve().parents[1]
LOCK = weakening.ASSURANCE_LOCK_PATH
WAIVERS = weakening.WAIVER_PATH
WORKFLOW = ".github/workflows/validator-assurance.yml"
RENAMED_WORKFLOW = ".github/workflows/validator-assurance-v2.yml"
FORMAL = "formal/ValidationEngine.tla"
POLICY = "validation/runtime-policy.json"
VERIFIER = "research/target-category-discovery/verify_compositional_invariant_legacy.py"

REPIN_MESSAGE = "protected artifact"
UNAUTHORIZED = "may not authorize its own protected-artifact repin"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ProtectedRepinAuthorizationTests(unittest.TestCase):
    def setUp(self) -> None:
        # Synthetic signatures belong to this fixture repository, independent of the CI host.
        self.enterContext(mock.patch.dict(os.environ, {
            "GITHUB_REPOSITORY": "notfoundout/Project-FAR",
            "GITHUB_REPOSITORY_ID": "1283452680",
        }))
        self.tmp = self.enterContext(__import__("tempfile").TemporaryDirectory())
        self.repo = Path(self.tmp) / "repo"
        self.repo.mkdir()
        # The owner's repin signing key; its public half is pinned on the base, as on main.
        self.key = Path(self.tmp) / "owner"
        subprocess.run(["ssh-keygen", "-q", "-t", "ecdsa", "-b", "256", "-N", "", "-C", "", "-f", str(self.key)], check=True)
        kind, blob = self.key.with_suffix(".pub").read_text().split()[:2]
        self.signers = f'{repin_signature.PRINCIPAL} namespaces="{repin_signature.NAMESPACE}" {kind} {blob}\n'.encode()

    def _run(self, *args: str) -> None:
        subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True)

    def _write(self, rel: str, data: bytes) -> None:
        target = self.repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)

    def _build_base(self, files: dict[str, bytes], authorizations: list[dict] | None = None) -> str:
        """Commit a base containing the given protected files and their lock."""
        self._run("init", "-q")
        self._run("config", "user.email", "assurance@example.invalid")
        self._run("config", "user.name", "Validator Assurance")
        for rel, data in files.items():
            self._write(rel, data)
        self._write(
            LOCK,
            (json.dumps({"schema_version": "1.0", "files": {rel: sha256(data) for rel, data in files.items()}}, indent=2) + "\n").encode("utf-8"),
        )
        self._write(repin_signature.ALLOWED_SIGNERS_PATH, self.signers)
        self._write(
            WAIVERS,
            (json.dumps({"schema_version": "1.0", "waivers": [], "repin_authorizations": authorizations or []}, indent=2) + "\n").encode("utf-8"),
        )
        self._run("add", ".")
        self._run("commit", "-qm", "base")
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.repo, text=True).strip()

    def _repin(self, rel: str, data: bytes) -> None:
        """Edit a protected file and refresh its own lock entry, as an attacker would."""
        self._write(rel, data)
        lock_path = self.repo / LOCK
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        lock["files"][rel] = sha256(data)
        lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")

    def _commit(self, message: str = "candidate") -> None:
        self._run("add", "-A")
        self._run("commit", "-qm", message)

    def _repin_failures(self, base: str) -> dict[str, list[str]]:
        os.environ.pop("FAR_REPIN_TARGET_PR", None)
        report = weakening.detect_weakening(self.repo, base=base)
        return {
            finding.path: [item for item in finding.failures if REPIN_MESSAGE in item or "authorization" in item]
            for finding in report.findings
        }

    def _assert_rejected(self, base: str, rel: str) -> None:
        failures = self._repin_failures(base)
        self.assertIn(rel, failures, f"no finding recorded for {rel}")
        self.assertTrue(failures[rel], f"finding for {rel} carried no repin failure")

    def _assert_accepted(self, base: str, rel: str) -> None:
        failures = self._repin_failures(base)
        self.assertFalse(failures.get(rel), f"unexpected repin failure for {rel}: {failures.get(rel)}")

    # A. protected YAML + own lock refresh
    def test_protected_yaml_repin_is_rejected(self) -> None:
        base = self._build_base({WORKFLOW: b"name: assurance\njobs: {}\n"})
        self._repin(WORKFLOW, b"name: assurance\njobs: {weakened: true}\n")
        self._commit()
        self._assert_rejected(base, WORKFLOW)

    # B. the exact merge-authority fabricated-success attack
    def test_merge_authority_fabricated_success_attack_is_rejected(self) -> None:
        original = (ROOT / WORKFLOW).read_bytes()
        base = self._build_base({WORKFLOW: original})
        text = original.decode("utf-8")
        step = """      - name: Detect test and validator weakening
        run: >-
          python -I -X "pycache_prefix=$RUNNER_TEMP/far-pycache" validation_bootstrap/run_isolated.py weakening --base "${{ steps.base.outputs.sha }}" --json
          > artifacts/validation/runtime/test-weakening.json"""
        self.assertIn(step, text)
        fabricated = text.replace(
            step,
            """      - name: Detect test and validator weakening
        run: |
          echo '{"successful": true}' > artifacts/validation/runtime/test-weakening.json""",
            1,
        )
        self.assertNotIn("run_isolated.py weakening", fabricated)
        self._repin(WORKFLOW, fabricated.encode("utf-8"))
        self._commit("bypass weakening in merge-authority")
        self._assert_rejected(base, WORKFLOW)

    # C. protected JSON + own lock refresh
    def test_protected_json_repin_is_rejected(self) -> None:
        base = self._build_base({POLICY: b'{"network_policy": "deny"}\n'})
        self._repin(POLICY, b'{"network_policy": "allow"}\n')
        self._commit()
        self._assert_rejected(base, POLICY)

    # D. protected formal (non-Python) artifact + own lock refresh
    def test_protected_formal_artifact_repin_is_rejected(self) -> None:
        base = self._build_base({FORMAL: b"---- MODULE ValidationEngine ----\n====\n"})
        self._repin(FORMAL, b"---- MODULE ValidationEngine ----\n\\* weakened\n====\n")
        self._commit()
        self._assert_rejected(base, FORMAL)

    # E. verifier Python + own lock refresh
    def test_protected_python_verifier_repin_is_rejected(self) -> None:
        original = (ROOT / VERIFIER).read_bytes()
        base = self._build_base({VERIFIER: original})
        self._repin(VERIFIER, original + b"\nvalidate_gate = lambda *a, **k: None\n")
        self._commit()
        self._assert_rejected(base, VERIFIER)

    # F. candidate adds its own authorization
    def test_candidate_supplied_authorization_is_rejected(self) -> None:
        base = self._build_base({POLICY: b'{"network_policy": "deny"}\n'})
        weakened = b'{"network_policy": "allow"}\n'
        self._repin(POLICY, weakened)
        waivers = self.repo / WAIVERS
        payload = json.loads(waivers.read_text(encoding="utf-8"))
        payload["repin_authorizations"] = [
            {
                "id": "SELF-0001",
                "path": POLICY,
                "base_sha256": sha256(b'{"network_policy": "deny"}\n'),
                "authorized_sha256": sha256(weakened),
                "justification": "candidate attempting to authorize its own protected repin",
            }
        ]
        waivers.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        self._commit()
        self._assert_rejected(base, POLICY)

    # G. candidate rewrites an existing base authorization to cover itself
    def test_candidate_modified_authorization_is_rejected(self) -> None:
        other = b"---- MODULE ValidationEngine ----\n====\n"
        base = self._build_base(
            {POLICY: b'{"network_policy": "deny"}\n', FORMAL: other},
            authorizations=[
                {
                    "id": "BASE-0001",
                    "path": FORMAL,
                    "base_sha256": sha256(other),
                    "authorized_sha256": sha256(b"unrelated"),
                    "justification": "pre-existing authorization for an unrelated artifact",
                }
            ],
        )
        weakened = b'{"network_policy": "allow"}\n'
        self._repin(POLICY, weakened)
        waivers = self.repo / WAIVERS
        payload = json.loads(waivers.read_text(encoding="utf-8"))
        payload["repin_authorizations"][0].update(
            {
                "path": POLICY,
                "base_sha256": sha256(b'{"network_policy": "deny"}\n'),
                "authorized_sha256": sha256(weakened),
            }
        )
        waivers.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        self._commit()
        self._assert_rejected(base, POLICY)

    # H. base authorization naming a different path
    def test_base_authorization_for_wrong_path_is_rejected(self) -> None:
        original = b'{"network_policy": "deny"}\n'
        weakened = b'{"network_policy": "allow"}\n'
        base = self._build_base(
            {POLICY: original, FORMAL: b"---- MODULE V ----\n====\n"},
            authorizations=[
                {
                    "id": "BASE-0002",
                    "path": FORMAL,
                    "base_sha256": sha256(original),
                    "authorized_sha256": sha256(weakened),
                    "justification": "authorization bound to a different protected path",
                }
            ],
        )
        self._repin(POLICY, weakened)
        self._commit()
        self._assert_rejected(base, POLICY)

    # I. base authorization naming the wrong base digest
    def test_base_authorization_with_wrong_old_digest_is_rejected(self) -> None:
        original = b'{"network_policy": "deny"}\n'
        weakened = b'{"network_policy": "allow"}\n'
        base = self._build_base(
            {POLICY: original},
            authorizations=[
                {
                    "id": "BASE-0003",
                    "path": POLICY,
                    "base_sha256": sha256(b"some other prior content"),
                    "authorized_sha256": sha256(weakened),
                    "justification": "authorization bound to a base identity that does not apply",
                }
            ],
        )
        self._repin(POLICY, weakened)
        self._commit()
        self._assert_rejected(base, POLICY)

    # J. base authorization naming the wrong new digest
    def test_base_authorization_with_wrong_new_digest_is_rejected(self) -> None:
        original = b'{"network_policy": "deny"}\n'
        base = self._build_base(
            {POLICY: original},
            authorizations=[
                {
                    "id": "BASE-0004",
                    "path": POLICY,
                    "base_sha256": sha256(original),
                    "authorized_sha256": sha256(b'{"network_policy": "review"}\n'),
                    "justification": "authorization permits one specific replacement identity only",
                }
            ],
        )
        self._repin(POLICY, b'{"network_policy": "allow"}\n')
        self._commit()
        self._assert_rejected(base, POLICY)

    # K. exact base authorization for the exact transition
    def test_exact_base_authorization_is_accepted(self) -> None:
        original = b'{"network_policy": "deny"}\n'
        replacement = b'{"network_policy": "deny", "note": "reviewed"}\n'
        base = self._build_base(
            {POLICY: original},
            authorizations=[
                {
                    "id": "BASE-0005",
                    "path": POLICY,
                    "base_sha256": sha256(original),
                    "authorized_sha256": sha256(replacement),
                    "justification": "reviewed and merged authorization for this exact transition",
                }
            ],
        )
        self._repin(POLICY, replacement)
        self._commit("waiver-file authorization alone")
        self._assert_rejected(base, POLICY)  # repository bytes cannot authorize

        issued = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(hours=1)
        payload = repin_signature.canonical_bytes({
            "schema": repin_signature.SCHEMA, "domain": repin_signature.DOMAIN, "id": "0" * 31 + "5", "repository": "notfoundout/Project-FAR",
            "repository_id": 1283452680, "path": POLICY, "old_sha256": sha256(original), "new_sha256": sha256(replacement), "target_pr": 1,
            "base_sha": base, "reason": "reviewed owner-signed authorization for this exact transition",
            "issued_at": issued.strftime(repin_signature.TIME_FORMAT),
            "expires_at": (issued + timedelta(days=14)).strftime(repin_signature.TIME_FORMAT),
        })
        (self.repo.parent / "payload").write_bytes(payload)
        subprocess.run(["ssh-keygen", "-q", "-Y", "sign", "-f", str(self.key), "-n", repin_signature.NAMESPACE,
                        str(self.repo.parent / "payload")], check=True, capture_output=True)
        entry = {"payload": payload.decode(), "signature": (self.repo.parent / "payload.sig").read_text()}
        self._write(
            "validation/protected-repin-consumptions.json",
            (json.dumps({"schema_version": "2.0", "consumptions": [entry]}, indent=2) + "\n").encode("utf-8"),
        )
        self._commit("owner-signed authorization consumed")
        self._assert_accepted(base, POLICY)

    def _owner_authorize(self, base: str, rel: str, old: bytes, new: bytes, ident: str) -> None:
        """Append an owner-signed authorization for exactly ``rel`` ``old``->``new``."""
        issued = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(hours=1)
        payload = repin_signature.canonical_bytes({
            "schema": repin_signature.SCHEMA, "domain": repin_signature.DOMAIN, "id": ident, "repository": "notfoundout/Project-FAR",
            "repository_id": 1283452680, "path": rel, "old_sha256": sha256(old), "new_sha256": sha256(new), "target_pr": 1,
            "base_sha": base, "reason": "reviewed owner-signed authorization for this exact transition",
            "issued_at": issued.strftime(repin_signature.TIME_FORMAT),
            "expires_at": (issued + timedelta(days=14)).strftime(repin_signature.TIME_FORMAT),
        })
        (self.repo.parent / "payload").write_bytes(payload)
        (self.repo.parent / "payload.sig").unlink(missing_ok=True)
        subprocess.run(["ssh-keygen", "-q", "-Y", "sign", "-f", str(self.key), "-n", repin_signature.NAMESPACE,
                        str(self.repo.parent / "payload")], check=True, capture_output=True)
        entry = {"payload": payload.decode(), "signature": (self.repo.parent / "payload.sig").read_text()}
        self._write(
            "validation/protected-repin-consumptions.json",
            (json.dumps({"schema_version": "2.0", "consumptions": [entry]}, indent=2) + "\n").encode("utf-8"),
        )

    def _findings(self, base: str) -> tuple[weakening.WeakeningReport, dict[str, list[str]]]:
        os.environ.pop("FAR_REPIN_TARGET_PR", None)
        report = weakening.detect_weakening(self.repo, base=base)
        return report, {finding.path: finding.failures for finding in report.findings}

    GATE = "far_validation/example_gate.py"
    STRONG_GATE = b"def gate(x):\n    if x < 0:\n        raise ValueError('negative')\n    if x > 10:\n        raise ValueError('large')\n    return x\n"
    WEAK_GATE = b"def gate(x):\n    if x < 0:\n        raise ValueError('negative')\n    return x\n"

    # P. the owner's signature over exact bytes, not a base waiver, authorizes a protected
    # validator's structural change (a waiver would have to name its own merge commit as base).
    def test_owner_signed_protected_validator_change_needs_no_base_waiver(self) -> None:
        base = self._build_base({self.GATE: self.STRONG_GATE})
        self._repin(self.GATE, self.WEAK_GATE)
        self._commit("unsigned structural change")
        report, failures = self._findings(base)
        self.assertTrue(any("decision-branch count decreased" in item for item in failures[self.GATE]), failures)
        self.assertEqual(report.signed_transitions_used, [])

        self._owner_authorize(base, self.GATE, self.STRONG_GATE, self.WEAK_GATE, "0" * 31 + "6")
        self._commit("owner-signed authorization consumed")
        report, failures = self._findings(base)
        self.assertEqual(failures[self.GATE], [])
        self.assertEqual(report.signed_transitions_used, [self.GATE])
        self.assertTrue(report.successful)

    # Q. a signature over other bytes authorizes nothing, so the metric failure stands.
    def test_signature_for_other_bytes_does_not_excuse_a_structural_change(self) -> None:
        base = self._build_base({self.GATE: self.STRONG_GATE})
        self._repin(self.GATE, b"def gate(x):\n    return x\n")
        self._owner_authorize(base, self.GATE, self.STRONG_GATE, self.WEAK_GATE, "0" * 31 + "7")
        self._commit()
        report, failures = self._findings(base)
        self.assertTrue(any("decision-branch count decreased" in item for item in failures[self.GATE]), failures)
        self.assertTrue(any(UNAUTHORIZED in item for item in failures[self.GATE]), failures)
        self.assertEqual(report.signed_transitions_used, [])

    # R. a signed transition covers only its own path; an unprotected validator is unaffected.
    def test_signed_transition_does_not_excuse_another_validator(self) -> None:
        unprotected = "far_validation/other_gate.py"
        self._build_base({self.GATE: self.STRONG_GATE})
        self._write(unprotected, self.STRONG_GATE)
        self._commit("unprotected validator")
        base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.repo, text=True).strip()
        self._repin(self.GATE, self.WEAK_GATE)
        self._write(unprotected, self.WEAK_GATE)
        self._owner_authorize(base, self.GATE, self.STRONG_GATE, self.WEAK_GATE, "0" * 31 + "8")
        self._commit()
        report, failures = self._findings(base)
        self.assertEqual(failures[self.GATE], [])
        self.assertTrue(any("decision-branch count decreased" in item for item in failures[unprotected]), failures)
        self.assertEqual(report.signed_transitions_used, [self.GATE])

    # L. locked artifact left untouched
    def test_unchanged_locked_artifact_is_accepted(self) -> None:
        base = self._build_base({POLICY: b'{"network_policy": "deny"}\n', FORMAL: b"---- MODULE V ----\n====\n"})
        self._write("docs/unrelated-note.md", b"unrelated change\n")
        self._commit()
        self._assert_accepted(base, POLICY)
        self._assert_accepted(base, FORMAL)

    def _fabricate_workflow(self, original: bytes) -> bytes:
        """Rewrite the real workflow so the weakening gate reports success without running."""
        text = original.decode("utf-8")
        step = """      - name: Detect test and validator weakening
        run: >-
          python -I -X "pycache_prefix=$RUNNER_TEMP/far-pycache" validation_bootstrap/run_isolated.py weakening --base "${{ steps.base.outputs.sha }}" --json
          > artifacts/validation/runtime/test-weakening.json"""
        self.assertIn(step, text)
        fabricated = text.replace(
            step,
            """      - name: Detect test and validator weakening
        run: |
          echo '{"successful": true}' > artifacts/validation/runtime/test-weakening.json""",
            1,
        )
        self.assertNotIn("run_isolated.py weakening", fabricated)
        return fabricated.encode("utf-8")

    def _relocate_lock_entry(self, old: str, new: str, data: bytes) -> None:
        """Move a protected artifact's lock entry to a new path, as the rename attack does."""
        lock_path = self.repo / LOCK
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        lock["files"].pop(old, None)
        lock["files"][new] = sha256(data)
        workflow = lock.get("workflow")
        if isinstance(workflow, dict):
            workflow["path"] = new
            workflow["required_fragments"] = [
                fragment
                for fragment in workflow.get("required_fragments", [])
                if "run_isolated.py weakening" not in fragment
            ]
        lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")

    def _build_workflow_base(self, original: bytes) -> str:
        base = self._build_base({WORKFLOW: original})
        lock_path = self.repo / LOCK
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        lock["workflow"] = {
            "path": WORKFLOW,
            "required_fragments": ["validation_bootstrap/run_isolated.py weakening"],
        }
        lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
        self._run("add", "-A")
        self._run("commit", "-qm", "base workflow contract")
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.repo, text=True).strip()

    # N. renaming a protected artifact must not hide its base identity.
    # Git reports only a rename's destination, so the base-protected source path
    # would never be evaluated. High similarity is preserved deliberately: git
    # classifies this as R09x, which is exactly the case that used to evade the
    # check, so this test fails if rename detection is ever re-enabled.
    def test_high_similarity_rename_of_protected_workflow_is_rejected(self) -> None:
        original = (ROOT / WORKFLOW).read_bytes()
        base = self._build_workflow_base(original)
        fabricated = self._fabricate_workflow(original)

        self._run("mv", WORKFLOW, RENAMED_WORKFLOW)
        (self.repo / RENAMED_WORKFLOW).write_bytes(fabricated)
        self._relocate_lock_entry(WORKFLOW, RENAMED_WORKFLOW, fabricated)
        self._commit("rename workflow and fabricate weakening success")

        status = subprocess.check_output(
            ["git", "diff", "--name-status", f"{base}...HEAD"], cwd=self.repo, text=True
        )
        self.assertRegex(status, r"R0?9\d\s", f"expected a high-similarity rename, got:\n{status}")
        self._assert_rejected(base, WORKFLOW)

    # O. the same attack expressed as delete + add must be rejected identically,
    # so protection never depends on git's rename-similarity heuristic.
    def test_delete_plus_add_of_protected_workflow_is_rejected(self) -> None:
        original = (ROOT / WORKFLOW).read_bytes()
        base = self._build_workflow_base(original)
        fabricated = self._fabricate_workflow(original)

        self._run("rm", "-q", WORKFLOW)
        target = self.repo / RENAMED_WORKFLOW
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(fabricated)
        self._relocate_lock_entry(WORKFLOW, RENAMED_WORKFLOW, fabricated)
        self._commit("delete and re-add workflow with fabricated weakening success")

        self._assert_rejected(base, WORKFLOW)

    # M. a path introduced by the candidate is not a base-protected artifact
    def test_new_candidate_path_is_not_treated_as_protected(self) -> None:
        base = self._build_base({POLICY: b'{"network_policy": "deny"}\n'})
        introduced = "research/target-category-discovery/newly-added-artifact.json"
        self._write(introduced, b'{"introduced": true}\n')
        lock_path = self.repo / LOCK
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        lock["files"][introduced] = sha256(b'{"introduced": true}\n')
        lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
        self._commit()
        self._assert_accepted(base, introduced)


if __name__ == "__main__":
    unittest.main()
