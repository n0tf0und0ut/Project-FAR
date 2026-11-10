#!/usr/bin/env python3
"""Retrospective keyword retrieval baseline over a frozen FAR Research snapshot.

This is a document-ranking diagnostic, not an agent, scientific validator, or
evidence promotion mechanism. No new knowledge claims are introduced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_FIXTURE = HERE / "frozen-v0.1.json"
STOP = frozenset(
    "a an and are as at be by can did do does for from has have how in into "
    "is it its of on or our that the their these this to was were what when "
    "where which who why with far project record records source sources "
    "which evidence observation observations research".split()
)


def tokens(value: str) -> frozenset[str]:
    if not isinstance(value, str):
        raise ValueError("retrieval text must be a string")
    return frozenset(re.findall(r"[a-z0-9]+", value.lower())) - STOP


def strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    out: dict[str, object] = {}
    for name, value in pairs:
        if name in out:
            raise ValueError(f"duplicate JSON key: {name}")
        out[name] = value
    return out


def load_fixture(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=strict_object)
    if obj.get("format") != "far-cross-investigation-retrieval-baseline/0.1":
        raise ValueError("wrong fixture format")
    if obj.get("frozen_before_scoring") is not True:
        raise ValueError("benchmark is not frozen")
    source = {row["id"]: row for row in obj["sources"]}
    records = {row["id"]: row for row in obj["records"]}
    if len(source) != len(obj["sources"]) or len(records) != len(obj["records"]):
        raise ValueError("duplicate source/record id")
    case_ids: set[str] = set()
    for row in obj["records"]:
        if row["kind"] == "observation":
            parent = source.get(row["source_id"])
            if not parent or row["source_sha256"] != parent["sha256"]:
                raise ValueError(f"source binding mismatch: {row['id']}")
    for case in obj["cases"]:
        if case["id"] in case_ids:
            raise ValueError("duplicate case id")
        case_ids.add(case["id"])
        gold = case["gold_ids"]
        if len(set(gold)) != len(gold):
            raise ValueError(f"duplicate gold id: {case['id']}")
        for name in gold:
            if name not in records or not records[name]["active"]:
                raise ValueError(f"missing/inactive gold: {case['id']} {name}")
        if (not gold) != (case["control"] == "unanswerable_source"):
            raise ValueError(f"invalid control: {case['id']}")
    if not obj["cases"] or not obj["records"]:
        raise ValueError("empty fixture")
    return obj


def verify_source_bytes(fixture: dict, source_path: Path) -> None:
    """Check exact Git blob bytes and bound synthesis metadata; fail on drift."""
    raw = source_path.read_bytes()
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    pinned = fixture["snapshot"]
    if blob != pinned["synthesis_git_blob_sha1"]:
        raise ValueError("source bytes differ from pinned synthesis Git blob")
    obj = json.loads(raw, object_pairs_hook=strict_object)
    for key in ("corpus_sha256", "synthesis_input_sha256", "inventory_sha256"):
        if obj.get(key) != pinned[key]:
            raise ValueError(f"synthesis metadata drift: {key}")
    sources = {s["id"]: s for s in obj["sources"]}
    for src in fixture["sources"]:
        current = sources.get(src["id"])
        if current is None or any(current.get(k) != src[k] for k in
                                  ("path", "sha256", "evidence_usable",
                                   "review_status", "primary_evidence_verified")):
            raise ValueError(f"source metadata mismatch: {src['id']}")
    observations = {r["id"]: r for r in obj["observations"]}
    conclusions = {r["id"]: r for r in obj["conclusions"]}
    mechanisms = {r["id"]: r for r in obj["mechanisms"]}
    if len(fixture["records"]) != len(observations) + len(conclusions) + len(mechanisms):
        raise ValueError("source record count differs")
    for row in fixture["records"]:
        if row["kind"] == "observation":
            origin = observations[row["id"]]
            checks = ("statement", "active", "source_id", "source_sha256",
                      "relation", "scope_key", "epistemic_class")
        elif row["kind"] == "conclusion":
            origin = conclusions[row["id"]]
            checks = ("statement", "epistemic_class", "disposition")
        else:
            origin = mechanisms[row["id"]]
            if row["text"] != origin["name"] + " " + origin["literal_comparison"]:
                raise ValueError(f"mechanism text changed: {row['id']}")
            continue
        for key in checks:
            candidate = row["text"] if key == "statement" else row[key]
            if candidate != origin[key]:
                raise ValueError(f"snapshot record differs: {row['id']} {key}")


def admissible(row: dict, sources: dict[str, dict]) -> bool:
    if not row["active"]:
        return False
    if row["kind"] != "observation":
        return True
    source = sources[row["source_id"]]
    return source["evidence_usable"] is True and source["primary_evidence_verified"] is True


def ranking(records: list[dict], question: str, k: int = 5) -> list[dict]:
    """Deterministic lexical IDF baseline, no synonym expansion or learned model."""
    if k < 1:
        raise ValueError("k must be positive")
    query = tokens(question)
    if not query:
        return []
    doc_tokens = [(row, tokens(row["text"] + " " + row.get("uncertainty", "")
                                + " " + row.get("counterevidence", "")))
                  for row in records]
    counts: Counter[str] = Counter()
    for _, terms in doc_tokens:
        counts.update(terms)
    n = len(doc_tokens)
    ranked = []
    for row, terms in doc_tokens:
        common = query.intersection(terms)
        if not common:
            continue
        score = sum(math.log((n + 1) / (counts[t] + 1)) + 1 for t in common)
        score /= math.sqrt(max(1, len(terms)))
        ranked.append((score, row["id"], row))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [{"id": ident, "kind": row["kind"], "score": round(score, 8),
             "source_id": row.get("source_id"), "epistemic_class": row.get("epistemic_class"),
             "state": row.get("disposition", row.get("state"))}
            for score, ident, row in ranked[:k]]


def evaluate(fixture: dict, k: int = 5) -> dict:
    sources = {src["id"]: src for src in fixture["sources"]}
    documents = [r for r in fixture["records"] if admissible(r, sources)]
    results, positive_recalls, reciprocal_ranks, control_results = [], [], [], []
    for case in fixture["cases"]:
        hits = ranking(documents, case["question"], k)
        returned = [row["id"] for row in hits]
        gold = set(case["gold_ids"])
        covered = [name for name in returned if name in gold]
        if gold:
            recall = len(covered) / len(gold)
            rr = next((1 / (i + 1) for i, name in enumerate(returned) if name in gold), 0.0)
            positive_recalls.append(recall)
            reciprocal_ranks.append(rr)
        else:
            recall = None
            rr = None
            control_results.append(not returned)
        results.append({"id": case["id"], "question": case["question"],
                        "control": case["control"], "gold_ids": case["gold_ids"],
                        "retrieved": hits, "recall_at_k": recall,
                        "reciprocal_rank": rr, "abstained": not returned})
    return {"format": "far-knowledge-retrieval-result/0.1", "status": "Research",
            "method": "fixed unsupervised lexical IDF ranker on frozen corpus projection",
            "k": k, "documents_indexed": len(documents), "cases": len(results),
            "positive_cases": len(positive_recalls), "negative_controls": len(control_results),
            "macro_recall_at_k": sum(positive_recalls) / len(positive_recalls),
            "mrr_at_k": sum(reciprocal_ranks) / len(reciprocal_ranks),
            "unanswerable_abstention_rate": (sum(control_results) / len(control_results)
                                            if control_results else None),
            "snapshot": fixture["snapshot"], "case_results": results,
            "limits": ["Internal authored gold; no independent adjudication.",
                       "Measures only lexical retrieval, not correctness of generated answers.",
                       "Source metadata inherited from repository; no new source authentication.",
                       "This is a comparator over FAR corpus records, not a claim that FAR "
                       "currently exposes this retrieval algorithm as a native API."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--verify-source", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()
    fixture = load_fixture(args.fixture)
    if args.verify_source is not None:
        verify_source_bytes(fixture, args.verify_source)
    result = evaluate(fixture, args.k)
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
