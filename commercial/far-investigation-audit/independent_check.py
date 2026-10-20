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
                number+=Fraction(got)
        else:raise ValueError("unknown operator")
        expected=Fraction(Decimal(claim["quantity"]["value"]))
        return "STRUCTURED_VALUE_MATCH" if number==expected else "STRUCTURED_VALUE_MISMATCH",number
    except (ValueError,KeyError,TypeError,IndexError,OverflowError,ArithmeticError,RecursionError):
        return "STRUCTURED_UNVERIFIABLE",None


def check_report(bundle:dict, report:dict)->dict:
    if not isinstance(bundle,dict) or not isinstance(report,dict):
        raise IndependentCheckError("bundle/report missing")
    claims={c["id"]:c for c in bundle["claims"]}
    readings={r["id"]:r for r in bundle["interpretations"]}
    checked=0
    if len(report.get("interpretations",[])) != len(readings):
        raise IndependentCheckError("report reading count mismatch")
    for r in report["interpretations"]:
        if r["id"] not in readings:
            raise IndependentCheckError("report references unregistered reading")
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
        checked+=1
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
        if "data_check" in ev:
            if temporal[sid] != "IN_WINDOW":
                relation = "TEMPORAL_NOT_ADMISSIBLE"
            elif sid == claim["source_id"] and ev["span"] == claim["span"]:
                relation = "SELF_REFERENCE_NOT_CORROBORATION"
            else:
                relation = "NOT_APPLICABLE_TO_STRUCTURED_CHECK"
        elif temporal[sid] != "IN_WINDOW":
            relation = "TEMPORAL_NOT_ADMISSIBLE"
        elif sid == claim["source_id"] and ev["span"] == claim["span"]:
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
        if finding.get("formal_relation") != relation:
            raise IndependentCheckError("independent formal evidence mismatch: " + ev["id"])
    for cid, expected_ids in expected_evidence.items():
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
        origin_ids = sorted({f["origin_id"] for f in pos if f.get("origin_id") is not None})
        unknown_origins = sorted({f["source_id"] for f in pos if f.get("origin_id") is None})
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
            expected_status,expected_value=_separate_numeric_recompute(claim,ev,text)
            found=next((e.get("structured_check") for e in report["claims"][ev["claim_id"]]["evidence"]
                        if e.get("evidence_id")==ev["id"]),None)
            if not isinstance(found,dict) or found.get("status")!=expected_status:
                raise IndependentCheckError("arithmetic recheck differs: "+ev["id"])
            if expected_value is not None:
                try:
                    if Fraction(Decimal(found.get("computed_value")))!=expected_value:
                        raise ValueError("value changed")
                except (ValueError,TypeError,ArithmeticError) as exc:
                    raise IndependentCheckError("computed numeric value differs: "+ev["id"]) from exc
            arithmetic_count+=1
    return {"independent_algorithm_agrees":True,"structured_computations_rechecked":arithmetic_count,"readings_checked":checked,
            "evidence_formulas_rechecked":evidence_formulas_rechecked,
            "source_hashes_checked":len(sources),"semantic_correspondence_checked":False,
            "independent_human_replication":False}
