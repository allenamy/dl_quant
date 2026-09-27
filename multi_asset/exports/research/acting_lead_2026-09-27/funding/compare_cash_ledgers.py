#!/usr/bin/env python3
"""Compare funding event facts on common coverage, never infer portfolio cash/PnL.

Frozen before real reads: second buckets are diagnostic joins only. Preserve every
new millisecond event and report multiplicity separately; never coalesce for trading.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import resource
import time


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def classify(old, new):
    """Lists of (integer millisecond, finite rate), one diagnostic second bucket."""
    if not old:
        return 'new_only_second'
    if not new:
        return 'old_only_second'
    if len(old) != 1 or len(new) != 1:
        return 'multiple_events_same_second'
    same_rate = old[0][1] == new[0][1]
    same_time = old[0][0] == new[0][0]
    if same_rate and same_time:
        return 'one_to_one_exact'
    if same_rate:
        return 'one_to_one_subsecond_time_changed'
    return 'one_to_one_rate_changed'


def groups(times, rates, lo, hi):
    """Per-symbol grouping; raw times are retained in each list."""
    out = {}
    for t, r in zip(times, rates):
        t = int(t)
        if lo <= t <= hi:
            out.setdefault(t // 1000, []).append((t, float(r)))
    return out


def load_bound(spec, field, np):
    p = Path(spec['path'])
    with p.open('rb') as f:
        before = os.fstat(f.fileno())
        h = hashlib.sha256()
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
        assert h.hexdigest() == spec['sha256'], 'ledger SHA mismatch'
        f.seek(0)
        with np.load(f, allow_pickle=False) as z:
            data = {k: z[k] for k in ['symbols', 'off', field, 'rate']}
        after = os.fstat(f.fileno())
        at_path = p.stat()
        signature = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns)
        assert signature(before) == signature(after) == signature(at_path), 'file changed'
    s, off, ts, rate = (data[k] for k in ['symbols', 'off', field, 'rate'])
    assert s.ndim == 1 and s.dtype.kind in 'US' and len(set(s.tolist())) == len(s)
    assert off.ndim == 1 and off.dtype.kind in 'iu' and len(off) == len(s) + 1
    offsets = [int(x) for x in off]
    assert offsets[0] == 0 and offsets[-1] == len(ts)
    assert all(0 <= a <= b <= len(ts) for a, b in zip(offsets, offsets[1:]))
    assert ts.ndim == 1 and ts.dtype.kind in 'iu' and len(ts) > 0
    assert rate.shape == ts.shape and rate.dtype.kind == 'f' and np.isfinite(rate).all()
    if field == 'ft':
        assert int(ts.max()) < 100000000000, 'old clock not seconds'
        ts = ts.astype(np.int64) * 1000
    else:
        assert 1000000000000 <= int(ts.min()) <= int(ts.max()) < 100000000000000
    for a, b in zip(offsets, offsets[1:]):
        assert all(int(x) <= int(y) for x, y in zip(ts[a:b-1], ts[a+1:b])) if b > a else True
    return {'symbols': s.tolist(), 'offsets': offsets, 'times': ts, 'rates': rate,
            'rows': len(ts), 'min_ms': int(ts.min()), 'max_ms': int(ts.max())}


def compare(old, new):
    lo = max(old['min_ms'], new['min_ms'])
    hi = min(old['max_ms'], new['max_ms'])
    assert lo <= hi
    maps = [{s: i for i, s in enumerate(x['symbols'])} for x in [old, new]]
    counters, years, examples, per_symbol = Counter(), {}, {}, {}
    totals = {'old_events_in_common_coverage': 0, 'new_events_in_common_coverage': 0}
    for symbol in sorted(set(maps[0]) | set(maps[1])):
        gs = []
        for k, data in enumerate([old, new]):
            if symbol not in maps[k]:
                gs.append({})
                continue
            j = maps[k][symbol]; a, b = data['offsets'][j:j+2]
            gs.append(groups(data['times'][a:b], data['rates'][a:b], lo, hi))
        counts = Counter()
        for sec in sorted(set(gs[0]) | set(gs[1])):
            o, n = gs[0].get(sec, []), gs[1].get(sec, [])
            kind = classify(o, n)
            counts[kind] += 1; counters[kind] += 1
            year = str(datetime.fromtimestamp(sec, timezone.utc).year)
            years.setdefault(year, Counter())[kind] += 1
            totals['old_events_in_common_coverage'] += len(o)
            totals['new_events_in_common_coverage'] += len(n)
            if kind not in ('one_to_one_exact', 'one_to_one_subsecond_time_changed'):
                bucket = examples.setdefault(kind, [])
                if len(bucket) < 24:
                    bucket.append({'symbol': symbol, 'second': sec, 'old_events': o, 'new_events': n})
        if any(k not in ('one_to_one_exact', 'one_to_one_subsecond_time_changed') for k in counts):
            per_symbol[symbol] = dict(counts)
    return {'common_interval_ms_inclusive': [lo, hi], 'counts_second_buckets': dict(counters),
            'counts_by_year': {k: dict(v) for k, v in sorted(years.items())},
            'event_counts': totals, 'nontrivial_symbols': per_symbol,
            'first_24_examples_per_nontrivial_class': examples,
            'limitation': 'No held quantities, prices, fills, candidate outcomes or cash impact read. '
            'Second buckets are diagnostic alignment only, not settlement aggregation. '
            'Common global coverage does not certify each symbol coverage.'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--identity', required=True); ap.add_argument('--identity-sha', required=True)
    ap.add_argument('--self-sha', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    assert digest(__file__) == a.self_sha
    raw = Path(a.identity).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == a.identity_sha
    assert not Path(a.out).exists()
    mem = int(Path('/sys/fs/cgroup/memory.max').read_text())
    used = int(Path('/sys/fs/cgroup/memory.current').read_text())
    assert mem - used >= 2 * 1024**3, 'less than 2GiB cgroup headroom'
    os.nice(19)
    resource.setrlimit(resource.RLIMIT_CPU, (90, 90))
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024**2, 768 * 1024**2))
    import numpy as np
    start = time.monotonic()
    assets = json.loads(raw)['assets']
    old = load_bound(assets['ledger_full'], 'ft', np)
    new = load_bound(assets['ms_ledger'], 'ft_ms', np)
    report = compare(old, new)
    report.update({'status': 'EVENT_FACTS_COMPARED_NOT_PORTFOLIO_EVALUATION',
                   'source_sha256': a.self_sha, 'identity_manifest_sha256': a.identity_sha,
                   'inputs': {k: assets[k] for k in ['ledger_full', 'ms_ledger']},
                   'full_coverage': {k: {n: v[n] for n in ['rows', 'min_ms', 'max_ms']}
                                     for k, v in [('old', old), ('new', new)]},
                   'wall_seconds': time.monotonic() - start,
                   'peak_rss_kib_linux': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
    with Path(a.out).open('x') as f:
        json.dump(report, f, indent=2, allow_nan=False); f.write('\n')
    print(json.dumps({k: report[k] for k in ['status', 'counts_second_buckets', 'event_counts',
                                            'wall_seconds', 'peak_rss_kib_linux']}))


if __name__ == '__main__':
    main()
