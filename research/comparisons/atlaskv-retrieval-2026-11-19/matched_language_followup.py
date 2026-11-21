"""Post-hoc, template-bound natural-language controlled retrieval comparison.

All retrieval arms take question text, the same pre-existing frozen facts, and
an equal evidence-record output cap. This is an internal follow-up on a known
corpus; the rules were authored with access to the question templates.
It is NOT an AtlasKV trained-model evaluation or blinded external comparison.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
import csv
import json
import re
from pathlib import Path
from typing import Mapping
import evaluate as original

BASE=Path(__file__).resolve().parent
PATTERNS=(
    (re.compile(r'^What method powers the service operated by the organization employing (Analyst_\d+)\?$'),
     lambda m:dict(anchor=m[1],relations=['employed_by','operates','powered_by'],source=None,as_of=None)),
    (re.compile(r'^According to (audit_[a-z]+), what is the audit status of ((?:Platform|Unregistered)_\d+)\?$'),
     lambda m:dict(anchor=m[2],relations=['audit_status'],source=m[1],as_of=None)),
    (re.compile(r'^Who maintained (Component_\d+) as of (\d{4}-\d{2}-\d{2})\?$'),
     lambda m:dict(anchor=m[1],relations=['maintained_by'],source=None,as_of=m[2])),
)

def parse_question(question):
    """Pure question-only parse; fail closed on unknown or ambiguous patterns."""
    matches=[build(m) for pattern,build in PATTERNS if (m:=pattern.fullmatch(question))]
    if len(matches)!=1:
        return None
    return matches[0]


def evaluate_all(budgets=(1,2,3,8,16)):
    _,data=original.load_frozen()
    index=original.BenchmarkIndex(data['facts'])
    rows=[]
    arms=('flat_tfidf_full','flat_tfidf_triples','hierarchical_proxy_full','structured_graph_text_parsed')
    old_budget=original.BUDGET
    try:
        for budget in budgets:
            original.BUDGET=budget
            for c in data['cases']:
                parsed=parse_question(c['question'])
                for arm in arms:
                    if arm=='structured_graph_text_parsed':
                        selected=[] if parsed is None else index.select(parsed,'structured_graph_oracle')
                        # Answer semantics for graph are also derived from text only.
                        observed='UNKNOWN' if parsed is None else original.deterministic_answer(parsed,selected)
                    else:
                        selected=index.select(c,arm)
                        # Existing arms retain their declared case parser for answer evaluation;
                        # this benefits them vs the graph's own parser, not vice versa.
                        observed=original.deterministic_answer(c,selected)
                    ids={f['id'] for f in selected}
                    complete=all(i in ids for i in c['proof']) if c['proof'] else None
                    if arm=='flat_tfidf_triples' and c['family'] in ('contradiction','temporal'):
                        complete=False
                    rows.append(dict(case_id=c['id'],family=c['family'],budget=budget,arm=arm,
                                     expected=c['answer'],observed=observed,correct=int(observed==c['answer']),
                                     proof_complete=complete,parse_ok=(parsed is not None),selected_ids=';'.join(f['id'] for f in selected)))
    finally:
        original.BUDGET=old_budget
    summary={'schema':'far-matched-language-followup/1.0',
             'scope':'post-hoc, template-specific internal synthetic evaluation, no trained AtlasKV model',
             'note':'Parser authored after exposure to dataset templates; flat and hierarchical arms use the original typed answer semantics.',
             'cases':len(data['cases']),'parser_coverage':sum(parse_question(c['question']) is not None for c in data['cases']),
             'arms':{},'by_budget':{}}
    for budget in budgets:
        summary['by_budget'][str(budget)]={}
        for arm in arms:
            selected=[r for r in rows if r['budget']==budget and r['arm']==arm]
            positive=[r for r in selected if r['expected']!='UNKNOWN']
            summary['by_budget'][str(budget)][arm]={
                'correct':sum(r['correct'] for r in selected),
                'positive_correct':sum(r['correct'] for r in positive),
                'complete_proof':sum(r['proof_complete'] is True for r in positive),
                'unknown_correct':sum(r['correct'] for r in selected if r['expected']=='UNKNOWN')}
    return summary,rows


def write_outputs():
    summary,rows=evaluate_all()
    with (BASE/'matched_language_results.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=tuple(rows[0]));writer.writeheader();writer.writerows(rows)
    (BASE/'matched_language_summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    return summary

if __name__=='__main__': print(json.dumps(write_outputs(),indent=2))
