"""Research-only, frozen, local open-weight intervention/output reliability pilot.

No production imports, generated code execution, silent model substitution, or training.
The proposer sees development prompts/activations only. The evaluator owns grades,
policy, frozen schedule and checkpoint-byte audit. Internal separation is not external
independence or protection against a malicious host process.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'research/weight-space/protocol-v0.1.json'


def canonical(x):
    return json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(',', ':'),
                      allow_nan=False).encode()


def sha(x):
    return hashlib.sha256(x).hexdigest()


def read(path):
    def pairs(xs):
        out = {}
        for k, v in xs:
            if k in out:
                raise ValueError('duplicate JSON key')
            out[k] = v
        return out
    return json.loads(Path(path).read_bytes(), object_pairs_hook=pairs,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def write(path, value):
    # Evidence is immutable: an existing attempt directory must never be reused.
    path = Path(path)
    with path.open('xb') as f:
        f.write(canonical(value) + b'\n')


def digest_file(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        while block := f.read(1024*1024):
            h.update(block)
    return h.hexdigest()


def load_protocol(path):
    p = read(path)
    if p['schema'] != 'far-weight-pilot/0.1' or p['status'] != 'Research':
        raise ValueError('unregistered protocol')
    if p['model']['revision'] != '12fd25f77366fa6b3b4b768ec3050bf629380bac':
        raise ValueError('unregistered model revision')
    if p['model']['id'] != 'HuggingFaceTB/SmolLM2-135M-Instruct':
        raise ValueError('unregistered model')
    tasks_path = ROOT / p['tasks']['path']
    if digest_file(tasks_path) != p['tasks']['sha256']:
        raise ValueError('task drift')
    tasks = read(tasks_path)
    ids = [t['id'] for t in tasks]
    if len(ids) != len(set(ids)) or not all(t['split'] in ('development','heldout','regression') for t in tasks):
        raise ValueError('invalid task identity/split')
    for task in tasks:
        if set(task) != {'id','split','category','prompt','grader','gold'}:
            raise ValueError('task fields')
        if task['grader'] not in ('exact','json'):
            raise ValueError('grader')
    if p['arms'] != ['baseline','sham','ablate','half_ablate','random_ablate','prompt','decoding','budget']:
        raise ValueError('arm drift')
    return p, tasks


def schedule(p, tasks):
    # Seeded complete random permutation of eight arms within each task/seed block.
    rng = random.Random(p['schedule_seed'])
    slots = []
    for task in tasks:
        if task['split'] == 'development':
            continue
        for seed in p['seeds']:
            arms = list(p['arms'])
            rng.shuffle(arms)
            slots.extend((task['id'], seed, arm) for arm in arms)
    return slots


def verify_checkpoint(model_dir, manifest):
    for entry in manifest['files']:
        name = entry['name']
        if Path(name).name != name or name.startswith('.'):
            raise ValueError('checkpoint path')
        file = model_dir / name
        if file.is_symlink() or file.stat().st_size != entry['size'] or digest_file(file) != entry['sha256']:
            raise ValueError('checkpoint file mismatch: '+name)


def source_receipt(p, protocol_path):
    names = ['tools/weight_space_pilot.py','tools/weight_space_edits.py',
             'tools/weight_space_grading.py','tools/weight_space_replay.py',
             'research/weight-space/requirements.txt',p['tasks']['path'],
             str(Path(protocol_path).relative_to(ROOT)),p['model']['manifest']]
    return {name:digest_file(ROOT/name) for name in names}


def inventory(model):
    from tools.weight_space_edits import tensor_sha
    return {name:(tensor_sha(param.detach().cpu().numpy()) if param.ndim == 2 else
        sha(canonical({'dtype':str(param.dtype),'shape':list(param.shape)})+param.detach().cpu().numpy().tobytes()))
        for name,param in model.named_parameters()}


def verify_source_committed(source):
    for name,digest in source.items():
        try:
            data=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT,stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as exc:
            raise ValueError('experimental source is not committed: '+name) from exc
        if sha(data)!=digest:
            raise ValueError('experimental source differs from committed bytes: '+name)


def cpu_model():
    try:
        for line in Path('/proc/cpuinfo').read_text().splitlines():
            if line.startswith('model name'):
                return line.split(':',1)[1].strip()
    except OSError:
        pass
    return platform.processor()


def run(protocol_path,model_dir,output):
    if output.exists():
        raise ValueError('refusing to overwrite prior evidence')
    output.mkdir(parents=True)
    write(output/'attempt.json',{'started_utc':datetime.now(timezone.utc).isoformat(),
        'protocol_path':str(protocol_path),'protocol_sha256':digest_file(protocol_path)})
    try:
        return _run(protocol_path,model_dir,output)
    except Exception as exc:
        write(output/'failure-attempt.json',{'time_utc':datetime.now(timezone.utc).isoformat(),
            'error_type':type(exc).__name__,'error':str(exc),
            'status':'FAILED_ATTEMPT_PRESERVED; no complete performance claim'})
        raise


def _run(protocol_path, model_dir, output):
    from tools.weight_space_edits import apply_edit, tensor_sha
    from tools.weight_space_grading import grade
    import numpy as np
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    p,tasks = load_protocol(protocol_path)
    manifest = read(ROOT/p['model']['manifest'])
    if sha(canonical(manifest)) != p['model']['manifest_sha256']:
        raise ValueError('manifest drift')
    verify_checkpoint(model_dir, manifest)
    source = source_receipt(p, protocol_path)
    revision = subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    verify_source_committed(source)
    env = {name:importlib.metadata.version(name) for name in
           ['torch','transformers','huggingface_hub','safetensors','numpy','tokenizers']}
    expected = p['runtime']
    for key in env:
        if env[key].split('+')[0] != expected[key]:
            raise ValueError('runtime version mismatch: '+key)
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(p['seeds'][0])
    tokenizer = AutoTokenizer.from_pretrained(model_dir, local_files_only=True, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(model_dir, local_files_only=True,
        trust_remote_code=False, use_safetensors=True, torch_dtype=torch.float32,
        attn_implementation='eager').cpu().eval()
    base_inventory = inventory(model)
    params = dict(model.named_parameters())
    tensor_name = p['intervention']['tensor']
    target = params[tensor_name]
    original = target.detach().cpu().numpy().copy()
    write(output/'registration.json', {'schema':p['schema'],'time_utc':datetime.now(timezone.utc).isoformat(),
        'source_commit':revision,'source_files':source,'protocol_sha256':digest_file(protocol_path),
        'checkpoint_manifest_sha256':p['model']['manifest_sha256'],'environment':env,
        'machine':{'platform':platform.platform(),'processor':cpu_model(),
                   'threads':2,'dtype':'float32','attention':'eager','device':'cpu'},
        'baseline_parameter_inventory':base_inventory,'observations':'LIVE_PRETRAINED_MODEL',
        'external_independence':False,'general_reliability':'NOT_ESTABLISHED'})

    def generate(task, seed, arm):
        prompt = task['prompt'] + (p['prompt_suffix'] if arm == 'prompt' else '')
        messages = [{'role':'user','content':prompt}]
        ids = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True,
                                             return_tensors='pt')
        config = dict(p['generation'])
        if arm == 'budget':
            config['max_new_tokens'] = p['budget_tokens']
        if arm == 'decoding':
            config['repetition_penalty'] = p['repetition_penalty']
        torch.manual_seed(seed)
        start, cpu_start = time.perf_counter(), time.process_time()
        with torch.inference_mode():
            result = model.generate(ids, **config, pad_token_id=tokenizer.eos_token_id)
        elapsed, cpu = time.perf_counter()-start, time.process_time()-cpu_start
        tokens = result[0,ids.shape[-1]:].tolist()
        text = tokenizer.decode(tokens,skip_special_tokens=True)
        hit = len(tokens) == config['max_new_tokens'] and tokens[-1] != tokenizer.eos_token_id
        request = {'messages':messages,'input_ids':ids[0].tolist(),'seed':seed,'generation':config}
        return {'request':request,'request_sha256':sha(canonical(request)),
                'output_ids':tokens,'text':text,'text_sha256':sha(text.encode()),
                'grade':grade(task,text,tokens,hit),'input_tokens':ids.shape[-1],
                'output_tokens':len(tokens),'elapsed_seconds':elapsed,'cpu_seconds':cpu,
                'hit_token_limit':hit}

    # Proposer information boundary: only development inputs/activations, never evaluation tasks or golds.
    layer = model.get_submodule(tensor_name.rsplit('.',1)[0])
    activations=[]
    for task in [t for t in tasks if t['split']=='development']:
        row=generate(task,p['seeds'][0],'baseline')
        write(output/('development-'+task['id']+'.json'),row)
        ids=torch.tensor([row['request']['input_ids']])
        captured=[]
        def hook(_module,args):
            captured.append(args[0][0,-1,:].detach().cpu().numpy().copy())
        handle=layer.register_forward_pre_hook(hook)
        try:
            with torch.inference_mode():
                model(ids,use_cache=False)
        finally:
            handle.remove()
        if len(captured)!=1:
            raise ValueError('activation collection count')
        activations.append(captured[0])
    np.savez_compressed(output/'selection-inputs.npz',original=original,activations=np.stack(activations))
    scores=np.mean(np.square(np.stack(activations).astype(np.float64)),axis=0)*np.sum(original.astype(np.float64)**2,axis=0)
    selected=int(np.argmax(scores))
    norms=np.linalg.norm(original.astype(np.float64),axis=0)
    rng=np.random.default_rng(p['negative_control_seed'])
    candidates=[i for i in range(len(norms)) if i!=selected and abs(norms[i]/norms[selected]-1)<=0.10]
    if not candidates:
        raise ValueError('no norm-matched random negative control; stop without replacement search')
    random_column=int(rng.choice(candidates))
    policy={'tensor':tensor_name,'shape':list(original.shape),'dtype':original.dtype.name,
        'max_changed_parameters':original.shape[0],'max_relative_l2':0.20,
        'allowed_operations':['identity','scale_columns'],'max_columns':1}
    proposals={}
    for arm, factor, column in [('sham',None,None),('ablate',0.0,selected),
                               ('half_ablate',0.5,selected),('random_ablate',0.0,random_column)]:
        proposal={'schema':'far-weight-edit/0.1','tensor':tensor_name,
                  'base_tensor_sha256':tensor_sha(original),'operation':'identity' if factor is None else 'scale_columns'}
        if factor is not None:
            proposal.update(columns=[column],factor=factor)
        edited,audit=apply_edit(original,proposal,policy)
        proposals[arm]=(edited,audit)
        write(output/('proposal-'+arm+'.json'),{'proposal':proposal,'trusted_policy':policy,'audit':audit})
    write(output/'selection.json',{'selected_column':selected,'random_column':random_column,
        'selection':'development mean squared activation times output-column norm squared',
        'activation_sha256':sha(np.stack(activations).tobytes()),'scores':scores.tolist(),
        'negative_control_column_norm_ratio':float(norms[random_column]/norms[selected]),
        'no_evaluation_labels_supplied':True,'semantic_mechanism':'NOT_IDENTIFIED'})
    lookup={t['id']:t for t in tasks}
    for index,(task_id,seed,arm) in enumerate(schedule(p,tasks)):
        try:
            expected_inventory=dict(base_inventory)
            edited,audit=proposals.get(arm,(original,None))
            with torch.no_grad():
                target.copy_(torch.from_numpy(edited.copy()))
            expected_inventory[tensor_name]=tensor_sha(edited)
            observed=inventory(model)
            if observed!=expected_inventory:
                raise ValueError('unexpected checkpoint parameter differences')
            row=generate(lookup[task_id],seed,arm)
            row.update(index=index,task_id=task_id,seed=seed,arm=arm,
                       parameter_inventory_sha256=sha(canonical(observed)),
                       edit_audit_sha256=None if audit is None else sha(canonical(audit)))
            write(output/f'slot-{index:04d}.json',row)
            if index%24==0:
                print(json.dumps({'completed':index+1,'planned':len(schedule(p,tasks))}),flush=True)
        except Exception as exc:
            write(output/f'failure-{index:04d}.json',{'index':index,'task_id':task_id,'seed':seed,
                'arm':arm,'error_type':type(exc).__name__,'error':str(exc)})
            raise
        finally:
            with torch.no_grad():
                target.copy_(torch.from_numpy(original.copy()))
    if inventory(model)!=base_inventory:
        raise ValueError('restore mismatch')
    write(output/'completion.json',{'completed_slots':len(schedule(p,tasks)),
        'restored_parameter_inventory_sha256':sha(canonical(base_inventory)),
        'time_utc':datetime.now(timezone.utc).isoformat()})
    from tools.weight_space_replay import replay
    write(output/'analysis.json',replay(protocol_path,output,model_dir))


def fetch_checkpoint(protocol_path,model_dir):
    p,_=load_protocol(protocol_path)
    manifest=read(ROOT/p['model']['manifest'])
    if sha(canonical(manifest))!=p['model']['manifest_sha256']:
        raise ValueError('manifest drift')
    model_dir.mkdir(parents=True,exist_ok=True)
    for entry in manifest['files']:
        file=model_dir/entry['name']
        if file.exists():
            if file.is_symlink() or digest_file(file)!=entry['sha256']:
                raise ValueError('refusing to replace mismatched model file')
            continue
        url='https://huggingface.co/'+p['model']['id']+'/resolve/'+p['model']['revision']+'/'+entry['name']
        temporary=file.with_suffix(file.suffix+'.partial')
        with urllib.request.urlopen(url,timeout=120) as response,temporary.open('xb') as out:
            while block:=response.read(1024*1024):out.write(block)
        if temporary.stat().st_size!=entry['size'] or digest_file(temporary)!=entry['sha256']:
            raise ValueError('download digest mismatch; partial evidence retained')
        temporary.rename(file)
    verify_checkpoint(model_dir,manifest)
    print(json.dumps({'checkpoint_files_verified':len(manifest['files'])}))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='cmd',required=True)
    for name in ('validate','fetch','run','replay'):
        parser=sub.add_parser(name)
        parser.add_argument('--protocol',type=Path,default=DEFAULT)
        if name in ('run','replay'):
            parser.add_argument('--output',type=Path,required=True)
        if name!='validate':
            parser.add_argument('--model-dir',type=Path,required=True)
    a=ap.parse_args()
    if a.cmd=='validate':
        p,t=load_protocol(a.protocol)
        print(json.dumps({'status':'VALID_INFRASTRUCTURE_ONLY','slots':len(schedule(p,t))}))
    elif a.cmd=='fetch':
        fetch_checkpoint(a.protocol,a.model_dir)
    elif a.cmd=='run':
        run(a.protocol,a.model_dir,a.output)
    else:
        from tools.weight_space_replay import replay
        print(json.dumps(replay(a.protocol,a.output,a.model_dir),indent=2))

if __name__=='__main__':
    main()
