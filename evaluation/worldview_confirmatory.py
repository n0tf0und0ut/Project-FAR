"""Conservative, reproducible paired analysis of a FAR worldview ablation.

Neither creates forecasts nor authenticates timestamps, source records, model
versions, preregistration, independence, or outcome labels. No study may
self-certify an empirical truth-discovery advantage.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
import random
from statistics import NormalDist

from evaluation.worldview_truth_discovery_ablation import score, _probability, AblationError

ARMS = ("neutral", "orthodox", "placebo")
PAIRS = ("neutral", "placebo")
SEED_DOMAIN = "FAR-WORLD-CONFIRMATORY/0.1"


def _percentile(xs: list[float], p: float) -> float:
    ordered = sorted(xs)
    if not ordered:
        raise AblationError("cannot estimate uncertainty with zero samples")
    idx = p * (len(ordered) - 1)
    lo, hi = math.floor(idx), math.ceil(idx)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (idx - lo)


def recommended_minimum(delta: float = 0.02, paired_sd: float = 0.2,
                        familywise_alpha: float = 0.05, power: float = 0.8,
                        comparisons: int = 2) -> int:
    """Conservative normal-approximation planning, not achieved statistical power."""
    if not (math.isfinite(delta) and delta > 0 and math.isfinite(paired_sd)
            and paired_sd > 0 and 0 < familywise_alpha < 1
            and 0 < power < 1 and type(comparisons) is int
            and comparisons >= 1):
        raise ValueError("invalid prespecified power parameters")
    normal = NormalDist()
    z_alpha = normal.inv_cdf(1 - familywise_alpha / (2 * comparisons))
    z_beta = normal.inv_cdf(power)
    return math.ceil(((z_alpha + z_beta) * paired_sd / delta) ** 2)


def analyze(document: dict, clusters: dict[str, str], *, bootstrap=4096,
            minimum_independent_clusters=200, effect_threshold=0.02) -> dict:
    """Calculate paired Brier-loss contrasts with source-blocked uncertainty.

    Investigator-supplied cluster identities are not verified. Returned
    statistical candidates always require external audit and replication.
    """
    baseline = score(document)
    if type(bootstrap) is not int or not 512 <= bootstrap <= 32768:
        raise AblationError("bootstrap repetitions must be 512..32768")
    if type(minimum_independent_clusters) is not int or minimum_independent_clusters < 2:
        raise AblationError("minimum independent clusters must be integer >=2")
    if type(effect_threshold) is not float or not math.isfinite(effect_threshold) or effect_threshold <= 0:
        raise AblationError("effect threshold must be positive finite float")
    ids = [c["id"] for c in document["cases"]]
    if (not isinstance(clusters, dict) or set(clusters) != set(ids)
            or any(not isinstance(v, str) or not v.strip()
                   for v in clusters.values())):
        raise AblationError("every case must have a nonempty declared source cluster")
    groups: dict[str, list[dict]] = defaultdict(list)
    for case in document["cases"]:
        y = float(case["outcome"]["value"])
        probs = {arm: float(_probability(case["forecasts"][arm]["p"])) for arm in ARMS}
        groups[clusters[case["id"]]].append({
            arm: (probs["orthodox"] - y) ** 2 - (probs[arm] - y) ** 2
            for arm in PAIRS
        })
    keys = sorted(groups)
    if not keys:
        return {**baseline, "independent_clusters_claimed": 0,
                "status": "NO_DATA", "statistical_candidate": False,
                "assurance": "NO_EXTERNAL_TRUTH_EVIDENCE"}
    n = len(ids)
    observed = {arm: sum(d[arm] for group in groups.values() for d in group) / n
                for arm in PAIRS}
    input_record = {"document": document, "clusters": clusters, "method": SEED_DOMAIN}
    raw = json.dumps(input_record, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    rng = random.Random(int(digest[:16], 16))
    values = {arm: [] for arm in PAIRS}
    for _ in range(bootstrap):
        sampled = [keys[rng.randrange(len(keys))] for _ in keys]
        total = sum(len(groups[k]) for k in sampled)
        for arm in PAIRS:
            values[arm].append(sum(d[arm] for k in sampled for d in groups[k]) / total)
    upper = {arm: _percentile(values[arm], 0.975) for arm in PAIRS}
    candidate = (len(groups) >= minimum_independent_clusters and
                 all(observed[a] <= -effect_threshold and upper[a] < 0 for a in PAIRS))
    return {**baseline,
        "paired_mean_brier_difference": {a: round(v, 8) for a, v in observed.items()},
        "simultaneous_95pct_upper_bound": {a: round(v, 8) for a, v in upper.items()},
        "independent_clusters_claimed": len(groups),
        "cases_per_cluster_max": max(len(v) for v in groups.values()),
        "seed_input_sha256": digest,
        "method": "SOURCE_BLOCK_BOOTSTRAP_BONFERRONI_TWO_ONE_SIDED_UPPER_97_5",
        "bootstrap_repetitions": bootstrap,
        "effect_threshold": effect_threshold,
        "statistical_candidate": candidate if document["data_class"] == "prospective" else False,
        "assurance": "EXTERNAL_INDEPENDENCE_OUTCOMES_AND_PREREGISTRATION_UNVERIFIED",
        "status": ("SYNTHETIC_TEST_ONLY" if document["data_class"] == "synthetic"
                   else "PROSPECTIVE_UNVERIFIED_REQUIRES_INDEPENDENT_AUDIT"),
    }


def main(argv=None):
    """Emit reproducible conditional statistical report, never a proof verdict."""
    import argparse
    from pathlib import Path
    import sys
    parser = argparse.ArgumentParser(description="Compute blocked paired worldview ablation uncertainty")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("clusters", type=Path, help="JSON map: case_id -> independent source/event cluster")
    parser.add_argument("--bootstrap", type=int, default=4096)
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        clusters = json.loads(args.clusters.read_text(encoding="utf-8"))
        result = analyze(manifest, clusters, bootstrap=args.bootstrap)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
