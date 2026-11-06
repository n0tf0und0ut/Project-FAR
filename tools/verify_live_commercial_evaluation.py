#!/usr/bin/env python3
"""Verify recorded live-001 bytes and recompute its disclosed retrieval metrics."""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

from run_live_commercial_evaluation import ROOT, DATA, BASE, digest, read, score_retrieval

# Identity anchors for this recorded campaign, not provider authenticity or an
# independent seal. A supplied copy cannot replace its own verification policy.
MANIFEST_SHA256 = {
    'artifact-manifest-v1.json': '22d57fede58b5235150f5bb73b98605404a66cea5f3f092c76e0f05b741a192b',
    'artifact-manifest-v2.json': '7199defbbb2a240af9a851712aac3adea2fa752ace9b51decf4031e138df2526',
}


def frozen_runtime(data):
    """Resolve the recorded source inventory, independently of later source additions.

    Prefer matching checkout bytes. If implementation evolved, recover the exact
    recorded blob from the registered Git baseline and verify its SHA-256 before
    execution. Missing history is an explicit failure, never a current-code fallback.
    """
    record = read(data / 'registration-v1.json')
    if record['base_commit'] != BASE:
        raise ValueError('registered baseline changed')
    campaign = DATA.relative_to(ROOT)
    runtime = Path('commercial/far-investigation-audit')
    sources = {}
    for rel, expected in record['files'].items():
        path = Path(rel)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('unsafe registered source path')
        current = data / path.relative_to(campaign) if path.is_relative_to(campaign) else ROOT / path
        try:
            raw = current.read_bytes()
        except OSError:
            raw = b''
        if digest(raw) != expected:
            recovered = subprocess.run(['git', 'show', BASE + ':' + rel], cwd=ROOT,
                                       capture_output=True, timeout=30)
            if recovered.returncode or digest(recovered.stdout) != expected:
                raise ValueError('frozen source unavailable or mismatched: ' + rel)
            raw = recovered.stdout
        if path.parent == runtime and path.suffix == '.py':
            sources[path.name] = raw
    if 'full_cli.py' not in sources:
        raise ValueError('frozen replay entrypoint missing')
    return sources


def verify(data=DATA, replay=True):
    manifest_path = data / 'artifact-manifest-v2.json'
    if not manifest_path.exists():
        manifest_path = data / 'artifact-manifest-v1.json'
    if digest(manifest_path.read_bytes()) != MANIFEST_SHA256[manifest_path.name]:
        raise ValueError('recorded artifact manifest identity changed')
    manifest = read(manifest_path)
    for rel, expected in manifest['files'].items():
        path = Path(rel)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('unsafe artifact path')
        if digest((data / path).read_bytes()) != expected:
            raise ValueError('artifact bytes changed: ' + rel)
    sources = frozen_runtime(data)
    cases = read(data / 'cases-v1.json')['retrieval_cases']
    original = read(data / 'summary-v1.json')
    successor = read(data / 'sequential-summary-v2.json')
    for provider, receipt_dir, rows in [
        ('consensus', 'receipts', [r for r in original['retrieval'] if r['provider'] == 'consensus']),
        ('scispace', 'receipts', [r for r in original['retrieval'] if r['provider'] == 'scispace']),
        ('consensus', 'receipts-v2', successor['rows']),
    ]:
        if len(rows) != len(cases):
            raise ValueError('case count mismatch')
        for c, observed in zip(cases, rows):
            p = data / receipt_dir / (provider + '-' + c['id'] + '.json')
            expected = score_retrieval(read(p), c)
            expected['receipt_sha256'] = digest(p.read_bytes())
            if observed != expected:
                raise ValueError('retrieval metrics changed')
    local = read(data / 'far-results-v1.json')['rows']
    aggregate = {'cases': len(local), 'errors': sum(r['returncode'] != 0 for r in local),
                 'replay_passes': sum((r.get('replay') or {}).get('returncode') == 0 for r in local),
                 'claim_candidates': sum(r.get('claim_candidates', 0) for r in local),
                 'inference_statuses': dict(Counter(s for r in local for s in r.get('inference_statuses', []))),
                 'claim_statuses': dict(Counter(s for r in local for s in r.get('claim_statuses', [])))}
    if aggregate != original['far_local']:
        raise ValueError('local aggregate changed')
    if original['customer_value_established'] is not False or original['general_reasoning_reliability_established'] is not False:
        raise ValueError('unsupported result promotion')
    if successor['customer_value_established'] is not False or successor['general_reasoning_reliability_established'] is not False:
        raise ValueError('unsupported successor promotion')
    if replay:
        with tempfile.TemporaryDirectory() as tmp:
            historical = Path(tmp) / 'frozen-runtime'
            historical.mkdir()
            for name, raw in sources.items():
                (historical / name).write_bytes(raw)
            with zipfile.ZipFile(data / 'far-deliveries-v1.zip') as z:
                names = z.namelist()
                if len(names) != len(set(names)) or sum(i.file_size for i in z.infolist()) > 20_000_000:
                    raise ValueError('invalid archive bounds')
                for name in names:
                    p = Path(name)
                    if p.is_absolute() or '..' in p.parts or p.parts[0] not in ('far-packages', 'far-requests'):
                        raise ValueError('unsafe archive path')
                z.extractall(tmp)
            packages = sorted((Path(tmp) / 'far-packages').iterdir())
            if len(packages) != len(local):
                raise ValueError('archive case count changed')
            by_id = {r['case_id']: r for r in local}
            if len(by_id) != len(local) or {p.name for p in packages} != set(by_id):
                raise ValueError('archive identity mismatch')
            for package in packages:
                result = by_id[package.name]
                request = Path(tmp) / 'far-requests' / (package.name + '.json')
                if digest(request.read_bytes()) != result['input_sha256']:
                    raise ValueError('request identity changed')
                r = subprocess.run([sys.executable, '-E', '-s', str(historical / 'full_cli.py'),
                                    '--verify', str(package)], cwd=historical,
                                   capture_output=True, text=True, timeout=30)
                if r.returncode:
                    raise ValueError('package replay failed: ' + package.name)
    return {'verified_retrieval_receipts': 12, 'local_packages': len(local),
            'historical_runtime_sources_verified': len(sources), 'runtime_base_commit': BASE,
            'portable_replay_executed': replay, 'customer_value_established': False,
            'general_reasoning_reliability_established': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=DATA)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.data), sort_keys=True))
    except (ValueError, KeyError, OSError, zipfile.BadZipFile) as exc:
        print('LIVE_EVALUATION_INVALID: ' + str(exc), file=sys.stderr)
        raise SystemExit(2)
