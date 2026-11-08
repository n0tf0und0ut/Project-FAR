#!/usr/bin/env python3
"""Build a provenance-labelled, fail-closed snapshot of GitHub observations.

Input observations were obtained via authenticated GitHub connector reads on
2026-11-07. No network fetch is asserted by this offline snapshot builder.
"""
import collections
import json
import pathlib
from datetime import datetime, timezone

OUT = pathlib.Path(__file__).resolve().parent
REPO = 'n0tf0und0ut/Project-FAR'
MAIN = 'eff47bc4fc9e272e87d71ecfc8d559cd1176753e'
OLD = 'c7456b469f9dfe88b92d0fc7a211e5c9ed64de61'
NEW = '8683ff11d36d6e0264e02aea71138a46bc0f40e3'

# Number, current head, abbreviated title, candidate SHA claimed in the PR body,
# native branch-protected checks (merge authority, repin, review convergence).
# A dash means the required check was absent from fetched check-runs, not waived.
ROWS = '''
625 fbb7a5be0bc1185d868a09cb51bfaddcb1b24cd7 fbb7a5be0bc1185d868a09cb51bfaddcb1b24cd7 pending success success
597 94603603fd6c863cf3895496af64cf2f003db480 ababafde8888b897cdf5312c0fd40385b974a6b3 pending success failure
490 495cc99f9c8a189968a9835a591550215726fa0d none missing success missing
617 4651fa065b1847901871d3903b9ebcdc57e787aa 89f72221ad6d4fcf3e13c0f42e62adceb7fcb091 failure failure success
621 03e19ac40424636c47e9370d1fb72f85d51246e9 22af7f59a5137caf337c25dbc35cb66a4c68db16 pending success failure
623 3a62632658a12938caac75f5d6921a7b9dadd425 87cec59af8f07b94737ddcb1c3b88dc0851141a4 success success failure
601 eb58ea4dcc5e5d590c55002d17e047d4cf74b907 a75d6b1fa2450645ef082854a810d731b4bb1262 pending success failure
599 7b5b6febf1f2b7725c2b4d2523ebab225c5ab223 5e521f93f29d3b9dcf84334a3c2ef4262e4683e0 success success failure
606 130c69035624c133954d96f5b6a5d063e2e82d97 dd00a19507a617ab6e067c25b845ac08106d6431 success success failure
600 a8079e4e6d4b3f5caccab969756c910ab3b91d5b ee6219337074e58b8dda26fc09764caffb31e29a success success failure
607 c934d21ff5e598403caa27e0c436f4e23737bfaf e959c755bff26a6994df8ddc4ac05e272778a0c0 success success failure
611 d217afa409fd58798b32d8d2afbf06151b40e6d7 0e8364466db56ed3580a248827cedf1e8991f740 success success failure
608 054a7e691cb83237eef308b9455855bbc102a67c 6f59f8a539717940ac2a27cc26a8cc204eec7b1f pending success failure
614 d91d86893c1be9a15eae6d63dc178bcfc8471a6f 0d26eca3e2fde19c4b0613f80c4cd02d1986a0f9 pending success failure
619 1f173c990c695ff5bd0244a9cc3015073a06a89f none success success failure
615 b360aab81ad14e0289d87f4acd67d84d20ae0116 87315d1402205a2bf1c56fd880f49532ebb27860 pending success failure
618 9f3bdd0a7dcf9890e87006cda2812a547c24e42e 8ab8c9d13d696a3e970937d58c83bb490edf357b success success failure
616 8261c05a85784b40de0e4d0148fd3920670ac25e 01632e92a975a8a51af9287cb9d86db93db6fcc7 success success failure
620 8f7af32b4d8f9c9557cbf2adba18d12568a4a865 8ca6d68fe202e3569f1ad90c1e10e546ff1508c9 success success failure
622 61d0493116184e48606ac1360746e5c99d5b49da 0762cfca954d50ec6d41de9c176c94eb0311026f success success failure
'''.strip()

TITLES = {
625:'Nontechnical onboarding and governed navigation',
597:'Bounded epistemic debugger and hostile source evaluation',
490:'Permanent noncanonical living-research inbox',
617:'Pinned Python patch for signed cache',
621:'Strict JSON in Decision Integrity',
623:'Checker behavior and cache provenance',
601:'FAR-MECH falsification and audit hardening',
599:'Live commercial retrieval comparison',
606:'Bounded architecture-routing pilot',
600:'Prospective forecasting and factual investigation',
607:'Local Qwen instruction-effect comparison',
611:'Weight-space intervention audit',
608:'Explicit verifier routing and uncertain selection',
614:'General investigation engine',
619:'Good-view JEPA retrieval pilot',
615:'Architecture search and negative experiments',
618:'Agent reliability exposure evidence',
616:'Model-directed semantic augmentation workspace',
620:'Numeric grounding and primary-gate failure',
622:'Synthetic agent fault/replay campaign'
}
# Current-head evidence file existence verified through GitHub's Contents API.
# Historical blob is separately read and compared where an historical SHA was supplied.
EVIDENCE = {
625:('docs/maintenance/beginner-comprehension-check.md','f77cf4b71c12b066649c1676230be456c65f555e',None,None),
597:('commercial/far-investigation-audit/REVIEW_LEDGER_597.md','43c8f8b082d0803daebe5daea524c90b877f7ee6','3a72aea5e9cc1f089648d7820a8939fc8fedeed5','3a63b9833c94f71af97e2a89ce5e61e16934d63b'),
490:('research/living/inbox/.rolling-pr-anchor.json','42203bd35466d59192bee95d884b391130b106fe',None,None),
617:('docs/audits/signed-cache-python-patch-mismatch-2026-11-03.md','066ffc3804bfbb3ab7e2df8a92e8a4bf0621450e','f3447d5f86a40da75785b91486ceaa55ceab381b','066ffc3804bfbb3ab7e2df8a92e8a4bf0621450e'),
621:('commercial/far-decision-integrity/PILOT_VALIDATION.md','686c45d674f0ead4bc07b8fd74a2a31f5fecd419',None,None),
623:('docs/architecture/validator-assurance-hardening.md','0f37b534060eb79fc87365584bcc197f50cf97c3',None,None),
601:('docs/research/far-mech-convergence-20261103.md','d128b4f209e6224050b76fc0885cfba46955b521','a75d6b1fa2450645ef082854a810d731b4bb1262','d128b4f209e6224050b76fc0885cfba46955b521'),
599:('commercial/far-investigation-audit/evaluation/live-001/README.md','3dbc5808db3689eb070f7dab081874300e2c3ae7',None,None),
606:('research/architecture-routing/finding-ledger.md','af87488c4c30f4f9ccf331796ad25cf20ad94106','dd00a19507a617ab6e067c25b845ac08106d6431','af87488c4c30f4f9ccf331796ad25cf20ad94106'),
600:('docs/research/orthodox-forecast-factual-experiment-execution-v0.1.md','7d5763e4c11eb20949b0f56323affe4cea80a1eb','ee6219337074e58b8dda26fc09764caffb31e29a','7d5763e4c11eb20949b0f56323affe4cea80a1eb'),
607:('research/workflow-efficacy/LOCAL-QWEN-VALIDATION-V0.2.md','defe7c8de9d7ee4ec8329e43d90615aab6f7b903','e959c755bff26a6994df8ddc4ac05e272778a0c0','defe7c8de9d7ee4ec8329e43d90615aab6f7b903'),
611:('research/weight_space_programming/README.md','487dc9dc00126c3b08708ee6c0f5786fa5849060','0e8364466db56ed3580a248827cedf1e8991f740','487dc9dc00126c3b08708ee6c0f5786fa5849060'),
608:('research/uncertain-routing/finding-ledger.md','061a3ea2fb5cb95dbbcd566694552c7e00b1cd5f','6f59f8a539717940ac2a27cc26a8cc204eec7b1f','061a3ea2fb5cb95dbbcd566694552c7e00b1cd5f'),
614:('research/investigation-engine/finding-ledger.md','c32448d272a59c3d51b3beee0dff40b3189d284f','0d26eca3e2fde19c4b0613f80c4cd02d1986a0f9','c32448d272a59c3d51b3beee0dff40b3189d284f'),
619:('research/good-view-jepa/README.md','0fabeca599665d07e92e0515a0c463bc7f3bd977',None,None),
615:('research/model-architecture-search/CONVERGENCE-2026-11-03.md','60df8b1910177fe52be7274890ef5a0c9b1f2fdd','87315d1402205a2bf1c56fd880f49532ebb27860','60df8b1910177fe52be7274890ef5a0c9b1f2fdd'),
618:('research/repository-convergence/2026-11-03/README.md','3f0a2e1f8ca9b88e0ee03556af1517a1d71f8e14','8ab8c9d13d696a3e970937d58c83bb490edf357b','3f0a2e1f8ca9b88e0ee03556af1517a1d71f8e14'),
616:('commercial/far-demo/evaluation/semantic-live-smoke-20261103.md','d28c31a84f8d04d00f17b55d12b49611b88fbb3b','01632e92a975a8a51af9287cb9d86db93db6fcc7','d28c31a84f8d04d00f17b55d12b49611b88fbb3b'),
620:('research/numeric-grounding/RESULTS-LIVE-V0.1.md','0a1cc10a540c187b71c1503d0fc1832b419c34b5','8ca6d68fe202e3569f1ad90c1e10e546ff1508c9','0a1cc10a540c187b71c1503d0fc1832b419c34b5'),
622:('research/tool-agent-reliability/FAULT-CAMPAIGN-V0.1.md','f9ff1227afe6a5499a3997ca0f12673e7a85ade5',None,None),
}
# Last observed official Codex bot state, separately bound to its reviewed SHA.
REVIEWS={
625:(6713872509,'fbb7a5be0bc1185d868a09cb51bfaddcb1b24cd7',False),
597:(6446273256,'ababafde8888b897cdf5312c0fd40385b974a6b3',False),
617:(6612214385,'89f72221ad6d4fcf3e13c0f42e62adceb7fcb091',False),
621:(6673150735,'22af7f59a5137caf337c25dbc35cb66a4c68db16',False),
623:(6713050709,'87cec59af8f07b94737ddcb1c3b88dc0851141a4',True),
601:(6535625808,'71cd19f348a659e43d03ce96d0640b87ac1a2135',False),
599:(6612212165,'abf71a30a5906cdd7270cb155d98f0df1cc4b522',False),
606:(6584455676,'cec9386fd6d511090250c12150ef314ffbf8a7ea',False),
600:(6504085083,'58ef77dac335cf2dc8da0062cbbb3c90c6038fa1',False),
607:(6589021842,'df3b55a70780562937303f5c855c3dba125e83fc',False),
611:(6612351467,'e48f6dc29302bb0848a5632b49c726d2128a327d',False),
608:(6589148775,'6f59f8a539717940ac2a27cc26a8cc204eec7b1f',False),
614:(6612894369,'0d26eca3e2fde19c4b0613f80c4cd02d1986a0f9',False),
619:(6687896846,'d888fc27ab248c4b8d32f8124d241b8de7e88ce6',False),
615:(6609504790,'db0c95f6568d873e4e4e96aab8c247af5a03d79b',False),
618:(6612631290,'354811a6f7d1732371c3730af28bc1bee996223a',False),
616:(6611963267,'a12f711d2f5130034eada4896a3d28c731a1fe76',False),
620:(6687892854,'769ab788275b4455619f228ee0d21a96edd78ce1',False),
622:(6686766151,'52ef171bcf0a7e43ddf6351242b873b012b5c0e3',False),
}
THREAD_COUNTS={625:0,597:15,490:0,617:0,621:8,623:5,601:13,599:1,606:6,600:3,607:3,611:3,608:8,614:24,619:2,615:2,618:1,616:8,620:5,622:0}
CHECK_IDS = {
    625:[128560572614,128563256456,128559957936],
    597:[128555020265,128563321361,128548508503],
    490:[None,128563324798,None],
    617:[128556427771,128563280294,128549019584],
    621:[128559878533,128563266793,128548869690],
    623:[128557127557,128563260409,128548759605],
    601:[128558679093,128563310086,128548456055],
    599:[128556979491,128563317762,128548438298],
    606:[128557424121,128563306138,128548427839],
    600:[128555071352,128563313939,128548413639],
    607:[128554066166,128563301906,128548327145],
    611:[128553922359,128563294819,128548313604],
    608:[128554207897,128563298284,128548296617],
    614:[128556774232,128563290898,128548278000],
    619:[128554651001,128563273608,128548197499],
    615:[128557578261,128563287695,128548179633],
    618:[128553881648,128563276731,128548168815],
    616:[128554625096,128563284124,128548155914],
    620:[128550365561,128563270302,128548056921],
    622:[128548999577,128563263699,128548035456],
}

CHECK_NAMES = ['merge-authority','protected-repin-gate','pr-review-convergence-observation']
APP_IDS = [15368,5073230,15368]

# Confirmed explicit dependencies, and potential integration collisions labelled separately.
DEPENDENCIES = {
597:[{'type':'ordered_integration','pr':625,'confidence':'explicit_PR_body','rule':'apply #625 first; then reconcile README and W4/W6 digest supplements and review the combined head'}],
614:[{'type':'predecessor_integration','pr':608,'confidence':'explicit_PR_body','rule':'integrate exact current #608 before successor #614'}],
608:[{'type':'conditional','pr':617,'confidence':'explicit_PR_body','rule':'protected-cache runtime repair needed only if signed-cache path blocks this candidate'}],
614:[{'type':'predecessor_integration','pr':608,'confidence':'explicit_PR_body','rule':'integrate #608 first'}, {'type':'conditional','pr':617,'confidence':'explicit_PR_body','rule':'repair signed-cache runtime if its protected checks block this branch'}]
}
INTEGRATION_RISKS={
597:[625,599],625:[597],599:[597],608:[614],614:[608],616:[621],621:[616],
606:[608,614],618:[606,608,614],620:[606,608,614]
}
UNRESOLVED={
623:[
 {'thread_id':'PRRT_kwDOTH_vCM607BpC','comment_id':'PRRC_kwDOTH_vCM8AAAABDHM_ag','file':'tools/check_governance_register_integrity.py','line':100,'outdated':False,'finding':'Shared leading condition discarded across coordinated status claims','invariant':'Condition scope must survive conjunction/coordinate parsing','state':'open'},
 {'thread_id':'PRRT_kwDOTH_vCM607BpE','comment_id':'PRRC_kwDOTH_vCM8AAAABDHM_bQ','file':'tools/check_governance_register_integrity.py','line':114,'outdated':False,'finding':'Markdown emphasis prevents recognition of table condition cells','invariant':'Condition cells must be normalized without enabling false acceptance','state':'open'}
]
}
BOUNDARIES={
625:'No uncoached external-reader comprehension pilot executed; do not claim usability validation.',
597:'Authored-case software verification is not independent causal or commercial effectiveness.',
490:'Living research ingestion cannot promote canonical scientific claims; never merge rolling anchor.',
617:'Owner signature absent for protected verifier/cache transition; preserve draft until governed authorization.',
621:'Old success evidence cannot attest newer strict parsing source; rerun exact head.',
623:'Two actionable semantic false-acceptance counterexamples remain open on current implementation.',
601:'Original bounded mechanistic findings do not establish general causal explanations or agent reliability.',
599:'Retrieval comparison is bounded; no independent customer-effectiveness inference.',
606:'Observed model routing 9/12 vs 12/12 deterministic and declarative controls; no routing advantage.',
600:'No worldview truth, forecasting advantage or factual decision benefit established.',
607:'Local Qwen study cannot substitute for general reliability; merged #605 remains 11/30 vs 10/30.',
611:'Weight-space capability is experimental, not demonstrated reliable self-improvement.',
608:'No adaptive routing benefit established; #614 depends on this implementation.',
614:'Frozen agent 0/8 vs deterministic/declarative 7/8; external ODR comparison blocked by missing authenticated adapter/source evidence.',
619:'Synthetic good-view result does not establish external image/text retrieval benefit.',
615:'Preserved negative architecture search does not show superiority or generalization.',
618:'Agent general reliability, causal uplift and customer economics unestablished.',
616:'One local model generated malformed output: FAR HTTP 502, not end-to-end semantic success.',
620:'Registered primary gate failed: wrong numeric releases 0 in both arms despite 12/16 vs 8/16 secondary correct numbers.',
622:'Synthetic fault-injection/forgery demonstration does not attest real model reliability or origin.'
}

prs=[]
for line in ROWS.splitlines():
    n_s, head, declared, m, p, r = line.split()
    n=int(n_s)
    is_inbox=n==490
    is_draft=n in (490,617)
    base=NEW if n in (490,621,623,625) else OLD
    path, live_blob, historical_commit, historical_blob=EVIDENCE[n]
    evidence={'path':path,'exact_head_blob_sha':live_blob,
              'exact_head_file_verified':True,
              'exact_head_url':f'https://github.com/{REPO}/blob/{head}/{path}',
              'historical_ref_commit':historical_commit,
              'historical_ref_blob_sha':historical_blob,
              'historical_ref_url':f'https://github.com/{REPO}/blob/{historical_commit}/{path}' if historical_commit else None,
              'historical_byte_identity': ('unchanged' if historical_blob==live_blob else 'changed') if historical_blob else 'not_compared'}
    check_states=[m,p,r]
    checks=[]
    for k,name in enumerate(CHECK_NAMES):
        state=check_states[k]
        job=CHECK_IDS[n][k]
        checks.append({'context':name,'required_app_id':APP_IDS[k],
                       'observed_status':'in_progress' if state=='pending' else ('not_observed' if state=='missing' else 'completed'),
                       'observed_conclusion':state if state in ('success','failure') else None,
                       'job_or_check_id':job,
                       'check_url': (f'https://github.com/{REPO}/runs/{job}' if name=='protected-repin-gate' and job else None),
                       'check_api_url':f'https://api.github.com/repos/{REPO}/check-runs/{job}' if job else None,
                       'current_head_bound':True if job else None})
    summ=REVIEWS.get(n)
    review={'source':'authenticated_GitHub_issue_comment_machine_summary',
            'summary_comment_id':summ[0] if summ else None,
            'reviewed_sha':summ[1] if summ else None,
            'has_unresolved_findings':summ[2] if summ else None,
            'completed':bool(summ),
            'exact_head_coverage':bool(summ and summ[1]==head),
            'human_approvals':0,'human_changes_requested':0,
            'total_threads':THREAD_COUNTS[n],
            'unresolved_threads':UNRESOLVED.get(n,[])}
    blockers=[]
    if is_inbox:
        blockers.append({'class':'intentional_governance','reason':'permanent draft and NEVER_MERGE_THIS_ANCHOR; snapshot promotion must use separate PR'})
    else:
        if is_draft: blockers.append({'class':'draft','reason':'draft PR not eligible for normal protected merge'})
        if declared=='none' or declared!=head:
            blockers.append({'class':'stale_candidate_identity','reason':'body does not pin actual live head SHA; previous claims cannot certify this head'})
        if not review['exact_head_coverage']:
            blockers.append({'class':'review_coverage','reason':'no authenticated completed clean Codex review on exact current SHA (or non-author human approval)'})
        if review['unresolved_threads']:
            blockers.append({'class':'substantive_findings','reason':f'{len(review["unresolved_threads"])} open current review threads'})
        for c in checks:
            if c['observed_conclusion']!='success':
                blockers.append({'class':'required_gate','reason':f'{c["context"]}: {c["observed_conclusion"] or c["observed_status"]}'})
        blockers.append({'class':'protected_merge_authorization','reason':'no user authorization to merge, auto-merge or modify protected main'})
        if n==617:
            blockers.append({'class':'owner_signature','reason':'zero valid owner signatures on protected transition request; dedicated App refuses authorization'})
        if n==614:
            blockers.append({'class':'external_experiment','reason':'registered ODR comparison still lacks original authenticated adapter/source and competitor evidence; separate from PR merge'})
        if n==625:
            blockers.append({'class':'empirical_claim','reason':'no actual uncoached human reader pilot; prohibits comprehension effectiveness claim, not the documentation PR itself'})
    prs.append({'pr':n,'url':f'https://github.com/{REPO}/pull/{n}', 'title':TITLES[n],
         'state':'open','draft':is_draft,'target_branch':'main','live_head_sha':head,
         'github_pr_base_sha_at_observation':base,
         'protected_main_sha_at_observation':MAIN,
         'base_is_current_main':base==MAIN,
         'body_declared_candidate_sha':None if declared=='none' else declared,
         'body_candidate_matches_live':declared==head,
         'evidence_reference':evidence,
         'reviews':review,'required_checks':checks,
         'dependencies':DEPENDENCIES.get(n,[]),
         'integration_risks_with_prs':INTEGRATION_RISKS.get(n,[]),
         'blockers':blockers, 'scientific_boundary':BOUNDARIES[n],
         'disposition':'KEEP_OPEN_DRAFT_NEVER_MERGE' if is_inbox else 'BLOCKED_NO_MERGE',
         'merge_authorized':False})

assert len(prs)==20 and len({p['pr'] for p in prs})==20
manifest={'schema':'far-pr-current-head-convergence-snapshot/1.0',
    'repo':REPO,'evidence_collected_date':'2026-11-07',
    'constructed_at_utc':datetime.now(timezone.utc).isoformat(),
    'snapshot_note':'Non-atomic sequential GitHub connector reads 2026-11-07 UTC, approximately 22:38–23:40. State may change between requests; no atomicity or head lease is claimed. Check conclusions are observations at retrieval time; rerun before acting.',
    'main':{'sha':MAIN,'protected':True,'source':'GitHub REST refs/heads/main and branches/main',
           'required_checks':[{'name':n,'app_id':a} for n,a in zip(CHECK_NAMES,APP_IDS)],
           'protection_endpoint':'403 Resource not accessible by integration; branch response supplied check source IDs',
           'rulesets_observed':[]},
    'governance':{'AGENTS.md_blob_sha':'7d2ddee5150ab907818e43f43d8c4398f7570f34',
        'pr-review-convergence.md_blob_sha':'b0a20b96e2f04634ad61fbdb5d71534a46771949',
        'authority_rule':'No merge without signed protected gates, exact-head independent review, finding closure, source-bound verification and authorization.'},
    'counts':{},'pull_requests':prs,'limitations':[
        'Snapshot builder consumes connector-derived observations; this file cannot auto-refresh. Companion verifier checks internal mechanical consistency, not live freshness.',
        'Every PR evidence object contains one principal verified evidence artifact, not exhaustive validation of every historical action-run URL or all hyperlinks in bodies.',
        'Exact-head check publication is not proof of scientific or software correctness; currently in-progress jobs may subsequently complete.',
        'GraphQL review threads and current Codex comment state were queried, but review-evidence collector behavior must be rerun on updated state before protected merge.',
        'Overlapping path sets indicate integration risk, not verified textual conflicts. Dependencies are explicitly confirmed where noted.',
        'The GitHub protection endpoint returned HTTP 403, but branch metadata supplied explicit required contexts and GitHub App IDs.',
        'No repository branches, PRs, signatures, protections, frozen data or protected main were mutated while collecting this snapshot.'
    ]}

states=collections.Counter(p['disposition'] for p in prs)
manifest['counts']={
'open_prs':20,
'ordinary_merge_candidates':19,
'perpetual_inbox':1,
'ordinary_candidate_bodies_not_pinning_live_sha':sum(not p['body_candidate_matches_live'] for p in prs if p['pr']!=490),
'current_head_automated_clean_review':sum(p['reviews']['exact_head_coverage'] and not p['reviews']['has_unresolved_findings'] for p in prs),
'review_convergence_failures':sum(c['observed_conclusion']=='failure' for p in prs for c in p['required_checks'] if c['context']=='pr-review-convergence-observation'),
'open_threads':sum(len(p['reviews']['unresolved_threads']) for p in prs),
'all_three_required_checks_green':sum(all(c['observed_conclusion']=='success' for c in p['required_checks']) for p in prs),
'blocked_ordinary_prs':sum(p['disposition']=='BLOCKED_NO_MERGE' for p in prs),
}
(OUT/'project_far_current_head_convergence.json').write_text(json.dumps(manifest,sort_keys=True,indent=2,ensure_ascii=False)+'\n')

lines=['# Project FAR — Open PR exact-head convergence manifest', '',
       '**Observed:** 2026-11-07 UTC; sequential GitHub connector reads, not an atomic transaction.',
       f'**Protected main SHA:** `{MAIN}`.',
       f'**Inventory:** 20 open PRs, 19 merge candidates and one perpetual draft inbox (#490).',
       '', '## Required gates', '',
       '| Context | Required source App ID |', '|---|---|']
for n,a in zip(CHECK_NAMES,APP_IDS):lines.append(f'| `{n}` | `{a}` |')
lines+=['','Notation: ✓ = completed success; ✕ = completed failure; … = in progress; — = no check observed. A green machine gate is not an independent code review or merge authorization.',
'','## All currently open PRs', '',
'| PR | Exact live head | Declared head | M / P / R | Unresolved threads | Disposition |',
'|---|---|---|---|---:|---|']
fmt={'success':'✓','failure':'✕','pending':'…','missing':'—'}
for p in prs:
    checks=[fmt[(c['observed_conclusion'] or ('pending' if c['observed_status']=='in_progress' else 'missing'))] for c in p['required_checks']]
    desc=p['body_declared_candidate_sha']
    declared=('match' if p['body_candidate_matches_live'] else ('absent' if not desc else f'stale `{desc[:10]}`'))
    line=f"| [#{p['pr']}]({p['url']}) | [`{p['live_head_sha'][:12]}`](https://github.com/{REPO}/commit/{p['live_head_sha']}) | {declared} | {' / '.join(checks)} | {len(p['reviews']['unresolved_threads'])} | {p['disposition']} |"
    lines.append(line)
lines+=['','## Findings and root causes', '',
'**#623 remains substantively blocked.** The two unresolved, current, non-outdated threads are:', '',
'- `PRRT_kwDOTH_vCM607BpC`, `tools/check_governance_register_integrity.py:100`: shared leading conditions incorrectly discarded across coordinated status claims.',
'- `PRRT_kwDOTH_vCM607BpE`, `tools/check_governance_register_integrity.py:114`: Markdown emphasis breaks condition-cell recognition.', '',
'All other PRs returned zero unresolved review threads in the queried GraphQL state. This only describes thread state, not correctness. No nonauthor human `APPROVED` review was observed.', '',
'**#617** remains draft and `BLOCKED_GOVERNANCE` by absent owner signatures for the protected repin request. Its merge-authority, App repin and exact-head assurance checks failed. Draft review success is not merge readiness.', '',
'**#625** has completed current-head Codex `completed/false/false` review, successful protected-repin and review-convergence gates; merge-authority and exact-head assurance remained in progress at the last check snapshot.', '',
'**#490** is the permanent research inbox. Its workflow intentionally keeps it draft and nonmergeable; snapshot/promotion PRs must exclude `.rolling-pr-anchor.json`.', '',
'## Dependency and integration ordering', '',
'`#608 → #614` is an explicit predecessor requirement: integrate #608 before #614. `#625 → #597` is documented ordering for conflicting README and W4/W6 living digests, not a requirement for #625 to wait for #597. The combined README requires recalculating both living digests and repeating tests and reviews. #617 is a conditional protected-cache-runtime prerequisite when its trusted path prevents other candidates from passing.', '',
'Additional overlaps needing integration tests include `#597 ↔ #599` (investigation audit), `#616 ↔ #621` (commercial demo), and shared living-promotion regression and scheduled-research test files across many branches. File-path overlap alone does not prove textual conflict.', '',
'## Exact evidence identity', '',
'Each row below is a Content API lookup at the **current live candidate SHA**. Historical linked evidence is separately read where available; matching blob SHA proves byte identity for that file only.', '',
'| PR | Verified evidence path | Current Git blob | Historical pointer identity |', '|---|---|---|---|']
for p in prs:
    e=p['evidence_reference']; lines.append(f"| #{p['pr']} | [`{e['path']}`]({e['exact_head_url']}) | `{e['exact_head_blob_sha'][:12]}` | {e['historical_byte_identity']} |")
lines+=['','For #597, the historical linked finding ledger had a **different** Git blob SHA from the current-head ledger. It must not be cited as an unchanged current-head verdict. Most other historically linked principal evidence files retained identical bytes, but do not certify the changed code.', '',
'## Authorization and claim boundaries', '',
'No PR was merge-authorized here; no branch-protection bypass, signature substitution, protected-main edit, merge or auto-merge was performed. The legal path is to fix current-head findings, stabilize integration, re-run all source-bound checks, obtain substantive independent current-head review, and apply owner authorization last.', '',
'**Scientific boundary:** #620 failed its preregistered primary numeric-release improvement gate (zero incorrect releases in each arm); #616 had a local model output rejected with HTTP 502; #614 retained agent 0/8 vs deterministic/declarative 7/8. These are negative or bounded observations, not improvements to general agent reliability.', '',
'## Audit method and limitations', '',
'GitHub sources: `GET /repos/n0tf0und0ut/Project-FAR/pulls?state=open&per_page=100`, individual PR metadata, `GET /git/ref/heads/main`, `GET /branches/main`, check-runs on each exact SHA, pull-request review submissions, GraphQL review-thread state, machine summaries from issue comments, changed-file inventories and evidence-file Contents lookups.', '',
'The collection was **sequential** and source state may move. Unfinished workflows may settle later. A stable manifest requires re-querying main, PR list and heads both before and after collection, rejecting a changed head or inventory. The accompanying validator detects internal contradictions but does not itself consult GitHub. Source check provenance was observed as App IDs 15368/5073230/15368; the dedicated full protection endpoint returned HTTP 403.', '',
'Every attached evidence path was verified at its stated current candidate; the manifest does **not** claim exhaustive verification of all linked job logs, archived ZIP contents, historical run URLs, reviewer output semantics, or direct scientific truth.']
(OUT/'project_far_current_head_convergence.md').write_text('\n'.join(lines)+'\n')
print('generated',len(prs),'prs',manifest['counts'])
