"""Research-only CPU index-space stress test for AtlasKV hierarchical pruning.

Reference: HKUST-KnowComp/AtlasKV @ 61e3abc1fb09fbfb426cfc847c4c26c5e94bcaeb,
src/atlaskv/models/llama3_model.py:193-217 and 511-566.

Executes source_pruning_witness's transcribed prune_key operation, not the
trained AtlasKV model. Enumerates synthetic subset positions and local winners.
Failures are NOT empirical model-error rates.
"""
from __future__ import annotations

from itertools import combinations
import json
import torch
from source_pruning_witness import upstream_prune_key, UPSTREAM_COMMIT


def run():
    n_global = 6
    global_ids = torch.tensor([10 * (i + 1) for i in range(n_global)])
    results = {key: {"cases": 0, "mismatches": 0} for key in (
        "intermediate_top1", "intermediate_top100", "leaf_top1", "leaf_top100"
    )}
    with torch.no_grad():
        for width in range(2, n_global):
            for positions in combinations(range(n_global), width):
                selected_ids = global_ids[list(positions)]
                for winner in range(width):
                    logits = torch.full((1, 1, 1, width), -9.0)
                    logits[0, 0, 0, winner] = 9.0
                    for topk, suffix in ((1, "top1"), (100, "top100")):
                        observed_inter = upstream_prune_key(logits, global_ids, topk_size=topk)
                        actual_inter = [int(v) for v in observed_inter.reshape(-1)]
                        expected_inter = [int(selected_ids[winner])] if topk == 1 else selected_ids.tolist()
                        intermediate = results["intermediate_" + suffix]
                        intermediate["cases"] += 1
                        intermediate["mismatches"] += actual_inter != expected_inter

                        observed_local = upstream_prune_key(logits, None, topk_size=topk)
                        actual_leaf_positions = ([int(observed_local)] if topk == 1 else list(observed_local))
                        expected_leaf_positions = ([positions[winner]] if topk == 1 else list(positions))
                        leaf = results["leaf_" + suffix]
                        leaf["cases"] += 1
                        leaf["mismatches"] += actual_leaf_positions != expected_leaf_positions
    return {
        "status": "Research",
        "scope": "Synthetic isolated index-space checks; not native model inference or model failure frequency",
        "upstream_commit": UPSTREAM_COMMIT,
        "global_count": n_global,
        "subset_sizes": [2, 3, 4, 5],
        "results": results,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))

