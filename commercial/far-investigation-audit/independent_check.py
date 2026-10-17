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
            "source_hashes_checked":len(sources),"semantic_correspondence_checked":False,
            "independent_human_replication":False}
