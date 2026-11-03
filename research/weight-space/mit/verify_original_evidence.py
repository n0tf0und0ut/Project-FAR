"""Read-only audit of immutable author logs; no neural inference or author code execution."""
import hashlib,json,math,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
SRC=ROOT/'lm_understand-logs'
E=SRC/'exp8_math'
rows=[]; source_paths=set()
def read(p):
 source_paths.add(p)
 return json.loads(p.read_text())
for family,names in [(E/'eval',['unedited','p10c','p25c','p50c']),(E/'gemma_followup/eval',['unedited','g05b','g10b','g25b','g50b'])]:
 for name in names:
  dr=family/name
  merged=read(dr/'merged.json')
  for bench,m in merged.items():
   sums={k:0 for k in ['ok','total','cut','tokens_sum','n_problems']}; seen=set(); protos=[]; count_lenient=0
   for f in sorted((dr/'parts').glob('*/scores.json')):
    d=read(f)
    if bench not in d: continue
    v=d[bench]
    assert v['shard'] not in seen
    seen.add(v['shard']); protos.append(d.get('_protocol'))
    for k in sums: sums[k]+=v[k]
    count_lenient+=v.get('ok_lenient',0)
   assert sums['total']>0,(name,bench)
   assert math.isclose(m['acc'],sums['ok']/sums['total'],abs_tol=1e-14)
   assert math.isclose(m['cut_share'],sums['cut']/sums['total'],abs_tol=1e-14)
   assert math.isclose(m['mean_tokens'],sums['tokens_sum']/sums['total'],abs_tol=1e-8)
   assert m['problems']==sums['n_problems']
   if m.get('acc_lenient') is not None: assert math.isclose(m['acc_lenient'],count_lenient/sums['total'],abs_tol=1e-14)
   per=list((dr/'parts').glob(f'*/{bench}_per_problem.json'))
   ids=set(); per_ok=0; per_n=0
   for p in per:
    ps=read(p)
    for v in ps:
     assert v['id'] not in ids
     ids.add(v['id']); per_ok+=sum(v['correct']); per_n+=len(v['correct'])
   assert per_ok==sums['ok'] and per_n==sums['total'],(name,bench,per_ok,sums)
   rows.append({'family':'qwen' if family==E/'eval' else 'gemma','run':name,'benchmark':bench,**sums,'acc':m['acc'],'acc_lenient':m.get('acc_lenient'),'cut_share':m['cut_share'],'mean_tokens':m['mean_tokens'],'unique_problems':len(ids),'score_and_problem_recomputed':True,'protocol_variants':len({json.dumps(p,sort_keys=True) for p in protos})})
mp=E/'runs/p50c/edit/manifest.json'; man=read(mp)
zp=E/'runs/p50c/edit/edit.npz';source_paths.add(zp)
z=np.load(zp,allow_pickle=False)
fm=read(E/'runs/p50c/work_notes/frozen_weights_manifest.json')
weight=[]
for i,t in enumerate(man['tensors']):
 idx,val=z[f't{i}_idx'],z[f't{i}_val']; nr,nc=t['shape'];layer=t['name'].split('.')[3]
 assert len(idx)==t['changed_entries']==len(set(idx.tolist()))
 assert idx.min()>=0 and idx.max()<nr*nc and val.dtype==np.uint16
 cols=np.unique(idx%nc).tolist(); assert cols==fm[layer]['selected_neurons']
 assert len(cols)==t['changed_columns']==64
 weight.append({**t,'npz_changed_entries_verified':len(idx),'selected_columns_verified':cols})
assert sum(t['changed_entries'] for t in man['tensors'])==130188
for p in [E/'README.md',E/'gemma_followup/README.md',E/'code/evaluate.py',E/'code/profiles.py',E/'code/apply_edit.py',E/'code/st_numpy.py',E/'code/build_ckpt.py',E/'code/mathqa.py',E/'runs/p50c/tool_calls.jsonl',E/'runs/p50c/turns/t001/prompt.txt',E/'runs/p50c/work_notes/final_report.md',E/'runs/p50c/work_notes/submission_evidence.json',E/'runs/p50c/work_notes/frozen_edit_audit.json',E/'runs/p50c/work_notes/final_confirmation.csv']:
 source_paths.add(p)
for name in ['p10c','p25c','p50c']: source_paths.add(E/f'runs/{name}/state.json')
manifest={'status':'Research','audit_type':'independent arithmetic and immutable source-byte audit, not new inference','logs_repo':'https://github.com/RikiyaT/lm_understand-logs','logs_revision':'4d09ba6d6a7e891dd8063974dfe81b3d78e3494f','base_model':{'repo':'Qwen/Qwen3.5-0.8B','revision':'2fc06364715b967f1860aea9cf38778875588b17'},'rows':rows,'weight_diff':weight,'files':[{'path':str(p.relative_to(SRC)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size,'url':'https://github.com/RikiyaT/lm_understand-logs/blob/4d09ba6d6a7e891dd8063974dfe81b3d78e3494f/'+str(p.relative_to(SRC))} for p in sorted(source_paths)]}
(ROOT/'mit-source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'score_groups_recomputed':len(rows),'source_files_hashed':len(source_paths),'changed_bf16_entries':130188,'touched_slots':131072,'new_inference_runs':0,'math500_rows':[r for r in rows if r['benchmark']=='math500']},indent=2))
