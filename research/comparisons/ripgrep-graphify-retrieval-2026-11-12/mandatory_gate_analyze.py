#!/usr/bin/env python3
"""Score preregistered 24x3 Graphify adoption-gate receipts after all runs are frozen."""
from __future__ import annotations
import collections,hashlib,json,pathlib,random,statistics
D=pathlib.Path(__file__).resolve().parent
P=json.loads((D/'mandatory_gate_protocol.json').read_text())
M=json.loads((D/'mandatory_gate_execution_manifest.json').read_text())
GOLD=json.loads((D/'mandatory_gate_oracle.json').read_text())
assert M['protocol_sha256']==hashlib.sha256((D/'mandatory_gate_protocol.json').read_bytes()).hexdigest()
assert M['oracle_sha256']==hashlib.sha256((D/'mandatory_gate_oracle.json').read_bytes()).hexdigest()
assert M['runner_sha256']==hashlib.sha256((D/'mandatory_gate_run.py').read_bytes()).hexdigest()
assert set(GOLD)=={t['function'] for t in P['tasks']}
raw=D/'mandatory_gate_raw.jsonl'
receipts=[json.loads(line) for line in raw.read_text().splitlines() if line.strip()]
assert len(receipts)==72, ('count',len(receipts))
assert len({(r['task_id'],r['arm']) for r in receipts})==72
arms=list(P['arms'])
by={(r['function'],r['arm']):r for r in receipts}
results=[]
for t in P['tasks']:
 name=t['function'];gold=set(GOLD[name])
 for arm in arms:
  r=by[name,arm]
  pred=set(r['selected_files'])
  tp=len(pred&gold);fp=len(pred-gold);fn=len(gold-pred)
  pr=r['patch_result']
  exact=(not r.get('error') and not r.get('invalid_action') and
         r['final_action']=='apply_patch' and
         pr is not None and pr['syntax_valid'] and
         pred==gold and pr['files_requested']==sorted(pred) and
         t['definition_file'] in pr['edit_files'])
  if pr and pr['syntax_valid']:
   eligible_edits=set(gold)|{t['definition_file']}
   if any(x not in eligible_edits for x in pr['edit_files']):raise RuntimeError('edited unallowed file')
   if any(x not in set(r['selected_files'])|{t['definition_file']} for x in pr['edit_files']):raise RuntimeError('patched unrequested file')
  results.append({'task_id':t['task_id'],'function':name,'gold_files':len(gold),'arm':arm,
    'selected_files':sorted(pred),'missing':sorted(gold-pred),'extra':sorted(pred-gold),
    'tp':tp,'fp':fp,'fn':fn,'f1':2*tp/(2*tp+fp+fn) if (tp or fp or fn) else 1,
    'exact_synthetic_patch':bool(exact),'code_compiles':bool(pr and pr['syntax_valid']),
    'files_actually_modified':len(pr['edit_files']) if pr else 0,
    'model_total_tokens':r['model_total_tokens'],
    'graphify_requested':r['second_stage_graph_requested'],
    'n_model_calls':len(r['model_calls']),
    'model_seconds':sum(x['wall_seconds'] for x in r['model_calls']),
    'reported_error':r.get('error') or r.get('invalid_action'),
    'rg_lookup_seconds':r['tool_initial_retrieval_seconds'],
    'graph_lookup_seconds':r['graph_lookup_seconds'] if arm=='mandatory_graph_hook' or r['second_stage_graph_requested'] else 0})
summary={}
for arm in arms:
 rs=[r for r in results if r['arm']==arm];tp=sum(x['tp'] for x in rs);fp=sum(x['fp'] for x in rs);fn=sum(x['fn'] for x in rs)
 summary[arm]={
   'runs':len(rs),'exact':sum(x['exact_synthetic_patch'] for x in rs),
   'micro_precision':round(tp/(tp+fp),4) if tp+fp else 0,
   'micro_recall':round(tp/(tp+fn),4) if tp+fn else 0,
   'micro_f1':round(2*tp/(2*tp+fp+fn),4) if tp or fp or fn else 1,
   'tp':tp,'fp':fp,'fn':fn,
   'total_model_tokens':sum(x['model_total_tokens'] for x in rs),
   'mean_model_tokens':round(statistics.mean(x['model_total_tokens'] for x in rs),2),
   'total_model_seconds':round(sum(x['model_seconds'] for x in rs),3),
   'total_rg_lookup_seconds':round(sum(x['rg_lookup_seconds'] for x in rs),3),
   'total_graph_lookup_seconds':round(sum(x['graph_lookup_seconds'] for x in rs),3),
   'graph_requests':sum(x['graphify_requested'] for x in rs),
   'model_calls':sum(x['n_model_calls'] for x in rs),
   'invalid_actions':[x['function'] for x in rs if x['reported_error']],
   'syntax_failures':[x['function'] for x in rs if not x['code_compiles']],
   'cases_failed':[x['function'] for x in rs if not x['exact_synthetic_patch']]
 }
rnd=random.Random(662)
paired={}
for b in ['rg_only','optional_graph']:
 diffs=[]
 for t in P['tasks']:
  name=t['function']
  x=next(x for x in results if x['function']==name and x['arm']=='mandatory_graph_hook')
  y=next(x for x in results if x['function']==name and x['arm']==b)
  diffs.append(int(x['exact_synthetic_patch'])-int(y['exact_synthetic_patch']))
 boots=sorted(sum(diffs[rnd.randrange(24)] for _ in range(24))/24 for _ in range(10000))
 paired['mandatory_minus_'+b]={
   'wins':sum(x>0 for x in diffs),'ties':sum(x==0 for x in diffs),'losses':sum(x<0 for x in diffs),
   'mean_exact_difference':round(statistics.mean(diffs),4),
   'bootstrap_95_interval':[round(boots[249],4),round(boots[9749],4)]}
indexing=json.loads((D/'graphify_initial_extraction.json').read_text())
repeat=json.loads((D/'graphify_repeat_extraction.json').read_text())
# Even with one build amortized over 72 work items, this adds >1s/task.
cost={}
for arm in arms:
 s=summary[arm];total=s['total_model_seconds']+s['total_rg_lookup_seconds']+s['total_graph_lookup_seconds']
 cost[arm]={'observed_calls_only_seconds':round(total,3),
            'total_seconds_with_one_cold_graph_build':round(total+indexing['wall_seconds'],3) if arm=='mandatory_graph_hook' else None,
            'total_seconds_with_one_warm_index_refresh':round(total+repeat['wall_seconds'],3) if arm=='mandatory_graph_hook' else None}
mand=summary['mandatory_graph_hook']
passes={}
passes['at_least_three_net_extra_exact_over_each']=(mand['exact']-summary['rg_only']['exact']>=3 and mand['exact']-summary['optional_graph']['exact']>=3)
passes['no_new_mandatory_failures']=all(
 next(x for x in results if x['function']==t['function'] and x['arm']=='mandatory_graph_hook')['exact_synthetic_patch'] or
 not (next(x for x in results if x['function']==t['function'] and x['arm']=='rg_only')['exact_synthetic_patch'] or
      next(x for x in results if x['function']==t['function'] and x['arm']=='optional_graph')['exact_synthetic_patch'])
 for t in P['tasks'])
passes['zero_extra_planned_or_syntax_failures']=(mand['fp']==0 and not mand['syntax_failures'] and not mand['invalid_actions'])
passes['model_tokens_within_5pct_both']=(mand['total_model_tokens']<=1.05*summary['rg_only']['total_model_tokens'] and mand['total_model_tokens']<=1.05*summary['optional_graph']['total_model_tokens'])
passes['wall_time_within_5pct_both_including_one_cold_graph_build']=(cost['mandatory_graph_hook']['total_seconds_with_one_cold_graph_build']<=1.05*cost['rg_only']['observed_calls_only_seconds'] and cost['mandatory_graph_hook']['total_seconds_with_one_cold_graph_build']<=1.05*cost['optional_graph']['observed_calls_only_seconds'])
passes['bootstrap_lower_bound_positive_both']=all(v['bootstrap_95_interval'][0]>0 for v in paired.values())
passes['fail_open_and_stale_index_verified']=False # deliberately NOT tested
passes['all_14_specialists_live_integration_verified']=False # deliberately NOT tested
passes['non_python_and_frozen_evidence_coverage_verified']=False # deliberately NOT tested
decision='NO: keep Graphify optional; do not add mandatory agent hooks, required integration or startup hooks' if not all(passes.values()) else 'ELIGIBLE_FOR_FURTHER_GOVERNED_ACCEPTANCE'
output={'schema':'far-pr662-mandatory-graphify-adoption-analysis/v0.1',
 'status':'Research; not independently replicated or authorized production change',
 'source_sha':P['source_sha'],'protocol_sha256':M['protocol_sha256'],'runner_sha256':M['runner_sha256'],
 'model_sha256':M['model_sha256'],
 'task_count':len(P['tasks']),'model_run_count':len(receipts),
 'metrics':summary,'paired':paired,'costs':cost,'graph_initial_seconds':indexing['wall_seconds'],
 'graph_repeat_seconds':repeat['wall_seconds'],
 'gate_passes':passes,'verdict':decision,
 'scored_runs':results,
 'scope_limitations':['Synthetic AST terminal-identifier rename; model chooses paths, deterministic tool performs edits. No real semantic refactor, imports, or end-to-end agent code authoring.','No installed hooks were exercised; mandatory condition simulates auto-injected Graphify context.','All three arms share one model and source. No independent replicate or broader language coverage.','Graph index frozen before edits, not refreshed from mutated worktree; no stale-index fail-open demonstration.','Cost timings are one observed run per condition; no GPU, provider or 14-role hardware extrapolation.','All failures preserved; the no-adoption verdict is a current deployment decision, not an assertion that Graphify can never be useful.']}
(D/'mandatory_gate_analysis.json').write_text(json.dumps(output,indent=2,sort_keys=True)+'\n')
print(json.dumps({'summary':summary,'paired':paired,'costs':cost,'gate_passes':passes,'verdict':decision},indent=2))
