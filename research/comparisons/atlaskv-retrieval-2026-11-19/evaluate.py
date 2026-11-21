"""CPU evidence-retrieval stress test. This does NOT run AtlasKV model weights.

Arms: flat TF-IDF (metadata retained), flat TF-IDF (bare triples),
unsupervised hierarchical TF-IDF proxy, and an oracle with a supplied
structured query plan. The oracle is an upper bound, not a fair competitor.

The deterministic answerer receives the same predeclared query semantics for
all arms and only inspects selected evidence. It is not an LLM.
"""
from __future__ import annotations
from collections import defaultdict
import csv
import hashlib
import json
import platform
from pathlib import Path
from time import perf_counter_ns

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
import sklearn

BASE=Path(__file__).resolve().parent
SEED=20261119
BUDGET=8
ARMS=('flat_tfidf_full','flat_tfidf_triples','hierarchical_proxy_full','structured_graph_oracle')

def load_frozen():
    manifest=json.loads((BASE/'frozen_manifest.json').read_text())
    blob=(BASE/'frozen_fixture.json').read_bytes()
    assert hashlib.sha256(blob).hexdigest()==manifest['fixture_sha256'], 'fixture seal broken'
    data=json.loads(blob)
    assert len(data['cases'])==manifest['cases'] and len(data['facts'])==manifest['facts']
    assert BUDGET==manifest['retrieval_budget_facts']
    return manifest,data

def fact_text(f, full=True):
    base=f"{f['subject']} {f['relation'].replace('_',' ')} {f['object']}"
    if full:
        if f['source'] is not None: base+=f" according to {f['source']}"
        if f['valid_from'] is not None: base+=f" effective {f['valid_from']}"
    return base

def project(f):
    return {k:f[k] for k in ['id','subject','relation','object']}

def deterministic_answer(case, selected):
    """Returns UNKNOWN whenever selected evidence cannot justify an exact answer."""
    frontier=[case['anchor']]
    for relation in case['relations']:
        next_frontier=[]
        for entity in frontier:
            eligible=[f for f in selected if f['subject']==entity and f['relation']==relation]
            if case['source'] is not None:
                eligible=[f for f in eligible if f.get('source')==case['source']]
            if case['as_of'] is not None:
                eligible=[f for f in eligible if f.get('valid_from') is not None and f['valid_from']<=case['as_of']]
                if eligible:
                    latest=max(f['valid_from'] for f in eligible)
                    eligible=[f for f in eligible if f['valid_from']==latest]
            if len(eligible)!=1:
                return 'UNKNOWN'
            next_frontier.append(eligible[0]['object'])
        frontier=next_frontier
    return frontier[0] if len(frontier)==1 else 'UNKNOWN'

class BenchmarkIndex:
    def __init__(self, facts):
        self.facts=facts
        self.ids={f['id']:f for f in facts}
        self.text_full=[fact_text(f,True) for f in facts]
        self.text_triple=[fact_text(f,False) for f in facts]
        self.v_full=TfidfVectorizer(ngram_range=(1,2),sublinear_tf=True)
        self.v_triple=TfidfVectorizer(ngram_range=(1,2),sublinear_tf=True)
        self.f_full=self.v_full.fit_transform(self.text_full)
        self.f_triple=self.v_triple.fit_transform(self.text_triple)
        n_components=min(32,self.f_full.shape[0]-1,self.f_full.shape[1]-1)
        self.svd=TruncatedSVD(n_components=n_components,random_state=SEED)
        self.x=normalize(self.svd.fit_transform(self.f_full))
        root=KMeans(n_clusters=8,random_state=SEED,n_init=4).fit_predict(self.x)
        self.root_members={r:np.flatnonzero(root==r) for r in range(8)}
        self.root_centers=np.array([normalize(self.x[ix].mean(axis=0).reshape(1,-1))[0] for ix in self.root_members.values()])
        self.inter_members={}; self.inter_root={}; self.inter_centers=[]
        for r,indices in self.root_members.items():
            k=min(4,len(indices))
            groups=KMeans(n_clusters=k,random_state=SEED+int(r),n_init=3).fit_predict(self.x[indices]) if k>1 else np.zeros(len(indices),dtype=int)
            for j in range(k):
                gid=len(self.inter_centers)
                members=indices[groups==j]
                self.inter_members[gid]=members
                self.inter_root[gid]=r
                self.inter_centers.append(normalize(self.x[members].mean(axis=0).reshape(1,-1))[0])
        self.inter_centers=np.array(self.inter_centers)

    @staticmethod
    def _top(scores, count):
        # Fully deterministic tie rule.
        return sorted(range(len(scores)),key=lambda i:(-float(scores[i]),i))[:count]

    def select(self,case,arm):
        if arm=='structured_graph_oracle':
            # Execute the supplied typed query plan over the full graph. Crucially,
            # retrieval NEVER reads the expected answer or supporting proof IDs.
            frontier=[case['anchor']]
            evidence=[]
            for rel in case['relations']:
                candidates=[f for f in self.facts if f['subject'] in frontier and f['relation']==rel]
                if case['source'] is not None:
                    candidates=[f for f in candidates if f['source']==case['source']]
                if case['as_of'] is not None:
                    candidates=[f for f in candidates if f['valid_from'] is not None and f['valid_from']<=case['as_of']]
                candidates.sort(key=lambda f:f['id'])
                evidence.extend(candidates)
                if case['as_of'] is not None and candidates:
                    newest=max(f['valid_from'] for f in candidates)
                    frontier=[f['object'] for f in candidates if f['valid_from']==newest]
                else:
                    frontier=[f['object'] for f in candidates]
            return evidence[:BUDGET]
        if arm.startswith('flat_'):
            vectorizer, matrix=(self.v_full,self.f_full) if arm=='flat_tfidf_full' else (self.v_triple,self.f_triple)
            q=vectorizer.transform([case['question']])
            scores=(matrix@q.T).toarray().ravel()
            ids=self._top(scores,BUDGET)
            selected=[self.facts[i] for i in ids]
            return selected if arm=='flat_tfidf_full' else [project(f) for f in selected]
        if arm=='hierarchical_proxy_full':
            q=self.svd.transform(self.v_full.transform([case['question']]))
            q=normalize(q)[0]
            root_pick=self._top(self.root_centers@q,3)
            inter_candidates=[gid for gid,r in self.inter_root.items() if r in root_pick]
            inter_rank=sorted(inter_candidates,key=lambda i:(-float(self.inter_centers[i]@q),i))[:6]
            leaf_candidates=sorted({int(idx) for gid in inter_rank for idx in self.inter_members[gid]})
            leaf_rank=sorted(leaf_candidates,key=lambda i:(-float(self.x[i]@q),i))[:BUDGET]
            return [self.facts[i] for i in leaf_rank]
        raise ValueError(arm)

def collide(data):
    ids={f['id']:f for f in data['facts']}
    checks=[]
    for c in data['collision_candidates']:
        a,b=(dict(ids[i]) for i in c['facts'])
        before=[a,b]
        after=[dict(a),dict(b)]
        if c['kind']=='provenance_swap':
            after[0]['source'],after[1]['source']=after[1]['source'],after[0]['source']
            get=lambda rows: next(r['object'] for r in rows if r['source']==c['query_source'])
        elif c['kind']=='timestamp_swap':
            after[0]['valid_from'],after[1]['valid_from']=after[1]['valid_from'],after[0]['valid_from']
            def get(rows):
                rows=[r for r in rows if r['valid_from'] <= c['as_of']]
                return max(rows,key=lambda r:r['valid_from'])['object']
        else: raise ValueError(c['kind'])
        proj=lambda rows: sorted((r['subject'],r['relation'],r['object']) for r in rows)
        equal=(proj(before)==proj(after))
        answers_change=(get(before)!=get(after))
        checks.append(dict(id=c['id'],kind=c['kind'],same_triple_projection=equal,changed_contract_answer=answers_change))
    return checks

def run():
    manifest,data=load_frozen()
    collisions=collide(data)
    assert all(x['same_triple_projection'] and x['changed_contract_answer'] for x in collisions)
    idx=BenchmarkIndex(data['facts'])
    rows=[]
    for case in data['cases']:
        for arm in ARMS:
            start=perf_counter_ns()
            selected=idx.select(case,arm)
            elapsed=(perf_counter_ns()-start)/1e6
            observed=deterministic_answer(case,selected)
            selected_ids={f['id'] for f in selected}
            if case['family'] in ('contradiction','temporal') and arm=='flat_tfidf_triples':
                proof_complete=False  # necessary metadata is unrepresented
            else:
                proof_complete=all(fid in selected_ids for fid in case['proof']) if case['proof'] else None
            rows.append(dict(case_id=case['id'],family=case['family'],arm=arm,expected=case['answer'],observed=observed,
                         exact=int(observed==case['answer']),proof_complete=proof_complete,
                         selected_ids=';'.join(f['id'] for f in selected),latency_ms=round(elapsed,5)))
    with (BASE/'case_results.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    summary={'schema':'atlaskv-far-retrieval-results/1.0','manifest_sha256':hashlib.sha256((BASE/'frozen_manifest.json').read_bytes()).hexdigest(),
             'fixture_sha256':manifest['fixture_sha256'], 'facts':len(data['facts']), 'cases':len(data['cases']),
             'collision_witnesses':dict(total=len(collisions),provenance=sum(x['kind']=='provenance_swap' for x in collisions),temporal=sum(x['kind']=='timestamp_swap' for x in collisions),all_valid=all(x['same_triple_projection'] and x['changed_contract_answer'] for x in collisions)),
             'hardware':{'python':platform.python_version(),'sklearn':sklearn.__version__,'numpy':np.__version__, 'processor':'CPU only'},
             'scope':'Exploratory internal synthetic retrieval and projection test; no AtlasKV weights, LLM outputs, or external evaluation',
             'arms':{}}
    for arm in ARMS:
        arm_rows=[r for r in rows if r['arm']==arm]
        known=[r for r in arm_rows if r['proof_complete'] is not None]
        unknown=[r for r in arm_rows if r['expected']=='UNKNOWN']
        out={'exact_answer':sum(r['exact'] for r in arm_rows),'cases':len(arm_rows),
             'full_proof':sum(r['proof_complete'] is True for r in known),'known_cases':len(known),
             'unknown_abstentions':sum(r['exact'] for r in unknown),'unknown_cases':len(unknown),
             'median_retrieval_ms':round(float(np.median([r['latency_ms'] for r in arm_rows])),5),
             'family_exact':{fam:{'correct':sum(r['exact'] for r in arm_rows if r['family']==fam),
                                  'total':sum(r['family']==fam for r in arm_rows)}
                             for fam in sorted({r['family'] for r in arm_rows})}}
        summary['arms'][arm]=out
    (BASE/'collision_witnesses.json').write_text(json.dumps(collisions,indent=2,sort_keys=True)+'\n')
    (BASE/'results_summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':run()
