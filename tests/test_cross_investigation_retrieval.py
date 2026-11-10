"""Regression and adversarial checks for the frozen retrieval diagnostic."""
from __future__ import annotations

import copy
import json
import runpy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "research" / "knowledge-retrieval-001"
API = runpy.run_path(str(DIR / "run_baseline.py"))


class CrossInvestigationRetrievalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = API["load_fixture"](DIR / "frozen-v0.1.json")

    def test_frozen_gold_and_source_bindings(self):
        self.assertEqual(len(self.fixture["cases"]), 14)
        self.assertEqual(len(self.fixture["records"]), 44)
        self.assertEqual(len(self.fixture["sources"]), 22)
        API["verify_source_bytes"](
            self.fixture, ROOT / "research" / "corpus" / "synthesis-v1.0.json"
        )
        API["verify_corpus_bytes"](
            self.fixture, ROOT / "research" / "corpus" / "corpus-v1.0.json"
        )

    def test_results_are_deterministic(self):
        first = API["evaluate"](self.fixture, 5)
        second = API["evaluate"](self.fixture, 5)
        self.assertEqual(first, second)
        self.assertEqual(first["positive_cases"], 13)
        self.assertEqual(first["negative_controls"], 1)

    def test_zero_overlap_abstains(self):
        documents = [{"id": "A", "kind": "observation", "text": "contract factorization",
                      "active": True}]
        self.assertEqual(API["ranking"](documents, "banana spaceship moon", 5), [])

    def test_inactive_and_unverified_records_are_excluded(self):
        sources = {"S": {"evidence_usable": False, "primary_evidence_verified": False}}
        good = {"id": "A", "kind": "observation", "source_id": "S", "active": True}
        self.assertFalse(API["admissible"](good, sources))
        self.assertFalse(API["admissible"]({**good, "active": False}, sources))

    def test_inactive_gold_fails_closed(self):
        modified = copy.deepcopy(self.fixture)
        modified["cases"][0]["gold_ids"] = [
            "OBS-SCHEDULED-TASK-HISTORY-HISTORY-MISSING"
        ]
        with tempfile.TemporaryDirectory() as path:
            file = Path(path) / "mutant.json"
            import json
            file.write_text(json.dumps(modified), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing/inactive gold"):
                API["load_fixture"](file)

    def test_mutated_synthesis_refused(self):
        with tempfile.TemporaryDirectory() as path:
            mutant = Path(path) / "synthesis.json"
            original = ROOT / "research" / "corpus" / "synthesis-v1.0.json"
            mutant.write_bytes(original.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "pinned synthesis Git blob"):
                API["verify_source_bytes"](self.fixture, mutant)

    def test_mutated_corpus_refused(self):
        with tempfile.TemporaryDirectory() as path:
            mutant = Path(path) / "corpus.json"
            original = ROOT / "research" / "corpus" / "corpus-v1.0.json"
            mutant.write_bytes(original.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "pinned Git blob"):
                API["verify_corpus_bytes"](self.fixture, mutant)

    def test_duplicate_gold_refused(self):
        modified = copy.deepcopy(self.fixture)
        modified["cases"][0]["gold_ids"] *= 2
        with tempfile.TemporaryDirectory() as path:
            file = Path(path) / "mutant.json"
            import json
            file.write_text(json.dumps(modified), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate gold id"):
                API["load_fixture"](file)

    def test_empty_index_rejected_k(self):
        with self.assertRaisesRegex(ValueError, "k must be positive"):
            API["ranking"]([], "test", k=0)

    def test_python_ranking_matches_frozen_crosscheck(self):
        reference = json.loads(
            (DIR / "results-js-crosscheck-v0.1.json").read_text(encoding="utf-8")
        )
        actual = API["evaluate"](self.fixture, k=5)
        self.assertEqual(actual["documents_indexed"], reference["document_count"])
        self.assertAlmostEqual(actual["macro_recall_at_k"], reference["macro_recall_at_5"])
        self.assertAlmostEqual(actual["mrr_at_k"], reference["mrr_at_5"])
        self.assertEqual(
            actual["unanswerable_abstention_rate"], reference["abstain_accuracy"]
        )
        for observed, expected in zip(actual["case_results"], reference["results"], strict=True):
            self.assertEqual(observed["id"], expected["id"])
            self.assertEqual(
                [record["id"] for record in observed["retrieved"]],
                [record["id"] for record in expected["retrieved"]],
            )

    def test_cli_replays_pinned_baseline(self):
        process = subprocess.run(
            [sys.executable, str(DIR / "run_baseline.py"),
             "--verify-source", str(ROOT / "research/corpus/synthesis-v1.0.json"),
             "--verify-corpus", str(ROOT / "research/corpus/corpus-v1.0.json")],
            capture_output=True, text=True, check=True, timeout=30,
        )
        result = json.loads(process.stdout)
        self.assertEqual(result["cases"], 14)
        self.assertEqual(result["documents_indexed"], 43)
        self.assertAlmostEqual(result["macro_recall_at_k"], 1.0)
        self.assertAlmostEqual(result["mrr_at_k"], 25 / 26)
        self.assertEqual(result["unanswerable_abstention_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
