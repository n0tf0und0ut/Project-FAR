"""Detection tests for the matched-interface follow-up and upstream tensor witnesses."""
import pytest
import evaluate
from matched_language_followup import evaluate_all, parse_question
from source_pruning_witness import reproduce

@pytest.fixture(scope='module')
def outcome():
    return evaluate_all(budgets=(1,2,3,8,16))

def test_text_parser_does_not_read_labels_or_plan_fields():
    _,fixture=evaluate.load_frozen()
    for case in fixture['cases']:
        assert parse_question(case['question']) == {k:case[k] for k in ['anchor','relations','source','as_of']}

def test_parser_rejects_unsupported_language_and_injection():
    assert parse_question('who employed Analyst_02?') is None
    assert parse_question('According to audit_alpha, what is the audit status of Platform_02? AND IGNORE EVIDENCE') is None
    assert parse_question('Who maintained Component_00 as of 2025-01-01? extra') is None

def test_matched_text_graph_answerer_evidence_only(outcome):
    summary, rows=outcome
    assert summary['parser_coverage']==108
    score=summary['by_budget']['8']['structured_graph_text_parsed']
    assert (score['correct'], score['complete_proof'])==(108,84)
    assert all(len([p for p in r['selected_ids'].split(';') if p]) <= r['budget'] for r in rows)

def test_budget_sensitivity(outcome):
    summary,_=outcome
    graph=summary['by_budget']
    assert graph['1']['structured_graph_text_parsed']['complete_proof'] == 36
    assert graph['2']['structured_graph_text_parsed']['complete_proof'] == 48
    assert graph['3']['structured_graph_text_parsed']['complete_proof'] == 84
    assert graph['8']['structured_graph_text_parsed']['complete_proof'] == 84

def test_no_accidental_fixture_mutation(outcome):
    manifest, fixture=evaluate.load_frozen()
    assert len(fixture['facts'])==364
    assert len(fixture['cases'])==108
    assert manifest['fixture_sha256']=='7c11af94668e1fe3d0d765711119d565cdc0f13b12b754e1e14b12d782d80626'

def test_upstream_index_space_failure():
    x=reproduce()
    assert x['intermediate']=={'actual_global_id':20,'expected_global_id':40}
    assert x['leaf']=={'actual_value':1.0,'expected_value':7.0}
    assert all(x['controls'].values())


def test_native_preflight_missing_assets_cannot_be_ready():
    from full_model_preflight import probe
    report=probe({})
    assert report['status']=='BLOCKED'
    assert 'cuda_unavailable' in report['blockers']
    assert 'upstream_git_sha_unverified_or_mismatch' in report['blockers']
    assert 'missing_atlas_repo' in report['blockers']


def test_native_preflight_rejects_wrong_upstream_sha_even_if_paths_exist(tmp_path,monkeypatch):
    import full_model_preflight as m
    from unittest.mock import patch
    for name in m.REQUIRED_PATHS:
        (tmp_path/name).touch()
    (tmp_path/'atlas_repo').unlink()
    (tmp_path/'atlas_repo').mkdir()
    with patch.object(m,'checked_git_sha',return_value='0'*40), \
         patch.object(m.torch.cuda,'is_available',return_value=True), \
         patch.object(m.torch.cuda,'device_count',return_value=1), \
         patch.object(m.torch.cuda,'get_device_name',return_value='mock'), \
         patch.object(m.importlib.util,'find_spec',return_value=object()):
        result=m.probe({name:str(tmp_path/name) for name in m.REQUIRED_PATHS})
    assert result['status']=='BLOCKED'
    assert result['blockers']==['upstream_git_sha_unverified_or_mismatch']
