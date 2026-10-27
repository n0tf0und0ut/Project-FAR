"""Integrated epistemic checks around the existing canonical investigation audit.

The formal engine remains the sole source of propositional inference results.
This layer gates interpretation acceptance and emits model-relative repairs.
"""
from __future__ import annotations
import itertools
from engine import canonical, digest, required, validate_formula, _BoundedInference, evaluate
from semantic import fidelity, collisions, collision_contract
from cognitive import audit_traces

CONTRACT = "far-epistemic-debugger/1.0"


def runtime_identity(*,include_cognitive=False):
    """Deterministic source/version commitments, not an authenticated runtime seal."""
    from pathlib import Path
    import sys
    component=Path(__file__).resolve().parent
    root=component.parents[1]
    files=[*component.glob("*.py"),component/"debugger-1.0.schema.json",
           *root.glob("mechanization/far_mechanization/*.py"),
           root/"far_validation/epistemic_assurance.py",*root.glob("jsonschema/*.py"),
           *root.glob("schemas/*.json")]
    sources={str(p.relative_to(root)):digest(p.read_bytes()) for p in sorted(set(files))}
    optional=sys.modules.get("mechanization.far_mechanization.cognitive") if include_cognitive else None
    if optional is not None:
        sources["loaded_optional_cognitive_module"]=digest(Path(optional.__file__).read_bytes())
    payload={"schema":"far-debugger-runtime/1.0","python":".".join(map(str,sys.version_info[:3])),
             "source_sha256":sources,"boundary":"Source/version consistency only; no identity, timestamp, external truth or full-environment seal."}
    return {**payload,"identity_sha256":digest(canonical(payload))}


def repairs(premises, conclusion, *, atoms, costs=None, additions=None):
    """Exhaustive minimum-cost edit sets in a declared finite operation universe."""
    costs = {} if costs is None else costs
    additions = [] if additions is None else additions
    required(isinstance(costs,dict) and set(costs)<=set(premises) and
             all(type(v) is int and 1<=v<=10000 for v in costs.values()), "repair costs must be bounded positive integers keyed by premise")
    required(isinstance(additions,list) and len(additions)<=6, "bounded assumption additions required")
    ops = [{"operation":"withdraw_premise", "id":k, "cost":costs.get(k,1)} for k in sorted(premises)]
    seen=set()
    for a in additions:
        required(isinstance(a,dict) and set(a)=={"id","formula","cost","rationale"} and
                 isinstance(a["id"],str) and 0<len(a["id"])<=80 and a["id"] not in seen and
                 isinstance(a["rationale"],str) and 0<len(a["rationale"])<=1000 and
                 type(a["cost"]) is int and 1<=a["cost"]<=10000, "invalid admissible assumption")
        validate_formula(a["formula"],atoms)
        seen.add(a["id"])
        ops.append({"operation":"add_assumption", **a})
    logic=_BoundedInference()
    base=logic.run(list(premises.values()),conclusion)
    contract={"operations":ops, "cost_function":"sum of declared positive integer edit costs",
              "model":"bounded classical propositional semantics; consistency required",
              "meaning":"Assumption edits, not evidence discovery, causal interventions, or normative adjudication."}
    if len(ops)>8 or base["status"].startswith("NOT_CHECKED"):
        return {"status":"ABSTAIN_BOUND", "contract":contract,"base":base,"repairs":[]}
    all_nodes=[*premises.values(),conclusion,*[a["formula"] for a in additions]]
    metadata=[logic.metadata(x) for x in all_nodes]
    names=set().union(*(m[3] for m in metadata))
    estimated=(1<<len(ops))*(1<<len(names))*sum(m[2] for m in metadata)
    if len(names)>12 or estimated>1_000_000:
        return {"status":"ABSTAIN_WORK_BOUND", "contract":contract,"base":base,"repairs":[],"conservative_work_estimate":estimated}
    target="DOES_NOT_ENTAIL" if base["status"]=="ENTAILS_CONDITIONALLY" else "ENTAILS_CONDITIONALLY"
    candidates=[]
    for bits in itertools.product((False,True),repeat=len(ops)):
        selected=[o for o,b in zip(ops,bits) if b]
        candidates.append((sum(o["cost"] for o in selected),bits,selected))
    best=None
    found=[]
    checked=0
    for cost,bits,selected in sorted(candidates,key=lambda x:(x[0],x[1])):
        if best is not None and cost>best:
            break
        removed={o["id"] for o in selected if o["operation"]=="withdraw_premise"}
        ps=[v for k,v in premises.items() if k not in removed]+[o["formula"] for o in selected if o["operation"]=="add_assumption"]
        result=logic.run(ps,conclusion)
        checked+=1
        if result["status"]==target:
            # Recheck the actual modified problem, not a cached proposal label.
            from engine import entailment
            rechecked=entailment(ps,conclusion)
            required(result==rechecked, "counterfactual recheck mismatch")
            if target=="DOES_NOT_ENTAIL":
                w=result["countermodel"]
                required(w is not None and all(evaluate(p,w) for p in ps) and not evaluate(conclusion,w), "invalid repair witness")
            best=cost
            found.append({"edits":selected,"total_cost":cost,"rechecked_result":result})
    return {"status":"EXACT_MINIMUM_WITHIN_CONTRACT" if found else "NO_REPAIR_WITHIN_CONTRACT",
            "contract":contract, "base":base,"target":target,"candidate_sets_checked":checked,
            "minimum_cost":best,"repairs":found}


def debug(bundle, audit, proposal):
    required(proposal.get("debugger_contract")==CONTRACT, "unknown debugger contract")
    options=proposal.get("debugger_options",{})
    required(isinstance(options,dict) and set(options)<={"costs","admissible_assumptions","traces","epistemic_document","source_lineage","cognitive_audit"}, "unknown debugger options")
    costs=options.get("costs",{})
    adds=options.get("admissible_assumptions",{})
    reading_ids={r["id"] for r in bundle["interpretations"]}
    required(isinstance(costs,dict) and set(costs)<=reading_ids and isinstance(adds,dict) and set(adds)<=reading_ids, "unknown repair reading")
    claims={c["id"]:c for c in bundle["claims"]}
    semantics={c["id"]:{**fidelity(c["span"]["quote"],c["formula"],bundle["atoms"]),
                            "source_reference":{"source_id":c["source_id"],"span":c["span"]}}
               for c in claims.values()}
    evidence_semantics={e["id"]:fidelity(e["span"]["quote"],e["formula"],bundle["atoms"])
                        for e in bundle["evidence"] if "formula" in e}
    nodes=[]
    edges=[]
    def node(ident,kind,record):
        nodes.append({"id":ident,"type":kind,"record":record})
    def edge(a,b,relation):
        edges.append({"from":a,"to":b,"relation":relation})
    for s in bundle["sources"]:
        node("source:"+s["id"],"source",s)
    for c in claims.values():
        cid=c["id"]
        node("claim:"+cid,"assertion",c)
        node("meaning:"+cid,"interpretation",semantics[cid])
        edge("source:"+c["source_id"],"claim:"+cid,"asserts")
        edge("claim:"+cid,"meaning:"+cid,"interpreted_as")
    for e in bundle["evidence"]:
        node("evidence:"+e["id"],"evidence",e)
        edge("source:"+e["source_id"],"evidence:"+e["id"],"quotes")
        edge("evidence:"+e["id"],"meaning:"+e["claim_id"],"proposed_"+e["relation"])
    readings=[]
    for r in audit["interpretations"]:
        ids=[*r["premises"],r["conclusion"]]
        statuses=[semantics[c]["status"] for c in ids]
        accepted=(r["formal_inference"]["status"]=="ENTAILS_CONDITIONALLY" and all(x=="SUPPORTED_IN_GRAMMAR" for x in statuses))
        reason=("SEMANTIC_MISMATCH" if "CONTRADICTED" in statuses else
                "UNKNOWN_SEMANTICS" if "ABSTAIN" in statuses else r["formal_inference"]["status"])
        # Bound work across the request as well as each exact solver problem.
        result=repairs({c:claims[c]["formula"] for c in r["premises"]},claims[r["conclusion"]]["formula"],
                       atoms=bundle["atoms"],costs=costs.get(r["id"]),additions=adds.get(r["id"])) if len(audit["interpretations"])<=12 else {"status":"ABSTAIN_READING_LIMIT","repairs":[]}
        readings.append({"id":r["id"],"acceptance":"CONDITIONAL_ON_GRAMMAR_AND_PREMISES" if accepted else "NOT_ACCEPTED",
                         "reason":reason,"formal_result":r["formal_inference"],"counterfactual":result,
                         "failed_steps":[c for c in ids if semantics[c]["status"]!="SUPPORTED_IN_GRAMMAR"],
                         "next_evidence":"Authenticate premise evidence and resolve each disputed interpretation; no factual truth inferred from formal validity."})
        node("reading:"+r["id"],"inference",readings[-1])
        node("warrant:"+r["id"],"warrant",{"rule":"classical propositional entailment",
             "interpretation_notes":r["interpretation_notes"],"interpretation_card":r["interpretation_card"],
             "assumptions":"Declared formulas, meanings and premises; premise truth is not proved."})
        edge("warrant:"+r["id"],"reading:"+r["id"],"inference_rule")
        for c in r["premises"]:
            edge("meaning:"+c,"reading:"+r["id"],"premise")
        for c in ids:
            if semantics[c]["status"]=="CONTRADICTED":
                ident="defeater:"+r["id"]+":"+c
                node(ident,"interpretation_defeater",semantics[c]["witness"])
                edge("meaning:"+c,ident,"exhibits")
                edge(ident,"reading:"+r["id"],"blocks_semantic_acceptance")
        edge("meaning:"+r["conclusion"],"reading:"+r["id"],"conclusion_interpretation")
    for i,u in enumerate(bundle["unknowns"]):
        node("unknown:"+str(i),"unresolved_question",u)
    for left in bundle["interpretations"]:
        for right in bundle["interpretations"]:
            if left["id"] != right["id"] and left["conclusion"] in right["premises"]:
                edge("reading:"+left["id"],"reading:"+right["id"],"derived_premise_dependency")
    from diagnostics import critical_questions
    questions=critical_questions(bundle["claims"])
    for i,q in enumerate(questions):
        node("question:"+str(i),"critical_question",q)
        edge("claim:"+q["claim_id"],"question:"+str(i),"raises_obligation")
    # Source lineage and audit assurance compose their existing validators.
    import sys
    from pathlib import Path
    root=str(Path(__file__).resolve().parents[2])
    if root not in sys.path:
        sys.path.insert(0,root)
    from far_validation.epistemic_assurance import validate_source_lineage_set, validate_audit_assurance
    lineage=options.get("source_lineage",[])
    required(isinstance(lineage,list) and len(lineage)<=len(bundle["sources"]),"invalid source lineage list")
    if lineage:
        import jsonschema
        schema=__import__("json").loads((Path(root)/"schemas/far-source-lineage-v1.schema.json").read_text())
        for record in lineage:
            if list(jsonschema.Draft202012Validator(schema).iter_errors(record)):
                raise ValueError("invalid source lineage contract")
        validate_source_lineage_set(lineage)
        required({s["source_id"] for s in lineage}=={s["id"] for s in bundle["sources"]},"lineage must cover actual sources")
        for record in lineage:
            for upstream in record["upstream_source_ids"]:
                edge("source:"+upstream,"source:"+record["source_id"],"declared_source_lineage")
    semantic_states=[x["status"] for x in semantics.values()]+[
        evidence_semantics.get(e["id"],{"status":"ABSTAIN"})["status"] for e in bundle["evidence"]]
    semantic_status="fail" if "CONTRADICTED" in semantic_states else "unknown" if "ABSTAIN" in semantic_states else "pass"
    checks={k:{"status":"unknown","evidence":[],"limitations":["External assurance unestablished"]} for k in
            ("source_integrity","interpretation_fidelity","search_coverage","evidence_adjudication","inference_adjudication","reproducibility","hostile_source_isolation")}
    checks["source_integrity"]={"status":"pass","evidence":[audit["input_sha256"]],"limitations":["Byte integrity only, not authenticity"]}
    checks["interpretation_fidelity"]={"status":semantic_status,"evidence":[audit["input_sha256"]],"limitations":["Only declared controlled grammar"]}
    assurance={"schema":"far-audit-assurance/1.0","audit_id":audit["input_sha256"],"overall_status":"not_assured" if semantic_status=="fail" else "bounded", "checks":checks,"unresolved_defeaters":[]}
    validate_audit_assurance(assurance)
    cognition=audit_traces(options.get("traces",[]))
    if "cognitive_audit" in options:
        try:
            from mechanization.far_mechanization.cognitive import CognitiveDocument, audit as cognitive_audit
        except ImportError as exc:
            raise ValueError("canonical FAR-COG audit dependency is unavailable; no substitute diagnosis is emitted") from exc
        cognition["canonical_audit"]=cognitive_audit(CognitiveDocument.from_dict(options["cognitive_audit"]))
        node("cognitive:audit","canonical_cognitive_audit",cognition["canonical_audit"])
        for source in options["cognitive_audit"]["sources"]:
            ident="cognitive_source:"+source["id"]
            node(ident,"source",source)
            edge(ident,"cognitive:audit","canonical_audit_input_dependency")
        for record in options["cognitive_audit"]["source_lineage"]:
            for upstream in record["upstream_source_ids"]:
                edge("cognitive_source:"+upstream,"cognitive_source:"+record["source_id"],"declared_source_lineage")
    dependencies={r["id"]:set() for r in bundle["interpretations"]}
    for left in bundle["interpretations"]:
        for right in bundle["interpretations"]:
            if left["conclusion"] in right["premises"]:
                dependencies[left["id"]].add(right["id"])
    cyclic=[]
    for start in sorted(dependencies):
        visited=set()
        pending=list(dependencies[start])
        while pending:
            current=pending.pop()
            if current==start:
                cyclic.append(start)
                break
            if current not in visited:
                visited.add(current);pending.extend(dependencies[current])
    cognition["circular_dependency_readings"]=cyclic
    cognition["circularity_boundary"]="A declared dependency cycle is observable; independent premise evidence can still break justificatory circularity."
    epistemic={"status":"NOT_SUPPLIED"}
    if "epistemic_document" in options:
        # Compose the existing learning/ELENCHUS validator; never redefine it.
        from mechanization.far_mechanization.epistemic import EpistemicDocument
        document=EpistemicDocument.from_dict(options["epistemic_document"])
        epistemic={"status":"EXISTING_CONTRACT_VALIDATED","digest":document.digest,
                   "limits":"Conformance does not establish update rationality, causal identification, or general learning."}
    collision_records=collisions(list(claims.values()))
    for c in collision_records:
        c["far_ir_2_0"]=collision_contract(c,claims,as_of=bundle["as_of"])
    return {"schema":CONTRACT,"runtime_identity":runtime_identity(include_cognitive="cognitive_audit" in options),"input_sha256":audit["input_sha256"], "claims":semantics,
            "evidence_semantics":evidence_semantics,"collisions":collision_records,
            "readings":readings,"graph":{"nodes":nodes,"edges":edges},"cognitive":cognition,
            "epistemic_interchange":epistemic,"source_lineage":lineage,"audit_assurance":assurance,
            "unknowns":["External factual reliability and source authenticity unestablished.",
                        "Causal identification, normative premises, and general natural-language interpretation require separate evidence/contracts."]}


def render_debugger(result):
    lines=["\n## Epistemic debugger", "", "Controlled-language checks; external truth and general semantic fidelity remain unverified.", ""]
    for cid,c in result["claims"].items():
        lines.append(f"- {cid}: {c['status']}")
    for r in result["readings"]:
        lines.append(f"- {r['id']}: {r['acceptance']}; {r['reason']}; counterfactual {r['counterfactual']['status']}.")
    lines.append("\nFull exact source references, lost-distinction witnesses, assumption edits, dependency graph and limitations: debugger.json.\n")
    return "\n".join(lines)
