"""Route FAR task packets to native Codex sessions through a local mailbox.

An external controller dispatches each request to a real native subagent and
publishes its exact report. This runtime neither invokes a provider directly
nor establishes isolation, authentication of a controller, or independence.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import stat
import tempfile
import time
from pathlib import Path

from tools.adversarial_research_harness import ReasonerLane
from tools.subagent_orchestration import (
    ContextArtifact,
    OrchestrationResult,
    ReasonerLaneRuntime,
    RunStatus,
    canonical_json,
    far_research_plan,
    orchestrate,
    sha256_bytes,
    sha256_text,
)

MAX_RESPONSE_BYTES = 256 * 1024
REQUEST_SCHEMA = "far-native-codex-request/1"
RESPONSE_SCHEMA = "far-native-codex-response/1"


def publish_once(path: Path, value: object) -> None:
    """Make a complete message visible without overwriting any prior evidence."""
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(canonical_json(value).encode("utf-8"))
            stream.flush()
            os.link(temporary, path)
        finally:
            temporary.unlink()


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate mailbox key: {key}")
        result[key] = value
    return result


def _read_response(path: Path) -> bytes:
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    with os.fdopen(os.open(path, flags), "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("mailbox response must be a regular file")
        raw = stream.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ValueError("mailbox response exceeds byte limit")
    return raw


def _parse_response(raw: bytes) -> dict:
    record = json.loads(raw, object_pairs_hook=_unique_pairs)
    if not isinstance(record, dict) or set(record) != {
        "schema", "request_sha256", "native_agent_id", "report",
    }:
        raise ValueError("unexpected mailbox response fields")
    return record


def publish_native_report(request_path: Path, native_agent_id: str, report: str) -> None:
    """Relay a native worker's exact report after observing its dispatch."""
    suffix = ".request.json"
    if not request_path.name.endswith(suffix):
        raise ValueError("expected a native request filename")
    response_path = request_path.with_name(
        request_path.name.removesuffix(suffix) + ".response.json"
    )
    publish_once(response_path, {
        "schema": RESPONSE_SCHEMA,
        "request_sha256": sha256_bytes(request_path.read_bytes()),
        "native_agent_id": native_agent_id,
        "report": report,
    })


@dataclasses.dataclass(frozen=True, slots=True)
class NativeMailboxReceipt:
    task_id: str
    agent_id: str
    request_sha256: str
    response_sha256: str | None = None
    native_agent_id: str | None = None
    report_sha256: str | None = None


class NativeCodexMailbox:
    """A fresh, bounded exchange. Native agent IDs are controller declarations."""

    def __init__(self, directory: Path, *, timeout: float = 180) -> None:
        if not 0 < timeout <= 600:
            raise ValueError("mailbox timeout must be in (0, 600]")
        directory.mkdir(mode=0o700, parents=False, exist_ok=False)
        self.directory = directory
        self.timeout = timeout
        self._native_agents: set[str] = set()
        self._receipts: dict[str, NativeMailboxReceipt] = {}

    @property
    def receipts(self) -> tuple[NativeMailboxReceipt, ...]:
        return tuple(self._receipts.values())

    def exchange(self, agent_id: str, prompt: str, task_id: str) -> str:
        stem = sha256_text(task_id)
        request_path = self.directory / f"{stem}.request.json"
        response_path = self.directory / f"{stem}.response.json"
        request = {
            "schema": REQUEST_SCHEMA,
            "agent_id": agent_id,
            "task_id": task_id,
            "prompt": prompt,
        }
        request_sha256 = sha256_text(canonical_json(request))
        publish_once(request_path, request)
        receipt = NativeMailboxReceipt(task_id, agent_id, request_sha256)
        self._receipts[task_id] = receipt
        deadline = time.monotonic() + self.timeout
        while (remaining := deadline - time.monotonic()) > 0:
            try:
                response_bytes = _read_response(response_path)
            except FileNotFoundError:
                time.sleep(min(0.1, remaining))
                continue
            receipt = dataclasses.replace(receipt, response_sha256=sha256_bytes(response_bytes))
            self._receipts[task_id] = receipt
            if time.monotonic() < deadline:
                break
        else:
            raise TimeoutError(f"native Codex response timed out for {agent_id}")
        response = _parse_response(response_bytes)
        if response["schema"] != RESPONSE_SCHEMA or response["request_sha256"] != request_sha256:
            raise ValueError("mailbox response is not bound to the dispatched request")
        native_agent_id = response["native_agent_id"]
        report = response["report"]
        if not isinstance(native_agent_id, str) or not native_agent_id.strip():
            raise ValueError("mailbox response requires a native agent ID")
        if native_agent_id in self._native_agents:
            raise ValueError("native agent ID already used in this run")
        if not isinstance(report, str):
            raise ValueError("mailbox report must preserve the worker's exact text")
        try:
            native_agent_id.encode("utf-8")
            report_sha256 = sha256_text(report)
        except UnicodeEncodeError as exc:
            raise ValueError("mailbox worker ID and report must be valid UTF-8") from exc
        self._native_agents.add(native_agent_id)
        self._receipts[task_id] = dataclasses.replace(
            receipt, native_agent_id=native_agent_id, report_sha256=report_sha256,
        )
        return report


def run_native_codex(
    root: Path, mailbox: NativeCodexMailbox, objective: str,
    context: tuple[ContextArtifact, ...], run_id: str | None = None,
) -> OrchestrationResult:
    reference = far_research_plan(root)
    plan = dataclasses.replace(
        reference, plan_id="far-research-native-codex-i0-v1",
        agents=tuple(dataclasses.replace(agent, requires_isolation=False)
                     for agent in reference.agents),
    )
    lanes = {}
    for agent in plan.agents:
        agent_id = agent.agent_id
        lanes[agent_id] = ReasonerLane(
            provider_id=agent_id,
            model_identity="native-codex-collaboration-model-unattested",
            sandbox_id=f"native-codex-lane-{agent_id}",
            reasoner=lambda prompt, task_id, role=agent_id: mailbox.exchange(role, prompt, task_id),
            isolation_verified=False,
        )
    return orchestrate(
        plan=plan, objective=objective, context=context, run_id=run_id,
        runtime=ReasonerLaneRuntime(lanes, root=root),
    )


def _context(argument: str) -> ContextArtifact:
    artifact_id, separator, path = argument.partition("=")
    if not separator or not path:
        raise argparse.ArgumentTypeError("context must be ID=FILE")
    try:
        return ContextArtifact.from_text(artifact_id, Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--mailbox", type=Path, required=True)
    parser.add_argument("--objective", required=True)
    parser.add_argument("--context", type=_context, action="append", default=[])
    parser.add_argument("--run-id")
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args()
    mailbox = NativeCodexMailbox(args.mailbox, timeout=args.timeout)
    result = run_native_codex(args.root, mailbox, args.objective, tuple(args.context), args.run_id)
    publish_once(mailbox.directory / "result.json", {
        "schema": "far-native-codex-result/1",
        "assurance": "I0 internal collaboration; provider identity and isolation unattested",
        "orchestration": dataclasses.asdict(result),
        "mailbox_receipts": [dataclasses.asdict(item) for item in mailbox.receipts],
        "mailbox_receipts_sha256": sha256_text(canonical_json({
            "orchestration_sha256": result.result_sha256,
            "receipts": [dataclasses.asdict(item) for item in mailbox.receipts],
        })),
    })
    return 0 if result.status is RunStatus.COMPLETED else 1


if __name__ == "__main__":
    raise SystemExit(main())
