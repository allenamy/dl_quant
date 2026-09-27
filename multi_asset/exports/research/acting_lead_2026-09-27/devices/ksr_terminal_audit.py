#!/usr/bin/env python3
"""Manual, read-only KSR terminal supplement; no waiter and no research verdict.

Requires the approved corrected reader's DONE chain before opening candidate
arrays. Checks all eight S1 King LR first differences, then decomposes m0 only.
The original reader, 38 series, frozen rules, and D10 pins are never changed.
"""
import argparse
import calendar
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys
import time

import numpy as np

DAY, H4, W0, GM = 86400, 14400, 1696118400, 2.0
SEEDS = ('42', '2027')
ROLES = ('BASE', 'FULL', 'SEAT', 'COMP')
CHANNELS = ('pnl', 'car', 'cst', 'unk', 'g')
WAITER_SHA = 'ab04c7f357350198ca4f1d58af44facadffede479d782e8cda7417d726010014'
CONFIG_SHA = '5a0a12dc9cf959844a10b4e34ae304cb1e0e7be0666c7f8926d7fd0521279775'
READER_SHA = '816d373458906f397f8b8e564feb67250f86a981d74e99b168162a9c20232118'
GATE4_SHA = '9557d128585a9d4ff1a8f25daa5d2a91454a87ecc2cd9e129d4f948e705bd267'
PATH_ORDER_PINS = {
    '/dev/shm/fresh_2026-09-23/devices/fa_ladsave.py': 'a2dccf15a232a546c886e12fb2e1cd5522762509f42edd324eb3df4e57d17855',
    '/dev/shm/mretrain_2026-09-26/devices/mr_engine_queue.sh': '000b6a4ba599ee0fd701a705effa2fba096dbc86296a23783462561676732f98',
}


class Unavailable(ValueError):
    """Unknown, incomplete, changed, or misaligned input; never a research REJECT."""


def need(condition, reason):
    if not condition:
        raise Unavailable(reason)


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def check_hashes(pins):
    for path, digest in pins.items():
        need(Path(path).is_file(), 'missing bound input: ' + str(path))
        need(sha(path) == digest, 'changed bound input: ' + str(path))


def ts(year, month, day=1):
    return calendar.timegm((year, month, day, 0, 0, 0))


def iso(anchor):
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(int(anchor)))


def axis(a):
    a = np.asarray(a)
    need(a.ndim == 1 and len(a) > 0 and a.dtype.kind in 'iu', 'empty or non-integer anchor axis')
    need(bool(np.all(np.diff(a) > 0)), 'duplicate or unordered anchor axis')
    need(bool(np.all(a % H4 == 0)), 'anchor is not on the four-hour UTC grid')
    return a.astype(np.int64)


def exact_edges(a, edges):
    a = axis(a)
    for edge in edges:
        need(bool(np.any(a == edge)), 'missing exact anchor ' + str(edge))
    return {iso(edge): int(np.searchsorted(a, edge)) for edge in edges}


def check_s1_lr(a0, a1, lr0, lr1):
    a0, a1 = axis(a0), axis(a1)
    need(np.array_equal(a0, a1), 'S0/S1 legs axes differ')
    exact_edges(a0, [W0])
    need(a0[0] < W0, 'no pre-window history; bitwise equality would be vacuous')
    x, y = np.asarray(lr0), np.asarray(lr1)
    need(x.shape == y.shape == (len(a0), 3), 'LR shape must be anchor x [King,rev24,fund]')
    need(x.dtype == y.dtype and x.dtype.kind in 'fiu', 'LR dtype differs or is not numeric')
    need(bool(np.isfinite(x).all() and np.isfinite(y).all()), 'non-finite LR; equality of NaNs is not evidence')

    def differing_rows(left, right):
        lb = np.ascontiguousarray(left).view(np.uint8).reshape(len(a0), -1)
        rb = np.ascontiguousarray(right).view(np.uint8).reshape(len(a0), -1)
        return np.flatnonzero(np.any(lb != rb, axis=1))

    all_rows = differing_rows(x, y)
    king_rows = differing_rows(x[:, 0], y[:, 0])
    for name, rows in [('LR', all_rows), ('King LR', king_rows)]:
        need(len(rows) > 0, name + ' never differs')
        need(int(a0[rows[0]]) == W0, name + ' first difference is not exact first window anchor')
    return {'LR_first_differing_anchor': int(a0[all_rows[0]]),
            'king_first_differing_anchor': int(a0[king_rows[0]]),
            'first_window_anchor_exists': True, 'pre_window_bitwise_equal': True,
            'LR_differing_rows': len(all_rows), 'king_differing_rows': len(king_rows),
            'LR_shape': list(x.shape), 'LR_dtype': str(x.dtype)}


def segment_masks(a):
    a = axis(a)
    masks = {
        'PRE2026_ALL_AVAILABLE': a < ts(2026, 1),
        'PRE2026_G4_COMMON': (a >= ts(2023, 6, 30) + H4) & (a < ts(2026, 1)),
        '2026_ALL_AVAILABLE': a >= ts(2026, 1),
        '2026F': a >= ts(2026, 7),
    }
    for year in (2023, 2024, 2025):
        masks[f'H1_{year}'] = (a >= ts(year, 10)) & (a < ts(year + 1, 1))
    masks['H1_merged'] = masks['H1_2023'] | masks['H1_2024'] | masks['H1_2025']
    months = np.array([iso(t)[:7] for t in a])
    for month in sorted(set(months)):
        masks['MONTH_' + month] = months == month
    return masks


def daily_indices(a, mask):
    a = axis(a); mask = np.asarray(mask)
    need(mask.dtype == bool and mask.shape == a.shape, 'segment mask shape/type differs')
    day = (a // DAY) * DAY
    days, counts = np.unique(day[mask], return_counts=True)
    days = days[counts == 6]
    need(len(days) > 0, 'segment has no full UTC days')
    ix = np.stack([np.flatnonzero(mask & (day == d)) for d in days])
    need(np.array_equal(a[ix], days[:, None] + np.arange(6) * H4), 'incomplete UTC day grid')
    return days, ix


def decompose_seed(cells, mask):
    need(set(cells) == set(ROLES), 'decomposition must contain exactly BASE/FULL/SEAT/COMP m0')
    a = axis(cells['BASE']['anchors'])
    days, ix = daily_indices(a, mask)
    levels = {}
    for role in ROLES:
        z = cells[role]
        need(np.array_equal(axis(z['anchors']), a), role + ': anchor axes differ')
        arrays = {}
        for key in ('r',) + CHANNELS:
            x = np.asarray(z[key + '_per_path'])
            need(x.shape == (32, len(a)), role + ': expected 32 paths for ' + key)
            need(bool(np.isfinite(x).all()), role + ': non-finite channel ' + key)
            arrays[key] = x
        levels[role] = {'dbar_compounded_bps': 1e4 * (np.prod(1 + arrays['r'][:, ix], axis=2) - 1)}
        for key in CHANNELS:
            levels[role][key + '_NAV_bps'] = GM * arrays[key][:, ix].sum(axis=2)
    terms = {role: {k: levels[role][k] - levels['BASE'][k] for k in levels[role]}
             for role in ('FULL', 'SEAT', 'COMP')}
    terms['INTERACTION'] = {k: terms['FULL'][k] - terms['SEAT'][k] - terms['COMP'][k]
                            for k in terms['FULL']}
    for term in terms.values():
        term['compounding_minus_g_bps'] = term['dbar_compounded_bps'] - term['g_NAV_bps']
        term['g_minus_price_net_NAV_bps'] = (term['g_NAV_bps'] - term['pnl_NAV_bps']
                                          + term['car_NAV_bps'] + term['cst_NAV_bps'] + term['unk_NAV_bps'])
    return {'days': days, 'terms': terms}


def summarize_terms(terms):
    return {role: {k: {'mean_bps_per_day': float(x.mean()),
                       'per_path_mean_bps_per_day': x.mean(axis=1).tolist(),
                       'daily_path_mean_sha256': hashlib.sha256(np.ascontiguousarray(x.mean(axis=0), dtype='<f8').tobytes()).hexdigest()}
                   for k, x in metrics.items()} for role, metrics in terms.items()}


def validate_done_identity(done):
    wanted = {'status': 'DONE', 'pgid': 3505287, 'upstream_pgid': 3479615,
              'upstream_start_ticks': 508358906, 'waiter_sha256': WAITER_SHA, 'config_sha256': CONFIG_SHA}
    for key, value in wanted.items():
        need(done.get(key) == value, 'corrected reader DONE identity differs: ' + key)


def completion_inputs(root):
    """Only receipts/hashes; no candidate metric JSON or NPZ arrays opened here."""
    root = Path(root)
    done_path, cfg_path, bind_path = root / 'DONE.json', root / 'ksr_readout_config.json', root / 'INPUTS_BOUND.json'
    need(done_path.is_file(), 'corrected reader has no DONE receipt')
    done = json.loads(done_path.read_text()); validate_done_identity(done)
    check_hashes({cfg_path: CONFIG_SHA, bind_path: done['input_manifest_sha256']})
    cfg = json.loads(cfg_path.read_text()); bound = json.loads(bind_path.read_text())
    need(Path(cfg['root']).resolve() == root.resolve(), 'readout root differs from approved config')
    need(bound['code_pins'] == cfg['pins'], 'reader code binding differs')
    need([bound.get(k) for k in ('series_count', 'tstats_count', 'gate4_count')] == [38, 16, 11], 'incomplete terminal inputs')
    need(done['output'] == str(root / 'KSR_BOOK_2026-09-27.json'), 'reader output path differs')
    book_path = Path(done['output'])
    pins = {str(done_path): sha(done_path), str(cfg_path): CONFIG_SHA,
            str(bind_path): done['input_manifest_sha256'], str(book_path): done['output_sha256'],
            **cfg['pins'], **bound['inputs'], **PATH_ORDER_PINS}
    check_hashes(pins)
    cmap = json.loads((root / 'cell_map.json').read_text())
    expected_map = {
        'S1': {f'm{k}': f'KSR_S1_m{k}' for k in range(8)},
        'S0': {f'm{k}': f'KSR_S0_m{k}' for k in range(8)},
        'RED': {'m0': 'KSR_RED_m0'},
        'HYB': {'SEAT_ONLY': 'KSR_SEAT_ONLY_m0', 'COMP_ONLY': 'KSR_COMP_ONLY_m0'},
    }
    need(cmap == expected_map, 'cell map differs from fixed m0 decomposition population')
    series = [str(Path(cfg['series']) / f'SER_{cell}_s{s}.npz')
              for group in cmap.values() for cell in group.values() for s in SEEDS]
    targets = [str(Path(cfg['tstats']) / f'{cell}_s{s}.npz') for cell in cmap['S1'].values() for s in SEEDS]
    gates = [str(Path(cfg['gate4']) / (cell + '.json')) for group in ('S1', 'RED', 'HYB') for cell in cmap[group].values()]
    need(set(bound['inputs']) == set(series + targets + gates), 'bound input population differs from 38/16/11')
    return cfg, cmap, book_path, pins, series, targets


def check_gate4_and_axes(cfg, cmap, pins, series, targets):
    facts = {}
    # Intentionally S1 only. HYB's LR is A0 by construction, so never apply this contract to HYB.
    for member, cell_name in cmap['S1'].items():
        p = Path(cfg['gate4']) / (cell_name + '.json'); r = json.loads(p.read_text())
        need(r.get('PASS') is True and r.get('self_sha256') == GATE4_SHA and r.get('mode') == 'legs', 'old gate4 identity/PASS differs: ' + cell_name)
        need(r.get('first_window_anchor') == W0, 'gate4 first window differs: ' + cell_name)
        lr_meta = r['arrays']['LR']
        need(lr_meta.get('axis0_is_anchor') is True and lr_meta.get('pre_window_bitwise_equal') is True
             and lr_meta.get('first_differing_anchor') == W0, 'gate4 LR first difference differs: ' + cell_name)
        leg_root = Path(cfg['gate4']).parent / 'legs'
        need(r['S0_legs'] == str(leg_root / f'KSR_S0_{member}.npz')
             and r['spliced_legs'] == str(leg_root / (cell_name + '.npz')), 'gate4 member paths differ: ' + cell_name)
        leg_pins = {r['S0_legs']: r['S0_legs_sha256'], r['spliced_legs']: r['spliced_legs_sha256']}
        for path, digest in leg_pins.items():
            need(pins.get(path, digest) == digest, 'conflicting legs binding: ' + path)
        check_hashes(leg_pins); pins.update(leg_pins)
        with np.load(r['S0_legs'], allow_pickle=False) as old, np.load(r['spliced_legs'], allow_pickle=False) as new:
            result = check_s1_lr(old['E_ts'], new['E_ts'], old['LR'], new['LR'])
        need(result['LR_differing_rows'] == lr_meta['n_anchors_differing'], 'actual LR differs from gate4 receipt')
        facts[member] = {'gate4_path': str(p), 'gate4_sha256': pins[str(p)], 'legs': leg_pins, **result}
    edges = [ts(y, m) for y, m in [(2023, 10), (2024, 1), (2024, 10), (2025, 1), (2025, 10), (2026, 1), (2026, 7)]]
    axes = {}; common = None
    for p in series:
        with np.load(p, allow_pickle=False) as z:
            a = axis(z['anchors'])
            positions = exact_edges(a, edges)
            if common is None:
                common = a.copy()
            need(np.array_equal(a, common), 'series axis differs: ' + p)
        axes[p] = {'first_anchor': int(a[0]), 'last_anchor': int(a[-1]), 'n_anchors': len(a), 'exact_switch_positions': positions}
    for p in targets:
        with np.load(p, allow_pickle=False) as z:
            axes[p] = {}
            for key in ('anchors', 'legs_E_ts'):
                a = axis(z[key]); positions = exact_edges(a, edges)
                if key == 'anchors':
                    need(np.array_equal(a, common), 'targets axis differs from series: ' + p)
                axes[p][key] = {'first_anchor': int(a[0]), 'last_anchor': int(a[-1]), 'n_anchors': len(a), 'exact_switch_positions': positions}
    return {'S1_first_difference': facts, 'axes': axes, 'HYB_LR_contract': 'NOT_APPLIED_BY_DESIGN'}, common


def import_frozen_stats(cfg):
    loaded = {}
    engine = Path('/dev/shm/news_2026-09-23/engine')
    for name in ('bt_tables', 'bt_driver_lib', 'news_stats'):
        p = engine / (name + '.py')
        need(str(p) in cfg['pins'], 'unbound statistics module: ' + name)
        check_hashes({p: cfg['pins'][str(p)]})
        spec = importlib.util.spec_from_file_location('ksr_audit_' + name, p)
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); loaded[name] = mod
    ns = loaded['news_stats']; ns.BT = loaded['bt_tables']; ns.DL = loaded['bt_driver_lib']
    need(float(ns.BT.GM) == GM, 'fixed gross multiplier changed')
    return ns


def build_description(cfg, cmap, book_path, a):
    book = json.loads(book_path.read_text())
    need(book.get('self_sha256') == READER_SHA and book.get('status') == 'BOOK_HALF_OF_THE_VERDICT', 'corrected book reader identity differs')
    need(float(book['GM']) == GM, 'reader gross multiplier differs')
    ns = import_frozen_stats(cfg)
    roles = {'BASE': cmap['S0']['m0'], 'FULL': cmap['S1']['m0'],
             'SEAT': cmap['HYB']['SEAT_ONLY'], 'COMP': cmap['HYB']['COMP_ONLY']}
    population = {}; cells = {}
    for seed in SEEDS:
        cells[seed] = {}; population[seed] = {}
        for role, label in roles.items():
            p = Path(cfg['series']) / f'SER_{label}_s{seed}.npz'; population[seed][role] = str(p)
            with np.load(p, allow_pickle=False) as z:
                cells[seed][role] = {key: z[key] for key in ('anchors',) + tuple(c + '_per_path' for c in ('r',) + CHANNELS)}
    output = {}; worst_parity = 0.0
    for segment, mask in segment_masks(a).items():
        need(bool(mask.any()), 'required segment is empty: ' + segment)
        by_seed = {}; raw = {}
        for seed in SEEDS:
            raw[seed] = decompose_seed(cells[seed], mask)
            days = raw[seed]['days']; need(np.array_equal(days, ns.full_days(a, mask)), 'full-day selection differs from frozen NS')
            for role in ('FULL', 'SEAT', 'COMP'):
                paths = lambda role: [{'A': a, 'r': cells[seed][role]['r_per_path'][j]} for j in range(32)]
                _, frozen = ns.dbar(paths(role), paths('BASE'), mask, days)
                actual = raw[seed]['terms'][role]['dbar_compounded_bps']
                error = float(np.max(np.abs(actual - frozen * 1e4))); worst_parity = max(worst_parity, error)
                need(bool(np.allclose(actual, frozen * 1e4, rtol=1e-12, atol=1e-9)), 'frozen dbar parity failed')
            by_seed[seed] = summarize_terms(raw[seed]['terms'])
        # Path j is the same execution seed within both model seeds; expose each seed separately above.
        averaged = {role: {key: np.mean([raw[s]['terms'][role][key] for s in SEEDS], axis=0)
                           for key in raw[SEEDS[0]]['terms'][role]} for role in raw[SEEDS[0]]['terms']}
        selected = a[mask]
        output[segment] = {'requested_first_anchor': iso(selected[0]), 'requested_last_anchor': iso(selected[-1]),
                           'n_requested_anchors': len(selected), 'n_full_UTC_days': len(days),
                           'first_used_UTC_day': iso(days[0]), 'last_used_UTC_day': iso(days[-1]),
                           'days_sha256': hashlib.sha256(np.ascontiguousarray(days, dtype='<i8').tobytes()).hexdigest(),
                           'by_seed': by_seed, 'mean_of_two_seeds_same_path': summarize_terms(averaged)}
    return {'population_m0_only': population, 'segments': output,
            'frozen_news_stats_dbar_max_abs_parity_error_bps': worst_parity}


def write_json(path, value):
    path = Path(path); tmp = path.with_name(path.name + '.tmp')
    with tmp.open('x') as f:
        json.dump(value, f, indent=1, allow_nan=False); f.write('\n'); f.flush(); os.fsync(f.fileno())
    need(json.loads(tmp.read_text()) == value, 'JSON readback differs')
    os.replace(tmp, path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--readout-root', required=True)
    parser.add_argument('--out-dir', required=True)
    parser.add_argument('--self-sha', required=True)
    args = parser.parse_args(argv); out = Path(args.out_dir); created = False
    started = time.monotonic()
    try:
        need(sha(__file__) == args.self_sha, 'postprocessor source SHA differs')
        need(set(os.environ) <= {'PATH', 'HOME', 'LC_CTYPE', 'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS'}, 'environment not clean')
        need(os.environ.get('OPENBLAS_NUM_THREADS') == os.environ.get('OMP_NUM_THREADS') == '1', 'single-thread environment required')
        maximum = Path('/sys/fs/cgroup/memory.max').read_text().strip()
        need(maximum != 'max', 'finite cgroup memory limit required')
        need(int(maximum) - int(Path('/sys/fs/cgroup/memory.current').read_text()) >= 2 * (1 << 30), 'cgroup headroom below 2 GiB')
        os.nice(19); resource.setrlimit(resource.RLIMIT_AS, (3 << 30, 3 << 30)); resource.setrlimit(resource.RLIMIT_CPU, (600, 600))
        cfg, cmap, book, pins, series, targets = completion_inputs(args.readout_root)
        # Use a new sibling output, never a frozen data path or the active reader directory.
        root = Path(args.readout_root).resolve(); out = out.resolve()
        need(out.parent == root.parent and out.name.startswith('ksr_terminal_audit_'), 'output must be a new ksr_terminal_audit_* sibling directory')
        out.mkdir(exist_ok=False); created = True
        checks, a = check_gate4_and_axes(cfg, cmap, pins, series, targets)
        description = build_description(cfg, cmap, book, a)
        check_hashes(pins)
        result = {'status': 'DESCRIPTIVE_ONLY_NOT_A_VERDICT', 'utc': iso(time.time()),
                  'device': Path(__file__).name, 'self_sha256': sha(__file__), 'argv': sys.argv,
                  'runtime_versions': {'python': sys.version, 'numpy': np.__version__},
                  'input_sha256': pins, 'technical_checks': checks, **description,
                  'units': {'dbar_compounded_bps': 'mean daily per-path compound NAV return difference, bps/day; r already includes fixed 2x',
                            'channels': 'native bps/anchor/gross summed within the same full UTC days, multiplied by GM=2, NAV bps/day',
                            'car': 'funding PAID; positive is more paid, not a benefit',
                            'cst': 'fees PAID; positive is more paid',
                            'compounding_minus_g_bps': 'daily-compounding difference minus arithmetic g channel; not forced to zero',
                            'g_minus_price_net_NAV_bps': 'g - (pnl - car - cst - unk); reported, not forced to zero'},
                  'interaction': '(FULL_m0 - S0_m0) - (SEAT_ONLY_m0 - S0_m0) - (COMP_ONLY_m0 - S0_m0), separately per seed/path/day before any average',
                  'path_identity': 'Rows 0..31 follow pinned fa_ladsave seed checks and order. Series has no explicit path-id array; original PATH files were removed, so historical per-PATH identity cannot be independently rechecked.',
                  'limits': ['No new significance/non-inferiority/approximately-zero threshold; no causal claim or overall candidate verdict.',
                             'Monthly and full-pre2026 rows are descriptive; they do not replace frozen H1 decision windows.',
                             'H2 age mechanism remains unrun. Current historical exporter hash is checked; it is not a new proof of code deployed at historical execution time.',
                             'PRE2026_G4_COMMON is the original 2023-06-30T04Z comparison window; PRE2026_ALL_AVAILABLE starts at the series first anchor.'],
                  'runtime_seconds': time.monotonic() - started, 'maxrss_native': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
        write_json(out / 'KSR_TERMINAL_AUDIT.json', result)
        receipt = {'status': 'DONE', 'result': str(out / 'KSR_TERMINAL_AUDIT.json'),
                   'result_sha256': sha(out / 'KSR_TERMINAL_AUDIT.json'), 'self_sha256': sha(__file__),
                   'pid': os.getpid(), 'pgid': os.getpgrp()}
        write_json(out / 'DONE.json', receipt)
        print('KSR_POSTPROCESS_DONE ' + json.dumps(receipt, sort_keys=True), flush=True)
        return 0
    except Exception as exc:
        failed = {'status': 'UNAVAILABLE', 'type': type(exc).__name__, 'reason': str(exc)}
        if created:
            try:
                write_json(out / 'FAILED.json', failed)
            except Exception as write_error:
                failed['receipt_write_error'] = type(write_error).__name__ + ': ' + str(write_error)
        print('KSR_POSTPROCESS_UNAVAILABLE ' + json.dumps(failed, sort_keys=True), flush=True)
        return 2


if __name__ == '__main__':
    sys.exit(main())
