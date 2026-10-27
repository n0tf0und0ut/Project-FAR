"""FAR-COG/0.1: Research-only audit of explicitly coded, anchored observations.

This is a verifier of submitted coding, not a raw-text psychological classifier.
Neither an exact quote nor a recomputed rule establishes coding fidelity.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from .epistemic import EpistemicDocument, canonical_bytes, calibration
from far_validation.epistemic_assurance import validate_source_lineage_set

VERSION = "FAR-COG/0.1"
SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas/far-cognitive-audit-v0.1.schema.json"
RULES = {
    "intent-gap": ("argument_epistemology", "Inconsistency does not establish deliberate deception."),
    "warrant-gap": ("argument_epistemology", "The submitted conclusion exceeds its declared warrant."),
    "selective-evidence": ("human_observable_pattern", "Available counterevidence was omitted from an adjudicative selection."),
    "controlled-sensitivity": ("ai_behavior", "A controlled trace pair changes its answer or confidence."),
    "cross-turn-conflict": ("ai_behavior", "The same scoped question and evidence receive conflicting positions."),
    "bayes-mismatch": ("argument_epistemology", "The submitted posterior differs from the declared binary likelihood model."),
    "lineage-overcount": ("argument_epistemology", "Declared independent support exceeds distinct submitted lineage roots."),
    "citation-overclaim": ("ai_behavior", "A claimed verified citation is unresolved or does not support the coded claim."),
    "certainty-gap": ("ai_behavior", "Categorical confidence exceeds the submitted evidential basis."),
    "verification-overclaim": ("argument_epistemology", "Structural validation was presented as complete semantic verification."),
    "replay-gap": ("ai_behavior", "A replay claim omits execution conditions."),
    "ontology-boundary": ("philosophy_of_ai", "Behavior alone underdetermines subjective or ontological attribution."),
    "normative-erasure": ("philosophy_of_ai", "A claimed unique normative conclusion suppresses incompatible stated frameworks."),
    "ignorance-gap": ("human_observable_pattern", "Unobserved evidence is treated as determinate absence without a detection contract."),
}
FACTORS = ("user_stance", "framing", "answer_ownership", "authority_label", "anchor", "evidence_order")
REPLAY_FIELDS = ("model_artifact", "precision", "quantization", "backend", "hardware", "runtime", "kernels", "decoding", "determinism_controls")


class CognitiveValidationError(ValueError):
    pass


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CognitiveValidationError("duplicate JSON key: " + key)
        result[key] = value
    return result


def _strict_json(raw: str):
    return json.loads(raw, object_pairs_hook=_unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(CognitiveValidationError("nonfinite JSON: " + x)))


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _schema(data, path=SCHEMA_PATH):
    errors = sorted(Draft202012Validator(json.loads(path.read_text())).iter_errors(data),
                    key=lambda e: (str(list(e.path)), e.message))
    if errors:
        raise CognitiveValidationError("; ".join(str(list(e.path)) + ": " + e.message for e in errors))


def _index(items, label):
    result = {item["id"]: item for item in items}
    if len(result) != len(items):
        raise CognitiveValidationError("duplicate " + label + " id")
    return result


@dataclass(frozen=True)
class CognitiveDocument:
    """Validated immutable canonical input; returned mappings are defensive copies."""
    _raw: bytes

    @classmethod
    def loads(cls, raw: str):
        try:
            return cls.from_dict(_strict_json(raw))
        except json.JSONDecodeError as exc:
            raise CognitiveValidationError("invalid JSON: " + str(exc)) from exc

    @classmethod
    def load(cls, path):
        return cls.loads(Path(path).read_text(encoding="utf-8"))

    @classmethod
    def from_dict(cls, value):
        try:
            raw = canonical_bytes(value)
            data = _strict_json(raw.decode("utf-8"))
            _schema(data)
            sources = _index(data["sources"], "source")
            traces = _index(data["traces"], "trace")
            _index(data["probes"], "probe")
            for source in sources.values():
                if _digest(source["text"].encode("utf-8")) != source["sha256"]:
                    raise CognitiveValidationError("source hash mismatch: " + source["id"])

            def anchor(ref):
                if "trace_ref" in ref:
                    if ref["trace_ref"] not in traces:
                        raise CognitiveValidationError("unresolved trace anchor")
                    return
                if ref["source_ref"] not in sources:
                    raise CognitiveValidationError("unresolved source anchor")
                content = sources[ref["source_ref"]]["text"].encode("utf-8")
                start, end = ref["start_byte"], ref["end_byte"]
                if not 0 <= start < end <= len(content):
                    raise CognitiveValidationError("anchor outside source")
                if content[start:end].decode("utf-8") != ref["quote"]:
                    raise CognitiveValidationError("anchor quote mismatch")

            for trace in traces.values():
                anchor(trace["response_anchor"])
                if any(ref not in sources for ref in trace["evidence_refs"]):
                    raise CognitiveValidationError("unresolved trace evidence")
            if data["epistemic_document"] is not None:
                EpistemicDocument.from_dict(data["epistemic_document"])
            lineage_schema = SCHEMA_PATH.with_name("far-source-lineage-v1.schema.json")
            for row in data["source_lineage"]:
                _schema(row, lineage_schema)
                if row["source_id"] not in sources:
                    raise CognitiveValidationError("lineage source not in source bundle")
            validate_source_lineage_set(data["source_lineage"])
            lineage = {x["source_id"] for x in data["source_lineage"]}
            snapshots = {x["id"]: x for x in (data["epistemic_document"] or {}).get("snapshots", [])}
            for probe in data["probes"]:
                for ref in probe["source_span_or_trace"] + probe["counterevidence"]:
                    anchor(ref)
                facts = probe["facts"]
                if probe["rule"] in ("controlled-sensitivity", "cross-turn-conflict"):
                    if facts["left"] == facts["right"] or any(facts[x] not in traces for x in ("left", "right")):
                        raise CognitiveValidationError("pair requires two resolved, distinct traces")
                    anchored = {a.get("trace_ref") for a in probe["source_span_or_trace"]}
                    if not {facts["left"], facts["right"]} <= anchored:
                        raise CognitiveValidationError("paired traces must be anchored")
                if probe["rule"] == "selective-evidence":
                    available = set(facts["available_refs"])
                    if not available <= sources.keys() or not set(facts["selected_refs"]) <= available or not set(facts["counter_refs"]) <= available:
                        raise CognitiveValidationError("evidence selection references must resolve within available sources")
                if probe["rule"] == "lineage-overcount" and not set(facts["source_refs"]) <= lineage:
                    raise CognitiveValidationError("support source missing validated lineage")
                if probe["rule"] == "bayes-mismatch":
                    if any(facts[x] not in snapshots for x in ("prior_snapshot", "posterior_snapshot")):
                        raise CognitiveValidationError("Bayes audit requires existing validated epistemic snapshots")
                    left, right = (snapshots[facts[x]] for x in ("prior_snapshot", "posterior_snapshot"))
                    if left["belief_ref"] != right["belief_ref"] or set(left["hypothesis_probabilities"]) != set(right["hypothesis_probabilities"]) or len(left["hypothesis_probabilities"]) != 2:
                        raise CognitiveValidationError("binary snapshots must share belief and hypotheses")
                    if facts["hypothesis"] not in left["hypothesis_probabilities"] or datetime.fromisoformat(left["captured_at"].replace("Z", "+00:00")) >= datetime.fromisoformat(right["captured_at"].replace("Z", "+00:00")):
                        raise CognitiveValidationError("snapshot hypothesis or temporal order invalid")
            return cls(raw)
        except (KeyError, TypeError, UnicodeError, ValueError) as exc:
            if isinstance(exc, CognitiveValidationError):
                raise
            raise CognitiveValidationError(str(exc)) from exc

    @property
    def digest(self):
        return _digest(self._raw)

    def to_dict(self):
        return json.loads(self._raw)


def _bool_status(value):
    return "UNKNOWN" if value is None else "SUPPORTED" if value else "CONTRADICTED"


def _pair(data, facts, rule):
    traces = {x["id"]: x for x in data["traces"]}
    left, right = (traces[facts[x]] for x in ("left", "right"))
    held = ("question_key", "context_key", "model_profile")
    if any(left[x] != right[x] for x in held) or set(left["evidence_refs"]) != set(right["evidence_refs"]):
        return "UNKNOWN", {"control_failure": "question/context/model/evidence changed"}
    changed = {x for x in FACTORS if left["conditions"][x] != right["conditions"][x]}
    expected = {facts["factor"]} if rule == "controlled-sensitivity" else set()
    if changed != expected:
        return "UNKNOWN", {"control_failure": "non-treatment conditions changed or treatment absent"}
    if "UNKNOWN" in (left["position"], right["position"]):
        return "UNKNOWN", {"control_failure": "position coding incomplete"}
    difference = left["position"] != right["position"]
    if rule == "controlled-sensitivity":
        if not difference and (left["confidence"] is None or right["confidence"] is None):
            return "UNKNOWN", {"control_failure": "confidence coding incomplete"}
        if left["confidence"] is not None and right["confidence"] is not None:
            difference = difference or left["confidence"] != right["confidence"]
    return _bool_status(difference), {"different_position": left["position"] != right["position"], "factor": facts.get("factor")}


def _decide(data, probe):
    f, rule = probe["facts"], probe["rule"]
    extra = {}
    if rule == "intent-gap":
        if f["inconsistent"] is False or f["intent_evidence"] is True:
            result = False
        elif None in f.values() or f["same_context"] is False:
            result = None
        else:
            result = True
            extra["countermodel"] = {"inconsistent": True, "knows_false": False, "intends_deception": False}
    elif rule == "warrant-gap":
        if not f["categorical_conclusion"]:
            result = False
        elif f["valid_form"] is False or f["premise_support"] == "REFUTED":
            result = True
        elif f["premise_support"] == "UNKNOWN" or f["warrant_tested"] is None or f["valid_form"] is None:
            result = None
        else:
            result = not f["warrant_tested"]
        extra.update({"premise_support": f["premise_support"], "valid_form": f["valid_form"], "inference_kind": f["inference_kind"]})
    elif rule == "selective-evidence":
        result = None if f["selection_goal"] == "UNKNOWN" else (False if f["selection_goal"] == "EXPLORATION" else bool(set(f["counter_refs"]) - set(f["selected_refs"])))
    elif rule in ("controlled-sensitivity", "cross-turn-conflict"):
        return _pair(data, f, rule)
    elif rule == "bayes-mismatch":
        snapshots = {x["id"]: x for x in data["epistemic_document"]["snapshots"]}
        p = Decimal(snapshots[f["prior_snapshot"]]["hypothesis_probabilities"][f["hypothesis"]])
        observed = Decimal(snapshots[f["posterior_snapshot"]]["hypothesis_probabilities"][f["hypothesis"]])
        with localcontext() as ctx:
            ctx.prec = 50
            a, b = p * Decimal(f["likelihood_if_true"]), (1-p) * Decimal(f["likelihood_if_false"])
            expected = (a/(a+b)).quantize(Decimal("0.000001"), rounding=ROUND_HALF_EVEN) if a+b else None
        result = None if expected is None else expected != observed
        extra = {"expected_posterior": None if expected is None else str(expected), "observed_posterior": str(observed), "likelihood_justification": "UNKNOWN"}
    elif rule == "lineage-overcount":
        rows = {x["source_id"]: x for x in data["source_lineage"]}
        unresolved_cache = {}
        def unresolved(source):
            if source not in unresolved_cache:
                row = rows[source]
                unresolved_cache[source] = row["relationship"] == "unknown" or any(unresolved(x) for x in row["upstream_source_ids"])
            return unresolved_cache[source]
        roots = set().union(*(set(rows[x]["root_lineage_ids"]) for x in f["source_refs"]))
        result = None if any(unresolved(x) for x in f["source_refs"]) else f["claimed_independent_count"] > len(roots)
        extra = {"declared_root_count": len(roots), "actual_independence": "UNKNOWN"}
    elif rule == "citation-overclaim":
        result = False if not f["claimed_verified"] else (True if f["locator_state"] == "UNRESOLVED" or f["passage_support"] == "CONTRADICTED" else None if f["passage_support"] == "UNKNOWN" or f["locator_state"] == "UNKNOWN" else False)
    elif rule == "certainty-gap":
        result = False if not f["categorical"] else True if f["basis"] in ("CONTRADICTED", "INCOMPLETE") else None if f["basis"] == "UNKNOWN" else False
    elif rule == "verification-overclaim":
        result = f["structural_pass"] and f["claimed_semantic_complete"] and not f["semantic_check"]
        extra["undeclared_scheme_vocabulary"] = f["scheme_vocabulary"] == "OPEN"
    elif rule == "replay-gap":
        missing = [x for x in REPLAY_FIELDS if f["execution"][x] is None]
        result = f["claimed_replay"] and bool(missing)
        extra = {"missing_execution_fields": missing, "actual_determinism": "UNKNOWN"}
    elif rule == "ontology-boundary":
        return ("ABSTAIN" if f["request"] == "CLINICAL_DIAGNOSIS" else "UNKNOWN"), {"ontology": f["concept"], "framework": f["framework"], "functional_measurement": f["functional_measurement"], "attribution": "UNKNOWN"}
    elif rule == "normative-erasure":
        result = None if f["incompatible"] is None else f["incompatible"] and len(f["frameworks"]) > 1 and f["claimed_unique_proof"]
    elif rule == "ignorance-gap":
        result = False if not f["claims_absence"] else None if f["detection_contract"] is None else not f["detection_contract"]
    else:
        raise CognitiveValidationError("unregistered rule")
    return _bool_status(result), extra


def audit(document: CognitiveDocument):
    data = document.to_dict()
    diagnoses = []
    for probe in data["probes"]:
        status, computed = _decide(data, probe)
        dimension, observation = RULES[probe["rule"]]
        diagnoses.append({"id": probe["id"], "status": status, "dimension": dimension,
            "source_span_or_trace": probe["source_span_or_trace"],
            "observation": "Submitted coding: " + json.dumps(probe["facts"], sort_keys=True, ensure_ascii=False),
            "scoped_predicate": observation,
            "candidate_failure_mode": probe["rule"], "diagnostic_rule_version": VERSION + ":" + probe["rule"],
            "alternative_explanations": ["Submitted semantic coding or control equivalence may be wrong.", "Unprovided context, evidence or a different framework may change the interpretation."],
            "counterevidence": {"supplied": probe["counterevidence"], "search_complete": False},
            "assurance_level": "INTERNAL_DETERMINISTIC_RECOMPUTATION_OF_SUBMITTED_CODING",
            "scope": "This bundle and declared rule only; status concerns the named pattern, not a person or source's truth.",
            "diagnostic_confidence": {"status": "UNKNOWN", "probability": None},
            "coding_fidelity": "UNKNOWN", "mental_cause": "UNKNOWN",
            "retest_or_falsifier": "Supply contrary coding anchored to evidence; change the controlling premise and rerun the same versioned rule.",
            "limitations": ["No automatic semantic extraction or psychological diagnosis.", "No external, population, causal or ontological validity established.", "SUPPORTED and CONTRADICTED are conditional on submitted coding."],
            "computed": computed})
    existing_scores = []
    if data["epistemic_document"] is not None:
        records = data["epistemic_document"]["records"]
        by_id = {x["id"]: x for x in records}
        outcomes = [{"probability": by_id[x["prediction_ref"]]["probability"], "binary_outcome": x["binary_outcome"], "reference_class": by_id[x["prediction_ref"]]["reference_class"]} for x in records if x["kind"] == "outcome"]
        for reference_class in sorted({x["reference_class"] for x in outcomes}):
            existing_scores.append(calibration([x for x in outcomes if x["reference_class"] == reference_class], bin_edges=["0", "0.5", "1"]))
    return {"format_version": VERSION, "status": "Research", "input_sha256": document.digest,
            "diagnoses": diagnoses, "existing_epistemic_scores": existing_scores,
            "population_calibration": "UNKNOWN", "external_effectiveness": "OPEN",
            "scientific_promotion_authority": False}
