"""Second, separately coded finite-propositional checking implementation.

Unlike engine.py's valuation iterator, this checker constructs truth-set
bitmasks. It is a design-diverse regression oracle, not independently authored
software or third-party verification. It does not check semantic mappings.
"""
from __future__ import annotations
import hashlib
import itertools
import json
from decimal import Decimal
from fractions import Fraction

class IndependentCheckError(ValueError):
    pass


def _variables(expr):
    if not isinstance(expr, dict) or len(expr) != 1:
        raise IndependentCheckError("invalid formula")
    op, v=next(iter(expr.items()))
    if op=="atom":
        if not isinstance(v,str):raise IndependentCheckError("invalid atom")
        return {v}
    if op=="not":return _variables(v)
    if op not in {"and","or","implies"} or not isinstance(v,list):
        raise IndependentCheckError("unknown operator")
    if op=="implies" and len(v)!=2:
        raise IndependentCheckError("invalid implication")
    if op in {"and","or"} and not 2<=len(v)<=32:
        raise IndependentCheckError("invalid logical arity")
    return set().union(*[_variables(e) for e in v])


def check(premises:list[dict], conclusion:dict):
    if not isinstance(premises,list) or not premises:
        raise IndependentCheckError("premises required")
    names=sorted(set().union(*[_variables(x) for x in [*premises,conclusion]]))
    if len(names)>12:
        return {"status":"NOT_CHECKED_ATOM_LIMIT","atom_count":len(names),"limit":12}
    n=len(names);total=1<<n;universe=(1<<total)-1
    atom_masks={}
    for i,name in enumerate(names):
        bit=0
        for val in range(total):
            if (val>>(n-i-1))&1:
                bit|=1<<val
        atom_masks[name]=bit
    def truthset(node):
        op,v=next(iter(node.items()))
        if op=="atom":return atom_masks[v]
        if op=="not":return universe^truthset(v)
        if op=="and":
            out=universe
            for child in v:out &= truthset(child)
            return out
        if op=="or":
            out=0
            for child in v:out |= truthset(child)
            return out
        if op=="implies":return (universe^truthset(v[0]))|truthset(v[1])
        raise IndependentCheckError("invalid operator")
    ps=universe
    for p in premises:ps &= truthset(p)
    wrong=ps & (universe^truthset(conclusion))
    if ps==0:status="INCONSISTENT_PREMISES"
    elif wrong:status="DOES_NOT_ENTAIL"
    else:status="ENTAILS_CONDITIONALLY"
    index=(wrong & -wrong).bit_length()-1 if wrong else None
    counter={name:bool((index>>(n-i-1))&1) for i,name in enumerate(names)} if index is not None else None
    return {"status":status,"atoms":names,"assignments_checked":total,
            "premise_satisfying_assignments":ps.bit_count(),"countermodel":counter}


def _separate_numeric_recompute(claim:dict, record:dict, text:str):
    """A different Fraction-based oracle for the bounded tabular operators."""
    try:
        def pairs(elements):
            out={}
            for k,v in elements:
                if k in out:raise ValueError("duplicate key")
                out[k]=v
            return out
        def reject(token):raise ValueError("nonfinite")
        data=json.loads(text,object_pairs_hook=pairs,parse_float=Decimal,parse_constant=reject)
        contract=record["data_check"]
        pointer=contract["pointer"]
        selected=data
        if pointer:
            if not isinstance(pointer,str) or not pointer.startswith("/"):
                raise ValueError("bad pointer")
            for part in pointer.split("/")[1:]:
                if '~' in part and any(part[j+1:j+2] not in ('0','1') for j,c in enumerate(part) if c=='~'):
                    raise ValueError("invalid escape")
                key=part.replace("~1","/").replace("~0","~")
                if isinstance(selected,dict):selected=selected[key]
                elif isinstance(selected,list):selected=selected[int(key)]
                else:raise ValueError("scalar path")
        if not isinstance(selected,list) or len(selected)>10000:raise ValueError("rows invalid")
        op=contract["operation"]
        if op=="count_rows":number=Fraction(len(selected))
        elif op=="count_where":
            where=contract["where"]
            field=where["field"];target=where["equals"]
            count=0
            for row in selected:
                if not isinstance(row,dict) or field not in row:raise ValueError("field absent")
                got=row[field]
                if type(got) is type(target) and got==target:count+=1
            number=Fraction(count)
        elif op=="sum_field":
            number=Fraction(0)
            for row in selected:
                if not isinstance(row,dict) or contract["field"] not in row:raise ValueError("field absent")
                got=row[contract["field"]]
                if isinstance(got,bool) or not isinstance(got,(int,Decimal)):
                    raise ValueError("not numeric")
                amount = Decimal(got)
                # Mirror the declared finite input *domain*, but compute
                # quantities with Fraction rather than engine Decimal sums.
                # Out-of-range source values are not arithmetic mismatches.
                if (not amount.is_finite() or len(amount.as_tuple().digits) > 40 or
                        abs(amount.as_tuple().exponent) > 40):
                    raise ValueError("source number exceeds bounded decimal domain")
                number+=Fraction(amount)
        else:raise ValueError("unknown operator")
        expected=Fraction(Decimal(claim["quantity"]["value"]))
        return ("STRUCTURED_VALUE_MATCH" if number==expected else "STRUCTURED_VALUE_MISMATCH",
                number, len(selected))
    except (ValueError,KeyError,TypeError,IndexError,OverflowError,ArithmeticError,RecursionError):
        return "STRUCTURED_UNVERIFIABLE",None,None


def check_report(bundle:dict, report:dict)->dict:
    if not isinstance(bundle,dict) or not isinstance(report,dict):
        raise IndependentCheckError("bundle/report missing")
    claims={c["id"]:c for c in bundle["claims"]}
    readings={r["id"]:r for r in bundle["interpretations"]}
    checked=0
    reported = report.get("interpretations")
    if not isinstance(reported, list):
        raise IndependentCheckError("interpretation coverage mismatch")
    reported_ids = [item.get("id") if isinstance(item, dict) else None
                    for item in reported]
    if (len(reported_ids) != len(readings)
            or any(not isinstance(rid, str) for rid in reported_ids)
            or len(set(reported_ids)) != len(reported_ids)
            or set(reported_ids) != set(readings)):
        raise IndependentCheckError("interpretation coverage mismatch")
    for r in reported:
        spec=readings[r["id"]]
        basis = spec.get("formalization_basis", "explicit_formulas")
        if basis == "unformalized_candidate":
            result = {"status": "NOT_CHECKED_UNFORMALIZED",
                      "reason": "Auto-generated atom labels cannot test natural-language entailment."}
        elif basis == "explicit_formulas":
            result=check([claims[p]["formula"] for p in spec["premises"]],claims[spec["conclusion"]]["formula"])
        else:
            raise IndependentCheckError("unknown formalization basis")
        if result!=r["formal_inference"]:
            raise IndependentCheckError("logical checker disagrees on reading: "+r["id"])
        if not isinstance(report.get("claims"), dict):
            raise IndependentCheckError("claim reports missing for interpretation")
        try:
            unsupported = [p for p in spec["premises"]
                           if report["claims"][p]["status"] != "CONDITIONAL_FORMAL_SUPPORT_RECORDED"]
            fields = {
                "premises": spec["premises"],
                "conclusion": spec["conclusion"],
                "mapping_status": spec["mapping_status"],
                "formalization_basis": basis,
                "interpretation_notes": spec.get("interpretation_notes", ""),
                "interpretation_card": spec.get("interpretation_card", {}),
                "premises_without_uncontested_formal_evidence": unsupported,
                "semantic_fidelity_independently_verified": False,
            }
        except (KeyError, TypeError) as exc:
            raise IndependentCheckError("interpretation dependencies missing: " + r["id"]) from exc
        if (set(r) != set(fields) | {"id", "formal_inference"} or
                any(r.get(name) != value for name, value in fields.items())):
            raise IndependentCheckError("interpretation metadata mismatch: " + r["id"])
        checked+=1
    # Reporting a different set of interpretation conditions can suppress
    # prominent safety warnings without changing any per-reading inference.
    expected_flags = {
        "interpretation_sensitive_inference": len({
            r["formal_inference"]["status"] for r in reported}) > 1,
        "interpretation_cards_differ": len({
            json.dumps(r["interpretation_card"], sort_keys=True, separators=(",", ":"))
            for r in reported}) > 1,
        "interpretations_present": bool(reported),
    }
    if any(type(report.get(k)) is not bool or report[k] != v
           for k, v in expected_flags.items()):
        raise IndependentCheckError("interpretation flags mismatch")
    # Validate quotation and hashes independently (independent implementation).
    sources={s["id"]:s for s in bundle["sources"]}
    for s in sources.values():
        if hashlib.sha256(s["text"].encode("utf-8")).hexdigest()!=s["sha256"]:
            raise IndependentCheckError("independent source hash mismatch")
    for c in bundle["claims"]:
        text=sources[c["source_id"]]["text"]
        span=c["span"]
        if text[span["start"]:span["end"]]!=span["quote"]:
            raise IndependentCheckError("independent quotation mismatch")
    # Independently recompute the admissibility routing and formal relations of
    # evidence. Checking argument entailment alone leaves evidence-derived claim
    # statuses vulnerable to an undetected first-checker error.
    from datetime import datetime
    cutoff = datetime.fromisoformat(bundle["as_of"].replace("Z", "+00:00"))
    temporal = {}
    if set(report.get("source_temporal_status", {})) != set(sources):
        raise IndependentCheckError("source temporal coverage mismatch")
    for sid, source in sources.items():
        captured = source.get("captured_at")
        captured_dt = datetime.fromisoformat(captured.replace("Z", "+00:00")) if captured else None
        if captured_dt is not None and captured_dt > cutoff:
            expected_time = "AFTER_CUTOFF_OR_UNVERIFIED_HISTORICAL_VERSION"
        elif (source.get("publication_date_verified") is True
              and source.get("published_at") is not None and captured_dt is not None):
            expected_time = "IN_WINDOW"
        else:
            expected_time = "UNKNOWN_TEMPORAL_ELIGIBILITY"
        if report["source_temporal_status"][sid] != expected_time:
            raise IndependentCheckError("independent temporal eligibility mismatch: " + sid)
        temporal[sid] = expected_time

    if set(report.get("claims", {})) != set(claims):
        raise IndependentCheckError("claim report coverage mismatch")
    expected_evidence = {cid: [] for cid in claims}
    evidence_formulas_rechecked = 0
    for ev in bundle["evidence"]:
        cid, sid = ev["claim_id"], ev["source_id"]
        claim = claims[cid]
        found = [f for f in report["claims"][cid].get("evidence", [])
                 if f.get("evidence_id") == ev["id"]]
        if len(found) != 1:
            raise IndependentCheckError("missing or duplicated evidence result: " + ev["id"])
        finding = found[0]
        expected_evidence[cid].append(ev["id"])
        if (finding.get("source_id") != sid or
                finding.get("temporal_status") != temporal[sid] or
                finding.get("claimed_relation") != ev["relation"]):
            raise IndependentCheckError("evidence reference or status mismatch: " + ev["id"])
        if ("origin_id" not in finding or
                finding["origin_id"] != sources[sid].get("origin_id")):
            raise IndependentCheckError("evidence origin differs from source record: " + ev["id"])
        if finding.get("mapping_status") != ev["mapping_status"]:
            raise IndependentCheckError("evidence mapping status mismatch: " + ev["id"])
        if "data_check" in ev:
            if temporal[sid] != "IN_WINDOW":
                relation = "TEMPORAL_NOT_ADMISSIBLE"
            elif (sid == claim["source_id"] and
                  ev["span"]["start"] < claim["span"]["end"] and
                  claim["span"]["start"] < ev["span"]["end"]):
                relation = "SELF_REFERENCE_NOT_CORROBORATION"
            else:
                relation = "NOT_APPLICABLE_TO_STRUCTURED_CHECK"
        elif temporal[sid] != "IN_WINDOW":
            relation = "TEMPORAL_NOT_ADMISSIBLE"
        elif (sid == claim["source_id"] and
                  ev["span"]["start"] < claim["span"]["end"] and
                  claim["span"]["start"] < ev["span"]["end"]):
            relation = "SELF_REFERENCE_NOT_CORROBORATION"
        elif "formula" not in ev:
            relation = "UNTESTED_SEMANTIC_ASSESSMENT"
        else:
            pos = check([ev["formula"]], claim["formula"])
            neg = check([ev["formula"]], {"not": claim["formula"]})
            if pos["status"] == "INCONSISTENT_PREMISES":
                relation = "INCONSISTENT_EVIDENCE_FORMULA"
            elif pos["status"] == "NOT_CHECKED_ATOM_LIMIT":
                relation = "NOT_CHECKED_ATOM_LIMIT"
            elif pos["status"] == "ENTAILS_CONDITIONALLY":
                relation = "FORMALLY_SUPPORTS_IF_MAPPINGS_CORRECT"
            elif neg["status"] == "ENTAILS_CONDITIONALLY":
                relation = "FORMALLY_CONTRADICTS_IF_MAPPINGS_CORRECT"
            else:
                relation = "DOES_NOT_ESTABLISH"
            if relation == "DOES_NOT_ESTABLISH" and finding.get("countermodel") != pos["countermodel"]:
                raise IndependentCheckError("evidence countermodel mismatch: " + ev["id"])
            discrepancy = (
                (ev["relation"] == "supports" and relation != "FORMALLY_SUPPORTS_IF_MAPPINGS_CORRECT")
                or (ev["relation"] == "contradicts" and relation != "FORMALLY_CONTRADICTS_IF_MAPPINGS_CORRECT")
            )
            if finding.get("assessment_disagrees_with_formalization", False) is not discrepancy:
                raise IndependentCheckError("evidence assessment discrepancy mismatch: " + ev["id"])
            evidence_formulas_rechecked += 1
        if "data_check" in ev:
            structured = finding.get("structured_check")
            if (not isinstance(structured, dict)
                    or finding.get("structured_temporal_eligibility") != temporal[sid]):
                raise IndependentCheckError("structured annotation mismatch: " + ev["id"])
            disagrees = (
                (ev["relation"] == "supports" and
                 structured.get("status") != "STRUCTURED_VALUE_MATCH")
                or (ev["relation"] == "contradicts" and
                    structured.get("status") != "STRUCTURED_VALUE_MISMATCH")
            )
            if ("assessment_disagrees_with_structured_check" in finding) != disagrees or (
                disagrees and finding["assessment_disagrees_with_structured_check"] is not True
            ):
                raise IndependentCheckError("structured annotation mismatch: " + ev["id"])
        if finding.get("formal_relation") != relation:
            raise IndependentCheckError("independent formal evidence mismatch: " + ev["id"])
    for cid, expected_ids in expected_evidence.items():
        if report["claims"][cid].get("mapping_status") != claims[cid]["mapping_status"]:
            raise IndependentCheckError("claim mapping status mismatch: " + cid)
        if report["claims"][cid].get("origin_independence_verified") is not False:
            raise IndependentCheckError("claim origin independence marker mismatch: " + cid)
        findings = report["claims"][cid].get("evidence", [])
        if (len(findings) != len(expected_ids)
                or {f.get("evidence_id") for f in findings} != set(expected_ids)):
            raise IndependentCheckError("extraneous or missing claim evidence: " + cid)
        pos = [f for f in findings if f["formal_relation"] == "FORMALLY_SUPPORTS_IF_MAPPINGS_CORRECT"]
        neg = [f for f in findings if f["formal_relation"] == "FORMALLY_CONTRADICTS_IF_MAPPINGS_CORRECT"]
        status = ("CONFLICT_RECORDED" if pos and neg else
                  "CONDITIONAL_FORMAL_SUPPORT_RECORDED" if pos else
                  "CONDITIONAL_FORMAL_CONTRADICTION_RECORDED" if neg else
                  "NOT_ESTABLISHED")
        if report["claims"][cid].get("status") != status:
            raise IndependentCheckError("independent claim evidence aggregation mismatch: " + cid)
        origin_ids = sorted({sources[f["source_id"]]["origin_id"] for f in pos
                             if sources[f["source_id"]].get("origin_id") is not None})
        unknown_origins = sorted({f["source_id"] for f in pos
                                  if sources[f["source_id"]].get("origin_id") is None})
        if (report["claims"][cid].get("support_origin_ids") != origin_ids or
                report["claims"][cid].get("support_sources_with_unknown_origin") != unknown_origins):
            raise IndependentCheckError("claim support lineage mismatch: " + cid)
    arithmetic_count=0
    for ev in bundle["evidence"]:
        text=sources[ev["source_id"]]["text"]
        span=ev["span"]
        if text[span["start"]:span["end"]]!=span["quote"]:
            raise IndependentCheckError("independent evidence quote mismatch")
        if "data_check" in ev:
            claim=claims[ev["claim_id"]]
            expected_status,expected_value,rows_inspected=_separate_numeric_recompute(claim,ev,text)
            found=next((e.get("structured_check") for e in report["claims"][ev["claim_id"]]["evidence"]
                        if e.get("evidence_id")==ev["id"]),None)
            if not isinstance(found,dict) or found.get("status")!=expected_status:
                raise IndependentCheckError("arithmetic recheck differs: "+ev["id"])
            base_fields = {"status", "declared_value", "unit",
                           "semantic_mapping_verified", "source_authenticity_verified"}
            detail_fields = ({"reason"} if expected_status == "STRUCTURED_UNVERIFIABLE"
                             else {"computed_value", "operation", "rows_inspected"})
            if (set(found) != base_fields | detail_fields
                    or found["declared_value"] != claim["quantity"]["value"]
                    or found["unit"] != claim["quantity"]["unit"]
                    or found["semantic_mapping_verified"] is not False
                    or found["source_authenticity_verified"] is not False):
                raise IndependentCheckError("structured metadata mismatch: " + ev["id"])
            if expected_status == "STRUCTURED_UNVERIFIABLE":
                if not isinstance(found["reason"], str) or not found["reason"].strip():
                    raise IndependentCheckError("structured metadata mismatch: " + ev["id"])
            elif (found["operation"] != ev["data_check"]["operation"]
                    or type(found["rows_inspected"]) is not int
                    or found["rows_inspected"] != rows_inspected):
                raise IndependentCheckError("structured metadata mismatch: " + ev["id"])
            if expected_value is not None:
                try:
                    if Fraction(Decimal(found.get("computed_value")))!=expected_value:
                        raise ValueError("value changed")
                except (ValueError,TypeError,ArithmeticError) as exc:
                    raise IndependentCheckError("computed numeric value differs: "+ev["id"]) from exc
            arithmetic_count+=1
    for cid, claim_report in report["claims"].items():
        findings = claim_report["evidence"]
        admissible = [f["structured_check"] for f in findings
                      if "structured_check" in f
                      and temporal[f["source_id"]] == "IN_WINDOW"
                      and f["formal_relation"] != "SELF_REFERENCE_NOT_CORROBORATION"]
        snapshot = [f["structured_check"] for f in findings
                    if "structured_check" in f
                    and f["formal_relation"] in {
                        "TEMPORAL_NOT_ADMISSIBLE", "SELF_REFERENCE_NOT_CORROBORATION"}]
        matches = sum(x["status"] == "STRUCTURED_VALUE_MATCH" for x in admissible)
        mismatches = sum(x["status"] == "STRUCTURED_VALUE_MISMATCH" for x in admissible)
        expected_summary = {
            "status": ("CONFLICTING_STRUCTURED_VALUES" if matches and mismatches else
                       "STRUCTURED_VALUE_MATCH_CONDITIONALLY" if matches else
                       "STRUCTURED_VALUE_MISMATCH_CONDITIONALLY" if mismatches else
                       "SNAPSHOT_ONLY_VALUE_CHECK_TEMPORALLY_INADMISSIBLE" if snapshot else
                       "NOT_ESTABLISHED"),
            "matches": matches, "mismatches": mismatches,
            "unverifiable": len(admissible) - matches - mismatches,
            "snapshot_only_not_admissible": len(snapshot),
            "snapshot_only_matches": sum(x["status"] == "STRUCTURED_VALUE_MATCH" for x in snapshot),
            "snapshot_only_mismatches": sum(x["status"] == "STRUCTURED_VALUE_MISMATCH" for x in snapshot),
            "claim_meaning_verified": False,
            "temporal_eligibility_not_promoted_by_computation": True,
        }
        if claim_report.get("structured_value_checks") != expected_summary:
            raise IndependentCheckError("independent structured summary mismatch: " + cid)
    if report.get("unknowns") != bundle.get("unknowns"):
        raise IndependentCheckError("assurance boundary mismatch: unknowns")
    # Reify the declared non-production guarantees as a second explicit
    # checker contract. An audit-engine regression may not silently promote a
    # statement about world truth, source authenticity or semantic fidelity.
    assurance_contract = {
        "formal_entailment": "exhaustive bounded propositional valuations",
        "source_integrity": "byte-level SHA-256 of supplied snapshot, not authenticity",
        "quote_validation": "exact span equality, not semantic entailment",
        "semantic_fidelity": "unverified: claim and evidence text to atoms/formulas is supplied by author",
        "evidence_independence": "origin_ids are reported, not independently authenticated",
        "real_world_truth": "not established",
        "open_world_search_completeness": "not established",
        "structured_numbers": "deterministic computations over supplied JSON, not verification of measurement, population, scope, or claim interpretation",
    }
    if report.get("assurance_boundary") != assurance_contract:
        raise IndependentCheckError("assurance boundary mismatch: declared limitations")
    # Independently bind top-level report identity and self-excluding digest.
    # Keep these after structural/semantic checks so diagnostic regressions
    # preserve the more specific violated-field error messages.
    try:
        canonical_input = json.dumps(bundle, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode("utf-8")
        input_hash = hashlib.sha256(canonical_input).hexdigest()
        report_without_digest = {k: v for k, v in report.items() if k != "report_sha256"}
        report_bytes = json.dumps(report_without_digest, sort_keys=True,
                                  separators=(",", ":"), ensure_ascii=False,
                                  allow_nan=False).encode("utf-8")
        report_hash = hashlib.sha256(report_bytes).hexdigest()
    except (ValueError, TypeError, OverflowError, RecursionError) as exc:
        raise IndependentCheckError("invalid report identity serialization") from exc
    expected_identity = {
        "schema": "far-investigation-report/0.2",
        "engine": "far-investigation-audit/0.4.1",
        "investigation_id": bundle["investigation_id"],
        "input_sha256": input_hash,
        "as_of": bundle["as_of"],
        "report_sha256": report_hash,
    }
    for field, expected in expected_identity.items():
        if report.get(field) != expected:
            raise IndependentCheckError("independent report identity mismatch: " + field)
    return {"independent_algorithm_agrees":True,"structured_computations_rechecked":arithmetic_count,"readings_checked":checked,
            "evidence_formulas_rechecked":evidence_formulas_rechecked,
            "source_hashes_checked":len(sources),"semantic_correspondence_checked":False,
            "independent_human_replication":False}
