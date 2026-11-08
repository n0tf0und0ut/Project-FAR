import copy
import json
import pathlib
import unittest
import importlib.util

P=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('far_validator',P/'verify_far_pr_manifest.py')
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class ManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads((P/'project_far_current_head_convergence.json').read_text())
    def fresh(self):return copy.deepcopy(self.data)
    def test_complete_snapshot(self):
        out=mod.verify_snapshot(self.fresh())
        self.assertEqual(out['open_prs'],20)
        self.assertEqual(out['review_convergence_failures'],17)
        self.assertEqual(out['open_threads'],2)
        self.assertEqual(out['all_three_required_checks_green'],0)
    def test_reject_dropped_pr(self):
        x=self.fresh();x['pull_requests'].pop()
        with self.assertRaises(mod.AuditError):mod.verify_snapshot(x)
    def test_reject_forged_green_gate(self):
        x=self.fresh();p=next(z for z in x['pull_requests'] if z['pr']==623)
        p['required_checks'][2]['observed_conclusion']='success'
        with self.assertRaises(mod.AuditError):mod.verify_snapshot(x)
    def test_reject_review_sha_spoof(self):
        x=self.fresh();p=next(z for z in x['pull_requests'] if z['pr']==623)
        p['reviews']['exact_head_coverage']=True
        with self.assertRaises(mod.AuditError):mod.verify_snapshot(x)
    def test_reject_suppressed_findings(self):
        x=self.fresh();p=next(z for z in x['pull_requests'] if z['pr']==623)
        p['reviews']['unresolved_threads']=[]
        with self.assertRaises(mod.AuditError):mod.verify_snapshot(x)
    def test_reject_inbox_promotion(self):
        x=self.fresh();p=next(z for z in x['pull_requests'] if z['pr']==490)
        p['disposition']='BLOCKED_NO_MERGE'
        with self.assertRaises(mod.AuditError):mod.verify_snapshot(x)
    def test_reject_wrong_required_app(self):
        x=self.fresh();p=next(z for z in x['pull_requests'] if z['pr']==625)
        p['required_checks'][0]['required_app_id']=1
        with self.assertRaises(mod.AuditError):mod.verify_snapshot(x)
    def test_reject_forged_evidence_identity(self):
        x=self.fresh();p=next(z for z in x['pull_requests'] if z['pr']==597)
        p['evidence_reference']['historical_byte_identity']='unchanged'
        with self.assertRaises(mod.AuditError):mod.verify_snapshot(x)
    def test_latest_summary_authentication(self):
        normal={'id':1,'updated_at':'2026-11-07T00:00:00Z','user':{'login':mod.BOT_LOGIN,'type':'Bot'},'performed_via_github_app':{'slug':mod.BOT_APP,'id':mod.BOT_APP_ID},'body':'<!-- codex-review-state:v1 {"code_review":{"commit_sha":"'+'a'*40+'","status":"completed","has_unresolved_findings":false}} -->'}
        self.assertEqual(mod.latest_codex_summary([normal])[2]['status'],'completed')
        normal['performed_via_github_app']['id']=1
        with self.assertRaises(mod.AuditError):mod.latest_codex_summary([normal])
    def test_reject_spoofed_required_check_app(self):
        runs=[{'id':5,'name':'merge-authority','app':{'id':8},'started_at':'2026-11-07T00:00:00Z','status':'completed','conclusion':'success'}]
        with self.assertRaises(mod.AuditError):mod.normalize_check(runs,'merge-authority',15368)
    def test_reject_missing_live_token(self):
        with self.assertRaises(mod.AuditError):mod.GithubReader('', 'n0tf0und0ut/Project-FAR')

if __name__=='__main__':unittest.main(verbosity=2)

class SimulatedLiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot=json.loads((P/'project_far_current_head_convergence.json').read_text())

    class Reader:
        def __init__(self,s):
            self.s=s;self.map={p['pr']:p for p in s['pull_requests']}
            self.changed_head=None
            self.inject_bad_app=None
            self.extra_thread=None
        def get(self,route):
            if route=='/git/ref/heads/main':return {'object':{'sha':self.s['main']['sha']}}
            if route=='/branches/main':return {'commit':{'sha':self.s['main']['sha']},'protection':{'required_status_checks':{'checks':[{'context':x['name'],'app_id':x['app_id']} for x in self.s['main']['required_checks']]}}}
            if route.startswith('/pulls/'):
                n=int(route.rsplit('/',1)[1]);p=self.map[n];sha=self.changed_head if n==625 and self.changed_head else p['live_head_sha']
                body=sha if p['body_candidate_matches_live'] else 'historical description'
                return {'number':n,'head':{'sha':sha},'base':{'sha':p['github_pr_base_sha_at_observation'],'ref':'main'},'draft':p['draft'],'state':'open','body':body,'user':{'login':'n0tf0und0ut'}}
            if '/commits/' in route and '/check-runs?' in route:
                sha=route.split('/commits/')[1].split('/check-runs')[0]
                p=next((q for q in self.map.values() if q['live_head_sha']==sha),None)
                if not p:return {'total_count':0,'check_runs':[]}
                runs=[]
                for c in p['required_checks']:
                    if c['job_or_check_id'] is None:continue
                    app=c['required_app_id']
                    if self.inject_bad_app and p['pr']==623 and c['context']=='merge-authority':app=1
                    runs.append({'name':c['context'],'id':c['job_or_check_id'],'app':{'id':app},'started_at':'2026-11-07T23:00:00Z','status':c['observed_status'],'conclusion':c['observed_conclusion']})
                return {'total_count':len(runs),'check_runs':runs}
            if route.startswith('/contents/'):
                _,tail=route.split('/contents/',1)
                path,sha=tail.split('?ref=')
                p=next((q for q in self.map.values() if q['live_head_sha']==sha and q['evidence_reference']['path']==path),None)
                return {'sha':p['evidence_reference']['exact_head_blob_sha'] if p else 'a'*40}
            raise AssertionError('Unexpected read: '+route)
        def paginate(self,route):
            if route=='/pulls?state=open':
                return [{'number':p['pr'],'head':{'sha':p['live_head_sha']}} for p in self.map.values()]
            if route.startswith('/issues/'):
                n=int(route.split('/')[2]);rv=self.map[n]['reviews'];sha=rv['reviewed_sha']
                if not sha:return []
                state={'code_review':{'commit_sha':sha,'status':'completed','has_any_findings':rv['has_unresolved_findings'],'has_unresolved_findings':rv['has_unresolved_findings']}}
                return [{'id':rv['summary_comment_id'],'updated_at':'2026-11-07T22:00:00Z','user':{'login':mod.BOT_LOGIN,'type':'Bot'},'performed_via_github_app':{'slug':mod.BOT_APP,'id':mod.BOT_APP_ID},'body':'<!-- codex-review-state:v1 '+json.dumps(state,separators=(',',':'))+' -->'}]
            if route.startswith('/pulls/') and route.endswith('/reviews'):
                return []
            raise AssertionError('Unexpected list: '+route)
        def threads(self,n):
            p=self.map[n];out=[{'id':f['thread_id'],'isResolved':False} for f in p['reviews']['unresolved_threads']]
            for i in range(p['reviews']['total_threads']-len(out)):
                out.append({'id':f'synthetic-resolved-{n}-{i}','isResolved':True})
            if self.extra_thread and n==625:out.append({'id':self.extra_thread,'isResolved':False})
            return out
    def test_simulated_live_roundtrip(self):
        self.assertEqual(mod.compare_live(self.snapshot,self.Reader(self.snapshot)),[])
    def test_simulated_live_detects_head_mutation(self):
        r=self.Reader(self.snapshot);r.changed_head='f'*40
        errors=mod.compare_live(self.snapshot,r)
        self.assertTrue(any('#625 head changed:' in e for e in errors))
    def test_simulated_live_detects_new_thread(self):
        r=self.Reader(self.snapshot);r.extra_thread='PRRT_new'
        errors=mod.compare_live(self.snapshot,r)
        self.assertTrue(any('#625 review thread' in e for e in errors))
    def test_simulated_live_rejects_spoofed_app(self):
        r=self.Reader(self.snapshot);r.inject_bad_app=True
        with self.assertRaises(mod.AuditError):mod.compare_live(self.snapshot,r)
