#!/usr/bin/env python3
from collections import defaultdict
from fnmatch import fnmatchcase
from pathlib import Path
import yaml
from common_health import ROOT, iter_files, rel
errors=[]; registry_ids=defaultdict(list); proof_ids=defaultdict(list); adversarial_ids=defaultdict(list)
REGISTRY_NAMES=('registry','adversarial')
INTENTIONALLY_MALFORMED_YAML={
    'conformance/far-ir-1.0/invalid/malformed.yaml',
    'tests/fixtures/mechanization/parser/invalid/malformed.yaml',
}
EXTERNAL_RUNTIME_REFERENCE_FILES={
    'commercial/far-release-assurance/external-validation/swe-agent-v1.0.0-v1.0.1/agent-config.yaml',
    'commercial/far-release-assurance/external-validation/swe-agent-v1.0.0-v1.0.1-gemini-3.1-pro-preview-v2/agent-config.yaml',
}

def resolve_ref(p, v):
    cands=[(p.parent/v).resolve(), (ROOT/v).resolve()]
    return any(c.exists() for c in cands)

def is_dynamic_ref(v):
    return '${{' in v or '$(' in v

def resolves_coderabbit_review_glob(relative, location, key, value):
    """Only CodeRabbit path_instructions.path may name a source glob.

    Require a real file match so a typo remains a repository hygiene failure.
    All other YAML path references retain the exact-path validation.
    """
    if (relative != '.coderabbit.yaml' or key != 'path'
            or len(location) != 3 or location[:2] != ('reviews', 'path_instructions')
            or not isinstance(location[2], int)):
        return False
    if not any(char in value for char in '*?['):
        return False
    if Path(value).is_absolute() or '..' in Path(value).parts:
        return False
    return any(fnmatchcase(rel(candidate), value)
               for candidate in ROOT.rglob('*') if candidate.is_file())

for p in iter_files({'.yaml','.yml'}):
    relative=rel(p)
    try:
        data=yaml.safe_load(p.read_text(encoding='utf-8'))
    except Exception as e:
        if relative in INTENTIONALLY_MALFORMED_YAML:
            continue
        errors.append(f'{relative}: invalid YAML: {e}'); continue
    if isinstance(data, dict) and isinstance(data.get('id'), (str,int)):
        if 'proof-objects' in p.parts and p.name.startswith('T-'):
            proof_ids[str(data['id'])].append(p)
        elif any(n in p.name for n in REGISTRY_NAMES):
            registry_ids[str(data['id'])].append(p)
    is_workflow = p.parent == ROOT / '.github' / 'workflows'
    def walk(x, parent_key='', location=(), artifact_inputs=False):
        if isinstance(x, dict):
            uses = x.get('uses')
            action, separator, ref = uses.partition('@') if isinstance(uses, str) else ('', '', '')
            artifact_step = (
                is_workflow
                and len(location) == 4
                and location[0] == 'jobs'
                and location[2] == 'steps'
                and isinstance(location[3], int)
                and action in {'actions/upload-artifact', 'actions/download-artifact'}
                and bool(separator and ref)
                and not any(c.isspace() for c in ref)
                and not is_dynamic_ref(ref)
            )
            if any(n in p.name for n in REGISTRY_NAMES) and isinstance(x.get('id'), (str,int)):
                registry_ids[str(x['id'])].append(p)
            for k,v in x.items():
                kl=str(k).lower()
                if (
                    relative not in EXTERNAL_RUNTIME_REFERENCE_FILES
                    # Artifact paths name runtime upload inputs/download outputs,
                    # not files required to exist in the source checkout. Other
                    # action inputs and all non-workflow references still check.
                    and not (artifact_inputs and k == 'path')
                    and isinstance(v,str)
                    and (kl.endswith('path') or kl.endswith('file') or kl in {'path','file','fixture','report','source'})
                    and not is_dynamic_ref(v)
                    and not v.startswith(('http://','https://'))
                    and ('/' in v or '.' in v)
                    and not resolve_ref(p, v)
                    and not resolves_coderabbit_review_glob(relative, location, kl, v)
                ):
                    errors.append(f'{relative}: referenced path missing: {v}')
                walk(v, kl, location + (k,), artifact_step and k == 'with')
        elif isinstance(x, list):
            for index, v in enumerate(x):
                walk(v, parent_key, location + (index,))
    walk(data)
# Unique top-level proof-object ids.
for idv,paths in proof_ids.items():
    if len(paths)>1: errors.append(f'duplicate proof object id {idv}: '+', '.join(sorted({rel(p) for p in paths})))
# Unique adversarial case ids within adversarial suite files.
for p in iter_files({'.yaml','.yml'}):
    if 'adversarial' not in p.name: continue
    try: data=yaml.safe_load(p.read_text(encoding='utf-8'))
    except Exception: continue
    local=defaultdict(int)
    def ids(x):
        if isinstance(x, dict):
            if isinstance(x.get('id'), (str,int)): local[str(x['id'])]+=1
            for v in x.values(): ids(v)
        elif isinstance(x, list):
            for v in x: ids(v)
    ids(data)
    for idv,count in local.items():
        if count>1: errors.append(f'{rel(p)}: duplicate adversarial suite id {idv}')
for e in errors: print('FAIL', e)
if errors: raise SystemExit(1)
print('Repository hygiene OK')
