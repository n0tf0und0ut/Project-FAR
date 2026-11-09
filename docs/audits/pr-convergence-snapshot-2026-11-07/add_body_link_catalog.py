#!/usr/bin/env python3
"""Exhaustive literal GitHub URL inventory from the observed PR body snapshot.

The path data below was extracted by running a URL regexp on all twenty PR
bodies returned by GET /pulls?state=open&per_page=100. Source URLs are not
silently recast as valid/current-head execution evidence.
"""
import json
from pathlib import Path
from urllib.parse import urlparse

P=Path(__file__).resolve().parent / 'project_far_current_head_convergence.json'
s=json.loads(P.read_text())
root='https://github.com/n0tf0und0ut/Project-FAR/'
paths={
625:'actions/runs/42422391193/job/128553408474;actions/runs/42423510337;actions/runs/42423770020;pull/597;issues/597#issuecomment-6714352771',
623:'actions/runs/42254195680;actions/runs/42254895954;pull/623#issuecomment-6690201824;pull/623#issuecomment-6690164862;commit/6f59f8a539717940ac2a27cc26a8cc204eec7b1f;actions/runs/42254896773;actions/runs/42260068100;actions/runs/42260068053;actions/runs/42260067966;actions/runs/42260068055;actions/runs/42260067865;actions/runs/42415099613;actions/runs/42415099487;actions/runs/42415099511',
622:'actions/runs/42230689638;actions/runs/42230839947',
621:'actions/runs/42414344206;actions/runs/42414344134;actions/runs/42415463479;actions/runs/42415463464;actions/runs/42416104473;actions/runs/42416166985;actions/runs/42416272047;actions/runs/42416420154/job/128536226344;runs/128536185092;actions/runs/42416272018;actions/runs/42416272044;actions/runs/42416940242;actions/runs/42416964261',
620:'actions/runs/42090379885;actions/runs/42090379885/artifacts/13445236161;blob/8ca6d68fe202e3569f1ad90c1e10e546ff1508c9/research/numeric-grounding/RESULTS-LIVE-V0.1.md',
619:'actions/runs/42242559173/job/127976304759;pull/619#issuecomment-6687896846;actions/runs/42242558765/job/127976335024;actions/runs/42242558848/job/127976529599;actions/runs/42243492741/job/127979580691',
618:'blob/8ab8c9d13d696a3e970937d58c83bb490edf357b/research/repository-convergence/2026-11-03/README.md',
617:'blob/f3447d5f86a40da75785b91486ceaa55ceab381b/docs/audits/signed-cache-python-patch-mismatch-2026-11-03.md;blob/89f72221ad6d4fcf3e13c0f42e62adceb7fcb091/validation/repin-requests/PR-617-signed-cache-python.json',
616:'blob/01632e92a975a8a51af9287cb9d86db93db6fcc7/commercial/far-demo/evaluation/semantic-live-smoke-20261103.md',
615:'blob/87315d1402205a2bf1c56fd880f49532ebb27860/research/model-architecture-search/CONVERGENCE-2026-11-03.md',
614:'blob/0d26eca3e2fde19c4b0613f80c4cd02d1986a0f9/research/investigation-engine/finding-ledger.md;actions/runs/42246514987/job/128001115478',
611:'blob/0e8364466db56ed3580a248827cedf1e8991f740/research/weight_space_programming/README.md',
608:'blob/6f59f8a539717940ac2a27cc26a8cc204eec7b1f/research/uncertain-routing/finding-ledger.md;pull/608#discussion_r4494361655;actions/runs/42246514987/job/128001115478',
607:'actions/runs/41727268815/job/126235238730;blob/e959c755bff26a6994df8ddc4ac05e272778a0c0/research/workflow-efficacy/LOCAL-QWEN-VALIDATION-V0.2.md',
606:'blob/dd00a19507a617ab6e067c25b845ac08106d6431/research/architecture-routing/finding-ledger.md',
601:'blob/a75d6b1fa2450645ef082854a810d731b4bb1262/docs/research/far-mech-convergence-20261103.md',
600:'blob/ee6219337074e58b8dda26fc09764caffb31e29a/docs/research/orthodox-forecast-factual-experiment-execution-v0.1.md',
599:'actions/runs/42246606754/job/127990361298',
597:'blob/3a72aea5e9cc1f089648d7820a8939fc8fedeed5/commercial/far-investigation-audit/REVIEW_LEDGER_597.md;actions/runs/42260642825;actions/runs/42260642826;actions/runs/42260642756;runs/128041678372;pull/597#issuecomment-6446273256;actions/runs/42414405376/job/128531430741;actions/runs/42260642756/job/128053754156;actions/runs/42260642826/job/128039365739',
490:''
}
counts={625:5,623:14,622:2,621:13,620:3,619:5,618:1,617:2,616:1,615:1,614:2,611:1,608:3,607:2,606:1,601:1,600:1,599:1,597:9,490:0}
by_pr={p['pr']:p for p in s['pull_requests']}
assert set(paths)==set(by_pr)==set(counts)
for n,txt in paths.items():
    a=txt.split(';') if txt else []
    assert len(a)==counts[n],(n,len(a),counts[n])
    assert len(a)==len(set(a)),n
    p=by_pr[n]
    refs=[]
    for part in a:
        kind=('git_blob' if part.startswith('blob/') else 'github_actions_run' if part.startswith('actions/runs/') else 'check_run' if part.startswith('runs/') else 'pr_or_issue_comment' if part.startswith(('pull/','issues/')) else 'commit')
        identity='unverified_or_historical'
        if kind=='git_blob':
            split=part.split('/',2)
            target_sha=split[1]
            if target_sha==p['live_head_sha']:identity='candidate_head'
            elif target_sha==p['evidence_reference']['historical_ref_commit']:identity='historical_commit_file_verified'
            else:identity='historical_commit_file_unverified'
        if n==625 and part=='actions/runs/42423770020':identity='live_head_bound_success_observed'
        refs.append({'url':root+part,'kind':kind,'identity_scope':identity,'verified_http_exists':kind=='git_blob' and identity=='historical_commit_file_verified',
                    'test_result_reused_for_live_head':identity=='live_head_bound_success_observed'})
    p['pr_body_github_urls']=refs

for p in s['pull_requests']:
    rv=p['reviews']
    sid=rv.get('summary_comment_id')
    rv['summary_url']=(f'https://github.com/n0tf0und0ut/Project-FAR/issues/{p["pr"]}#issuecomment-{sid}' if sid else None)
    if p['pr']==623:
        source={'PRRT_kwDOTH_vCM607BpC':'https://github.com/n0tf0und0ut/Project-FAR/pull/623#discussion_r4503846762',
                'PRRT_kwDOTH_vCM607BpE':'https://github.com/n0tf0und0ut/Project-FAR/pull/623#discussion_r4503846765'}
        for t in rv['unresolved_threads']:
            t['source_url']=source[t['thread_id']]
            t['source_comment_head_sha']=p['live_head_sha']
    if p['pr']==617:
        p['authorization_document']={'path':'validation/repin-requests/PR-617-signed-cache-python.json',
            'at_live_head_sha':p['live_head_sha'],
            'git_blob_sha':'9949fd00f3d1710f1fc92ddcda9f32bd83b38408',
            'target_pr':617, 'transition_path':'.github/workflows/validator-assurance.yml',
            'expires_at_utc':'2026-11-17T18:25:29Z',
            'signature_count_observed_valid':0,
            'url':'https://github.com/n0tf0und0ut/Project-FAR/blob/'+p['live_head_sha']+'/validation/repin-requests/PR-617-signed-cache-python.json'}

s['counts']['literal_pr_body_github_urls']=sum(len(p['pr_body_github_urls']) for p in s['pull_requests'])
s['limitations']=[x.replace('one principal verified evidence artifact, not exhaustive validation of every historical action-run URL or all hyperlinks in bodies.',
                   'one principal verified evidence artifact; all literal GitHub URLs in PR bodies are enumerated but historical run/job URLs are not individually independently re-fetched or cryptographically authenticated.') for x in s['limitations']]
P.write_text(json.dumps(s,sort_keys=True,ensure_ascii=False,indent=2)+'\n')
report=Path(__file__).resolve().parent / 'project_far_current_head_convergence.md'
with report.open('a') as f:
    f.write('\n## Exhaustive PR-body GitHub URL index\n\n')
    f.write('The machine-readable JSON carries every explicit `https://github.com/n0tf0und0ut/Project-FAR/…` URL extracted from the 20 PR descriptions in the collected REST responses. Historical run URLs are catalogued but not re-certified as current-head results.\n\n')
    f.write('| PR | Literal URL references | Current-head verified execution refs |\n|---|---:|---:|\n')
    for p in s['pull_requests']:
        refs=p['pr_body_github_urls'];f.write(f"| #{p['pr']} | {len(refs)} | {sum(z['test_result_reused_for_live_head'] for z in refs)} |\n")
    f.write('\nNo URL-count claim is made for inline PR numbers, comment IDs without URLs, or references stored only inside linked artifacts.\n')
print('enriched',s['counts']['literal_pr_body_github_urls'],'body URLs')
