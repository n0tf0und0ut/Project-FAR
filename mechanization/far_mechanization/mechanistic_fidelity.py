"""FAR-MECH/0.1: audit *submitted* causal explanation measurements.

Computes activation error and downstream KL after component replacement.
The program does NOT run a neural network, validate intervention execution,
establish circuit completeness, or authorize semantic interpretation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

VERSION = "FAR-MECH/0.1"
SCHEMA = Path(__file__).resolve().parents[2] / "schemas/far-mechanistic-fidelity-v0.1.schema.json"
QUANT = Decimal("0.000000001")
ZERO = Decimal(0)
ONE = Decimal(1)


class MechanismAuditError(ValueError):
    pass


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise MechanismAuditError("duplicate JSON key: " + key)
        result[key] = value
    return result


def _strict_loads(raw):
    try:
        return json.loads(raw, object_pairs_hook=_unique,
                          parse_constant=lambda x: (_ for _ in ()).throw(
                              MechanismAuditError("nonfinite JSON: " + x)))
    except (TypeError, ValueError) as exc:
        raise MechanismAuditError("invalid JSON: " + str(exc)) from exc


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False,
                          allow_nan=False, separators=(",", ":")).encode("utf-8", "strict")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise MechanismAuditError("noncanonical data") from exc


def _time(value):
    try:
        t = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    except (TypeError, ValueError) as exc:
        raise MechanismAuditError("invalid time") from exc
    if t.tzinfo is None or t.utcoffset() is None:
        raise MechanismAuditError("timestamp must have offset")
    return t


def _number(value):
    try:
        out = Decimal(value)
    except (TypeError, InvalidOperation) as exc:
        raise MechanismAuditError("invalid finite decimal") from exc
    if not out.is_finite():
        raise MechanismAuditError("nonfinite decimal")
    return out


def _probabilities(values):
    nums = [_number(x) for x in values]
    if any(x <= ZERO for x in nums):
        raise MechanismAuditError("all reported probabilities must be strictly positive")
    if sum(nums) != ONE:
        raise MechanismAuditError("probability vector must sum to exactly one")
    return nums


def _kl(p, q):
    # D_KL(original || replacement): asymmetry is intentional.
    with localcontext() as ctx:
        ctx.prec = 50
        result = sum((a * (a / b).ln() for a, b in zip(p, q)), ZERO)
        if result < ZERO and abs(result) < Decimal("1e-35"):
            result = ZERO
        return max(result, ZERO)


def _mean(rows):
    with localcontext() as ctx:
        ctx.prec = 50
        return sum(rows, ZERO) / Decimal(len(rows))


def _fmt(number):
    with localcontext() as ctx:
        ctx.prec = 50
        return format(number.quantize(QUANT), "f")


def _validate(value):
    try:
        data = _strict_loads(_canonical(value).decode("utf-8"))
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        errors = sorted(Draft202012Validator(schema).iter_errors(data),
                        key=lambda e: (str(list(e.path)), e.message))
        if errors:
            raise MechanismAuditError("; ".join(
                str(list(e.path)) + ": " + e.message for e in errors))
        sources = {s["id"]: s for s in data["sources"]}
        if len(sources) != len(data["sources"]):
            raise MechanismAuditError("duplicate source id")
        for source in sources.values():
            if hashlib.sha256(source["text"].encode("utf-8")).hexdigest() != source["sha256"]:
                raise MechanismAuditError("source bytes do not match commitment: " + source["id"])
        explanation = data["explanation"]
        if any(ref not in sources for ref in explanation["hypothesis_source_ids"]):
            raise MechanismAuditError("unresolved explanation source")
        registered = _time(data["registered_at"])
        seen = set()
        dimensions = set()
        splits = set()
        for case in data["cases"]:
            if case["id"] in seen:
                raise MechanismAuditError("duplicate case id")
            seen.add(case["id"])
            splits.add(case["split"])
            if _time(case["measured_at"]) <= registered:
                raise MechanismAuditError("measurement not after declared registration")
            if any(ref not in sources for ref in case["source_ids"]):
                raise MechanismAuditError("unresolved observation source")
            dimensions.add(len(case["original_probs"]))
            if not (len(case["original_probs"]) ==
                    len(case["replacement_probs"]) ==
                    len(case["baseline_probs"])):
                raise MechanismAuditError("probability dimensions differ")
            for key in ("original_probs", "replacement_probs", "baseline_probs"):
                _probabilities(case[key])
            if (_number(case["observed_activation"]) ==
                    _number(case["explained_activation"]) and
                    case["original_probs"] != case["replacement_probs"]):
                raise MechanismAuditError(
                    "unchanged activation cannot change deterministic downstream distribution")
        if len(dimensions) != 1:
            raise MechanismAuditError("inconsistent outcome dimensions")
        if splits != {"heldout", "adversarial", "control"}:
            raise MechanismAuditError("heldout, adversarial and control cases required")
        return data
    except (KeyError, IndexError, AttributeError) as exc:
        raise MechanismAuditError("malformed mechanism audit") from exc


@dataclass(frozen=True)
class MechanismAudit:
    _raw: bytes

    @classmethod
    def from_dict(cls, value):
        return cls(_canonical(_validate(value)))

    @classmethod
    def loads(cls, raw):
        return cls.from_dict(_strict_loads(raw))

    @classmethod
    def load(cls, path):
        return cls.loads(Path(path).read_text(encoding="utf-8"))

    @property
    def digest(self):
        return hashlib.sha256(self._raw).hexdigest()

    def to_dict(self):
        return _strict_loads(self._raw.decode("utf-8"))

    def evaluate(self):
        document = self.to_dict()
        scores = {}
        counterexamples = []
        for split in ("heldout", "adversarial", "control"):
            rows = [c for c in document["cases"] if c["split"] == split]
            activation_error = []
            baseline_activation_error = []
            replacement_kl = []
            baseline_kl = []
            for row in rows:
                activation_error.append(abs(
                    _number(row["observed_activation"]) -
                    _number(row["explained_activation"])))
                baseline_activation_error.append(abs(
                    _number(row["observed_activation"]) -
                    _number(row["baseline_activation"])))
                p = _probabilities(row["original_probs"])
                replaced = _kl(p, _probabilities(row["replacement_probs"]))
                comparator = _kl(p, _probabilities(row["baseline_probs"]))
                replacement_kl.append(replaced)
                baseline_kl.append(comparator)
                # Description quality/activation accuracy does not certify
                # preserved downstream behavior. Keep individual failures.
                if replaced > comparator:
                    counterexamples.append({
                        "case_id": row["id"], "split": split,
                        "kind": "DOWNSTREAM_WORSE_THAN_BASELINE",
                        "replacement_kl": _fmt(replaced),
                        "baseline_kl": _fmt(comparator),
                        "source_ids": list(row["source_ids"]),
                    })
            mean_kl = _mean(replacement_kl)
            mean_base = _mean(baseline_kl)
            scores[split] = {
                "n": len(rows),
                "activation_mae": _fmt(_mean(activation_error)),
                "baseline_activation_mae": _fmt(_mean(baseline_activation_error)),
                "mean_downstream_kl": _fmt(mean_kl),
                "baseline_downstream_kl": _fmt(mean_base),
                "delta_kl": _fmt(mean_kl - mean_base),
                "cases_worse_than_baseline": sum(
                    x > y for x, y in zip(replacement_kl, baseline_kl)),
            }
        return {
            "format_version": VERSION, "audit_id": document["id"],
            "document_sha256": self.digest, "data_class": document["data_class"],
            "component_id": document["model"]["component_id"],
            "metric": "D_KL(original || component_replacement)",
            "by_split": scores,
            "counterexamples": sorted(counterexamples, key=lambda x: (x["split"], x["case_id"])),
            "status": ("SYNTHETIC_DEMONSTRATION_ONLY" if document["data_class"] == "synthetic"
                       else "SUBMITTED_INTERVENTIONS_NOT_INDEPENDENTLY_REPLAYED"),
            "assurance": "STRUCTURAL_AND_NUMERICAL_AUDIT_ONLY_NOT_CAUSAL_PROOF",
            "unverified": [
                "actual model execution and reproducibility",
                "whether the component was replaced as claimed",
                "whether evidence sampling was unbiased or preregistered",
                "semantic adequacy of the explanation",
                "generalization beyond submitted cases",
            ],
        }


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description="Audit submitted mechanism replacement measurements")
    parser.add_argument("document", type=Path)
    args = parser.parse_args(argv)
    try:
        result = MechanismAudit.load(args.document).evaluate()
    except (OSError, MechanismAuditError) as exc:
        parser.exit(2, str(exc) + "\n")
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
