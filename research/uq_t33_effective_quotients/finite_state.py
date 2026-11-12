"""UQ-T33 finite deterministic Moore-machine quotient algorithm and regressions."""
from itertools import product
import unittest


def canonical(labels):
    index = {}
    return tuple(index.setdefault(value, len(index)) for value in labels)


def quotient(outputs, transitions):
    """Compute exact observational classes and strict refinement count.

    States are 0..n-1; transitions[state][action] is the next state.
    Outputs have decidable equality; transitions are fully known and total.
    """
    n = len(outputs)
    if n == 0 or len(transitions) != n:
        raise ValueError("nonempty state set and one transition row per state required")
    actions = len(transitions[0])
    if any(len(row) != actions or any(type(s) is not int or s < 0 or s >= n for s in row)
           for row in transitions):
        raise ValueError("invalid transition table")
    labels = canonical(outputs)
    rounds = 0
    while True:
        updated = canonical((outputs[x], tuple(labels[s] for s in transitions[x]))
                            for x in range(n))
        if updated == labels:
            return labels, rounds
        assert len(set(updated)) > len(set(labels))
        labels = updated
        rounds += 1
        assert rounds <= max(n - 2, 0)


def observation(outputs, transitions, state, word):
    for action in word:
        state = transitions[state][action]
    return outputs[state]


def bounded_partition(outputs, transitions, depth):
    n, actions = len(outputs), len(transitions[0])
    signatures = [[] for _ in range(n)]
    for length in range(depth + 1):
        for word in product(range(actions), repeat=length):
            for state in range(n):
                signatures[state].append(observation(outputs, transitions, state, word))
    return canonical(tuple(signature) for signature in signatures)


def black_box_equivalent(observe, first, second, actions, certified_max_states):
    """Exact equality of infinite-word behavior under a *trusted* finite-state cap.

    The caller must externally certify a deterministic Moore model with
    at most certified_max_states reachable states and reliable reset access.
    No finite observations can verify this premise by themselves.
    """
    if type(actions) is not int or actions < 0 or type(certified_max_states) is not int or certified_max_states < 1:
        raise ValueError("valid alphabet size and certified positive state bound required")
    for length in range(max(certified_max_states - 2, 0) + 1):
        for word in product(range(actions), repeat=length):
            if observe(first, word) != observe(second, word):
                return False
    return True


class FiniteStateQuotientTests(unittest.TestCase):
    def test_all_binary_one_action_machines_up_to_four_states(self):
        for n in range(1, 5):
            for outputs in product((0, 1), repeat=n):
                for next_states in product(range(n), repeat=n):
                    trans = tuple((s,) for s in next_states)
                    labels, rounds = quotient(outputs, trans)
                    self.assertEqual(labels, bounded_partition(outputs, trans, max(n - 2, 0)))
                    self.assertLessEqual(rounds, max(n - 2, 0))

    def test_all_binary_two_action_machines_up_to_three_states(self):
        for n in range(1, 4):
            for outputs in product((0, 1), repeat=n):
                for dests in product(range(n), repeat=2 * n):
                    trans = tuple(dests[2 * x:2 * x + 2] for x in range(n))
                    self.assertEqual(quotient(outputs, trans)[0],
                                     bounded_partition(outputs, trans, max(n - 2, 0)))

    def test_sharp_chain_requires_n_minus_two_actions(self):
        for n in range(2, 10):
            outputs = tuple(int(x == n - 1) for x in range(n))
            trans = tuple((min(x + 1, n - 1),) for x in range(n))
            w = (0,) * (n - 2)
            self.assertNotEqual(observation(outputs, trans, 0, w),
                                observation(outputs, trans, 1, w))
            if n > 2:
                short = (0,) * (n - 3)
                self.assertEqual(observation(outputs, trans, 0, short),
                                 observation(outputs, trans, 1, short))
            labels, rounds = quotient(outputs, trans)
            self.assertEqual(len(set(labels)), n)
            self.assertEqual(rounds, n - 2)

    def test_constant_output_remains_one_class(self):
        for n in range(1, 10):
            outputs = (0,) * n
            trans = tuple((min(x + 1, n - 1),) for x in range(n))
            self.assertEqual(quotient(outputs, trans), ((0,) * n, 0))

    def test_certified_black_box_bound_matches_complete_quotient(self):
        for n in range(1, 4):
            for outputs in product((0, 1), repeat=n):
                for dests in product(range(n), repeat=2 * n):
                    trans = tuple(dests[2 * x:2 * x + 2] for x in range(n))
                    labels, _ = quotient(outputs, trans)
                    observe = lambda state, word: observation(outputs, trans, state, word)
                    for x in range(n):
                        for y in range(n):
                            self.assertEqual(black_box_equivalent(observe, x, y, 2, n),
                                             labels[x] == labels[y])

    def test_unknown_state_bound_can_hide_later_distinction(self):
        for observed_horizon in range(0, 12):
            # A state cap underquoted to observed_horizon+2 misses the
            # chain's first difference at word length observed_horizon+1.
            n = observed_horizon + 3
            outputs = tuple(int(x == n - 1) for x in range(n))
            trans = tuple((min(x + 1, n - 1),) for x in range(n))
            observe = lambda state, word: observation(outputs, trans, state, word)
            self.assertTrue(black_box_equivalent(observe, 0, 1, 1, n - 1))
            self.assertFalse(black_box_equivalent(observe, 0, 1, 1, n))

    def test_invalid_tables_fail(self):
        for outputs, transitions in (((), ()), ((0, 1), ((0,),)),
                                     ((0, 1), ((1,), (2,))),
                                     ((0, 1), ((0,), (0, 1)))):
            with self.assertRaises(ValueError):
                quotient(outputs, transitions)


if __name__ == "__main__":
    unittest.main()
