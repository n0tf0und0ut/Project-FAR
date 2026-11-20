"""Synthetic source-succession controls; these do not certify any external study."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "agent_alphaxiv_external_intake.py"
spec = importlib.util.spec_from_file_location("candidate_intake", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture_rows():
    return [
        {
            "project_id": f"study-{n:03}",
            "lab": f"Lab {n % 3}",
            "title": f"Test paper {n}",
            "slug": f"paper-{n}",
            "latest_version_id": f"version-{n}",
            "in_paper_cohort": n != 7,
        }
        for n in range(12)
    ]


class DistinctSourceCandidateTests(unittest.TestCase):
    def test_original_registration_is_unchanged(self):
        self.assertEqual(module.SOURCES["001"], (
            "a63f46066ac16fcb470f41933415e175825b6bcc", 961, 926,
            "FAR-AGENT-ALPHAXIV-001/candidate-v0.1",
        ))
        original = module.build_manifest(fixture_rows(), strict=False, sample_size=6)
        explicit = module.build_manifest(fixture_rows(), strict=False, sample_size=6, candidate="001")
        self.assertEqual(original, explicit)

    def test_002_is_separate_with_exact_new_source(self):
        result = module.build_manifest(fixture_rows(), strict=False, sample_size=6, candidate="002")
        self.assertEqual(result["dataset_revision"], "cc892aab131be3872283e1a778af663382315817")
        self.assertEqual(result["protocol"], "FAR-AGENT-ALPHAXIV-002/candidate-v0.1")
        self.assertEqual(result["sample_size"], 6)
        self.assertEqual(result["verified_empirical_claims"], 0)
        self.assertEqual({row["lab"] for row in result["selected"]}, {"Lab 0", "Lab 1", "Lab 2"})
        self.assertTrue(all(row["screening_status"] == "UNSCREENED" for row in result["selected"]))

    def test_successor_metadata_determinism(self):
        a = fixture_rows()
        self.assertEqual(
            module.build_manifest(a, strict=False, sample_size=6, candidate="002"),
            module.build_manifest(a[::-1], strict=False, sample_size=6, candidate="002")
        )

    def test_unknown_source_and_002_strict_counts_fail(self):
        with self.assertRaisesRegex(ValueError, "unregistered candidate"):
            module.build_manifest(fixture_rows(), strict=False, candidate="bogus")
        with self.assertRaisesRegex(ValueError, "916, 881"):
            module.build_manifest(fixture_rows(), candidate="002")


if __name__ == "__main__":
    unittest.main()
