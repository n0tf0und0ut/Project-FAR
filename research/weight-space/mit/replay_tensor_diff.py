"""Fetch only immutable public tensor byte ranges and independently replay published sparse diffs. No inference."""
from pathlib import Path
import argparse,hashlib,json,struct,tempfile,urllib.request
import numpy as np
R=Path(__file__).resolve().parent
BASE='https://huggingface.co/Qwen/Qwen3.5-0.8B/resolve/2fc06364715b967f1860aea9cf38778875588b17/model.safetensors-00001-of-00001.safetensors'
def get_range(url,a,b):
 req=urllib.request.Request(url,headers={'Range':f'bytes={a}-{b}'})
 with urllib.request.urlopen(req,timeout=60) as x:
  if x.status!=206 or not x.headers.get('Content-Range','').startswith(f'bytes {a}-{b}/'):raise ValueError('HTTP source did not honor exact range')
  v=x.read(b-a+2)
  if len(v)!=b-a+1: raise ValueError('range length mismatch')
  return v
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir',type=Path,default=R/'lm_understand-logs')
    parser.add_argument('--output-dir',type=Path,help='New directory for reconstructed bytes; default verifies the published receipt without changing it')
    args=parser.parse_args()
    ROOT=args.source_dir/'exp8_math/runs/p50c/edit'
    temporary=tempfile.TemporaryDirectory(prefix='far-mit-tensors-') if args.output_dir is None else None
    OUT=Path(temporary.name) if temporary else args.output_dir
    if not temporary:OUT.mkdir(parents=True,exist_ok=False)
    n=struct.unpack('<Q',get_range(BASE,0,7))[0]
    raw=get_range(BASE,8,8+n-1);(OUT/'base-safetensors-header.json').write_bytes(raw)
    h=json.loads(raw); man=json.loads((ROOT/'manifest.json').read_text());npz=np.load(ROOT/'edit.npz',allow_pickle=False)
    counts={'full_checkpoint':sum(np.prod(x['shape']).item() for k,x in h.items() if k!='__metadata__'),'language_model_prefix':sum(np.prod(x['shape']).item() for k,x in h.items() if k.startswith('model.language_model.'))}
    rows=[]
    for i,t in enumerate(man['tensors']):
     x=h[t['name']];assert x['dtype']=='BF16' and x['shape']==t['shape']
     a,b=x['data_offsets'];original=get_range(BASE,8+n+a,8+n+b-1)
     assert hashlib.sha256(original).hexdigest()==t['base_sha256']
     bits=np.frombuffer(original,dtype='<u2').copy();idx=npz[f't{i}_idx'];val=npz[f't{i}_val']
     assert np.all(bits[idx]!=val)
     bits[idx]=val
     edited=bits.tobytes();assert hashlib.sha256(edited).hexdigest()==t['edited_sha256']
     prefix=f'layer{t["name"].split(".")[3]}'
     (OUT/f'{prefix}.base.bf16').write_bytes(original);(OUT/f'{prefix}.edited.bf16').write_bytes(edited)
     different=np.flatnonzero(np.frombuffer(original,dtype='<u2')!=bits)
     assert np.array_equal(different,idx)
     rows.append({'name':t['name'],'shape':x['shape'],'dtype':'BF16','base_sha256':hashlib.sha256(original).hexdigest(),'edited_sha256':hashlib.sha256(edited).hexdigest(),'changed_entries_actual':len(idx),'changed_columns_actual':len(np.unique(idx%t['shape'][1])),'all_other_entries_identical':True,'source_byte_range':[8+n+a,8+n+b-1]})
    result={'status':'Research','execution':'independent sparse diff replay on HTTP206 source tensor bytes; no neural inference','base_url':BASE,'base_revision':'2fc06364715b967f1860aea9cf38778875588b17','base_header_sha256':hashlib.sha256(raw).hexdigest(),'parameter_counts_from_header':counts,'touched_slots':131072,'changed_bf16_entries':130188,'changed_fraction_full_checkpoint':130188/counts['full_checkpoint'],'changed_fraction_language_model_prefix':130188/counts['language_model_prefix'],'tensors':rows,'unmodified_tensors':'Not downloaded; construction touches only these two. No comparison of the complete independently hosted edited checkpoint was executed.'}
    if temporary:
     assert result==json.loads((R/'tensor-replay/receipt.json').read_text()),'Published tensor receipt differs'
     temporary.cleanup()
    else:
     (OUT/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__ == "__main__":
    main()
