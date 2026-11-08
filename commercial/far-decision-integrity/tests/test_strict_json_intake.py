"""Regression controls for LIM-057 commercial JSON trust-boundary ambiguity."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "commercial" / "far-decision-integrity" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from far_decision_integrity.cli import main as decision_main
from far_decision_integrity.evidence import canonical_json_bytes, verify_evidence_bundle
from far_decision_integrity.io import load_package
from far_decision_integrity.model import PackageValidationError
from far_decision_integrity.regression import load_suite
from far_decision_integrity.strict_json import loads_strict
from far_decision_integrity.swe_agent import load_swe_agent_trace


def _decision_package() -> dict:
    return {
        "schema_version": "far-decision-package/0.1",
        "decision_id": "demo-decision",
        "decision_type": "test",
        "policy_version": "1",
        "decision_root": "root",
        "proposed_action": {},
        "nodes": [{"node_id": "root", "kind": "decision", "statement": "Proceed"}],
        "dependencies": [],
        "authorization_requirements": [],
        "unknowns": [],
        "trace_completeness": 1.0,
        "metadata": {},
    }


class StrictJSONIntakeTests(unittest.TestCase):
    def test_decoder_recursion_error_fails_closed_at_every_reader(self) -> None:
        # CPython decoder nesting limits vary across supported Python versions.
        # Inject the actual error boundary on valid JSON rather than assuming
        # that any fixed nesting depth must fail on every interpreter.
        text = json.dumps(_decision_package())
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "manifest.json"
            source.write_text(text, encoding="utf-8")
            with mock.patch(
                "far_decision_integrity.strict_json.json.loads",
                side_effect=RecursionError("injected decoder depth overflow"),
            ) as decoder:
                with self.assertRaisesRegex(ValueError, "nesting"):
                    loads_strict(text)
                for loader, error in ((load_package, PackageValidationError),
                                      (load_suite, ValueError),
                                      (load_swe_agent_trace, ValueError)):
                    with self.subTest(loader=loader.__name__), self.assertRaisesRegex(error, "nesting"):
                        loader(source)
                self.assertFalse(verify_evidence_bundle(directory))
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(decision_main([str(source)]), 40)
                self.assertGreaterEqual(decoder.call_count, 6)
            self.assertEqual(json.loads(output.getvalue())["status"], "invalid-package")

    def test_parser_accepts_ordinary_json_and_rejects_ambiguity(self) -> None:
        self.assertEqual(loads_strict('{"a":[1,2.5,true,null]}'), {"a": [1, 2.5, True, None]})
        for text in (
            '{"x":1,"x":2}',
            '{"outer":{"x":1,"x":2}}',
            '[{"x":1,"x":2}]',
            '{"x":NaN}',
            '{"x":Infinity}',
            '{"x":-Infinity}',
            '{"x":1e999}',
            '{"x":-1e999}',
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                loads_strict(text)

    def test_decision_package_loader_and_cli_fail_closed(self) -> None:
        plain = json.dumps(_decision_package())
        self.assertEqual(loads_strict(plain)["decision_id"], "demo-decision")
        bad = (
            plain.replace('"decision_id": "demo-decision"', '"decision_id": "demo-decision", "decision_id": "other"'),
            plain.replace('"metadata": {}', '"metadata": {"x": 1, "x": 2}'),
            plain.replace('"metadata": {}', '"metadata": {"x": NaN}'),
            plain.replace('"metadata": {}', '"metadata": {"x": 1e999}'),
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "package.json"
            source.write_text(plain, encoding="utf-8")
            self.assertEqual(load_package(source).decision_id, "demo-decision")
            for text in bad:
                with self.subTest(text=text):
                    source.write_text(text, encoding="utf-8")
                    with self.assertRaises(PackageValidationError):
                        load_package(source)
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        code = decision_main([str(source)])
                    self.assertEqual(code, 40)
                    self.assertEqual(json.loads(output.getvalue())["status"], "invalid-package")

    def test_regression_loader_rejects_invalid_json(self) -> None:
        plain = '{"suite_id":"s","baseline":[],"candidate":[]}'
        bad = (
            '{"suite_id":"s","suite_id":"other","baseline":[],"candidate":[]}',
            '{"suite_id":"s","baseline":[],"candidate":[],"extra":NaN}',
            '{"suite_id":"s","baseline":[],"candidate":[],"extra":1e999}',
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "suite.json"
            source.write_text(plain, encoding="utf-8")
            self.assertEqual(load_suite(source)[0], "s")
            for text in bad:
                with self.subTest(text=text):
                    source.write_text(text, encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "unable to load regression suite"):
                        load_suite(source)

    def test_swe_trajectory_loader_rejects_invalid_json(self) -> None:
        plain = '{"trajectory":[]}'
        bad = (
            '{"trajectory":[],"trajectory":[]}',
            '{"trajectory":[],"ignored":NaN}',
            '{"trajectory":[],"ignored":1e999}',
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "trajectory.json"
            source.write_text(plain, encoding="utf-8")
            self.assertEqual(len(load_swe_agent_trace(source).events), 0)
            for text in bad:
                with self.subTest(text=text):
                    source.write_text(text, encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "unable to load SWE-agent trajectory"):
                        load_swe_agent_trace(source)

    def test_evidence_manifest_rejects_invalid_json_without_bypassing_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            contents = b'{"finding":"unchanged"}\n'
            (root / "report.json").write_bytes(contents)
            digest = hashlib.sha256(contents).hexdigest()
            plain = json.dumps({
                "schema_version": "far-evidence-manifest/0.1",
                "report": {"path": "report.json", "sha256": digest},
                "sources": [],
            })
            manifest = root / "manifest.json"
            manifest.write_text(plain, encoding="utf-8")
            self.assertTrue(verify_evidence_bundle(root))
            bad = (
                plain.replace('"sources": []', '"sources": [], "sources": []'),
                plain.replace('"sources": []', '"sources": [], "ignored": NaN'),
                plain.replace('"sources": []', '"sources": [], "ignored": 1e999'),
            )
            for text in bad:
                with self.subTest(text=text):
                    manifest.write_text(text, encoding="utf-8")
                    self.assertFalse(verify_evidence_bundle(root))

    def test_synthetic_cli_examples_and_semantic_gate(self) -> None:
        from far_decision_integrity.adjudicate import adjudicate

        examples = ROOT / "commercial" / "far-decision-integrity" / "examples"
        clear = load_package(examples / "clear-package.json")
        contradicted = load_package(examples / "contradicted-package.json")
        self.assertEqual(adjudicate(clear).status.value, "justified")
        self.assertEqual(adjudicate(contradicted).status.value, "unsupported")
        self.assertEqual(adjudicate(clear, require_semantic_contract=True).status.value, "unverifiable")

    def test_writer_rejects_nonfinite_numbers(self) -> None:
        for number in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(number=str(number)), self.assertRaises(ValueError):
                canonical_json_bytes({"invalid": number})
        self.assertEqual(canonical_json_bytes({"b": 2, "a": 1}), b'{"a":1,"b":2}\n')


if __name__ == "__main__":
    unittest.main()
