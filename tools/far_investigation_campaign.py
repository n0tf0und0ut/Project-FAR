"""Reproducible live investigation campaign and conservative integrity metrics.

This scores observable execution, never self-reported semantic correctness.
Existing-system and independent semantic adjudication are separate records.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import os
import socket
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
from tools.far_investigation_usage import model_usage_report

MODEL_SHA256 = '9c9f56a391a3abbd5b89d0245bf6106081bcc3173119d4229235dd9d23253f94'
RUNNER_SHA256 = 'ae1311cdc0f67bd78e01e7b20bc5ed403814a621c290dd0ee29b8c67c0feece0'
# A bounded native source can appear in several retained HTTP observations,
# original receipts and terminal rechecks. The historical 64 MB per-member
# limit fits one source but not two legal near-ceiling sources (~75.6 MB).
# Derive a conservative finite admission ceiling from the default 16-call
# campaign budget (at most eight retrieval/recheck pairs). Campaigns that
# exceed this separate recording budget fail during execution; audit never
# silently certifies archives larger than the execution contract.
MAX_TRANSCRIPT_MEMBER_BYTES = 64_000_000 * max(1, Budget().max_http_calls // 2)
MAX_ARCHIVE_TOTAL_UNCOMPRESSED_BYTES = 2 * MAX_TRANSCRIPT_MEMBER_BYTES
MAX_CAMPAIGN_INDEX_BYTES = 8_000_000

IMPLEMENTATION = ('tools/far_investigation_engine.py', 'tools/far_investigation_retrieval.py',
                  'tools/far_investigation_audit.py',
                  'tools/far_investigation_usage.py',
                  'tools/far_investigation_verifiers.py', 'tools/far_investigation_campaign.py',
                  'tools/far_autonomous_investigation.py', 'tools/far_uncertain_routing_pilot.py',
                  'tools/far_routing_dispatch.py')


def file_sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def _file_identity(path):
    stat = Path(path).stat()
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)


def _server_identity(server, command, executable_identity, model_identity):
    """Fail closed unless this live Linux child owns the endpoint and weights.

    A health response alone identifies neither the serving process nor model.
    Bind the listener's kernel socket inode, exact process arguments, executable
    file identity and mapped model inode to the process we actually launched.
    This is local provenance, not protection against a malicious host or runner.
    """
    if server.poll() is not None:
        raise RuntimeError('local server exited during startup or inference')
    try:
        # /proc can expose the parent PID namespace while Popen reports the
        # child's innermost PID. Resolve only our actual direct children; never
        # interpret an unrelated same-numbered process as the launched server.
        parent_status = Path('/proc/self/status').read_text().splitlines()
        parent_pid = next(line.split()[1] for line in parent_status if line.startswith('Pid:'))
        candidates = []
        for candidate in Path('/proc').iterdir():
            if not candidate.name.isdigit():
                continue
            try:
                status = (candidate / 'status').read_text().splitlines()
            except OSError:
                continue  # Unrelated processes can disappear or deny access.
            fields = {line.split(':', 1)[0]: line.split(':', 1)[1].split() for line in status if ':' in line}
            if fields.get('PPid') != [parent_pid]:
                continue
            namespace_ids = fields.get('NSpid', [])
            if namespace_ids and int(namespace_ids[-1]) == server.pid:
                candidates.append(candidate)
        if len(candidates) != 1:
            raise RuntimeError('cannot uniquely identify the launched direct child')
        proc = candidates[0]
        actual_command = [os.fsdecode(x) for x in (proc / 'cmdline').read_bytes().split(b'\0') if x]
        if actual_command != command or _file_identity(proc / 'exe') != executable_identity:
            raise RuntimeError('local server executable or command identity changed')
        model_path = Path(command[command.index('--model') + 1])
        if _file_identity(model_path) != model_identity:
            raise RuntimeError('local model file identity changed')
        device, inode = model_identity[:2]
        mapped = any(int(parts[4]) == inode
                     and tuple(int(x, 16) for x in parts[3].split(':'))
                     == (os.major(device), os.minor(device))
                     for line in (proc / 'maps').read_text().splitlines()
                     if len(parts := line.split(None, 5)) >= 5)
        if not mapped:
            raise RuntimeError('launched server has not mapped the registered model file')
        listeners = {parts[9] for line in (proc / 'net' / 'tcp').read_text().splitlines()[1:]
                     if len(parts := line.split()) >= 10
                     and parts[1] == '0100007F:1F95' and parts[3] == '0A'}
        owned = {entry.readlink().as_posix() for entry in (proc / 'fd').iterdir()}
        matching = sorted(inode for inode in listeners if 'socket:[' + inode + ']' in owned)
        if len(matching) != 1 or set(matching) != listeners or server.poll() is not None:
            raise RuntimeError('model endpoint is not exclusively owned by the launched server')
        return {'pid': server.pid, 'procfs_pid': int(proc.name), 'endpoint': 'http://127.0.0.1:8085',
                'command': command, 'listener_inode': matching[0],
                'executable_file_identity': list(executable_identity),
                'mapped_model_file_identity': list(model_identity),
                'scope': 'Linux process/listener/file identity; no malicious-host authentication'}
    except (OSError, ValueError, IndexError, StopIteration) as exc:
        raise RuntimeError('cannot establish launched server process/model ownership') from exc


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
            'native_counterexamples': sum(e['result'].get('counterexample') is not None for e in state['evaluations']),
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
    errors, audited, usage_audits = [], 0, []
    def same(left, right):
        return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)
    try:
        manifest = _parse((directory / 'evidence-manifest.json').read_text())
        entries = manifest['files']
        if type(entries) is not list or not entries:
            raise ValueError('nonempty evidence manifest required')
    except (ValueError, KeyError, TypeError, OSError) as exc:
        return {'valid': False, 'errors': ['invalid evidence manifest: ' + str(exc)],
                'audited_transcripts': 0, 'scope': 'Declared byte integrity and native replay only.'}
    seen_paths = set()
    for entry in entries:
        try:
            relative = Path(entry['path'])
            if relative.is_absolute() or '..' in relative.parts or str(relative) in seen_paths:
                raise ValueError('unsafe or duplicate evidence path')
            seen_paths.add(str(relative))
            path = directory / relative
            if not path.is_file() or file_sha(path) != entry['sha256']:
                raise ValueError('evidence hash mismatch: ' + str(relative))
            if not entry.get('audit_transcripts'):
                continue
            # The registered selection lives outside the mutable campaign ZIP.
            selection_path = Path(entry['selection_path'])
            if selection_path.is_absolute() or '..' in selection_path.parts:
                raise ValueError('unsafe selection path')
            selection_bytes = (directory / selection_path).read_bytes()
            selection = _parse(selection_bytes.decode())
            tasks = selection['tasks']
            registered_hosts = sorted({urlsplit(url).hostname for task in tasks
                                       for url in task['source_hints']}
                                      | {'api.crossref.org', 'en.wikipedia.org'})
            modes = entry['modes']
            if (not tasks or len({t['id'] for t in tasks}) != len(tasks)
                    or type(modes) is not list or not modes
                    or len(set(modes)) != len(modes)
                    or any(m not in ('agent', 'deterministic', 'declarative') for m in modes)):
                raise ValueError('invalid registered task/mode exposure')
            expected = [(t['id'], mode) for t in tasks for mode in modes]
            with zipfile.ZipFile(path) as archive:
                members = archive.infolist()
                if len({i.filename for i in members}) != len(members):
                    raise ValueError('duplicate archive member')
                # Bound both a single decoded transcript and the cumulative
                # uncompressed archive. ZIP compression is not a trusted
                # substitute for these limits; the index gets a smaller bound.
                if any(i.file_size > (MAX_CAMPAIGN_INDEX_BYTES if i.filename == 'campaign.json'
                                      else MAX_TRANSCRIPT_MEMBER_BYTES) for i in members):
                    raise ValueError('archive member exceeds bound')
                if sum(i.file_size for i in members) > MAX_ARCHIVE_TOTAL_UNCOMPRESSED_BYTES:
                    raise ValueError('archive total uncompressed bytes exceed bound')
                campaign = _parse(archive.read('campaign.json').decode())
                if (campaign['schema'] != 'far-investigation-campaign/0.1'
                        or campaign['status'] != 'EXECUTED'
                        or not same(campaign['selection'], selection)
                        or campaign['selection_sha256'] != hashlib.sha256(selection_bytes).hexdigest()):
                    raise ValueError('campaign differs from registered selection or completion status')
                if campaign.get('policy_hosts') != registered_hosts:
                    raise ValueError('campaign host policy differs from registered source hints')
                if (campaign['git_head'] != entry['source_commit']
                        or campaign['source_hashes'] != entry['source_hashes']):
                    raise ValueError('campaign source identity differs from retained execution binding')
                if 'agent' in modes and campaign['model_sha256'] != MODEL_SHA256:
                    raise ValueError('campaign model differs from registered model')
                rows = campaign['rows']
                if [(r['task_id'], r['mode']) for r in rows] != expected:
                    raise ValueError('campaign exposure missing, duplicated, reordered or unregistered')
                for row, (task_id, mode) in zip(rows, expected):
                    name = task_id + '-' + mode + '.json'
                    if row['transcript'] != name:
                        raise ValueError('campaign transcript identity mismatch')
                    raw = archive.read(name)
                    if hashlib.sha256(raw).hexdigest() != row['transcript_sha256']:
                        raise ValueError('campaign transcript hash mismatch: ' + name)
                    state = _parse(raw.decode())
                    task = next(t for t in tasks if t['id'] == task_id)
                    if (state['question'] != task['question'] or state['mode'] != mode
                            or not same(state['policy']['budget'], campaign['budget'])):
                        raise ValueError('transcript task, mode or budget differs from registered campaign')
                    if (not same(state.get('seeds'), task['source_hints']) or
                            not same(state['policy'].get('allowed_hosts'), registered_hosts)):
                        raise ValueError('transcript source exposure or permitted hosts differ from registered selection')
                    result = audit_transcript(state)
                    usage_audits.append({'archive': str(relative), 'transcript': name,
                                         **model_usage_report(state)})
                    audited += 1
                    errors.extend(name + ': ' + error for error in result['errors'])
                    if not same(row['metrics'], metrics(state)):
                        raise ValueError('campaign metrics do not reconstruct: ' + name)
                if not same(campaign['summary'], summarize(rows)):
                    raise ValueError('campaign summary does not reconstruct')
        except (ValueError, KeyError, TypeError, OSError, UnicodeError, zipfile.BadZipFile) as exc:
            errors.append(str(entry.get('path', '<invalid>') if isinstance(entry, dict) else '<invalid>')
                          + ': ' + type(exc).__name__ + ' ' + str(exc))
    return {'valid': not errors, 'errors': errors, 'audited_transcripts': audited,
            'raw_usage_audit': {
                'schema': 'far-investigation-campaign-raw-usage-audit/1',
                'recorded_model_tokens': sum(r['recorded_model_tokens'] for r in usage_audits),
                'validated_response_tokens_lower_bound': sum(r['validated_response_tokens_lower_bound'] for r in usage_audits),
                'attempts_with_usage': sum(r['attempts_with_usage'] for r in usage_audits),
                'attempts_without_usage': sum(r['attempts_without_usage'] for r in usage_audits),
                'transcripts': usage_audits,
                'scope': 'Original campaign counters remain byte-checked legacy observations. This separate retained-response telemetry lower bound includes rejected actions; unobserved or timed-out work remains unknown. It is not total consumption, billing, or external authentication.'},
            'scope': 'Declared byte integrity and native replay only; semantic correctness is separate.'}



def persist_campaign_index(output, campaign):
    """Preflight the proposed index and cumulative JSON bytes before replacement.

    Match persist's indented, ASCII-escaped JSON plus final newline. Exclude the
    previous index from the sum because this write replaces it atomically.
    A rejected write leaves that last bounded index and raw transcripts intact.
    """
    output = Path(output)
    index = output / 'campaign.json'
    proposed = (json.dumps(campaign, indent=2, sort_keys=True, allow_nan=False)
                + '\n').encode('utf-8')
    if len(proposed) > MAX_CAMPAIGN_INDEX_BYTES:
        raise ValueError('campaign index exceeds bounded archive member budget')
    other_bytes = sum(path.stat().st_size for path in output.glob('*.json')
                      if path != index)
    if other_bytes + len(proposed) > MAX_ARCHIVE_TOTAL_UNCOMPRESSED_BYTES:
        raise ValueError('campaign index and transcripts exceed total uncompressed archive budget')
    persist(index, campaign)


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
    persist_campaign_index(output, campaign)
    server = None
    log = None
    try:
        if 'agent' in modes:
            if not model_path or not server_path or campaign['model_sha256'] != MODEL_SHA256:
                raise ValueError('actual exact pinned local model and server required')
            # An unrelated server must not satisfy readiness, even if the new
            # executable exits before the first successful health response.
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reservation:
                try:
                    reservation.bind(('127.0.0.1', 8085))
                except OSError as exc:
                    raise RuntimeError('local model endpoint is occupied') from exc
            model_path, server_path = Path(model_path).resolve(strict=True), Path(server_path).resolve(strict=True)
            executable_identity, model_identity = _file_identity(server_path), _file_identity(model_path)
            campaign['server_executable_sha256'] = file_sha(server_path)
            if (file_sha(model_path) != campaign['model_sha256']
                    or _file_identity(model_path) != model_identity
                    or _file_identity(server_path) != executable_identity):
                raise RuntimeError('model or executable changed while binding launch provenance')
            command = [str(server_path), '--model', str(model_path), '--host', '127.0.0.1',
                '--port', '8085', '--ctx-size', '16384', '--threads', '6', '--parallel', '1',
                '--seed', '271828', '--jinja', '--no-webui']
            log = (output / 'model-server.log').open('w')
            server = subprocess.Popen(command, stdout=log, stderr=log)
            persist_campaign_index(output, campaign)
            for _ in range(120):
                if server.poll() is not None:
                    raise RuntimeError('local server exited during startup')
                try:
                    with urllib.request.urlopen('http://127.0.0.1:8085/health', timeout=1) as response:
                        if response.status == 200:
                            campaign['server_process_identity'] = _server_identity(
                                server, command, executable_identity, model_identity)
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
                def retain_bounded(state):
                    persist(path, state)
                    if path.stat().st_size > MAX_TRANSCRIPT_MEMBER_BYTES:
                        raise ValueError('transcript exceeds bounded campaign archive member budget')
                runtime = Investigation(task['question'], policy, seeds=task['source_hints'], mode=mode,
                                       budget=budget, checkpoint=retain_bounded)
                state = runtime.run_agent(LocalModel(identity_check=lambda: _server_identity(
                    server, command, executable_identity, model_identity))) if mode == 'agent' else runtime.run_workflow()
                retain_bounded(state)
                if sum(p.stat().st_size for p in output.glob('*.json')) > MAX_ARCHIVE_TOTAL_UNCOMPRESSED_BYTES:
                    raise ValueError('campaign transcripts exceed total uncompressed archive budget')
                row = {'task_id': task['id'], 'mode': mode, 'transcript': path.name,
                       'transcript_sha256': file_sha(path), 'metrics': metrics(state)}
                campaign['rows'].append(row)
                campaign['summary'] = summarize(campaign['rows'])
                persist_campaign_index(output, campaign)
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
        persist_campaign_index(output, campaign)
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
