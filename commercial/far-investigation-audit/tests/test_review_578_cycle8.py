"""Eighth-cycle red/green controls for ambiguous replay and mutable inputs."""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from engine import InvalidBundle, canonical
from evaluate import evaluate_cases
from field_validation import predictions_from_far_bundle
from full_cli import verify_package, write_package
from workflow import investigate
import verify


def sample():
    return investigate({"source": {"kind": "text", "text": "One bounded claim can be audited."}})


class EighthReviewRegressions(unittest.TestCase):
    def test_manifest_cannot_assert_unverified_truth_or_semantics(self):
        for injected in ({"external_truth_verified": True},
                         {"semantic_fidelity_verified": True}):
            with self.subTest(injected=injected), tempfile.TemporaryDirectory() as folder:
                path = pathlib.Path(folder) / "package"
                write_package(path, sample())
                manifest_path = path / "manifest.json"
                manifest = json.loads(manifest_path.read_bytes())
                manifest.update(injected)
                manifest_path.write_bytes(canonical(manifest))
                with self.assertRaisesRegex(InvalidBundle, "manifest fields"):
                    verify_package(path)

    def test_standalone_replay_refuses_duplicate_object_fields(self):
        result = sample()
        for target, existing_key in (("report", "input_sha256"), ("input", "investigation_id")):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as folder:
                root = pathlib.Path(folder)
                b, r = root / "input.json", root / "report.json"
                b.write_bytes(canonical(result["bundle"]))
                r.write_bytes(canonical(result["audit"]))
                path = b if target == "input" else r
                path.write_bytes(b'{"' + existing_key.encode() + b'":"attacker-first",' +
                                 path.read_bytes()[1:])
                with mock.patch.object(sys, "argv", ["verify", str(b), str(r)]):
                    with redirect_stderr(StringIO()):
                        self.assertEqual(verify.main(), 2)

    def test_predictions_use_previously_verified_bytes_after_file_swap(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "package"
            write_package(path, sample())
            actual_ids = set(json.loads((path / "audit.json").read_bytes())["claims"])
            real_verify = verify_package

            def tamper_after_validation(directory, **kwargs):
                validated = real_verify(directory, **kwargs)
                malicious = json.loads((path / "audit.json").read_bytes())
                malicious["claims"] = {"forged": {"status": "SUPPORTED"}}
                (path / "audit.json").write_bytes(canonical(malicious))
                return validated

            with mock.patch("full_cli.verify_package", side_effect=tamper_after_validation):
                extracted = predictions_from_far_bundle(path)
            self.assertEqual({p["claim_id"] for p in extracted}, actual_ids)
            self.assertNotIn("forged", {p["claim_id"] for p in extracted})

    def test_oversized_discovery_expansion_is_skipped_and_disclosed(self):
        outcome = investigate(
            {"source": {"kind": "text", "text": "A bounded claim."},
             "discovery": "tavily", "queries": ["claim"], "expand_discovery": True},
            permit_network=True,
            source_fetcher=lambda url, *, permit_network: {"text": "x" * 200_000},
            search_requester=lambda payload: {"results": [{
                "url": "https://example.org/source", "title": "large source"}]})
        self.assertEqual(len(outcome["bundle"]["sources"]), 1)
        receipt = outcome["discovery"]["results"][0]
        self.assertIn("exceeds text cap", receipt["fetch_status"])
        self.assertNotIn("source_id", receipt)

    def test_empty_or_misspelled_diagnostic_expectations_fail_closed(self):
        configuration = {"source": {"kind": "text", "text": "A bounded claim."}}
        for expected in ({}, {"nonexistent_result_key": None}):
            with self.subTest(expected=expected):
                with self.assertRaisesRegex(InvalidBundle, "diagnostic expectations"):
                    evaluate_cases([{"config": configuration, "expected": expected}])


if __name__ == "__main__":
    unittest.main()
