"""Ninth-review counterexamples for generated bounds and numeric anchoring."""
from __future__ import annotations

import copy
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine import InvalidBundle, audit, canonical, digest
from full_cli import verify_package, write_package
from independent_check import IndependentCheckError, check_report
from proposals import MAX_READINGS, heuristic_proposal
from workflow import investigate
from test_review_578 import bundle


def numeric_bundle(quote="2 dollars received.", value="2", start=0,
                   snapshot='{"rows":[{"amount":2}]}'):
    result = bundle(primary=quote, secondary=snapshot)
    result["claims"][0]["quantity"] = {
        "value": value, "number_span": {"start": start, "end": start + len(value)},
        "unit": "dollars"}
    evidence = result["evidence"][0]
    evidence.pop("formula")
    evidence["data_check"] = {"operation": "sum_field", "pointer": "/rows",
                              "field": "amount"}
    return result


def config_for(snapshot):
    quote = "2 dollars received."
    return {
        "source": {"kind": "text", "text": quote},
        "evidence_sources": [{"kind": "text", "text": snapshot}],
        "proposal_mode": "supplied",
        "proposal": {"claims": [{"id": "c1", "quote": quote, "quantity": {
            "value": "2", "number_span": {"start": 0, "end": 1}, "unit": "dollars"}}],
            "arguments": [], "evidence": [{"id": "e1", "claim_id": "c1",
                "source_id": "ev1", "quote": snapshot, "relation": "supports",
                "data_check": {"operation": "sum_field", "pointer": "/rows", "field": "amount"}}]}}


class NinthReviewRegressions(unittest.TestCase):
    def test_generated_reading_overflow_is_bounded_disclosed_and_replayable(self):
        for count in (13, 23):
            text = "The initial observation is recorded. " + " ".join(
                f"Therefore conclusion number {i} follows." for i in range(count))
            with self.subTest(count=count), tempfile.TemporaryDirectory() as folder:
                proposal = heuristic_proposal(text)
                self.assertEqual(len(proposal["arguments"]), MAX_READINGS)
                omission = f"{count - MAX_READINGS} additional discourse-cue candidate"
                self.assertTrue(any(omission in note for note in proposal["unknowns"]))
                result = investigate({"source": {"kind": "text", "text": text}})
                self.assertEqual(len(result["audit"]["interpretations"]), MAX_READINGS)
                self.assertIn(omission, result["report_md"])
                path = pathlib.Path(folder) / "package"
                write_package(path, result)
                self.assertTrue(verify_package(path)["replay_match"])

    def test_exact_reading_limit_does_not_report_truncation(self):
        text = "An observation was recorded. " + " ".join(
            f"Therefore conclusion number {i} follows." for i in range(MAX_READINGS))
        proposal = heuristic_proposal(text)
        self.assertEqual(len(proposal["arguments"]), MAX_READINGS)
        self.assertFalse(any("additional discourse-cue candidate" in note
                             for note in proposal["unknowns"]))

    def test_extreme_decimal_exponents_are_unavailable_in_both_parsers(self):
        for number in ("1e9999999999999999999999999", "-1e-9999999999999999999999999"):
            with self.subTest(number=number):
                case = numeric_bundle(snapshot='{"rows":[{"amount":' + number + '}]}')
                report = audit(case)
                finding = report["claims"]["c1"]["evidence"][0]["structured_check"]
                self.assertEqual(finding["status"], "STRUCTURED_UNVERIFIABLE")
                self.assertTrue(check_report(case, report)["independent_algorithm_agrees"])

    def test_extreme_source_number_completes_cli_and_package_replay(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            request, output = root / "request.json", root / "package"
            request.write_bytes(canonical(config_for(
                '{"rows":[{"amount":1e9999999999999999999999999}]}')))
            run = subprocess.run([sys.executable, str(ROOT / "full_cli.py"), str(request),
                                  "--output", str(output)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertTrue(verify_package(output)["replay_match"])

    def test_partial_numeric_literals_are_rejected_by_primary_checker(self):
        for quote, value, start in (("-2 dollars received.", "2", 1),
                                     ("12 dollars received.", "2", 1),
                                     ("1.2 dollars received.", "2", 2),
                                     ("1.2 dollars received.", "1", 0),
                                     ("1e2 dollars received.", "2", 2),
                                     ("+2 dollars received.", "2", 1),
                                     ("−2 dollars received.", "2", 1),
                                     ("1,234 dollars received.", "234", 2),
                                     (".2 dollars received.", "2", 1)):
            with self.subTest(quote=quote, value=value):
                with self.assertRaisesRegex(InvalidBundle, "complete numeric literal"):
                    audit(numeric_bundle(quote, value, start))

    def test_independent_checker_rejects_forged_partial_numeric_anchor(self):
        original = numeric_bundle()
        report = audit(original)
        for quote, value, start in (("-2 dollars received.", "2", 1),
                                     ("12 dollars received.", "2", 1),
                                     ("1.2 dollars received.", "2", 2)):
            with self.subTest(quote=quote):
                case = numeric_bundle(quote, value, start)
                forged = copy.deepcopy(report)
                forged["input_sha256"] = digest(canonical(case))
                forged["report_sha256"] = digest(canonical(
                    {k: v for k, v in forged.items() if k != "report_sha256"}))
                with self.assertRaisesRegex(IndependentCheckError, "numeric literal"):
                    check_report(case, forged)

    def test_complete_signed_decimal_and_punctuation_remain_supported(self):
        for quote, value, start, number in (("-2 dollars received.", "-2", 0, "-2"),
                                            ("1.2 dollars received.", "1.2", 0, "1.2"),
                                            ("Total: 2.", "2", 7, "2"),
                                            ("Total: (2).", "2", 8, "2")):
            with self.subTest(quote=quote):
                case = numeric_bundle(quote, value, start,
                                      '{"rows":[{"amount":' + number + '}]}')
                report = audit(case)
                self.assertEqual(report["claims"]["c1"]["evidence"][0]
                                 ["structured_check"]["status"], "STRUCTURED_VALUE_MATCH")
                self.assertTrue(check_report(case, report)["independent_algorithm_agrees"])

    def test_clipping_the_claim_quote_cannot_strip_a_numeric_prefix(self):
        original = numeric_bundle()
        report = audit(original)
        for prefix in ("-", "1", "1.", "1e", "1,"):
            with self.subTest(prefix=prefix):
                case = copy.deepcopy(original)
                source = case["sources"][0]
                source["text"] = prefix + source["text"]
                source["sha256"] = digest(source["text"].encode())
                span = case["claims"][0]["span"]
                span["start"] += len(prefix)
                span["end"] += len(prefix)
                with self.assertRaisesRegex(InvalidBundle, "complete numeric literal"):
                    audit(case)
                forged = copy.deepcopy(report)
                forged["input_sha256"] = digest(canonical(case))
                forged["report_sha256"] = digest(canonical(
                    {k: v for k, v in forged.items() if k != "report_sha256"}))
                with self.assertRaisesRegex(IndependentCheckError, "numeric literal"):
                    check_report(case, forged)


if __name__ == "__main__":
    unittest.main()
