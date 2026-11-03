"""Regression for the observed cross-runner Python patch-version cache miss."""
from pathlib import Path
import json
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

from far_validation.assured_engine import ValidationEngine
from far_validation.trust import HMACTrust

ROOT = Path(__file__).resolve().parents[1]


class SignedCacheRuntimeBindingTests(unittest.TestCase):
    def test_cache_jobs_select_one_exact_python_patch_release(self):
        text = (ROOT / ".github/workflows/validator-assurance.yml").read_text()
        versions = []
        for name in ("signed-cache-producer", "signed-cache-consumer", "merge-authority"):
            match = re.search(r"^  " + name + r":\n(.*?)(?=^  [a-z]|\Z)", text, re.M | re.S)
            self.assertIsNotNone(match, name)
            version = re.search(r"python-version: '([^']+)'", match.group(1)).group(1)
            self.assertRegex(version, r"^\d+\.\d+\.\d+$")
            versions.append(version)
        self.assertEqual(len(set(versions)), 1)

    def test_patch_mismatch_invalidates_signed_cache_and_same_patch_reuses_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "validation").mkdir()
            (root / "check.py").write_text("print('ok')\n")
            manifest = {
                "schema_version": "1.0", "profiles": {"pr-fast": ["x"]},
                "protected_checks": [], "global_invalidation_paths": [],
                "checks": [{"id": "x", "title": "x",
                            "command": [sys.executable, "check.py"],
                            "profiles": ["pr-fast"], "inputs": ["check.py"]}],
            }
            (root / "validation/manifest.json").write_text(json.dumps(manifest))
            trust = HMACTrust(key=b"test-only", trust_domain="test", key_id="test")
            outcomes = []
            for version in ("3.12.15", "3.12.16", "3.12.16"):
                with patch("far_validation.engine.platform.python_version", return_value=version):
                    result = ValidationEngine(root, jobs=1, trust=trust,
                                              require_signed_cache=True).run(profile="pr-fast")
                self.assertTrue(result.successful)
                outcomes.append(result.results[0])
            self.assertFalse(outcomes[0].cache_hit)
            self.assertFalse(outcomes[1].cache_hit)
            self.assertNotEqual(outcomes[0].cache_key, outcomes[1].cache_key)
            self.assertTrue(outcomes[2].cache_hit)
            self.assertTrue(outcomes[2].cache_signature_verified)


if __name__ == "__main__":
    unittest.main()
