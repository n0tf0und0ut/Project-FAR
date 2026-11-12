"""Bounded adversarial controls for FAR contract completeness (Research only).

Model checks are not general proofs or evidence that an externally chosen
behavioral contract captures the semantics of a live system.
"""
from __future__ import annotations
from itertools import product
import unittest


def complete(observation: tuple[int, ...], target: tuple[int, ...]) -> bool:
    if len(observation) != len(target):
        raise ValueError("different world domains")
    return all(
        observation[i] != observation[j] or target[i] == target[j]
        for i in range(len(observation)) for j in range(len(observation))
    )


def injective(observation: tuple[int, ...]) -> bool:
    return len(set(observation)) == len(observation)


def all_functions(n: int, codomain_size: int):
    return product(range(codomain_size), repeat=n)


class ContractCompletenessControls(unittest.TestCase):
    def test_exhaustive_sufficiency_decision(self):
        count = 0
        for n in range(5):
            for observation in all_functions(n, max(n, 1)):
                for target in all_functions(n, 2):
                    seen = {}
                    by_fibres = True
                    for o, y in zip(observation, target):
                        if o in seen and seen[o] != y:
                            by_fibres = False
                        seen[o] = y
                    self.assertEqual(complete(observation, target), by_fibres)
                    count += 1
        self.assertEqual(count, sum(max(n, 1)**n * 2**n for n in range(5)))

    def test_unrestricted_target_completeness_iff_injective(self):
        for n in range(5):
            for observation in all_functions(n, max(n, 1)):
                all_targets = all(complete(observation, target)
                                  for target in all_functions(n, 2))
                self.assertEqual(all_targets, injective(observation))

    def test_collision_admits_opposite_target_completions(self):
        for n in range(2, 5):
            identity = tuple(range(n))
            constant = tuple(0 for _ in range(n))
            for observation in all_functions(n, max(n, 1)):
                if injective(observation):
                    continue
                self.assertTrue(complete(observation, constant))
                self.assertFalse(complete(observation, identity))

    def test_partial_sample_cannot_certify_global_target(self):
        observation = (0, 0)
        good = (0, 0)
        bad = (0, 1)
        indices = (0,)
        self.assertEqual(tuple(good[i] for i in indices), tuple(bad[i] for i in indices))
        self.assertTrue(complete(observation, good))
        self.assertFalse(complete(observation, bad))

    def test_exact_model_identity_cannot_restore_hidden_world_bit(self):
        world = tuple(product((0, 1), repeat=2))
        encode = tuple(s[0] for s in world)
        world_target = tuple(s[1] for s in world)
        self.assertFalse(complete(encode, world_target))
        self.assertTrue(complete((0, 1), (0, 1)))

    def test_reference_bridge_under_explicit_correspondence(self):
        for n in range(5):
            for observation in all_functions(n, 2):
                for reference in all_functions(n, 2):
                    if not complete(observation, reference):
                        continue
                    for readout in all_functions(2, 2):
                        target = tuple(readout[z] for z in reference)
                        self.assertTrue(complete(observation, target))

    def test_marginal_completeness_is_not_joint_completeness(self):
        correlated = {(0, 0): 0.5, (0, 1): 0, (1, 0): 0, (1, 1): 0.5}
        independent = {(a, b): 0.25 for a, b in product((0, 1), repeat=2)}
        def marginal(p):
            return (sum(v for (a, _), v in p.items() if a == 1),
                    sum(v for (_, b), v in p.items() if b == 1))
        self.assertEqual(marginal(correlated), marginal(independent))
        self.assertNotEqual(correlated, independent)

    def test_injectivity_sufficient_for_all_targets_but_not_minimal(self):
        obs = tuple(range(4))
        self.assertTrue(all(complete(obs, target) for target in all_functions(4, 2)))
        constant = (0, 0, 0, 0)
        self.assertTrue(complete(constant, constant))
        self.assertGreater(len(set(obs)), len(set(constant)))


def epistemic_status(observation, possible_targets):
    if not possible_targets:
        return "INCONSISTENT"
    verdicts = {complete(observation, target) for target in possible_targets}
    if verdicts == {True}:
        return "CERTIFIED"
    if verdicts == {False}:
        return "REFUTED"
    return "UNDERDETERMINED"


class VersionSpaceAudit(unittest.TestCase):
    def test_all_small_world_version_spaces(self):
        count = 0
        for n in range(5):
            for observation in product(range(2), repeat=n):
                for mask in range(1 << n):
                    sampled = {i for i in range(n) if mask & (1 << i)}
                    for actual in product(range(2), repeat=n):
                        possible = [
                            target for target in product(range(2), repeat=n)
                            if all(target[i] == actual[i] for i in sampled)
                        ]
                        status = epistemic_status(observation, possible)
                        verdicts = {complete(observation, target) for target in possible}
                        self.assertEqual(status == "UNDERDETERMINED", len(verdicts) == 2)
                        self.assertEqual(status == "CERTIFIED", verdicts == {True})
                        self.assertEqual(status == "REFUTED", verdicts == {False})
                        count += 1
        self.assertEqual(count, sum(8**n for n in range(5)))

    def test_missing_any_nonsingleton_fiber_point_blocks_yes(self):
        count = 0
        for n in range(2, 6):
            for observation in product(range(2), repeat=n):
                for mask in range(1 << n):
                    sampled = {i for i in range(n) if mask & (1 << i)}
                    missing = [
                        i for i in range(n) if i not in sampled
                        and any(j != i and observation[j] == observation[i]
                                for j in range(n))
                    ]
                    if missing:
                        omitted = missing[0]
                        good = (0,) * n
                        bad = tuple(int(i == omitted) for i in range(n))
                        self.assertTrue(all(good[i] == bad[i] for i in sampled))
                        self.assertTrue(complete(observation, good))
                        self.assertFalse(complete(observation, bad))
                    count += 1
        self.assertEqual(count, sum(4**n for n in range(2, 6)))

    def test_covered_nonsingleton_fibers_certify_yes(self):
        count = 0
        for n in range(5):
            for observation in product(range(2), repeat=n):
                relevant = {
                    i for i in range(n)
                    if any(j != i and observation[j] == observation[i] for j in range(n))
                }
                for mask in range(1 << n):
                    sampled = {i for i in range(n) if mask & (1 << i)}
                    if not relevant.issubset(sampled):
                        continue
                    for target in product(range(2), repeat=n):
                        pairs_agree = all(
                            observation[i] != observation[j] or target[i] == target[j]
                            for i in sampled for j in sampled
                        )
                        if pairs_agree:
                            self.assertTrue(complete(observation, target))
                        count += 1
        self.assertGreater(count, 0)

    def test_empty_version_space_is_not_justified_certified(self):
        observation = (0, 0)
        samples = [(0, 0), (0, 1)]
        possible = [
            f for f in product(range(2), repeat=2)
            if all(f[i] == value for i, value in samples)
        ]
        self.assertFalse(possible)
        self.assertEqual(epistemic_status(observation, possible), "INCONSISTENT")
        self.assertTrue(all(complete(observation, f) for f in possible))
        self.assertTrue(all(not complete(observation, f) for f in possible))

    def test_false_hypothesis_class_creates_false_confidence(self):
        observation = (0, 0)
        possible = [(0, 0), (1, 1)]  # Assumed, not independently justified.
        self.assertEqual(epistemic_status(observation, possible), "CERTIFIED")
        actual = (0, 1)
        self.assertNotIn(actual, possible)
        self.assertFalse(complete(observation, actual))


if __name__ == "__main__":
    unittest.main()
