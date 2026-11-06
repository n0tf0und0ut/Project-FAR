"""Adversarial tests for the Research-only weight-space evidence gate."""
import copy
import hashlib
import json
import tempfile
import tracemalloc
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.weight_space_research import EvidenceError, analyze, audit_safetensors


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        base = "a" * 64
        edited = "b" * 64
        sham = "e" * 64
        self.manifest = {
            "schema": "far-wsp/v0.1", "status": "Research",
            "checkpoint": {"base_sha256": base, "sham_sha256": sham, "edited_sha256": edited},
            "suite_sha256": "c" * 64, "source_sha256": "d" * 64,
            "arms": ["base", "prompt_fix", "decode_fix", "sham_edit", "weight_edit"],
            "slots": [{"case_id": "L01", "seed": 0, "family": "loops"},
                      {"case_id": "M01", "seed": 1, "family": "arithmetic"}],
            "observations": [],
        }
        for case, seed in [("L01", 0), ("M01", 1)]:
            for arm in self.manifest["arms"]:
                key = f"{case}_{seed}_{arm}"
                trace = f"actual transcript for {key}".encode()
                success = arm == "weight_edit" or (arm == "prompt_fix" and case == "M01")
                grade = {"correct": success, "completed": success, "unsafe_action": False,
                         "output_tokens": 20, "elapsed_ms": 100,
                         "failure_category": "none" if success else "reasoning_loop"}
                grade_bytes = json.dumps(grade).encode()
                (self.root / f"{key}.txt").write_bytes(trace)
                (self.root / f"{key}.json").write_bytes(grade_bytes)
                self.manifest["observations"].append({
                    "case_id": case, "seed": seed, "arm": arm,
                    "checkpoint_sha256": edited if arm == "weight_edit" else sham if arm == "sham_edit" else base,
                    "trace_path": f"{key}.txt", "trace_sha256": sha(trace),
                    "grade_path": f"{key}.json", "grade_sha256": sha(grade_bytes),
                })

    def test_complete_paired_cohort_counts(self):
        r = analyze(self.manifest, self.root)
        self.assertEqual(r["observations"], 10)
        self.assertEqual(r["arms"]["weight_edit"]["success"], 2)
        self.assertTrue(r["internal_screen_pass"])
        self.assertEqual(r["paired_vs_weight_edit"]["prompt_fix"]["paired_success_difference"], .5)

    def test_identical_safetensors_sham_roundtrip_is_a_valid_complete_campaign(self):
        try:
            import torch
            from safetensors.torch import load_file, save_file
        except ImportError:
            self.skipTest("optional local checkpoint dependencies not installed")
        base, sham, edited = (self.root / arm for arm in ("base", "sham", "edited"))
        for path in (base, sham, edited):
            path.mkdir()
        original = torch.zeros((10, 10))
        candidate = original.clone()
        candidate[0, 0] = 1
        save_file({"target": original}, str(base / "weights.safetensors"))
        save_file(load_file(str(base / "weights.safetensors")), str(sham / "weights.safetensors"))
        save_file({"target": candidate}, str(edited / "weights.safetensors"))
        self.assertEqual((base / "weights.safetensors").read_bytes(),
                         (sham / "weights.safetensors").read_bytes())
        base_audit = audit_safetensors(base, edited, {"target"}, .1)
        sham_audit = audit_safetensors(sham, edited, {"target"}, .1)
        self.assertEqual(base_audit["base_sha256"], sham_audit["base_sha256"])
        identities = self.manifest["checkpoint"]
        identities.update(base_sha256=base_audit["base_sha256"],
                          sham_sha256=sham_audit["base_sha256"],
                          edited_sha256=base_audit["edited_sha256"])
        for obs in self.manifest["observations"]:
            obs["checkpoint_sha256"] = identities[
                "edited_sha256" if obs["arm"] == "weight_edit" else
                "sham_sha256" if obs["arm"] == "sham_edit" else "base_sha256"]
        report = analyze(self.manifest, self.root)
        self.assertEqual(report["observations"], 10)
        self.assertTrue(report["internal_screen_pass"])

    def test_edited_checkpoint_must_differ_from_each_control(self):
        for control in ("base_sha256", "sham_sha256"):
            with self.subTest(control=control):
                manifest = copy.deepcopy(self.manifest)
                manifest["checkpoint"]["edited_sha256"] = manifest["checkpoint"][control]
                with self.assertRaisesRegex(EvidenceError, "distinct digest"):
                    analyze(manifest, self.root)

    def test_missing_slot_fails_closed(self):
        self.manifest["observations"].pop()
        with self.assertRaisesRegex(EvidenceError, "incomplete"):
            analyze(self.manifest, self.root)

    def test_duplicate_fails_closed(self):
        self.manifest["observations"].append(copy.deepcopy(self.manifest["observations"][0]))
        with self.assertRaisesRegex(EvidenceError, "duplicate"):
            analyze(self.manifest, self.root)

    def test_tampered_trace_fails(self):
        (self.root / self.manifest["observations"][0]["trace_path"]).write_text("tamper")
        with self.assertRaisesRegex(EvidenceError, "digest-mismatched"):
            analyze(self.manifest, self.root)

    def test_wrong_checkpoint_arm_fails(self):
        self.manifest["observations"][0]["checkpoint_sha256"] = "b" * 64
        with self.assertRaisesRegex(EvidenceError, "checkpoint identity"):
            analyze(self.manifest, self.root)

    def test_extraneous_or_replaced_slot_fails(self):
        self.manifest["observations"][0]["case_id"] = "surrogate"
        with self.assertRaisesRegex(EvidenceError, "extra"):
            analyze(self.manifest, self.root)

    def test_path_traversal_fails(self):
        self.manifest["observations"][0]["trace_path"] = "../outside"
        with self.assertRaises((EvidenceError, FileNotFoundError)):
            analyze(self.manifest, self.root)

    def test_symlink_escape_fails(self):
        outside = self.root.parent / (self.root.name + "-other")
        outside.write_bytes(b"outside")
        self.addCleanup(outside.unlink)
        (self.root / "escape").symlink_to(outside)
        obs = self.manifest["observations"][0]
        obs["trace_path"] = "escape"
        obs["trace_sha256"] = sha(b"outside")
        with self.assertRaisesRegex(EvidenceError, "escapes"):
            analyze(self.manifest, self.root)

    def test_grade_is_not_a_self_attested_success(self):
        obs = self.manifest["observations"][0]
        path = self.root / obs["grade_path"]
        grade = json.loads(path.read_text())
        grade["success"] = True
        raw = json.dumps(grade).encode()
        path.write_bytes(raw)
        obs["grade_sha256"] = sha(raw)
        with self.assertRaisesRegex(EvidenceError, "grade schema"):
            analyze(self.manifest, self.root)

    def test_contradictory_grade_fails(self):
        obs = self.manifest["observations"][0]
        path = self.root / obs["grade_path"]
        grade = json.loads(path.read_text())
        grade["failure_category"] = "none"
        raw = json.dumps(grade).encode()
        path.write_bytes(raw)
        obs["grade_sha256"] = sha(raw)
        with self.assertRaisesRegex(EvidenceError, "contradiction"):
            analyze(self.manifest, self.root)

    def test_duplicate_grade_key_fails_closed(self):
        obs = self.manifest["observations"][0]
        path = self.root / obs["grade_path"]
        raw = path.read_bytes().replace(b'"correct": false',
                                       b'"correct": true, "correct": false')
        path.write_bytes(raw)
        obs["grade_sha256"] = sha(raw)
        with self.assertRaisesRegex(EvidenceError, "duplicate JSON key"):
            analyze(self.manifest, self.root)

    def test_boolean_seed_cannot_alias_registered_integer(self):
        self.manifest["observations"][0]["seed"] = False
        with self.assertRaisesRegex(EvidenceError, "types"):
            analyze(self.manifest, self.root)

    def test_nonfinite_grade_is_rejected(self):
        obs = self.manifest["observations"][0]
        path = self.root / obs["grade_path"]
        raw = path.read_bytes().replace(b'100', b'NaN')
        path.write_bytes(raw)
        obs["grade_sha256"] = sha(raw)
        with self.assertRaisesRegex(EvidenceError, "non-finite"):
            analyze(self.manifest, self.root)

    def test_cannot_claim_improvement_when_simple_fix_is_stronger(self):
        obs = next(o for o in self.manifest["observations"] if o["arm"] == "weight_edit" and o["case_id"] == "L01")
        path = self.root / obs["grade_path"]
        grade = json.loads(path.read_text())
        grade.update(correct=False, completed=False, failure_category="reasoning_loop")
        raw = json.dumps(grade).encode()
        path.write_bytes(raw)
        obs["grade_sha256"] = sha(raw)
        report = analyze(self.manifest, self.root)
        self.assertFalse(report["internal_screen_pass"])


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        try:
            import torch  # noqa: F401
            from safetensors.torch import save_file  # noqa: F401
        except ImportError:
            self.skipTest("optional local checkpoint dependencies not installed")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.base = self.root / "base"
        self.edit = self.root / "edited"
        self.base.mkdir()
        self.edit.mkdir()
        from safetensors.torch import save_file
        import torch
        self.base_tensor = {"target": torch.zeros((2, 4)), "protect": torch.ones((4,))}
        self.edit_tensor = {k: v.clone() for k, v in self.base_tensor.items()}
        self.edit_tensor["target"][0, 0] = 1.0
        save_file(self.base_tensor, str(self.base / "weights.safetensors"))
        save_file(self.edit_tensor, str(self.edit / "weights.safetensors"))
        (self.base / "config.json").write_text("{}")
        (self.edit / "config.json").write_text("{}")

    def test_exact_sparse_change_count(self):
        result = audit_safetensors(self.base, self.edit, {"target"}, .10)
        self.assertEqual(result["total_parameters"], 12)
        self.assertEqual(result["changed_parameters"], 1)
        self.assertNotEqual(result["base_sha256"], result["edited_sha256"])
        self.assertAlmostEqual(result["changed_fraction"], 1 / 12)

    def test_scalar_tensor_is_a_valid_bounded_checkpoint_coordinate(self):
        import torch
        from safetensors.torch import save_file
        save_file({"scalar": torch.tensor(1.0), "guard": torch.ones(9)},
                  str(self.base / "weights.safetensors"))
        save_file({"scalar": torch.tensor(2.0), "guard": torch.ones(9)},
                  str(self.edit / "weights.safetensors"))
        result = audit_safetensors(self.base, self.edit, {"scalar"}, .2)
        self.assertEqual(result["total_parameters"], 10)
        self.assertEqual(result["changed_parameters"], 1)
        self.assertEqual(result["touched_tensors"], ["scalar"])

    def test_empty_tensor_dtype_is_checked_without_value_chunks(self):
        import torch
        from safetensors.torch import save_file
        original = torch.zeros(100)
        candidate = original.clone()
        candidate[0] = 1
        for shape in ((0, 2), (0, 0), (0, 2, 3), (2, 0), (0,)):
            with self.subTest(shape=shape):
                save_file({"target": original, "empty": torch.empty(shape, dtype=torch.float32)},
                          str(self.base / "weights.safetensors"))
                save_file({"target": candidate, "empty": torch.empty(shape, dtype=torch.float32)},
                          str(self.edit / "weights.safetensors"))
                result = audit_safetensors(self.base, self.edit, {"target"}, .10)
                self.assertEqual((result["total_parameters"], result["changed_parameters"]), (100, 1))
                save_file({"target": candidate, "empty": torch.empty(shape, dtype=torch.float64)},
                          str(self.edit / "weights.safetensors"))
                with self.assertRaisesRegex(EvidenceError, "tensor dtype changed: empty"):
                    audit_safetensors(self.base, self.edit, {"target"}, .10)

    def test_float8_sparse_edits_enforce_finiteness_and_changed_budget(self):
        import torch
        from safetensors.torch import save_file
        for dtype in (torch.float8_e4m3fn, torch.float8_e5m2):
            with self.subTest(dtype=dtype):
                original = torch.zeros((10, 10))
                candidate = original.clone()
                candidate[0, 0] = 1
                save_file({"target": original.to(dtype)}, str(self.base / "weights.safetensors"))
                save_file({"target": candidate.to(dtype)}, str(self.edit / "weights.safetensors"))
                result = audit_safetensors(self.base, self.edit, {"target"}, .10)
                self.assertEqual(result["total_parameters"], 100)
                self.assertEqual(result["changed_parameters"], 1)
                self.assertEqual(result["changed_fraction"], .01)
                with self.assertRaisesRegex(EvidenceError, "budget"):
                    audit_safetensors(self.base, self.edit, {"target"}, .005)
                for side in (self.base, self.edit):
                    finite = original if side == self.base else candidate
                    for invalid in (float("nan"), float("inf")):
                        with self.subTest(side=side.name, invalid=invalid):
                            nonfinite = finite.clone()
                            nonfinite[0, 1] = invalid
                            save_file({"target": nonfinite.to(dtype)}, str(side / "weights.safetensors"))
                            with self.assertRaisesRegex(EvidenceError, "non-finite"):
                                audit_safetensors(self.base, self.edit, {"target"}, .10)
                        save_file({"target": finite.to(dtype)}, str(side / "weights.safetensors"))

    def test_finite_float64_values_are_not_overflowed_by_finiteness_conversion(self):
        import torch
        from safetensors.torch import save_file
        original = torch.full((10, 10), 1e300, dtype=torch.float64)
        candidate = original.clone()
        candidate[0, 0] = 2e300
        save_file({"target": original}, str(self.base / "weights.safetensors"))
        save_file({"target": candidate}, str(self.edit / "weights.safetensors"))
        self.assertEqual(audit_safetensors(self.base, self.edit, {"target"}, .10)["changed_parameters"], 1)

    def test_large_nonweight_artifact_has_bounded_python_memory(self):
        # File creation precedes tracing; the audit must never materialize this
        # 32 MiB asset. tracemalloc detects the original Path.read_bytes defect.
        for directory in (self.base, self.edit):
            with (directory / "pytorch_model.bin").open("wb") as handle:
                for _ in range(32):
                    handle.write(b"x" * 1024 * 1024)
        tracemalloc.start()
        try:
            result = audit_safetensors(self.base, self.edit, {"target"}, .10)
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertEqual(result["changed_parameters"], 1)
        self.assertLess(peak, 8 * 1024 * 1024, f"unbounded auxiliary-file allocation: {peak}")
        with (self.edit / "pytorch_model.bin").open("r+b") as handle:
            handle.seek(-1, 2)
            handle.write(b"y")
        with self.assertRaisesRegex(EvidenceError, "non-weight asset changed"):
            audit_safetensors(self.base, self.edit, {"target"}, .10)

    def test_nonweight_comparison_reads_only_bounded_blocks(self):
        for directory in (self.base, self.edit):
            (directory / "pytorch_model.bin").write_bytes(b"x" * (2 * 1024 * 1024 + 7))
        original_open, reads = Path.open, []
        test = self
        class BoundedReader:
            def __init__(self, handle):
                self.handle = handle
            def __enter__(self):
                self.handle.__enter__()
                return self
            def __exit__(self, *args):
                return self.handle.__exit__(*args)
            def read(self, amount=-1):
                test.assertGreater(amount, 0, "whole-file read of auxiliary checkpoint asset")
                test.assertLessEqual(amount, 1024 * 1024)
                reads.append(amount)
                return self.handle.read(amount)
        def bounded_open(path, *args, **kwargs):
            handle = original_open(path, *args, **kwargs)
            return BoundedReader(handle) if path.name == "pytorch_model.bin" else handle
        with patch.object(Path, "open", bounded_open):
            self.assertEqual(audit_safetensors(self.base, self.edit, {"target"}, .10)["changed_parameters"], 1)
        self.assertTrue(reads)

    def test_budget_failure(self):
        with self.assertRaisesRegex(EvidenceError, "budget"):
            audit_safetensors(self.base, self.edit, {"target"}, .01)

    def test_unapproved_tensor_mutation(self):
        with self.assertRaisesRegex(EvidenceError, "unapproved"):
            audit_safetensors(self.base, self.edit, {"protect"}, .99)

    def test_nonweight_change_fails(self):
        (self.edit / "config.json").write_text('{"special":true}')
        with self.assertRaisesRegex(EvidenceError, "non-weight"):
            audit_safetensors(self.base, self.edit, {"target"}, .9)


if __name__ == "__main__":
    unittest.main()
