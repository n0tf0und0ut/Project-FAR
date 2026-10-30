"""Bounded question-driven candidate discovery for a supplied deterministic model.

No model weights, hooks, source authenticity or real-world interventions are
attested here. The caller supplies *executable* forward and explanation functions;
findings are candidates until independently traced into FAR-MECH documents.
"""
from __future__ import annotations

from decimal import Decimal
import re
from typing import Callable, Sequence

from .mechanistic_fidelity import (
    MechanismAuditError, _kl, _fmt, _number, _probabilities,
)


def search_counterexamples(
    inputs: Sequence[str],
    *,
    observed_activation: Callable[[str], str],
    explained_activation: Callable[[str], str],
    baseline_activation: Callable[[str], str],
    output_distribution: Callable[[str, str], list[str]],
    max_cases: int = 256,
) -> list[dict]:
    """Deterministically enumerate candidate inputs and rank KL degradation.

    Output is untrusted, uncited probe data. A mechanism-audit source attachment
    and external-replay record are required before any evidentiary promotion.
    """
    if type(max_cases) is not int or not 1 <= max_cases <= 256:
        raise MechanismAuditError("max_cases out of supported range")
    if isinstance(inputs, (str, bytes)) or not isinstance(inputs, (list, tuple)):
        raise MechanismAuditError("inputs must be a finite list/tuple")
    if not inputs or len(inputs) > max_cases:
        raise MechanismAuditError("input cohort empty or exceeds bound")
    if any(not isinstance(x, str) or not x or len(x) > 128 for x in inputs):
        raise MechanismAuditError("invalid search input")
    if len(set(inputs)) != len(inputs):
        raise MechanismAuditError("duplicate input in probe cohort")

    findings = []
    for key in inputs:
        actual = observed_activation(key)
        predicted = explained_activation(key)
        baseline = baseline_activation(key)
        if not all(isinstance(z, str) and re.fullmatch(
                r"-?(?:0|[1-9][0-9]{0,2})(?:\.[0-9]{1,6})?", z)
                   for z in (actual, predicted, baseline)):
            raise MechanismAuditError("activation functions must return bounded decimal strings")
        a, p, b = _number(actual), _number(predicted), _number(baseline)
        if any(not x.is_finite() for x in (a, p, b)):
            raise MechanismAuditError("nonfinite model activation")
        original = _probabilities(output_distribution(key, actual))
        replaced = _probabilities(output_distribution(key, predicted))
        comparison = _probabilities(output_distribution(key, baseline))
        if not (len(original) == len(replaced) == len(comparison)):
            raise MechanismAuditError("candidate output dimensions differ")
        delta = _kl(original, replaced) - _kl(original, comparison)
        if delta > Decimal(0):
            findings.append((delta, {
                "input_key": key,
                "activation_error": _fmt(abs(a - p)),
                "replacement_kl": _fmt(_kl(original, replaced)),
                "baseline_kl": _fmt(_kl(original, comparison)),
                "delta_kl": _fmt(delta),
                "classification": "UNVERIFIED_ADVERSARIAL_CANDIDATE",
            }))
    # Rank by the unrounded loss difference with a stable tie-break.
    return [record for _, record in sorted(findings, key=lambda x: (-x[0], x[1]["input_key"]))]
