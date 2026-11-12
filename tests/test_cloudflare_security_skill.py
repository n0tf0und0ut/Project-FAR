"""Tests for Cloudflare skill integrity and read-only CI integration."""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml
from tools import check_cloudflare_security_skill as lock

ROOT = Path(__file__).resolve().parents[1]


class CloudflareSecuritySkillTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(lock.LOCK.read_text(encoding="utf-8"))

    def test_exact_upstream_snapshot_is_preserved(self):
        self.assertEqual(lock.verify(self.manifest), [])

    def test_manifest_bytes_are_also_pinned_not_just_self_reported(self):
        original = lock.LOCK.read_bytes()
        self.assertEqual(lock.verify_manifest_bytes(original), [])
        changed = original + b"\n"
        self.assertIn("modified source-lock manifest (requires separately reviewed re-pin)",
                      lock.verify_manifest_bytes(changed))

    def test_modification_and_missing_file_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "skill"
            shutil.copytree(lock.SKILL_DIR, target)
            original = target / "SKILL.md"
            original.write_bytes(original.read_bytes() + b"\n")
            (target / "validate-findings.cjs").unlink()
            errors = lock.verify(self.manifest, target)
            self.assertIn("modified vendor file: SKILL.md", errors)
            self.assertIn("missing vendor file: validate-findings.cjs", errors)

    def test_unlisted_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "skill"
            shutil.copytree(lock.SKILL_DIR, target)
            (target / "extra.md").write_text("unlisted", encoding="utf-8")
            self.assertIn("unlisted vendor file: extra.md",
                          lock.verify(self.manifest, target))

    def test_tampered_upstream_identity_and_traversal_fail_closed(self):
        for key, value in (
            ("upstream_commit", "0" * 40),
            ("upstream_repository", "attacker/repo"),
            ("installed_skill_path", "../../elsewhere"),
        ):
            changed = copy.deepcopy(self.manifest)
            changed[key] = value
            self.assertNotEqual(lock.verify(changed), [], key)
        changed = copy.deepcopy(self.manifest)
        changed["files"][0]["path"] = lock.BASE + "/../escape"
        self.assertTrue(any("invalid file name" in e
                            for e in lock.verify(changed)))

    def test_claude_adapter_keeps_single_canonical_copy(self):
        path = ROOT / ".claude/skills/security-audit/SKILL.md"
        content = path.read_text(encoding="utf-8")
        self.assertIn("name: security-audit", content)
        self.assertIn(".agents/skills/security-audit/SKILL.md", content)
        self.assertIn("CLAUDE.md", content)

    def test_ci_never_grants_write_token_or_auto_merges(self):
        doc = yaml.safe_load(
            (ROOT / ".github/workflows/cloudflare-security-audit-skill.yml")
            .read_text(encoding="utf-8")
        )
        events = doc.get("on", doc.get(True, {}))
        self.assertIn("pull_request", events)
        self.assertNotIn("pull_request_target", events)
        self.assertEqual(doc["permissions"], {"contents": "read"})
        for job in doc["jobs"].values():
            self.assertEqual(job["permissions"], {"contents": "read"})
            self.assertNotIn("if", job)
            for step in job["steps"]:
                self.assertNotIn("secrets.", str(step))
                if "uses" in step:
                    self.assertRegex(
                        step["uses"],
                        r"^[A-Za-z0-9_./-]+@[a-f0-9]{40}$",
                    )


if __name__ == "__main__":
    unittest.main()
