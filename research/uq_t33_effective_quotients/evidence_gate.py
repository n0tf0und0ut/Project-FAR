"""Research-only, finite-explicit forward-simulation evidence checker.

A passing report proves a statement about the DECLARED source transition model,
not about an independently observed device, executable, or real-world system.
"""
from __future__ import annotations

import hashlib
import json
from itertools import product
from typing import Any

from research.uq_t33_effective_quotients.finite_state import quotient, observation


class EvidenceError(ValueError):
    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code


def _require(condition: bool, code: str, detail: str) -> None:
    if not condition:
        raise EvidenceError(code, detail)


def _table(name: str, table: Any) -> tuple[list[str], list[str], list[Any], list[list[int]]]:
    _require(isinstance(table, dict), "SCHEMA", f"{name} must be an object")
    states, actions, outputs, transitions = (table.get(k) for k in
                                            ("states", "actions", "outputs", "transitions"))
    _require(isinstance(states, list) and bool(states), "STATES", f"{name} needs nonempty states")
    _require(all(isinstance(s, str) and s for s in states) and len(set(states)) == len(states),
             "STATES", f"{name} state names must be distinct nonempty strings")
    _require(isinstance(actions, list) and all(isinstance(a, str) and a for a in actions)
             and len(set(actions)) == len(actions), "ACTIONS", f"{name} action names invalid")
    _require(isinstance(outputs, list) and len(outputs) == len(states)
             and all(type(o) in (str, int, bool, type(None)) for o in outputs),
             "OUTPUTS", f"{name} must supply primitive typed outputs for every state")
    _require(isinstance(transitions, list) and len(transitions) == len(states),
             "TOTALITY", f"{name} must supply a transition row for every state")
    n = len(states)
    for i, row in enumerate(transitions):
        _require(isinstance(row, list) and len(row) == len(actions),
                 "TOTALITY", f"{name} row {i} lacks a complete action definition")
        _require(all(type(v) is int and 0 <= v < n for v in row),
                 "CLOSURE", f"{name} row {i} leaves the declared state set")
    return states, actions, outputs, transitions


def certificate(model: dict[str, Any]) -> dict[str, Any]:
    """Check full finite concrete-to-abstract Moore-machine homomorphism.

    The concrete state domain and admitted action alphabet are *assumed* complete
    as interpretations of the externally supplied system. That premise is not
    inferred from matching examples, metadata, or a caller's declaration.
    """
    _require(isinstance(model, dict), "SCHEMA", "expected a certificate object")
    concrete = model.get("concrete")
    abstract = model.get("abstract")
    c_states, c_actions, c_out, c_delta = _table("concrete", concrete)
    a_states, a_actions, a_out, a_delta = _table("abstract", abstract)
    _require(c_actions == a_actions, "ACTION_COVERAGE", "the admitted alphabets differ")
    # Only a canonical digest of the *submitted finite source table* is checked.
    # It is not evidence that this table is the actual system implementation.
    source_bytes = json.dumps(concrete, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=False).encode("utf-8")
    digest = hashlib.sha256(source_bytes).hexdigest()
    expected = model.get("expected_concrete_table_sha256")
    _require(isinstance(expected, str) and expected == digest, "SOURCE_DIGEST",
             "submitted concrete table differs from its recorded digest")
    mapping = model.get("abstraction")
    _require(isinstance(mapping, list) and len(mapping) == len(c_states)
             and all(type(s) is int and 0 <= s < len(a_states) for s in mapping),
             "MAPPING", "every concrete state must map to an abstract state")
    _require(type(model.get("claimed_state_bound")) is int
             and model["claimed_state_bound"] >= len(a_states), "BOUND",
             "the claimed bound must cover the full abstract carrier")
    for s in range(len(c_states)):
        _require(type(c_out[s]) is type(a_out[mapping[s]])
                 and c_out[s] == a_out[mapping[s]], "OUTPUT_FIDELITY",
                 f"state {c_states[s]} does not preserve the observable output")
        for a in range(len(c_actions)):
            _require(mapping[c_delta[s][a]] == a_delta[mapping[s]][a],
                     "TRANSITION_FIDELITY",
                     f"state {c_states[s]} on action {c_actions[a]} violates transition commutation")
    classes, _ = quotient(tuple(a_out), tuple(tuple(row) for row in a_delta))
    return {
        "result": "FINITE_TABLE_REFINEMENT_VERIFIED",
        "authority": "DECLARED_MODELS_ONLY",
        "external_system_correspondence": "NOT_VERIFIED",
        "source_table_sha256": digest,
        "source_states": len(c_states),
        "abstract_states": len(a_states),
        "behavioral_classes_in_abstract_model": len(set(classes)),
        "word_length_bound": max(len(a_states) - 2, 0),
        "verified_output_obligations": len(c_states),
        "verified_transition_obligations": len(c_states) * len(c_actions),
    }


def witness(model: dict[str, Any], first: int, second: int) -> tuple[int, ...] | None:
    """Distinguishing word for two concrete states, conditional on certificate."""
    report = certificate(model)
    concrete, abstract = model["concrete"], model["abstract"]
    _require(all(type(s) is int and 0 <= s < len(concrete["states"]) for s in (first, second)),
             "QUERY", "invalid concrete initial state")
    x, y = model["abstraction"][first], model["abstraction"][second]
    outs, steps = abstract["outputs"], abstract["transitions"]
    for length in range(report["word_length_bound"] + 1):
        for word in product(range(len(abstract["actions"])), repeat=length):
            if observation(outs, steps, x, word) != observation(outs, steps, y, word):
                return word
    return None
