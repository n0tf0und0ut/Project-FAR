"""Fail-closed prerequisite inventory for an actual native AtlasKV smoke evaluation.

Only a preflight: does not generate model answers, rewrite frozen inputs,
install packages, download checkpoints, or start a paid GPU.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import sys
import torch

UPSTREAM_SHA='61e3abc1fb09fbfb426cfc847c4c26c5e94bcaeb'
REQUIRED_PATHS=('atlas_repo','model_dir','encoder_file','llama_base','test_data',
                'leaf_keys','leaf_values','inter_keys','root_keys',
                'root_c2id','inter_c2id','root_id2c','inter_id2c')
REQUIRED_MODULES=('transformers','sentence_transformers','accelerate','evaluate')

def checked_git_sha(path):
    if not path or not Path(path).is_dir():return None
    try:
        result=subprocess.run(['git','-C',str(path),'rev-parse','HEAD'],
                              text=True,capture_output=True,timeout=5,check=True)
        return result.stdout.strip()
    except (OSError,subprocess.CalledProcessError,subprocess.TimeoutExpired):
        return None

def probe(paths):
    checks={key:dict(supplied=bool(paths.get(key)),exists=bool(paths.get(key)) and Path(paths[key]).exists())
            for key in REQUIRED_PATHS}
    modules={name:importlib.util.find_spec(name) is not None for name in REQUIRED_MODULES}
    actual_upstream_sha=checked_git_sha(paths.get('atlas_repo'))
    gpu=bool(torch.cuda.is_available())
    blockers=[f'missing_{name}' for name,value in checks.items() if not value['exists']]
    if not gpu:blockers.append('cuda_unavailable')
    blockers.extend(f'missing_python_module_{name}' for name,available in modules.items() if not available)
    if actual_upstream_sha!=UPSTREAM_SHA:blockers.append('upstream_git_sha_unverified_or_mismatch')
    # Presence of paths does NOT prove checkpoint identity, data semantics,
    # inference correctness, GPU capacity, or fair baseline equivalence.
    return {
        'schema':'atlas-kv-native-preflight/1.1',
        'scope':'prerequisite inventory only; no trained AtlasKV model inference or comparison',
        'upstream_repository':'HKUST-KnowComp/AtlasKV',
        'upstream_expected_git_sha':UPSTREAM_SHA,
        'upstream_observed_git_sha':actual_upstream_sha,
        'python':platform.python_version(),
        'torch':torch.__version__,
        'cuda_available':gpu,
        'gpu_count':torch.cuda.device_count() if gpu else 0,
        'gpu_names':[torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())] if gpu else [],
        'dependencies':modules,
        'paths':checks,
        'status':'PREREQUISITES_PRESENT_UNVERIFIED' if not blockers else 'BLOCKED',
        'blockers':blockers,
        'nonclaims':['checkpoint identity unverified','checkpoint-data compatibility unverified',
                     'GPU memory sufficiency unverified','training/model inference not executed'],
    }

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in REQUIRED_PATHS:parser.add_argument('--'+key.replace('_','-'))
    parser.add_argument('--output',default='native_preflight.json')
    args=parser.parse_args()
    result=probe(vars(args))
    Path(args.output).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if result['status']=='PREREQUISITES_PRESENT_UNVERIFIED' else 2

if __name__=='__main__':sys.exit(main())
