"""Read-only provenance and negative-control checks for PR #662 research evidence.

The study is internal Research, not proof of software reliability or a production
tool integration. These tests validate archived observations, not model quality.
"""
from __future__ import annotations

import copy
import gzip
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "research/comparisons/ripgrep-graphify-retrieval-2026-11-12"
ORIGINAL_SOURCE_SHA = "8c6dc6cf840a0d82fb4dcde114c1af471b3f74fe"
FROZEN_HASHES = {
    "protocol.json": "f6ca19d8f772d1e487579ea7ef460de41bf24e4392161334b0e968e766960564",
    "oracle.json": "a23c05325d326c0c9f5a79ae26e776c84f63a89b3e292c51ca959a4c0300bd30",
    "mandatory_gate_protocol.json": "64b58b30c274867d36844350de2836f6b382ed09a71471370eae8162129ec43c",
    "mandatory_gate_oracle.json": "abb4f420e829748de5c3932e7dfc277a4067c561d0ceca88ef26921459856fdc",
    "graphify_initial_extraction.json": "c3421e09ae1faa8f5482f728086f5c563a0080557bc178e6bbf7e117b7a387bb",
    "graphify_repeat_extraction.json": "b5f8e8175d62fb770641dcdf3e8260d0941e8d539368fc1ebd21ef96299b2da9",
}
COMPRESSED_SHA256 = "310de9914bdfc140f972920db2e25c1288c225121200f160de5765863043265a"
DECOMPRESSED_SHA256 = "be8903fab02fc4ba94c41f51491331575c9f7e0ca279cc88f9ecbd4daad3d519"


def _sha256(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _json(name: str) -> dict:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def _receipts(compressed: bytes) -> list[dict]:
    if _sha256(compressed) != COMPRESSED_SHA256:
        raise ValueError("compressed model receipt hash mismatch")
    try:
        raw = gzip.decompress(compressed)
    except (gzip.BadGzipFile, EOFError, OSError) as exc:
        raise ValueError("invalid receipt archive") from exc
    if _sha256(raw) != DECOMPRESSED_SHA256:
        raise ValueError("decompressed model receipt hash mismatch")
    items = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    if len(items) != 72 or len({(r["task_id"], r["arm"]) for r in items}) != 72:
        raise ValueError("missing, duplicated, or extra task/arm receipts")
    return items


def _mandatory_qualified(analysis: dict) -> bool:
    gates = analysis.get("gate_passes")
    return (
        isinstance(gates, dict)
        and bool(gates)
        and all(value is True for value in gates.values())
        and analysis.get("verdict") == "ELIGIBLE_FOR_FURTHER_GOVERNED_ACCEPTANCE"
    )


class GraphifyResearchEvidenceTests(unittest.TestCase):
    def test_frozen_protocol_and_source_provenance(self):
        for name, expected in FROZEN_HASHES.items():
            with self.subTest(name=name):
                self.assertEqual(_sha256((EVIDENCE / name).read_bytes()), expected)
        first = _json("protocol.json")
        second = _json("mandatory_gate_protocol.json")
        original = {item["function"] for item in first["tasks"]}
        prospect = {item["function"] for item in second["tasks"]}
        self.assertEqual(len(original), 12)
        self.assertEqual(len(prospect), 24)
        self.assertFalse(original & prospect)
        self.assertEqual(first["commit"], ORIGINAL_SOURCE_SHA)
        self.assertEqual(second["source_sha"], ORIGINAL_SOURCE_SHA)
        self.assertEqual(set(_json("mandatory_gate_oracle.json")), prospect)
        for name in ("graphify_initial_extraction.json", "graphify_repeat_extraction.json"):
            self.assertFalse((EVIDENCE / name).read_bytes().endswith(b"\n"),
                             "original frozen bytes must not be silently normalized")

    def test_reject_modified_model_receipt(self):
        blob = (EVIDENCE / "mandatory_gate_raw.jsonl.gz").read_bytes()
        self.assertEqual(len(_receipts(blob)), 72)
        altered = bytearray(blob)
        altered[len(altered) // 2] ^= 1
        with self.assertRaises(ValueError):
            _receipts(bytes(altered))
        with self.assertRaises(ValueError):
            _receipts(blob[:-1])

    def test_reject_unearned_mandatory_gate(self):
        analysis = _json("mandatory_gate_analysis.json")
        self.assertFalse(_mandatory_qualified(analysis))
        self.assertEqual(analysis["verdict"].split(":")[0], "NO")
        fabricated = copy.deepcopy(analysis)
        fabricated["gate_passes"] = {key: True for key in analysis["gate_passes"]}
        self.assertFalse(_mandatory_qualified(fabricated),
                         "claim requires a recorded qualified verdict, not changed booleans")
        fabricated["verdict"] = "ELIGIBLE_FOR_FURTHER_GOVERNED_ACCEPTANCE"
        fabricated["gate_passes"]["all_14_specialists_live_integration_verified"] = False
        self.assertFalse(_mandatory_qualified(fabricated),
                         "missing deployment evidence cannot satisfy a mandatory hook gate")

    def test_scored_72_run_end_to_end_replay(self):
        """Recompute observable per-task decisions independently of the archived scorer."""
        runs = _receipts((EVIDENCE / "mandatory_gate_raw.jsonl.gz").read_bytes())
        gold = _json("mandatory_gate_oracle.json")
        analysis = _json("mandatory_gate_analysis.json")
        self.assertEqual(analysis["model_run_count"], 72)
        expected = analysis["metrics"]
        by_arm = {}
        for arm in ("rg_only", "optional_graph", "mandatory_graph_hook"):
            selected = [row for row in runs if row["arm"] == arm]
            self.assertEqual(len(selected), 24)
            tp = fp = fn = exact = tokens = calls = 0
            for row in selected:
                self.assertEqual(row["source_sha"], ORIGINAL_SOURCE_SHA)
                self.assertIsNone(row["error"])
                truth = set(gold[row["function"]])
                predicted = set(row["selected_files"])
                self.assertEqual(len(predicted), len(row["selected_files"]))
                tp += len(predicted & truth)
                fp += len(predicted - truth)
                fn += len(truth - predicted)
                tokens += row["model_total_tokens"]
                calls += len(row["model_calls"])
                patch = row["patch_result"]
                if (
                    row["final_action"] == "apply_patch"
                    and row["invalid_action"] is None
                    and patch is not None
                    and patch["syntax_valid"]
                    and predicted == truth
                    and row["definition_file"] in patch["edit_files"]
                ):
                    exact += 1
            self.assertEqual(
                (tp, fp, fn, exact, tokens, calls),
                (expected[arm]["tp"], expected[arm]["fp"], expected[arm]["fn"],
                 expected[arm]["exact"], expected[arm]["total_model_tokens"],
                 expected[arm]["model_calls"]),
            )
            by_arm[arm] = (exact, tokens)
        self.assertEqual(by_arm, {
            "rg_only": (9, 14885),
            "optional_graph": (10, 17876),
            "mandatory_graph_hook": (10, 18408),
        })

    def test_installer_side_effects_and_coverage_scope(self):
        installed = _json("mandatory_hook_install_smoke.json")
        removal = _json("mandatory_hook_uninstall_smoke.json")
        coverage = _json("mandatory_gate_coverage.json")
        self.assertTrue(installed["new_policy_requires_graph_before_grep"])
        self.assertTrue(installed["test_assertions_passed"])
        self.assertTrue(removal["policy_byte_identical"])
        self.assertTrue(removal["merge_driver_removed"])
        self.assertEqual(len(installed["git_hooks"]), 4)
        self.assertEqual(coverage["by_extension"][".lean"]["covered_as_graph_node_source_paths"], 0)
        self.assertEqual(coverage["by_extension"][".md"]["covered_as_graph_node_source_paths"], 0)


if __name__ == "__main__":
    unittest.main()
