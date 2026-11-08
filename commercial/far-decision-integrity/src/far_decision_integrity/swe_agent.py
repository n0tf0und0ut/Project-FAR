from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .external_trace import ExternalEvent, ExternalTrace, ProvenanceKind, SourceLocation
from .strict_json import loads_strict


OBSERVATION_TYPES = frozenset({"observation", "tool-output", "tool_output", "tool-result", "tool_result"})


def load_swe_agent_trace(path: str | Path, *, trace_id: str | None = None) -> ExternalTrace:
    source = Path(path)
    try:
        payload = loads_strict(source.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"unable to load SWE-agent trajectory: {exc}") from exc

    records = _records(payload)
    events: list[ExternalEvent] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            continue
        actor = _first_text(record, "role", "actor", "agent") or "unknown"
        message_type = (_first_text(record, "message_type", "type") or "").lower().replace(" ", "_")
        content = _first_text(record, "content", "message", "text", "thought")
        action = record.get("action") or record.get("tool_call") or record.get("command")
        observation = record.get("observation") or record.get("result") or record.get("output")

        # SWE-agent trajectories also encode observations as typed messages, for
        # example {"message_type": "observation", "message": "..."}. Treating
        # those as agent messages loses the environment/tool-output distinction.
        if message_type in OBSERVATION_TYPES and observation is None and content is not None:
            observation = content
            content = None
            actor = "environment"

        if content:
            events.append(_event(source.name, index, len(events), actor, "message", content, {}))
        if action is not None:
            statement, attributes = _describe("Tool/action invocation", action)
            events.append(_event(source.name, index, len(events), actor, "tool-call", statement, attributes))
        if observation is not None:
            statement, attributes = _describe("Recorded tool/action output", observation)
            events.append(_event(source.name, index, len(events), "environment", "tool-output", statement, attributes))

    resolved_id = trace_id or source.stem
    return ExternalTrace(
        trace_id=resolved_id,
        source_format="swe-agent-trajectory",
        events=tuple(events),
        complete=False,
    )


def _records(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("trajectory", "history", "messages", "steps", "events"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
    raise ValueError("SWE-agent trajectory must contain a list of records")


def _first_text(record: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _describe(prefix: str, value: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(value, str):
        return f"{prefix}: {value}", {"raw_value": value}
    serialized = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return f"{prefix}: {serialized}", {"raw_value": value}


def _event(
    artifact: str,
    record_index: int,
    sequence: int,
    actor: str,
    event_type: str,
    statement: str,
    attributes: dict[str, Any],
) -> ExternalEvent:
    return ExternalEvent(
        event_id=f"event-{sequence:06d}",
        sequence=sequence,
        actor=actor,
        event_type=event_type,
        statement=statement,
        provenance=ProvenanceKind.OBSERVED,
        source=SourceLocation(artifact, str(record_index)),
        attributes=attributes,
    )
