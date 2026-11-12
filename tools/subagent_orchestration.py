#!/usr/bin/env python3
"""Provider-neutral, fail-closed subagent orchestration for Project FAR.

This module is execution infrastructure, not theory authority. It provides a typed,
content-addressed coordination layer above FAR specialist skills while preserving
explicit information flow and existing isolation semantics. It intentionally does
not treat model agreement, agent count, or coordinator synthesis as evidence of
truth or external independence.

The protocol is runtime-neutral. ``ReasonerLaneRuntime`` adapts the existing
``adversarial_research_harness.ReasonerLane`` abstraction without depending on a
provider SDK. Other runtimes can implement ``AgentRuntime`` directly.
"""
from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from contextvars import ContextVar
from pathlib import Path, PurePosixPath
from typing import Protocol

from tools.adversarial_research_harness import ReasonerLane, redact_outbound


_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_FORBIDDEN_CLEAN_ROOM_CONTEXT = frozenset({
    "accepted_answer", "preferred_conclusion", "prior_far_verdict",
    "prior_target_conclusion", "synthesis", "target_conclusion",
})


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


class AgentKind(str, enum.Enum):
    SPECIALIST = "specialist"
    COORDINATOR = "coordinator"


class DependencyView(str, enum.Enum):
    FULL = "full"
    FINDINGS = "findings"
    CLAIMS_ONLY = "claims-only"


class FindingDisposition(str, enum.Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    UNKNOWN = "unknown"
    LIMITATION = "limitation"


class ReportStatus(str, enum.Enum):
    COMPLETED = "completed"
    FAILED = "failed"


class RunStatus(str, enum.Enum):
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclasses.dataclass(frozen=True, slots=True)
class ContextArtifact:
    artifact_id: str
    sha256: str
    text: str

    def __post_init__(self) -> None:
        _validate_id(self.artifact_id, "artifact_id")
        if not _HEX64.fullmatch(self.sha256):
            raise ValueError(f"{self.artifact_id}: sha256 must be lowercase hex")
        actual = sha256_text(self.text)
        if actual != self.sha256:
            raise ValueError(
                f"{self.artifact_id}: content hash mismatch: declared {self.sha256}, actual {actual}"
            )

    @classmethod
    def from_text(cls, artifact_id: str, text: str) -> "ContextArtifact":
        return cls(artifact_id=artifact_id, sha256=sha256_text(text), text=text)


@dataclasses.dataclass(frozen=True, slots=True)
class Finding:
    finding_id: str
    claim_id: str
    disposition: FindingDisposition
    statement: str
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_id(self.finding_id, "finding_id")
        _validate_id(self.claim_id, "claim_id")
        if not isinstance(self.disposition, FindingDisposition):
            raise ValueError("invalid finding disposition")
        _require_str(self.statement, "statement")
        if type(self.evidence_refs) is not tuple:
            raise ValueError("evidence_refs must be a tuple")
        if not self.statement.strip():
            raise ValueError(f"{self.finding_id}: statement is required")
        if len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise ValueError(f"{self.finding_id}: evidence_refs must be unique")
        for ref in self.evidence_refs:
            _validate_id(ref, "evidence_ref")


@dataclasses.dataclass(frozen=True, slots=True)
class AgentReport:
    agent_id: str
    task_id: str
    input_sha256: str
    status: ReportStatus
    findings: tuple[Finding, ...] = ()
    limitations: tuple[str, ...] = ()
    error: str | None = None

    def __post_init__(self) -> None:
        _validate_id(self.agent_id, "agent_id")
        _validate_id(self.task_id, "task_id")
        if not _HEX64.fullmatch(self.input_sha256):
            raise ValueError(f"{self.agent_id}: input_sha256 must be lowercase hex")
        if not isinstance(self.status, ReportStatus):
            raise ValueError("invalid report status")
        if type(self.findings) is not tuple or any(type(item) is not Finding for item in self.findings):
            raise ValueError("findings must be a tuple of Finding values")
        if type(self.limitations) is not tuple:
            raise ValueError("limitations must be a tuple")
        for limitation in self.limitations:
            _require_str(limitation, "limitation")
        if self.error is not None:
            _require_str(self.error, "error")
        ids = [item.finding_id for item in self.findings]
        if len(ids) != len(set(ids)):
            raise ValueError(f"{self.agent_id}: duplicate finding_id")
        if self.status is ReportStatus.COMPLETED and self.error is not None:
            raise ValueError(f"{self.agent_id}: completed report cannot contain error")
        if self.status is ReportStatus.FAILED:
            if not self.error or not self.error.strip():
                raise ValueError(f"{self.agent_id}: failed report requires error")
            if self.findings:
                raise ValueError(f"{self.agent_id}: failed report cannot assert findings")


@dataclasses.dataclass(frozen=True, slots=True)
class AgentSpec:
    agent_id: str
    skill_path: str
    skill_sha256: str
    role: str
    kind: AgentKind = AgentKind.SPECIALIST
    dependencies: tuple[str, ...] = ()
    receives_dependency_reports: bool = True
    requires_isolation: bool = True
    repository_tools_allowed: bool = False
    context_ids: tuple[str, ...] | None = None
    dependency_view: DependencyView = DependencyView.FULL
    clean_room: bool = False

    def __post_init__(self) -> None:
        _validate_id(self.agent_id, "agent_id")
        if not isinstance(self.kind, AgentKind) or not isinstance(self.dependency_view, DependencyView):
            raise ValueError(f"{self.agent_id}: invalid agent kind or dependency view")
        skill_parts = PurePosixPath(self.skill_path).parts
        if (
            len(skill_parts) != 4
            or skill_parts[:2] != (".claude", "skills")
            or skill_parts[-1] != "SKILL.md"
            or skill_parts[2] in {"", ".", ".."}
        ):
            raise ValueError(f"{self.agent_id}: skill_path must reference one FAR skill")
        if not _HEX64.fullmatch(self.skill_sha256):
            raise ValueError(f"{self.agent_id}: skill_sha256 must be lowercase hex")
        if not self.role.strip():
            raise ValueError(f"{self.agent_id}: role is required")
        if len(self.dependencies) != len(set(self.dependencies)):
            raise ValueError(f"{self.agent_id}: dependencies must be unique")
        if self.context_ids is not None:
            if len(self.context_ids) != len(set(self.context_ids)):
                raise ValueError(f"{self.agent_id}: context_ids must be unique")
            for artifact_id in self.context_ids:
                _validate_id(artifact_id, "context_id")
        for flag in (self.receives_dependency_reports, self.requires_isolation,
                     self.repository_tools_allowed, self.clean_room):
            if type(flag) is not bool:
                raise ValueError("plan flags must be booleans")
        if self.clean_room:
            if self.context_ids is None:
                raise ValueError(f"{self.agent_id}: clean-room context must have an explicit allowlist")
            if self.dependency_view is not DependencyView.CLAIMS_ONLY:
                raise ValueError(f"{self.agent_id}: clean-room dependencies require claims-only view")
            forbidden = {
                item for item in self.context_ids
                if item.casefold().replace("-", "_") in _FORBIDDEN_CLEAN_ROOM_CONTEXT
            }
            if forbidden:
                raise ValueError(f"{self.agent_id}: forbidden clean-room context {sorted(forbidden)}")
            if not self.requires_isolation or self.repository_tools_allowed:
                raise ValueError(f"{self.agent_id}: clean-room task requires isolation without repository tools")


@dataclasses.dataclass(frozen=True, slots=True)
class OrchestrationPlan:
    plan_id: str
    coordinator_id: str
    agents: tuple[AgentSpec, ...]

    def __post_init__(self) -> None:
        _validate_id(self.plan_id, "plan_id")
        _validate_id(self.coordinator_id, "coordinator_id")
        validate_plan(self)

    @property
    def by_id(self) -> dict[str, AgentSpec]:
        return {agent.agent_id: agent for agent in self.agents}

    @property
    def sha256(self) -> str:
        return sha256_text(canonical_json(_plan_payload(self)))


@dataclasses.dataclass(frozen=True, slots=True)
class RuntimeCapabilities:
    sandbox_id: str
    isolation_verified: bool
    instruction_sha256: str
    repository_tools_enabled: bool = False
    shared_state_with: tuple[str, ...] = ()
    clean_room_verified: bool = False
    provider_id: str | None = None
    model_identity: str | None = None
    prior_exposure: str | None = None

    def __post_init__(self) -> None:
        _validate_id(self.sandbox_id, "sandbox_id")
        for flag in (self.isolation_verified, self.repository_tools_enabled,
                     self.clean_room_verified):
            if type(flag) is not bool:
                raise ValueError("runtime capability flags must be booleans")
        if type(self.shared_state_with) is not tuple:
            raise ValueError("shared_state_with must be a tuple")
        for peer in self.shared_state_with:
            _validate_id(peer, "shared-state peer")
        if self.clean_room_verified and (not self.isolation_verified
                                         or self.repository_tools_enabled
                                         or self.shared_state_with):
            raise ValueError("contradictory clean-room capability")
        for value in (self.sandbox_id, *self.shared_state_with,
                      self.provider_id, self.model_identity, self.prior_exposure):
            if value is not None and (not _require_str(value, "runtime identity").strip()
                                      or redact_outbound(value) != value):
                raise ValueError("invalid runtime identity")
        if not _HEX64.fullmatch(self.instruction_sha256):
            raise ValueError("instruction_sha256 must be lowercase hex")
        if len(self.shared_state_with) != len(set(self.shared_state_with)):
            raise ValueError("shared_state_with must be unique")


@dataclasses.dataclass(frozen=True, slots=True)
class AgentTask:
    run_id: str
    task_id: str
    address: str
    agent_id: str
    skill_path: str
    skill_sha256: str
    objective: str
    input_sha256: str
    context: tuple[ContextArtifact, ...]
    dependency_reports: tuple[VisibleDependency, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class VisibleDependency:
    agent_id: str
    task_id: str
    view: DependencyView
    claim_ids: tuple[str, ...] = ()
    findings: tuple[Finding, ...] = ()
    limitations: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True, slots=True)
class Conflict:
    conflict_id: str
    claim_id: str
    supporting_findings: tuple[str, ...]
    contradicting_findings: tuple[str, ...]


@dataclasses.dataclass(frozen=True, slots=True)
class AgentFailure:
    agent_id: str
    task_id: str
    error: str


@dataclasses.dataclass(frozen=True, slots=True)
class InvocationReceipt:
    agent_id: str
    task_id: str
    input_sha256: str
    request_sha256: str
    response_sha256: str | None


@dataclasses.dataclass(frozen=True, slots=True)
class OrchestrationResult:
    run_id: str
    plan_sha256: str
    status: RunStatus
    reports: tuple[AgentReport, ...]
    conflicts: tuple[Conflict, ...]
    failures: tuple[AgentFailure, ...]
    blocked_agents: tuple[str, ...]
    coordinator_report: AgentReport | None
    result_sha256: str
    runtime_capabilities: tuple[tuple[str, RuntimeCapabilities], ...] = ()
    invocation_receipts: tuple[InvocationReceipt, ...] = ()


class AgentRuntime(Protocol):
    """Provider/runtime boundary for FAR subagents."""

    def capabilities(self, agent: AgentSpec) -> RuntimeCapabilities:
        ...

    def invoke(self, agent: AgentSpec, task: AgentTask) -> AgentReport:
        ...


AgentCallable = Callable[[AgentSpec, AgentTask], AgentReport]


class CallableRuntime:
    """Small deterministic adapter useful for local runtimes and tests."""

    def __init__(
        self,
        callbacks: Mapping[str, AgentCallable],
        capabilities: Mapping[str, RuntimeCapabilities],
    ) -> None:
        self._callbacks = dict(callbacks)
        self._capabilities = dict(capabilities)

    def capabilities(self, agent: AgentSpec) -> RuntimeCapabilities:
        try:
            return self._capabilities[agent.agent_id]
        except KeyError as exc:
            raise ValueError(f"no runtime capabilities for {agent.agent_id}") from exc

    def invoke(self, agent: AgentSpec, task: AgentTask) -> AgentReport:
        try:
            callback = self._callbacks[agent.agent_id]
        except KeyError as exc:
            raise ValueError(f"no runtime callback for {agent.agent_id}") from exc
        return callback(agent, task)


class ReasonerLaneRuntime:
    """Adapt existing FAR ``ReasonerLane`` instances to the typed subagent protocol.

    Each lane receives canonical JSON and must return a single JSON object conforming
    to ``far-subagent-report/1.0``. The adapter redacts credential-shaped outbound
    strings. Isolation metadata is carried from ``ReasonerLane`` and enforced by the
    orchestrator before any lane is invoked.
    """

    def __init__(
        self,
        lanes: Mapping[str, ReasonerLane],
        *,
        root: Path | str = Path("."),
        skill_texts: Mapping[str, str] | None = None,
    ) -> None:
        self._lanes = dict(lanes)
        self._root = Path(root).resolve()
        self._skill_texts = dict(skill_texts or {})
        self._receipt: ContextVar[InvocationReceipt | None] = ContextVar(
            "reasoner_lane_receipt", default=None
        )
        self._skill_cache: dict[tuple[str, str], tuple[str, str]] = {}

    def capabilities(self, agent: AgentSpec) -> RuntimeCapabilities:
        try:
            lane = self._lanes[agent.agent_id]
        except KeyError as exc:
            raise ValueError(f"no reasoner lane for {agent.agent_id}") from exc
        if lane.provider_id != agent.agent_id:
            raise ValueError(
                f"{agent.agent_id}: lane/provider identity mismatch: {lane.provider_id}"
            )
        if not lane.model_identity.strip():
            raise ValueError(f"{agent.agent_id}: model identity is required")
        _text, digest = self._load_skill(agent)
        return RuntimeCapabilities(
            sandbox_id=lane.sandbox_id,
            isolation_verified=lane.isolation_verified,
            instruction_sha256=digest,
            repository_tools_enabled=lane.repository_tools_enabled,
            shared_state_with=lane.shared_state_with,
            provider_id=lane.provider_id,
            model_identity=lane.model_identity,
            prior_exposure=lane.prior_exposure,
        )

    def invoke(self, agent: AgentSpec, task: AgentTask) -> AgentReport:
        self._receipt.set(None)
        lane = self._lanes[agent.agent_id]
        skill_text, _digest = self._load_skill(agent)
        payload = _redacted_task_payload(agent, task, skill_text)
        wire_input = sha256_text(canonical_json(payload))
        payload["task"]["input_sha256"] = wire_input
        prompt = canonical_json(payload)
        receipt = InvocationReceipt(agent.agent_id, task.task_id, wire_input,
                                    sha256_text(prompt), None)
        try:
            raw = lane.reasoner(prompt, task.task_id)
            if not isinstance(raw, str):
                raise TypeError("reasoner output must be text")
            receipt = dataclasses.replace(receipt, response_sha256=sha256_text(raw))
        finally:
            self._receipt.set(receipt)
        report = parse_agent_report(raw)
        if report.input_sha256 != wire_input:
            raise ValueError("wire report input hash mismatch")
        return dataclasses.replace(report, input_sha256=task.input_sha256)

    def take_receipt(self, task: AgentTask) -> InvocationReceipt | None:
        receipt = self._receipt.get()
        self._receipt.set(None)
        return receipt if receipt is not None and receipt.task_id == task.task_id else None

    def _load_skill(self, agent: AgentSpec) -> tuple[str, str]:
        cache_key = (agent.skill_path, agent.skill_sha256)
        cached = self._skill_cache.get(cache_key)
        if cached is not None:
            return cached
        if agent.skill_path in self._skill_texts:
            text = self._skill_texts[agent.skill_path]
            raw = text.encode("utf-8")
        else:
            candidate = (self._root / agent.skill_path).resolve()
            skills_root = (self._root / ".claude" / "skills").resolve()
            if not candidate.is_relative_to(skills_root):
                raise ValueError(f"{agent.agent_id}: skill path escapes skills root")
            try:
                raw = candidate.read_bytes()
            except OSError as exc:
                raise ValueError(
                    f"{agent.agent_id}: cannot read skill {agent.skill_path}: {exc}"
                ) from exc
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise ValueError(
                    f"{agent.agent_id}: skill is not valid UTF-8"
                ) from exc
        digest = sha256_bytes(raw)
        if digest != agent.skill_sha256:
            raise ValueError(
                f"{agent.agent_id}: skill hash mismatch: expected "
                f"{agent.skill_sha256}, got {digest}"
            )
        result = (text, digest)
        self._skill_cache[cache_key] = result
        return result


def parse_agent_report(raw: str) -> AgentReport:
    def unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate report key: {key}")
            result[key] = value
        return result

    try:
        data = json.loads(
            raw, object_pairs_hook=unique_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"non-finite {value}")),
        )
    except json.JSONDecodeError as exc:
        raise ValueError(f"agent report is not valid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ValueError("agent report must be a JSON object")
    required = {
        "contract",
        "agent_id",
        "task_id",
        "input_sha256",
        "status",
        "findings",
        "limitations",
        "error",
    }
    if set(data) != required:
        missing = sorted(required - set(data))
        extra = sorted(set(data) - required)
        raise ValueError(f"agent report keys mismatch: missing={missing}, extra={extra}")
    if data["contract"] != "far-subagent-report/1.0":
        raise ValueError("unsupported agent report contract")
    if not isinstance(data["findings"], list) or not isinstance(data["limitations"], list):
        raise ValueError("findings and limitations must be arrays")
    findings: list[Finding] = []
    finding_keys = {"finding_id", "claim_id", "disposition", "statement", "evidence_refs"}
    for index, item in enumerate(data["findings"]):
        if not isinstance(item, dict) or set(item) != finding_keys:
            raise ValueError(f"finding[{index}] keys mismatch")
        if not isinstance(item["evidence_refs"], list) or not all(
            isinstance(ref, str) for ref in item["evidence_refs"]
        ):
            raise ValueError(f"finding[{index}].evidence_refs must be strings")
        try:
            disposition = FindingDisposition(item["disposition"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"finding[{index}]: invalid disposition") from exc
        findings.append(
            Finding(
                finding_id=_require_str(item["finding_id"], f"finding[{index}].finding_id"),
                claim_id=_require_str(item["claim_id"], f"finding[{index}].claim_id"),
                disposition=disposition,
                statement=_require_str(item["statement"], f"finding[{index}].statement"),
                evidence_refs=tuple(item["evidence_refs"]),
            )
        )
    if not all(isinstance(item, str) for item in data["limitations"]):
        raise ValueError("limitations must contain strings")
    try:
        status = ReportStatus(data["status"])
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid report status") from exc
    error = data["error"]
    if error is not None and not isinstance(error, str):
        raise ValueError("error must be a string or null")
    return AgentReport(
        agent_id=_require_str(data["agent_id"], "agent_id"),
        task_id=_require_str(data["task_id"], "task_id"),
        input_sha256=_require_str(data["input_sha256"], "input_sha256"),
        status=status,
        findings=tuple(findings),
        limitations=tuple(data["limitations"]),
        error=error,
    )


def validate_plan(plan: OrchestrationPlan) -> None:
    ids = [agent.agent_id for agent in plan.agents]
    if not ids:
        raise ValueError("plan requires at least one agent")
    if len(ids) != len(set(ids)):
        raise ValueError("agent_id values must be unique")
    by_id = {agent.agent_id: agent for agent in plan.agents}
    if plan.coordinator_id not in by_id:
        raise ValueError("coordinator_id is not present in agents")
    coordinators = [agent for agent in plan.agents if agent.kind is AgentKind.COORDINATOR]
    if len(coordinators) != 1 or coordinators[0].agent_id != plan.coordinator_id:
        raise ValueError("plan must contain exactly one matching coordinator")
    specialists = set(by_id) - {plan.coordinator_id}
    coordinator = by_id[plan.coordinator_id]
    if set(coordinator.dependencies) != specialists:
        raise ValueError("coordinator must depend on every specialist exactly once")
    if not coordinator.receives_dependency_reports:
        raise ValueError("coordinator must receive dependency reports")
    if coordinator.dependency_view is not DependencyView.FULL:
        raise ValueError("coordinator requires full specialist reports")

    for agent in plan.agents:
        for dependency in agent.dependencies:
            if dependency not in by_id:
                raise ValueError(f"{agent.agent_id}: unknown dependency {dependency}")
            if dependency == agent.agent_id:
                raise ValueError(f"{agent.agent_id}: self dependency")
        if agent.kind is AgentKind.SPECIALIST and plan.coordinator_id in agent.dependencies:
            raise ValueError(f"{agent.agent_id}: specialist cannot depend on coordinator")
    topological_order(plan)


def topological_order(plan: OrchestrationPlan) -> tuple[str, ...]:
    by_id = {agent.agent_id: agent for agent in plan.agents}
    indegree = {agent_id: 0 for agent_id in by_id}
    children: dict[str, list[str]] = {agent_id: [] for agent_id in by_id}
    for agent in plan.agents:
        for dependency in agent.dependencies:
            indegree[agent.agent_id] += 1
            children[dependency].append(agent.agent_id)
    ready = sorted(agent_id for agent_id, degree in indegree.items() if degree == 0)
    order: list[str] = []
    while ready:
        current = ready.pop(0)
        order.append(current)
        for child in sorted(children[current]):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
                ready.sort()
    if len(order) != len(by_id):
        raise ValueError("agent dependency graph contains a cycle")
    if order[-1] != plan.coordinator_id:
        raise ValueError("coordinator must be the terminal agent")
    return tuple(order)


def detect_conflicts(reports: Sequence[AgentReport]) -> tuple[Conflict, ...]:
    by_claim: dict[str, dict[FindingDisposition, list[str]]] = {}
    for report in reports:
        if report.status is not ReportStatus.COMPLETED:
            continue
        for finding in report.findings:
            slots = by_claim.setdefault(
                finding.claim_id,
                {
                    FindingDisposition.SUPPORTS: [],
                    FindingDisposition.CONTRADICTS: [],
                },
            )
            if finding.disposition in slots:
                slots[finding.disposition].append(finding.finding_id)
    conflicts: list[Conflict] = []
    for claim_id in sorted(by_claim):
        supports = sorted(by_claim[claim_id][FindingDisposition.SUPPORTS])
        contradicts = sorted(by_claim[claim_id][FindingDisposition.CONTRADICTS])
        if supports and contradicts:
            digest = sha256_text(
                canonical_json(
                    {"claim_id": claim_id, "supports": supports, "contradicts": contradicts}
                )
            )[:16]
            conflicts.append(
                Conflict(
                    conflict_id=f"CONFLICT-{digest}",
                    claim_id=claim_id,
                    supporting_findings=tuple(supports),
                    contradicting_findings=tuple(contradicts),
                )
            )
    return tuple(conflicts)


def orchestrate(
    *,
    plan: OrchestrationPlan,
    objective: str,
    context: Sequence[ContextArtifact],
    runtime: AgentRuntime,
    run_id: str | None = None,
) -> OrchestrationResult:
    """Execute a plan with explicit-only inter-agent information flow.

    Runtime capability checks are completed for the full plan before the first call.
    Specialists see only base context plus reports from declared dependencies. A
    sequencing-only dependency can set ``receives_dependency_reports=False``. Any
    support/contradiction conflict blocks coordinator invocation; no vote or majority
    can erase it.
    """
    if not objective.strip():
        raise ValueError("objective is required")
    context_tuple = tuple(context)
    if not all(isinstance(item, ContextArtifact) for item in context_tuple):
        raise TypeError("context must contain ContextArtifact values")
    artifact_ids = [item.artifact_id for item in context_tuple]
    if len(artifact_ids) != len(set(artifact_ids)):
        raise ValueError("context artifact_id values must be unique")
    available_context = set(artifact_ids)
    for agent in plan.agents:
        if agent.context_ids is not None:
            missing = set(agent.context_ids) - available_context
            if missing:
                raise ValueError(f"{agent.agent_id}: missing context artifacts {sorted(missing)}")

    actual_run_id = run_id or _default_run_id(plan, objective, context_tuple)
    _validate_id(actual_run_id, "run_id")
    capabilities = _validate_runtime(plan, runtime)
    receipts: list[InvocationReceipt] = []

    by_id = plan.by_id
    reports: dict[str, AgentReport] = {}
    failures: list[AgentFailure] = []
    blocked: list[str] = []

    for agent_id in topological_order(plan):
        agent = by_id[agent_id]
        missing_or_failed = [
            dependency
            for dependency in agent.dependencies
            if dependency not in reports
            or reports[dependency].status is not ReportStatus.COMPLETED
        ]
        if missing_or_failed:
            blocked.append(agent_id)
            continue

        if agent.kind is AgentKind.COORDINATOR:
            current_conflicts = detect_conflicts(
                [reports[item] for item in sorted(reports)]
            )
            if current_conflicts:
                blocked.append(agent_id)
                return _result(
                    run_id=actual_run_id,
                    plan=plan,
                    status=RunStatus.BLOCKED,
                    reports=reports,
                    conflicts=current_conflicts,
                    failures=failures,
                    blocked=blocked,
                    coordinator_report=None,
                    capabilities=capabilities, receipts=receipts,
                )

        dependency_reports = (
            tuple(_project_dependency(reports[item], agent.dependency_view) for item in agent.dependencies)
            if agent.receives_dependency_reports
            else ()
        )
        visible_context = (
            context_tuple if agent.context_ids is None else
            tuple(item for item in context_tuple if item.artifact_id in agent.context_ids)
        )
        task = _build_task(
            plan=plan,
            run_id=actual_run_id,
            agent=agent,
            objective=objective,
            context=visible_context,
            dependency_reports=dependency_reports,
        )
        try:
            report = runtime.invoke(agent, task)
            _validate_report_binding(report, task)
            _validate_global_finding_ids(report, reports.values())
        except Exception as exc:
            report = AgentReport(
                agent_id=agent.agent_id,
                task_id=task.task_id,
                input_sha256=task.input_sha256,
                status=ReportStatus.FAILED,
                error=redact_outbound(f"{type(exc).__name__}: {exc}").encode(
                    "utf-8", errors="replace").decode("utf-8"),
            )
        finally:
            if isinstance(runtime, ReasonerLaneRuntime):
                receipt = runtime.take_receipt(task)
                if receipt is not None:
                    receipts.append(receipt)
        reports[agent_id] = report
        if report.status is ReportStatus.FAILED:
            failures.append(
                AgentFailure(
                    agent_id=agent.agent_id,
                    task_id=task.task_id,
                    error=report.error or "unknown runtime failure",
                )
            )

    coordinator = reports.get(plan.coordinator_id)
    conflicts = detect_conflicts([reports[item] for item in sorted(reports)])
    if failures:
        status = RunStatus.FAILED
    elif conflicts or plan.coordinator_id in blocked or coordinator is None:
        status = RunStatus.BLOCKED
    else:
        status = RunStatus.COMPLETED
    return _result(
        run_id=actual_run_id,
        plan=plan,
        status=status,
        reports=reports,
        conflicts=conflicts,
        failures=failures,
        blocked=blocked,
        coordinator_report=coordinator,
        capabilities=capabilities, receipts=receipts,
    )


def far_research_plan(root: Path | str = Path(".")) -> OrchestrationPlan:
    """Return a skill-byte-bound graph using existing FAR specialist skills.

    This plan does not claim to satisfy a clean-room or external-independence stage.
    Those stages require their separately governed frozen-input/isolation protocols.
    """
    root_path = Path(root).resolve()

    def bound(agent_id: str, skill_name: str, role: str, **kwargs) -> AgentSpec:
        skill_path = f".claude/skills/{skill_name}/SKILL.md"
        raw = (root_path / skill_path).read_bytes()
        return AgentSpec(
            agent_id=agent_id,
            skill_path=skill_path,
            skill_sha256=sha256_bytes(raw),
            role=role,
            **kwargs,
        )

    specialists = (
        bound(
            "discovery",
            "far-discovery-engine",
            "Map current evidence, alternatives, and unresolved questions.",
        ),
        bound(
            "formalizer",
            "far-formalizer",
            "Formalize exact claims, assumptions, scope, and falsifiers.",
            dependencies=("discovery",),
        ),
        bound(
            "prior-art",
            "far-prior-art-adversary",
            "Search for prior art and competing explanations without novelty inflation.",
            dependencies=("discovery",),
        ),
        bound(
            "counterexample",
            "far-counterexample-hunter",
            "Attack the formalized claim with counterexamples and boundary cases.",
            dependencies=("formalizer",),
        ),
        bound(
            "theory-audit",
            "far-theory-auditor",
            "Audit logical validity, hidden assumptions, and scope transfer.",
            dependencies=("formalizer",),
        ),
        bound(
            "quality-gate",
            "far-research-quality-gate",
            "Check evidence discipline, unresolved conflicts, and claim boundaries.",
            dependencies=(
                "discovery",
                "formalizer",
                "prior-art",
                "counterexample",
                "theory-audit",
            ),
        ),
    )
    specialists += (
        bound("canonical-source", "far-canonical-source-resolver",
              "Locate governing sources and identify provenance limits."),
        bound("claim-registry", "far-claim-registry",
              "Inspect claim identities and declared scope.", dependencies=("formalizer",)),
        bound("clean-room-audit", "far-clean-room-auditor",
              "Check isolation limitations without issuing an independent verdict."),
        bound("contradiction", "far-contradiction-detector",
              "Identify competing findings.", dependencies=("formalizer", "counterexample")),
        bound("embedding", "far-embedding-tester",
              "Check for unsupported transfer or embedding.", dependencies=("formalizer",)),
        bound("evidence-ledger", "far-evidence-ledger",
              "Check evidence traceability.", dependencies=("discovery", "canonical-source")),
        bound("project-state", "far-project-state-manager",
              "Summarize project-state implications without changing repository state.",
              dependencies=("quality-gate",)),
    )
    specialist_ids = tuple(agent.agent_id for agent in specialists)
    coordinator = bound(
        "coordinator",
        "far-research-orchestrator",
        "Integrate completed specialist reports without averaging away conflicts.",
        kind=AgentKind.COORDINATOR,
        dependencies=specialist_ids,
    )
    return OrchestrationPlan(
        plan_id="far-research-subagents-v2",
        coordinator_id="coordinator",
        agents=specialists + (coordinator,),
    )


def _validate_runtime(
    plan: OrchestrationPlan, runtime: AgentRuntime
) -> tuple[tuple[str, RuntimeCapabilities], ...]:
    verified = []
    seen_sandboxes: dict[str, str] = {}
    plan_ids = set(plan.by_id)
    for agent in plan.agents:
        capabilities = runtime.capabilities(agent)
        if type(capabilities) is not RuntimeCapabilities:
            raise TypeError("runtime must return RuntimeCapabilities")
        verified.append((agent.agent_id, capabilities))
        if capabilities.instruction_sha256 != agent.skill_sha256:
            raise ValueError(
                f"{agent.agent_id}: runtime instruction hash does not match bound skill"
            )
        if agent.requires_isolation and not capabilities.isolation_verified:
            raise ValueError(f"{agent.agent_id}: required isolation is not verified")
        if agent.clean_room and not capabilities.clean_room_verified:
            raise ValueError(f"{agent.agent_id}: clean-room isolation is not verified")
        if capabilities.repository_tools_enabled and not agent.repository_tools_allowed:
            raise ValueError(f"{agent.agent_id}: repository tools are not authorized")
        if agent.requires_isolation and capabilities.shared_state_with:
            raise ValueError(
                f"{agent.agent_id}: hidden shared state is prohibited under isolation: "
                f"{sorted(capabilities.shared_state_with)}"
            )
        shared = sorted(plan_ids.intersection(capabilities.shared_state_with))
        if shared:
            raise ValueError(
                f"{agent.agent_id}: hidden shared state with plan agents is prohibited: {shared}"
            )
        prior = seen_sandboxes.get(capabilities.sandbox_id)
        if prior is not None:
            raise ValueError(
                f"{agent.agent_id}: sandbox_id duplicates {prior}: {capabilities.sandbox_id}"
            )
        seen_sandboxes[capabilities.sandbox_id] = agent.agent_id
    return tuple(sorted(verified))


def _build_task(
    *,
    plan: OrchestrationPlan,
    run_id: str,
    agent: AgentSpec,
    objective: str,
    context: tuple[ContextArtifact, ...],
    dependency_reports: tuple[VisibleDependency, ...],
) -> AgentTask:
    payload = {
        "contract": "far-subagent-task/1.0",
        "plan_sha256": plan.sha256,
        "run_id": run_id,
        "agent_id": agent.agent_id,
        "skill_path": agent.skill_path,
        "skill_sha256": agent.skill_sha256,
        "objective": objective,
        "context": [_artifact_payload(item) for item in context],
        "dependency_reports": [_dependency_payload(item) for item in dependency_reports],
    }
    input_sha = sha256_text(canonical_json(payload))
    task_id = f"TASK-{sha256_text(run_id + chr(0) + agent.agent_id + chr(0) + input_sha)[:24]}"
    return AgentTask(
        run_id=run_id,
        task_id=task_id,
        address=f"far/{plan.plan_id}/{run_id}/{agent.agent_id}",
        agent_id=agent.agent_id,
        skill_path=agent.skill_path,
        skill_sha256=agent.skill_sha256,
        objective=objective,
        input_sha256=input_sha,
        context=context,
        dependency_reports=dependency_reports,
    )


def _validate_report_binding(report: AgentReport, task: AgentTask) -> None:
    if not isinstance(report, AgentReport):
        raise TypeError("runtime must return AgentReport")
    if report.agent_id != task.agent_id:
        raise ValueError(
            f"report agent mismatch: expected {task.agent_id}, got {report.agent_id}"
        )
    if report.task_id != task.task_id:
        raise ValueError(
            f"report task mismatch: expected {task.task_id}, got {report.task_id}"
        )
    if report.input_sha256 != task.input_sha256:
        raise ValueError("report input hash mismatch")
    visible_refs = {item.artifact_id for item in task.context}
    visible_refs.update(
        finding.finding_id
        for dependency in task.dependency_reports
        for finding in dependency.findings
    )
    for finding in report.findings:
        hidden = sorted(set(finding.evidence_refs) - visible_refs)
        if hidden:
            raise ValueError(
                f"{finding.finding_id}: evidence refs were not visible to task: {hidden}"
            )


def _validate_global_finding_ids(
    report: AgentReport, prior_reports: Iterable[AgentReport]
) -> None:
    prior = {
        finding.finding_id
        for item in prior_reports
        for finding in item.findings
    }
    duplicates = sorted(prior.intersection(item.finding_id for item in report.findings))
    if duplicates:
        raise ValueError(f"duplicate cross-agent finding_id values: {duplicates}")


def _default_run_id(
    plan: OrchestrationPlan, objective: str, context: tuple[ContextArtifact, ...]
) -> str:
    payload = {
        "plan_sha256": plan.sha256,
        "objective": objective,
        "context": [_artifact_payload(item) for item in context],
    }
    return f"RUN-{sha256_text(canonical_json(payload))[:24]}"


def _result(
    *,
    run_id: str,
    plan: OrchestrationPlan,
    status: RunStatus,
    reports: Mapping[str, AgentReport],
    conflicts: Sequence[Conflict],
    failures: Sequence[AgentFailure],
    blocked: Sequence[str],
    coordinator_report: AgentReport | None,
    capabilities: tuple[tuple[str, RuntimeCapabilities], ...],
    receipts: Sequence[InvocationReceipt],
) -> OrchestrationResult:
    ordered_reports = tuple(reports[key] for key in sorted(reports))
    payload = {
        "run_id": run_id,
        "plan_sha256": plan.sha256,
        "status": status.value,
        "reports": [_report_payload(item) for item in ordered_reports],
        "conflicts": [dataclasses.asdict(item) for item in conflicts],
        "failures": [dataclasses.asdict(item) for item in failures],
        "blocked_agents": sorted(set(blocked)),
        "runtime_capabilities": [(agent, dataclasses.asdict(cap)) for agent, cap in capabilities],
        "invocation_receipts": [dataclasses.asdict(item) for item in receipts],
        "coordinator_task_id": (
            coordinator_report.task_id if coordinator_report is not None else None
        ),
    }
    return OrchestrationResult(
        run_id=run_id,
        plan_sha256=plan.sha256,
        status=status,
        reports=ordered_reports,
        conflicts=tuple(conflicts),
        failures=tuple(failures),
        blocked_agents=tuple(sorted(set(blocked))),
        coordinator_report=coordinator_report,
        result_sha256=sha256_text(canonical_json(payload)),
        runtime_capabilities=capabilities,
        invocation_receipts=tuple(receipts),
    )


def _plan_payload(plan: OrchestrationPlan) -> dict:
    return {
        "plan_id": plan.plan_id,
        "coordinator_id": plan.coordinator_id,
        "agents": [
            {
                "agent_id": item.agent_id,
                "skill_path": item.skill_path,
                "skill_sha256": item.skill_sha256,
                "role": item.role,
                "kind": item.kind.value,
                "dependencies": list(item.dependencies),
                "receives_dependency_reports": item.receives_dependency_reports,
                "requires_isolation": item.requires_isolation,
                "repository_tools_allowed": item.repository_tools_allowed,
                "context_ids": list(item.context_ids) if item.context_ids is not None else None,
                "dependency_view": item.dependency_view.value,
                "clean_room": item.clean_room,
            }
            for item in plan.agents
        ],
    }


def _artifact_payload(artifact: ContextArtifact) -> dict:
    return {
        "artifact_id": artifact.artifact_id,
        "sha256": artifact.sha256,
        "text": artifact.text,
    }


def _finding_payload(finding: Finding) -> dict:
    return {
        "finding_id": finding.finding_id,
        "claim_id": finding.claim_id,
        "disposition": finding.disposition.value,
        "statement": finding.statement,
        "evidence_refs": list(finding.evidence_refs),
    }


def _report_payload(report: AgentReport) -> dict:
    return {
        "agent_id": report.agent_id,
        "task_id": report.task_id,
        "input_sha256": report.input_sha256,
        "status": report.status.value,
        "findings": [_finding_payload(item) for item in report.findings],
        "limitations": list(report.limitations),
        "error": report.error,
    }


def _project_dependency(report: AgentReport, view: DependencyView) -> VisibleDependency:
    return VisibleDependency(
        agent_id=report.agent_id,
        task_id=report.task_id,
        view=view,
        claim_ids=tuple(sorted({item.claim_id for item in report.findings})),
        findings=report.findings if view is not DependencyView.CLAIMS_ONLY else (),
        limitations=report.limitations if view is DependencyView.FULL else (),
    )


def _dependency_payload(report: VisibleDependency) -> dict:
    payload = {"agent_id": report.agent_id, "task_id": report.task_id, "view": report.view.value}
    if report.view is DependencyView.CLAIMS_ONLY:
        payload["claim_ids"] = list(report.claim_ids)
    else:
        payload["findings"] = [_finding_payload(item) for item in report.findings]
        if report.view is DependencyView.FULL:
            payload["limitations"] = list(report.limitations)
    return payload


def _redacted_task_payload(
    agent: AgentSpec, task: AgentTask, skill_text: str
) -> dict:
    instructions = redact_outbound(skill_text)
    context = [_artifact_payload(
        ContextArtifact.from_text(item.artifact_id, redact_outbound(item.text))
    ) for item in task.context]
    dependencies = [_dependency_payload(item) for item in task.dependency_reports]
    for dependency in dependencies:
        for finding in dependency.get("findings", ()):
            finding["statement"] = redact_outbound(finding["statement"])
        if "limitations" in dependency:
            dependency["limitations"] = [redact_outbound(item) for item in dependency["limitations"]]
    payload = {
        "contract": "far-subagent-task/1.0",
        "response_contract": "far-subagent-report/1.0",
        "agent": {
            "agent_id": agent.agent_id,
            "role": redact_outbound(agent.role),
            "skill_path": agent.skill_path,
            "skill_sha256": sha256_text(instructions),
            "instructions": instructions,
        },
        "task": {
            "run_id": task.run_id,
            "task_id": task.task_id,
            "address": task.address,
            "objective": redact_outbound(task.objective),
            "context": context,
            "dependency_reports": dependencies,
        },
        "rules": [
            "return exactly one JSON object matching far-subagent-report/1.0",
            "separate evidence from inference",
            "preserve unknowns and limitations",
            "do not infer truth from agreement or agent count",
            "do not claim authority beyond the assigned role",
        ],
    }
    # Routing identities and references must remain exact. Reject the packet
    # rather than rewriting identities or exposing credential-shaped metadata.
    serialized = canonical_json(payload)
    if redact_outbound(serialized) != serialized:
        raise ValueError("credential-shaped metadata or unredacted prompt")
    return payload


def _validate_id(value: str, label: str) -> None:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ValueError(f"{label} must match {_ID.pattern}")


def _require_str(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    value.encode("utf-8")
    return value
