#!/usr/bin/env python3
"""Read-only pre-review invariant traceability check; not a correctness oracle.

Run from protected main in the existing required PR workflow. The only candidate
input is PR metadata and read-only contents addressed by the exact PR head SHA.
"""
from __future__ import annotations

import argparse
import ast
import base64
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.pr_review_convergence import api, paginate

# The preflight contract is introduced through a protected PR. Earlier open
# PRs retain their historical review obligations without surprise CI changes.
CUTOVER = '2026-11-10T00:00:00Z'
START = '<!-- FAR-INVARIANTS-V1\n'
END = '\nFAR-INVARIANTS-END -->'
IDENTIFIER = re.compile(r'[A-Z][A-Z0-9]*(?:-[A-Z0-9]+){1,8}\Z')
TEST_REFERENCE = re.compile(r'(?P<path>(?:tests/|[^/]+/tests/)[A-Za-z0-9_./-]+\.(?:py|rs|go|js|ts))::(?P<name>test_[A-Za-z0-9_]+)\Z')
CODE_SUFFIXES = {'.py', '.rs', '.go', '.js', '.jsx', '.ts', '.tsx', '.sh', '.c', '.cc', '.cpp', '.h', '.java', '.rb', '.jl', '.lean', '.sql'}
SPECIAL_FILES = {'AGENTS.md', 'CLAUDE.md', 'pyproject.toml', 'Cargo.toml', 'Cargo.lock', 'go.mod', 'go.sum', 'Dockerfile', 'Makefile', 'requirements.txt', '.github/pull_request_template.md'}
SOFTWARE_CONFIG = {'.json', '.yml', '.yaml', '.toml'}


def _date(value: str) -> datetime:
    if type(value) is not str:
        raise ValueError('created_at must be a timestamp')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed) or parsed.tzinfo is None:
        raise ValueError('created_at must include UTC timezone')
    return parsed


def is_implementation_path(path: str) -> bool:
    if type(path) is not str or path.startswith('/') or '..' in Path(path).parts:
        return False
    if path in SPECIAL_FILES or path.startswith('.github/workflows/') or path.startswith('.github/actions/'):
        return True
    if path.startswith('schemas/') and Path(path).suffix in SOFTWARE_CONFIG:
        return True
    if path.startswith('docs/governance/') and path.endswith('pr-review-convergence.md'):
        return True
    if path.startswith('tests/') or '/tests/' in path:
        return False
    if path.endswith('.lock') or Path(path).name.startswith('requirements-') and path.endswith('.txt'):
        return True
    return Path(path).suffix in CODE_SUFFIXES


def parse_contract(body: object) -> dict:
    if type(body) is not str or body.count(START) != 1 or body.count(END) != 1:
        raise ValueError('exactly one FAR-INVARIANTS-V1 block required in PR description')
    fragment = body.split(START, 1)[1].split(END, 1)[0]
    if '<!-- FAR-INVARIANTS-V1' in fragment or 'FAR-INVARIANTS-END' in fragment:
        raise ValueError('nested or ambiguous invariant block')

    def unique(pairs):
        data = {}
        for key, value in pairs:
            if key in data:
                raise ValueError('duplicate contract JSON key: ' + key)
            data[key] = value
        return data

    payload = json.loads(fragment, object_pairs_hook=unique, parse_constant=lambda v: (_ for _ in ()).throw(ValueError('nonfinite JSON value')))
    if type(payload) is not dict:
        raise ValueError('contract must be an object')
    return payload


def _text(x: object, minimum: int = 12) -> bool:
    return type(x) is str and len(x.strip()) >= minimum and '\x00' not in x


def _valid_test_ref(reference: object) -> tuple[str, str] | None:
    if type(reference) is not str:
        return None
    match = TEST_REFERENCE.fullmatch(reference)
    if match is None:
        return None
    path = match['path']
    if '..' in Path(path).parts or '/./' in path:
        return None
    return path, match['name']


def test_defined(path: str, name: str, source: str) -> bool:
    if not isinstance(source, str) or len(source) > 1_000_000:
        return False
    if path.endswith('.py'):
        try:
            tree = ast.parse(source)
        except (SyntaxError, ValueError):
            return False
        return any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and node.name == name for node in ast.walk(tree))
    # For non-Python tests, this is only existence of the named symbol, not proof
    # it is executable by any particular runner.
    return re.search(r'(?<!\w)' + re.escape(name) + r'(?!\w)', source) is not None


def evaluate(pr: dict, changed_files: list[dict], read_file, *, cutoff: str = CUTOVER) -> dict:
    """Pure checker. read_file(path, exact_head)-> text or None. No code execution."""
    problems = []
    if type(pr) is not dict or type(pr.get('number')) is not int or type(pr.get('head')) is not dict:
        raise ValueError('invalid PR metadata')
    head = pr['head'].get('sha')
    if type(head) is not str or re.fullmatch(r'[a-f0-9]{40}', head) is None:
        raise ValueError('invalid exact PR head')
    if pr.get('base', {}).get('ref') != 'main' or pr.get('state') != 'open':
        raise ValueError('expected open main-targeting PR')
    if type(changed_files) is not list or any(type(f) is not dict or type(f.get('filename')) is not str for f in changed_files):
        raise ValueError('incomplete changed-file inventory')
    if type(pr.get('changed_files')) is not int or len(changed_files) != pr['changed_files']:
        raise ValueError('changed-file inventory count mismatch; cannot silently omit paths')
    paths = sorted({f['filename'] for f in changed_files if f.get('status') != 'removed'})
    affected = {p for p in paths if is_implementation_path(p)}
    result = {'schema': 'far-pr-invariant-preflight/1', 'pr': pr['number'], 'head_sha': head,
              'base_sha': pr['base'].get('sha'), 'implementation_paths': sorted(affected),
              'contracts_checked': 0, 'mode': 'enforce', 'valid': False,
              'software_correctness_verified': False, 'independent_review_verified': False,
              'required_protected_checks_verified': False, 'errors': problems}
    created = _date(pr.get('created_at'))
    if created < _date(cutoff):
        result.update(mode='historical-pr', valid=True)
        return result
    if pr.get('draft') is True:
        result.update(mode='draft-deferred', valid=True)
        return result
    if not affected:
        result.update(mode='documentation-only', valid=True)
        return result
    try:
        data = parse_contract(pr.get('body'))
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        problems.append(str(exc))
        return result
    if set(data) != {'version', 'scope', 'invariants', 'limitations'} or data['version'] != 1:
        problems.append('contract schema keys/version invalid')
        return result
    if not _text(data.get('scope'), 20) or not isinstance(data.get('limitations'), list) or not data['limitations'] or any(not _text(x, 15) for x in data['limitations']):
        problems.append('scope and explicit limitations required')
    rows = data.get('invariants')
    if type(rows) is not list or not rows:
        problems.append('nonempty invariants array required')
        return result
    tested = set()
    covered = set()
    seen_ids = set()
    for i, row in enumerate(rows):
        tag = f'invariants[{i}]'
        if type(row) is not dict or set(row) != {'id', 'statement', 'boundary', 'changed_paths', 'failure_modes', 'positive_control', 'integration_control', 'assurance_limit'}:
            problems.append(tag + ': exact invariant fields required')
            continue
        ident = row['id']
        if type(ident) is not str or not IDENTIFIER.fullmatch(ident) or ident in seen_ids:
            problems.append(tag + ': invalid or duplicate invariant ID')
        seen_ids.add(ident)
        if not _text(row['statement'], 35) or not _text(row['boundary'], 15) or not _text(row['assurance_limit'], 20):
            problems.append(tag + ': statement, trust boundary, and assurance limit must be explicit')
        entries = row['changed_paths']
        if type(entries) is not list or not entries or any(type(p) is not str for p in entries):
            problems.append(tag + ': must cover nonempty changed implementation paths')
        else:
            if len(set(entries)) != len(entries) or not set(entries) <= affected:
                problems.append(tag + ': paths must be unique changed implementation paths')
            covered.update(entries)
        modes = row['failure_modes']
        if type(modes) is not list or len(modes) < 2:
            problems.append(tag + ': at least two distinct counterexample modes required')
        else:
            seen_modes = set()
            for j, item in enumerate(modes):
                if type(item) is not dict or set(item) != {'case', 'test'} or not _text(item.get('case') if type(item) is dict else None, 20):
                    problems.append(f'{tag}.failure_modes[{j}]: case description and test required')
                    continue
                if item['case'] in seen_modes:
                    problems.append(tag + ': duplicate failure case')
                seen_modes.add(item['case'])
                tested.add(item['test'])
        tested.add(row['positive_control'])
        tested.add(row['integration_control'])
        result['contracts_checked'] += 1
    if covered != affected:
        problems.append('changed implementation paths missing invariant coverage: ' + ', '.join(sorted(affected - covered)))
    valid_refs = {}
    for reference in tested:
        parsed = _valid_test_ref(reference)
        if parsed is None:
            problems.append('invalid test reference: ' + repr(reference))
        else:
            valid_refs[reference] = parsed
    cache = {}
    for reference, (path, name) in sorted(valid_refs.items()):
        if path not in cache:
            try:
                cache[path] = read_file(path, head)
            except Exception as exc:
                problems.append(path + ': unable to verify test at head: ' + type(exc).__name__)
                cache[path] = None
        if not test_defined(path, name, cache[path]):
            problems.append(reference + ': test symbol not present in exact-head file')
    result['valid'] = not problems
    result['test_references_checked'] = len(valid_refs)
    return result


def check_live(repo: str, number: int, expected_head: str, token: str) -> dict:
    if re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo) is None:
        raise ValueError('invalid repository identity')
    if type(number) is not int or number <= 0 or re.fullmatch(r'[a-f0-9]{40}', expected_head) is None:
        raise ValueError('invalid PR number or expected head')
    base = 'https://api.github.com/repos/' + repo
    pr = api(f'{base}/pulls/{number}', token)
    if pr['head']['sha'] != expected_head:
        raise ValueError('PR moved before preflight')
    # Existing PRs and drafts must not depend on a new file-list API or the
    # contract introduced after their creation. Still recheck their head.
    phase = 'historical-pr' if _date(pr.get('created_at')) < _date(CUTOVER) else (
        'draft-deferred' if pr.get('draft') is True else None)
    if phase:
        if api(f'{base}/pulls/{number}', token)['head']['sha'] != expected_head:
            raise ValueError('PR moved during preflight')
        return {'schema': 'far-pr-invariant-preflight/1', 'pr': number,
                'head_sha': expected_head, 'base_sha': pr.get('base', {}).get('sha'),
                'implementation_paths': [], 'contracts_checked': 0,
                'mode': phase, 'valid': True, 'errors': [],
                'software_correctness_verified': False,
                'independent_review_verified': False,
                'required_protected_checks_verified': False}
    changed_files = paginate(f'{base}/pulls/{number}/files', token)

    def read_file(path, head):
        encoded = quote(path, safe='/')
        response = api(f'{base}/contents/{encoded}?ref={head}', token)
        if type(response) is not dict or response.get('encoding') != 'base64' or type(response.get('content')) is not str or response.get('size', 0) > 1_000_000:
            return None
        return base64.b64decode(response['content'], validate=False).decode('utf-8')

    result = evaluate(pr, changed_files, read_file)
    if api(f'{base}/pulls/{number}', token)['head']['sha'] != expected_head:
        raise ValueError('PR moved during preflight')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--repository', required=True)
    parser.add_argument('--pr', type=int, required=True)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args(argv)
    try:
        result = check_live(arguments.repository, arguments.pr, arguments.expected_head, os.environ['GH_TOKEN'])
    except (ValueError, KeyError, OSError) as exc:
        result = {'schema': 'far-pr-invariant-preflight/1', 'valid': False, 'errors': [str(exc)],
                  'head_sha': arguments.expected_head, 'software_correctness_verified': False}
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(result, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, sort_keys=True))
    return 0 if result['valid'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
