#!/usr/bin/env python3
"""Finite observational-quotient experiments for Project FAR UQ-T33.

This code tests finite instances and illustrates an infinite-test undecidability
reduction; it does NOT establish undecidability by execution. That is deductive.
"""
from __future__ import annotations

from itertools import combinations
from random import Random
import json
import unittest
from pathlib import Path


def partition(rows: tuple[tuple[int, ...], ...], selected: tuple[int, ...]) -> tuple[int, ...]:
    """Canonical class index for each case, in first-appearance order.

    rows[t][x] is the exact outcome for test t on case x.
    """
    if not rows:
        if selected:
            raise IndexError("cannot select a nonexistent test")
        return ()
    n = len(rows[0])
    if any(len(row) != n for row in rows):
        raise ValueError("inconsistent case counts")
    names: dict[tuple[int, ...], int] = {}
    labels = []
    for x in range(n):
        sig = tuple(rows[t][x] for t in selected)
        if sig not in names:
            names[sig] = len(names)
        labels.append(names[sig])
    return tuple(labels)


def min_complete_basis(rows: tuple[tuple[int, ...], ...]) -> tuple[int, ...]:
    """Exhaustively minimize the number of tests preserving the full quotient."""
    if not rows:
        raise ValueError("provide at least one test row (possibly with zero cases)")
    goal = partition(rows, tuple(range(len(rows))))
    for size in range(len(rows) + 1):
        for selected in combinations(range(len(rows)), size):
            if partition(rows, selected) == goal:
                return selected
    raise AssertionError("all tests must yield the full quotient")


def greedy_complete_basis(rows: tuple[tuple[int, ...], ...]) -> tuple[int, ...]:
    """Build a <=k-1 basis when the entire FINITE test table is supplied.

    Uses the complete table to know which refinements are required. Its output
    does not certify unknown or unenumerated tests.
    """
    if not rows:
        raise ValueError("provide at least one test row")
    goal = partition(rows, tuple(range(len(rows))))
    goal_k = len(set(goal))
    selected: tuple[int, ...] = ()
    while partition(rows, selected) != goal:
        cur_k = len(set(partition(rows, selected)))
        for t in range(len(rows)):
            if t not in selected and len(set(partition(rows, selected + (t,)))) > cur_k:
                selected += (t,)
                break
        else:
            raise AssertionError("a proper coarsening must have a splitting test")
    assert len(selected) <= max(goal_k - 1, 0)
    return selected


def isolated_rows(n: int) -> tuple[tuple[int, ...], ...]:
    """Tightness example: n-1 tests, each isolates one case from a last all-zero case."""
    if n < 1:
        raise ValueError("n must be positive")
    return tuple(tuple(int(x == t) for x in range(n)) for t in range(n - 1))


def halted_within(program: tuple[tuple, ...], limit: int) -> bool:
    """Bounded two-counter register-machine simulator; total for every limit.

    Instructions: ('INC', register, next_pc); ('DECJZ', register, pos_pc,
    zero_pc); ('HALT',). Nonnegative counters, deterministic.
    """
    pc = 0
    regs = [0, 0]
    for _ in range(limit):
        ins = program[pc]
        if ins[0] == "HALT":
            return True
        if ins[0] == "INC":
            _, reg, next_pc = ins
            regs[reg] += 1
            pc = next_pc
        elif ins[0] == "DECJZ":
            _, reg, on_positive, on_zero = ins
            if regs[reg] > 0:
                regs[reg] -= 1
                pc = on_positive
            else:
                pc = on_zero
        else:
            raise ValueError("unknown opcode")
    return False


def halting_observation(program: tuple[tuple, ...], t: int, case: int) -> int:
    """rho(0)=rho(1)=0; beta(t, 0)=0; beta(t, 1)=halts_within(program,t)."""
    if case not in (0, 1):
        raise ValueError("case must be 0 or 1")
    return int(case == 1 and halted_within(program, t))


def delayed_halting_program(delay: int) -> tuple[tuple, ...]:
    return tuple(("INC", 0, i + 1) for i in range(delay)) + (("HALT",),)


class QuotientDiscoveryTests(unittest.TestCase):
    def test_all_binary_test_families_up_to_three_cases(self) -> None:
        # All subsets of all binary observation maps T_i : X -> {0,1}.
        # Include a constant dummy test to give an unambiguous base domain.
        for n in (1, 2, 3):
            possible = tuple(tuple((b >> x) & 1 for x in range(n)) for b in range(2**n))
            for mask in range(1 << len(possible)):
                rows = tuple(row for i, row in enumerate(possible) if mask & (1 << i))
                # Empty T is represented by a constant row: same quotient.
                if not rows:
                    rows = (tuple(0 for _ in range(n)),)
                selected = min_complete_basis(rows)
                k = len(set(partition(rows, tuple(range(len(rows))))))
                self.assertLessEqual(len(selected), max(k - 1, 0))
                self.assertEqual(partition(rows, selected), partition(rows, tuple(range(len(rows)))))

    def test_random_multivalued_families(self) -> None:
        rng = Random(7331)
        for n in range(2, 7):
            for _ in range(150):
                t = rng.randint(1, 8)
                rows = tuple(tuple(rng.randrange(4) for _ in range(n)) for _ in range(t))
                selected = min_complete_basis(rows)
                k = len(set(partition(rows, tuple(range(t)))))
                self.assertLessEqual(len(selected), k - 1)

    def test_exhaustive_four_case_binary_families_greedy(self) -> None:
        n = 4
        possible = tuple(tuple((b >> x) & 1 for x in range(n)) for b in range(2**n))
        for mask in range(1 << len(possible)):
            rows = tuple(row for i, row in enumerate(possible) if mask & (1 << i))
            if not rows:
                rows = (tuple(0 for _ in range(n)),)
            selected = greedy_complete_basis(rows)
            goal = partition(rows, tuple(range(len(rows))))
            self.assertEqual(partition(rows, selected), goal)
            self.assertLessEqual(len(selected), len(set(goal)) - 1)

    def test_bound_is_tight(self) -> None:
        for n in range(2, 10):
            rows = isolated_rows(n)
            self.assertEqual(len(min_complete_basis(rows)), n - 1)
            self.assertEqual(len(set(partition(rows, tuple(range(len(rows)))))), n)

    def test_no_finite_prefix_certifies_complete_infinite_behavior(self) -> None:
        # For every observed finite horizon H, exhibit an indistinguishable
        # prefix and a later separating observation for a valid finite program.
        diverging = (("INC", 0, 1), ("DECJZ", 0, 0, 0))
        for horizon in range(0, 25):
            delayed = delayed_halting_program(horizon + 1)
            for t in range(horizon + 1):
                self.assertEqual(halting_observation(delayed, t, 1), 0)
                self.assertEqual(halting_observation(diverging, t, 1), 0)
            later = horizon + 2
            self.assertEqual(halting_observation(delayed, later, 1), 1)
            self.assertEqual(halting_observation(delayed, later, 0), 0)
            self.assertEqual(halting_observation(diverging, later, 1), 0)

    def test_malformed_rows_rejected(self) -> None:
        with self.assertRaises(ValueError):
            min_complete_basis(((0, 1), (0, 1, 2)))


def results() -> dict:
    exhausted = sum(1 << (1 << n) for n in (1, 2, 3))
    examples = []
    for n in (2, 3, 4, 6):
        rows = isolated_rows(n)
        selected = min_complete_basis(rows)
        examples.append({"cases": n, "observational_classes": n,
                         "tests_available": n - 1, "minimum_basis_size": len(selected),
                         "bound": n - 1})
    horizon = 6
    delayed = delayed_halting_program(horizon + 1)
    example = {"tested_horizon": horizon,
               "all_prefix_tests_collide": all(halting_observation(delayed, t, 1) == 0
                                                for t in range(horizon + 1)),
               "later_separating_test": horizon + 2,
               "late_observation_1": halting_observation(delayed, horizon + 2, 1),
               "late_observation_0": halting_observation(delayed, horizon + 2, 0)}
    return {"status": "bounded_executable_corrob_only", "exhaustive_binary_test_families_n_1_through_4": exhausted + (1 << (1 << 4)),
            "tight_cases": examples, "finite_horizon_counterexample": example}


if __name__ == "__main__":
    import sys
    suite = unittest.TestLoader().loadTestsFromTestCase(QuotientDiscoveryTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        sys.exit(1)
    output = results()
    Path(__file__).with_name("results.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))
