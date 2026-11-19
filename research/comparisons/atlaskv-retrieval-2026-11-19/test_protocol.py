"""Independent checks on the benchmark fixtures, selectors, and adjudication."""
from collections import Counter
from copy import deepcopy
import hashlib
import pytest
from evaluate import load_frozen, collide, BenchmarkIndex, deterministic_answer, project, ARMS, BUDGET

@pytest.fixture(scope='module')
def bundle():
    _, data=load_frozen()
    return data

@pytest.fixture(scope='module')
def index(bundle):
    return BenchmarkIndex(bundle['facts'])

def test_frozen_facts_and_case_uniqueness(bundle):
    assert len(bundle['facts'])==364
    assert len(bundle['cases'])==108
    assert len({f['id'] for f in bundle['facts']})==364
    assert len({c['id'] for c in bundle['cases']})==108
    assert Counter(c['family'] for c in bundle['cases']) == dict(multi_hop=36,contradiction=24,temporal=24,unknown_entity=12,unknown_source=12)

def test_collisions_are_real_counterexamples(bundle):
    records=collide(bundle)
    assert len(records)==48
    assert all(r['same_triple_projection'] and r['changed_contract_answer'] for r in records)

def test_graph_retriever_never_reads_gold(bundle,index):
    for c in bundle['cases']:
        got=[f['id'] for f in index.select(c,'structured_graph_oracle')]
        bogus=deepcopy(c)
        bogus['answer']='CORRUPTED';bogus['proof']=['FICTIONAL-ID']
        assert got==[f['id'] for f in index.select(bogus,'structured_graph_oracle')]

def test_graph_retriever_supports_all_known_cases(bundle,index):
    for c in bundle['cases']:
        got=index.select(c,'structured_graph_oracle')
        assert len(got)<=BUDGET
        assert all(fid in {f['id'] for f in got} for fid in c['proof'])
        assert deterministic_answer(c,got)==c['answer']

def test_source_is_not_implicitly_in_a_triple(bundle):
    c=next(c for c in bundle['cases'] if c['family']=='contradiction')
    matched=[f for f in bundle['facts'] if f['subject']==c['anchor']]
    assert deterministic_answer(c, matched)==c['answer']
    assert deterministic_answer(c, [project(f) for f in matched])=='UNKNOWN'

def test_time_is_not_implicitly_in_a_triple(bundle):
    c=next(c for c in bundle['cases'] if c['family']=='temporal')
    matched=[f for f in bundle['facts'] if f['subject']==c['anchor']]
    assert deterministic_answer(c,matched)==c['answer']
    assert deterministic_answer(c,[project(f) for f in matched])=='UNKNOWN'

def test_multi_hop_requires_all_three_edges(bundle):
    c=next(c for c in bundle['cases'] if c['family']=='multi_hop')
    evidence=[f for f in bundle['facts'] if f['id'] in c['proof']]
    assert deterministic_answer(c,evidence)==c['answer']
    for i in range(3):
        assert deterministic_answer(c,evidence[:i]+evidence[i+1:])=='UNKNOWN'

def test_source_swap_changes_answer(bundle):
    c=next(c for c in bundle['cases'] if c['family']=='contradiction')
    evidence=[dict(f) for f in bundle['facts'] if f['subject']==c['anchor']]
    assert len(evidence)==2
    prior=deterministic_answer(c,evidence)
    evidence[0]['source'],evidence[1]['source']=evidence[1]['source'],evidence[0]['source']
    assert deterministic_answer(c,evidence)!=prior

def test_no_arm_exceeds_budget(bundle,index):
    for c in bundle['cases']:
        for arm in ARMS:
            got=index.select(c,arm)
            assert 0<=len(got)<=BUDGET
            assert len({f['id'] for f in got})==len(got)
