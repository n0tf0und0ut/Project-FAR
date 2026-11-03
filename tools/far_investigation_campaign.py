"""Reproducible live investigation campaign and conservative integrity metrics.

This scores observable execution, never self-reported semantic correctness.
Existing-system and independent semantic adjudication are separate records.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.far_investigation_engine import (
    Budget, Investigation, LocalModel, RetrievalPolicy, audit_transcript, now, persist,
)
from tools.far_routing_dispatch import _parse

MODEL_SHA256 = '9c9f56a391a3abbd5b89d0245bf6106081bcc3173119d4229235dd9d23253f94'
RUNNER_SHA256 = 'ae1311cdc0f67bd78e01e7b20bc5ed403814a621c290dd0ee29b8c67c0feece0'
IMPLEMENTATION = ('tools/far_investigation_engine.py', 'tools/far_investigation_retrieval.py',
                  'tools/far_investigation_audit.py',
                  'tools/far_investigation_verifiers.py', 'tools/far_investigation_campaign.py',
                  'tools/far_autonomous_investigation.py', 'tools/far_uncertain_routing_pilot.py',
                  'tools/far_routing_dispatch.py')


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def metrics(state):
    integrity = audit_transcript(state)
    intake = state['intake']
    frozen = bool(intake and intake['freeze']['status'] == 'FROZEN')
    candidates = intake['discovery']['contract_candidates'] if intake else []
    return {'status': state['status'], 'pipeline_completed': state['status'] == 'BOUNDED_PIPELINE_COMPLETED',
            'integrity_valid': integrity['valid'], 'integrity_errors': integrity['errors'],
            'retrieved_sources': len(state['sources']), 'extracted_quotes': len(state['evidence']),
            'source_comparisons': len(state['comparisons']), 'frozen_valid_family': frozen and integrity['valid'],
            'candidate_count': len(candidates), 'native_evaluations': len(state['evaluations']),
            'native_counterexamples': sum(bool(e['result'].get('counterexample')) for e in state['evaluations']),
            'analyst_declared_conflicts': sum(c['asserted_conflict'] for c in state['comparisons']),
            'semantic_correctness': None, 'contract_semantic_completeness': None,
            'unsupported_conclusions': None,
            'semantic_score_boundary': 'Requires separate substantive adjudication; integrity is not correctness.',
            'tool_proposals': sum(e['kind'] == 'TOOL_PROPOSAL' for e in state['events']),
            'rejected_calls': state['rejected_calls'], 'controller_substitutions': state['controller_substitutions'],
            'http_calls': state['http_calls'], 'model_calls': len(state['model_calls']),
            'http_calls_definition': 'Reserved HTTP tool attempts including destination/transport rejection; not a count of successful network responses.',
            'model_tokens': state['model_tokens'], 'elapsed_seconds': state['elapsed_seconds'],
            'source_bytes': sum(r['observed_bytes'] for r in state['sources'].values()),
            'billed_cost': None, 'cost_boundary': 'Local execution; no billing, energy or amortized hardware-cost measurement.',
            'closure': state['report']['investigation_closure'] if state['report'] else 'Incomplete'}


def summarize(rows):
    result = {}
    for mode in ('agent', 'deterministic', 'declarative'):
        selected = [r for r in rows if r['mode'] == mode]
        result[mode] = {'attempted': len(selected),
                        'pipeline_completed': sum(r['metrics']['pipeline_completed'] for r in selected),
                        'valid_integrity': sum(r['metrics']['integrity_valid'] for r in selected),
                        'frozen_valid_families': sum(r['metrics']['frozen_valid_family'] for r in selected),
                        'rejected_calls': sum(r['metrics']['rejected_calls'] for r in selected),
                        'controller_substitutions': sum(r['metrics']['controller_substitutions'] for r in selected),
                        'http_calls': sum(r['metrics']['http_calls'] for r in selected),
                        'model_tokens': sum(r['metrics']['model_tokens'] for r in selected),
                        'semantic_successes': None, 'superiority': 'NOT_ESTABLISHED'}
    return result


def audit_directory(directory):
    """Verify declared evidence bytes and replay current-version transcripts."""
    directory = Path(directory)
    manifest = _parse((directory / 'evidence-manifest.json').read_text())
    errors, audited = [], 0
    for entry in manifest['files']:
        relative = Path(entry['path'])
        if relative.is_absolute() or '..' in relative.parts:
            errors.append('unsafe evidence path')
            continue
        path = directory / relative
        if not path.is_file() or file_sha(path) != entry['sha256']:
            errors.append('evidence hash mismatch: ' + str(relative))
            continue
        if entry.get('audit_transcripts'):
            try:
                with zipfile.ZipFile(path) as archive:
                    if any(i.file_size > 64_000_000 for i in archive.infolist()):
                        raise ValueError('archive member exceeds bound')
                    campaign = _parse(archive.read('campaign.json').decode())
                    for row in campaign['rows']:
                        raw = archive.read(row['transcript'])
                        if hashlib.sha256(raw).hexdigest() != row['transcript_sha256']:
                            errors.append('campaign transcript hash mismatch: ' + row['transcript'])
                        state = _parse(raw.decode())
                        result = audit_transcript(state)
                        audited += 1
                        errors.extend(row['transcript'] + ': ' + error for error in result['errors'])
            except (ValueError, KeyError, OSError, zipfile.BadZipFile) as exc:
                errors.append(str(relative) + ': ' + type(exc).__name__ + ' ' + str(exc))
    return {'valid': not errors, 'errors': errors, 'audited_transcripts': audited,
            'scope': 'Declared byte integrity and native replay only; semantic correctness is separate.'}


def run(selection, output, *, model_path=None, server_path=None, modes=('deterministic', 'declarative', 'agent'),
        budget=Budget(max_steps=24, max_seconds=420), dns_mode='preflight'):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    selection_bytes = Path(selection).read_bytes()
    document = _parse(selection_bytes.decode())
    tasks = document['tasks']
    if not tasks or len({t['id'] for t in tasks}) != len(tasks):
        raise ValueError('nonempty unique task selection required')
    policy_hosts = sorted({urlsplit(url).hostname for t in tasks for url in t['source_hints']}
                          | {'api.crossref.org', 'en.wikipedia.org'})
    policy = RetrievalPolicy(tuple(policy_hosts), timeout=20, dns_mode=dns_mode)
    campaign = {'schema': 'far-investigation-campaign/0.1', 'status': 'RUNNING', 'started_at': now(),
                'selection_sha256': hashlib.sha256(selection_bytes).hexdigest(),
                'selection': document, 'budget': vars(budget), 'policy_hosts': policy_hosts,
                'source_hashes': {p: file_sha(ROOT / p) for p in IMPLEMENTATION},
                'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'python': platform.python_version(), 'platform': platform.platform(),
                'model_sha256': file_sha(model_path) if model_path else None,
                'model_identity': 'bartowski/Qwen2.5-3B-Instruct-GGUF@f302c64a2269a69fb27b2f9473b362f5bb8e78d8 Q4_K_M',
                'rows': [], 'nonclaims': ['No external/I2 independence', 'No source-truth certification',
                    'No general autonomy or superiority', 'No evidence-closure promotion'],
                'workflow_comparator_identity': 'Deterministic and declarative lanes share the same algorithm and tools; different execution representation only.'}
    persist(output / 'campaign.json', campaign)
    server = None
    log = None
    try:
        if 'agent' in modes:
            if not model_path or not server_path or campaign['model_sha256'] != MODEL_SHA256:
                raise ValueError('actual exact pinned local model and server required')
            log = (output / 'model-server.log').open('w')
            server = subprocess.Popen([str(server_path), '--model', str(model_path), '--host', '127.0.0.1',
                '--port', '8085', '--ctx-size', '16384', '--threads', '6', '--parallel', '1',
                '--seed', '271828', '--jinja', '--no-webui'], stdout=log, stderr=log)
            campaign['server_executable_sha256'] = file_sha(server_path)
            persist(output / 'campaign.json', campaign)
            for _ in range(120):
                try:
                    with urllib.request.urlopen('http://127.0.0.1:8085/health', timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    if server.poll() is not None:
                        raise RuntimeError('local server exited during startup')
                    time.sleep(.25)
            else:
                raise RuntimeError('local server startup timed out')
        # Task start order remains manifest order; no replacement of failures.
        for task in tasks:
            for mode in modes:
                path = output / (task['id'] + '-' + mode + '.json')
                runtime = Investigation(task['question'], policy, seeds=task['source_hints'], mode=mode,
                                       budget=budget, checkpoint=lambda s: persist(path, s))
                state = runtime.run_agent(LocalModel()) if mode == 'agent' else runtime.run_workflow()
                persist(path, state)
                row = {'task_id': task['id'], 'mode': mode, 'transcript': path.name,
                       'transcript_sha256': file_sha(path), 'metrics': metrics(state)}
                campaign['rows'].append(row)
                campaign['summary'] = summarize(campaign['rows'])
                persist(output / 'campaign.json', campaign)
                print(json.dumps({'task': task['id'], 'mode': mode, **row['metrics']}), flush=True)
        campaign['status'] = 'EXECUTED'
    except (ValueError, RuntimeError, OSError) as exc:
        campaign['status'] = 'FAILED_OR_INCOMPLETE'
        campaign['failure'] = {'class': type(exc).__name__, 'reason': str(exc)}
        raise
    finally:
        if server:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
        if log:
            log.close()
        campaign['finished_at'] = now()
        campaign['summary'] = summarize(campaign['rows'])
        persist(output / 'campaign.json', campaign)
    return campaign


def main(argv=None):
    args_in = sys.argv[1:] if argv is None else list(argv)
    if args_in and args_in[0] == 'audit':
        if len(args_in) != 2:
            raise ValueError('audit requires an evidence directory')
        result = audit_directory(args_in[1])
        print(json.dumps(result, indent=2))
        return 0 if result['valid'] else 2
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('selection', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model', type=Path)
    parser.add_argument('--server', type=Path)
    parser.add_argument('--mode', choices=('agent', 'deterministic', 'declarative'), action='append')
    parser.add_argument('--seconds', type=float, default=420)
    parser.add_argument('--dns-mode', choices=('preflight', 'proxy'), default='preflight')
    args = parser.parse_args(args_in)
    campaign = run(args.selection, args.output, model_path=args.model, server_path=args.server,
                   modes=tuple(args.mode) if args.mode else ('deterministic', 'declarative', 'agent'),
                   budget=Budget(max_steps=24, max_seconds=args.seconds), dns_mode=args.dns_mode)
    print(json.dumps(campaign['summary'], indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
