"""Offline adversarial controls; these fixtures are not model observations."""
from __future__ import annotations

import copy
import unittest

try:
    import numpy as np
except ImportError:
    np = None

from tools.weight_space_edits import SCHEMA, apply_edit, canonical, sha, tensor_sha


@unittest.skipIf(np is None, "Optional NumPy research dependency is unavailable")
class WeightSpaceEditTests(unittest.TestCase):
    def setUp(self):
        self.original = np.arange(1, 13, dtype=np.float32).reshape(3, 4)
        self.policy = {
            "tensor": "model.layers.0.mlp.down_proj.weight",
            "shape": [3, 4], "dtype": "float32", "max_changed_parameters": 12,
            "max_relative_l2": 8.0, "allowed_operations": ["identity", "scale_columns", "project_columns", "sparse_replace"],
            "max_columns": 4,
        }

    def proposal(self, operation="identity", **fields):
        return {"schema": SCHEMA, "tensor": self.policy["tensor"],
                "base_tensor_sha256": tensor_sha(self.original),
                "operation": operation, **fields}

    def test_identity_copies_and_commits_no_changes(self):
        result, audit = apply_edit(self.original, self.proposal(), self.policy)
        self.assertFalse(np.shares_memory(result, self.original))
        self.assertEqual(audit["touched_parameters"], 0)
        self.assertEqual(audit["changed_parameters"], 0)
        self.assertEqual(audit["base_tensor_sha256"], audit["edited_tensor_sha256"])
        self.assertEqual(audit["changed_coordinates_sha256"], sha(canonical([])))

    def test_scaling_only_changes_selected_columns_and_original_is_immutable(self):
        before = self.original.tobytes()
        result, audit = apply_edit(self.original, self.proposal("scale_columns", columns=[1, 3], factor=0.5), self.policy)
        np.testing.assert_array_equal(result[:, [0, 2]], self.original[:, [0, 2]])
        np.testing.assert_array_equal(result[:, [1, 3]], self.original[:, [1, 3]] / 2)
        self.assertEqual(audit["touched_parameters"], 6)
        self.assertEqual(audit["changed_parameters"], 6)
        self.assertEqual(self.original.tobytes(), before)
        self.assertEqual(audit["changed_coordinates"], [[0, 1], [0, 3], [1, 1], [1, 3], [2, 1], [2, 3]])

    def test_projection_uses_unit_direction_and_strength(self):
        result, audit = apply_edit(self.original, self.proposal("project_columns", columns=[0], direction=[0, 6, 0], strength=1), self.policy)
        expected = self.original.copy()
        expected[1, 0] = 0
        np.testing.assert_array_equal(result, expected)
        self.assertEqual(audit["touched_parameters"], 3)
        self.assertEqual(audit["changed_parameters"], 1)
        # The reported MIT intervention strength6 is expressible, without implying replication.
        result, _ = apply_edit(self.original, self.proposal("project_columns", columns=[0], direction=[0, 6, 0], strength=6), self.policy)
        self.assertEqual(result[1, 0], -25)

    def test_float16_rounding_counts_actual_changes(self):
        self.original = np.array([[1.0, 100.0], [1.0, 1.0]], dtype=np.float16)
        self.policy.update(shape=[2, 2], dtype="float16", max_columns=2)
        result, audit = apply_edit(self.original, self.proposal("sparse_replace", indices=[[0, 0], [0, 1]], values=[1.00001, 100.2]), self.policy)
        self.assertEqual(audit["touched_parameters"], 2)
        self.assertEqual(audit["changed_parameters"], 1)
        self.assertEqual(result[0, 0], 1)

    def test_sparse_signed_zero_is_a_byte_change(self):
        self.original[0, 0] = 0
        result, audit = apply_edit(self.original, self.proposal("sparse_replace", indices=[[0, 0]], values=[-0.0]), self.policy)
        self.assertTrue(np.signbit(result[0, 0]))
        self.assertEqual(audit["changed_parameters"], 1)
        self.assertEqual(audit["numerical_changed_parameters"], 0)
        self.assertNotEqual(audit["base_tensor_sha256"], audit["edited_tensor_sha256"])

    def test_hash_binds_dtype_shape_byte_order_and_not_memory_layout(self):
        a = self.original.copy()
        self.assertEqual(tensor_sha(a), tensor_sha(np.asfortranarray(a)))
        self.assertNotEqual(tensor_sha(a), tensor_sha(a.astype(np.float64)))
        self.assertNotEqual(tensor_sha(a), tensor_sha(a.reshape(4, 3)))
        self.assertNotEqual(tensor_sha(a), tensor_sha(a.astype(">f4")))

    def test_forged_base_rejected(self):
        proposal = self.proposal("scale_columns", columns=[0], factor=2)
        proposal["base_tensor_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "commitment"):
            apply_edit(self.original, proposal, self.policy)

    def test_proposal_cannot_supply_or_override_policy(self):
        for key, value in [("policy", self.policy), ("max_changed_parameters", 1000), ("approval", True), ("python", "import os")]:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "fields"):
                apply_edit(self.original, {**self.proposal(), key: value}, self.policy)

    def test_operation_allowlist_and_tensor_identity_are_binding(self):
        policy = {**self.policy, "allowed_operations": ["identity"]}
        with self.assertRaisesRegex(ValueError, "not admitted"):
            apply_edit(self.original, self.proposal("scale_columns", columns=[0], factor=2), policy)
        for key, value in [("schema", "future"), ("tensor", "other")]:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "mismatch"):
                apply_edit(self.original, {**self.proposal(), key: value}, self.policy)

    def test_exact_fields_and_typed_policy_rejected(self):
        bads = [dict(self.policy, shape=[True, 4]), dict(self.policy, dtype="float64"),
                dict(self.policy, max_columns=True), dict(self.policy, max_changed_parameters=True),
                dict(self.policy, max_relative_l2=float("inf")), dict(self.policy, allowed_operations=["identity", "identity"]),
                dict(self.policy, allowed_operations=["exec"]), dict(self.policy, extra=1)]
        for policy in bads:
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                apply_edit(self.original, self.proposal(), policy)

    def test_boolean_duplicate_negative_and_oob_columns_rejected(self):
        for cols in ([True], [1, 1], [-1], [4], [], "0"):
            with self.subTest(cols=cols), self.assertRaises(ValueError):
                apply_edit(self.original, self.proposal("scale_columns", columns=cols, factor=1), self.policy)

    def test_nonfinite_or_out_of_bounds_arithmetic_rejected(self):
        for factor in [True, -1, 9, float("nan"), float("inf"), "2"]:
            with self.subTest(factor=factor), self.assertRaises(ValueError):
                apply_edit(self.original, self.proposal("scale_columns", columns=[0], factor=factor), self.policy)
        for direction in ([0, 0, 0], [1, 0], [True, 0, 1], [float("nan"), 0, 1]):
            with self.subTest(direction=direction), self.assertRaises(ValueError):
                apply_edit(self.original, self.proposal("project_columns", columns=[0], direction=direction, strength=1), self.policy)
        original = np.full((3, 4), 60000, dtype=np.float16)
        policy = {**self.policy, "dtype": "float16"}
        proposal = {**self.proposal("scale_columns", columns=[0], factor=8), "base_tensor_sha256": tensor_sha(original)}
        with self.assertRaises(ValueError):
            apply_edit(original, proposal, policy)

    def test_sparse_duplicates_bools_bounds_and_nonfinite_rejected(self):
        for indices, values in [([[0, 0], [0, 0]], [1, 2]), ([[True, 0]], [1]), ([[0, -1]], [1]),
                                ([[3, 0]], [1]), ([[0, 0]], [True]), ([[0, 0]], [float("inf")]),
                                ([[0, 0]], []), ([], []), ([[0, 0, 0]], [1])]:
            with self.subTest(indices=indices, values=values), self.assertRaises(ValueError):
                apply_edit(self.original, self.proposal("sparse_replace", indices=indices, values=values), self.policy)

    def test_actual_changed_parameter_and_column_budgets_fail_closed(self):
        proposal = self.proposal("scale_columns", columns=[0, 1], factor=2)
        for policy in [dict(self.policy, max_changed_parameters=5), dict(self.policy, max_columns=1),
                       dict(self.policy, max_relative_l2=0.001)]:
            with self.subTest(policy=policy), self.assertRaises(ValueError):
                apply_edit(self.original, proposal, policy)
        # Touched-but-unchanged locations do not consume an actual-change budget.
        _, audit = apply_edit(self.original, self.proposal("scale_columns", columns=[0], factor=1), dict(self.policy, max_changed_parameters=0))
        self.assertEqual(audit["changed_parameters"], 0)

    def test_sparse_column_budget_is_enforced(self):
        with self.assertRaisesRegex(ValueError, "column budget"):
            apply_edit(self.original, self.proposal("sparse_replace", indices=[[0, 0], [1, 1]], values=[10, 11]), dict(self.policy, max_columns=1))

    def test_rejected_edit_does_not_mutate_original_proposal_or_policy(self):
        proposal = self.proposal("scale_columns", columns=[0], factor=2)
        policy = dict(self.policy, max_changed_parameters=0)
        before = (self.original.tobytes(), copy.deepcopy(proposal), copy.deepcopy(policy))
        with self.assertRaises(ValueError):
            apply_edit(self.original, proposal, policy)
        self.assertEqual(before, (self.original.tobytes(), proposal, policy))

    def test_nonfinite_wrong_type_and_wrong_rank_arrays_rejected(self):
        for value in [np.array([[np.nan]]), np.array([[np.inf]]), np.array([[1]], dtype=int),
                      np.array([1.0]), np.array([[1j]]), [[1.0]], np.empty((0, 2))]:
            with self.subTest(value=type(value)), self.assertRaises(ValueError):
                tensor_sha(value)

    def test_zero_tensor_only_accepts_numerically_identical_edit(self):
        self.original[:] = 0
        _, audit = apply_edit(self.original, self.proposal(), self.policy)
        self.assertEqual(audit["relative_l2"], 0)
        with self.assertRaisesRegex(ValueError, "relative L2"):
            apply_edit(self.original, self.proposal("sparse_replace", indices=[[0, 0]], values=[1]), self.policy)

    def test_large_diff_uses_lossless_row_runs(self):
        self.original = np.ones((100, 100), dtype=np.float32)
        self.policy.update(shape=[100, 100], max_columns=100, max_changed_parameters=10000)
        _, audit = apply_edit(self.original, self.proposal("scale_columns", columns=list(range(100)), factor=2), self.policy)
        self.assertNotIn("changed_coordinates", audit)
        self.assertEqual(audit["changed_coordinate_row_runs"], [[r, 0, 100] for r in range(100)])
        coords = [[r, c] for r in range(100) for c in range(100)]
        self.assertEqual(audit["changed_coordinates_sha256"], sha(canonical(coords)))

    def test_ordinary_canonical_json_only(self):
        self.assertEqual(canonical({"b": 2, "a": [True, None, 1.0]}), b'{"a":[true,null,1.0],"b":2}')
        for value in [{1: "coerced"}, {"x": np.float32(1)}, (1, 2), {"x": float("nan")}, {"x": "\ud800"}]:
            with self.subTest(value=repr(value)), self.assertRaises(ValueError):
                canonical(value)


if __name__ == "__main__":
    unittest.main()
