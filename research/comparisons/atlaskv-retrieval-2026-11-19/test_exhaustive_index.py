"""Defect-detecting synthetic exhaustive index-space controls."""
from exhaustive_index_audit import run


def test_index_space_mismatch_exhaustive():
    record = run()
    assert record["upstream_commit"] == "61e3abc1fb09fbfb426cfc847c4c26c5e94bcaeb"
    assert record["results"] == {
        "intermediate_top1": {"cases": 180, "mismatches": 124},
        "intermediate_top100": {"cases": 180, "mismatches": 180},
        "leaf_top1": {"cases": 180, "mismatches": 124},
        "leaf_top100": {"cases": 180, "mismatches": 166},
    }

