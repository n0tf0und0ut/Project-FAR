"""A deliberately small, total controlled-language compiler, not general NLP.

Opaque lexical predicates, fixed reference, nonempty quantified population.
Unsupported syntax abstains; no paraphrase model supplies its own correctness.
"""
from __future__ import annotations

import itertools
import re
import copy
from datetime import date
from engine import canonical, digest, required

VERSION = "far-semantic/1.0"
TERM = r"[a-z][a-z0-9_-]*(?: [a-z][a-z0-9_-]*){0,2}"
WORD = r"[a-z][a-z0-9_-]*"
RESERVED = set("he she it they this that these those allegedly reportedly probably unless except most many few not and or if then only some all every no before after during in on may must can should would could might will who which whose".split())
NUMBER_WORDS=dict(zip("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty".split(),range(21)))


def normalize(text):
    return re.sub(r"\s+", " ", re.sub(r"^(?:therefore|thus|hence),?\s+", "", text.strip(), flags=re.I)).rstrip(".").lower()


def _term(text):
    return re.fullmatch(TERM, text) is not None and not (set(text.split()) & RESERVED)


def compile_text(text, *, depth=0):
    """Return an AST only when *all* source syntax is in the declared grammar."""
    if not isinstance(text, str) or len(text) > 1000 or depth > 4:
        return None
    s = normalize(text)
    # Only this finite table is admitted; arbitrary number words remain unknown.
    words=re.fullmatch(r"(at least|at most|more than|less than|exactly) ([a-z]+) (.+)",s)
    if words and words[2] in NUMBER_WORDS:
        s=f"{words[1]} {NUMBER_WORDS[words[2]]} {words[3]}"
    m = re.fullmatch(r"if (.+?)(?:,)? then (.+)", s)
    if m:
        a, b = (compile_text(v, depth=depth+1) for v in m.groups())
        return {"kind": "implies", "operands": [a, b]} if a and b else None
    temporal = None
    m = re.search(r" (before|after|during|in|on) (\d{4}(?:-\d{2}(?:-\d{2})?)?)$", s)
    if m:
        temporal = {"relation": m[1], "literal": m[2]}
        try:
            date.fromisoformat(m[2]+("-01-01" if len(m[2])==4 else "-01" if len(m[2])==7 else ""))
        except ValueError:
            return None
        s = s[:m.start()]
    m = re.fullmatch(rf"({TERM}) (causes|is correlated with) ({TERM})", s)
    if m and _term(m[1]) and _term(m[3]):
        return {"kind": "relation", "subject": m[1], "object": m[3], "relation": m[2], "time": temporal}
    m = re.fullmatch(rf"(?:(some|all|every|no) |(at least|at most|more than|less than|exactly) ([0-9]{{1,2}}) )?({TERM}) (are|were|is|was|may be|must be|can be|will be|should be) (not )?({WORD})", s)
    if not m or not _term(m[4]) or not (_term(m[7]) or m[7] in {"on","off"}):
        return None
    q, comparison, number, subject, copula, negation, predicate = m.groups()
    if q == "every":
        q = "all"
    return {"kind": "predication", "quantifier": q or ("count" if comparison else "singular"),
            "threshold": {"comparison": comparison, "number": int(number)} if comparison else None,
            "subject": subject, "predicate": predicate, "negative": bool(negation),
            "copula": copula, "time": temporal}


def formula_meaning(formula, atoms):
    op, value = next(iter(formula.items()))
    if op == "atom":
        return compile_text(atoms[value])
    parts = [formula_meaning(x, atoms) for x in ([value] if op == "not" else value)]
    if any(x is None for x in parts):
        return None
    if op == "not" and parts[0].get("kind")=="predication":
        child=copy.deepcopy(parts[0])
        if child["quantifier"]=="singular":
            if child["copula"] not in {"is","was","are","were"} or child["time"] is not None:
                return None
            child["negative"]=not child["negative"]
            return child
        if child["quantifier"] in {"some","no"}:
            child["quantifier"]={"some":"no","no":"some"}[child["quantifier"]]
            return child
        if child["quantifier"]=="all":
            if child["copula"] not in {"is","was","are","were"}:
                return None
            child["quantifier"]="some"
            child["negative"]=not child["negative"]
            return child
    return {"kind": op, "operands": parts}


def round_trip(formula, atoms):
    op, value = next(iter(formula.items()))
    if op == "atom":
        return atoms[value]
    parts = [round_trip(x, atoms).rstrip(".") for x in ([value] if op == "not" else value)]
    if op == "implies":
        return f"If {parts[0]}, then {parts[1]}."
    return ("Not ("+parts[0]+")" if op == "not" else (" "+op+" ").join("("+p+")" for p in parts))


def _count_truth(ast, population, positives):
    count = population - positives if ast["negative"] else positives
    q = ast["quantifier"]
    if q == "some":
        return count > 0
    if q == "all":
        return count == population
    if q == "no":
        return count == 0
    t = ast["threshold"]
    if t:
        n = t["number"]
        return {"at least": count >= n, "at most": count <= n,
                "more than": count > n, "less than": count < n, "exactly": count == n}[t["comparison"]]
    return None


def contrast(a, b):
    """Checked finite witnesses where defined; otherwise a typed AST contrast."""
    if a == b:
        return None
    shared = (a.get("kind") == b.get("kind") == "predication" and
              all(a.get(k) == b.get(k) for k in ("subject", "predicate", "copula", "time")) and
              a["quantifier"] != "singular" and b["quantifier"] != "singular")
    if shared:
        cap = max(2, *(x["threshold"]["number"]+1 if x.get("threshold") else 2 for x in (a,b)))
        # This is a witness search, never an unbounded equivalence decision.
        for n in range(1, min(cap, 101)+1):
            for k in range(n+1):
                left, right = _count_truth(a,n,k), _count_truth(b,n,k)
                if left != right:
                    return {"type": "FORMAL_COUNTERMODEL", "contract": "nonempty finite opaque predicate population",
                            "population": n, "positive_count": k,
                            "source_value": left, "interpretation_value": right, "rechecked": True}
    return {"type": "ALTERNATIVE_INTERPRETATION", "source_ast": a, "interpretation_ast": b,
            "rechecked": a != b, "limit": "Syntactic semantic distinction; not a causal intervention or world countermodel."}


def fidelity(text, formula, atoms):
    a, b = compile_text(text), formula_meaning(formula, atoms)
    reconstructed = round_trip(formula, atoms)
    if a is None or b is None:
        status, witness = "ABSTAIN", None
    elif a == b:
        status, witness = "SUPPORTED_IN_GRAMMAR", None
    else:
        witness = contrast(a,b)
        # Different syntax is not by itself proof of different truth conditions.
        # Count/polarity equivalents lacking a distinguishing witness abstain.
        same_predicate=(a.get("kind")==b.get("kind")=="predication" and
                        all(a.get(k)==b.get(k) for k in ("subject","predicate","copula","time")))
        if same_predicate and witness["type"]!="FORMAL_COUNTERMODEL":
            status, witness = "ABSTAIN", None
        else:
            status = "CONTRADICTED"
    return {"schema": VERSION, "status": status, "source_ast": a, "interpretation_ast": b,
            "round_trip": reconstructed, "witness": witness,
            "assumptions": ["English controlled grammar only; lexical terms are opaque and reference-fixed.",
                            "Quantified population is nonempty; no unstated taxonomy or entity resolution.",
                            "No pragmatic, presupposition, or general paraphrase equivalence guarantee."],
            "unknowns": ["Meaning outside the grammar and actual source intent are unverified."] if status == "ABSTAIN" else [],
            "semantic_id": digest(canonical(a)) if a else None}


def collisions(records):
    """Same formal encoding, distinct checked source meanings: sufficiency fails."""
    groups = {}
    for record in records:
        groups.setdefault(canonical(record["formula"]), []).append(record)
    out = []
    for group in groups.values():
        for a,b in itertools.combinations(group,2):
            left, right = compile_text(a["text"]), compile_text(b["text"])
            if left is not None and right is not None and left != right:
                witness=contrast(left,right)
                if (left.get("kind")==right.get("kind")=="predication" and
                    all(left.get(k)==right.get(k) for k in ("subject","predicate","copula","time")) and
                    witness["type"]!="FORMAL_COUNTERMODEL"):
                    continue
                out.append({"claim_ids": [a["id"],b["id"]], "representation": a["formula"],
                            "lost_distinction": witness})
    return out


def collision_contract(collision,claims,*,as_of):
    """Use the existing far-ir/2.0 verifier for the exact two-case collision."""
    import sys
    from pathlib import Path
    root=str(Path(__file__).resolve().parents[2])
    if root not in sys.path:sys.path.insert(0,root)
    from mechanization.far_mechanization.contract_v2 import contract_sha256,validate_contract
    ids=collision["claim_ids"]
    contract={"id":"debugger.collision.contract","contract_version":"2.0","mode":"exact",
        "source_domain":{"status":"EXPLICIT","kind":"finite_explicit","description":"Only the two listed claim occurrences","cases":[{"id":c,"value":claims[c]["span"]} for c in ids]},
        "required_behavior":{"status":"EXPLICIT","description":"Preserve the declared controlled-grammar AST distinctions; not general intent","table":[{"case_id":c,"value":compile_text(claims[c]["text"])} for c in ids]},
        "representation":{"status":"EXPLICIT","description":"Supplied propositional encoding","table":[{"case_id":c,"value":claims[c]["formula"]} for c in ids]},
        "observation_contexts":[{"id":"obs.ast","description":"Inspect the declared semantic AST","status":"EXPLICIT"}],
        "admitted_transformations":[{"id":"eq.literal","kind":"equivalence","description":"Literal equality of table values","status":"EXPLICIT"}],
        "interpretation_profile":{"id":"interp.controlled","description":"Opaque fixed-reference controlled English grammar","status":"EXPLICIT"},
        "target_model_class":{"id":"target.two","description":"Two listed cases only","status":"EXPLICIT"},
        "frame":{"id":"frame.grammar","description":"No additional lexical or world premises","status":"EXPLICIT"}}
    record={"format_version":"far-ir/2.0","id":"debugger.collision", "contract":contract,
        "report":{"outcome":"REFUTED","evidence":{"kind":"collision","status":"CHECKED_FINITE_EXPLICIT","left_case_id":ids[0],"right_case_id":ids[1]},"failure_report":["Same propositional representation loses a declared AST distinction."]},
        "provenance":{"producer":VERSION,"created_at":as_of,"sources":[]},
        "freeze":{"status":"FROZEN","frozen_at":as_of,"contract_sha256":contract_sha256(contract)}}
    result=validate_contract(record)
    required(result.success,"existing far-ir/2.0 rejected generated collision witness")
    return record
