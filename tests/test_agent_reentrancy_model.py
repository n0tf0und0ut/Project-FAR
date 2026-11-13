"""Bounded exhaustive transition-model check independent of runtime code.

Explores every valid two-identity event history up to six events. It is not a
proof of arbitrary liveness, model/implementation correspondence, or I3 review.
"""
from __future__ import annotations

import itertools
import unittest
from typing import NamedTuple


class State(NamedTuple):
    active: tuple[int, int] = (0, 0)
    denied: tuple[int, int] = (0, 0)


EVENTS = (('enter', 0), ('leave', 0), ('enter', 1), ('leave', 1))


def transition(state: State, event: tuple[str, int], *, guarded: bool) -> State | None:
    operation, task = event
    active, denied = list(state.active), list(state.denied)
    if operation == 'enter':
        if guarded and active[task]:
            denied[task] += 1
        else:
            active[task] += 1
    elif operation == 'leave':
        if not active[task]:
            return None
        active[task] -= 1
    else:
        raise ValueError(f'unsupported event: {operation}')
    return State(tuple(active), tuple(denied))


def execute(events: tuple[tuple[str, int], ...], guarded: bool) -> tuple[State, ...] | None:
    states = [State()]
    for event in events:
        next_state = transition(states[-1], event, guarded=guarded)
        if next_state is None:
            return None
        states.append(next_state)
    return tuple(states)


class BoundedSafetyModel(unittest.TestCase):
    def test_all_valid_histories_and_baseline_counterexample(self):
        checked = 0
        witness = None
        for length in range(7):
            for events in itertools.product(EVENTS, repeat=length):
                safe = execute(events, True)
                if safe is not None:
                    checked += 1
                    self.assertTrue(all(max(state.active) <= 1 for state in safe))
                baseline = execute(events, False)
                if witness is None and baseline is not None and any(
                    max(state.active) > 1 for state in baseline
                ):
                    witness = events
        self.assertEqual(checked, 873)
        self.assertEqual(witness, (('enter', 0), ('enter', 0)))

    def test_deny_preserves_active_task_and_sequential_start_recovers(self):
        self.assertEqual(execute((('enter', 0), ('enter', 0)), True)[-1],
                         State((1, 0), (1, 0)))
        self.assertEqual(execute((('enter', 0), ('enter', 0), ('leave', 0),
                                  ('enter', 0)), True)[-1], State((1, 0), (1, 0)))

    def test_independent_task_does_not_interfere(self):
        self.assertEqual(execute((('enter', 0), ('enter', 1)), True)[-1],
                         State((1, 1), (0, 0)))


if __name__ == '__main__':
    unittest.main()
