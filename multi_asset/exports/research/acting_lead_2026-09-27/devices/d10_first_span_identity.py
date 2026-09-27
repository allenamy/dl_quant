#!/usr/bin/env python3
"""Independent input gate for a future first 120-anchor exact-ms consumer.

No executor imports, simulation, training, target construction, or old-file writes.
Passing this gate proves input/clock binding only, never consumer cash correctness.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


class Unavailable(ValueError):
    pass


def need(ok, reason):
    if not ok: raise Unavailable(reason)


def stream_sha(f):
    h = hashlib.sha256()
    for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def sha(path):
    with Path(path).open('rb') as f: return stream_sha(f)


def pinned_file(obj, name):
    p = Path(obj['path'])
    need(p.is_absolute() and p.is_file(), name + ': missing or non-absolute file')
    got = sha(p)
    need(got == obj['sha256'], name + ': actual file SHA differs')
    return p


def validate_contract(c, identity, manifest_sha):
    need(identity['schema'] == 'd10-first-span-input-identity/1', 'identity schema differs')
    need(c['schema'] == 'd10-first-120-contract/1', 'contract schema differs')
    need(c['identity_manifest_sha256'] == manifest_sha, 'contract bound another identity manifest')
    a = c['anchors']
    need(isinstance(a, list) and len(a) == 120 and all(type(x) is int for x in a), 'exactly 120 integer anchors required')
    need(a[0] > 0 and all(y - x == 14400 for x, y in zip(a, a[1:])), 'anchor grid differs')
    need(a[0] % 14400 == 0, 'first anchor not a UTC 4h boundary')
    lo, hi = a[0] * 1000, (a[-1] + 14400) * 1000
    need(type(c['end_ms']) is int and c['end_ms'] == hi, 'end must equal (last anchor + 14400)*1000')
    need(c['cash_interval'] == '(start,end]', 'cash endpoint convention differs')
    need(c['feature_known_offset_ms'] == 999 and c['decision_offset_ms'] == 1440000,
         'producer whole-second feature clock or A+24m decision differs')
    need(c['funding_before_same_time_fill'] is True, 'same-time funding-before-fill required')
    f = c['funding']; expected = identity['assets']['ms_ledger']
    for k, v in {'field': 'ft_ms', 'dtype': '<i8', 'unit': 'millisecond',
                 'clock': 'economic_settlement', 'coalesce_seconds': False}.items():
        need(f.get(k) == v, 'funding field/unit/clock mismatch: ' + k)
    need(f['path'] == expected['path'] and f['sha256'] == expected['sha256'], 'funding declared path/SHA differs from ms identity')
    need(str(Path(f['path']).resolve()) == expected['resolved'], 'actual funding resolved path differs')
    need(c['consumer']['kind'] == 'exact_ms_active_view', 'unsupported or integer-second consumer')
    old_target = identity['assets']['targets']['path']
    t = c['targets']
    need(t.get('new_independent') is True and str(Path(t['path']).resolve()) != str(Path(old_target).resolve()),
         'fresh independent targets required; prior target cannot be borrowed')
    return lo, hi


def check_and_load(contract, identity_path, identity_sha):
    """The new consumer must use these returned events, not reopen an unbound ledger.

    Hash and NPZ reads share one file descriptor. Timestamp arithmetic/filtering stays
    int64 milliseconds; no second buckets or rates are aggregated. Consumer and target
    source identities are recorded but their behavior still needs independent controls.
    """
    identity_path = Path(identity_path)
    need(sha(identity_path) == identity_sha, 'actual identity manifest SHA differs')
    identity = json.loads(identity_path.read_text())
    lo, hi = validate_contract(contract, identity, identity_sha)
    consumer = pinned_file(contract['consumer'], 'consumer source')
    target = pinned_file(contract['targets'], 'fresh targets')
    fmeta = contract['funding']; p = Path(fmeta['path'])
    need(p.is_file(), 'actual ms ledger missing')
    with p.open('rb') as f:
        before = p.stat(); actual_sha = stream_sha(f)
        need(actual_sha == fmeta['sha256'], 'loaded funding file SHA differs')
        f.seek(0)
        with np.load(f, allow_pickle=False) as z:
            need('ft_ms' in z.files and 'ft' not in z.files, 'actual funding schema is not exclusively ft_ms')
            need({'off', 'symbols', 'rate'} <= set(z.files), 'actual funding schema incomplete')
            ft = z['ft_ms']; off = z['off']; syms = z['symbols']; rate = z['rate']
        after = p.stat()
        need((before.st_ino, before.st_size, before.st_mtime_ns) ==
             (after.st_ino, after.st_size, after.st_mtime_ns), 'funding file changed while loading')
    need(ft.ndim == 1 and ft.dtype.str == '<i8' and len(ft) > 0, 'actual ft_ms must be nonempty int64')
    need(int(ft.min()) >= 1000000000000, 'ft_ms magnitude is seconds or outside supported history')
    need(syms.ndim == 1 and syms.dtype.kind in 'US' and len(set(syms.tolist())) == len(syms), 'invalid symbol axis')
    need(off.ndim == 1 and off.dtype.kind in 'iu' and len(off) == len(syms) + 1 and
         off[0] == 0 and off[-1] == len(ft) and bool((np.diff(off) >= 0).all()), 'invalid funding offsets')
    need(rate.shape == ft.shape and rate.dtype.kind == 'f' and bool(np.isfinite(rate).all()), 'invalid/nonfinite funding rate')
    selected = []
    for j in range(len(syms)):
        l, r = int(off[j]), int(off[j + 1]); times = ft[l:r]
        need(bool((np.diff(times) > 0).all()), 'duplicate or unsorted exact-ms event within symbol')
        ix = np.flatnonzero((times > lo) & (times <= hi)) + l
        if len(ix): selected.append((j, ix))
    need(bool(selected), 'no settlement events in the fixed first span')
    ix = np.concatenate([v for _, v in selected]); jj = np.concatenate([np.full(len(v), j, np.int32) for j, v in selected])
    order = np.lexsort((jj, ft[ix])); ix, jj = ix[order], jj[order]
    events = {'ft_ms': ft[ix], 'symbol_index': jj, 'rate': rate[ix], 'symbols': syms}
    report = {'status': 'INPUT_CONTRACT_PASS_CASH_UNVALIDATED', 'execution_ready': False,
              'identity_manifest_sha256': identity_sha, 'source_sha256': sha(__file__),
              'loaded_funding': {'path': str(p), 'resolved': str(p.resolve()), 'sha256': actual_sha,
                                 'field': 'ft_ms', 'dtype': ft.dtype.str, 'unit': 'millisecond'},
              'span': {'anchors': contract['anchors'], 'start_ms_exclusive': lo, 'end_ms_inclusive': hi},
              'events': {'selected_rows': len(ix), 'first_ms': int(events['ft_ms'][0]), 'last_ms': int(events['ft_ms'][-1]),
                         'ft_ms_sha256': hashlib.sha256(events['ft_ms'].tobytes()).hexdigest()},
              'consumer': {'path': str(consumer), 'sha256': contract['consumer']['sha256']},
              'targets': {'path': str(target), 'sha256': contract['targets']['sha256']},
              'remaining': ['consumer exact-ms cash/priority controls', 'actual target/adapter first-span lineage',
                            'first legal admission, prices/UNKNOWN/cutoff', 'nonzero fills and reachable settlements']}
    return events, report


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--contract', required=True); ap.add_argument('--identity', required=True)
    ap.add_argument('--identity-sha', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args(); out = Path(a.out)
    need(not out.exists(), 'output exists; refusing overwrite')
    rc = 0
    try:
        _, result = check_and_load(json.loads(Path(a.contract).read_text()), a.identity, a.identity_sha)
    except (Unavailable, OSError, KeyError, ValueError, TypeError) as e:
        result = {'status': 'UNAVAILABLE', 'execution_ready': False, 'reason': str(e)}; rc = 2
    with out.open('x') as f: json.dump(result, f, indent=2); f.write('\n')
    print(result['status']); return rc


if __name__ == '__main__': raise SystemExit(main())
