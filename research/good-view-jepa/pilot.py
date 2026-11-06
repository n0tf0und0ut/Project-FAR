"""Research-only independent-view JEPA retrieval pilot; NEVER a FAR verifier.

Requires optional torch and numpy; does not download data/models or use network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import time

SCHEMA = "far-good-view-jepa-data/0.1"
SPLITS = ("train", "calibration", "test")
CONDITIONS = ("untrained", "pca", "bad_view", "good_view")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def validate(data):
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise ValueError("incorrect dataset schema")
    rows = data.get("items")
    if not isinstance(rows, list) or not 48 <= len(rows) <= 5000:
        raise ValueError("dataset must contain 48-5000 records")
    seen, families, dimensions = set(), {}, {}
    counts = {s: 0 for s in SPLITS}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("item must be an object")
        ident, split = row.get("id"), row.get("split")
        if not isinstance(ident, str) or not ident or ident in seen or split not in SPLITS:
            raise ValueError("duplicate/invalid item ID or split")
        seen.add(ident)
        counts[split] += 1
        family = row.get("family_id")
        if not isinstance(family, str) or not family:
            raise ValueError("missing family_id")
        if family in families and families[family] != split:
            raise ValueError("family leakage across splits")
        families[family] = split
        if row.get("stance") not in ("supports", "opposes", "unknown"):
            raise ValueError("missing or invalid stance")
        if not isinstance(row.get("source_id"), str) or not row["source_id"]:
            raise ValueError("source_id required; retrieval never verifies it")
        for mod in ("text", "image"):
            views = row.get(mod)
            if not isinstance(views, list) or len(views) < 2:
                raise ValueError("each modality needs at least two views")
            for view in views:
                if not isinstance(view, list) or not 2 <= len(view) <= 512:
                    raise ValueError("invalid vector length")
                if any(type(v) not in (int, float) or not math.isfinite(v) for v in view):
                    raise ValueError("vectors must contain finite numbers")
                d = len(view)
                if mod in dimensions and dimensions[mod] != d:
                    raise ValueError("inconsistent modality dimensions")
                dimensions[mod] = d
    if any(counts[s] < 8 for s in SPLITS) or counts["train"] < 32:
        raise ValueError("insufficient data in one or more splits")
    return counts


def synthetic(seed=1729, per_split=(120, 48, 48)):
    """Clearly labeled simulated vectors; no raw text or actual image encoding."""
    import numpy as np
    rng = np.random.default_rng(seed)
    matrices = {m: rng.normal(size=(10, 32)).astype("float32") / 3 for m in ("text", "image")}
    rows = []
    for split, families in zip(SPLITS, per_split):
        for j in range(families):
            base = rng.normal(size=10)
            for stance, sign in (("supports", 1), ("opposes", -1)):
                latent = base.copy()
                latent[0] = sign * 1.25
                item = {"id": f"{split}-{j:04d}-{stance}", "split": split,
                        "family_id": f"{split}-{j:04d}", "stance": stance,
                        "source_id": f"synthetic:{split}:{j}:{stance}"}
                for mod in ("text", "image"):
                    signal = latent @ matrices[mod]
                    item[mod] = [(signal + 1.2 * rng.normal(size=32)).astype(float).tolist()
                                 for _ in range(2)]
                rows.append(item)
    result = {"schema": SCHEMA, "origin": "synthetic-only", "generator_seed": seed, "items": rows}
    validate(result)
    return result


def features(data, modality):
    import numpy as np
    groups = {s: [r for r in data["items"] if r["split"] == s] for s in SPLITS}
    # The input contract permits extra views; training and evaluation use the first two.
    x = {s: np.asarray([r[modality][:2] for r in rs], dtype="float32") for s, rs in groups.items()}
    train = x["train"].reshape(-1, x["train"].shape[-1])
    mu, sd = train.mean(axis=0), np.maximum(train.std(axis=0), 1e-5)
    return {s: (value - mu) / sd for s, value in x.items()}


def train_encoder(inputs, condition, seed, steps, width):
    import numpy as np
    import torch
    torch.manual_seed(seed)
    torch.set_num_threads(1)
    d = inputs["train"].shape[-1]
    if condition == "pca":
        train = inputs["train"][:, 0]
        _, _, vt = np.linalg.svd(train - train.mean(axis=0), full_matrices=False)
        directions = vt[:width].T
        return {s: arr[:, 0] @ directions for s, arr in inputs.items()}, 0.0
    network = torch.nn.Sequential(torch.nn.Linear(d, 64), torch.nn.ReLU(), torch.nn.Linear(64, width))
    optimizer = torch.optim.Adam(network.parameters(), lr=0.003)
    original = torch.as_tensor(inputs["train"], dtype=torch.float32)
    generator = torch.Generator().manual_seed(seed + 50000)
    start = time.perf_counter()
    if condition != "untrained":
        for _ in range(steps):
            idx = torch.randint(len(original), (min(128, len(original)),), generator=generator)
            first = original[idx, 0]
            if condition == "good_view":
                second = original[idx, 1]
            else:
                mask = (torch.rand(first.shape, generator=generator) > 0.25).float()
                second = first * mask
            z1, z2 = network(first), network(second)
            invariance = (z1 - z2).square().mean()
            variance = (torch.relu(1 - (z1.var(0, unbiased=False) + 1e-4).sqrt()).mean()
                        + torch.relu(1 - (z2.var(0, unbiased=False) + 1e-4).sqrt()).mean()) / 2
            center1, center2 = z1 - z1.mean(0), z2 - z2.mean(0)
            cov1 = center1.T @ center1 / len(idx)
            cov2 = center2.T @ center2 / len(idx)
            offdiag = ~torch.eye(width, dtype=torch.bool)
            covariance = (cov1[offdiag].square().mean() + cov2[offdiag].square().mean()) / 2
            loss = invariance + 4 * variance + 0.04 * covariance
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
    network.eval()
    with torch.no_grad():
        transformed = {s: network(torch.as_tensor(arr[:, 0], dtype=torch.float32)).numpy()
                       for s, arr in inputs.items()}
    return transformed, time.perf_counter() - start


def opposing_labels(left, right):
    return (left == "supports" and right == "opposes") or (left == "opposes" and right == "supports")


def evaluate(text_encoded, image_encoded, test_rows):
    import numpy as np
    x, y = image_encoded["calibration"], text_encoded["calibration"]
    mx, my = x.mean(0), y.mean(0)
    u, _, vt = np.linalg.svd((x - mx).T @ (y - my), full_matrices=False)
    rotation = u @ vt
    q = (image_encoded["test"] - mx) @ rotation
    c = text_encoded["test"] - my
    q = q / np.maximum(np.linalg.norm(q, axis=1, keepdims=True), 1e-8)
    c = c / np.maximum(np.linalg.norm(c, axis=1, keepdims=True), 1e-8)
    similarity = q @ c.T
    ranks = np.argsort(-similarity, axis=1, kind="stable")
    true_ranks = np.asarray([int(np.flatnonzero(row == i)[0]) + 1 for i, row in enumerate(ranks)])
    opposition = 0
    sibling_wins = 0
    sibling_count = 0
    for i, row in enumerate(test_rows):
        j = int(ranks[i, 0])
        if (test_rows[j]["family_id"] == row["family_id"] and
                opposing_labels(row["stance"], test_rows[j]["stance"])):
            opposition += 1
        siblings = [j for j, other in enumerate(test_rows) if j != i and
                    other["family_id"] == row["family_id"] and opposing_labels(row["stance"], other["stance"])]
        for j in siblings:
            sibling_count += 1
            sibling_wins += int(similarity[i, i] > similarity[i, j])
    return {"recall_at_1": round(float((true_ranks == 1).mean()), 6),
            "recall_at_5": round(float((true_ranks <= 5).mean()), 6),
            "mrr": round(float((1 / true_ranks).mean()), 6),
            "opposition_top1_rate": round(opposition / len(test_rows), 6),
            "stance_discrimination": round(sibling_wins / sibling_count, 6) if sibling_count else None,
            "n_queries": len(test_rows)}


def run(data, seeds=(11, 29, 47), steps=200, width=8):
    import numpy as np
    import torch
    if not isinstance(seeds, (tuple, list)) or len(set(seeds)) != len(seeds) or not seeds:
        raise ValueError("seeds must be distinct")
    if not 1 <= steps <= 2000 or not 2 <= width <= 32:
        raise ValueError("invalid training parameters")
    counts = validate(data)
    encoded = {m: features(data, m) for m in ("text", "image")}
    if width > min(encoded[m]["train"].shape[-1] for m in encoded):
        raise ValueError("width exceeds modality dimensions")
    test_rows = [r for r in data["items"] if r["split"] == "test"]
    results = []
    for seed in seeds:
        metrics = {}
        for cond in CONDITIONS:
            reps = {}
            seconds = 0.0
            for m, salt in (("text", 0), ("image", 1000)):
                reps[m], duration = train_encoder(encoded[m], cond, seed + salt, steps, width)
                seconds += duration
            metrics[cond] = {**evaluate(reps["text"], reps["image"], test_rows),
                             "train_wall_seconds": round(seconds, 4)}
        results.append({"seed": seed, "conditions": metrics})
    delta = [r["conditions"]["good_view"]["recall_at_1"] - r["conditions"]["bad_view"]["recall_at_1"] for r in results]
    vs_pca = [r["conditions"]["good_view"]["recall_at_1"] - r["conditions"]["pca"]["recall_at_1"] for r in results]
    return {"schema": "far-good-view-jepa-result/0.1", "dataset_sha256": hashlib.sha256(canonical(data)).hexdigest(),
            "dataset_origin": data.get("origin", "unverified-external"), "counts": counts,
            "method": "independent-per-modality VICReg-style encoders; calibration-only orthogonal map",
            "config": {"seeds": list(seeds), "steps": steps, "width": width},
            "environment": {"python": platform.python_version(), "torch": torch.__version__, "numpy": np.__version__,
                            "cpu_only": not torch.cuda.is_available()},
            "runs": results, "good_minus_bad_r1": [round(x, 6) for x in delta],
            "good_minus_pca_r1": [round(x, 6) for x in vs_pca],
            "production_eligibility": False, "external_effectiveness_established": False,
            "factual_correctness_evaluated": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sources = parser.add_mutually_exclusive_group(required=True)
    sources.add_argument("--synthetic", action="store_true")
    sources.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--width", type=int, default=8)
    args = parser.parse_args()
    data = synthetic() if args.synthetic else json.loads(args.input.read_text(encoding="utf-8"))
    result = run(data, steps=args.steps, width=args.width)
    args.output.write_bytes(canonical(result) + b"\n")
    print(json.dumps({"output": str(args.output), "dataset_sha256": result["dataset_sha256"],
                      "deltas": result["good_minus_bad_r1"], "delta_vs_pca": result["good_minus_pca_r1"]}))


if __name__ == "__main__":
    main()
