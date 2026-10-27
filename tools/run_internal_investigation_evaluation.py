#!/usr/bin/env python3
"""Registered, project-controlled exploratory probes; no external scientific claims."""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
CASE_DIR = ROOT / 'commercial/far-investigation-audit/evaluation/internal-001'
AUDIT_DIR = ROOT / 'commercial/far-investigation-audit'
NOESIS_PIN = 'd38eb1fd956843b6eeeaeb582d3b4e1092255d94'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise ValueError('duplicate JSON key: ' + k)
            result[k] = v
        return result
    return json.loads(Path(path).read_text(), object_pairs_hook=unique)


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value) + b'\n')


def validate_cases(corpus):
    if corpus.get('schema') != 'far-internal-exploratory-corpus/1':
        raise ValueError('wrong corpus schema')
    for group in ['source_to_report', 'formal_comparison']:
        rows = corpus.get(group)
        if not isinstance(rows, list) or not 1 <= len(rows) <= 500:
            raise ValueError('invalid bounded corpus')
        ids = [r.get('case_id') for r in rows]
        if any(not isinstance(i, str) or not re.fullmatch('[A-Za-z0-9_.-]{1,80}', i) for i in ids) or len(set(ids)) != len(ids):
            raise ValueError('invalid or duplicate case identity')
    source_ids = {r['case_id'] for r in corpus['source_to_report']}
    if not set(corpus.get('raw_comparison_case_ids', [])).issubset(source_ids):
        raise ValueError('unknown raw comparator case')
    for row in corpus['source_to_report']:
        if row['reference'].get('label_origin') != 'PROJECT_AUTHORED_CONTROL_NOT_EXTERNAL_GOLD':
            raise ValueError('reference independence misclassified')
        cfg = row['config']
        if cfg.get('source', {}).get('kind') != 'text' or any(x.get('kind') != 'text' for x in cfg.get('evidence_sources', [])):
            raise ValueError('only supplied local text allowed')
        if cfg.get('discovery') or cfg.get('proposal_mode') != 'supplied':
            raise ValueError('network/model condition forbidden')
    return corpus


def bound_files():
    return sorted([Path(__file__).resolve(), CASE_DIR / 'cases-v1.json', CASE_DIR / 'protocol-v1.json',
                   *AUDIT_DIR.glob('*.py')])


def freeze(path, noesis_root, predecessor=None):
    path, noesis_root = Path(path), Path(noesis_root).resolve()
    if path.exists():
        raise ValueError('registration exists; preserve history')
    corpus = validate_cases(read(CASE_DIR / 'cases-v1.json'))
    head = subprocess.check_output(['git', '-C', str(noesis_root), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(noesis_root), 'status', '--porcelain', '--untracked-files=no'], text=True)
    if head != NOESIS_PIN or dirty:
        raise ValueError('Noesis source pin or tracked bytes changed')
    versions = {n: importlib.metadata.version(n) for n in ['noesis-evidence', 'sympy', 'duckdb', 'fastavro', 'jsonschema', 'PyYAML']}
    if versions['sympy'] != '1.14.0' or versions['noesis-evidence'] != '0.1.0':
        raise ValueError('unregistered comparator version')
    record = {'schema': 'far-internal-exploratory-registration/1', 'status': 'FROZEN_INTERNAL_EXPLORATORY',
              'frozen_at': datetime.now(timezone.utc).isoformat(), 'external_verification': 'DEFERRED_BY_USER',
              'harness_source_commit': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
              'reference_independence': False, 'noesis_commit': head, 'versions': versions,
              'python': platform.python_version(), 'platform': platform.platform(),
              'noesis_root': str(noesis_root), 'noesis_cli_sha256': sha(Path(sys.executable).with_name('noesis').read_bytes()),
              'files': {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in bound_files()},
              'source_case_ids': [r['case_id'] for r in corpus['source_to_report']],
              'formal_case_ids': [r['case_id'] for r in corpus['formal_comparison']]}
    if predecessor is not None:
        previous = read(predecessor)
        record['repair_of_registration_sha256'] = sha(Path(predecessor).read_bytes())
        record['repair_reason'] = 'Resolve artifact and input paths before changing comparator subprocess working directory.'
        record['same_case_bytes_as_predecessor'] = previous['files']['commercial/far-investigation-audit/evaluation/internal-001/cases-v1.json'] == record['files']['commercial/far-investigation-audit/evaluation/internal-001/cases-v1.json']
        if record['same_case_bytes_as_predecessor'] is not True:
            raise ValueError('adapter repair may not change case/reference bytes')
    write(path, record)
    return record


def validate_registration(path):
    record = read(path)
    if (record.get('schema') != 'far-internal-exploratory-registration/1'
            or record.get('external_verification') != 'DEFERRED_BY_USER'
            or record.get('reference_independence') is not False):
        raise ValueError('invalid registration boundary')
    expected = {str(p.relative_to(ROOT)) for p in bound_files()}
    if set(record.get('files', {})) != expected:
        raise ValueError('incomplete source binding')
    for name, digest in record['files'].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or sha(path.read_bytes()) != digest:
            raise ValueError('registered bytes drifted: ' + name)
    for name, version in record['versions'].items():
        if importlib.metadata.version(name) != version:
            raise ValueError('comparator environment drift: ' + name)
    corpus = validate_cases(read(CASE_DIR / 'cases-v1.json'))
    if (record['source_case_ids'] != [r['case_id'] for r in corpus['source_to_report']]
            or record['formal_case_ids'] != [r['case_id'] for r in corpus['formal_comparison']]):
        raise ValueError('registered case identities drifted')
    return record, corpus


def modules():
    sys.path.insert(0, str(AUDIT_DIR))
    import engine, workflow, full_cli, field_validation, independent_check, presentation
    return engine, workflow, full_cli, field_validation, independent_check, presentation


def sym_formula(formula):
    import sympy as s
    op, value = next(iter(formula.items()))
    if op == 'atom': return s.Symbol(value)
    if op == 'not': return s.Not(sym_formula(value))
    values = [sym_formula(x) for x in value]
    if op == 'and': return s.And(*values)
    if op == 'or': return s.Or(*values)
    if op == 'implies': return s.Implies(*values)
    raise ValueError('unsupported formula')


def sym_status(premises, conclusion):
    from sympy import And, Not
    from sympy.logic.inference import satisfiable
    p = And(*[sym_formula(x) for x in premises])
    if satisfiable(p) is False: return 'INCONSISTENT_PREMISES'
    return 'ENTAILS_CONDITIONALLY' if satisfiable(And(p, Not(sym_formula(conclusion)))) is False else 'DOES_NOT_ENTAIL'


def checked_witness(premises, conclusion, witness):
    from sympy import Symbol, false, true
    if not isinstance(witness, dict) or any(type(x) is not bool for x in witness.values()): return False
    assignment = {Symbol(k): v for k, v in witness.items()}
    return (all(sym_formula(p).subs(assignment) == true for p in premises)
            and sym_formula(conclusion).subs(assignment) == false)


def pipeline_case(row, destination):
    engine, workflow, full_cli, field, independent, presentation = modules()
    package = workflow.investigate(row['config'])
    full_cli.write_package(destination, package)
    replay = full_cli.verify_package(destination)
    audit = package['audit']
    observations = {'argument_statuses': [r['formal_inference']['status'] for r in audit['interpretations']],
                    'semantic_mapping_verified': package['manifest']['semantic_mapping_independently_verified'],
                    'factual_verdicts': [p['verdict'] for p in field.predictions_from_far_bundle(destination)],
                    'input_sha256': audit['input_sha256'], 'audit_sha256': audit['report_sha256'],
                    'source_lineage': package['manifest']['source_snapshots_sha256'], 'replay_match': replay['replay_match'],
                    'source_temporal_status': audit['source_temporal_status']}
    # Controlled auditor subprobe is distinct from the raw pipeline: source date
    # verification is a declared fixture assumption, never an external seal.
    controlled = None
    if row.get('controlled_temporal_variant') or row.get('controlled_in_window_variant'):
        bundle = json.loads(json.dumps(package['bundle']))
        for source in bundle['sources']:
            source['publication_date_verified'] = bool(row.get('controlled_in_window_variant'))
            if source['id'] != 'primary' and row.get('controlled_temporal_variant'):
                source['captured_at'] = '2026-10-26T13:00:00Z'
        report = engine.audit(bundle)
        independent.check_report(bundle, report)
        controlled = {'scope': 'PROJECT_AUTHORED_TEMPORAL_ASSUMPTION_NOT_PIPELINE_VERIFICATION',
                      'input': bundle, 'audit': report,
                      'deterministic_replay': engine.audit(bundle) == report}
        write(destination.parent / (row['case_id'] + '-controlled-auditor.json'), controlled)
    reference = row['reference']
    checks = {'argument_status': observations['argument_statuses'] == [reference['argument_status']],
              'no_semantic_promotion': observations['semantic_mapping_verified'] is False,
              'factual_abstention': all(x == 'ABSTAIN' for x in observations['factual_verdicts']),
              'replay': replay['replay_match'] is True}
    return {'case_id': row['case_id'], 'research_intake_ids': row['research_intake_ids'],
            'reference': reference, 'observations': observations, 'checks': checks,
            'unfaithful_mapping_can_pass_formal_check': reference['semantic_fidelity_internal_reference'] == 'UNFAITHFUL'
              and observations['argument_statuses'] == ['ENTAILS_CONDITIONALLY'],
            'controlled_auditor_executed': controlled is not None}


def clean_environment():
    env = {k: v for k, v in os.environ.items() if k in {'PATH', 'LANG', 'LC_ALL', 'TMPDIR', 'SYSTEMROOT'}}
    env.update({'NOESIS_JEV_ENABLED': 'false', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1'})
    return env


def command(argv, destination, *, cwd):
    started = time.perf_counter()
    try:
        result = subprocess.run([str(x) for x in argv], cwd=cwd, env=clean_environment(), capture_output=True,
                                text=True, timeout=45)
        record = {'argv': [str(x) for x in argv], 'returncode': result.returncode,
                  'stdout': result.stdout, 'stderr': result.stderr, 'elapsed_seconds': time.perf_counter() - started}
    except subprocess.TimeoutExpired as exc:
        record = {'argv': [str(x) for x in argv], 'returncode': None, 'error': 'TIMEOUT',
                  'elapsed_seconds': time.perf_counter() - started,
                  'stdout': (exc.stdout or b'').decode() if isinstance(exc.stdout, bytes) else exc.stdout,
                  'stderr': (exc.stderr or b'').decode() if isinstance(exc.stderr, bytes) else exc.stderr}
    write(destination, record)
    if record['returncode'] != 0:
        raise ValueError('recorded subprocess failure: ' + str(destination))
    return record


def raw_far(config, destination):
    # Run a separate CLI process so startup and serialization cost is visible.
    cfg = destination / 'config.json'
    write(cfg, config)
    proc = command([sys.executable, str(AUDIT_DIR / 'full_cli.py'), str(cfg), '--output', str(destination / 'package')],
                   destination / 'command.json', cwd=ROOT)
    _, _, full_cli, field, _, _ = modules()
    verify = full_cli.verify_package(destination / 'package')
    bundle = read(destination / 'package/input.json')
    return {'elapsed_seconds': proc['elapsed_seconds'], 'claim_quotes': [x['span']['quote'] for x in bundle['claims']],
            'claims_detected': len(bundle['claims']), 'factual_verdicts': [x['verdict'] for x in field.predictions_from_far_bundle(destination / 'package')],
            'sources_retained': len(bundle['sources']), 'replay_match': verify['replay_match'],
            'semantic_mapping_verified': False}


def raw_noesis(config, question, destination, noesis_cli):
    workspace = destination / 'workspace'
    cfg = workspace / 'config.json'
    logs = []
    prefix = [str(noesis_cli), '--config', str(cfg)]
    logs.append(command([*prefix, 'init', '--root', str(workspace), '--non-interactive', '--json'], destination / 'init.json', cwd=destination))
    warnings, extracted = [], 0
    for index, source in enumerate([config['source'], *config.get('evidence_sources', [])]):
        path = destination / ('source-' + str(index) + '.txt')
        path.write_text(source['text'])
        log = command([*prefix, 'ingest', str(path), '--domain', 'local', '--json'], destination / ('ingest-' + str(index) + '.json'), cwd=destination)
        logs.append(log)
        payload = json.loads(log['stdout'])['data']['processing']
        warnings.extend(payload.get('warnings', [])); extracted += payload.get('claims_indexed', 0)
    log = command([*prefix, 'ask', question, '--domain', 'local', '--format', 'json'], destination / 'ask.json', cwd=destination)
    logs.append(log)
    answer = json.loads(log['stdout'])['data']['data']
    bundle_path = destination / 'answer.bundle.json'
    logs.append(command([*prefix, 'export', 'answer', '--domain', 'local', '--question', question,
                         '--include-private', '--output', str(bundle_path), '--json'], destination / 'export.json', cwd=destination))
    verification = command([*prefix, 'verify', str(bundle_path), '--json'], destination / 'verify.json', cwd=destination)
    logs.append(verification)
    verified = json.loads(verification['stdout'])
    if verified.get('valid') is not True:
        raise ValueError('Noesis evidence bundle did not verify')
    # These are extractive evidence verdicts, not external world-truth labels.
    statements = answer.get('statements', [])
    return {'elapsed_seconds': sum(x['elapsed_seconds'] for x in logs), 'claims_detected': extracted,
            'claim_quotes': [s['text'] for s in statements if s.get('claim_id')],
            'evidence_bundle_verified': True, 'answer_status': answer.get('answer_status'), 'reported_verdicts': [s.get('verdict') for s in statements],
            'world_truth_verdicts': [], 'degradation_warnings': warnings,
            'documents_considered': answer.get('evidence_plan', {}).get('documents_considered'),
            'scope': 'MINIMAL_MODEL_FREE_CONFIG_NOT_FULL_NOESIS_CAPABILITY'}


def raw_pair(case, output, noesis_cli, *, question=None):
    output = Path(output).resolve()
    config = json.loads(json.dumps(case['config']))
    config.pop('proposal', None); config['proposal_mode'] = 'heuristic'
    output.mkdir(parents=True)
    # Identical document bytes in both conditions, without a FAR-only formalization.
    write(output / 'common-input.json', config)
    far = raw_far(config, output / 'far')
    (output / 'noesis').mkdir()
    noesis = raw_noesis(config, question or 'Identify the checkable claims and the reasoning errors in the supplied documents.', output / 'noesis', noesis_cli)
    references = [c['quote'] for c in case.get('config', {}).get('proposal', {}).get('claims', [])]
    for result in [far, noesis]:
        result['reference_claims'] = len(references)
        result['exact_reference_quote_hits'] = sum(x in result['claim_quotes'] for x in references)
        result['reference_claim_recall'] = (result['exact_reference_quote_hits'] / len(references)) if references else None
        result['external_api_usd'] = 0
        result['fully_attributed_compute_and_human_usd'] = None
        result['human_reviewer_corrections'] = None
    return {'case_id': case['case_id'], 'common_input_sha256': sha(canonical(config)), 'far': far, 'noesis': noesis}


def artifact_inventory(output):
    output = Path(output)
    return {str(p.relative_to(output)): sha(p.read_bytes()) for p in sorted(output.rglob('*'))
            if p.is_file() and 'workspace' not in p.relative_to(output).parts
            and p.name != 'artifact-manifest.json'}


def run(registration, output, noesis_cli):
    manifest, corpus = validate_registration(registration)
    head = subprocess.check_output(['git', '-C', manifest['noesis_root'], 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', manifest['noesis_root'], 'status', '--porcelain', '--untracked-files=no'], text=True)
    if head != manifest['noesis_commit'] or dirty or sha(Path(noesis_cli).read_bytes()) != manifest['noesis_cli_sha256']:
        raise ValueError('comparator source or executable drift')
    output = Path(output).resolve()
    if output.exists(): raise ValueError('run exists; preserve outcomes')
    output.mkdir(parents=True)
    write(output / 'registration-copy.json', manifest)
    started = datetime.now(timezone.utc).isoformat()
    engine, *_ = modules()
    results = {'schema': 'far-internal-exploratory-results/1', 'status': 'IN_PROGRESS', 'started_at': started,
               'registration_sha256': sha(Path(registration).read_bytes()), 'external_verification': 'DEFERRED_BY_USER',
               'source_to_report': [], 'formal': [], 'raw_comparison': [], 'history': [], 'failures': [],
               'independent_factual_accuracy': None, 'customer_advantage': None}
    def checkpoint(): write(output / 'results.json', results)
    checkpoint()
    for row in corpus['source_to_report']:
        try:
            r = pipeline_case(row, output / 'source-to-report' / row['case_id'])
            results['source_to_report'].append(r)
            if not all(r['checks'].values()): results['failures'].append({'case_id': row['case_id'], 'checks': r['checks']})
        except Exception as exc:
            results['failures'].append({'case_id': row['case_id'], 'error': type(exc).__name__ + ': ' + str(exc)})
        checkpoint()
    for row in corpus['formal_comparison']:
        tick = time.perf_counter(); ours = engine.entailment(row['premises'], row['conclusion']); far_time = time.perf_counter() - tick
        tick = time.perf_counter(); theirs = sym_status(row['premises'], row['conclusion']); sym_time = time.perf_counter() - tick
        abstained = ours['status'].startswith('NOT_CHECKED')
        witness_ok = checked_witness(row['premises'], row['conclusion'], ours['countermodel']) if ours['status'] == 'DOES_NOT_ENTAIL' else None
        r = {'case_id': row['case_id'], 'kind': row['kind'], 'reference_status': row['reference_status'],
             'far': ours, 'sympy_status': theirs, 'far_abstained': abstained,
             'countermodel_verified_with_sympy_substitution': witness_ok,
             'far_elapsed_seconds': far_time, 'sympy_elapsed_seconds': sym_time,
             'same_status': ours['status'] == theirs}
        results['formal'].append(r)
        if theirs != row['reference_status'] or (not abstained and ours['status'] != theirs) or witness_ok is False:
            results['failures'].append({'case_id': row['case_id'], 'error': 'formal disagreement or invalid witness'})
        checkpoint()
    for row in corpus['source_to_report']:
        if row['case_id'] not in corpus['raw_comparison_case_ids']: continue
        try: results['raw_comparison'].append(raw_pair(row, output / 'raw' / row['case_id'], noesis_cli))
        except Exception as exc: results['failures'].append({'case_id': row['case_id'], 'raw_error': str(exc)})
        checkpoint()
    for pair in corpus['history_pairs']:
        conditions = []
        for retained in [False, True]:
            case = {'case_id': pair['id'] + ('-retained' if retained else '-fresh'), 'config': {
                'investigation_id': pair['id'], 'captured_at': '2026-10-26T12:00:00Z',
                'source': {'kind': 'text', 'text': pair['followup_text']},
                'evidence_sources': [{'kind': 'text', 'text': pair['prior_text']}] if retained else []}}
            try: conditions.append(raw_pair(case, output / 'history' / case['case_id'], noesis_cli, question=pair['question']))
            except Exception as exc: results['failures'].append({'case_id': case['case_id'], 'history_error': str(exc)})
        results['history'].append({'pair_id': pair['id'], 'conditions': conditions,
              'treatment': 'same retained source bytes made available to both callers; not automatic FAR memory',
              'customer_value_established': False})
        checkpoint()
    results['status'] = 'COMPLETED_WITH_RECORDED_FAILURES' if results['failures'] else 'COMPLETED_INTERNAL_EXPLORATORY'
    results['finished_at'] = datetime.now(timezone.utc).isoformat()
    results['interpretation'] = {'formal_conditionals_do_not_verify_semantics': True,
        'noesis_missing_classifier_is_not_a_far_win': True, 'commercial_advantage_established': False,
        'unrun_commercial_arms_are_missing_not_losses': True}
    checkpoint()
    write(output / 'artifact-manifest.json', {'schema': 'far-internal-run-artifacts/1',
          'files': artifact_inventory(output)})
    return results


def verify_run(output):
    output = Path(output).resolve()
    manifest = read(output / 'artifact-manifest.json')
    actual = set(artifact_inventory(output))
    if set(manifest['files']) != actual:
        raise ValueError('incomplete artifact manifest')
    results = read(output / 'results.json')
    registration = read(output / 'registration-copy.json')
    if ([r['case_id'] for r in results['source_to_report']] != registration['source_case_ids']
            or [r['case_id'] for r in results['formal']] != registration['formal_case_ids']):
        raise ValueError('missing or substituted case output')
    for name, expected in manifest['files'].items():
        path = (output / name).resolve()
        if not path.is_relative_to(output) or sha(path.read_bytes()) != expected:
            raise ValueError('recorded output drift: ' + name)
    _, _, full_cli, _, _, _ = modules()
    packages = list((output / 'source-to-report').glob('*/manifest.json')) + list(output.glob('raw/*/far/package/manifest.json')) + list(output.glob('history/*/far/package/manifest.json'))
    for path in packages:
        if not full_cli.verify_package(path.parent)['replay_match']: raise ValueError('package replay failed')
    engine, _, _, _, independent, _ = modules()
    controlled = list((output / 'source-to-report').glob('*-controlled-auditor.json'))
    for path in controlled:
        record = read(path)
        if engine.audit(record['input']) != record['audit']:
            raise ValueError('controlled auditor replay failed')
        independent.check_report(record['input'], record['audit'])
    return {'verified_files': len(manifest['files']), 'far_packages_replayed': len(packages),
            'controlled_audits_replayed': len(controlled),
            'external_independence': False, 'scope': 'retained bytes and software replay only'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    f = sub.add_parser('freeze'); f.add_argument('--output', type=Path, required=True); f.add_argument('--noesis-root', type=Path, required=True); f.add_argument('--predecessor', type=Path)
    r = sub.add_parser('run'); r.add_argument('--registration', type=Path, required=True); r.add_argument('--output', type=Path, required=True); r.add_argument('--noesis-cli', type=Path, required=True)
    v = sub.add_parser('verify'); v.add_argument('output', type=Path)
    args = p.parse_args()
    try:
        if args.command == 'freeze': value = freeze(args.output, args.noesis_root, args.predecessor)
        elif args.command == 'run': value = run(args.registration, args.output, args.noesis_cli)
        else: value = verify_run(args.output)
        print(json.dumps(value if args.command != 'run' else {'status': value['status'], 'failures': value['failures']}, indent=2))
        return int(args.command == 'run' and bool(value['failures']))
    except (ValueError, OSError, KeyError, ImportError) as exc:
        print('INTERNAL_EVALUATION_FAILED: ' + str(exc), file=sys.stderr); return 2


if __name__ == '__main__': raise SystemExit(main())
