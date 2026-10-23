"""Bounded, deterministic, source-anchored investigation auditor.

Checks source integrity, temporal eligibility, evidence formalization entailment,
and argument formalization entailment. Does not verify natural-language mappings.
"""
from __future__ import annotations

import hashlib
import copy
import itertools
import json
import re
from datetime import datetime
from typing import Any

from structured import StructuredInputError, evaluate_structured

SCHEMA = "far-investigation-audit/0.1"
ENGINE = "far-investigation-audit/0.4.5"
MAX_ATOMS = 12
MAX_ITEMS = 500
MAX_ENTAILMENT_WORK = 8_000_000


class InvalidBundle(ValueError):
    """Fail-closed malformed, tampered, or structurally inconsistent input."""


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def required(condition: bool, problem: str) -> None:
    if not condition:
        raise InvalidBundle(problem)


def timestamp(value: Any, where: str) -> datetime:
    required(isinstance(value, str) and re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", value) is not None,
        f"{where}: UTC timestamp with at most microsecond precision required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        required(parsed.utcoffset().total_seconds() == 0, f"{where}: UTC required")
        return parsed
    except (ValueError, AttributeError, TypeError) as exc:
        raise InvalidBundle(f"{where}: invalid UTC timestamp") from exc


def objects(items: Any, field: str, *, allow_empty: bool = False) -> dict[str, dict[str, Any]]:
    required(isinstance(items, list) and (allow_empty or len(items)>0) and len(items) <= MAX_ITEMS, f"{field}: bounded list required")
    found: dict[str, dict[str, Any]] = {}
    for item in items:
        required(isinstance(item, dict), f"{field}: record must be object")
        ident = item.get("id")
        required(isinstance(ident, str) and re.fullmatch(r"[a-zA-Z0-9_.:-]{1,80}", ident) is not None, f"{field}: invalid id")
        required(ident not in found, f"{field}: duplicate id {ident}")
        found[ident] = item
    return found


def validate_formula(node: Any, atoms: dict[str, Any], *, depth: int = 0, count: list[int] | None = None) -> None:
    if count is None:
        count = [0]
    count[0] += 1
    required(depth <= 32 and count[0] <= 512, "formula complexity limit exceeded")
    required(isinstance(node, dict) and len(node) == 1, "formula must be a single-operator object")
    op, value = next(iter(node.items()))
    if op == "atom":
        required(isinstance(value, str) and value in atoms, "undeclared formula atom")
    elif op == "not":
        validate_formula(value, atoms, depth=depth + 1, count=count)
    elif op == "implies":
        required(isinstance(value, list) and len(value) == 2, "implies requires exactly two operands")
        for x in value:
            validate_formula(x, atoms, depth=depth + 1, count=count)
    elif op in ("and", "or"):
        required(isinstance(value, list) and 2 <= len(value) <= 32, f"{op} needs 2–32 operands")
        for x in value:
            validate_formula(x, atoms, depth=depth + 1, count=count)
    else:
        raise InvalidBundle(f"unknown formula operation: {op}")


def variables(node: dict[str, Any]) -> set[str]:
    op, value = next(iter(node.items()))
    if op == "atom":
        return {value}
    if op == "not":
        return variables(value)
    if isinstance(value, list):
        return set().union(*(variables(x) for x in value))
    raise AssertionError("invalid checked formula")


def evaluate(node: dict[str, Any], valuation: dict[str, bool]) -> bool:
    op, value = next(iter(node.items()))
    if op == "atom":
        return valuation[value]
    if op == "not":
        return not evaluate(value, valuation)
    if op == "and":
        return all(evaluate(x, valuation) for x in value)
    if op == "or":
        return any(evaluate(x, valuation) for x in value)
    if op == "implies":
        return not evaluate(value[0], valuation) or evaluate(value[1], valuation)
    raise AssertionError("invalid checked formula")


def entailment(premises: list[dict[str, Any]], conclusion: dict[str, Any]) -> dict[str, Any]:
    atoms = sorted(set().union(*(variables(p) for p in [*premises, conclusion])))
    if len(atoms) > MAX_ATOMS:
        return {"status": "NOT_CHECKED_ATOM_LIMIT", "atom_count": len(atoms), "limit": MAX_ATOMS}
    tested = 0
    satisfying = 0
    countermodel = None
    for values in itertools.product((False, True), repeat=len(atoms)):
        tested += 1
        interpretation = dict(zip(atoms, values))
        if all(evaluate(p, interpretation) for p in premises):
            satisfying += 1
            if not evaluate(conclusion, interpretation) and countermodel is None:
                countermodel = interpretation
    if not satisfying:
        status = "INCONSISTENT_PREMISES"
    elif countermodel is not None:
        status = "DOES_NOT_ENTAIL"
    else:
        status = "ENTAILS_CONDITIONALLY"
    return {"status": status, "atoms": atoms, "assignments_checked": tested,
            "premise_satisfying_assignments": satisfying, "countermodel": countermodel}


class _BoundedInference:
    """Per-audit conservative node/valuation budget and repeated-query cache."""
    def __init__(self):
        self.work = 0
        self.formulas = {}
        self.results = {}

    def metadata(self, node):
        identity = id(node)
        if identity not in self.formulas:
            op, value = next(iter(node.items()))
            children = [] if op == "atom" else [value] if op == "not" else value
            parts = [self.metadata(child) for child in children]
            names = {value} if op == "atom" else set().union(*(part[3] for part in parts))
            # Retain the node: identity-keyed metadata must never alias a
            # later temporary negation after Python reuses an object ID.
            self.formulas[identity] = (node, digest(canonical(node)),
                                       1 + sum(part[2] for part in parts), names)
        return self.formulas[identity]

    def run(self, premises, conclusion):
        metadata = [self.metadata(node) for node in [*premises, conclusion]]
        key = tuple(part[1] for part in metadata)
        self.work += len(metadata)  # Even cached input-reference work is bounded.
        required(self.work <= MAX_ENTAILMENT_WORK, "aggregate entailment work budget exceeded")
        if key not in self.results:
            names = set().union(*(part[3] for part in metadata))
            nodes = sum(part[2] for part in metadata)
            valuations = 1 << len(names) if len(names) <= MAX_ATOMS else 1
            self.work += nodes * valuations
            required(self.work <= MAX_ENTAILMENT_WORK, "aggregate entailment work budget exceeded")
            self.results[key] = entailment(premises, conclusion)
        return copy.deepcopy(self.results[key])


def anchor(record: dict[str, Any], sources: dict[str, dict[str, Any]], label: str) -> None:
    srcid = record.get("source_id")
    required(isinstance(srcid, str) and srcid in sources, f"{label}: unknown source")
    span = record.get("span")
    required(isinstance(span, dict), f"{label}: span required")
    start, end, quote = span.get("start"), span.get("end"), span.get("quote")
    text = sources[srcid]["text"]
    required(type(start) is int and type(end) is int and 0 <= start < end <= len(text), f"{label}: invalid span")
    required(isinstance(quote, str) and text[start:end] == quote, f"{label}: quote is not an exact source span")


def audit(bundle: dict[str, Any]) -> dict[str, Any]:
    required(isinstance(bundle, dict) and bundle.get("schema") == SCHEMA, "unknown bundle schema")
    try:
        required(len(canonical(bundle)) <= 2_000_000, "bundle byte limit exceeded")
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise InvalidBundle("bundle contains non-JSON or non-finite values") from exc
    required(isinstance(bundle.get("investigation_id"), str) and bool(bundle["investigation_id"].strip()), "investigation id required")
    proposal_hash = bundle.get("proposal_sha256")
    required(proposal_hash is None or (isinstance(proposal_hash, str) and
             re.fullmatch(r"[0-9a-f]{64}", proposal_hash) is not None),
             "invalid proposal provenance commitment")
    discovery_hash = bundle.get("discovery_sha256")
    required(discovery_hash is None or (isinstance(discovery_hash, str) and
             re.fullmatch(r"[0-9a-f]{64}", discovery_hash) is not None),
             "invalid discovery provenance commitment")
    as_of = timestamp(bundle.get("as_of"), "as_of")
    atoms = bundle.get("atoms")
    required(isinstance(atoms, dict) and 0 < len(atoms) <= 100, "bounded atom definitions required")
    for name, definition in atoms.items():
        required(isinstance(name, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{0,39}", name) is not None, "invalid atom name")
        required(isinstance(definition, str) and bool(definition.strip()), "atom definition missing")
    sources = objects(bundle.get("sources"), "sources")
    claims = objects(bundle.get("claims"), "claims")
    readings = objects(bundle.get("interpretations"), "interpretations", allow_empty=True)
    evidence = bundle.get("evidence", [])
    required(isinstance(evidence, list) and len(evidence) <= MAX_ITEMS, "invalid evidence list")
    if evidence:
        objects(evidence, "evidence")
    unknowns = bundle.get("unknowns", [])
    required(isinstance(unknowns, list) and all(isinstance(x, str) and x.strip() for x in unknowns), "invalid unknowns")
    times: dict[str, str] = {}
    for sid, source in sources.items():
        raw = source.get("text")
        required(isinstance(raw, str) and 0 < len(raw.encode("utf-8")) <= 200000, f"source {sid}: invalid text")
        required(isinstance(source.get("sha256"), str) and digest(raw.encode("utf-8")) == source["sha256"], f"source {sid}: hash mismatch")
        origin = source.get("origin_id")
        required(origin is None or (isinstance(origin, str) and bool(origin.strip())), f"source {sid}: invalid origin_id")
        commitment = source.get("acquisition_sha256")
        required(commitment is None or (isinstance(commitment, str) and
                 re.fullmatch(r"[0-9a-f]{64}", commitment) is not None),
                 f"source {sid}: invalid acquisition commitment")
        # Validate any supplied timestamps, even when the source date or its
        # provenance has not been independently authenticated.  Unverified is
        # not a license to retain malformed or chronologically impossible data.
        published_at = source.get("published_at")
        captured_at = source.get("captured_at")
        pub = timestamp(published_at, f"{sid}.published_at") if published_at is not None else None
        captured = timestamp(captured_at, f"{sid}.captured_at") if captured_at is not None else None
        if pub is not None and captured is not None:
            required(pub <= captured, f"source {sid}: publication after capture")
        # Missing is NOT true: JSON documents supplied directly to audit()
        # must not acquire historical admissibility by omitting verification.
        required(type(source.get("publication_date_verified", False)) is bool,
                 f"source {sid}: invalid publication verification flag")
        required(type(source.get("origin_verified", False)) is bool,
                 f"source {sid}: invalid origin verification flag")
        if captured is not None and captured > as_of:
            times[sid] = "AFTER_CUTOFF_OR_UNVERIFIED_HISTORICAL_VERSION"
        elif source.get("publication_date_verified") is not True or pub is None or captured is None:
            times[sid] = "UNKNOWN_TEMPORAL_ELIGIBILITY"
        else:
            times[sid] = "IN_WINDOW"
    for cid, claim in claims.items():
        required(isinstance(claim.get("text"), str) and bool(claim["text"].strip()), f"claim {cid}: text required")
        anchor(claim, sources, f"claim {cid}")
        validate_formula(claim.get("formula"), atoms)
        required(claim.get("mapping_status") in ("unreviewed", "review_recorded"), f"claim {cid}: mapping status required")
    for eid, entry in ((e["id"], e) for e in evidence):
        required(isinstance(entry.get("claim_id"), str) and entry["claim_id"] in claims, f"evidence {eid}: unknown claim")
        anchor(entry, sources, f"evidence {eid}")
        required(entry.get("relation") in ("supports", "contradicts", "qualifies", "unknown"), f"evidence {eid}: invalid relation")
        required(entry.get("mapping_status") in ("unreviewed", "review_recorded"), f"evidence {eid}: mapping status required")
        if "formula" in entry:
            validate_formula(entry["formula"], atoms)
        required("data_check" not in entry or "formula" not in entry,
                 f"evidence {eid}: structured and propositional checks must be separate records")
    logic = _BoundedInference()
    findings: dict[str, list[dict[str, Any]]] = {cid: [] for cid in claims}
    for evidence_item in evidence:
        sid = evidence_item["source_id"]
        claim = claims[evidence_item["claim_id"]]
        finding: dict[str, Any] = {
            "evidence_id": evidence_item["id"], "source_id": sid,
            "origin_id": sources[sid].get("origin_id"), "temporal_status": times[sid],
            "claimed_relation": evidence_item["relation"], "mapping_status": evidence_item["mapping_status"],
        }
        if "data_check" in evidence_item:
            # Arithmetic is about the exact supplied snapshot, so it can be
            # recomputed even when the snapshot's historical availability is
            # unknown. It NEVER makes the source admissible at claim time.
            try:
                checked = evaluate_structured(claim, evidence_item, sources[sid]["text"],
                    claim_source_text=sources[claim["source_id"]]["text"])
            except StructuredInputError as exc:
                raise InvalidBundle(f"evidence {evidence_item['id']}: {exc}") from exc
            finding["structured_check"] = checked
            finding["structured_temporal_eligibility"] = times[sid]
            if times[sid] != "IN_WINDOW":
                finding["formal_relation"] = "TEMPORAL_NOT_ADMISSIBLE"
            elif (sid == claim["source_id"] and
                  evidence_item["span"]["start"] < claim["span"]["end"] and
                  claim["span"]["start"] < evidence_item["span"]["end"]):
                finding["formal_relation"] = "SELF_REFERENCE_NOT_CORROBORATION"
            else:
                finding["formal_relation"] = "NOT_APPLICABLE_TO_STRUCTURED_CHECK"
            if evidence_item["relation"] == "supports" and checked["status"] != "STRUCTURED_VALUE_MATCH":
                finding["assessment_disagrees_with_structured_check"] = True
            if evidence_item["relation"] == "contradicts" and checked["status"] != "STRUCTURED_VALUE_MISMATCH":
                finding["assessment_disagrees_with_structured_check"] = True
        elif times[sid] != "IN_WINDOW":
            finding["formal_relation"] = "TEMPORAL_NOT_ADMISSIBLE"
        elif (sid == claim["source_id"] and
                  evidence_item["span"]["start"] < claim["span"]["end"] and
                  claim["span"]["start"] < evidence_item["span"]["end"]):
            finding["formal_relation"] = "SELF_REFERENCE_NOT_CORROBORATION"
        elif "formula" not in evidence_item:
            finding["formal_relation"] = "UNTESTED_SEMANTIC_ASSESSMENT"
        else:
            positive = logic.run([evidence_item["formula"]], claim["formula"])
            negative = logic.run([evidence_item["formula"]], {"not": claim["formula"]})
            if positive["status"] == "INCONSISTENT_PREMISES":
                relation = "INCONSISTENT_EVIDENCE_FORMULA"
            elif positive["status"] == "NOT_CHECKED_ATOM_LIMIT":
                relation = "NOT_CHECKED_ATOM_LIMIT"
            elif positive["status"] == "ENTAILS_CONDITIONALLY":
                relation = "FORMALLY_SUPPORTS_IF_MAPPINGS_CORRECT"
            elif negative["status"] == "ENTAILS_CONDITIONALLY":
                relation = "FORMALLY_CONTRADICTS_IF_MAPPINGS_CORRECT"
            else:
                relation = "DOES_NOT_ESTABLISH"
            finding["formal_relation"] = relation
            if relation == "DOES_NOT_ESTABLISH":
                finding["countermodel"] = positive.get("countermodel")
            if (evidence_item["relation"] == "supports" and relation != "FORMALLY_SUPPORTS_IF_MAPPINGS_CORRECT") or (evidence_item["relation"] == "contradicts" and relation != "FORMALLY_CONTRADICTS_IF_MAPPINGS_CORRECT"):
                finding["assessment_disagrees_with_formalization"] = True
        findings[evidence_item["claim_id"]].append(finding)
    claim_reports: dict[str, dict[str, Any]] = {}
    for cid, claim in claims.items():
        assessed = findings[cid]
        pos = [r for r in assessed if r["formal_relation"] == "FORMALLY_SUPPORTS_IF_MAPPINGS_CORRECT"]
        neg = [r for r in assessed if r["formal_relation"] == "FORMALLY_CONTRADICTS_IF_MAPPINGS_CORRECT"]
        status = ("CONFLICT_RECORDED" if pos and neg else "CONDITIONAL_FORMAL_SUPPORT_RECORDED" if pos
                  else "CONDITIONAL_FORMAL_CONTRADICTION_RECORDED" if neg else "NOT_ESTABLISHED")
        structured = [r["structured_check"] for r in assessed if "structured_check" in r and
                      r["structured_temporal_eligibility"] == "IN_WINDOW" and
                      r["formal_relation"] != "SELF_REFERENCE_NOT_CORROBORATION"]
        snapshot_only = [r["structured_check"] for r in assessed if "structured_check" in r and
                         r["formal_relation"] in {"TEMPORAL_NOT_ADMISSIBLE", "SELF_REFERENCE_NOT_CORROBORATION"}]
        nonadmissible_structured = len(snapshot_only)
        matched = sum(r["status"] == "STRUCTURED_VALUE_MATCH" for r in structured)
        mismatched = sum(r["status"] == "STRUCTURED_VALUE_MISMATCH" for r in structured)
        numeric_state = ("CONFLICTING_STRUCTURED_VALUES" if matched and mismatched else
                         "STRUCTURED_VALUE_MATCH_CONDITIONALLY" if matched else
                         "STRUCTURED_VALUE_MISMATCH_CONDITIONALLY" if mismatched else
                         "SNAPSHOT_ONLY_VALUE_CHECK_TEMPORALLY_INADMISSIBLE" if snapshot_only else "NOT_ESTABLISHED")
        claim_reports[cid] = {"status": status, "mapping_status": claim["mapping_status"],
                              "structured_value_checks": {"status": numeric_state,
                                  "matches": matched, "mismatches": mismatched,
                                  "unverifiable": len(structured) - matched - mismatched,
                                  "snapshot_only_not_admissible": nonadmissible_structured,
                                  "snapshot_only_matches": sum(x["status"] == "STRUCTURED_VALUE_MATCH" for x in snapshot_only),
                                  "snapshot_only_mismatches": sum(x["status"] == "STRUCTURED_VALUE_MISMATCH" for x in snapshot_only),
                                  "claim_meaning_verified": False,
                                  "temporal_eligibility_not_promoted_by_computation": True},
                              "support_origin_ids": sorted({r["origin_id"] for r in pos if r["origin_id"] is not None}),
                              "support_sources_with_unknown_origin": sorted({r["source_id"] for r in pos if r["origin_id"] is None}),
                              "origin_independence_verified": False, "evidence": assessed}
    reading_reports: list[dict[str, Any]] = []
    for rid, reading in readings.items():
        ps = reading.get("premises")
        required(isinstance(ps, list) and len(ps) > 0 and all(isinstance(p, str) for p in ps), f"reading {rid}: invalid premises")
        required(len(ps) == len(set(ps)) and all(p in claims for p in ps), f"reading {rid}: duplicate or unknown premise")
        conclusion = reading.get("conclusion")
        required(isinstance(conclusion, str) and conclusion in claims, f"reading {rid}: unknown conclusion")
        required(conclusion not in ps, f"reading {rid}: conclusion cannot be a premise")
        required(reading.get("mapping_status") in ("unreviewed", "review_recorded"), f"reading {rid}: mapping status required")
        missing = [p for p in ps if claim_reports[p]["status"] != "CONDITIONAL_FORMAL_SUPPORT_RECORDED"]
        basis = reading.get("formalization_basis", "explicit_formulas")
        required(isinstance(basis, str) and basis in {"explicit_formulas", "unformalized_candidate"},
                 f"reading {rid}: invalid formalization basis")
        result = ({"status": "NOT_CHECKED_UNFORMALIZED",
                   "reason": "Auto-generated atom labels cannot test natural-language entailment."}
                  if basis == "unformalized_candidate" else
                  logic.run([claims[p]["formula"] for p in ps], claims[conclusion]["formula"]))
        notes = reading.get("interpretation_notes", "")
        card = reading.get("interpretation_card", {})
        required(isinstance(notes, str) and len(notes) <= 2000, f"reading {rid}: invalid interpretation notes")
        required(isinstance(card, dict), f"reading {rid}: interpretation card must be object")
        permitted_fields = {"subject", "population", "time", "geography", "quantifier",
                            "measurement", "comparison", "threshold", "assumptions"}
        required(all(k in permitted_fields and isinstance(v, dict) and set(v)=={"value", "origin"}
                     and isinstance(v["value"], str) and len(v["value"]) <= 250
                     and isinstance(v["origin"], str)
                     and v["origin"] in {"stated", "inferred", "default", "unknown"}
                     for k,v in card.items()), f"reading {rid}: invalid interpretation card")
        reading_reports.append({"id": rid, "premises": ps, "conclusion": conclusion,
                                "mapping_status": reading["mapping_status"],
                                "formalization_basis": basis,
                                "interpretation_notes": notes, "interpretation_card": card,
                                "formal_inference": result,
                                "premises_without_uncontested_formal_evidence": missing,
                                "semantic_fidelity_independently_verified": False})
    statuses = {r["formal_inference"]["status"] for r in reading_reports}
    report = {"schema": "far-investigation-report/0.2", "engine": ENGINE,
              "investigation_id": bundle["investigation_id"], "input_sha256": digest(canonical(bundle)),
              "as_of": bundle["as_of"], "source_temporal_status": times,
              "claims": claim_reports, "interpretations": reading_reports,
              "interpretation_sensitive_inference": len(statuses) > 1,
              "interpretation_cards_differ": len({canonical(r["interpretation_card"]) for r in reading_reports}) > 1,
              "interpretations_present": bool(reading_reports),
              "unknowns": unknowns,
              "assurance_boundary": {"formal_entailment": "exhaustive bounded propositional valuations",
                  "source_integrity": "byte-level SHA-256 of supplied snapshot, not authenticity",
                  "quote_validation": "exact span equality, not semantic entailment",
                  "semantic_fidelity": "unverified: claim and evidence text to atoms/formulas is supplied by author",
                  "evidence_independence": "origin_ids are reported, not independently authenticated",
                  "real_world_truth": "not established", "open_world_search_completeness": "not established",
                  "structured_numbers": "deterministic computations over supplied JSON, not verification of measurement, population, scope, or claim interpretation"}}
    report["report_sha256"] = digest(canonical(report))
    return report
