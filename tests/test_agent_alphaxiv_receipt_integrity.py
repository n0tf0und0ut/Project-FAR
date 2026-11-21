"""Verify the externally executed, candidate-only study index against its hashes.

This is *not* an independent adjudication of scientific claims. The input
metadata digest was observed in GitHub Actions and cannot by itself prove that
the upstream data were truthful or remained downloadable.
"""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "research" / "external-validation" / "agent-alphaxiv-002" / "selection-receipt.json"
LABEL = "FAR-AGENT-ALPHAXIV-002/candidate-v0.1"


def canonical(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def reconstruct(r):
    return {
        "protocol": r["protocol"],
        "status": "RESEARCH_CANDIDATE_NOT_LAUNCHED",
        "dataset": r["dataset"],
        "dataset_revision": r["dataset_revision"],
        "all_studies": r["expected_studies"],
        "paper_cohort": r["expected_paper_cohort"],
        "represented_labs": r["represented_sample_labs"],
        "sample_size": r["sample_size"],
        "input_row_metadata_sha256": r["input_row_metadata_sha256"],
        "selection_rule": "min SHA256(label + LF + project_id) per lab; then global min SHA256 fill",
        "selected": r["selected"],
        "verified_empirical_claims": r["verified_empirical_claims"],
    }


class ReceiptIntegrity(unittest.TestCase):
    def test_selected_60_are_unique_and_all_unreviewed(self):
        r = json.loads(RECEIPT.read_text(encoding="utf-8"))
        ids = [row["project_id"] for row in r["selected"]]
        self.assertEqual((len(ids), len(set(ids))), (60, 60))
        self.assertEqual(len({row["lab"] for row in r["selected"]}), 31)
        self.assertEqual(r["independent_sealed_cases"], 0)
        self.assertEqual(r["checker_executions"], 0)
        self.assertEqual(r["far_executions"], 0)
        digests = []
        for row in r["selected"]:
            self.assertEqual(row["screening_status"], "UNSCREENED")
            key = hashlib.sha256((LABEL + "\n" + row["project_id"]).encode("utf-8")).hexdigest()
            self.assertEqual(row["selection_digest"], key)
            digests.append(key)
        self.assertEqual(digests, sorted(digests))

    def test_canonical_manifest_and_byte_hashes_are_recomputable(self):
        r = json.loads(RECEIPT.read_text(encoding="utf-8"))
        self.assertEqual(r["status"], "METADATA_INTAKE_COMPLETE_UNSCREENED")
        self.assertEqual(r["dataset_revision"], "cc892aab131be3872283e1a778af663382315817")
        self.assertEqual((r["expected_studies"], r["expected_paper_cohort"]), (916, 881))
        data = reconstruct(r)
        h = hashlib.sha256(canonical(data)).hexdigest()
        self.assertEqual(h, r["manifest_canonical_sha256"])
        data["manifest_sha256"] = h
        artifact_bytes = (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        self.assertEqual(hashlib.sha256(artifact_bytes).hexdigest(), r["manifest_json_file_sha256"])

    def test_mutation_breaks_fingerprints(self):
        r = json.loads(RECEIPT.read_text(encoding="utf-8"))
        data = reconstruct(r)
        data["selected"][0]["title"] += " unauthorized change"
        self.assertNotEqual(hashlib.sha256(canonical(data)).hexdigest(), r["manifest_canonical_sha256"])


if __name__ == "__main__":
    unittest.main()
