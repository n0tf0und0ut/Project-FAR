#!/usr/bin/env python3
"""One-shot research proof: queue -> real local model -> verified PR proposal.

This is intentionally NOT a production software factory, and makes no claim of
protected delivery or independent agent identity without external GitHub data.
The CLI only runs on protected main; no model-generated Python runs on the host.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

from tools.software_factory import Factory, FactoryError, canonical
from tools.factory_zero_key_smoke import (
    MODEL, MODEL_DIGEST, SmokeError, git, grade_in_docker,
    grader_image_id, sha, strict_json,
)

REPO = 'n0tf0und0ut/Project-FAR'
SOURCE = 'tools/software_factory.py'
HOLDOUT = 'research/factory-evaluation/claim-parameter-holdout.py.txt'
TEST = 'tests/test_factory_claim_contract.py'
PRESERVATION_HOLDOUT = 'research/factory-evaluation/claim-preservation-oracle.py.txt'
PRESERVATION_TEST = 'tests/test_factory_claim_preservation.py'
PRESERVATION_SHA256 = '104f24eeaede44a6f25bf16e2910c2512a7c21150646c1ebd66f06d88901cb51'
ORACLE_SHA256 = '73a34c32a4ea99576fd2ee65121406eae57406528a1bdc3f3b13822b2877b0b4'
SCHEMA = 'far-software-factory/autonomous-source-proposal/1'
WORKER = 'qwen-local-model'
MAX_BYTES = 20000


def hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_oracle(root: Path) -> bytes:
    p = root / HOLDOUT
    raw = p.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ORACLE_SHA256:
        raise SmokeError('frozen oracle SHA-256 changed')
    return raw


def check_preservation(root: Path) -> bytes:
    raw = (root / PRESERVATION_HOLDOUT).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PRESERVATION_SHA256:
        raise SmokeError('frozen preservation oracle SHA-256 changed')
    return raw


def work_order(base_sha: str) -> dict:
    if re.fullmatch('[a-f0-9]{40}', base_sha) is None:
        raise SmokeError('invalid exact base SHA')
    return {'schema': 'far-software-factory/work-order/1',
            'id': 'claimcontract', 'repository': REPO, 'base_sha': base_sha,
            'tasks': [{'id': 'repair',
                       'objective': 'Reject invalid claim lease parameter types without consuming a lease',
                       'acceptance': [
                           'ttl and max_attempts must be exact positive integers (bool is invalid)',
                           'ttl maximum 86400 seconds and existing worker validation unchanged',
                           'invalid input preserves SQLite state and lease history',
                           'independent frozen four-test oracle passes'],
                       'depends_on': []}]}


def claim_guard(source: str) -> tuple[str, str]:
    tree = ast.parse(source)
    classes = [x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == 'Factory']
    if len(classes) != 1:
        raise SmokeError('ambiguous factory class')
    functions = [x for x in classes[0].body if isinstance(x, ast.FunctionDef) and x.name == 'claim']
    if len(functions) != 1 or not isinstance(functions[0].body[0], ast.If):
        raise SmokeError('missing exact first claim guard')
    f = functions[0]
    guard = f.body[0]
    if guard.lineno != guard.test.end_lineno or guard.lineno != guard.test.lineno:
        raise SmokeError('multiline guard not allowed in bounded proof')
    lines = source.splitlines(keepends=True)
    old = lines[guard.lineno - 1]
    if not old.startswith('        if ') or not old.rstrip('\r\n').endswith(':'):
        raise SmokeError('unexpected guard formatting')
    snippet = ''.join(lines[f.lineno - 1:f.end_lineno])
    if len(snippet.encode('utf-8')) > 5500:
        raise SmokeError('oversized method snippet')
    return old, snippet


def replace_claim_guard(source: str, proposal: object) -> str:
    old, _ = claim_guard(source)
    if type(proposal) is not str or len(proposal) > 650 or any(c in proposal for c in '\r\n\x00'):
        raise SmokeError('model proposed invalid single physical line')
    if proposal.startswith('if '):
        proposal = '        ' + proposal
    if not proposal.startswith('        if ') or not proposal.endswith(':'):
        raise SmokeError('model proposal is not a Python if-guard line')
    if proposal + ('\r\n' if old.endswith('\r\n') else '\n') == old:
        raise SmokeError('model did not change the defective guard')
    lines = source.splitlines(keepends=True)
    matches = [i for i, line in enumerate(lines) if line == old]
    if len(matches) != 1:
        raise SmokeError('ambiguous original guard identity')
    lines[matches[0]] = proposal + ('\r\n' if old.endswith('\r\n') else '\n')
    updated = ''.join(lines)
    ast.parse(updated)
    if len(updated) > len(source) + 500:
        raise SmokeError('model proposal unusually large')
    return updated


def ask_model(prompt: str, output: Path) -> tuple[str, dict]:
    if len(prompt.encode()) > 7000:
        raise SmokeError('oversized model prompt')
    request = {
        'model': MODEL, 'stream': False, 'keep_alive': '5m', 'format': 'json',
        'options': {'temperature': 0, 'seed': 0, 'num_ctx': 2048, 'num_predict': 220},
        'messages': [
            {'role': 'system', 'content': 'You are a Python coding worker. Respond only as JSON with exactly one string key "line" holding the corrected complete if statement. Preserve all existing checks. No Markdown, no extra text.'},
            {'role': 'user', 'content': prompt},
        ],
    }
    payload = json.dumps(request, separators=(',', ':'), sort_keys=True).encode()
    (output / 'model-request-sha256.txt').write_text(sha(payload) + '\n')
    req = urllib.request.Request('http://127.0.0.1:11434/api/chat', data=payload,
                                 headers={'Content-Type': 'application/json'}, method='POST')
    started = time.monotonic()
    with urllib.request.urlopen(req, timeout=150) as response:
        raw = response.read(MAX_BYTES + 1)
    (output / 'model-transport.json').write_bytes(raw)  # PRESERVE before parsing
    if len(raw) > MAX_BYTES:
        raise SmokeError('oversized model response')
    body = strict_json(raw)
    if (type(body) is not dict or body.get('done') is not True
            or body.get('model') != MODEL or type(body.get('message')) is not dict
            or type(body['message'].get('content')) is not str
            or type(body.get('eval_count')) is not int or body['eval_count'] < 1
            or type(body.get('prompt_eval_count')) is not int or body['prompt_eval_count'] < 1):
        raise SmokeError('missing genuine completed generation evidence')
    content = body['message']['content'].encode('utf-8')
    (output / 'model-content.json').write_bytes(content)
    metadata = {'model': body['model'], 'input_tokens': body['prompt_eval_count'],
                'output_tokens': body['eval_count'], 'transport_sha256': sha(raw),
                'content_sha256': sha(content), 'duration_seconds': round(time.monotonic()-started, 3),
                'request_sha256': sha(payload)}
    (output / 'model-generation.json').write_text(json.dumps(metadata, sort_keys=True, indent=2) + '\n')
    decoded = strict_json(content)
    if type(decoded) is not dict or set(decoded) != {'line'} or type(decoded['line']) is not str:
        raise SmokeError('model must return only JSON line string')
    return decoded['line'], metadata


def grade_with_oracle(checkout: Path, oracle: bytes, output: Path, label: str, image: str,
                      *, target_path: str = TEST, test_module: str = 'test_factory_claim_contract') -> dict:
    p = checkout / target_path
    if p.exists() or p.is_symlink():
        raise SmokeError('frozen test path collision')
    p.write_bytes(oracle)
    try:
        return grade_in_docker(checkout, test_module, output, label, image_id=image)
    finally:
        p.unlink()


def snapshot_sanitized(factory: Factory, order_id: str) -> dict:
    # Core snapshot excludes token; never include raw SQLite/WAL in public artifacts.
    snap = factory.snapshot(order_id)
    if 'token' in canonical(snap).lower() or snap['authority'] != 'ADVISORY_ONLY':
        raise SmokeError('unsafe or misrepresented queue snapshot')
    return snap


def attempt(repo: Path, db: Path, output: Path) -> bool:
    repo, db, output = repo.resolve(), db.resolve(), output.resolve()
    if output.exists() or output.is_relative_to(repo) or db.is_relative_to(repo):
        raise SmokeError('attempt outputs and persistent queue must be outside checkout')
    if os.environ.get('GITHUB_EVENT_NAME') not in (None, 'push') or os.environ.get('GITHUB_REF') not in (None, 'refs/heads/main'):
        raise SmokeError('trusted protected main event required')
    if os.environ.get('GITHUB_REPOSITORY') not in (None, REPO):
        raise SmokeError('unexpected GitHub repository')
    base = git(repo, 'rev-parse', 'HEAD^{commit}').stdout.decode().strip()
    if os.environ.get('GITHUB_SHA') and os.environ['GITHUB_SHA'] != base:
        raise SmokeError('runner checkout differs from trusted main event')
    oracle = check_oracle(repo)
    preservation = check_preservation(repo)
    output.mkdir(mode=0o700, parents=True)
    o = work_order(base)
    (output / 'work-order.json').write_text(canonical(o)+'\n')
    f = Factory(db)
    submit = f.submit(o)
    claim = f.claim(o['id'], WORKER, ttl=3600)
    if claim is None or claim['stage'] != 'build' or claim['task_id'] != 'repair':
        raise SmokeError('no valid initial build lease')
    state = {'schema': SCHEMA, 'base_sha': base, 'repository': REPO,
             'work_order_sha256': submit['sha256'], 'oracle_sha256': sha(oracle),
             'preservation_oracle_sha256': sha(preservation),
             'worker': WORKER, 'worker_model': MODEL, 'model_digest': None,
             'source_blob': None, 'candidate_blob': None,
             'model_generation': None, 'before': None, 'after': None, 'regression': None,
             'preservation_before': None, 'preservation_after': None,
             'verdict': 'UNKNOWN', 'attempt': 1,
             'limitations': ['Model identity is local Ollama-reported and not externally signed.',
                             'Generated source is not executed on the Actions host.',
                             'Public tests and model reports do not substitute for independent PR checks.',
                             'No protected merge occurs in this model generation stage.']}
    worktree = None
    try:
        from tools.workflow_efficacy_free_agent import local_model_digest
        state['model_digest'] = local_model_digest()
        if state['model_digest'] != MODEL_DIGEST:
            raise SmokeError('model binary digest mismatch')
        image = grader_image_id()
        state['grader_image_id'] = image
        with tempfile.TemporaryDirectory(prefix='far-auto-proof-') as tmp:
            worktree = Path(tmp) / 'source'
            git(repo, 'worktree', 'add', '--detach', str(worktree), base)
            target = worktree / SOURCE
            if target.is_symlink() or not target.is_file() or target.stat().st_size > 120000:
                raise SmokeError('unsafe coding target')
            state['source_blob'] = git(worktree, 'hash-object', SOURCE).stdout.decode().strip()
            orig = target.read_text()
            old, snippet = claim_guard(orig)
            state['before'] = grade_with_oracle(worktree, oracle, output, 'before', image)
            if state['before']['state'] != 'FAIL' or state['before'].get('test_count_reported') != 4:
                raise SmokeError('baseline defect not reproduced; no model attempt allowed')
            state['preservation_before'] = grade_with_oracle(
                worktree, preservation, output, 'preservation-before', image,
                target_path=PRESERVATION_TEST, test_module='test_factory_claim_preservation')
            if (state['preservation_before']['state'] != 'PASS'
                    or state['preservation_before'].get('test_count_reported') != 3):
                raise SmokeError('existing claim validation did not pass preservation baseline')
            prompt = ("Task: Repair the existing Factory.claim first if guard. "
                      "It currently crashes on noninteger ttl/max_attempts and accepts Python booleans as lease limits. "
                      "Both ttl and max_attempts must be EXACT positive int values, not bool, float, string, None or containers. "
                      "Python isinstance(True, int) is True; reject booleans with strict type checks. "
                      "Preserve current worker name validation, ttl 1..86400 limit, and positive attempt count. "
                      "Return a complete replacement of ONLY the guard IF line in JSON with key line. "
                      "No edits to other lines, and do not add any explanatory comments.\n"
                      "Original Factory.claim function:\n"+snippet)
            proposed, metadata = ask_model(prompt, output)
            state['model_generation'] = metadata
            changed = replace_claim_guard(orig, proposed)
            target.write_text(changed)
            patch = git(worktree, 'diff', '--no-ext-diff', '--', SOURCE).stdout
            if not patch or len(patch) > 10000:
                raise SmokeError('no bounded model-generated change')
            (output / 'candidate.patch').write_bytes(patch)
            state['patch_sha256'] = sha(patch)
            modified = git(worktree, 'diff', '--name-only', 'HEAD').stdout.decode().splitlines()
            if modified != [SOURCE]:
                raise SmokeError('model modified anything beyond allowed file')
            state['candidate_blob'] = git(worktree, 'hash-object', SOURCE).stdout.decode().strip()
            state['after'] = grade_with_oracle(worktree, oracle, output, 'after', image)
            if state['after']['state'] != 'PASS' or state['after'].get('test_count_reported') != 4:
                raise SmokeError('model candidate failed frozen acceptance oracle')
            state['preservation_after'] = grade_with_oracle(
                worktree, preservation, output, 'preservation-after', image,
                target_path=PRESERVATION_TEST, test_module='test_factory_claim_preservation')
            if (state['preservation_after']['state'] != 'PASS'
                    or state['preservation_after'].get('test_count_reported') != 3):
                raise SmokeError('model proposal lost preexisting worker/lease bounds')
            state['regression'] = grade_in_docker(worktree, 'test_software_factory', output, 'regression', image_id=image)
            if state['regression']['state'] != 'PASS':
                raise SmokeError('model candidate failed factory regression suite')
            state['verdict'] = 'MODEL_PATCH_ELIGIBLE_FOR_INDEPENDENT_GITHUB_PR'
    except Exception as exc:
        # Preserve completed-model counters even when its inner JSON was rejected.
        preserved = output / 'model-generation.json'
        if state['model_generation'] is None and preserved.is_file():
            state['model_generation'] = strict_json(preserved.read_bytes())
        # Preserve failures without inventing a success; no secret exception content.
        state['verdict'] = 'MODEL_ATTEMPT_FAILED'
        state['error_type'] = type(exc).__name__
        state['failure_stage'] = str(exc)[:160] if isinstance(exc, SmokeError) else type(exc).__name__
        f.fail(o['id'], 'repair', claim['token'], 'worker failed: '+type(exc).__name__)
    finally:
        if worktree is not None:
            git(repo, 'worktree', 'remove', '--force', str(worktree), check=False)
        state['queue_snapshot'] = snapshot_sanitized(f, o['id'])
        state['artifacts_sha256'] = {p.name: hash_file(p) for p in sorted(output.iterdir()) if p.is_file()}
        (output / 'attempt-receipt.json').write_text(json.dumps(state, indent=2, sort_keys=True)+'\n')
    return state['verdict'] == 'MODEL_PATCH_ELIGIBLE_FOR_INDEPENDENT_GITHUB_PR'


def _run(*args: str, cwd: Path) -> str:
    p = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=65)
    if p.returncode:
        # GitHub CLI output can include credentials or private data; don't echo it.
        raise SmokeError('authenticated GitHub publication command failed: '+args[0]+' '+args[1])
    return p.stdout.strip()


def publish(repo: Path, db: Path, output: Path) -> dict:
    repo, output = repo.resolve(), output.resolve()
    raw = (output / 'attempt-receipt.json').read_bytes()
    receipt = strict_json(raw)
    if receipt.get('schema') != SCHEMA or receipt.get('verdict') != 'MODEL_PATCH_ELIGIBLE_FOR_INDEPENDENT_GITHUB_PR':
        raise SmokeError('no eligible genuine model-produced patch')
    if receipt.get('base_sha') != git(repo, 'rev-parse', 'HEAD^{commit}').stdout.decode().strip():
        raise SmokeError('source changed between model run and publisher')
    if not os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_REPOSITORY') != REPO:
        raise SmokeError('publisher requires explicit credential and repository binding')
    oracle = check_oracle(repo)
    if sha(oracle) != receipt['oracle_sha256']:
        raise SmokeError('oracle drift')
    preservation = check_preservation(repo)
    if sha(preservation) != receipt.get('preservation_oracle_sha256'):
        raise SmokeError('preservation oracle drift')
    if (receipt.get('preservation_before', {}).get('state') != 'PASS'
            or receipt.get('preservation_after', {}).get('state') != 'PASS'):
        raise SmokeError('missing successful preservation-bound receipts')
    patch = (output / 'candidate.patch').read_bytes()
    if sha(patch) != receipt.get('patch_sha256') or len(patch) > 10000:
        raise SmokeError('candidate patch digest mismatch')
    source = (repo / SOURCE).read_text()
    if git(repo, 'hash-object', SOURCE).stdout.decode().strip() != receipt['source_blob']:
        raise SmokeError('source blob changed')
    if (output / 'model-transport.json').exists():
        if receipt['model_generation']['transport_sha256'] != hash_file(output / 'model-transport.json'):
            raise SmokeError('model transport hash changed')
    # Replay the original code-only edit from a data artifact; don't execute it.
    git(repo, 'apply', '--check', '--', str(output / 'candidate.patch'))
    branch = 'automation/far-autonomous-proof-' + str(os.environ.get('GITHUB_RUN_ID','local'))
    if re.fullmatch(r'automation/far-autonomous-proof-[0-9]{1,20}', branch) is None:
        raise SmokeError('untrusted GitHub run identity')
    _run('git', 'switch', '-c', branch, cwd=repo)
    git(repo, 'apply', '--', str(output / 'candidate.patch'))
    dest = repo / TEST
    if dest.exists() or dest.is_symlink():
        raise SmokeError('frozen regression test already exists')
    dest.write_bytes(oracle)
    preservation_dest = repo / PRESERVATION_TEST
    if preservation_dest.exists() or preservation_dest.is_symlink():
        raise SmokeError('frozen preservation test path collision')
    preservation_dest.write_bytes(preservation)
    if git(repo, 'hash-object', SOURCE).stdout.decode().strip() != receipt['candidate_blob']:
        raise SmokeError('model candidate source blob diverged during publication')
    _run('git', 'add', '--', SOURCE, TEST, PRESERVATION_TEST, cwd=repo)
    staged = set(_run('git', 'diff', '--cached', '--name-only', cwd=repo).splitlines())
    if staged != {SOURCE,TEST,PRESERVATION_TEST}:
        raise SmokeError('staged paths are not source+frozen oracle')
    _run('git', 'config', 'user.name', 'project-far-factory-proof-bot', cwd=repo)
    _run('git', 'config', 'user.email', 'project-far-factory-proof-bot@users.noreply.github.com', cwd=repo)
    _run('git', 'commit', '-m', 'fix(factory): reject invalid claim lease parameter types (model-produced)', cwd=repo)
    head = _run('git', 'rev-parse', 'HEAD', cwd=repo)
    ancestry = _run('git','rev-list','--parents','-n','1',head,cwd=repo).split()
    if len(ancestry)!=2 or ancestry[1] != receipt['base_sha']:
        raise SmokeError('candidate must be exactly one commit above protected base')
    # The trusted publisher alone gets GH_TOKEN. The model subprocess never did.
    _run('gh', 'auth', 'setup-git', cwd=repo)  # ephemeral trusted publisher credential helper
    _run('git', 'push', '--set-upstream', 'origin', 'HEAD:refs/heads/'+branch, cwd=repo)
    desc = [
        '## Source-exact autonomous factory proof candidate', '',
        f'Factory queue and genuine pinned local coding worker generated the SOURCE edit, not the operator. GitHub Actions source event `{receipt["base_sha"]}`.',
        f'Worker run: https://github.com/{REPO}/actions/runs/{os.environ["GITHUB_RUN_ID"]}',
        f'Worker model: `{MODEL}`; digest `{MODEL_DIGEST}`.',
        f'Generated source blob: `{receipt["candidate_blob"]}`; patch SHA-256 `{receipt["patch_sha256"]}`.',
        f'Frozen independent-from-model four-test oracle SHA-256: `{ORACLE_SHA256}`.',
        f'Frozen three-test preservation oracle SHA-256: `{PRESERVATION_SHA256}`.',
        'Baseline oracle FAIL; model-generated candidate oracle PASS, preservation oracle PASS, and existing factory regression PASS in bounded Docker.',
        '', '## Trust and governance', '',
        'New PR head is a proposed result. Worker reports are untrusted; fresh independent exact-head CI and Codex review are mandatory. No protected merge has occurred.',
        'Model identity comes from pinned local Ollama binary, not externally signed attestation. The tested oracle was authored by the initiating coordinator, not an outside reviewer.',
        'The trusted publisher alone performed repository writes after verifying model output. No model-generated source was executed on the Actions host.',
        '', '## Finding ledger', '',
        '- FACTORY-CLAIM-TYPES-001: invalid ttl/max_attempts types crash or consume lease on baseline; frozen oracle checks this. Candidate claims fix; independent exact-head validation pending.',
        '', '<!-- FAR-INVARIANTS-V1',
        json.dumps({'version': 1,
                    'scope': 'One source-exact generated Factory.claim repair with frozen new-behavior and preservation regression oracles',
                    'limitations': [
                        'Original holdout and preservation oracles are coordinator-authored, not externally authored.',
                        'Local pinned model identity is based on Ollama metadata and not externally signed.',
                        'No independent GitHub exact-head check, substantive review, or protected merge has occurred yet.',
                    ],
                    'invariants': [{
                        'id': 'FACTORY-CLAIM-TYPES-001',
                        'statement': 'Reject invalid and boolean lease parameter types before consuming a queue lease and preserve old valid worker checks.',
                        'boundary': 'Untrusted model-authored Python guard entering the persistent factory SQLite lease transition',
                        'changed_paths': [SOURCE, TEST, PRESERVATION_TEST],
                        'failure_modes': [
                            {'case': 'Malformed ttl must not consume a lease or raise uncontrolled input type errors',
                             'test': TEST+'::test_bad_ttl_does_not_consume_lease'},
                            {'case': 'Malformed retry bounds must not consume a lease or be interpreted as a positive integer',
                             'test': TEST+'::test_bad_attempt_bound_does_not_consume_lease'},
                        ],
                        'positive_control': TEST+'::test_valid_integer_lease_remains_accepted',
                        'integration_control': PRESERVATION_TEST+'::test_invalid_worker_rejected_without_mutation',
                        'assurance_limit': 'This publisher creates a candidate PR only; independent exact-head checks, Codex review and protected merge are still mandatory.',
                    }]}, indent=2),
        'FAR-INVARIANTS-END -->',
    ]
    body = output / 'pr-body.md'
    body.write_text('\n'.join(desc)+'\n')
    prurl = _run('gh','pr','create','--repo',REPO,'--base','main','--head',branch,
                 '--title','fix(factory): model-produced strict claim lease parameter validation',
                 '--body-file',str(body),cwd=repo)
    number = int(_run('gh','pr','view',prurl,'--repo',REPO,'--json','number','--jq','.number',cwd=repo))
    f = Factory(db)
    snap = f.snapshot('claimcontract')
    if snap['tasks'][0]['state']!='running' or snap['tasks'][0]['stage']!='build':
        raise SmokeError('actual factory build lease changed before publication')
    # Lease token exists only in SQLite private runner, never public artifact.
    token = f.db.execute('SELECT token FROM tasks WHERE order_id=? AND id=?',('claimcontract','repair')).fetchone()[0]
    f.record('claimcontract','repair',token,{'head_sha':head,'pr_number':number,'branch':branch})
    publication = {'schema':'far-software-factory/autonomous-published-pr/1',
                   'work_order_sha256':receipt['work_order_sha256'],'run_id':os.environ['GITHUB_RUN_ID'],
                   'head_sha':head,'pr_number':number,'branch':branch,'pr_url':prurl,
                   'base_sha':receipt['base_sha'],'model_source_blob':receipt['candidate_blob'],
                   'queue_snapshot':snapshot_sanitized(f,'claimcontract'),
                   'verdict':'MODEL_GENERATED_PR_PENDING_INDEPENDENT_REVIEW_AND_PROTECTED_MERGE'}
    (output/'publication-receipt.json').write_text(json.dumps(publication,indent=2,sort_keys=True)+'\n')
    return publication


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('command',choices=['run','publish'])
    ap.add_argument('--repo',type=Path,required=True)
    ap.add_argument('--db',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args(argv)
    try:
        result = attempt(args.repo,args.db,args.output) if args.command=='run' else publish(args.repo,args.db,args.output)
        print(json.dumps({'command':args.command,'result':result if isinstance(result,bool) else result['verdict'],'output':str(args.output)}))
        return 0 if result is True or isinstance(result,dict) else 1
    except Exception as exc:
        print('FACTORY_AUTONOMOUS_PROOF_BLOCKED: '+type(exc).__name__+(' '+str(exc)[:130] if isinstance(exc,SmokeError) else ''),file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
