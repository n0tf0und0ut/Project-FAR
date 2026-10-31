"""Export complete FAR three-arm runs as official ForecastBench submission JSON.

Only formatting. Never submits, registers, verifies data, or falsifies a date.
Requires explicit truthful team/creator names and model variant identification.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys

from evaluation.prospective_forecast_runner import ARMS, MARKET, ProspectiveError


def export_sets(run, *, organization, model_organization):
    if not isinstance(run, dict) or run.get("status") != "PRE_SUBMISSION_REQUIRES_EXTERNAL_LOCK":
        raise ProspectiveError("only complete on-time real runs may be exported")
    for name, value in (("organization", organization),
                        ("model_organization", model_organization)):
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,70}", value):
            raise ProspectiveError("unsafe or empty " + name)
    selected = run.get("units_selected")
    total = run.get("units_total")
    predictions = run.get("predictions")
    if (type(selected) is not int or type(total) is not int or selected != total
            or total <= 0 or not isinstance(predictions, list)
            or len(predictions) != 3 * total):
        raise ProspectiveError("incomplete question coverage")
    due = run.get("forecast_due_date")
    if not isinstance(due, str) or run.get("dataset") != due + "-llm.json":
        raise ProspectiveError("question set/due date mismatch")
    model_id = run.get("model_id")
    if not isinstance(model_id, str) or not model_id.strip():
        raise ProspectiveError("model identity required")
    results = {arm: [] for arm in ARMS}
    seen = set()
    units = set()
    for row in predictions:
        if not isinstance(row, dict) or row.get("arm") not in ARMS:
            raise ProspectiveError("invalid arm")
        arm = row["arm"]
        source = row.get("source")
        qid = row.get("id")
        horizon = row.get("resolution_date")
        p = row.get("probability")
        if (not isinstance(source, str) or not isinstance(qid, str) or not qid
                or (source in MARKET and horizon is not None)
                or (source not in MARKET and not isinstance(horizon, str))
                or type(p) not in (int, float) or not math.isfinite(p) or not 0 <= p <= 1):
            raise ProspectiveError("invalid official forecast fields")
        ident = (source, qid, horizon)
        pair = (ident, arm)
        if pair in seen:
            raise ProspectiveError("duplicate forecast")
        seen.add(pair)
        units.add(ident)
        reasoning = row.get("reasoning")
        if not isinstance(reasoning, str):
            raise ProspectiveError("missing reasoning string")
        results[arm].append({"id": qid, "source": source, "forecast": p,
                             "resolution_date": horizon, "reasoning": reasoning})
    if len(units) != total or any(len(results[a]) != total for a in ARMS):
        raise ProspectiveError("missing arms or incorrect unit coverage")
    output = {}
    for arm in ARMS:
        output[arm] = {
            "organization": organization,
            "model": model_id + " [" + arm + " prompt]",
            "model_organization": model_organization,
            "question_set": run["dataset"],
            "forecasts": sorted(results[arm], key=lambda x: (x["source"], x["id"],
                          x["resolution_date"] or "")),
        }
    return output


def main(argv=None):
    p = argparse.ArgumentParser(description="Export three ForecastBench files; no upload")
    p.add_argument("record", type=Path)
    p.add_argument("output_dir", type=Path)
    p.add_argument("--organization", required=True)
    p.add_argument("--model-organization", required=True)
    args = p.parse_args(argv)
    try:
        run = json.loads(args.record.read_text(encoding="utf-8"))
        files = export_sets(run, organization=args.organization,
                            model_organization=args.model_organization)
        root = args.output_dir
        targets = {arm: root / (
            run["forecast_due_date"] + "." + args.organization + "." +
            str(i + 1) + ".json") for i, arm in enumerate(ARMS)}
        if any(path.exists() for path in targets.values()):
            raise ProspectiveError("refusing to overwrite submitted or staged file")
        root.mkdir(parents=True, exist_ok=True)
        for arm in ARMS:
            targets[arm].write_text(json.dumps(files[arm], indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps({arm: str(path) for arm, path in targets.items()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
