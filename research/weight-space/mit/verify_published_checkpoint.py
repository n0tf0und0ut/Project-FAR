"""Fetch public checkpoint metadata/scores and compare two edited tensors, without inference."""
from pathlib import Path
import json,urllib.request,hashlib,struct
from replay_tensor_diff import get_range
R=Path(__file__).resolve().parent
rev='d1671a178705bcab7644806d23c535517f35723b'
base=f'https://huggingface.co/RikiyaT/Qwen3.5-0.8B-weight-space-programming/resolve/{rev}/'
res={'status':'Research','repo':'RikiyaT/Qwen3.5-0.8B-weight-space-programming','revision':rev,'new_inference_runs':0,'files':[]}
for name in ['README.md','eval/scores_base_math500.json','eval/scores_edited_math500.json']:
 with urllib.request.urlopen(base+name,timeout=30) as x:data=x.read()
 (R/('published-'+name.replace('/','-'))).write_bytes(data)
 res['files'].append({'path':name,'sha256':hashlib.sha256(data).hexdigest(),'size':len(data),'url':base+name})
url=base+'model.safetensors-00001-of-00001.safetensors'
n=struct.unpack('<Q',get_range(url,0,7))[0];raw=get_range(url,8,8+n-1);h=json.loads(raw)
(R/'tensor-replay/published-safetensors-header.json').write_bytes(raw)
res['tensors']=[]
for t in json.load(open(R/'tensor-replay/receipt.json'))['tensors']:
 v=h[t['name']];a,b=v['data_offsets'];data=get_range(url,8+n+a,8+n+b-1);got=hashlib.sha256(data).hexdigest()
 assert got==t['edited_sha256']
 res['tensors'].append({'name':t['name'],'published_sha256':got,'matches_rebuilt_evaluated_hash':True})
(R/'published-checkpoint-receipt.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res,indent=2))
