"""Non-promoting field-evaluation scorer for independently adjudicated FAR outputs.

Gold labels are external inputs, never generated or inferred from FAR's audit.
A local score is not evidence that the reference annotations are independent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

PREDICTED = frozenset({'SUPPORTED', 'REFUTED', 'INSUFFICIENT', 'ABSTAIN'})
REFERENCE = frozenset({'SUPPORTED', 'REFUTED', 'INSUFFICIENT', 'CONTESTED'})
FIDELITY = frozenset({'FAITHFUL', 'UNFAITHFUL', 'DISPUTED'})
ADEQUACY = frozenset({'ADEQUATE', 'INADEQUATE', 'UNDETERMINED'})
TEMPORAL = frozenset({'IN_WINDOW', 'NOT_ADMISSIBLE', 'UNKNOWN'})
MAX_CASES = 10000

class InvalidFieldEvaluation(ValueError):
    pass


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def sha(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _no_duplicate(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise InvalidFieldEvaluation('duplicate JSON object field: ' + str(k))
        d[k] = v
    return d


def read_json(path: Path) -> object:
    if path.stat().st_size > 6_000_000:
        raise InvalidFieldEvaluation('input over six-megabyte limit')
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=_no_duplicate,
                      parse_constant=lambda s: (_ for _ in ()).throw(InvalidFieldEvaluation('nonfinite number')))


def _index(items, *, kind: str, field: str = 'case_id'):
    if not isinstance(items, list) or not 1 <= len(items) <= MAX_CASES:
        raise InvalidFieldEvaluation(kind + ' must contain 1–10000 cases')
    result = {}
    for item in items:
        if not isinstance(item, dict):
            raise InvalidFieldEvaluation(kind + ' contains non-object')
        key = item.get(field)
        if not isinstance(key, str) or not (1 <= len(key) <= 160) or key in result:
            raise InvalidFieldEvaluation(kind + ' missing/duplicate/oversized case ID')
        result[key] = item
    return result


def upper_error_rate(k: int, n: int, alpha: float = .05) -> float | None:
    """One-sided Clopper–Pearson upper bound, inversion of Binomial CDF.

    Assumes independent identically distributed Bernoulli observations in the
    declared population. No open-world/distribution-shift guarantee follows.
    """
    if n == 0:
        return None
    if not 0 <= k <= n or not 0 < alpha < 1:
        raise ValueError('invalid binomial confidence inputs')
    if k == n:
        return 1.0
    if k == 0:
        return -math.expm1(math.log(alpha) / n)
    def cdf(p: float):
        if p <= 0:
            return 1.0
        if p >= 1:
            return 0.0
        logp, logq = math.log(p), math.log1p(-p)
        terms = [math.lgamma(n+1)-math.lgamma(i+1)-math.lgamma(n-i+1)
                 + i*logp + (n-i)*logq for i in range(k+1)]
        mx = max(terms)
        return math.exp(mx)*math.fsum(math.exp(t-mx) for t in terms)
    lo, hi = 0.0, 1.0
    for _ in range(58):
        mid = (lo+hi)/2
        if cdf(mid) > alpha:
            lo = mid
        else:
            hi = mid
    return (lo+hi)/2


def evaluate(predictions: list[dict], adjudications: list[dict], *, alpha: float = .05) -> dict:
    """Score ONLY outcomes attributed to separate adjudicators. Does not judge the gold."""
    if isinstance(alpha, bool) or not isinstance(alpha, (float,int)) or not .001 <= alpha <= .2:
        raise InvalidFieldEvaluation('alpha outside [.001,.2]')
    p = _index(predictions, kind='predictions')
    a = _index(adjudications, kind='adjudications')
    if set(p) != set(a):
        raise InvalidFieldEvaluation('prediction/reference ID sets differ; dropped cases forbidden')
    by_domain: dict[str, list] = {}
    records = []
    for case_id in sorted(p):
        pred, gold = p[case_id], a[case_id]
        prediction = pred.get('verdict')
        truth, fidelity = gold.get('reference_verdict'), gold.get('mapping_fidelity')
        adequacy, temporal = gold.get('evidence_adequacy'), gold.get('temporal_eligibility')
        domain = gold.get('domain')
        if (prediction not in PREDICTED or truth not in REFERENCE or fidelity not in FIDELITY
                or adequacy not in ADEQUACY or temporal not in TEMPORAL
                or not isinstance(domain,str) or not 1 <= len(domain) <= 80):
            raise InvalidFieldEvaluation('invalid predictions or adjudications: ' + case_id)
        if any(field in pred for field in ('reference_verdict','mapping_fidelity','evidence_adequacy', 'temporal_eligibility')):
            raise InvalidFieldEvaluation('reference material leaked into predictions: ' + case_id)
        # Denominator includes abstentions; all decisive results must be evaluated.
        decisive = prediction != 'ABSTAIN'
        semantically_disputed = fidelity == 'DISPUTED'
        truth_disputed = truth == 'CONTESTED'
        # Reference uncertainty does not become a model error or a success. A
        # decisive judgment against disputed reference is counted as unsafe.
        justified = (decisive and not semantically_disputed and not truth_disputed
                     and prediction == truth and fidelity == 'FAITHFUL'
                     and adequacy == 'ADEQUATE' and temporal == 'IN_WINDOW')
        false_certainty = decisive and not justified
        record = {'case_id': case_id, 'domain':domain, 'verdict':prediction,
                  'decisive':decisive, 'justified_under_reference':justified,
                  'false_certainty_under_reference':false_certainty,
                  'mapping_fidelity':fidelity, 'reference_disputed':semantically_disputed or truth_disputed,
                  'temporal_eligibility':temporal}
        records.append(record)
        by_domain.setdefault(domain, []).append(record)
    def metrics(group):
        n = len(group)
        covered = sum(r['decisive'] for r in group)
        fc = sum(r['false_certainty_under_reference'] for r in group)
        return {'cases':n,'decisive':covered,'abstained':n-covered,
                'coverage':covered/n, 'false_certainty':fc,
                'false_certainty_rate_given_decisive':fc/covered if covered else None,
                'upper_false_certainty_rate_given_decisive':upper_error_rate(fc,covered,alpha),
                'reference_disputes':sum(r['reference_disputed'] for r in group),
                'faithful_interpretations_in_reference':sum(r['mapping_fidelity']=='FAITHFUL' for r in group),
                'unfaithful_interpretations_in_reference':sum(r['mapping_fidelity']=='UNFAITHFUL' for r in group)}
    result={'schema':'far-field-evaluation-score/0.1','predictions_sha256':sha(predictions),
            'adjudications_sha256':sha(adjudications),'alpha':float(alpha),
            'overall':metrics(records),
            'by_domain':{domain:metrics(items) for domain,items in sorted(by_domain.items())},
            'records':records,
            'reference_independence_verified':False,
            'precommitment_or_blinding_verified':False,
            'real_world_truth_proven':False,
            'distribution_free_guarantee':False,
            'statement':'Reference labels, sampling, independent adjudication and time eligibility need external provenance.'}
    return result


def predictions_from_far_bundle(bundle_dir: Path) -> list[dict]:
    """Extract strict, non-truth decisions from real FAR audit files.

    Conditional *formal* support is not a factual verdict. This adapter must
    NOT promote it to supported/refuted merely for better benchmark coverage.
    """
    from full_cli import verify_package
    verification=verify_package(bundle_dir)
    if not verification['replay_match']:
        raise InvalidFieldEvaluation('FAR bundle did not replay')
    manifest=read_json(bundle_dir/'manifest.json')
    audit=read_json(bundle_dir/'audit.json')
    if manifest.get('investigation_id') != audit.get('investigation_id'):
        raise InvalidFieldEvaluation('FAR audit identity mismatch')
    claims=audit.get('claims',{})
    if not isinstance(claims,dict) or not claims:
        raise InvalidFieldEvaluation('FAR audit contains no claims')
    # The current engine has *no* independently established empirical truth
    # status. Changing this adapter requires a new verified factual gate.
    return [{'case_id':audit['investigation_id']+':'+claim_id,
             'verdict':'ABSTAIN', 'formal_status':v.get('status'),
             'source_audit_sha256':audit.get('report_sha256')}
            for claim_id,v in sorted(claims.items())]


def main():
    parser=argparse.ArgumentParser(description='Score locked FAR field predictions against independently adjudicated reference records')
    parser.add_argument('--predictions',type=Path)
    parser.add_argument('--far-bundle',type=Path)
    parser.add_argument('--adjudications',required=True,type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        if bool(args.predictions) == bool(args.far_bundle):
            raise InvalidFieldEvaluation('select exactly one of predictions or far-bundle')
        preds=read_json(args.predictions) if args.predictions else predictions_from_far_bundle(args.far_bundle)
        score=evaluate(preds,read_json(args.adjudications))
        encoded=canonical_bytes(score)+b'\n'
        if args.output:
            args.output.write_bytes(encoded)
        else:
            sys.stdout.buffer.write(encoded)
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print('FAR_FIELD_EVAL_INVALID: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
