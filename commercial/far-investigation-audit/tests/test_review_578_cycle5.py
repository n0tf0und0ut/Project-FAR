"""Fifth-review counterexamples: bounded I/O/work and independent identity."""
from __future__ import annotations

import copy
import io
from pathlib import Path
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import engine
import independent_check
from engine import InvalidBundle, audit, canonical, digest
from independent_check import IndependentCheckError, check_report
from local_media import read_pdf, transcribe_local
from full_cli import verify_package, write_package
from workflow import investigate
from test_review_578 import bundle

ROOT = pathlib.Path(__file__).resolve().parents[1]


def rehash(report, source=None):
    if source is not None:
        report["input_sha256"] = digest(canonical(source))
    report.pop("report_sha256", None)
    report["report_sha256"] = digest(canonical(report))


def work_bundle(unique):
    b = bundle()
    b["atoms"] = {f"A{i}": f"Declared atom {i}" for i in range(12)}
    b["claims"][0]["formula"] = {"atom": "A0"}
    prototype = b["evidence"][0]
    b["evidence"] = []
    for i in range(48):
        leaves = [{"atom": f"A{j % 12}"} for j in range(480)]
        if unique:
            leaves[i], leaves[i + 1] = leaves[i + 1], leaves[i]
        record = copy.deepcopy(prototype)
        record["id"] = f"e{i}"
        record["formula"] = {"and": [{"and": leaves[j:j + 30]} for j in range(0, 480, 30)]}
        b["evidence"].append(record)
    return b


class FifthReviewRegressions(unittest.TestCase):
    def test_file_growth_after_size_check_remains_bounded(self):
        from bounded_io import BoundedInputError, read_bounded
        import os
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "growing.txt"
            path.write_bytes(b"small")
            original_stat = os.fstat
            def grow(fd):
                before = original_stat(fd)
                path.write_bytes(b"x" * 100)
                return before
            with patch("bounded_io.os.fstat", side_effect=grow):
                with self.assertRaises(BoundedInputError):
                    read_bounded(path, 32)

    def test_all_file_clis_reject_oversize_before_allocation(self):
        import resource  # Hosted contract is Linux; confines the adversarial child.
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d)
            huge = p / "huge.json"
            with huge.open("wb") as f:
                f.truncate(512 * 1024 * 1024)  # Sparse, no half-gigabyte allocation.
            config = p / "config.json"
            config.write_text(json.dumps({"source": {"kind": "text", "text": "A bounded source."}}))
            review = p / "review.json"
            review.write_text('{"schema":"far-review-attestation/1.0"}')
            cases = [
                ("cli.py", [str(huge)], "FAR_AUDIT_INVALID"),
                ("verify.py", [str(huge), str(config)], "FAR_REPLAY_INVALID"),
                ("evaluate.py", [str(huge)], "FAR_DIAGNOSTIC_INVALID"),
                ("capture.py", [str(huge), "--id", "bounded"], "FAR_CAPTURE_INVALID"),
                ("full_cli.py", [str(huge), "--output", str(p / "out")], "FAR_END_TO_END_INVALID"),
                ("full_cli.py", [str(config), "--review", str(huge), "--output", str(p / "out")], "FAR_END_TO_END_INVALID"),
                ("review.py", [str(huge), "--private-key", str(config), "--output", str(p / "out")], "FAR_REVIEW_INVALID"),
                ("review.py", [str(review), "--private-key", str(huge), "--output", str(p / "out")], "FAR_REVIEW_INVALID"),
            ]
            def constrain():
                resource.setrlimit(resource.RLIMIT_AS, (128 * 1024 * 1024,) * 2)
            for script, args, prefix in cases:
                with self.subTest(script=script, args=args):
                    result = subprocess.run([sys.executable, str(ROOT / script), *args],
                        capture_output=True, text=True, timeout=15, preexec_fn=constrain)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertTrue(result.stderr.startswith(prefix), result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertFalse((p / "out").exists())

    def test_pdf_hash_and_extraction_use_the_same_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "source.pdf"
            original = b"synthetic original PDF bytes"
            path.write_bytes(original)
            seen = []
            def reader(stream, **kwargs):
                seen.append(stream.read())
                path.write_bytes(b"replacement after extraction")
                return SimpleNamespace(is_encrypted=False, pages=[SimpleNamespace(
                    extract_text=lambda: "Original extracted text.")])
            with patch.dict(sys.modules, {"pypdf": SimpleNamespace(PdfReader=reader)}):
                result = read_pdf(path)
            self.assertEqual(seen, [original])
            self.assertEqual(result["raw_sha256"], digest(original))

    def test_media_hash_and_converter_use_the_same_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            path = pathlib.Path(d) / "source.wav"
            original = b"synthetic original recording"
            path.write_bytes(original)
            seen = []
            def convert(command, **kwargs):
                staged = pathlib.Path(command[command.index("-i") + 1])
                seen.append(staged.read_bytes())
                self.assertNotEqual(staged, path)
                path.write_bytes(b"replacement during conversion")
                pathlib.Path(command[-1]).write_bytes(b"synthetic encoding")
                return SimpleNamespace(returncode=0)
            client = SimpleNamespace(audio=SimpleNamespace(transcriptions=SimpleNamespace(
                create=lambda **kwargs: SimpleNamespace(text="Original recording text."))))
            with patch("local_media.subprocess.run", side_effect=convert):
                result = transcribe_local(path, permit_model=True, client=client)
            self.assertEqual(seen, [original])
            self.assertEqual(result["raw_sha256"], digest(original))

    def test_unverifiable_reason_is_recomputed_not_merely_nonempty(self):
        for text in ('{"rows":[{"x":1e100}]}', '{"rows":[{}]}', '{"rows":false}', 'bad JSON'):
            with self.subTest(source=text):
                b = bundle(secondary=text)
                b["claims"][0]["quantity"] = {"value": "1", "number_span": {"start": 8, "end": 9}, "unit": "rows"}
                b["evidence"][0].pop("formula")
                b["evidence"][0]["data_check"] = {"operation": "sum_field", "pointer": "/rows", "field": "x"}
                report = audit(b)
                self.assertTrue(check_report(b, report)["independent_algorithm_agrees"])
                report["claims"]["c1"]["evidence"][0]["structured_check"]["reason"] = "All values independently verified"
                rehash(report)
                with self.assertRaises(IndependentCheckError):
                    check_report(b, report)

    def test_temporal_oracle_rejects_invalid_publication_and_non_utc_capture(self):
        for field, value in (("published_at", "2026-10-18T00:00:00Z"),
                             ("published_at", "not a timestamp"),
                             ("captured_at", "2026-10-17T12:00:00+01:00")):
            with self.subTest(field=field, value=value):
                b = bundle()
                report = audit(b)
                b["sources"][1][field] = value
                rehash(report, b)
                with self.assertRaises(IndependentCheckError):
                    check_report(b, report)

    def test_formal_results_preserve_json_number_and_boolean_types(self):
        b = json.loads((ROOT / "examples" / "causal_jump.json").read_text())
        for field in ("assignments_checked", "premise_satisfying_assignments", "countermodel"):
            with self.subTest(field=field):
                report = audit(b)
                result = report["interpretations"][0]["formal_inference"]
                result[field] = ({k: int(v) for k, v in result[field].items()}
                                 if field == "countermodel" else float(result[field]))
                rehash(report)
                with self.assertRaises(IndependentCheckError):
                    check_report(b, report)
        evidence_bundle = bundle()
        evidence_bundle["atoms"]["Q"] = "Another declared observation"
        evidence_bundle["evidence"][0]["formula"] = {"atom": "Q"}
        report = audit(evidence_bundle)
        finding = report["claims"]["c1"]["evidence"][0]
        finding["countermodel"] = {k: int(v) for k, v in finding["countermodel"].items()}
        rehash(report)
        with self.assertRaises(IndependentCheckError):
            check_report(evidence_bundle, report)

    def test_aggregate_distinct_entailment_work_is_bounded(self):
        # Instrument the expensive primitive so the regression itself never
        # spends the formerly permitted hundreds of millions of node visits.
        with patch("engine.entailment", return_value={"status": "ENTAILS_CONDITIONALLY"}):
            with self.assertRaisesRegex(InvalidBundle, "work budget"):
                audit(work_bundle(unique=True))

    def test_repeated_entailment_pairs_are_computed_once_per_audit(self):
        with patch("engine.entailment", return_value={"status": "ENTAILS_CONDITIONALLY"}) as evaluate:
            audit(work_bundle(unique=False))
            self.assertEqual(evaluate.call_count, 2)


    def test_legacy_replay_does_not_coerce_float_counts_to_json_integers(self):
        import verify
        bundle = json.loads((ROOT / "examples/causal_jump.json").read_bytes())
        report = audit(bundle)
        report["interpretations"][0]["formal_inference"]["assignments_checked"] = float(
            report["interpretations"][0]["formal_inference"]["assignments_checked"])
        with tempfile.TemporaryDirectory() as folder:
            b, r = Path(folder) / "input.json", Path(folder) / "audit.json"
            b.write_bytes(canonical(bundle)); r.write_bytes(canonical(report))
            with patch.object(sys, "argv", ["verify", str(b), str(r)]), \
                    patch.object(sys, "stdout", io.StringIO()):
                self.assertEqual(verify.main(), 1)


    def test_package_replay_does_not_coerce_zero_to_false(self):
        package = investigate(json.loads((ROOT / "examples/full_speech.json").read_bytes()))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "package"
            write_package(root, package)
            path = root / "audit.json"
            report = json.loads(path.read_bytes())
            report["interpretations"][0]["semantic_fidelity_independently_verified"] = 0
            raw = canonical(report) + b"\n"
            path.write_bytes(raw)
            manifest_path = root / "manifest.json"
            manifest = json.loads(manifest_path.read_bytes())
            manifest["files_sha256"]["audit.json"] = digest(raw)
            manifest_path.write_bytes(canonical(manifest))
            with self.assertRaisesRegex(InvalidBundle, "auditor replay mismatch"):
                verify_package(root)

    def test_independent_repeated_queries_are_computed_once(self):
        b = work_bundle(unique=False)
        report = audit(b)
        with patch("independent_check.check", wraps=independent_check.check) as calls:
            self.assertTrue(check_report(b, report)["independent_algorithm_agrees"])
            self.assertEqual(calls.call_count, 2)

    def test_cache_hits_do_not_expand_entire_formula_families_again(self):
        b = bundle()
        b["atoms"] = {f"A{i}": f"Declared atom {i}" for i in range(40)}
        prototype = b["claims"][0]
        b["claims"] = []
        for i in range(80):
            formula = {"and": [{"or": [{"atom": f"A{(i+j+k*18) % 40}"}
                                        for j in range(18)]} for k in range(10)]}
            b["claims"].append({**copy.deepcopy(prototype), "id": f"c{i}", "formula": formula})
        b["evidence"] = []
        b["interpretations"] = [{"id": f"r{i}", "premises": [f"c{j}" for j in range(79)],
                                  "conclusion": "c79", "mapping_status": "unreviewed"}
                                 for i in range(400)]
        input_size = len(canonical(b))
        self.assertLess(input_size, 2_000_000)
        serialized_bytes = 0
        original = engine.canonical
        def counted(value):
            nonlocal serialized_bytes
            raw = original(value)
            serialized_bytes += len(raw)
            return raw
        with patch("engine.canonical", side_effect=counted):
            report = audit(b)
        self.assertEqual(len(report["interpretations"]), 400)
        # A cache hit cannot serialize the full formula family again. This
        # bounds deterministic serialization work without a timing assertion.
        self.assertLess(serialized_bytes, 25 * input_size)

    def test_manifest_cannot_add_an_unbounded_family_of_artifacts(self):
        package = investigate(json.loads((ROOT / "examples/full_speech.json").read_bytes()))
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder) / "package"
            write_package(root, package)
            path = root / "manifest.json"
            manifest = json.loads(path.read_bytes())
            for i in range(50):
                name = f"extra{i}.txt"
                (root / name).write_bytes(b"untrusted adjunct")
                manifest["files_sha256"][name] = digest(b"untrusted adjunct")
            path.write_bytes(canonical(manifest))
            with self.assertRaises(InvalidBundle):
                verify_package(root)

    def test_package_writer_rejects_artifacts_that_cannot_be_verified(self):
        package = investigate(json.loads((ROOT / "examples/full_speech.json").read_bytes()))
        package["report_md"] = "x" * 6_000_001
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder) / "package"
            with self.assertRaisesRegex(InvalidBundle, "artifact size limit"):
                write_package(root, package)
            self.assertFalse(root.exists())
            self.assertEqual(list(pathlib.Path(folder).iterdir()), [])


if __name__ == "__main__":
    unittest.main()
