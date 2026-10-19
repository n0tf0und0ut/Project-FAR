"""A promotion must rebuild and independently replay its dependent Research views."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tools import check_living_promotion_head as integrity
from tools import reconcile_research_corpus as corpus
from tools import run_living_research_promotion as runner

ROOT = Path(__file__).resolve().parents[1]
STATE = "research/living/repository-state-v1.0.json"
PLANNED = "docs/research/promotion-corpus-probe.txt"


class PromotionCorpusRegressionTests(unittest.TestCase):
    def test_dependent_views_are_rebuilt_before_canonical_validation(self):
        with mock.patch.object(runner, "run") as run:
            runner.run_validations()
        commands = [call.args for call in run.call_args_list]
        living = commands.index((sys.executable, "tools/reconcile_living_repo.py"))
        rebuild = commands.index((sys.executable, "tools/reconcile_research_corpus.py", "--write"))
        verify = commands.index((sys.executable, "tools/reconcile_research_corpus.py"))
        health = commands.index((sys.executable, "tools/repo_health_check.py", "--fast"))
        self.assertLess(living, rebuild)
        self.assertLess(rebuild, verify)
        self.assertLess(verify, health)

    def test_generated_corpus_replays_and_rehashed_forgery_fails(self):
        def git(root, *args):
            return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

        def living_reconcile(root):
            # A deterministic living-state change from one planned payload.
            # Actual corpus validation/derivation below is deliberately not mocked.
            state = json.loads((root / STATE).read_text())
            state["promotion_regression_probe"] = (root / PLANNED).read_text()
            (root / STATE).write_text(json.dumps(state, sort_keys=True) + "\n")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repository"
            subprocess.run(["git", "clone", "--quiet", "--shared", str(ROOT), str(root)], check=True)
            git(root, "config", "user.name", "promotion-regression")
            git(root, "config", "user.email", "regression@example.invalid")
            base = git(root, "rev-parse", "HEAD")
            (root / PLANNED).write_text("authorized payload\n")
            living_reconcile(root)
            data = corpus.load_json(corpus.CORPUS, root)
            self.assertEqual(corpus.validate(data, root), [])
            expected = corpus.expected_outputs(data, root)
            for path, raw in expected.items():
                (root / path).write_bytes(raw)
            git(root, "add", "--", PLANNED, STATE, *map(str, expected))
            git(root, "commit", "-qm", "materialize derived views")
            head = git(root, "rev-parse", "HEAD")
            generated = {STATE, *map(str, expected)}
            with mock.patch("tools.reconcile_living_repo.reconcile", side_effect=living_reconcile):
                integrity._verify_generated_outputs(root, base, head, {PLANNED}, generated)
            for path in expected:
                # Even a newly committed/rehashed view cannot supply its own authority.
                (root / path).write_bytes(b"forged derived view\n")
                git(root, "add", "--", str(path))
                git(root, "commit", "-qm", "adversarial derived view")
                forged = git(root, "rev-parse", "HEAD")
                with mock.patch("tools.reconcile_living_repo.reconcile", side_effect=living_reconcile):
                    with self.assertRaisesRegex(integrity.IntegrityError, "not canonical reconciliation output"):
                        integrity._verify_generated_outputs(root, base, forged, {PLANNED}, generated)
                (root / path).write_bytes(expected[path])


if __name__ == "__main__":
    unittest.main()
