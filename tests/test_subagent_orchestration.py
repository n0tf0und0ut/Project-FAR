from __future__ import annotations

import dataclasses
import json
import tempfile
import unittest
from pathlib import Path

from tools import subagent_orchestration as sub


ROOT = Path(__file__).resolve().parents[1]


def spec(*, skill_path: str, **kwargs) -> sub.AgentSpec:
    digest = sub.sha256_bytes((ROOT / skill_path).read_bytes())
    return sub.AgentSpec(skill_path=skill_path, skill_sha256=digest, **kwargs)


def cap(agent: sub.AgentSpec, **overrides) -> sub.RuntimeCapabilities:
    values = {
        "sandbox_id": f"sandbox:{agent.agent_id}",
        "isolation_verified": True,
        "instruction_sha256": agent.skill_sha256,
        "repository_tools_enabled": False,
        "shared_state_with": (),
    }
    values.update(overrides)
    return sub.RuntimeCapabilities(**values)


def completed(task: sub.AgentTask, *findings: sub.Finding) -> sub.AgentReport:
    return sub.AgentReport(
        agent_id=task.agent_id,
        task_id=task.task_id,
        input_sha256=task.input_sha256,
        status=sub.ReportStatus.COMPLETED,
        findings=tuple(findings),
    )


class PlanTests(unittest.TestCase):
    def test_default_plan_is_deterministic_and_coordinator_is_terminal(self):
        left = sub.far_research_plan()
        right = sub.far_research_plan()
        self.assertEqual(left.sha256, right.sha256)
        order = sub.topological_order(left)
        self.assertEqual(order[-1], "coordinator")
        self.assertEqual(set(left.by_id["coordinator"].dependencies), set(order[:-1]))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for agent in left.agents:
                skill = root / agent.skill_path
                skill.parent.mkdir(parents=True, exist_ok=True)
                skill.write_bytes((ROOT / agent.skill_path).read_bytes())
            frozen = sub.far_research_plan(root)
            skill = root / frozen.by_id["discovery"].skill_path
            skill.write_text("changed instructions\n", encoding="utf-8")
            changed = sub.far_research_plan(root)
            self.assertNotEqual(frozen.sha256, changed.sha256)
            self.assertNotEqual(frozen.by_id["discovery"].skill_sha256,
                                changed.by_id["discovery"].skill_sha256)

    def test_cycle_and_incomplete_coordinator_dependency_fail_closed(self):
        specialist = spec(
            agent_id="a",
            skill_path=".claude/skills/far-formalizer/SKILL.md",
            role="a",
            dependencies=("b",),
        )
        other = spec(
            agent_id="b",
            skill_path=".claude/skills/far-formalizer/SKILL.md",
            role="b",
            dependencies=("a",),
        )
        coordinator = spec(
            agent_id="coordinator",
            skill_path=".claude/skills/far-research-orchestrator/SKILL.md",
            role="coordinate",
            kind=sub.AgentKind.COORDINATOR,
            dependencies=("a", "b"),
        )
        with self.assertRaisesRegex(ValueError, "cycle"):
            sub.OrchestrationPlan(
                plan_id="cycle-plan",
                coordinator_id="coordinator",
                agents=(specialist, other, coordinator),
            )

        coordinator_missing = dataclasses.replace(
            coordinator, dependencies=("a",)
        )
        with self.assertRaisesRegex(ValueError, "every specialist"):
            sub.OrchestrationPlan(
                plan_id="missing-dependency",
                coordinator_id="coordinator",
                agents=(
                    dataclasses.replace(specialist, dependencies=()),
                    dataclasses.replace(other, dependencies=()),
                    coordinator_missing,
                ),
            )

    def test_context_is_content_addressed(self):
        artifact = sub.ContextArtifact.from_text("source-1", "exact bytes")
        self.assertEqual(artifact.sha256, sub.sha256_text("exact bytes"))
        with self.assertRaisesRegex(ValueError, "content hash mismatch"):
            sub.ContextArtifact("source-1", "0" * 64, "exact bytes")


class OrchestrationTests(unittest.TestCase):
    @staticmethod
    def simple_plan(*, sequencing_only=False) -> sub.OrchestrationPlan:
        a = spec(
            agent_id="a",
            skill_path=".claude/skills/far-discovery-engine/SKILL.md",
            role="a",
        )
        b = spec(
            agent_id="b",
            skill_path=".claude/skills/far-formalizer/SKILL.md",
            role="b",
            dependencies=("a",),
            receives_dependency_reports=not sequencing_only,
        )
        coordinator = spec(
            agent_id="coordinator",
            skill_path=".claude/skills/far-research-orchestrator/SKILL.md",
            role="coordinator",
            kind=sub.AgentKind.COORDINATOR,
            dependencies=("a", "b"),
        )
        return sub.OrchestrationPlan(
            plan_id="simple-plan",
            coordinator_id="coordinator",
            agents=(a, b, coordinator),
        )

    def test_explicit_dependency_visibility_and_only_coordinator_integrates(self):
        plan = self.simple_plan()
        seen = {}

        def callback(agent, task):
            seen[agent.agent_id] = tuple(
                report.agent_id for report in task.dependency_reports
            )
            return completed(task)

        runtime = sub.CallableRuntime(
            {name: callback for name in plan.by_id},
            {name: cap(plan.by_id[name]) for name in plan.by_id},
        )
        result = sub.orchestrate(
            plan=plan,
            objective="test objective",
            context=(sub.ContextArtifact.from_text("input", "frozen"),),
            runtime=runtime,
        )
        self.assertEqual(result.status, sub.RunStatus.COMPLETED)
        self.assertEqual(seen["a"], ())
        self.assertEqual(seen["b"], ("a",))
        self.assertEqual(seen["coordinator"], ("a", "b"))
        self.assertEqual(result.coordinator_report.agent_id, "coordinator")

    def test_sequencing_dependency_can_hide_upstream_report(self):
        plan = self.simple_plan(sequencing_only=True)
        seen_b = []

        def callback(agent, task):
            if agent.agent_id == "b":
                seen_b.extend(task.dependency_reports)
            return completed(task)

        runtime = sub.CallableRuntime(
            {name: callback for name in plan.by_id},
            {name: cap(plan.by_id[name]) for name in plan.by_id},
        )
        result = sub.orchestrate(
            plan=plan,
            objective="blind-after-sequence",
            context=(),
            runtime=runtime,
        )
        self.assertEqual(result.status, sub.RunStatus.COMPLETED)
        self.assertEqual(seen_b, [])

    def test_clean_room_receives_only_frozen_context_and_claim_ids(self):
        original = self.simple_plan()
        clean = dataclasses.replace(
            original.by_id["b"],
            context_ids=("frozen_claims",),
            dependency_view=sub.DependencyView.CLAIMS_ONLY,
            clean_room=True,
        )
        plan = sub.OrchestrationPlan(
            plan_id="clean-room-plan", coordinator_id="coordinator",
            agents=(original.by_id["a"], clean, original.by_id["coordinator"]),
        )
        seen = {}

        def callback(agent, task):
            seen[agent.agent_id] = task
            if agent.agent_id == "a":
                return completed(task, sub.Finding(
                    finding_id="F-1", claim_id="CLAIM-1",
                    disposition=sub.FindingDisposition.SUPPORTS,
                    statement="prior FAR verdict leaked if forwarded",
                    evidence_refs=("construction",),
                ))
            return completed(task)

        context = (
            sub.ContextArtifact.from_text("frozen_claims", "CLAIM-1 exact frozen packet"),
            sub.ContextArtifact.from_text("construction", "prior FAR verdict: accept"),
        )
        capabilities = {name: cap(plan.by_id[name]) for name in plan.by_id}
        capabilities["b"] = cap(clean, clean_room_verified=True)
        result = sub.orchestrate(plan=plan, objective="Assess CLAIM-1", context=context,
                                 runtime=sub.CallableRuntime({name: callback for name in plan.by_id}, capabilities))
        self.assertEqual(result.status, sub.RunStatus.COMPLETED)
        self.assertEqual([item.artifact_id for item in seen["b"].context], ["frozen_claims"])
        projected = seen["b"].dependency_reports[0]
        self.assertEqual(projected.claim_ids, ("CLAIM-1",))
        self.assertEqual(projected.findings, ())
        self.assertNotIn("prior FAR verdict", sub.canonical_json(sub._dependency_payload(projected)))

        capabilities["b"] = cap(clean)
        with self.assertRaisesRegex(ValueError, "clean-room isolation is not verified"):
            sub.orchestrate(plan=plan, objective="Assess CLAIM-1", context=context,
                            runtime=sub.CallableRuntime({name: callback for name in plan.by_id}, capabilities))
        with self.assertRaisesRegex(ValueError, "missing context artifacts"):
            sub.orchestrate(plan=plan, objective="Assess CLAIM-1", context=context[1:],
                            runtime=sub.CallableRuntime({name: callback for name in plan.by_id}, capabilities))

    def test_clean_room_metadata_rejects_conclusion_context_and_full_reports(self):
        base = self.simple_plan().by_id["b"]
        with self.assertRaisesRegex(ValueError, "claims-only"):
            dataclasses.replace(base, clean_room=True, context_ids=("frozen_claims",))
        with self.assertRaisesRegex(ValueError, "forbidden clean-room context"):
            dataclasses.replace(base, clean_room=True,
                                context_ids=("preferred_conclusion",),
                                dependency_view=sub.DependencyView.CLAIMS_ONLY)

    def test_support_contradiction_blocks_coordinator_even_under_majority(self):
        agents = []
        for name in ("a", "b", "c", "d"):
            agents.append(
                spec(
                    agent_id=name,
                    skill_path=".claude/skills/far-theory-auditor/SKILL.md",
                    role=name,
                )
            )
        coordinator = spec(
            agent_id="coordinator",
            skill_path=".claude/skills/far-research-orchestrator/SKILL.md",
            role="coordinate",
            kind=sub.AgentKind.COORDINATOR,
            dependencies=tuple(item.agent_id for item in agents),
        )
        plan = sub.OrchestrationPlan(
            plan_id="conflict-plan",
            coordinator_id="coordinator",
            agents=tuple(agents) + (coordinator,),
        )
        coordinator_called = False

        def callback(agent, task):
            nonlocal coordinator_called
            if agent.agent_id == "coordinator":
                coordinator_called = True
                return completed(task)
            disposition = (
                sub.FindingDisposition.CONTRADICTS
                if agent.agent_id == "d"
                else sub.FindingDisposition.SUPPORTS
            )
            finding = sub.Finding(
                finding_id=f"F-{agent.agent_id}",
                claim_id="CLAIM-1",
                disposition=disposition,
                statement=f"{agent.agent_id} result",
            )
            return completed(task, finding)

        runtime = sub.CallableRuntime(
            {name: callback for name in plan.by_id},
            {name: cap(plan.by_id[name]) for name in plan.by_id},
        )
        result = sub.orchestrate(
            plan=plan,
            objective="conflict",
            context=(),
            runtime=runtime,
        )
        self.assertEqual(result.status, sub.RunStatus.BLOCKED)
        self.assertFalse(coordinator_called)
        self.assertEqual(len(result.conflicts), 1)
        self.assertEqual(
            result.conflicts[0].supporting_findings, ("F-a", "F-b", "F-c")
        )
        self.assertEqual(result.conflicts[0].contradicting_findings, ("F-d",))
        self.assertIn("coordinator", result.blocked_agents)

    def test_runtime_failure_is_durable_and_blocks_dependents(self):
        plan = self.simple_plan()
        calls = []

        def callback(agent, task):
            calls.append(agent.agent_id)
            if agent.agent_id == "a":
                raise RuntimeError("provider unavailable")
            return completed(task)

        runtime = sub.CallableRuntime(
            {name: callback for name in plan.by_id},
            {name: cap(plan.by_id[name]) for name in plan.by_id},
        )
        result = sub.orchestrate(
            plan=plan,
            objective="failure",
            context=(),
            runtime=runtime,
        )
        self.assertEqual(result.status, sub.RunStatus.FAILED)
        self.assertEqual(calls, ["a"])
        self.assertEqual(result.failures[0].agent_id, "a")
        self.assertIn("provider unavailable", result.failures[0].error)
        self.assertEqual(result.blocked_agents, ("b", "coordinator"))
        report = next(item for item in result.reports if item.agent_id == "a")
        self.assertEqual(report.status, sub.ReportStatus.FAILED)

    def test_cross_task_report_substitution_becomes_failure(self):
        plan = self.simple_plan()

        def callback(agent, task):
            if agent.agent_id == "a":
                return sub.AgentReport(
                    agent_id="a",
                    task_id="TASK-wrong",
                    input_sha256=task.input_sha256,
                    status=sub.ReportStatus.COMPLETED,
                )
            return completed(task)

        runtime = sub.CallableRuntime(
            {name: callback for name in plan.by_id},
            {name: cap(plan.by_id[name]) for name in plan.by_id},
        )
        result = sub.orchestrate(
            plan=plan,
            objective="binding",
            context=(),
            runtime=runtime,
        )
        self.assertEqual(result.status, sub.RunStatus.FAILED)
        self.assertIn("report task mismatch", result.failures[0].error)

    def test_agent_cannot_cite_evidence_it_never_received(self):
        plan = self.simple_plan()

        def callback(agent, task):
            if agent.agent_id == "a":
                finding = sub.Finding(
                    finding_id="F-a",
                    claim_id="CLAIM-1",
                    disposition=sub.FindingDisposition.SUPPORTS,
                    statement="claims hidden support",
                    evidence_refs=("not-visible",),
                )
                return completed(task, finding)
            return completed(task)

        runtime = sub.CallableRuntime(
            {name: callback for name in plan.by_id},
            {name: cap(plan.by_id[name]) for name in plan.by_id},
        )
        result = sub.orchestrate(
            plan=plan,
            objective="evidence visibility",
            context=(),
            runtime=runtime,
        )
        self.assertEqual(result.status, sub.RunStatus.FAILED)
        self.assertIn("not visible to task", result.failures[0].error)

    def test_cross_agent_duplicate_finding_id_is_rejected(self):
        agents = (
            spec(
                agent_id="a",
                skill_path=".claude/skills/far-discovery-engine/SKILL.md",
                role="a",
            ),
            spec(
                agent_id="b",
                skill_path=".claude/skills/far-formalizer/SKILL.md",
                role="b",
            ),
        )
        coordinator = spec(
            agent_id="coordinator",
            skill_path=".claude/skills/far-research-orchestrator/SKILL.md",
            role="coordinate",
            kind=sub.AgentKind.COORDINATOR,
            dependencies=("a", "b"),
        )
        plan = sub.OrchestrationPlan(
            plan_id="duplicate-finding-plan",
            coordinator_id="coordinator",
            agents=agents + (coordinator,),
        )

        def callback(agent, task):
            if agent.agent_id == "coordinator":
                return completed(task)
            return completed(
                task,
                sub.Finding(
                    finding_id="F-shared",
                    claim_id=f"CLAIM-{agent.agent_id}",
                    disposition=sub.FindingDisposition.UNKNOWN,
                    statement=agent.agent_id,
                ),
            )

        runtime = sub.CallableRuntime(
            {name: callback for name in plan.by_id},
            {name: cap(plan.by_id[name]) for name in plan.by_id},
        )
        result = sub.orchestrate(
            plan=plan,
            objective="global finding identity",
            context=(),
            runtime=runtime,
        )
        self.assertEqual(result.status, sub.RunStatus.FAILED)
        self.assertEqual(result.failures[0].agent_id, "b")
        self.assertIn("duplicate cross-agent finding_id", result.failures[0].error)

    def test_runtime_capabilities_fail_before_first_invocation(self):
        plan = self.simple_plan()
        called = []

        def callback(agent, task):
            called.append(agent.agent_id)
            return completed(task)

        cases = [
            {
                "a": cap(plan.by_id["a"], isolation_verified=False),
                "b": cap(plan.by_id["b"]),
                "coordinator": cap(plan.by_id["coordinator"]),
            },
            {
                "a": cap(plan.by_id["a"], sandbox_id="same"),
                "b": cap(plan.by_id["b"], sandbox_id="same"),
                "coordinator": cap(plan.by_id["coordinator"]),
            },
            {
                "a": cap(plan.by_id["a"], shared_state_with=("b",)),
                "b": cap(plan.by_id["b"]),
                "coordinator": cap(plan.by_id["coordinator"]),
            },
            {
                "a": cap(plan.by_id["a"], shared_state_with=("external-hidden",)),
                "b": cap(plan.by_id["b"]),
                "coordinator": cap(plan.by_id["coordinator"]),
            },
            {
                "a": cap(plan.by_id["a"], instruction_sha256="1" * 64),
                "b": cap(plan.by_id["b"]),
                "coordinator": cap(plan.by_id["coordinator"]),
            },
            {
                "a": cap(plan.by_id["a"], repository_tools_enabled=True),
                "b": cap(plan.by_id["b"]),
                "coordinator": cap(plan.by_id["coordinator"]),
            },
        ]
        for capabilities in cases:
            with self.subTest(capabilities=capabilities), self.assertRaises(ValueError):
                sub.orchestrate(
                    plan=plan,
                    objective="capability check",
                    context=(),
                    runtime=sub.CallableRuntime(
                        {name: callback for name in plan.by_id}, capabilities
                    ),
                )
            self.assertEqual(called, [])

    def test_identical_inputs_produce_identical_run_task_and_result_hashes(self):
        plan = self.simple_plan()

        def callback(agent, task):
            return completed(task)

        def execute():
            runtime = sub.CallableRuntime(
                {name: callback for name in plan.by_id},
                {name: cap(plan.by_id[name]) for name in plan.by_id},
            )
            return sub.orchestrate(
                plan=plan,
                objective="deterministic",
                context=(sub.ContextArtifact.from_text("x", "y"),),
                runtime=runtime,
            )

        one, two = execute(), execute()
        self.assertEqual(one.run_id, two.run_id)
        self.assertEqual(
            [report.task_id for report in one.reports],
            [report.task_id for report in two.reports],
        )
        self.assertEqual(one.result_sha256, two.result_sha256)


class ReasonerLaneAdapterTests(unittest.TestCase):
    def test_adapter_redacts_secrets_and_strictly_parses_report(self):
        captured = []

        def reasoner(prompt, _invocation_id):
            captured.append(prompt)
            task = json.loads(prompt)["task"]
            return json.dumps(
                {
                    "contract": "far-subagent-report/1.0",
                    "agent_id": "a",
                    "task_id": task["task_id"],
                    "input_sha256": task["input_sha256"],
                    "status": "completed",
                    "findings": [],
                    "limitations": [],
                    "error": None,
                }
            )

        a = spec(
            agent_id="a",
            skill_path=".claude/skills/far-discovery-engine/SKILL.md",
            role="a",
        )
        coordinator = spec(
            agent_id="coordinator",
            skill_path=".claude/skills/far-research-orchestrator/SKILL.md",
            role="coordinate",
            kind=sub.AgentKind.COORDINATOR,
            dependencies=("a",),
        )
        plan = sub.OrchestrationPlan(
            plan_id="adapter-plan",
            coordinator_id="coordinator",
            agents=(a, coordinator),
        )

        def coordinator_reasoner(prompt, _invocation_id):
            task = json.loads(prompt)["task"]
            return json.dumps(
                {
                    "contract": "far-subagent-report/1.0",
                    "agent_id": "coordinator",
                    "task_id": task["task_id"],
                    "input_sha256": task["input_sha256"],
                    "status": "completed",
                    "findings": [],
                    "limitations": [],
                    "error": None,
                }
            )

        lanes = {
            "a": sub.ReasonerLane(
                provider_id="a",
                model_identity="model:a",
                sandbox_id="sandbox:a",
                reasoner=reasoner,
                isolation_verified=True,
            ),
            "coordinator": sub.ReasonerLane(
                provider_id="coordinator",
                model_identity="model:c",
                sandbox_id="sandbox:c",
                reasoner=coordinator_reasoner,
                isolation_verified=True,
            ),
        }
        result = sub.orchestrate(
            plan=plan,
            objective="token=github_pat_abcdefghijklmnopqrstuvwxyz0123456789",
            context=(),
            runtime=sub.ReasonerLaneRuntime(lanes),
        )
        self.assertEqual(result.status, sub.RunStatus.COMPLETED)
        self.assertIn("[REDACTED]", captured[0])
        self.assertNotIn("github_pat_", captured[0])
        payload = json.loads(captured[0])
        self.assertEqual(payload["agent"]["instructions"],
                         (ROOT / a.skill_path).read_text(encoding="utf-8"))
        self.assertEqual(payload["agent"]["skill_sha256"], a.skill_sha256)

    def test_wire_hash_binds_redacted_context_and_receipts(self):
        plan = sub.far_research_plan(ROOT)
        observed = {}

        def reasoner(prompt, task_id):
            payload = json.loads(prompt)
            task = payload["task"]
            wire_hash = task.pop("input_sha256")
            self.assertEqual(wire_hash, sub.sha256_text(sub.canonical_json(payload)))
            artifact = task["context"][0]
            self.assertEqual(artifact["text"], "[REDACTED]")
            self.assertEqual(artifact["sha256"], sub.sha256_text(artifact["text"]))
            self.assertEqual(payload["agent"]["skill_sha256"],
                             sub.sha256_text(payload["agent"]["instructions"]))
            raw = json.dumps(dict(contract="far-subagent-report/1.0",
                                  agent_id=payload["agent"]["agent_id"], task_id=task_id,
                                  input_sha256=wire_hash, status="completed", findings=[],
                                  limitations=[], error=None))
            observed[task_id] = (prompt, raw)
            return raw

        def execute(model):
            lanes = {
                agent.agent_id: sub.ReasonerLane(
                    agent.agent_id, model, f"sandbox:{agent.agent_id}", reasoner, True
                )
                for agent in plan.agents
            }
            return sub.orchestrate(
                plan=plan, objective="Check provenance",
                context=(sub.ContextArtifact.from_text("source", "token=example-credential"),),
                runtime=sub.ReasonerLaneRuntime(lanes, root=ROOT),
            )

        result = execute("declared-model")
        self.assertEqual(result.status, sub.RunStatus.COMPLETED)
        self.assertEqual(len(result.invocation_receipts), 14)
        self.assertEqual(len(result.runtime_capabilities), 14)
        self.assertEqual({item.agent_id for item in result.invocation_receipts}, set(plan.by_id))
        for receipt in result.invocation_receipts:
            request, response = observed[receipt.task_id]
            self.assertEqual(receipt.request_sha256, sub.sha256_text(request))
            self.assertEqual(receipt.response_sha256, sub.sha256_text(response))
        self.assertNotEqual(result.result_sha256, execute("different-model").result_sha256)

    def test_failed_reentrant_call_preserves_both_request_receipts(self):
        agent = spec(agent_id="coordinator", role="coordinate",
                     kind=sub.AgentKind.COORDINATOR,
                     skill_path=".claude/skills/far-research-orchestrator/SKILL.md")
        plan = sub.OrchestrationPlan("one-lane", agent.agent_id, (agent,))
        prompts = {}
        nested = None

        def reasoner(prompt, task_id):
            nonlocal nested
            task = json.loads(prompt)["task"]
            prompts[task_id] = prompt
            if task["run_id"] == "outer":
                nested = execute("inner")
                raise ValueError("outer transport failure")
            return "{}"

        runtime = sub.ReasonerLaneRuntime({
            agent.agent_id: sub.ReasonerLane(agent.agent_id, "model", "sandbox", reasoner, True),
        }, root=ROOT)

        def execute(run_id):
            return sub.orchestrate(plan=plan, objective="Check receipts", context=(),
                                   runtime=runtime, run_id=run_id)

        outer = execute("outer")
        self.assertEqual(outer.status, sub.RunStatus.FAILED)
        self.assertEqual(nested.status, sub.RunStatus.FAILED)
        outer_receipt, = outer.invocation_receipts
        inner_receipt, = nested.invocation_receipts
        self.assertIsNone(outer_receipt.response_sha256)
        self.assertEqual(inner_receipt.response_sha256, sub.sha256_text("{}"))
        for receipt in (outer_receipt, inner_receipt):
            self.assertEqual(receipt.request_sha256, sub.sha256_text(prompts[receipt.task_id]))

    def test_malformed_typed_reports_and_ambiguous_isolation_fail_closed(self):
        base = dict(agent_id="a", task_id="TASK-1", input_sha256="0" * 64)
        with self.assertRaisesRegex(ValueError, "invalid report status"):
            sub.AgentReport(**base, status="completed")
        with self.assertRaisesRegex(ValueError, "limitations"):
            sub.AgentReport(**base, status=sub.ReportStatus.COMPLETED, limitations="wrong")
        with self.assertRaises(UnicodeError):
            sub.AgentReport(**base, status=sub.ReportStatus.COMPLETED, limitations=("\ud800",))
        with self.assertRaisesRegex(ValueError, "invalid finding disposition"):
            sub.Finding("F-1", "C-1", "supports", "statement")
        with self.assertRaisesRegex(ValueError, "flags must be booleans"):
            sub.RuntimeCapabilities("sandbox", "false", "0" * 64)
        with self.assertRaisesRegex(ValueError, "shared_state_with must be a tuple"):
            sub.RuntimeCapabilities("sandbox", True, "0" * 64, shared_state_with="peer")
        with self.assertRaisesRegex(ValueError, "contradictory clean-room capability"):
            sub.RuntimeCapabilities("sandbox", False, "0" * 64, clean_room_verified=True)
        with self.assertRaisesRegex(ValueError, "forbidden clean-room context"):
            dataclasses.replace(sub.far_research_plan(ROOT).by_id["discovery"],
                                clean_room=True, context_ids=("Prior-FAR-Verdict",),
                                dependency_view=sub.DependencyView.CLAIMS_ONLY)

    def test_adapter_rejects_lane_provider_identity_mismatch_before_call(self):
        called = False

        def reasoner(_prompt, _invocation_id):
            nonlocal called
            called = True
            return "{}"

        a = spec(
            agent_id="a",
            skill_path=".claude/skills/far-discovery-engine/SKILL.md",
            role="a",
        )
        coordinator = spec(
            agent_id="coordinator",
            skill_path=".claude/skills/far-research-orchestrator/SKILL.md",
            role="coordinate",
            kind=sub.AgentKind.COORDINATOR,
            dependencies=("a",),
        )
        plan = sub.OrchestrationPlan(
            plan_id="provider-mismatch-plan",
            coordinator_id="coordinator",
            agents=(a, coordinator),
        )
        lanes = {
            "a": sub.ReasonerLane(
                provider_id="different",
                model_identity="model:a",
                sandbox_id="sandbox:a",
                reasoner=reasoner,
                isolation_verified=True,
            ),
            "coordinator": sub.ReasonerLane(
                provider_id="coordinator",
                model_identity="model:c",
                sandbox_id="sandbox:c",
                reasoner=reasoner,
                isolation_verified=True,
            ),
        }
        with self.assertRaisesRegex(ValueError, "lane/provider identity mismatch"):
            sub.orchestrate(
                plan=plan,
                objective="identity",
                context=(),
                runtime=sub.ReasonerLaneRuntime(lanes),
            )
        self.assertFalse(called)

    def test_parser_rejects_extra_keys_and_unknown_disposition(self):
        base = {
            "contract": "far-subagent-report/1.0",
            "agent_id": "a",
            "task_id": "TASK-1",
            "input_sha256": "0" * 64,
            "status": "completed",
            "findings": [],
            "limitations": [],
            "error": None,
        }
        extra = dict(base)
        extra["surprise"] = True
        with self.assertRaisesRegex(ValueError, "keys mismatch"):
            sub.parse_agent_report(json.dumps(extra))

        bad = dict(base)
        bad["findings"] = [
            {
                "finding_id": "F-1",
                "claim_id": "C-1",
                "disposition": "probably",
                "statement": "x",
                "evidence_refs": [],
            }
        ]
        with self.assertRaisesRegex(ValueError, "invalid disposition"):
            sub.parse_agent_report(json.dumps(bad))
        with self.assertRaisesRegex(ValueError, "duplicate report key"):
            sub.parse_agent_report(json.dumps(base).replace('"agent_id": "a"',
                                       '"agent_id": "a", "agent_id": "b"'))


if __name__ == "__main__":
    unittest.main()
