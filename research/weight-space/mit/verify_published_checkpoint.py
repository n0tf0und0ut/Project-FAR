"""Verify public checkpoint scores/two tensors without inference or evidence writes."""
from pathlib import Path
import argparse,json,urllib.request,hashlib,struct,tempfile
from replay_tensor_diff import get_range


def main():
    R=Path(__file__).resolve().parent
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,help='New directory for reconstruction; default compares the existing receipt read-only')
    args=parser.parse_args()
    temporary=tempfile.TemporaryDirectory(prefix='far-mit-published-') if args.output_dir is None else None
    out=Path(temporary.name) if temporary else args.output_dir
    if not temporary:out.mkdir(parents=True,exist_ok=False)
    rev='d1671a178705bcab7644806d23c535517f35723b'
    base=f'https://huggingface.co/RikiyaT/Qwen3.5-0.8B-weight-space-programming/resolve/{rev}/'
    res={'status':'Research','repo':'RikiyaT/Qwen3.5-0.8B-weight-space-programming','revision':rev,'new_inference_runs':0,'files':[]}
    scores={}
    for name in ['README.md','eval/scores_base_math500.json','eval/scores_edited_math500.json']:
        with urllib.request.urlopen(base+name,timeout=30) as x:data=x.read()
        (out/('published-'+name.replace('/','-'))).write_bytes(data)
        res['files'].append({'path':name,'sha256':hashlib.sha256(data).hexdigest(),'size':len(data),'url':base+name})
        if name.startswith('eval/'):
            scores['base' if '_base_' in name else 'edited']=json.loads(data)
    url=base+'model.safetensors-00001-of-00001.safetensors'
    n=struct.unpack('<Q',get_range(url,0,7))[0];raw=get_range(url,8,8+n-1);h=json.loads(raw)
    (out/'published-safetensors-header.json').write_bytes(raw)
    res['tensors']=[]
    for t in json.loads((R/'tensor-replay/receipt.json').read_text())['tensors']:
        v=h[t['name']];a,b=v['data_offsets'];data=get_range(url,8+n+a,8+n+b-1);got=hashlib.sha256(data).hexdigest()
        assert got==t['edited_sha256']
        res['tensors'].append({'name':t['name'],'published_sha256':got,'matches_rebuilt_evaluated_hash':True})
    res['score_arithmetic_recomputed']=[]
    for condition,d in scores.items():
        ps=d['per_problem'];ids=[p['id'] for p in ps]
        assert len(ids)==len(set(ids))==d['summary']['n_problems']
        labels=[v for p in ps for v in p['correct']]
        assert all(type(v) is int and v in (0,1) for v in labels)
        correct=sum(labels);total=len(labels)
        assert correct/total==d['summary']['acc']
        res['score_arithmetic_recomputed'].append({'condition':condition,'n_problems':len(ps),'total':total,'correct':correct,'accuracy':correct/total,'new_inference_runs':0})
    if temporary:
        assert res==json.loads((R/'published-checkpoint-receipt.json').read_text()),'Published checkpoint receipt differs'
        temporary.cleanup()
    else:
        (out/'published-checkpoint-receipt.json').write_text(json.dumps(res,indent=2)+'\n')
    print(json.dumps(res,indent=2))


if __name__=='__main__':
    main()
