"""Join locked three-arm ForecastBench forecasts to independently sourced resolutions.

Never fetch an oracle or assign outcomes inside the forecasting runner.
Source integrity and registration times require external independent review.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

from evaluation.prospective_forecast_runner import ARMS, SHARED, digest
from evaluation.worldview_truth_discovery_ablation import (
    VERSION, AblationError, _time, _digest, score
)


def _identity(row):
    return (row["source"], row["id"], row["resolution_date"])


def join_resolutions(forecast, resolution, *, registered_at,
                     protocol_sha256, data_class="synthetic"):
    if forecast.get("status") != "PRE_SUBMISSION_REQUIRES_EXTERNAL_LOCK":
        raise AblationError("only complete on-time pre-submission runs are eligible")
    if (not isinstance(forecast.get("predictions"), list) or
            len(forecast["predictions"]) != forecast.get("units_total", -1) * len(ARMS)):
        raise AblationError("incomplete forecast run")
    _digest(forecast.get("question_set_sha256"))
    _digest(protocol_sha256)
    reg = _time(registered_at)
    lock = _time(forecast.get("completed_at"))
    if reg >= lock:
        raise AblationError("protocol registration must precede prediction lock")
    if not isinstance(resolution, dict) or resolution.get("version") != "FAR-WORLD-RESOLVE/0.1":
        raise AblationError("invalid independently sourced resolution set")
    if resolution.get("question_set_sha256") != forecast["question_set_sha256"]:
        raise AblationError("resolution file refers to different question snapshot")
    events = resolution.get("events")
    if not isinstance(events, list):
        raise AblationError("resolution events must be an array")
    outcomes = {}
    for row in events:
        if not isinstance(row, dict) or set(row) != {
                "source", "id", "resolution_date", "value", "observed_at", "source_uri"}:
            raise AblationError("malformed resolution")
        key = _identity(row)
        if key in outcomes or type(row["value"]) is not bool:
            raise AblationError("duplicate event or non-Boolean outcome")
        if not isinstance(row["source_uri"], str) or not row["source_uri"]:
            raise AblationError("source URI missing")
        if _time(row["observed_at"]) <= lock:
            raise AblationError("resolution must be observed after all forecasts locked")
        outcomes[key] = row
    matrix = {}
    for row in forecast["predictions"]:
        if not isinstance(row, dict) or row.get("arm") not in ARMS:
            raise AblationError("invalid forecast arm")
        key = _identity(row)
        if (key, row["arm"]) in matrix:
            raise AblationError("duplicate arm forecast")
        _digest(row.get("raw_response_sha256"))
        _digest(row.get("question_sha256"))
        if type(row.get("probability")) not in (float, int) or not 0 <= row["probability"] <= 1:
            raise AblationError("invalid forecast probability")
        matrix[(key, row["arm"])] = row
    keys = {key for key, arm in matrix}
    if set(outcomes) - keys:
        raise AblationError("resolution event not in locked forecast set")
    if any((key, arm) not in matrix for key in keys for arm in ARMS):
        raise AblationError("not every question has all three arms")
    cases = []
    for key, event in sorted(outcomes.items(), key=lambda pair: str(pair[0])):
        rows = {arm: matrix[(key, arm)] for arm in ARMS}
        evidence = {row["question_sha256"] for row in rows.values()}
        if len(evidence) != 1:
            raise AblationError("different evidence between arms")
        mechanism = digest({"model_id": forecast.get("model_id"),
                            "shared_prompt": SHARED})
        forecasts = {}
        for arm, row in rows.items():
            p = format(row["probability"], ".6f").rstrip("0").rstrip(".")
            forecasts[arm] = {
                "p": p, "locked_at": forecast["completed_at"],
                "evidence_sha256": row["question_sha256"],
                "mechanism_sha256": mechanism,
                "artifact_sha256": row["raw_response_sha256"],
            }
        cases.append({
            "id": digest({"source": key[0], "id": key[1], "horizon": key[2]}),
            "domain": "empirical",
            "outcome": {"value": event["value"], "observed_at": event["observed_at"],
                        "source_uri": event["source_uri"]},
            "forecasts": forecasts,
        })
    study = {
        "version": VERSION,
        "study_id": forecast["dataset"] + "::" + forecast["model_id"],
        "data_class": data_class,
        "registered_at": registered_at,
        "protocol_sha256": protocol_sha256,
        "cases": cases,
    }
    # Always run the full scorer to catch missing fields and invalid p.
    return study, score(study)


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Join externally adjudicated outcomes to prior forecasts")
    parser.add_argument("forecast", type=Path)
    parser.add_argument("resolutions", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--registered-at", required=True)
    parser.add_argument("--protocol-sha256", required=True)
    parser.add_argument("--data-class", choices=("synthetic", "prospective"),
                        default="synthetic")
    args = parser.parse_args(argv)
    try:
        f = json.loads(args.forecast.read_text(encoding="utf-8"))
        o = json.loads(args.resolutions.read_text(encoding="utf-8"))
        study, result = join_resolutions(f, o, registered_at=args.registered_at,
                                         protocol_sha256=args.protocol_sha256,
                                         data_class=args.data_class)
        if args.output.exists():
            raise AblationError("refuse to overwrite existing scored record")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(study, indent=2, sort_keys=True) + "\n",
                               encoding="utf-8")
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
