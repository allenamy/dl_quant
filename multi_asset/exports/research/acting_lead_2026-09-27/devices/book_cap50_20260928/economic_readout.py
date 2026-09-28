"""Complete-day, paired readout. Does not modify simulations or release gates.

Primary metrics are calculated on each execution path, THEN aggregated.
Bootstrap units are market days, with paired path differences averaged first.
Fee x1.25 is fixed-action accounting sensitivity, not a new execution policy.
"""
import argparse
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time

import numpy as np

ENGINE = Path('/dev/shm/news2_2026-09-23/engine')
STATS_SHA = '7141ba42ab227b9f35b48acce62d5e2a2494f364fdf6a83189974cb2af67e03c'
WINDOWS = {
    '2023H2': ('2023-06-30T04:00:00Z', '2023-12-31T20:00:00Z'),
    '2024': ('2024-01-01T00:00:00Z', '2024-12-31T20:00:00Z'),
    '2025': ('2025-01-01T00:00:00Z', '2025-12-31T20:00:00Z'),
    'pre2026': ('2023-06-30T04:00:00Z', '2025-12-31T20:00:00Z'),
    '2026_JanAug': ('2026-01-01T00:00:00Z', '2026-08-31T20:00:00Z'),
    '2026_original_truncated': ('2026-01-01T00:00:00Z', '2026-08-31T00:00:00Z'),
    'Sep01_18_descriptive': ('2026-09-01T00:00:00Z', '2026-09-18T20:00:00Z'),
    'full_recipe': ('2023-06-30T04:00:00Z', '2026-09-18T20:00:00Z'),
}


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(4 << 20), b''):
            h.update(b)
    return h.hexdigest()


def dist(values):
    a = np.asarray(values, dtype=float)
    if not a.size or not np.isfinite(a).all():
        raise ValueError('missing/nonfinite metric')
    return dict(mean=float(a.mean()), median=float(np.median(a)),
                p05=float(np.percentile(a, 5)), p95=float(np.percentile(a, 95)))


def ci30(x, S):
    # Frozen non-circular MBB becomes a single unchanged block for n <= 30.
    # Do not report its zero-width output as statistical confidence.
    return S.boot(x, 30)['ci95_bps'] if len(x) > 30 else None


def path_metrics(p, mask, days, S, BT):
    A, r = p['A'][mask], p['r'][mask]
    rd = S.daily_on(A, r, days)
    if len(rd) < 2 or np.any(rd <= -1) or not np.isfinite(rd).all():
        raise ValueError('daily return not measurable')
    nav = np.cumprod(1 + r)
    result = dict(return_compound=float(np.prod(1 + rd) - 1),
                  cagr=BT.cagr(rd), sharpe_daily=BT.sharpe(rd),
                  annualized_vol=float(rd.std(ddof=1) * math.sqrt(365)),
                  mean_daily_bps=float(1e4 * rd.mean()),
                  maxdd_5m=BT.maxdd_5m(p, mask), worst_day=float(rd.min()),
                  days_below_minus2pct=int((rd < -.02).sum()),
                  days_below_minus4pct=int((rd < -.04).sum()),
                  crossed_entry_minus25pct=int(np.any(nav < .75)),
                  stop_flatten_events=float(p['dstop'][mask].sum()),
                  single_name_stop_events=float(p['nstop'][mask].sum()),
                  hold_fraction=float(p['hold'][mask].mean()),
                  halt_fraction=float(p['halt'][mask].mean()),
                  turnover_over_sizing_gross_per_anchor=float(p['tau'][mask].mean()),
                  unknown_notional_over_sizing_gross=float(p['unk_notional'][mask].mean()))
    # Terms are additive simple returns at 2x NAV, not dollar totals or the
    # compounding of each isolated leg. Carry positive means a cash cost.
    for key, label in [('pnl', 'price'), ('car', 'funding_paid'),
                       ('cst', 'fee'), ('unk', 'unknown_excluded')]:
        result[label + '_nav_bps_per_day_additive'] = float(2 * p[key][mask].sum() / len(days))
    additive = (result['price_nav_bps_per_day_additive']
                - result['funding_paid_nav_bps_per_day_additive']
                - result['fee_nav_bps_per_day_additive']
                - result['unknown_excluded_nav_bps_per_day_additive'])
    result['daily_compounding_interaction_bps'] = result['mean_daily_bps'] - additive
    stressed_r = r - .25 * 2 * p['cst'][mask] / 1e4
    if np.any(stressed_r <= -1) or not np.isfinite(stressed_r).all():
        raise ValueError('invalid accounting stress')
    stress_day = S.daily_on(A, stressed_r, days)
    return result, rd, stress_day


def run(root, out):
    terminal = root / 'TERMINAL.json'
    t = json.loads(terminal.read_text())
    if t['rc'] != 0 or t['status'] != 'EXPLORATORY_COMPARISON_COMPLETE_NOT_RELEASE':
        raise ValueError('batch not complete')
    if sha(ENGINE / 'news_stats.py') != STATS_SHA:
        raise ValueError('stats source drift')
    sys.path.insert(0, str(ENGINE))
    import news_stats as S
    import bt_tables as BT
    import bt_driver_lib as DL
    for f, h in S.DEV.items():
        if sha(ENGINE / f) != h:
            raise ValueError('stats dependency drift: ' + f)
    S.BT, S.DL = BT, DL
    identity = json.loads((root / 'ENGINE_IDENTITIES.json').read_text())
    if len(identity) != 2 or not all(x['all_arrays_bitwise'] for x in identity):
        raise ValueError('baseline identity incomplete')
    rec = dict(status='EXPLORATORY_NOT_RELEASE', utc=time.strftime('%FT%TZ', time.gmtime()),
               source_sha256=sha(__file__), terminal_sha256=sha(terminal),
               stats_sha256=STATS_SHA, dependencies=S.DEV, windows=WINDOWS,
               aggregation='metric per path then distribution; paired market-day MBB; 32 paths are not independent markets',
               clock='six 4h windows per UTC date; terminal window includes returns through next 00Z',
               stress='1.25x observed fees, actions and stops fixed; not a policy rerun',
               python=sys.executable, numpy=np.__version__, results={})
    for seed in (42, 2027):
        at = f'ALLOC_cap050_shared_s{seed}X_scaled_rule_raw_UAFE'
        rt = f'DLARCH_REF_NC_s{seed}X_scaled_rule_raw_UAFE'
        pa, fa = S.load_cell(str(root / f'cells/cap050_shared_s{seed}/runs/{at}'), at)
        pr, fr = S.load_cell(f'/workspace/dlarch_2026-09-24/chain/ref_nc_s{seed}X/runs/{rt}', rt)
        if len(pa) != 32 or len(pr) != 32 or not np.array_equal(pa[0]['A'], pr[0]['A']):
            raise ValueError('paired population incomplete')
        for p in pa + pr:
            if not np.isfinite(p['nav5']).all() or BT.g_identity_err(p) > 1e-5:
                raise ValueError('cash identity or 5m finite gate failed')
        A = pa[0]['A']
        sr = dict(candidate_paths=fa, baseline_paths=fr, results={})
        for label, (lo, hi) in WINDOWS.items():
            m0 = S.seg_mask(A, lo, hi)
            days = S.full_days(A, m0)
            m = m0 & np.isin(A // 86400 * 86400, days)
            if int(m.sum()) != 6 * len(days):
                raise ValueError('incomplete daily population')
            am, bm, dd, ds = [], [], [], []
            for a, b in zip(pa, pr):
                ar, ad, astress = path_metrics(a, m, days, S, BT)
                br, bd, bstress = path_metrics(b, m, days, S, BT)
                am.append(ar); bm.append(br); dd.append(ad-bd); ds.append(astress-bstress)
            d = np.stack(dd).mean(0)
            sd = np.stack(ds).mean(0)
            paired = {k: dist([a[k]-b[k] for a,b in zip(am,bm)]) for k in am[0]}
            sr['results'][label] = dict(n_days=len(days), n_anchors=int(m.sum()),
                first_anchor=int(A[m][0]), last_anchor=int(A[m][-1]),
                baseline={k:dist([a[k] for a in bm]) for k in bm[0]},
                candidate={k:dist([a[k] for a in am]) for k in am[0]},
                paired_metric_difference=paired,
                paired_daily_bps=float(1e4*d.mean()), ci95_bps=ci30(d,S),
                ci_status='MEASURED_30D_MBB' if len(days)>30 else 'UNAVAILABLE_SHORTER_THAN_BLOCK',
                fee125_paired_daily_bps=float(1e4*sd.mean()), fee125_ci95_bps=ci30(sd,S),
                paired_market_days=[int(x) for x in days], paired_daily_returns=d.tolist())
            print('processed',seed,label,len(days),flush=True)
        rec['results'][str(seed)] = sr
        del pa, pr
        gc.collect()
    with open(out, 'x') as f:
        json.dump(rec, f, indent=2, allow_nan=False)
        f.flush(); os.fsync(f.fileno())
    print('READOUT_COMPLETE',sha(out),flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    run(args.root,args.out)
