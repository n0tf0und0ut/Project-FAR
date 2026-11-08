"""Regression controls for frozen-evidence relocation and score binding."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("convergence_replay", ROOT / "tools/replay_convergence_comparators.py")
replay = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(replay)
ARCHIVE = ROOT / replay.EVIDENCE_RELATIVE / "causal-commercial-evidence.zip"


class ComparatorReplayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.checkout = self.base / "another-checkout"
        self.checkout.mkdir()
        for name in [*replay.SOURCE_HASHES, replay.STRUCTURED_FILE]:
            target = self.checkout / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.members, _ = replay.load_evidence(ARCHIVE)
        _, self.cases = replay.verify_sources(self.checkout)

    def changed_json(self, name, change):
        members = self.members.copy()
        value = json.loads(members[name])
        change(value)
        members[name] = json.dumps(value).encode()
        return members

    def test_actual_different_checkout_regrade_with_python_no_site_packages(self):
        launcher = self.checkout / "tools/replay_convergence_comparators.py"
        shutil.copyfile(ROOT / "tools/replay_convergence_comparators.py", launcher)
        output = self.base / "portable-regrade"
        result = subprocess.run([sys.executable, "-S", str(launcher), "--checkout", str(self.checkout),
                                 "--evidence", str(ARCHIVE), "--output", str(output)],
                                cwd=self.base, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertFalse(receipt["sdk_executed"])
        self.assertEqual(receipt["retained_output_regrade"]["target_outputs_regraded"], 92)
        self.assertEqual(receipt["retained_output_regrade"]["phoenix_scores_recomputed"], 184)
        self.assertEqual(receipt["retained_output_regrade"]["langsmith_scores_recomputed"], 184)
        self.assertEqual(replay.digest(ARCHIVE.read_bytes()), replay.ARCHIVE_SHA256)
        self.assertEqual(json.loads((output / "replay-freeze.json").read_text())["checkout"], str(self.checkout))

    def test_extracted_readonly_evidence_supported_without_modification(self):
        evidence = self.base / "original-extracted"
        evidence.mkdir()
        for name, raw in self.members.items():
            (evidence / name).write_bytes(raw)
            (evidence / name).chmod(0o400)
        evidence.chmod(0o500)
        self.addCleanup(evidence.chmod, 0o700)
        receipt = replay.replay(self.checkout, evidence, self.base / "new-regrade")
        self.assertEqual(receipt["status"], "COMPLETED")
        self.assertEqual({p.name: p.read_bytes() for p in evidence.iterdir()}, self.members)
        with self.assertRaisesRegex(ValueError, "overlaps original evidence"):
            replay.replay(self.checkout, evidence, evidence / "overwrite", execute_sdk=True)

    def test_archive_tamper_rejected(self):
        path = self.base / "bad.zip"
        path.write_bytes(ARCHIVE.read_bytes() + b"changed")
        with self.assertRaisesRegex(ValueError, "archive identity"):
            replay.load_evidence(path)

    def test_script_edit_with_self_rehashed_manifest_rejected(self):
        members = self.members.copy()
        members["local_sdk_probe.py"] = members["local_sdk_probe.py"].replace(replay.ORIGINAL_ROOT.encode(), b"/elsewhere")
        manifest = json.loads(members["evidence-manifest.json"])
        entry = next(r for r in manifest["files"] if r["path"] == "local_sdk_probe.py")
        entry.update(bytes=len(members[entry["path"]]), sha256=hashlib.sha256(members[entry["path"]]).hexdigest())
        members["evidence-manifest.json"] = json.dumps(manifest).encode()
        with self.assertRaisesRegex(ValueError, "manifest identity"):
            replay.verify_members(members)

    def test_unchanged_manifest_does_not_hide_member_tampering(self):
        members = self.members.copy()
        members["local-sdk-protocol.json"] += b" "
        with self.assertRaisesRegex(ValueError, "member identity"):
            replay.verify_members(members)

    def test_source_drift_rejected(self):
        (self.checkout / replay.CASE_FILE).write_bytes(b"{}")
        with self.assertRaisesRegex(ValueError, "source identity"):
            replay.verify_sources(self.checkout)

    def test_source_symlink_escape_rejected_even_for_identical_bytes(self):
        source = self.checkout / replay.CASE_FILE
        raw = source.read_bytes()
        outside = self.base / "same-source.json"
        outside.write_bytes(raw)
        source.unlink()
        source.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, "symlink"):
            replay.verify_sources(self.checkout)

    def test_incorrect_langsmith_grade_rejected(self):
        members = self.changed_json("langsmith-far.json", lambda v: v["rows"][0]["sdk_scores"].update(status_match=0))
        with self.assertRaisesRegex(ValueError, "incorrect LangSmith score"):
            replay.regrade(members, self.cases)

    def test_forged_reference_and_grade_cannot_replace_source_reference(self):
        def forge(value):
            value["rows"][0].update(reference="FORGED", status="FORGED")
        with self.assertRaisesRegex(ValueError, "source reference"):
            replay.regrade(self.changed_json("langsmith-far.json", forge), self.cases)

    def test_incorrect_phoenix_grade_rejected(self):
        members = self.changed_json("phoenix-scores.json", lambda v: v[0]["status_match_score"].update(score=0))
        with self.assertRaisesRegex(ValueError, "incorrect Phoenix score"):
            replay.regrade(members, self.cases)

    def test_duplicate_trial_rejected_even_with_expected_total(self):
        members = self.changed_json("langsmith-far.json", lambda v: v["rows"].__setitem__(1, copy.deepcopy(v["rows"][0])))
        with self.assertRaisesRegex(ValueError, "duplicate target trial"):
            replay.regrade(members, self.cases)

    def test_missing_trial_rejected(self):
        members = self.changed_json("langsmith-far.json", lambda v: v["rows"].pop())
        with self.assertRaisesRegex(ValueError, "missing target trials"):
            replay.regrade(members, self.cases)

    def test_duplicate_and_missing_phoenix_trials_rejected(self):
        for change in [lambda v: v.__setitem__(1, copy.deepcopy(v[0])), lambda v: v.pop()]:
            with self.subTest(change=change):
                with self.assertRaisesRegex(ValueError, "duplicate Phoenix|missing Phoenix"):
                    replay.regrade(self.changed_json("phoenix-scores.json", change), self.cases)

    def test_occupied_output_rejected_before_sdk_import_or_targets(self):
        output = self.base / "occupied"
        output.mkdir()
        sentinel = output / "retain.txt"
        sentinel.write_text("unchanged")
        with mock.patch.object(replay, "run_sdk") as sdk:
            with self.assertRaises(FileExistsError):
                replay.replay(self.checkout, ARCHIVE, output, execute_sdk=True)
            sdk.assert_not_called()
        self.assertEqual(sentinel.read_text(), "unchanged")
        with self.assertRaises(FileExistsError):
            replay.replay(self.checkout, ARCHIVE, output)

    def test_output_inside_archive_directory_rejected_before_sdk(self):
        with mock.patch.object(replay, "run_sdk") as sdk:
            with self.assertRaisesRegex(ValueError, "overlaps original evidence"):
                replay.replay(self.checkout, ARCHIVE, ARCHIVE.parent / "new-output", execute_sdk=True)
            sdk.assert_not_called()

    def test_output_symlink_and_symlink_parent_rejected(self):
        real = self.base / "real"
        real.mkdir()
        link = self.base / "linked"
        link.symlink_to(real, target_is_directory=True)
        for output in [link, link / "new"]:
            with self.subTest(output=output):
                with self.assertRaisesRegex(ValueError, "symlink"):
                    replay.replay(self.checkout, ARCHIVE, output, execute_sdk=True)

    def test_sdk_failure_retains_fresh_freeze_exception_and_partial_outputs(self):
        output = self.base / "failed-sdk"
        def fail(checkout, destination, members, cases, expected):
            self.assertTrue((destination / "replay-freeze.json").exists())
            (destination / "partial.json").write_text("partial retained")
            raise RuntimeError("exercised SDK failure")
        with mock.patch.object(replay, "run_sdk", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "exercised SDK failure"):
                replay.replay(self.checkout, ARCHIVE, output, execute_sdk=True)
        receipt = json.loads((output / "replay-receipt.json").read_text())
        self.assertEqual(receipt["status"], "FAILED")
        self.assertEqual(receipt["exception_type"], "RuntimeError")
        self.assertIn("partial.json", receipt["files"])
        self.assertIn("exercised SDK failure", (output / "failure-traceback.txt").read_text())

    def test_relocation_executes_original_module_bytes_with_fresh_here(self):
        output = self.base / "mapped-sdk"
        output.mkdir()
        expected_report, expected_rows = replay.regrade(self.members, self.cases)
        original = importlib.util.spec_from_file_location
        observed = {}
        def intercepted(name, path):
            spec = original(name, path)
            execute = spec.loader.exec_module
            def load(module):
                execute(module)
                def run():
                    observed.update(root=module.ROOT, here=module.HERE, file=Path(module.__file__))
                    self.assertEqual(replay.digest(Path(module.__file__).read_bytes()), replay.SCRIPT_SHA256)
                    for member in ["langsmith-far.json", "langsmith-sympy.json", "phoenix-scores.json", "local-sdk-results.json"]:
                        (module.HERE / member).write_bytes(self.members[member])
                module.run = run
            spec.loader.exec_module = load
            return spec
        with mock.patch.object(replay.importlib.metadata, "version", side_effect=replay.VERSIONS.__getitem__), \
             mock.patch.object(replay.importlib.util, "spec_from_file_location", side_effect=intercepted):
            result = replay.run_sdk(self.checkout, output, self.members, self.cases, expected_rows)
        self.assertEqual(result, expected_report)
        self.assertEqual(observed["root"], self.checkout)
        self.assertEqual(observed["here"], output / "sdk-output")
        self.assertNotEqual(observed["here"], observed["file"].parent)


if __name__ == "__main__":
    unittest.main()
