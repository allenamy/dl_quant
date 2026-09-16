"""Pure dynamic-NAV daily statistics; no actual-data or experiment admission.

The caller must bind actual replay/source/receipt/checkpoint evidence separately.
All dates, report segments, blocks, repetitions and random seed are fixed here.
This module never selects a strategy arm, fee, settlement, filter or date window.
"""
from pathlib import Path
import ast
import hashlib
import json
import math
import numpy as np

FIRST = 1735689600000
YEAR2026 = 1767225600000
TERMINAL = 1788220800000
DAY_MS = 86400000
EXPECTED = np.arange(FIRST, TERMINAL + 1, DAY_MS, dtype=np.int64)
PERIODS = {'full': (0, 608), '2025': (0, 365), '2026_ytd': (365, 608)}
ROLES = ('king_reference', 'f10_s42', 'f10_s2027')
BLOCKS = (7, 30)
REPS = 2000
SEED = 914
LEGACY = Path(__file__).resolve().parent / 'source/legacy_statistics.py'
LEGACY_SHA = '2aaa51f142f6b2f86449e19ee2017748ed6d7450faa3bb5c80b5faa5aa46cd10'
CONVENTION = 'T_MINUS_BEFORE_SAME_TIME_FUNDING_CLOSE_OR_TRADE'
SCOPE = {
    'caliber': 'COMPOUND_DAILY_NET_NAV_RETURNS',
    'units': 'NAV in account currency; all returns/drawdowns are fractions, not percent or bps',
    'costs': 'Fees, funding and conditional settlements already in NAV; no cash item subtracted again',
    'source_admission': 'NOT_PERFORMED_BY_THIS_PURE_STATISTICS_MODULE',
    'interpretation': 'Conditional research economic path, no actual settlement/PIT/live risk or deployment certification',
    'bootstrap': 'Circular moving blocks of realized daily returns; no account/PNS rerun, no multiple-selection correction',
    'daily_drawdown': 'UTC boundary drawdown only; not intraday drawdown or margin risk',
    'seed_comparison': 'Two F10 seeds relative to the same-layer King; one shared market history',
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def point_metrics(nav):
    """Mathematical kernel. The fixed-window reader decides eligibility to report."""
    v = np.asarray(nav, dtype=np.float64)
    if v.ndim != 1 or len(v) < 2 or not np.isfinite(v).all() or np.any(v <= 0):
        raise ValueError('positive finite NAV nodes required')
    with np.errstate(over='ignore', divide='ignore', invalid='ignore'):
        r = v[1:] / v[:-1] - 1.
        ratio = v[-1] / v[0]
    if not np.isfinite(r).all() or np.any(r <= -1) or not math.isfinite(float(ratio)) or ratio <= 0:
        raise ValueError('NAV ratio outside representable return range')
    n = len(r)
    sd = None if n < 2 else (0. if np.ptp(r) == 0 else float(r.std(ddof=1)))
    sharpe = float(r.mean() / sd * np.sqrt(365)) if sd is not None and sd > 0 else None
    cagr = float(np.expm1(np.log(ratio) * 365 / n))
    if not math.isfinite(cagr):
        raise ValueError('CAGR outside representable range')
    streak = longest = 0
    for value in r:
        streak = streak + 1 if value < 0 else 0
        longest = max(longest, streak)
    return dict(days=n, initial_nav=float(v[0]), terminal_nav=float(v[-1]),
        returns=r.astype(float).tolist(), mean_daily_return=float(r.mean()), daily_std_ddof1=sd,
        daily_sharpe=sharpe, cumulative_return=float(ratio - 1.), cagr=cagr,
        max_drawdown=float((v / np.maximum.accumulate(v) - 1.).min()),
        worst_day=float(r.min()), longest_losing_streak_days=longest)


def draw_indices(n, block_length):
    """Original frozen circular index expression, with fixed requested design."""
    if type(n) is not int or type(block_length) is not int or block_length not in BLOCKS or n < block_length:
        raise ValueError('fixed 7/30-day blocks require enough complete days')
    raw = LEGACY.read_bytes()
    if hashlib.sha256(raw).hexdigest() != LEGACY_SHA:
        raise ValueError('legacy draw source identity')
    tree = ast.parse(raw.decode())
    function = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'paired_blocks')
    assignments = [x for x in ast.walk(function) if isinstance(x, ast.Assign) and len(x.targets) == 1
                   and isinstance(x.targets[0], ast.Name) and x.targets[0].id == 'ix']
    if len(assignments) != 1:
        raise ValueError('unique original bootstrap index expression required')
    expression = compile(ast.Expression(assignments[0].value), str(LEGACY), 'eval')
    namespace = dict(np=np, rng=np.random.default_rng(SEED), n=n, k=math.ceil(n / block_length), block_length=block_length)
    return np.asarray([eval(expression, namespace) for _ in range(REPS)], dtype=np.int64)


def valuation_grid_drawdown(nodes, *, grid, initial_nav, clock_ms, attempt_offset_ms=None):
    """Optional proxy-clock drawdown, never a substitute for the DAY path."""
    if grid not in ('NAV_SNAPSHOT', 'READBACK'):
        raise ValueError('fixed valuation grid required')
    if nodes is None:
        return None
    if not isinstance(nodes, list) or not finite(initial_nav) or initial_nav <= 0 or type(clock_ms) is not int:
        raise ValueError('valuation list, positive capital and exact clock required')
    if grid == 'READBACK' and (type(attempt_offset_ms) is not int or attempt_offset_ms not in (1500000, 3300000)):
        raise ValueError('READBACK needs the explicit fixed 25/55-minute attempt clock')
    offset = 1200000 if grid == 'NAV_SNAPSHOT' else attempt_offset_ms
    expected = np.arange(FIRST, TERMINAL, 14400000, dtype=np.int64) + offset
    times, values = [], []
    for row in nodes:
        if not isinstance(row, dict) or type(row.get('ts_ms')) is not int:
            raise ValueError('exact valuation timestamp required')
        t, v = row['ts_ms'], row.get('nav')
        if t < int(expected[0]) or t > int(expected[-1]) or (t - FIRST - offset) % 14400000 or t > clock_ms or (times and t <= times[-1]):
            raise ValueError('duplicate, unordered, outside, future or wrong-clock valuation')
        if not finite(v) or v <= 0:
            raise ValueError('nonpositive/nonfinite event NAV cannot be reported')
        times.append(t); values.append(float(v))
    prefix = 0
    for t, wanted in zip(times, expected):
        if t != int(wanted):
            break
        prefix += 1
    dd = None
    if prefix:
        nav = np.asarray([initial_nav] + values[:prefix], dtype=np.float64)
        dd = float((nav / np.maximum.accumulate(nav) - 1.).min())
    return dict(grid=grid, offset_ms=offset, expected_nodes=len(expected), supplied_nodes=len(nodes),
        verified_prefix_nodes=prefix, complete_grid=prefix == len(expected),
        first_missing_ms=None if prefix == len(expected) else int(expected[prefix]),
        supplied_later_nodes=len(nodes) - prefix,
        max_drawdown_observed_prefix=dd, initial_reference_nav=float(initial_nav),
        basis='DECLARED_CLOSE_PROXY_GRID_WITH_INITIAL_CAPITAL_REFERENCE',
        interpretation='Observed fixed-clock prefix only; not continuous intraday maximum risk or full-path certification')


def summarize_state(state, *, event_valuations=None):
    """Describe fixed periods or an explicitly incomplete, unannualized prefix.

    Accepts Engine export structure. This checks arithmetic/population consistency
    only; it does not authenticate a caller's state or its declared policy source.
    """
    if not isinstance(state, dict) or state.get('schema') != 'DYNAMIC_EXECUTOR_CASH_STATE_1':
        raise ValueError('Engine state schema required')
    if state.get('scope', {}).get('certificate') != 'RESEARCH_ECONOMIC_PATH_ONLY':
        raise ValueError('explicit research economic path scope required')
    initial = state.get('config', {}).get('initial_capital')
    if not finite(initial) or initial <= 0:
        raise ValueError('finite positive initial capital')
    clock = state.get('clock_ms')
    if type(clock) is not int or clock < FIRST or clock > TERMINAL:
        raise ValueError('state clock outside fixed window')
    status, blocked = state.get('status'), state.get('blocked')
    if status not in ('RESEARCH_PATH_OPEN', 'UNMEASURABLE'):
        raise ValueError('explicit Engine path status required')
    if status == 'RESEARCH_PATH_OPEN' and blocked is not None:
        raise ValueError('open status contradicts blocked path')
    if status == 'UNMEASURABLE' and (not isinstance(blocked, dict) or not isinstance(blocked.get('reason'), str)
        or type(blocked.get('ts_ms')) is not int or blocked['ts_ms'] < clock):
        raise ValueError('unknown path needs its actual blocking event')
    if event_valuations is None:
        event_valuations = {'NAV_SNAPSHOT': None, 'READBACK': None}
    if not isinstance(event_valuations, dict) or set(event_valuations) != {'NAV_SNAPSHOT', 'READBACK'}:
        raise ValueError('explicit NAV_SNAPSHOT/READBACK valuation fields required')
    event_drawdowns = {grid: valuation_grid_drawdown(nodes, grid=grid, initial_nav=initial, clock_ms=clock,
        attempt_offset_ms=state.get('config', {}).get('attempt_offset_ms')) for grid, nodes in event_valuations.items()}
    rows = state.get('days')
    if not isinstance(rows, list):
        raise ValueError('DAY node list required')
    times, values = [], []
    for row in rows:
        if not isinstance(row, dict) or type(row.get('ts_ms')) is not int or row.get('convention') != CONVENTION:
            raise ValueError('exact integer timestamp and T-minus DAY convention required')
        t, v = row['ts_ms'], row.get('nav')
        if t < FIRST or t > TERMINAL or t % DAY_MS != 0 or t > clock or (times and t <= times[-1]):
            raise ValueError('duplicate, unordered, outside, or future DAY node')
        if not finite(v) or v <= 0:
            raise ValueError('nonpositive/nonfinite DAY NAV cannot be reported')
        times.append(t); values.append(float(v))
    if times and times[0] == FIRST and values[0] != initial:
        raise ValueError('initial DAY NAV must equal declared flat initial capital')
    prefix = 0
    for t, wanted in zip(times, EXPECTED):
        if t != int(wanted):
            break
        prefix += 1
    first_issue = None
    if prefix < len(EXPECTED):
        first_issue = dict(reason='MISSING_DAY_NODE', ts_ms=int(EXPECTED[prefix]),
                           supplied_later_nodes=len(rows) - prefix)
    if status == 'UNMEASURABLE':
        if first_issue is None or blocked['ts_ms'] <= first_issue['ts_ms']:
            first_issue = dict(reason='ENGINE_PATH_UNMEASURABLE', event=blocked)
    descriptive = None
    if prefix >= 2:
        p = point_metrics(np.array(values[:prefix]))
        descriptive = {k: p[k] for k in ('days', 'cumulative_return', 'max_drawdown', 'worst_day', 'longest_losing_streak_days')}
        descriptive['max_drawdown_basis'] = 'UTC_DAY_T_MINUS_FIXED_GRID'
    segments = {}
    for label, (i, j) in PERIODS.items():
        end = int(EXPECTED[j])
        complete = prefix > j and (status == 'RESEARCH_PATH_OPEN' or
                    (end < TERMINAL and blocked['ts_ms'] > end))
        metrics = point_metrics(np.array(values[i:j + 1])) if complete else None
        if metrics is not None:
            metrics['max_drawdown_basis'] = 'UTC_DAY_T_MINUS_FIXED_GRID'
        segments[label] = dict(start_ms=int(EXPECTED[i]), end_ms=end, expected_days=j - i,
            complete=bool(complete), metrics=metrics, bootstrap=None,
            label='2026 YTD through 2026-09-01 T-minus; 243 days' if label == '2026_ytd' else label)
    selected = dict(days=rows, initial_capital=initial, clock_ms=clock, status=status, blocked=blocked,
        event_valuations=event_valuations, attempt_offset_ms=state.get('config', {}).get('attempt_offset_ms'))
    return dict(schema='DYNAMIC_NAV_DAILY_SUMMARY_1', full_window_complete=segments['full']['complete'],
        initial_capital=float(initial), supplied_nodes=len(rows), first_issue=first_issue,
        prefix=dict(verified_nodes=prefix, verified_days=max(0, prefix - 1), start_ms=FIRST if prefix else None,
                    end_ms=int(EXPECTED[prefix - 1]) if prefix else None, descriptive=descriptive,
                    not_a_substitute_for_full_window=not segments['full']['complete']),
        segments=segments, event_valuation_drawdowns=event_drawdowns,
        input_content_sha256=digest(selected), scope=SCOPE.copy())


def _replicate_metrics(returns, draws):
    sampled = np.asarray(returns, dtype=np.float64)[draws]
    means = sampled.mean(axis=1)
    std = sampled.std(axis=1, ddof=1)
    std[np.ptp(sampled, axis=1) == 0] = 0.
    sharpe = np.full(REPS, np.nan)
    np.divide(means, std, out=sharpe, where=std > 0)
    sharpe *= np.sqrt(365)
    growth = np.log1p(sampled).sum(axis=1)
    with np.errstate(over='ignore', invalid='ignore'):
        cumulative = np.expm1(growth)
        cagr = np.expm1(growth * 365 / sampled.shape[1])
    return dict(mean_daily_return=means, daily_sharpe=sharpe, cumulative_return=cumulative, cagr=cagr)


def _intervals(vectors, draw_sha):
    counts, intervals = {}, {}
    for key, value in vectors.items():
        good = value[np.isfinite(value)]
        counts[key] = int(len(good))
        intervals[key] = np.quantile(good, [.025, .975], method='linear').astype(float).tolist() if len(good) >= .95 * REPS else None
    return dict(ci=intervals, defined_replicates=counts, reps=REPS, seed=SEED, draw_sha256=draw_sha,
                percentile=[.025, .975], quantile_method='linear', min_defined_fraction=.95,
                scheme='paired circular moving blocks of realized UTC daily NAV ratio returns')


def assess_group(states, *, policy_identities, event_valuations_by_role=None):
    """One caller-specified layer: both F10 seeds paired separately to its King.

    policy_identities must match exactly; this is a consistency check, not source
    authentication. No grid or factor selection and no formal config is emitted.
    """
    if not isinstance(states, dict) or set(states) != set(ROLES) or not isinstance(policy_identities, dict) or set(policy_identities) != set(ROLES):
        raise ValueError('exact King/F10-42/F10-2027 role population required')
    if not all(isinstance(policy_identities[r], dict) and policy_identities[r] for r in ROLES):
        raise ValueError('explicit same-layer policy identities required')
    if len({digest(policy_identities[r]) for r in ROLES}) != 1:
        raise ValueError('mixed economic policy layers')
    if event_valuations_by_role is None:
        event_valuations_by_role = {r: None for r in ROLES}
    if not isinstance(event_valuations_by_role, dict) or set(event_valuations_by_role) != set(ROLES):
        raise ValueError('optional event valuations require the same exact three roles')
    levels = {r: summarize_state(states[r], event_valuations=event_valuations_by_role[r]) for r in ROLES}
    if len({levels[r]['initial_capital'] for r in ROLES}) != 1:
        raise ValueError('same-layer initial capital required')
    pairs = {r: {} for r in ROLES[1:]}
    draw_records = {}
    for period, (_, _) in PERIODS.items():
        metrics = {r: levels[r]['segments'][period]['metrics'] for r in ROLES}
        complete = {r: metrics[r] is not None for r in ROLES}
        for r in ROLES[1:]:
            ok = complete[r] and complete[ROLES[0]]
            point_delta = None
            if ok:
                point_delta = {k: (metrics[r][k] - metrics[ROLES[0]][k]) if metrics[r][k] is not None and metrics[ROLES[0]][k] is not None else None
                    for k in ('mean_daily_return', 'daily_sharpe', 'cumulative_return', 'cagr', 'max_drawdown', 'worst_day')}
                # Preserve legacy paired mean operation order: mean(a-b), not
                # separately rounded mean(a)-mean(b).
                point_delta['mean_daily_return'] = float((np.asarray(metrics[r]['returns']) - np.asarray(metrics[ROLES[0]]['returns'])).mean())
            pairs[r][period] = dict(complete=ok, base=ROLES[0], arm=r, point_delta=point_delta,
                bootstrap={} if ok else None, difference_contract='Difference of two book functionals; daily return spread is not itself a compounded investable book')
        if not any(complete.values()):
            continue
        draw_records[period] = {}
        n = PERIODS[period][1] - PERIODS[period][0]
        for block in BLOCKS:
            draws = draw_indices(n, block)
            draw_sha = hashlib.sha256(draws.astype('<i8', copy=False).tobytes(order='C')).hexdigest()
            draw_records[period][str(block)] = dict(sha256=draw_sha, shape=list(draws.shape), dtype='<i8', seed=SEED)
            samples = {r: _replicate_metrics(metrics[r]['returns'], draws) for r in ROLES if complete[r]}
            for r, vectors in samples.items():
                segment = levels[r]['segments'][period]
                if segment['bootstrap'] is None:
                    segment['bootstrap'] = {}
                segment['bootstrap'][str(block)] = dict(block_length_days=block, **_intervals(vectors, draw_sha))
            for r in ROLES[1:]:
                if pairs[r][period]['complete']:
                    with np.errstate(invalid='ignore'):
                        delta = {k: samples[r][k] - samples[ROLES[0]][k] for k in samples[r]}
                    delta['mean_daily_return'] = (np.asarray(metrics[r]['returns'])[draws] - np.asarray(metrics[ROLES[0]]['returns'])[draws]).mean(axis=1)
                    pairs[r][period]['bootstrap'][str(block)] = dict(block_length_days=block, **_intervals(delta, draw_sha))
    result = dict(schema='DYNAMIC_NAV_SAME_LAYER_GROUP_STATISTICS_1', levels=levels, paired=pairs,
        draw_matrices=draw_records, common_policy_identity=policy_identities[ROLES[0]],
        fixed_contract=dict(nodes=609, days=608, annualization=365, blocks=list(BLOCKS), reps=REPS, seed=SEED,
                            legacy_source_sha256=LEGACY_SHA), scope=SCOPE.copy(),
        promotion='NOT_EVALUATED', formal_source_admission=False)
    json.dumps(result, allow_nan=False)
    return result
