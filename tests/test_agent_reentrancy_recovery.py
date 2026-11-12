"""Frozen same-task recursion controls from the prospective research protocol.

The first test must fail against the pinned, unmodified main orchestrator.
These are deterministic executed callback tests, not live model trials.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from tools import subagent_orchestration as sub

ROOT = Path(__file__).resolve().parents[1]
SKILL = '.claude/skills/far-research-orchestrator/SKILL.md'


def environment(callback):
    agent = sub.AgentSpec(
        agent_id='coordinator',
        skill_path=SKILL,
        skill_sha256=sub.sha256_bytes((ROOT / SKILL).read_bytes()),
        role='coordinate',
        kind=sub.AgentKind.COORDINATOR,
    )
    plan = sub.OrchestrationPlan('reentrancy-guard-experiment', 'coordinator', (agent,))
    capabilities = {
        'coordinator': sub.RuntimeCapabilities(
            sandbox_id='reentrancy-fixture',
            isolation_verified=True,
            instruction_sha256=agent.skill_sha256,
        )
    }
    runtime = sub.CallableRuntime({'coordinator': callback}, capabilities)
    return plan, runtime


def success(task):
    return sub.AgentReport(
        agent_id=task.agent_id, task_id=task.task_id,
        input_sha256=task.input_sha256, status=sub.ReportStatus.COMPLETED,
    )


class ReentrantTaskTests(unittest.TestCase):
    def test_same_inflight_task_is_not_executed_twice(self):
        calls = []
        nested = []

        def callback(_agent, task):
            calls.append(task.task_id)
            if len(calls) == 1:
                nested.append(sub.orchestrate(
                    plan=plan, runtime=runtime, objective='same-work',
                    context=(), run_id='same-run',
                ))
            return success(task)

        plan, runtime = environment(callback)
        outer = sub.orchestrate(plan=plan, runtime=runtime, objective='same-work',
                                context=(), run_id='same-run')
        self.assertEqual(outer.status, sub.RunStatus.COMPLETED)
        self.assertEqual(len(calls), 1, 'nested same-task dispatch performed redundant work')
        self.assertEqual(len(nested), 1)
        self.assertEqual(nested[0].status, sub.RunStatus.FAILED)
        self.assertEqual(len(nested[0].failures), 1)
        self.assertIn('duplicate in-flight task invocation', nested[0].failures[0].error)
        self.assertEqual(outer.reports[0].task_id, nested[0].failures[0].task_id)

    def test_distinct_nested_run_is_permitted(self):
        calls = []
        nested = []

        def callback(_agent, task):
            calls.append((task.run_id, task.task_id))
            if task.run_id == 'outer':
                nested.append(sub.orchestrate(
                    plan=plan, runtime=runtime, objective='same-work',
                    context=(), run_id='inner',
                ))
            return success(task)

        plan, runtime = environment(callback)
        outer = sub.orchestrate(plan=plan, runtime=runtime, objective='same-work',
                                context=(), run_id='outer')
        self.assertEqual([item[0] for item in calls], ['outer', 'inner'])
        self.assertNotEqual(calls[0][1], calls[1][1])
        self.assertEqual(outer.status, sub.RunStatus.COMPLETED)
        self.assertEqual(nested[0].status, sub.RunStatus.COMPLETED)

    def test_sequential_same_task_can_run_again(self):
        calls = []

        def callback(_agent, task):
            calls.append(task.task_id)
            return success(task)

        plan, runtime = environment(callback)
        outputs = [sub.orchestrate(plan=plan, runtime=runtime, objective='same-work',
                                   context=(), run_id='repeat') for _ in range(2)]
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], calls[1])
        self.assertTrue(all(result.status is sub.RunStatus.COMPLETED for result in outputs))

    def test_failing_callback_releases_inflight_guard(self):
        calls = []

        def callback(_agent, task):
            calls.append(task.task_id)
            raise RuntimeError('injected transport failure')

        plan, runtime = environment(callback)
        outputs = [sub.orchestrate(plan=plan, runtime=runtime, objective='same-work',
                                   context=(), run_id='retry-after-failure') for _ in range(2)]
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], calls[1])
        self.assertTrue(all(result.status is sub.RunStatus.FAILED for result in outputs))
        self.assertTrue(all('injected transport failure' in result.failures[0].error
                            for result in outputs))


    def test_recursive_failed_dispatch_is_bounded_and_later_retry_allowed(self):
        calls = []
        nested = []

        def callback(_agent, task):
            calls.append(task.task_id)
            if len(calls) == 1:
                nested.append(sub.orchestrate(
                    plan=plan, runtime=runtime, objective='same-failing-work',
                    context=(), run_id='same-failing-run',
                ))
            raise RuntimeError('injected unsuccessful attempt')

        plan, runtime = environment(callback)
        outer = sub.orchestrate(plan=plan, runtime=runtime, objective='same-failing-work',
                                context=(), run_id='same-failing-run')
        self.assertEqual(len(calls), 1, 'unsuccessful duplicate consumed a second invocation')
        self.assertEqual(outer.status, sub.RunStatus.FAILED)
        self.assertEqual(nested[0].status, sub.RunStatus.FAILED)
        self.assertIn('duplicate in-flight task invocation', nested[0].failures[0].error)
        self.assertIn('injected unsuccessful attempt', outer.failures[0].error)

        sequential = sub.orchestrate(plan=plan, runtime=runtime,
                                     objective='same-failing-work', context=(),
                                     run_id='same-failing-run')
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0], calls[1])
        self.assertEqual(sequential.status, sub.RunStatus.FAILED)


if __name__ == '__main__':
    unittest.main()
