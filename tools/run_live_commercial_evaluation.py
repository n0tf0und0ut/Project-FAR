#!/usr/bin/env python3
"""Replay a bounded live-service evaluation without equating retrieval with truth."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import time
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'commercial/far-investigation-audit/evaluation/live-001'
RUNTIME = ROOT / 'commercial/far-investigation-audit'
BASE = '38e6c8e8b3b1f0a7c75795c9eac8c1c6189cf7ab'
PROVIDERS = ('consensus', 'scispace')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise ValueError('duplicate JSON key')
            result[k] = v
        return result
    return json.loads(Path(path).read_text(), object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))


def write_new(path, value):
    raw = (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f:
        f.write(raw)


def bound_paths():
    return [Path(__file__), DATA / 'protocol-v1.json', DATA / 'cases-v1.json',
            DATA / 'crossref-reference-metadata-v1.json',
            ROOT / 'tests/test_live_commercial_evaluation.py',
            *sorted(RUNTIME.glob('*.py'))]


def freeze():
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if head != BASE:
        raise ValueError('unexpected baseline; register a successor')
    record = {'schema': 'far-live-registration/1', 'status': 'FROZEN_INTERNAL_EXPLORATORY',
              'frozen_at': datetime.now(timezone.utc).isoformat(), 'base_commit': BASE,
              'independent': False,
              'files': {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in bound_paths()}}
    write_new(DATA / 'registration-v1.json', record)
    return record


def check_freeze():
    record = read(DATA / 'registration-v1.json')
    if record['base_commit'] != BASE:
        raise ValueError('baseline changed')
    expected = {str(p.relative_to(ROOT)) for p in bound_paths()}
    if set(record['files']) != expected:
        raise ValueError('freeze inventory changed')
    for p, h in record['files'].items():
        if digest((ROOT / p).read_bytes()) != h:
            raise ValueError('frozen bytes changed: ' + p)
    return record


def normalized(text):
    return ' '.join(re.findall(r'\w+', unicodedata.normalize('NFKC', text).casefold()))


def score_retrieval(receipt, case):
    if receipt['provider'] not in PROVIDERS or receipt['case_id'] != case['id']:
        raise ValueError('provider/case mismatch')
    if receipt['request'] != case['query']:
        raise ValueError('input mismatch')
    if not isinstance(receipt['elapsed_ms'], (int, float)) or isinstance(receipt['elapsed_ms'], bool) or not math.isfinite(receipt['elapsed_ms']) or receipt['elapsed_ms'] < 0:
        raise ValueError('invalid elapsed time')
    response = receipt.get('response')
    payload = json.dumps(response, ensure_ascii=False, allow_nan=False)
    # Serialized wrappers can escape Unicode/newlines. Walk values instead so
    # presence checks apply to returned content, not the wrapper's JSON encoding.
    def strings(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for v in value.values():
                yield from strings(v)
        elif isinstance(value, list):
            for v in value:
                yield from strings(v)
    returned = '\n'.join(strings(response))
    error = receipt.get('error') or (isinstance(response, dict) and response.get('isError'))
    successful = response is not None and not error
    return {'provider': receipt['provider'], 'case_id': case['id'],
            'status': 'RESPONSE_RECORDED' if successful else 'ERROR_RECORDED',
            'target_doi_present': case['target_doi'].casefold() in returned.casefold() if successful else None,
            'target_title_present': normalized(case['target_title']) in normalized(returned) if successful else None,
            'elapsed_ms': receipt['elapsed_ms'], 'payload_sha256': digest(payload.encode()),
            'returned_rank': None, 'scientific_support_verified': False,
            'per_call_dollar_cost': None, 'human_effort_seconds': None}


def run_far():
    check_freeze()
    cases = read(DATA / 'cases-v1.json')
    rows = []
    for case in cases['raw_document_cases'] + cases['retrieval_cases']:
        ident = case['id']
        request = {'investigation_id': 'live-001-' + ident,
                   'source': {'kind': 'text', 'text': case.get('text', case.get('query'))},
                   'proposal_mode': 'heuristic', 'evidence_sources': []}
        request_path = DATA / 'far-requests' / (ident + '.json')
        write_new(request_path, request)
        destination = DATA / 'far-packages' / ident
        start = time.perf_counter()
        run = subprocess.run([sys.executable, str(RUNTIME / 'full_cli.py'), str(request_path),
                              '--output', str(destination)], cwd=ROOT, text=True,
                             capture_output=True, timeout=30)
        replay = None
        if run.returncode == 0:
            replay = subprocess.run([sys.executable, str(RUNTIME / 'full_cli.py'),
                                     '--verify', str(destination)], cwd=ROOT, text=True,
                                    capture_output=True, timeout=30)
        elapsed = time.perf_counter() - start
        row = {'case_id': ident, 'input_sha256': digest(request_path.read_bytes()),
               'elapsed_seconds_including_replay': elapsed, 'returncode': run.returncode,
               'stdout': run.stdout, 'stderr': run.stderr,
               'replay': {'returncode': replay.returncode, 'stdout': replay.stdout, 'stderr': replay.stderr} if replay else None,
               'operator_semantic_coding': False, 'actual_customer_time_seconds': None}
        if run.returncode == 0:
            audit = read(destination / 'audit.json')
            row.update({'claim_candidates': len(audit['claims']),
                        'inference_statuses': [r['formal_inference']['status'] for r in audit['interpretations']],
                        'claim_statuses': [r['status'] for r in audit['claims'].values()],
                        'semantic_fidelity_independently_verified': False})
        rows.append(row)
    write_new(DATA / 'far-results-v1.json', {'schema': 'far-live-local-results/1', 'rows': rows})
    return {'cases': len(rows), 'errors': sum(r['returncode'] != 0 for r in rows)}


def summarize():
    check_freeze()
    cases = read(DATA / 'cases-v1.json')
    scored = []
    missing = []
    for provider in PROVIDERS:
        for c in cases['retrieval_cases']:
            p = DATA / 'receipts' / (provider + '-' + c['id'] + '.json')
            if not p.exists():
                missing.append({'provider': provider, 'case_id': c['id']})
            else:
                row = score_retrieval(read(p), c)
                row['receipt_sha256'] = digest(p.read_bytes())
                scored.append(row)
    local = read(DATA / 'far-results-v1.json')['rows']
    value = {'schema': 'far-live-summary/1', 'status': 'Research',
             'registration_sha256': digest((DATA / 'registration-v1.json').read_bytes()),
             'retrieval': scored, 'missing_calls': missing,
             'far_local': {'cases': len(local), 'errors': sum(r['returncode'] != 0 for r in local),
                           'replay_passes': sum((r.get('replay') or {}).get('returncode') == 0 for r in local),
                           'claim_candidates': sum(r.get('claim_candidates', 0) for r in local),
                           'inference_statuses': dict(Counter(s for r in local for s in r.get('inference_statuses', []))),
                           'claim_statuses': dict(Counter(s for r in local for s in r.get('claim_statuses', [])))},
             'customer_value_established': False, 'general_reasoning_reliability_established': False,
             'independent_semantic_accuracy': None, 'customer_value_dollars': None,
             'comparative_superiority': 'NOT_ESTABLISHED'}
    write_new(DATA / 'summary-v1.json', value)
    return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('freeze', 'check', 'far', 'summarize'))
    args = parser.parse_args()
    result = {'freeze': freeze, 'check': check_freeze, 'far': run_far, 'summarize': summarize}[args.action]()
    print(json.dumps(result, sort_keys=True))
