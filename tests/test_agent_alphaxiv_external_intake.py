"""Tests for candidate external-data seal; fixtures do not count as external results."""
import importlib.util
from pathlib import Path
import random
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "agent_alphaxiv_external_intake.py"
spec = importlib.util.spec_from_file_location("agent_alphaxiv_external_intake", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def rows():
    return [
        {"project_id": f"id-{n}", "lab": f"Lab {n % 3}", "title": f"Paper {n}",
         "slug": f"paper-{n}", "latest_version_id": f"version-{n}",
         "in_paper_cohort": n != 9}
        for n in range(10)
    ]


class CandidateIntakeTests(unittest.TestCase):
    def test_deterministic_under_reordering_and_ignores_titles_for_selection(self):
        base = rows()
        result = module.build_manifest(base, strict=False, sample_size=6)
        again = base.copy()
        random.Random(4).shuffle(again)
        self.assertEqual(result, module.build_manifest(again, strict=False, sample_size=6))
        self.assertEqual(len(result["selected"]), 6)
        self.assertEqual({r["lab"] for r in result["selected"]}, {"Lab 0", "Lab 1", "Lab 2"})
        self.assertTrue(all(r["screening_status"] == "UNSCREENED" for r in result["selected"]))
        self.assertEqual(result["verified_empirical_claims"], 0)
        altered = rows()
        altered[0]["title"] = "Title changed without changing sampling key"
        b = module.build_manifest(altered, strict=False, sample_size=6)
        self.assertEqual({r["project_id"] for r in result["selected"]}, {r["project_id"] for r in b["selected"]})
        self.assertNotEqual(result["input_row_metadata_sha256"], b["input_row_metadata_sha256"])

    def test_duplicate_fail_closed(self):
        base = rows()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            module.build_manifest(base + [base[0]], strict=False, sample_size=5)

    def test_non_boolean_and_missing_id_fail_closed(self):
        base = rows()
        base[0]["in_paper_cohort"] = "true"
        with self.assertRaisesRegex(ValueError, "boolean"):
            module.build_manifest(base, strict=False, sample_size=5)
        base = rows()
        base[0]["project_id"] = None
        with self.assertRaisesRegex(ValueError, "project_id"):
            module.build_manifest(base, strict=False, sample_size=5)

    def test_counts_are_strict_by_default(self):
        with self.assertRaisesRegex(ValueError, "source count mismatch"):
            module.build_manifest(rows(), sample_size=6)

    def test_insufficient_sample_and_labs_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "insufficient"):
            module.build_manifest(rows(), strict=False, sample_size=10)
        with self.assertRaisesRegex(ValueError, "smaller than"):
            module.build_manifest(rows(), strict=False, sample_size=2)

    def test_only_cohort_samples(self):
        m = module.build_manifest(rows(), strict=False, sample_size=6)
        self.assertNotIn("id-9", {r["project_id"] for r in m["selected"]})


if __name__ == "__main__":
    unittest.main()
