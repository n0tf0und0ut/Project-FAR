"""Replay research observations and compare all semantic fields, ignoring timings."""
import argparse
import json
from pathlib import Path
import pilot


def semantic_view(result):
    return {
        'schema': result['schema'],
        'method': result['method'],
        'dataset_sha256': result['dataset_sha256'],
        'dataset_origin': result['dataset_origin'],
        'counts': result['counts'],
        'config': result['config'],
        'good_minus_bad_r1': result['good_minus_bad_r1'],
        'good_minus_pca_r1': result['good_minus_pca_r1'],
        'production_eligibility': result['production_eligibility'],
        'external_effectiveness_established': result['external_effectiveness_established'],
        'factual_correctness_evaluated': result['factual_correctness_evaluated'],
        'runs': [
            {'seed': row['seed'],
             'conditions': {
                 cond: {key: val for key, val in observation.items() if key != 'train_wall_seconds'}
                 for cond, observation in row['conditions'].items()}}
            for row in result['runs']
        ]
    }


def verify_result(result):
    config = result['config']
    if config != {'seeds': [11, 29, 47], 'steps': 200, 'width': 8}:
        raise ValueError('unexpected protocol configuration')
    actual = pilot.run(pilot.synthetic(), seeds=config['seeds'], steps=config['steps'], width=config['width'])
    if semantic_view(result) != semantic_view(actual):
        raise AssertionError('saved results disagree with fresh seeded execution')
    return {'replayed': True, 'dataset_sha256': actual['dataset_sha256'],
            'conditions': list(pilot.CONDITIONS), 'seeds': config['seeds']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify_result(json.loads(args.results.read_text(encoding='utf-8'))), sort_keys=True))


if __name__ == '__main__':
    main()
