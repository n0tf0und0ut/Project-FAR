"""Fail-closed prereq audit for an actual upstream AtlasKV model evaluation.

Only a preflight: never generates model answers, rewrites frozen inputs,
installs packages, downloads checkpoints, or starts a paid GPU.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import torch

UPSTREAM_SHA='61e3abc1fb09fbfb426cfc847c4c26c5e94bcaeb'
CHECKPOINTS=('model_dir','encoder_file','llama_base','test_data','leaf_keys','leaf_values',
             'inter_keys','root_keys','root_c2id','inter_c2id','root_id2c','inter_id2c')

def probe(paths):
    checks={key:dict(supplied=bool(paths.get(key)),exists=bool(paths.get(key)) and Path(paths[key]).exists())
            for key in CHECKPOINTS}
    gpu=bool(torch.cuda.is_available())
    result={
        'schema':'atlas-kv-native-preflight/1.0',
        'scope':'preflight only; no AtlasKV trained inference or comparison',
        'upstream_repository':'HKUST-KnowComp/AtlasKV',
        'upstream_expected_git_sha':UPSTREAM_SHA,
        'python':platform.python_version(),
        'torch':torch.__version__,
        'cuda_available':gpu,
        'gpu_count':torch.cuda.device_count() if gpu else 0,
        'gpu_names':[torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())] if gpu else [],
        'dependencies':{key:__import__('importlib').util.find_spec(key) is not None
                        for key in ('transformers','sentence_transformers','accelerate','evaluate')},
        'paths':checks,
        'status':'READY_FOR_NATIVE_UPSTREAM_SMOKE' if gpu and all(v['exists'] for v in checks.values()) else 'BLOCKED',
    }
    result['blockers']=([f'missing_{name}' for name,value in checks.items() if not value['exists']] +
                        ([] if gpu else ['cuda_unavailable']) +
                        [f'missing_python_module_{x}' for x,v in result['dependencies'].items() if not v])
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in CHECKPOINTS:parser.add_argument('--'+key.replace('_','-'))
    parser.add_argument('--output',default='native_preflight.json')
    args=parser.parse_args()
    payload=probe(vars(args))
    Path(args.output).write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n')
    print(json.dumps(payload,indent=2,sort_keys=True))
    return 0 if payload['status']=='READY_FOR_NATIVE_UPSTREAM_SMOKE' else 2

if __name__=='__main__':sys.exit(main())
