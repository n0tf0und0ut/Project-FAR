#!/usr/bin/env python3
"""Replay frozen internal observations with two explicitly limited controls."""
from __future__ import annotations
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mechanization.far_mechanization.cognitive import CognitiveDocument, audit

FOLDER = ROOT / "research/cognitive-audit"
CORPUS = FOLDER / "frozen-v1/cases.json"
REPORT = FOLDER / "internal-001-r3-results.json"
FREEZE = FOLDER / "freeze-v3.json"


def encoded(data):
    return (json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode()


def generic_argument_control(data):
    """Lexical control on the same source bundle; no model or external service."""
    text = " ".join(x["text"] for x in data["sources"]).lower()
    return "SUPPORTED" if any(x in text for x in ("therefore deliberately lied", "no evidence therefore absent", "valid so true")) else "UNKNOWN"


def structured_evidence_control(data):
    """Limited support/lineage control; no psychological or pair analysis."""
    facts = data["probes"][0]["facts"]
    if "premise_support" in facts:
        return {"REFUTED": "SUPPORTED", "ESTABLISHED": "CONTRADICTED", "UNKNOWN": "UNKNOWN"}[facts["premise_support"]]
    if "claimed_verified" in facts:
        if not facts["claimed_verified"]:
            return "CONTRADICTED"
        if facts["locator_state"] == "UNRESOLVED":
            return "SUPPORTED"
        return {"SUPPORTED": "CONTRADICTED", "CONTRADICTED": "SUPPORTED", "UNKNOWN": "UNKNOWN"}[facts["passage_support"]]
    if "claimed_independent_count" in facts:
        rows = [x for x in data["source_lineage"] if x["source_id"] in facts["source_refs"]]
        if any(x["relationship"] == "unknown" for x in rows):
            return "UNKNOWN"
        roots = {r for x in rows for r in x["root_lineage_ids"]}
        return "SUPPORTED" if facts["claimed_independent_count"] > len(roots) else "CONTRADICTED"
    return "UNKNOWN"


def separate_checks(cases):
    """Independent finite truth-table and rational arithmetic, not label voting."""
    witnesses = [{"inconsistent": conflict, "knows_false": knows, "intends_deception": intent}
                 for conflict in (False, True) for knows in (False, True) for intent in (False, True)
                 if conflict and not knows and not intent]
    updates = []
    for row in cases:
        data = row["input"]
        f = data["probes"][0]["facts"]
        if data["probes"][0]["rule"] != "bayes-mismatch":
            continue
        snapshots = {x["id"]: x["hypothesis_probabilities"] for x in data["epistemic_document"]["snapshots"]}
        p = Fraction(snapshots[f["prior_snapshot"]][f["hypothesis"]])
        a, b = p * Fraction(f["likelihood_if_true"]), (1-p) * Fraction(f["likelihood_if_false"])
        # Round exact rational to six places, ties-to-even; independent of Decimal.
        if a+b:
            exact = a/(a+b)
            rounded = Fraction(round(exact * 1000000), 1000000)
            mismatch = rounded != Fraction(snapshots[f["posterior_snapshot"]][f["hypothesis"]])
            status = "SUPPORTED" if mismatch else "CONTRADICTED"
        else:
            exact, status = None, "UNKNOWN"
        updates.append({"id": row["id"], "exact_posterior": str(exact) if exact is not None else None,
                        "status": status, "matches_frozen_reference": status == row["reference_status"]})
    return {"intent_countermodels": witnesses, "binary_update_checks": updates,
            "other_labels": "PROJECT_AUTHORED_CODING_NOT_INDEPENDENT_ORACLE"}


def metrics(rows, arm):
    c = Counter()
    for row in rows:
        ref, got = row["reference_status"], row["predictions"][arm]["status"]
        c["total"] += 1
        c["status_" + got] += 1
        c["exact_status_match"] += got == ref
        if ref in ("SUPPORTED", "CONTRADICTED"):
            c["binary_reference_cases"] += 1
            if got not in ("SUPPORTED", "CONTRADICTED"):
                c["binary_abstentions"] += 1
            else:
                c[{("SUPPORTED", "SUPPORTED"): "tp", ("CONTRADICTED", "SUPPORTED"): "fp",
                   ("SUPPORTED", "CONTRADICTED"): "fn", ("CONTRADICTED", "CONTRADICTED"): "tn"}[ref, got]] += 1
        else:
            c["unresolved_reference_cases"] += 1
            c["unresolved_correct_disposition"] += got == ref
    return {key: c[key] for key in ("total", "exact_status_match", "binary_reference_cases", "tp", "fp", "fn", "tn", "binary_abstentions", "unresolved_reference_cases", "unresolved_correct_disposition", "status_SUPPORTED", "status_CONTRADICTED", "status_UNKNOWN", "status_ABSTAIN", "status_ERROR")}


def evaluate():
    freeze = json.loads(FREEZE.read_text())
    for path, expected in freeze["file_sha256"].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != expected:
            raise ValueError("frozen source changed: " + path)
    cases = json.loads(CORPUS.read_text())["cases"]
    rows = []
    arms = ("far_cog", "generic_argument_control", "structured_evidence_control")
    for case in cases:
        data, predictions = case["input"], {}
        for name, run in zip(arms, (lambda x: audit(CognitiveDocument.from_dict(x)),
                                   lambda x: {"status": generic_argument_control(x)},
                                   lambda x: {"status": structured_evidence_control(x)})):
            try:
                result = run(data)
                predictions[name] = {"status": result["diagnoses"][0]["status"], "result": result} if name == "far_cog" else result
            except (ValueError, KeyError, TypeError) as exc:
                predictions[name] = {"status": "ERROR", "error": str(exc)}
        rows.append({"id": case["id"], "rule": data["probes"][0]["rule"], "reference_status": case["reference_status"],
                     "stability_group": case["stability_group"], "predictions": predictions})
    groups = sorted({x["stability_group"] for x in rows if x["stability_group"]})
    return {"campaign": "FAR-COG-INTERNAL-001", "status": "Research", "freeze": freeze,
            "label_assurance": "PROJECT_AUTHORED_IMPLEMENTATION_EXPOSED", "external_effectiveness": "OPEN",
            "diagnostic_calibration": "UNAVAILABLE_NO_DIAGNOSTIC_PROBABILITIES",
            "metrics": {a: metrics(rows, a) for a in arms},
            "by_rule": {r: {a: metrics([x for x in rows if x["rule"] == r], a) for a in arms} for r in sorted({x["rule"] for x in rows})},
            "stability": {g: {a: {"cases": [x["id"] for x in rows if x["stability_group"] == g], "stable": len({x["predictions"][a]["status"] for x in rows if x["stability_group"] == g}) == 1} for a in arms} for g in groups},
            "separate_checks": separate_checks(cases), "predictions": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true"); mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        result = evaluate(); raw = encoded(result)
        if args.write:
            if REPORT.exists() and REPORT.read_bytes() != raw:
                raise ValueError("preserve previous run; name a successor run before changing predictions")
            REPORT.write_bytes(raw)
        elif REPORT.read_bytes() != raw:
            raise ValueError("committed run does not replay")
        print(json.dumps(result["metrics"], sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(str(exc), file=sys.stderr); return 2


if __name__ == "__main__":
    raise SystemExit(main())
