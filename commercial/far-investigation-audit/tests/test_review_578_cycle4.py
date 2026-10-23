"""PR #578 independent fourth-review, five-invariant regression suite.

Each adversarial case preserves a previously accepted bounded source package
and attacks one declared provenance/identity/evaluation/failure boundary.
"""
from __future__ import annotations

import copy
import json
import pathlib
import sys
import tempfile
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from engine import InvalidBundle, digest, canonical
from field_validation import evaluate, predictions_from_far_bundle
from full_cli import write_package, verify_package
from independent_check import IndependentCheckError, check_report
from presentation import render_markdown
from proposals import openai_proposal
from workflow import investigate

CUTOFF = "2026-10-17T12:00:00Z"


def offline_package(inv_id="cycle4"):
    return investigate({"investigation_id": inv_id, "captured_at": CUTOFF,
                        "source": {"kind": "text", "text": "Exactly three observations were recorded."}})


class FourthReviewRegressions(unittest.TestCase):
    def test_unexpanded_discovery_route_is_immutable_audit_provenance(self):
        pkg = investigate(
            {"investigation_id": "discovery_network_receipt",
             "source": {"kind": "text", "text": "Exactly three observations were recorded."},
             "discovery": "tavily", "queries": ["sample research claim"]},
            permit_network=True,
            search_requester=lambda payload: {"results": []},
        )
        self.assertEqual(pkg["discovery"]["provider"], "tavily")
        self.assertRegex(pkg["bundle"]["discovery_sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(pkg["manifest"]["network_used"])
        original_identity = pkg["audit"]["report_sha256"]
        self.assertTrue(original_identity)
        pkg["discovery"] = None
        pkg["report_md"] = render_markdown(
            pkg["bundle"], pkg["audit"], acquisition=pkg["acquisition"],
            discovery=None, questions=pkg["critical_questions"])
        pkg["manifest"]["report_md_sha256"] = digest(pkg["report_md"].encode("utf-8"))
        pkg["manifest"]["network_used"] = False
        # The manifest and its complete file hash map are unsigned and can be
        # recomputed by write_package; original audited input/report stays same.
        with tempfile.TemporaryDirectory() as d:
            folder = pathlib.Path(d) / "pkg"
            write_package(folder, pkg)
            with self.assertRaisesRegex(InvalidBundle, "discovery provenance commitment"):
                verify_package(folder)

    def test_identity_fields_and_self_excluding_digest_independently_checked(self):
        pkg = offline_package()
        b, report = pkg["bundle"], pkg["audit"]
        self.assertTrue(check_report(b, report)["independent_algorithm_agrees"])
        for name, forged_value in (
            ("schema", "forged-schema"), ("engine", "forged-engine"),
            ("investigation_id", "fake_id"),
            ("input_sha256", "f" * 64),
            ("as_of", "2026-10-18T00:00:00Z"),
            ("report_sha256", "0" * 64),
        ):
            with self.subTest(field=name):
                forged = copy.deepcopy(report)
                forged[name] = forged_value
                with self.assertRaisesRegex(IndependentCheckError, "report identity"):
                    check_report(b, forged)

    def test_over_nested_manifest_and_nested_input_fail_closed(self):
        pkg = offline_package()
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d) / "pkg"
            write_package(root, pkg)
            oversized_depth = ("[" * 10000 + "0" + "]" * 10000).encode()
            self.assertLess(len(oversized_depth), 6_000_000)
            (root / "manifest.json").write_bytes(oversized_depth)
            with self.assertRaisesRegex(InvalidBundle, "over-nested JSON artifact"):
                verify_package(root)
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d) / "pkg"
            write_package(root, pkg)
            (root / "input.json").write_bytes(oversized_depth)
            manifest_path = root / "manifest.json"
            manifest = json.loads(manifest_path.read_bytes())
            manifest["files_sha256"]["input.json"] = digest(oversized_depth)
            manifest_path.write_bytes(canonical(manifest))
            with self.assertRaisesRegex(InvalidBundle, "over-nested JSON artifact"):
                verify_package(root)

    def test_generated_case_ids_fit_bounds_and_do_not_alias_colon_pairs(self):
        def prediction(inv_id, claim_id):
            p = investigate({
                "investigation_id": inv_id, "captured_at": CUTOFF,
                "source": {"kind": "text", "text": "Exactly three observations were recorded."},
                "proposal_mode": "supplied",
                "proposal": {"claims": [{"id": claim_id,
                            "quote": "Exactly three observations were recorded."}]},
            })
            with tempfile.TemporaryDirectory() as d:
                path = pathlib.Path(d) / "pkg"
                write_package(path, p)
                result = predictions_from_far_bundle(path)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["investigation_id"], inv_id)
            self.assertEqual(result[0]["claim_id"], claim_id)
            self.assertLessEqual(len(result[0]["case_id"]), 160)
            self.assertEqual(result[0]["verdict"], "ABSTAIN")
            return result[0]
        long = prediction("a" * 80, "b" * 80)
        reference = {"case_id": long["case_id"], "domain": "research",
                     "reference_verdict": "SUPPORTED", "mapping_fidelity": "FAITHFUL",
                     "evidence_adequacy": "ADEQUATE", "temporal_eligibility": "IN_WINDOW"}
        self.assertEqual(evaluate([long], [reference])["overall"]["abstained"], 1)
        self.assertNotEqual(prediction("a:b", "c")["case_id"],
                            prediction("a", "b:c")["case_id"])

    def test_model_provider_timeout_is_bounded_workflow_error(self):
        def bad_call(**kwargs):
            raise TimeoutError("private SDK error must not leak")
        fake = SimpleNamespace(chat=SimpleNamespace(
            completions=SimpleNamespace(create=bad_call)))
        with self.assertRaisesRegex(InvalidBundle, "model proposal provider unavailable"):
            openai_proposal("A bounded source sentence.", {}, client=fake)


if __name__ == "__main__":
    unittest.main()
