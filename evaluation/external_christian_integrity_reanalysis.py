"""Independent exact reanalysis of published ICMI-016 experimental counts.

Author-reported aggregates are inputs; raw trajectories are not independently
reproduced, and the reported outcome is research integrity, not factual accuracy.
"""
from fractions import Fraction
from math import comb

COUNTS = {
    "unconditioned": (16, 71),
    "christian": (5, 59),
    "secular": (4, 60),
    "christian_anchored": (2, 118),
    "secular_anchored": (12, 120),
}
COMPARISONS = (
    ("christian", "unconditioned"),
    ("secular", "unconditioned"),
    ("christian", "secular"),
    ("christian_anchored", "christian"),
    ("secular_anchored", "secular"),
)


def fisher_two_sided(a_success, a_total, b_success, b_total):
    """Probability-ordering Fisher exact two-sided p, in rational arithmetic."""
    values = (a_success, a_total, b_success, b_total)
    if any(type(x) is not int for x in values):
        raise ValueError("integer counts required")
    if not (0 <= a_success <= a_total and 0 <= b_success <= b_total
            and a_total > 0 and b_total > 0):
        raise ValueError("invalid counts")
    n = a_total + b_total
    k = a_success + b_success
    denominator = comb(n, a_total)
    lower = max(0, a_total - (n - k))
    upper = min(a_total, k)

    def probability(x):
        return Fraction(comb(k, x) * comb(n-k, a_total-x), denominator)

    observed = probability(a_success)
    return sum((probability(x) for x in range(lower, upper+1)
                if probability(x) <= observed), Fraction())


def report():
    return {
        "paper": "ICMI-016 (working paper, 2026-04-19)",
        "metric": "verified benchmark answer-key decryption and submission",
        "disclaimer": "published author counts independently recalculated, not raw traces independently audited",
        "arms": {k: {"events": v[0], "total": v[1],
                     "rate": round(v[0] / v[1], 6)}
                 for k, v in COUNTS.items()},
        "comparisons": [
            {"arms": [a, b],
             "p_two_sided": round(float(fisher_two_sided(*COUNTS[a], *COUNTS[b])), 6),
             "bonferroni_5_sensitivity": round(min(1.0, 5 * float(
                 fisher_two_sided(*COUNTS[a], *COUNTS[b]))), 6)}
            for a, b in COMPARISONS
        ],
        "interpretation": (
            "Christian and secular prompts both reduced shortcut cheating versus "
            "unconditioned; no established Christian-specific accuracy gain"
        ),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(report(), indent=2))
