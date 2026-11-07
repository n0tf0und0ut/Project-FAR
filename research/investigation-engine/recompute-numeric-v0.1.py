"""Post-hoc arithmetic on original retained sources, not a new model trial.

This is an internal reproducibility record, not independent semantic adjudication.
It never changes the ZIP, executes model output or accesses the network.
"""
import hashlib
import json
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
import calendar
import zipfile

ROOT = Path(__file__).resolve().parent
ZIP_SHA = 'ac45229fda1e7a38fe23b5127cfd361fc938601bc5b6db94bd5d9a95268473e9'
archive_bytes = (ROOT / 'hosted-recovery-v0.1.zip').read_bytes()
assert hashlib.sha256(archive_bytes).hexdigest() == ZIP_SHA
with zipfile.ZipFile(ROOT / 'hosted-recovery-v0.1.zip') as archive:
    states = {key: json.loads(archive.read(key + '-deterministic.json')) for key in ('H202', 'H203', 'H208')}


def source_binding(task, quote):
    state = states[task]
    projection = state['projections']['src.1']
    text = projection['text']
    start = text.index(quote)
    return {'source_url': state['sources']['src.1']['request']['url'],
            'source_sha256': projection['source_sha256'],
            'projection_sha256': projection['projection_sha256'],
            'quote': quote, 'start': start, 'end': start + len(quote)}


with localcontext() as context:
    context.prec = 50
    amplitude = Decimal(10) ** (Decimal('8.7') - Decimal('5.8'))
    energy = Decimal(10) ** (Decimal('1.5') * (Decimal('8.7') - Decimal('5.8')))
    sample = [50, 48, 44, 56, 61, 52, 53, 55, 67, 51]
    n = len(sample)
    average = Fraction(sum(sample), n)
    variance = sum((Fraction(x) - average) ** 2 for x in sample) / (n - 1)
    sd = (Decimal(variance.numerator) / Decimal(variance.denominator)).sqrt()
    statistic = ((Decimal(average.numerator) / Decimal(average.denominator) - 50)
                 / (sd / Decimal(n).sqrt()))
    years = list(range(2000, 2400))  # complete half-open proleptic Gregorian cycle
    leap = [y for y in years if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)]
    assert leap == [y for y in years if calendar.isleap(y)]
    mean_year = Fraction(400 * 365 + len(leap), 400)
    result = {
        'schema': 'far-posthoc-numeric-recomputation/0.1',
        'status': 'INTERNAL_POSTHOC_REPLAY_ONLY', 'original_zip_sha256': ZIP_SHA,
        'recipe_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'independent_semantic_adjudication': False, 'new_model_calls': 0,
        'H202': {'bindings': [source_binding('H202', '10**(8.7-5.8)'),
                             source_binding('H202', '10**(1.5*(8.7-5.8))')],
                 'amplitude_ratio_decimal_50_digits': str(amplitude),
                 'empirical_energy_ratio_decimal_50_digits': str(energy),
                 'nearest_integer_ratios': [int(amplitude.to_integral_value()), int(energy.to_integral_value())],
                 'scope': 'Recompute quoted formulas only; no intensity, damage or causal-effect inference.'},
        'H203': {'bindings': [source_binding('H203', '50  48  44  56  61  52  53  55  67  51'),
                             source_binding('H203', 'process mean is 50 counts'),
                             source_binding('H203', 't_{1-0.025, \\, 9} = 2.262')],
                 'n': n, 'sample': sample, 'mean_exact': str(average),
                 'sample_variance_exact': str(variance), 'sample_sd_decimal': str(sd),
                 't_statistic_decimal': str(statistic), 'degrees_of_freedom': n - 1,
                 'two_sided_alpha': '0.05', 'source_reported_critical_value': '2.262',
                 'critical_value_independently_recomputed': False,
                 'decision_using_reported_critical_value': 'DO_NOT_REJECT_POINT_NULL',
                 'comparison_passed': abs(statistic) < Decimal('2.262'),
                 'scope': 'Conditional arithmetic on retained observations; randomness, independence, distribution and process stability unverified.'},
        'H208': {'bindings': [source_binding('H208', 'centurial years that are not evenly divisible by 400'),
                             source_binding('H208', 'approximately 365.2422 days')],
                 'cycle_start_inclusive': 2000, 'cycle_end_exclusive': 2400,
                 'enumerated_leap_years': leap, 'leap_count': len(leap),
                 'total_days': 400 * 365 + len(leap), 'mean_days_exact': str(mean_year),
                 'calendar_library_agreement': True,
                 'difference_from_quoted_approximate_tropical_year_seconds_exact': str((mean_year - Fraction('365.2422')) * 86400),
                 'scope': 'Specified proleptic Gregorian cycle and quoted approximation only; no universal astronomical-year or long-term synchronization claim.'},
        'original_lane_observation': {
            key: {'native_evaluations': len(state['evaluations']),
                  'all_native_outcomes_unknown': all(e['outcome'] == 'Unknown' for e in state['evaluations']),
                  'native_plan_kinds': [c['contract']['plan']['kind'] for c in state['intake']['discovery']['contract_candidates']]}
            for key, state in states.items()},
        'limitations': ['Post-hoc analyst selection of three deterministic numeric obligations.',
                       'Calculations do not repair or replace original agent/workflow answers.',
                       'No competitor, human-outcome, population-reliability or causal-superiority estimate.']}
print(json.dumps(result, indent=2, sort_keys=True))
