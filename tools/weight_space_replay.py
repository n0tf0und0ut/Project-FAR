"""Independent trace consistency/grading and conservative research decision.

Recomputes grades from raw output, fixed slots and source commitments. This is
not a second model inference run, external replication or authenticity proof.
"""
from __future__ import annotations
import json
import math
import random
import statistics
import re
import subprocess
from pathlib import Path
from tools.weight_space_pilot import (ROOT,canonical,sha,read,digest_file,load_protocol,
                                     schedule,source_receipt)


def independent_grade(task, text, tokens, hit):
    # Intentionally independent implementation of the host's small output contracts.
    try:
        if task['grader']=='json':
            pairs=[]
            def hook(items):
                keys=[k for k,_ in items]
                if len(keys)!=len(set(keys)):
                    raise ValueError('duplicate')
                return dict(items)
            got=json.loads(text.strip(), object_pairs_hook=hook,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))
            correct=canonical(got)==canonical(task['gold'])
        else:
            correct=text.strip()==task['gold']
    except (ValueError,TypeError):
        correct=False
    repeated=False
    for width in range(2,17):
        if len(tokens)>=3*width:
            repeated |= (tokens[-width:]==tokens[-2*width:-width] and
                         tokens[-width:]==tokens[-3*width:-2*width])
    return {'correct':bool(correct),'repeated_suffix':bool(repeated),
        'hit_token_limit':bool(hit),'empty_output':text.strip()=='',
        'contract_failure_category':None if correct else task['category']}


def summarize(p,tasks,rows):
    lookup={t['id']:t for t in tasks}
    result={}
    for arm in p['arms']:
        values=[r for r in rows if r['arm']==arm]
        def stats(sub):
            n=len(sub)
            return {'correct':sum(r['grade']['correct'] for r in sub),'total':n,
                    'accuracy':sum(r['grade']['correct'] for r in sub)/n if n else None}
        by_task={t['id']:[r for r in values if r['task_id']==t['id']]
                 for t in tasks if t['split']!='development'}
        result[arm]={**stats(values),
            'by_split':{s:stats([r for r in values if lookup[r['task_id']]['split']==s]) for s in ['heldout','regression']},
            'all_trials_correct_tasks':sum(all(r['grade']['correct'] for r in xs) for xs in by_task.values()),
            'total_tasks':len(by_task),'failure_frequency_by_category':{
                c:sum(not r['grade']['correct'] for r in values if lookup[r['task_id']]['category']==c)
                for c in sorted({t['category'] for t in tasks})},
            'repetition_proxy_count':sum(r['grade']['repeated_suffix'] for r in values),
            'token_limit_count':sum(r['hit_token_limit'] for r in values),
            'empty_count':sum(r['grade']['empty_output'] for r in values),
            'input_tokens':sum(r['input_tokens'] for r in values),
            'output_tokens':sum(r['output_tokens'] for r in values),
            'cpu_seconds':sum(r['cpu_seconds'] for r in values),
            'generation_seconds':sum(r['elapsed_seconds'] for r in values),
            'median_generation_seconds':statistics.median(r['elapsed_seconds'] for r in values)}
    # Bootstrap tasks, preserving all seeds. Diagnostic only for the authored fixed cohort.
    comparisons={}
    for arm in ['ablate','half_ablate']:
        for comparator in ['baseline','sham','random_ablate','prompt','decoding','budget']:
            diffs=[]
            for t in tasks:
                if t['split']!='heldout':
                    continue
                av=[r['grade']['correct'] for r in rows if r['task_id']==t['id'] and r['arm']==arm]
                bv=[r['grade']['correct'] for r in rows if r['task_id']==t['id'] and r['arm']==comparator]
                diffs.append(statistics.mean(av)-statistics.mean(bv))
            rng=random.Random(91813)
            bs=sorted(statistics.mean(rng.choices(diffs,k=len(diffs))) for _ in range(2000))
            comparisons[arm+' vs '+comparator]={'heldout_difference':statistics.mean(diffs),
                'task_bootstrap_diagnostic_95_interval':[bs[49],bs[1949]],
                'population_inference':False}
    simpler=['baseline','prompt','decoding','budget']
    best=max(simpler,key=lambda a:result[a]['by_split']['heldout']['accuracy'])
    # Preselected ablate is primary; half_ablate is an ablation, never selected post hoc.
    primary=comparisons['ablate vs '+best]
    regression_delta=(result['ablate']['by_split']['regression']['accuracy']-
                      result['baseline']['by_split']['regression']['accuracy'])
    return {'schema':'far-weight-analysis/0.1','status':'COMPLETE_BOUNDED_OUTPUT_PILOT',
        'observed_slots':len(rows),'arms':result,'comparisons':comparisons,
        'strongest_observed_simpler_baseline':best,
        'screen':{'minimum_gain_met':primary['heldout_difference']>=p['adoption']['min_gain'],
            'positive_task_bootstrap_lower_bound':primary['task_bootstrap_diagnostic_95_interval'][0]>0,
            'regression_tolerance_met':regression_delta>=-p['adoption']['max_regression'],
            'regression_difference':regression_delta},
        'causality_scope':'Within frozen prompts, seeds, runtime and specified parameter edit only; mechanism semantics not identified',
        'external_replication':'NOT_RUN','cross_model_transfer':'NOT_RUN',
        'production_eligible':False,'general_agent_reliability':'NOT_ESTABLISHED',
        'independence':'Trusted grader code, Project-FAR-authored tasks; no externally blinded oracle',
        'cost_scope':'Actual generation CPU/wall and token counts; excludes setup, weight audit and proposal selection; FLOPs not measured',
        'decision':'RESEARCH_ONLY; independent preregistered replication and strongest simpler-baseline superiority required'}


def validate_token_trace(row,tokenizer):
    request=row['request']
    expected=tokenizer.apply_chat_template(request['messages'], tokenize=True, add_generation_prompt=True)
    if expected!=request['input_ids']:
        raise ValueError('tokenized request differs from recorded input IDs')
    if tokenizer.decode(row['output_ids'],skip_special_tokens=True)!=row['text']:
        raise ValueError('decoded output differs from recorded text')
    ids=row['output_ids']
    hit=bool(ids) and len(ids)==request['generation']['max_new_tokens'] and ids[-1]!=tokenizer.eos_token_id
    if row['hit_token_limit'] is not hit:
        raise ValueError('token-limit flag mismatch')


def validate_edit_artifacts(p,output,model_dir):
    import numpy as np
    from safetensors import safe_open
    from tools.weight_space_edits import tensor_sha,apply_edit
    with np.load(output/'selection-inputs.npz',allow_pickle=False) as saved:
        original=saved['original']
        acts=saved['activations']
    with safe_open(str(model_dir/'model.safetensors'),framework='pt',device='cpu') as f:
        from_checkpoint=f.get_tensor(p['intervention']['tensor']).float().numpy()
    if tensor_sha(original)!=tensor_sha(from_checkpoint):
        raise ValueError('selection base differs from pinned checkpoint')
    if acts.shape!=(6,original.shape[1]) or not np.isfinite(acts).all():
        raise ValueError('activation evidence shape/nonfinite')
    scores=np.mean(np.square(acts.astype(np.float64)),axis=0)*np.sum(original.astype(np.float64)**2,axis=0)
    selected=int(np.argmax(scores))
    norms=np.linalg.norm(original.astype(np.float64),axis=0)
    candidates=[i for i in range(len(norms)) if i!=selected and abs(norms[i]/norms[selected]-1)<=0.10]
    random_column=int(np.random.default_rng(p['negative_control_seed']).choice(candidates))
    selection=read(output/'selection.json')
    if selection['selected_column']!=selected or selection['random_column']!=random_column or selection['scores']!=scores.tolist() or selection['activation_sha256']!=sha(acts.tobytes()):
        raise ValueError('selection mismatch')
    policy={'tensor':p['intervention']['tensor'],'shape':list(original.shape),'dtype':original.dtype.name,
        'max_changed_parameters':original.shape[0],'max_relative_l2':0.20,
        'allowed_operations':['identity','scale_columns'],'max_columns':1}
    audits={}
    for arm,factor,column in [('sham',None,None),('ablate',0.0,selected),('half_ablate',0.5,selected),('random_ablate',0.0,random_column)]:
        expected={'schema':'far-weight-edit/0.1','tensor':p['intervention']['tensor'],
            'base_tensor_sha256':tensor_sha(original),'operation':'identity' if factor is None else 'scale_columns'}
        if factor is not None:
            expected.update(columns=[column],factor=factor)
        proposal=read(output/('proposal-'+arm+'.json'))
        if proposal['proposal']!=expected or proposal['trusted_policy']!=policy:
            raise ValueError('proposal overrides frozen experiment or trusted policy')
        _,audit=apply_edit(original,expected,policy)
        if audit!=proposal['audit']:
            raise ValueError('actual tensor diff disagrees with saved audit')
        audits[arm]=audit
    return audits


def replay(protocol_path:Path,output:Path,model_dir:Path|None=None):
    p,tasks=load_protocol(protocol_path)
    registration=read(output/'registration.json')
    if registration['observations']!='LIVE_PRETRAINED_MODEL':
        raise ValueError('synthetic traces are not model observations')
    revision=registration.get('source_commit','')
    if not re.fullmatch(r'[0-9a-f]{40}',revision):
        raise ValueError('invalid frozen source commit')
    for name,digest in registration['source_files'].items():
        try:
            data=subprocess.check_output(['git','show',revision+':'+name],cwd=ROOT,stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as exc:
            raise ValueError('frozen source commit unavailable') from exc
        if sha(data)!=digest:
            raise ValueError('frozen source commit byte mismatch')
    if registration['protocol_sha256']!=digest_file(protocol_path):
        raise ValueError('protocol drift')
    if registration['source_files']!=source_receipt(p,protocol_path):
        raise ValueError('source drift: replay using exact frozen source commit')
    if registration['checkpoint_manifest_sha256']!=p['model']['manifest_sha256']:
        raise ValueError('checkpoint manifest drift')
    if model_dir is None:
        raise ValueError('pinned local checkpoint required for token and tensor replay')
    from tools.weight_space_pilot import verify_checkpoint
    manifest=read(ROOT/p['model']['manifest'])
    if sha(canonical(manifest))!=p['model']['manifest_sha256']:
        raise ValueError('model manifest mismatch')
    verify_checkpoint(model_dir,manifest)
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(model_dir,local_files_only=True,trust_remote_code=False)
    # Reconstruct the complete loaded float32 parameter inventory from pinned weights,
    # independently of the live model's self-reported named_parameters receipt.
    from safetensors import safe_open
    from tools.weight_space_edits import tensor_sha
    config=read(model_dir/'config.json')
    actual_base={}
    with safe_open(str(model_dir/'model.safetensors'),framework='pt',device='cpu') as f:
        for name in f.keys():
            arr=f.get_tensor(name).float().numpy()
            if name=='lm_head.weight' and config.get('tie_word_embeddings'):
                if not (arr==f.get_tensor('model.embed_tokens.weight').float().numpy()).all():
                    raise ValueError('unexpected unequal tied embeddings')
                continue
            actual_base[name]=(tensor_sha(arr) if arr.ndim==2 else
                sha(canonical({'dtype':'torch.float32','shape':list(arr.shape)})+arr.tobytes()))
    if actual_base!=registration['baseline_parameter_inventory']:
        raise ValueError('full baseline parameter inventory differs from pinned checkpoint')
    audits=validate_edit_artifacts(p,output,model_dir)
    development=[]
    for task in [t for t in tasks if t['split']=='development']:
        row=read(output/('development-'+task['id']+'.json'))
        validate_token_trace(row,tokenizer)
        if row['request']['messages']!=[{'role':'user','content':task['prompt']}] or row['request']['generation']!=p['generation'] or row['request']['seed']!=p['seeds'][0]:
            raise ValueError('development request drift')
        if row['request_sha256']!=sha(canonical(row['request'])) or row['text_sha256']!=sha(row['text'].encode()) or row['grade']!=independent_grade(task,row['text'],row['output_ids'],row['hit_token_limit']):
            raise ValueError('development evidence mismatch')
        development.append(row)
    expected=schedule(p,tasks)
    if len(list(output.glob('slot-*.json')))!=len(expected) or list(output.glob('failure-*.json')):
        raise ValueError('incomplete/failed experiment; no complete-performance report')
    completion=read(output/'completion.json')
    inventory=registration['baseline_parameter_inventory']
    if completion['completed_slots']!=len(expected) or completion['restored_parameter_inventory_sha256']!=sha(canonical(inventory)):
        raise ValueError('completion/restore mismatch')
    lookup={t['id']:t for t in tasks}
    rows=[]
    for i,slot in enumerate(expected):
        row=read(output/f'slot-{i:04d}.json')
        if (row['task_id'],row['seed'],row['arm'])!=slot or row['index']!=i:
            raise ValueError('slot identity drift')
        task=lookup[row['task_id']]
        validate_token_trace(row,tokenizer)
        request=row['request']
        prompt=task['prompt']+(p['prompt_suffix'] if row['arm']=='prompt' else '')
        generation=dict(p['generation'])
        if row['arm']=='budget': generation['max_new_tokens']=p['budget_tokens']
        if row['arm']=='decoding': generation['repetition_penalty']=p['repetition_penalty']
        if request['messages']!=[{'role':'user','content':prompt}] or request['generation']!=generation or request['seed']!=row['seed']:
            raise ValueError('request drift/oracle exposure')
        if row['request_sha256']!=sha(canonical(request)) or row['text_sha256']!=sha(row['text'].encode()):
            raise ValueError('raw trace hash mismatch')
        for field in ['input_ids']:
            if not request[field] or not all(type(x) is int and x>=0 for x in request[field]):
                raise ValueError('invalid input token IDs')
        if not all(type(x) is int and x>=0 for x in row['output_ids']):
            raise ValueError('invalid output token IDs')
        if row['input_tokens']!=len(request['input_ids']) or row['output_tokens']!=len(row['output_ids']):
            raise ValueError('token count mismatch')
        if row['output_tokens']>generation['max_new_tokens']:
            raise ValueError('token cap exceeded')
        for field in ['elapsed_seconds','cpu_seconds']:
            if type(row[field]) not in (int,float) or not math.isfinite(row[field]) or row[field]<0:
                raise ValueError('invalid cost metric')
        if row['grade']!=independent_grade(task,row['text'],row['output_ids'],row['hit_token_limit']):
            raise ValueError('grade mismatch')
        expected_inventory=dict(inventory)
        arm=row['arm']
        if arm in ['sham','ablate','half_ablate','random_ablate']:
            audit=audits[arm]
            if row['edit_audit_sha256']!=sha(canonical(audit)):
                raise ValueError('edit audit mismatch')
            expected_inventory[p['intervention']['tensor']]=audit['edited_tensor_sha256']
        elif row['edit_audit_sha256'] is not None:
            raise ValueError('unexpected edit on simpler baseline')
        if row['parameter_inventory_sha256']!=sha(canonical(expected_inventory)):
            raise ValueError('unexpected checkpoint change')
        rows.append(row)
    # Identity arm must reproduce baseline exactly at identical inputs/seeds.
    for task in [t for t in tasks if t['split']!='development']:
        for seed in p['seeds']:
            pair=[r for r in rows if r['task_id']==task['id'] and r['seed']==seed and r['arm'] in ('baseline','sham')]
            if pair[0]['output_ids']!=pair[1]['output_ids']:
                raise ValueError('identity sham differs from baseline')
    report=summarize(p,tasks,rows)
    loops=sum(r['grade']['repeated_suffix'] for r in development)
    report['development']={'total':len(development),'correct':sum(r['grade']['correct'] for r in development),
        'repetition_proxy_count':loops}
    report['WSP_HLOOP']={'testable':loops>=2,'status':'EXPLORATORY_PROXY_COMPARISON' if loops>=2 else 'NOT_TESTABLE; fewer than two development repetition-proxy failures'}
    report['token_and_actual_tensor_diff_replay']='PASSED'

    report['replay_scope']='raw hash/source/slot/grading consistency; self-reported computation receipt, not external authenticity proof'
    return report
