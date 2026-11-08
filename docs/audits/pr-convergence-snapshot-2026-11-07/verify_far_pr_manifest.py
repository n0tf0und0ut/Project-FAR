#!/usr/bin/env python3
"""Verify a FAR PR convergence snapshot and optionally compare it to live GitHub.

Usage:
  python verify_far_pr_manifest.py project_far_current_head_convergence.json
  GITHUB_TOKEN=... python verify_far_pr_manifest.py path.json --live

Offline mode checks snapshot integrity, not freshness. Live mode compares all open
PR identities, protected branch check source IDs, current-head check runs,
Codex machine summaries, all GraphQL review threads, and evidence-file blobs.
A failure of any GitHub read aborts verification: no silent success downgrade.
No write APIs are used. No merge authority or reviewer assurance is granted.
"""
from __future__ import annotations
import argparse
import collections
import copy
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SHA40 = re.compile(r'[0-9a-f]{40}\Z')
CHECKS = [('merge-authority',15368),('protected-repin-gate',5073230),('pr-review-convergence-observation',15368)]
BOT_LOGIN = 'chatgpt-codex-connector[bot]'
BOT_APP = 'chatgpt-codex-connector'
BOT_APP_ID = 1144995
MARKER = re.compile(r'<!-- codex-review-state:v1 (\{[^\n]*\}) -->')

class AuditError(ValueError):
    pass

def require(ok, error):
    if not ok:
        raise AuditError(error)

def verify_snapshot(s):
    require(s.get('schema')=='far-pr-current-head-convergence-snapshot/1.0','unexpected schema')
    require(s.get('repo')=='n0tf0und0ut/Project-FAR','incorrect repository identity')
    main=s['main']['sha'];require(SHA40.fullmatch(main),'invalid protected main sha')
    require(s['main'].get('protected') is True,'main protection not observed')
    require(s['main']['required_checks']==[{'name':n,'app_id':i} for n,i in CHECKS],'protected check source profile drift')
    prs=s['pull_requests'];require(len(prs)==20,'wrong open PR inventory size')
    pmap={p['pr']:p for p in prs}
    require(len(pmap)==len(prs),'duplicate PR number')
    require(490 in pmap,'permanent draft inbox missing')
    ids=set(pmap)
    for p in prs:
        n=p['pr'];head=p['live_head_sha'];prefix=f'PR #{n}'
        require(SHA40.fullmatch(head),f'{prefix}: missing exact head')
        require(p['state']=='open' and p['target_branch']=='main',f'{prefix}: wrong target/state')
        require(p['url']==f'https://github.com/n0tf0und0ut/Project-FAR/pull/{n}',f'{prefix}: URL misbound')
        require(p['protected_main_sha_at_observation']==main,f'{prefix}: main ref mixing')
        require(SHA40.fullmatch(p['github_pr_base_sha_at_observation']),f'{prefix}: missing base SHA')
        require(p['base_is_current_main']==(p['github_pr_base_sha_at_observation']==main),f'{prefix}: base comparison false')
        declared=p['body_declared_candidate_sha']
        require(declared is None or SHA40.fullmatch(declared),f'{prefix}: malformed claimed head')
        require(p['body_candidate_matches_live']==(declared==head),f'{prefix}: incorrect claimed/live SHA comparison')
        e=p['evidence_reference']
        require(SHA40.fullmatch(e['exact_head_blob_sha']),f'{prefix}: missing evidence blob SHA')
        require(e['exact_head_file_verified'] is True,f'{prefix}: missing evidence read')
        require(e['exact_head_url']==f'https://github.com/n0tf0und0ut/Project-FAR/blob/{head}/{e["path"]}',f'{prefix}: evidence not bound to head')
        hist=e['historical_ref_commit'];hist_blob=e['historical_ref_blob_sha']
        require((hist is None and hist_blob is None) or (hist and hist_blob and SHA40.fullmatch(hist) and SHA40.fullmatch(hist_blob)),f'{prefix}: incomplete history identity')
        expected='not_compared' if hist is None else ('unchanged' if hist_blob==e['exact_head_blob_sha'] else 'changed')
        require(e['historical_byte_identity']==expected,f'{prefix}: wrong evidence identity disposition')
        checks=p['required_checks']
        require(len(checks)==3, f'{prefix}: check count incomplete')
        for c,(name,aid) in zip(checks,CHECKS):
            require(c['context']==name and c['required_app_id']==aid,f'{prefix}: check source mismatch')
            require(c['observed_status'] in ('not_observed','completed','in_progress'),f'{prefix}: unknown check status')
            require(c['observed_conclusion'] in ('success','failure',None),f'{prefix}: bad check conclusion')
            require((c['observed_status']=='completed')==(c['observed_conclusion'] is not None),f'{prefix}: status/conclusion inconsistent')
            require(bool(c['job_or_check_id'])==(c['observed_status']!='not_observed'),f'{prefix}: check identity gap')
            api=f'https://api.github.com/repos/n0tf0und0ut/Project-FAR/check-runs/{c["job_or_check_id"]}' if c['job_or_check_id'] else None
            require(c.get('check_api_url')==api,f'{prefix}: check API URL not bound to check identity')
        v=p['reviews']
        require(v['human_approvals']==0 and v['human_changes_requested']==0,f'{prefix}: owner/human review not supported by snapshot')
        reviewed=v['reviewed_sha']
        require(reviewed is None or SHA40.fullmatch(reviewed),f'{prefix}: bad review SHA')
        require(v['exact_head_coverage']==(v['completed'] and reviewed==head),f'{prefix}: stale review misidentified as current')
        require(v['total_threads']>=len(v['unresolved_threads']),f'{prefix}: impossible thread count')
        sid=v.get('summary_comment_id')
        expected_url=f'https://github.com/n0tf0und0ut/Project-FAR/issues/{n}#issuecomment-{sid}' if sid else None
        require(v.get('summary_url')==expected_url,f'{prefix}: bot summary provenance URL mismatch')
        for f in v['unresolved_threads']:
            require(f.get('thread_id') and f['state']=='open',f'{prefix}: incomplete finding evidence')
            require(f.get('source_url','').startswith(f'https://github.com/n0tf0und0ut/Project-FAR/pull/{n}#discussion_r'),f'{prefix}: missing source-linked current finding')
            require(f.get('source_comment_head_sha')==head,f'{prefix}: finding source not bound to live head')
        for d in p['dependencies']:
            require(d['pr'] in ids and d['pr']!=n,f'{prefix}: missing dependency PR')
            require(d.get('confidence')=='explicit_PR_body',f'{prefix}: unverified dependency promoted')
        require(all(z in ids for z in p['integration_risks_with_prs']),f'{prefix}: bad integration link')
        require(not p['merge_authorized'],f'{prefix}: unsupported merge authorization')
        if n==617:
            auth=p.get('authorization_document',{})
            require(auth.get('at_live_head_sha')==head and auth.get('target_pr')==617 and SHA40.fullmatch(auth.get('git_blob_sha','')),f'{prefix}: unverified signed-repin request')
            require(auth.get('signature_count_observed_valid')==0,f'{prefix}: signature claim not source-supported')
        if n==490:
            require(p['draft'] and p['disposition']=='KEEP_OPEN_DRAFT_NEVER_MERGE',f'{prefix}: rolling inbox merge-invariant violated')
        else:
            require(p['disposition']=='BLOCKED_NO_MERGE',f'{prefix}: unsupported promotion')
            require(any(b['class']=='protected_merge_authorization' for b in p['blockers']),f'{prefix}: authorization missing')
            for c in checks:
                if c['observed_conclusion']!='success':
                    require(any(b['class']=='required_gate' and c['context'] in b['reason'] for b in p['blockers']),f'{prefix}: failed check concealed')
            if v['unresolved_threads']:
                require(any(b['class']=='substantive_findings' for b in p['blockers']),f'{prefix}: unresolved finding concealed')
    computed={
      'open_prs':len(prs),
      'ordinary_merge_candidates':sum(p['pr']!=490 for p in prs),
      'perpetual_inbox':sum(p['pr']==490 for p in prs),
      'ordinary_candidate_bodies_not_pinning_live_sha':sum(not p['body_candidate_matches_live'] for p in prs if p['pr']!=490),
      'current_head_automated_clean_review':sum(p['reviews']['exact_head_coverage'] and p['reviews']['has_unresolved_findings'] is False for p in prs),
      'review_convergence_failures':sum(c['observed_conclusion']=='failure' for p in prs for c in p['required_checks'] if c['context']=='pr-review-convergence-observation'),
      'open_threads':sum(len(p['reviews']['unresolved_threads']) for p in prs),
      'all_three_required_checks_green':sum(all(c['observed_conclusion']=='success' for c in p['required_checks']) for p in prs),
      'blocked_ordinary_prs':sum(p['disposition']=='BLOCKED_NO_MERGE' for p in prs),
    }
    if 'literal_pr_body_github_urls' in s['counts']:
        refs=[z for p in prs for z in p.get('pr_body_github_urls',[])]
        urls=[z['url'] for z in refs]
        require(len(urls)==s['counts']['literal_pr_body_github_urls'], 'literal PR body URL count drift')
        for p in prs:
            r=p.get('pr_body_github_urls',[])
            require(len(r)==len({x['url'] for x in r}), f'PR #{p["pr"]}: duplicate body URLs')
            require(all(x['url'].startswith('https://github.com/n0tf0und0ut/Project-FAR/') for x in r),f'PR #{p["pr"]}: off-origin body URL')
        computed['literal_pr_body_github_urls']=len(refs)
    require(s['counts']==computed, f'false aggregate: observed {s["counts"]}, computed {computed}')
    return computed

class GithubReader:
    def __init__(self, token, repo):
        require(token and '\n' not in token and '\r' not in token,'GITHUB_TOKEN required for live audit')
        self.token=token;self.repo=repo
        self.api_root='https://api.github.com/repos/'+repo
    def fetch(self,url,post=None):
        require(url.startswith('https://api.github.com/'),'non-GitHub URL refused')
        b=None if post is None else json.dumps(post).encode('utf8')
        req=urllib.request.Request(url, data=b, headers={
            'Accept':'application/vnd.github+json','Authorization':'Bearer '+self.token,
            'X-GitHub-Api-Version':'2022-11-28','Content-Type':'application/json',
            'User-Agent':'FAR-exact-head-observer/1.0'},
            method='POST' if b is not None else 'GET')
        try:
            with urllib.request.urlopen(req,timeout=30) as f: data=f.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as ex:
            raise AuditError('GitHub API read failed: '+url+' '+str(ex)) from ex
        try: return json.loads(data)
        except ValueError as ex: raise AuditError('invalid JSON from '+url) from ex
    def get(self,route): return self.fetch(self.api_root+route)
    def paginate(self,route):
        out=[]
        for page in range(1,41):
            sep='&' if '?' in route else '?'
            result=self.get(route+sep+'per_page=100&page='+str(page))
            require(isinstance(result,list),'unparseable paginated collection: '+route)
            out.extend(result)
            if len(result)<100:return out
        raise AuditError('pagination exceeds 40 pages: '+route)
    def threads(self,n):
        query='''query($owner:String!,$repo:String!,$number:Int!,$cursor:String){repository(owner:$owner,name:$repo){pullRequest(number:$number){reviewThreads(first:50,after:$cursor){pageInfo{hasNextPage endCursor} nodes{id isResolved isOutdated path line comments(first:1){nodes{databaseId}}}}}}}'''
        owner,repo=self.repo.split('/')
        out=[];cursor=None
        for page in range(40):
            payload=self.fetch('https://api.github.com/graphql',{'query':query,'variables':{'owner':owner,'repo':repo,'number':n,'cursor':cursor}})
            require(not payload.get('errors'),'GraphQL returned errors for PR '+str(n))
            try:v=payload['data']['repository']['pullRequest']['reviewThreads']
            except (KeyError,TypeError) as ex:raise AuditError('incomplete GraphQL review threads') from ex
            out.extend(v['nodes'])
            if not v['pageInfo']['hasNextPage']:
                require(len({t['id'] for t in out})==len(out),'duplicate thread IDs');return out
            nxt=v['pageInfo']['endCursor'];require(nxt and nxt!=cursor,'invalid thread pagination cursor');cursor=nxt
        raise AuditError('review thread pagination incomplete')

def latest_codex_summary(comments):
    states=[]
    for c in comments:
        body=c.get('body') or ''
        if '<!-- codex-review-state:v1 ' not in body:continue
        user=c.get('user') or {};app=c.get('performed_via_github_app') or {}
        require(user.get('login')==BOT_LOGIN and user.get('type')=='Bot' and
                app.get('slug')==BOT_APP and app.get('id')==BOT_APP_ID,
                'unauthenticated summary marker present (cannot trust it)')
        matches=MARKER.findall(body)
        require(len(matches)==1,'ambiguous Codex machine-state markers')
        try: state=json.loads(matches[0])['code_review']
        except (KeyError,ValueError) as ex:raise AuditError('malformed Codex state') from ex
        states.append((c['updated_at'],c['id'],state))
    states.sort(key=lambda r:(r[0],r[1]))
    if not states:return None
    require(len(states)==1 or states[-1][0]!=states[-2][0], 'ambiguous latest summary times')
    return states[-1]

def normalize_check(runs,name,expected_app):
    matching=[x for x in runs if x.get('name')==name]
    if not matching:return ('not_observed',None,None)
    for c in matching:
        require(c.get('app',{}).get('id')==expected_app,'check name spoofed by wrong App: '+name)
    # Latest started check takes precedence; GitHub will decide required policy itself.
    matching.sort(key=lambda x:(x.get('started_at') or '',x.get('id',0)))
    latest=matching[-1]
    status=latest['status']
    conclusion=latest['conclusion']
    if status=='completed':
        require(isinstance(conclusion,str),'completed check missing conclusion')
    else: conclusion=None
    return (status,conclusion,latest['id'])

def compare_live(s,reader):
    errors=[]
    def check(cond,what):
        if not cond:errors.append(what)
    original_main=s['main']['sha']
    begin=reader.get('/git/ref/heads/main')['object']['sha']
    branch=reader.get('/branches/main')
    check(begin==original_main,f'protected main moved: {original_main} -> {begin}')
    check(branch['commit']['sha']==begin,'different main SHA from branch and git-ref endpoints')
    checks=branch['protection']['required_status_checks']['checks']
    check({(x['context'],x['app_id']) for x in checks}==set(CHECKS),'required branch context/App source changed')
    list_raw=reader.paginate('/pulls?state=open')
    expected={p['pr']:p for p in s['pull_requests']}
    actual={p['number']:p for p in list_raw}
    check(set(actual)==set(expected),f'open PR inventory drift: expected {sorted(expected)}, live {sorted(actual)}')
    for n,p in expected.items():
        if n not in actual:continue
        rp=reader.get('/pulls/'+str(n))
        check(rp.get('state')=='open',f'#{n} is no longer open')
        check(rp['head']['sha']==p['live_head_sha'],f'#{n} head changed: {p["live_head_sha"]} -> {rp["head"]["sha"]}')
        check(rp['base']['sha']==p['github_pr_base_sha_at_observation'],f'#{n} recorded PR base changed')
        check(rp['base']['ref']=='main',f'#{n} no longer targets main')
        check(rp['draft']==p['draft'],f'#{n} draft state changed')
        actual_body=rp.get('body') or ''
        check((p['live_head_sha'] in actual_body)==p['body_candidate_matches_live'],f'#{n} body candidate assertion drift')
        if rp['head']['sha']!=p['live_head_sha']:
            # Reviews/checks on a changed head still queried to find all drift, but report is unqualified.
            pass
        summaries=reader.paginate('/issues/'+str(n)+'/comments')
        summ=latest_codex_summary(summaries)
        expected_review=p['reviews']
        if not expected_review['reviewed_sha']:
            check(summ is None,f'#{n} new Codex summary appears')
        else:
            check(summ is not None,f'#{n} Codex summary disappeared')
            if summ:
                check(summ[2].get('commit_sha')==expected_review['reviewed_sha'],f'#{n} Codex summary exact head changed')
                check(summ[2].get('status')=='completed',f'#{n} latest review no longer completed')
                check(summ[2].get('has_unresolved_findings')==expected_review['has_unresolved_findings'],f'#{n} latest Codex findings changed')
        review_submissions=reader.paginate('/pulls/'+str(n)+'/reviews')
        check(sum(x.get('state')=='APPROVED' and x.get('user',{}).get('login')!=rp['user']['login'] for x in review_submissions)==expected_review['human_approvals'],f'#{n} human approval changed')
        check(sum(x.get('state')=='CHANGES_REQUESTED' for x in review_submissions)==expected_review['human_changes_requested'],f'#{n} changes-requested state changed')
        threads=reader.threads(n)
        check(len(threads)==expected_review['total_threads'],f'#{n} review thread inventory changed')
        ids={t['id'] for t in threads if not t['isResolved']}
        check(ids=={t['thread_id'] for t in expected_review['unresolved_threads']},f'#{n} unresolved review thread set changed')
        run_collection=reader.get('/commits/'+urllib.parse.quote(rp['head']['sha'])+'/check-runs?per_page=100')
        require(run_collection.get('total_count',0)<=100,f'#{n} check runs >100: unsupported incomplete pagination')
        runs=run_collection.get('check_runs')
        require(isinstance(runs,list),'check run API malformed')
        for c in p['required_checks']:
            st,con,job=normalize_check(runs,c['context'],c['required_app_id'])
            check((st,con,job)==(c['observed_status'],c['observed_conclusion'],c['job_or_check_id']),f'#{n} required check changed: {c["context"]} => {(st,con,job)}')
        ev=p['evidence_reference']
        pathname='/'.join(urllib.parse.quote(piece,safe='') for piece in ev['path'].split('/'))
        file_meta=reader.get('/contents/'+pathname+'?ref='+rp['head']['sha'])
        check(file_meta.get('sha')==ev['exact_head_blob_sha'],f'#{n} evidence blob changed on actual head')
    end=reader.get('/git/ref/heads/main')['object']['sha']
    check(end==begin,'protected main changed during audit')
    final_open={p['number']:p['head']['sha'] for p in reader.paginate('/pulls?state=open')}
    check(final_open=={n:p['live_head_sha'] for n,p in expected.items()},'open PR inventory/head moved during audit')
    return errors

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--live',action='store_true',help='compare against current authenticated GitHub API; no writes')
    args=parser.parse_args(argv)
    try:
        s=json.loads(args.manifest.read_text())
        counts=verify_snapshot(s)
        print('SNAPSHOT_INVARIANTS_PASS',json.dumps(counts,sort_keys=True))
        if args.live:
            api=GithubReader(os.environ.get('GITHUB_TOKEN'),s['repo'])
            errors=compare_live(s,api)
            if errors:
                for e in errors:print('DRIFT',e,file=sys.stderr)
                print('LIVE_RECONCILIATION_FAILED',len(errors),file=sys.stderr)
                return 1
            print('LIVE_RECONCILIATION_PASS')
        else:print('LIVE_NOT_CHECKED: offline snapshot validation only')
        return 0
    except (AuditError,KeyError,IndexError,TypeError,ValueError) as ex:
        print('AUDIT_FAILED',str(ex),file=sys.stderr)
        return 2
if __name__=='__main__':sys.exit(main())
