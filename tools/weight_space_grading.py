"""Trusted deterministic grading of a small authored output-contract corpus.

These categories describe observed strings, not inferred internal mental causes.
No model output can supply its own correctness label.
"""
from __future__ import annotations
import json
import re

CATEGORIES = ('repetition', 'premature_termination', 'tool_selection',
              'unsupported_inference', 'task_completion', 'source_distraction', 'regression')


def repeated_suffix(tokens: list[int]) -> bool:
    """Three adjacent copies of a 2..16-token suffix: a registered proxy only."""
    return any(len(tokens) >= 3*n and tokens[-n:] == tokens[-2*n:-n] == tokens[-3*n:-2*n]
               for n in range(2, 17))


def grade(task: dict, text: str, tokens: list[int], hit_limit: bool) -> dict:
    answer = text.strip()
    kind, gold = task['grader'], task['gold']
    if kind == 'exact':
        correct = answer == gold
    elif kind == 'json':
        try:
            def pairs(items):
                result = {}
                for key, value in items:
                    if key in result:
                        raise ValueError('duplicate field')
                    result[key] = value
                return result
            value = json.loads(answer, object_pairs_hook=pairs,
                               parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
            # JSON bool must not equal integer 1/0 in a strict output contract.
            correct = (json.dumps(value, sort_keys=True, separators=(',', ':')) ==
                       json.dumps(gold, sort_keys=True, separators=(',', ':')))
        except (ValueError, TypeError):
            correct = False
    else:
        raise ValueError('unknown grader')
    return {'correct': correct, 'repeated_suffix': repeated_suffix(tokens),
            'hit_token_limit': bool(hit_limit), 'empty_output': not bool(answer),
            'contract_failure_category': None if correct else task['category']}
