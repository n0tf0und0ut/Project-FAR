"""FAR-WORLD-EVAL/0.1: blinded-outcome scoring for worldview truth-discovery ablation.

This runner never generates forecasts or outcomes and cannot prove that a human
source or a researcher's preregistration is authentic. Prospective evidence
requires independent validation outside this tool. Synthetic fixtures are
exclusively implementation checks, not scientific performance evidence.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
import re
import json
from pathlib import Path
import sys

VERSION = "FAR-WORLD-EVAL/0.1"
ARMS = ("neutral", "orthodox", "placebo")
ZERO = Decimal("0")
ONE = Decimal("1")


class AblationError(ValueError):
    pass


def _keys(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise AblationError(f"{label} must contain exactly {sorted(keys)}")


def _time(value):
    if not isinstance(value, str):
        raise AblationError("timestamp must be a string")
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AblationError("invalid timestamp") from exc
    if date.tzinfo is None or date.utcoffset() is None:
        raise AblationError("timezone offset required")
    return date


def _probability(value):
    if not isinstance(value, str) or not re.fullmatch(r"(?:0(?:\.[0-9]{1,6})?|1(?:\.0{1,6})?)", value):
        raise AblationError("probability must be a bounded decimal between 0 and 1")
    try:
        n = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise AblationError("invalid decimal") from exc
    if not n.is_finite() or not ZERO <= n <= ONE or value != format(n, "f"):
        raise AblationError("probability outside [0, 1] or noncanonical")
    return n


def _digest(value):
    if not isinstance(value, str) or len(value) != 64:
        raise AblationError("digest must be a 64-digit lowercase sha256")
    if any(c not in "0123456789abcdef" for c in value):
        raise AblationError("invalid sha256")
    return value


def score(document):
    """Calculate exactly paired Brier losses; never infer causation from a score.

    No aggregate status can mean theological truth or product superiority.
    """
    _keys(document, ("version", "study_id", "data_class", "registered_at",
                     "protocol_sha256", "cases"), "document")
    if document["version"] != VERSION:
        raise AblationError("unsupported evaluation version")
    if document["data_class"] not in ("synthetic", "prospective"):
        raise AblationError("unsupported study class")
    if not isinstance(document["study_id"], str) or not document["study_id"].strip():
        raise AblationError("study_id missing")
    registered_at = _time(document["registered_at"])
    _digest(document["protocol_sha256"])
    cases = document["cases"]
    if not isinstance(cases, list):
        raise AblationError("cases must be array")
    losses = {arm: [] for arm in ARMS}
    changes = {"orthodox_vs_neutral": 0, "orthodox_vs_placebo": 0}
    ids = set()
    for case in cases:
        _keys(case, ("id", "domain", "outcome", "forecasts"), "case")
        if not isinstance(case["id"], str) or not case["id"] or case["id"] in ids:
            raise AblationError("missing or duplicate case id")
        ids.add(case["id"])
        if case["domain"] != "empirical":
            raise AblationError("non-empirical outcomes cannot be used for truth-accuracy uplift")
        outcome = case["outcome"]
        _keys(outcome, ("value", "observed_at", "source_uri"), "outcome")
        if type(outcome["value"]) is not bool or not isinstance(outcome["source_uri"], str) or not outcome["source_uri"]:
            raise AblationError("outcome must be independently sourced Boolean")
        observed_at = _time(outcome["observed_at"])
        if observed_at <= registered_at:
            raise AblationError("outcome must postdate protocol registration")
        forecasts = case["forecasts"]
        if not isinstance(forecasts, dict) or set(forecasts) != set(ARMS):
            raise AblationError("neutral, orthodox, placebo required per case")
        matching = set()
        estimates = {}
        for arm in ARMS:
            row = forecasts[arm]
            _keys(row, ("p", "locked_at", "evidence_sha256",
                        "mechanism_sha256", "artifact_sha256"), f"{arm} forecast")
            locked = _time(row["locked_at"])
            if locked < registered_at or locked >= observed_at:
                raise AblationError("forecast not locked between registration and outcome")
            matching.add((_digest(row["evidence_sha256"]), _digest(row["mechanism_sha256"])))
            _digest(row["artifact_sha256"])
            p = _probability(row["p"])
            estimates[arm] = p
            y = ONE if outcome["value"] else ZERO
            losses[arm].append((p - y) ** 2)
        if len(matching) != 1:
            raise AblationError("arms must use matched evidence and causal-mechanism commitments")
        changes["orthodox_vs_neutral"] += estimates["orthodox"] != estimates["neutral"]
        changes["orthodox_vs_placebo"] += estimates["orthodox"] != estimates["placebo"]

    if not cases:
        return {"version": VERSION, "study_id": document["study_id"], "n": 0,
                "status": "NO_DATA", "assurance": "NO_TRUTH_DISCOVERY_EVIDENCE"}
    n = Decimal(len(cases))
    mean = {arm: sum(losses[arm], ZERO) / n for arm in ARMS}
    differences = {
        "orthodox_minus_neutral": mean["orthodox"] - mean["neutral"],
        "orthodox_minus_placebo": mean["orthodox"] - mean["placebo"],
    }
    # The mere claim of prospective collection is not independently verifiable
    # from this document. No sample size can silently promote an unaudited run.
    if document["data_class"] == "synthetic":
        status = "SYNTHETIC_TEST_ONLY"
    elif len(cases) < 100:
        status = "INSUFFICIENT_PROSPECTIVE_CASES"
    else:
        status = "PROSPECTIVE_UNVERIFIED_REQUIRES_INDEPENDENT_AUDIT"
    return {
        "version": VERSION,
        "study_id": document["study_id"],
        "n": len(cases),
        "data_class": document["data_class"],
        "brier": {arm: format(mean[arm], "f") for arm in ARMS},
        "orthodox_minus_comparator_brier": {k: format(v, "f") for k, v in differences.items()},
        "changed_forecast_counts": changes,
        "status": status,
        "assurance": "MODEL_COMPARISON_ONLY_NOT_THEOLOGICAL_OR_CAUSAL_PROOF",
    }


def loads(raw):
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise AblationError("duplicate JSON key")
            result[k] = v
        return result
    try:
        return json.loads(raw, object_pairs_hook=unique,
                          parse_constant=lambda s: (_ for _ in ()).throw(AblationError("nonfinite number")))
    except (TypeError, ValueError) as exc:
        raise AblationError("invalid JSON") from exc


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Score paired worldview ablations; no forecast generation")
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)
    try:
        result = score(loads(args.manifest.read_text(encoding="utf-8")))
    except (OSError, AblationError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
