#!/usr/bin/env python3
"""Deduplicated operational dispositions over existing source identities; no promotion."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit
from run_living_research import normalize_doi

ROOT = Path(__file__).resolve().parents[1]
FOLDER = Path('research/scheduled-task-reconciliation')


def encoded(value):
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False).encode() + b'\n'


def sha(raw): return hashlib.sha256(raw).hexdigest()


def read(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise ValueError('duplicate key: ' + key)
            result[key] = value
        return result
    return json.loads(Path(path).read_text(), object_pairs_hook=unique)


def identity(value):
    """Work-level deduplication hint; explicit versions never become content proof."""
    if not isinstance(value, str) or not value.strip(): raise ValueError('source locator missing')
    raw = value.strip()
    if raw.lower().startswith('doi:') or raw.lower().startswith('10.'):
        doi = normalize_doi(raw[4:] if raw.lower().startswith('doi:') else raw)
        if not doi or not re.fullmatch(r'10\.[0-9]+/\S+', doi): raise ValueError('invalid DOI locator')
        if doi.startswith('10.48550/arxiv.'): raw = 'arxiv:' + doi.split('arxiv.', 1)[1]
        else: return 'doi:' + doi, None
    if raw.lower().startswith('arxiv:'):
        ident = raw[6:]
    else:
        url = urlsplit(raw)
        if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password:
            raise ValueError('invalid public source URL')
        host = url.hostname.lower()
        if host in ('doi.org', 'dx.doi.org'):
            return identity('doi:' + unquote(url.path.lstrip('/')))
        if host in ('arxiv.org', 'www.arxiv.org', 'export.arxiv.org') and url.path.startswith(('/abs/', '/pdf/', '/html/')):
            ident = url.path.split('/', 2)[2].removesuffix('.pdf')
        else:
            query = urlencode([(k, v) for k, v in parse_qsl(url.query, keep_blank_values=True)
                               if not k.lower().startswith('utm_') and k.lower() not in ('fbclid', 'gclid')])
            path = url.path.rstrip('/')
            if host == 'github.com' and len(path.strip('/').split('/')) == 2:
                path = path.removesuffix('.git').lower()
            return 'url:' + urlunsplit((url.scheme.lower(), host + (':' + str(url.port) if url.port else ''), path, query, '')), None
    match = re.fullmatch(r'([A-Za-z0-9./_-]+?)(v[1-9][0-9]*)?', ident)
    if not match or not re.fullmatch(r'(?:[0-9]{4}\.[0-9]{4,5}|[A-Za-z.-]+/[0-9]{7})', match[1]):
        raise ValueError('invalid arXiv identifier')
    return 'arxiv:' + match[1].lower(), match[2]


def validate_operations(operations, source_ids):
    if operations.get('schema') != 'far-research-operations/1' or operations.get('status') != 'Research':
        raise ValueError('invalid operational register')
    if operations.get('scientific_promotion_authority') is not False or operations.get('external_verification') != 'DEFERRED_BY_USER':
        raise ValueError('operational data cannot promote evidence or resume external verification')
    rows = operations.get('entries')
    if not isinstance(rows, list): raise ValueError('missing dispositions')
    ids = [row.get('source_id') for row in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(source_ids):
        raise ValueError('every intake source needs exactly one operational disposition')
    for row in rows:
        for field in ['owner_role', 'classification', 'disposition', 'next_test', 'exit_condition', 'evidence_limit']:
            if not isinstance(row.get(field), str) or not row[field].strip(): raise ValueError('missing ' + field)
        if row['classification'] not in ('RESEARCH_SIGNAL', 'COMMERCIAL_SIGNAL', 'ARCHITECTURAL_COUNTEREXAMPLE'):
            raise ValueError('unrecognized signal class')
        if row.get('source_evidence_promoted') is not False:
            raise ValueError('source promotion requires existing governed lifecycle')
        if row['classification'] == 'ARCHITECTURAL_COUNTEREXAMPLE':
            witness = row.get('architectural_witness', {})
            for key in ['baseline_anchor', 'failed_representation', 'extension_point_insufficiency', 'strongest_counterargument', 'reproducer']:
                if not isinstance(witness.get(key), str) or not witness[key].strip(): raise ValueError('architectural alert lacks ' + key)
    return rows


def compile_register(root=ROOT):
    root = Path(root)
    manifest_path = root/FOLDER/'current.json'
    manifest = read(manifest_path) if manifest_path.exists() else {'intakes':['intake-2026-10-20.json'],'operations':'operations-v1.json','index':'operations-index-v1.json'}
    def member(name):
        if not isinstance(name,str) or Path(name).name != name or not name.endswith('.json'):
            raise ValueError('register manifest requires local JSON filenames')
        return root/FOLDER/name
    if not isinstance(manifest.get('intakes'),list) or not manifest['intakes'] or len(set(manifest['intakes'])) != len(manifest['intakes']):
        raise ValueError('intake files must be a nonempty unique list')
    intake_paths = [member(x) for x in manifest['intakes']]
    ops_path = member(manifest['operations']); member(manifest['index'])
    operations = read(ops_path)
    sources = [s for path in intake_paths for s in read(path)['entries']]; ids = [s['id'] for s in sources]
    if len(ids) != len(set(ids)): raise ValueError('duplicate intake identity')
    rows = {x['source_id']: x for x in validate_operations(operations, ids)}
    aliases, inventory = {}, []
    candidates = sorted((root/'research/living/inbox/candidates').glob('FAR-LIT-*.json'))
    corpus_path = root/'research/corpus/corpus-v1.0.json'
    corpus = read(corpus_path)
    for path in candidates:
        record = read(path); inventory.append([str(path.relative_to(root)), sha(path.read_bytes())])
        locators = [record.get('source_key'), record.get('source', {}).get('doi'), record.get('source', {}).get('url')]
        for locator in locators:
            if not locator: continue
            try: work, version = identity(locator)
            except ValueError: continue
            aliases.setdefault(work, []).append({'kind': 'untrusted_living_candidate', 'path': str(path.relative_to(root)), 'version': version})
    for record in corpus['sources']:
        locator = record.get('external_identifier')
        if not locator: continue
        try: work, version = identity(locator)
        except ValueError: continue
        aliases.setdefault(work, []).append({'kind': 'existing_governed_corpus_source', 'source_id': record['id'], 'version': version})
    groups = {}
    for source in sources:
        work, version = identity(source['primary_url'])
        group = groups.setdefault(work, {'work_key': work, 'version_observations': [], 'operational_observations': [], 'existing_identity_links': []})
        version_record = {'intake_id': source['id'], 'version': version or 'UNSPECIFIED',
                          'primary_url': source['primary_url'], 'evidence_class': source['evidence_class'],
                          'source_scope': 'intake metadata, not newly verified primary bytes'}
        group['version_observations'].append(version_record)
        group['operational_observations'].append(rows[source['id']])
        linked = {json.dumps(x, sort_keys=True): x for x in aliases.get(work, [])}
        group['existing_identity_links'] = [linked[k] for k in sorted(linked)]
    return {'schema': 'far-research-operations-index/1', 'status': 'Research',
            'scientific_promotion_authority': False, 'external_verification': 'DEFERRED_BY_USER',
            'input_hashes': {'intakes': {str(path.relative_to(root)):sha(path.read_bytes()) for path in intake_paths}, 'operations': sha(ops_path.read_bytes()),
                             'corpus': sha(corpus_path.read_bytes()), 'candidate_inventory': sha(encoded(inventory))},
            'coverage': {'intake_sources': len(sources), 'deduplicated_work_keys': len(groups),
                         'living_candidate_files_inspected': len(candidates), 'complete_historical_scheduler_outputs': False,
                         'primary_content_verification_complete': False},
            'identity_limit': 'Normalized locators join existing identities; they do not prove equal content, versions, correctness or independence.',
            'groups': [groups[k] for k in sorted(groups)]}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--write', action='store_true'); args = p.parse_args()
    try:
        result = compile_register()
        manifest_path = ROOT/FOLDER/'current.json'
        output_name = read(manifest_path)['index'] if manifest_path.exists() else 'operations-index-v1.json'
        path = ROOT/FOLDER/output_name
        raw = encoded(result)
        if args.write: path.write_bytes(raw)
        elif not path.exists() or path.read_bytes() != raw: raise ValueError('operational index stale; regenerate intentionally with --write')
        print(json.dumps({'source_records': result['coverage']['intake_sources'], 'work_keys': len(result['groups']), 'mode': 'write' if args.write else 'check', 'promotion': False}))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print('RESEARCH_OPERATIONS_INVALID: ' + str(exc)); return 2


if __name__ == '__main__': raise SystemExit(main())
