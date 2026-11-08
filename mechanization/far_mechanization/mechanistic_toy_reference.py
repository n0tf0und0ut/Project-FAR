"""Deterministic six-decimal toy network for reproducible research tests only.

It is intentionally *not* a neural-network mechanistic result. A clipped ReLU
response creates a sharp, real downstream sensitivity to activation error.
"""
from __future__ import annotations

from decimal import Decimal

SIX = Decimal("0.000001")
ZERO = Decimal(0)
WIDTH = Decimal("0.010000")
START = Decimal("0.990000")
SLOPE = Decimal("60")


def model_probabilities(activation: str) -> list[str]:
    z = Decimal(activation)
    clipped = min(WIDTH, max(ZERO, z - START))
    p0 = (Decimal("0.800000") - SLOPE * clipped).quantize(SIX)
    return [format(p0, "f"), format((Decimal(1) - p0).quantize(SIX), "f")]


def replay_case(case: dict) -> bool:
    return all(
        model_probabilities(case[activation]) == case[probabilities]
        for activation, probabilities in (
            ("observed_activation", "original_probs"),
            ("explained_activation", "replacement_probs"),
            ("baseline_activation", "baseline_probs"),
        )
    )
