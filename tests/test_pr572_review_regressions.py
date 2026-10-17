from __future__ import annotations

import fnmatch
import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from tests import test_living_research as living_fixtures
from tools import reconcile_research_corpus as corpus
from tools import run_living_research as living
from tools import validate_research_carry as carry


def _receipt(raw: bytes, origin: str = "test") -> dict:
    return {
        "format_version": "far-frozen-input/1.1",
        "sha256": corpus.digest(raw),
        "size": len(raw),
        "origin": origin,
        "authority": "discovery_lead",
        "executable": False,
        "primary_evidence_verified": False,
        "review_status": "DISCOVERY_LEAD",
        "review_bridge": "research/corpus/reviewed-inputs-v1.0.json",
    }


def _review_observation(oid: str) -> dict:
    return {
        "id": oid,
        "proposition_id": f"FND-{oid}",
        "epistemic_class": "EVIDENCE",
        "statement": f"bounded statement {oid}",
        "scope": "bounded test scope",
        "scope_key": "source_bounded",
        "relation": "SUPPORTS",
        "relation_targets": [],
        "target_kind": "NONE",
        "replacement_effect": "NONE",
        "uncertainty": "test uncertainty remains",
        "mechanism_ids": [],
        "dependencies": [],
        "history": [],
    }


class PR572ReviewRegressionTests(unittest.TestCase):
    def test_external_accounting_rejects_orphan_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            external = root / "research/corpus/external"
            external.mkdir(parents=True)
            raw = b"receipt without blob"
            identity = corpus.digest(raw)
            (external / f"{identity}.json").write_bytes(corpus.canonical(_receipt(raw)))
            with self.assertRaisesRegex(ValueError, "receipt/blob pairing mismatch"):
                corpus.living_leads(root)

    def test_external_accounting_rejects_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            external = root / "research/corpus/external"
            external.mkdir(parents=True)
            stem = "a" * 64
            (external / f"{stem}.bin").write_bytes(b"actual bytes")
            bad = _receipt(b"different bytes")
            bad["size"] = len(b"actual bytes")
            (external / f"{stem}.json").write_bytes(corpus.canonical(bad))
            with self.assertRaisesRegex(ValueError, "frozen-byte receipt mismatch"):
                corpus.living_leads(root)

    def test_external_accounting_rejects_duplicate_or_ambiguous_pair(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            external = root / "research/corpus/external"
            external.mkdir(parents=True)
            raw = b"same frozen bytes"
            identity = corpus.digest(raw)
            receipt = corpus.canonical(_receipt(raw))
            (external / f"{identity}.bin").write_bytes(raw)
            (external / f"{identity}.json").write_bytes(receipt)
            alias = "f" * 64
            if alias == identity:
                alias = "e" * 64
            (external / f"{alias}.bin").write_bytes(raw)
            (external / f"{alias}.json").write_bytes(receipt)
            with self.assertRaisesRegex(ValueError, "duplicate external frozen-byte identity"):
                corpus.living_leads(root)

    def test_external_accounting_rejects_noncanonical_pair_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            external = root / "research/corpus/external"
            external.mkdir(parents=True)
            raw = b"valid bytes under wrong stem"
            identity = corpus.digest(raw)
            wrong = "0" * 64 if identity != "0" * 64 else "1" * 64
            (external / f"{wrong}.bin").write_bytes(raw)
            (external / f"{wrong}.json").write_bytes(corpus.canonical(_receipt(raw)))
            with self.assertRaisesRegex(ValueError, "receipt/blob identity mismatch"):
                corpus.living_leads(root)

    def test_reviewed_bridge_accepts_hash_bound_bin_and_pdf(self):
        data = corpus.load_json(corpus.CORPUS)
        for suffix in (".bin", ".pdf"):
            with self.subTest(suffix=suffix), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "candidate.json").write_text("{}\n", encoding="utf-8")
                primary = root / f"primary{suffix}"
                primary.write_bytes(b"%PDF-1.7 exact frozen primary evidence\x00")
                (root / "review.md").write_text("verified\n", encoding="utf-8")
                entry = {
                    "id": f"INPUT-{suffix[1:].upper()}",
                    "candidate": {
                        "path": "candidate.json",
                        "sha256": corpus.digest((root / "candidate.json").read_bytes()),
                    },
                    "primary_evidence": {
                        "path": primary.name,
                        "sha256": corpus.digest(primary.read_bytes()),
                        "external_identifier": f"frozen:test:{suffix[1:]}",
                        "version": "v1",
                        "independently_verified": True,
                    },
                    "review": {
                        "path": "review.md",
                        "sha256": corpus.digest((root / "review.md").read_bytes()),
                        "status": "VERIFIED_FOR_CORPUS",
                    },
                    "evidence_class": "external_primary",
                    "scope": "bounded",
                    "observations": [_review_observation(f"OBS-REVIEWED-{suffix[1:].upper()}")],
                }
                registry = {
                    "format_version": "far-reviewed-inputs/1.0",
                    "authority": "Research",
                    "entries": [entry],
                    "promotion_authority": False,
                }
                target = root / corpus.REVIEWED_INPUTS
                target.parent.mkdir(parents=True)
                target.write_text(json.dumps(registry), encoding="utf-8")
                sources, errors = corpus.reviewed_sources(data, root)
                self.assertEqual(errors, [])
                self.assertEqual(sources[0]["path"], primary.name)
                self.assertTrue(sources[0]["evidence_usable"])

    def test_carried_git_symlink_and_executable_blob_fail_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.name", "test"], check=True)
            state = root / "research/living/state-v1.0.json"
            state.parent.mkdir(parents=True)
            state.write_text("{}\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "regular"], check=True)
            carry.validate_ref_paths(root, "HEAD", ["research/living/state-v1.0.json"])

            state.unlink()
            state.symlink_to("../../README.md")
            subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "symlink"], check=True)
            with self.assertRaisesRegex(ValueError, "forbidden carried git object"):
                carry.validate_ref_paths(root, "HEAD", ["research/living/state-v1.0.json"])

            state.unlink()
            state.write_text("{}\n", encoding="utf-8")
            os.chmod(state, 0o755)
            subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "executable"], check=True)
            with self.assertRaisesRegex(ValueError, "forbidden carried git object"):
                carry.validate_ref_paths(root, "HEAD", ["research/living/state-v1.0.json"])

    def test_living_workflow_rebuilds_before_tests_and_validates_before_checkout(self):
        workflow = (corpus.ROOT / ".github/workflows/living-research.yml").read_text(encoding="utf-8")
        prepare = workflow.split("- name: Prepare persistent research inbox branch", 1)[1].split("- name: Preflight tests and authority checks", 1)[0]
        preflight = workflow.split("- name: Preflight tests and authority checks", 1)[1].split("- name: Discover current and historical research", 1)[0]
        self.assertIn("python tools/validate_research_carry.py", prepare)
        self.assertLess(prepare.index("python tools/validate_research_carry.py"), prepare.index('git checkout "origin/$branch" -- "$path"'))
        self.assertNotIn("corpus-reconciliation-v1.0.json", prepare)
        self.assertNotIn("repository-state-v1.0.json", prepare)
        self.assertLess(preflight.index("python tools/reconcile_living_repo.py"), preflight.index("python -m unittest"))
        self.assertLess(preflight.index("python tools/reconcile_research_corpus.py --living-loop --write"), preflight.index("python -m unittest"))

    def test_living_workflow_paths_cover_declared_corpus_inputs(self):
        workflow = (corpus.ROOT / ".github/workflows/living-research.yml").read_text(encoding="utf-8")
        trigger = workflow.split("  pull_request:", 1)[1].split("\nconcurrency:", 1)[0]
        patterns = [line.strip()[2:].strip("'") for line in trigger.splitlines() if line.strip().startswith("- '")]
        data = corpus.load_json(corpus.CORPUS)
        material_paths = {
            corpus.CORPUS.as_posix(), corpus.REVIEWED_INPUTS.as_posix(),
            corpus.SCHEMA.as_posix(), corpus.REVIEW_SCHEMA.as_posix(),
            *[source["path"] for source in data["sources"] if source.get("path")],
            *[item["path"] for item in data.get("dynamic_dependencies", [])],
        }
        material_paths.update({"tools/validate_research_carry.py", "tests/test_pr572_review_regressions.py"})
        uncovered = sorted(path for path in material_paths if not any(fnmatch.fnmatch(path, pattern) for pattern in patterns))
        self.assertEqual(uncovered, [])

    def test_repeated_living_runs_reuse_carried_state_without_duplicate_candidates(self):
        repo = living_fixtures.TempRepo()
        try:
            first = living.run(
                repo.root,
                now=datetime(2026, 9, 8, 12, 0, tzinfo=timezone.utc),
                crossref_transport=lambda *args: living_fixtures.crossref_payload(),
                openalex_transport=lambda *args: living_fixtures.openalex_payload(),
                openlibrary_transport=lambda *args: living_fixtures.openlibrary_payload(),
                sleep_fn=lambda _: None,
            )
            first_ids = {path.name for path in (repo.root / living.CANDIDATE_DIR).glob("*.json")}
            second = living.run(
                repo.root,
                now=datetime(2026, 9, 8, 12, 30, tzinfo=timezone.utc),
                crossref_transport=lambda *args: living_fixtures.crossref_payload(),
                openalex_transport=lambda *args: living_fixtures.openalex_payload(),
                openlibrary_transport=lambda *args: living_fixtures.openlibrary_payload(),
                sleep_fn=lambda _: None,
            )
            second_ids = {path.name for path in (repo.root / living.CANDIDATE_DIR).glob("*.json")}
            state = living.read_json(repo.root / living.STATE_PATH)
            self.assertEqual(first["status"], "SUCCESS")
            self.assertEqual(second["status"], "SUCCESS")
            self.assertEqual(state["run_count"], 2)
            self.assertEqual(first_ids, second_ids)
        finally:
            repo.close()


if __name__ == "__main__":
    unittest.main()
