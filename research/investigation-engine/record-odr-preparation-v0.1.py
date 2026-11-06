"""Record a new scripted graph preparation observation; never overwrite evidence."""
import argparse
import asyncio
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import socket
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.far_investigation_odr_preparation import ScriptedPreparationModel, prepare_graph
from tests.test_far_investigation_odr_preparation import ActualUpstreamGraphTests


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(upstream):
    lock = Path(__file__).with_name('requirements-odr-preparation-v0.1.txt')
    versions = {}
    for line in lock.read_text().splitlines():
        name, expected = line.split('==')
        actual = importlib.metadata.version(name)
        if actual != expected:
            raise ValueError('preparation dependency drift: ' + name)
        versions[name] = actual
    fixture = ActualUpstreamGraphTests()
    with patch.object(socket.socket, 'connect', side_effect=AssertionError('network forbidden')):
        result = asyncio.run(prepare_graph(upstream, fixture.runtime(),
                                          ScriptedPreparationModel(fixture.script())))
    result.update({
        'preparation_identity': 'FAR-ODR-PREP-001',
        'adapter_sha256': digest(ROOT/'tools/far_investigation_odr_preparation.py'),
        'fixture_sha256': digest(ROOT/'tests/test_far_investigation_odr_preparation.py'),
        'recipe_sha256': digest(Path(__file__)),
        'dependency_lock_sha256': digest(lock), 'dependency_versions': versions,
        'python': platform.python_version(), 'platform': platform.platform(),
        'resource_evidence': {'live_model_calls': 0, 'fixture_model_calls': len(result['model_fixture_journal']),
                              'billing': None, 'tokens': None},
    })
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output and args.output.exists():
        parser.error('output already exists; preserve observations and use a new location')
    result = record(args.upstream)
    raw = json.dumps(result, default=lambda obj: obj.model_dump(mode='json'),
                     sort_keys=True, indent=2, allow_nan=False) + '\n'
    if args.output:
        with args.output.open('x') as destination:
            destination.write(raw)
    else:
        print(raw, end='')
