"""Produce a deterministic, frozen, synthetic evidence-retrieval benchmark.

All facts and answers describe fictional entities. This benchmark is not an
external validation dataset and is not part of FAR's governed EFR program.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import random

SEED = 20261119
BASE = Path(__file__).resolve().parent

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def create():
    rng = random.Random(SEED)
    facts, cases, collisions = [], [], []
    def fact(fid, subject, relation, obj, source=None, valid_from=None):
        facts.append(dict(id=fid, subject=subject, relation=relation, object=obj, source=source, valid_from=valid_from))
    def case(cid, family, question, anchor, relations, answer, proof, source=None, as_of=None):
        cases.append(dict(id=cid, family=family, question=question, anchor=anchor, relations=relations, source=source,
                          as_of=as_of, answer=answer, proof=proof))

    for i in range(36):
        p,o,s,m = (f'Analyst_{i:02d}', f'Org_{i:02d}', f'Service_{i:02d}', f'Method_{i:02d}')
        ids = [f'M{i:02d}-1',f'M{i:02d}-2',f'M{i:02d}-3']
        fact(ids[0],p,'employed_by',o,'personnel_registry')
        fact(ids[1],o,'operates',s,'operations_registry')
        fact(ids[2],s,'powered_by',m,'architecture_registry')
        case(f'M{i:02d}','multi_hop',f'What method powers the service operated by the organization employing {p}?',
             p,['employed_by','operates','powered_by'],m,ids)

    for i in range(24):
        s=f'Platform_{i:02d}'
        a,b=('approved','rejected') if i%2==0 else ('rejected','approved')
        aid,bid=f'C{i:02d}-A',f'C{i:02d}-B'
        fact(aid,s,'audit_status',a,'audit_alpha')
        fact(bid,s,'audit_status',b,'audit_beta')
        src,answer,proof=('audit_alpha',a,aid) if i%2==0 else ('audit_beta',b,bid)
        case(f'C{i:02d}','contradiction',f'According to {src}, what is the audit status of {s}?',
             s,['audit_status'],answer,[proof],source=src)
        collisions.append({'id':f'C{i:02d}', 'kind':'provenance_swap','facts':[aid,bid],
                           'query_source':src,'answers_differ_after_swap':True})

    for i in range(24):
        s=f'Component_{i:02d}'; old=f'TeamLegacy_{i:02d}'; new=f'TeamCurrent_{i:02d}'
        oid,nid=f'T{i:02d}-old',f'T{i:02d}-new'
        fact(oid,s,'maintained_by',old,'ownership_ledger','2024-01-01')
        fact(nid,s,'maintained_by',new,'ownership_ledger','2026-01-01')
        dt,ans,proof=('2025-01-01',old,[oid]) if i%2==0 else ('2026-11-01',new,[oid,nid])
        case(f'T{i:02d}','temporal',f'Who maintained {s} as of {dt}?',
             s,['maintained_by'],ans,proof,as_of=dt)
        collisions.append({'id':f'T{i:02d}','kind':'timestamp_swap','facts':[oid,nid],
                           'as_of':dt,'answers_differ_after_swap':True})

    for i in range(12):
        subj=f'Unregistered_{i:02d}'
        case(f'U{i:02d}','unknown_entity',f'According to audit_alpha, what is the audit status of {subj}?',
             subj,['audit_status'],'UNKNOWN',[],source='audit_alpha')
    for i in range(12):
        subj=f'Platform_{i:02d}'
        case(f'V{i:02d}','unknown_source',f'According to audit_gamma, what is the audit status of {subj}?',
             subj,['audit_status'],'UNKNOWN',[],source='audit_gamma')

    for i in range(160):
        fid=f'D{i:03d}'
        subj=f'Distractor_{i%67:02d}'
        rel=['employed_by','operates','powered_by','audit_status','maintained_by'][i%5]
        obj=[f'Org_{rng.randrange(36):02d}', f'Service_{rng.randrange(36):02d}',
             f'Method_{rng.randrange(36):02d}', 'approved','unknown'][i%5]
        fact(fid,subj,rel,obj,source='distractor_registry')

    rng.shuffle(facts)
    rng.shuffle(cases)
    fixture={'schema':'atlaskv-far-retrieval-fixture/1.0','seed':SEED,'facts':facts,'cases':cases,'collision_candidates':collisions}
    blob=canonical(fixture)
    (BASE/'frozen_fixture.json').write_bytes(blob)
    manifest={'schema':'atlaskv-far-experiment-manifest/1.0','research_status':'exploratory_internal',
       'fixture_sha256':hashlib.sha256(blob).hexdigest(), 'facts':len(facts),'cases':len(cases),
       'metrics':['full_proof_recall@8','exact_answer_rate','unknown_abstention_rate',
                  'triple_projection_collision_count','retrieval_cpu_ms'],
       'arms':['flat_tfidf_full','flat_tfidf_triples','hierarchical_proxy_full','structured_graph_oracle'],
       'retrieval_budget_facts':8,
       'constraints':'No AtlasKV weights or CUDA; hierarchical proxy uses TF-IDF plus hierarchical clustering, not AtlasKV inference',
       'source_implementation':'HKUST-KnowComp/AtlasKV: src/atlaskv/models/llama3_model.py; inspected 2026-11-19'}
    (BASE/'frozen_manifest.json').write_bytes(canonical(manifest))
    print(json.dumps(manifest,indent=2))

if __name__=='__main__':create()
