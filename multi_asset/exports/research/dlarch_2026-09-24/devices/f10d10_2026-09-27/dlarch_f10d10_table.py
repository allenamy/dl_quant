#!/usr/bin/env python3
"""dlarch_f10d10_table.py -- the October D10 joint-arm reading table lead asked for (11:0xZ), NUMBERS ONLY, no verdict.
Written after dlarch_paired_d.py (4e293147, unchanged) produced PAIRED_D_D10_2026-09-27.json and before this table's own new
quantities (truncated-segment d, 2x-compounded drawdown, channels) were computed.

Per seed s in 42 / 2027 / 7, arm = DLARCH_D10_s (King + F10 on D10 features), base = DLARCH_REF_NC_s<s>X (in-service NC, same seed):
  d_seg = dbar(arm) - dbar(NC_s) in bps/day (frozen news_stats caliber). Every RETAIN receipt reports dbar against the SAME control
  DLARCH_REF_NC_s42X (asserted), so d = dbar_vs_control(arm) - dbar_vs_control(NC_s) exactly (the s42 reference is the control
  itself: its dbar is 0 by construction, read from its SELFCTL receipt, not assumed). Segments: pre2026, 2026 (extended to the axis
  end 09-18T20Z), 2026_frozen_truncated (frozen SEG, to 08-31), plus 2023H2 / 2024 / 2025. The pre2026 / 2026 d must equal
  paired_d's d_per_seed (asserted to 1e-12) -- the two routes are independent (scalar difference here vs frozen-judge series there).
  T0 reference column, sd(d), sigma_ref, SE: copied from PAIRED_D (not recomputed).
REVISION 1 (before its output was delivered): the first run compounded 1 + GM * r, but r is already the NAV return at the fixed
  2x gross -- measured on the NC s2027 series: r * 1e4 == 2 * g exactly, the same relation rc_read's D_bar ~ GM x g shows. That run
  doubled the leverage; its drawdowns (~0.39-0.47) are void and were not delivered. Fixed: nav = cumprod(1 + r).
Drawdown guard (rule: vs NC same seed, pre-2026, fixed 2x per-anchor compounding, pp): maxDD of nav = cumprod(1 + r) over the
  pre-2026 anchors, per path, mean over the 32 paths; reported arm - NC in pp (negative = arm deeper). The frozen judge's maxdd_5m
  path_mean (5-minute NAV; what earlier verdicts used) is reported beside it and labelled.
Channels (NAV bps/day, x GM, arm - NC, same seed, full UTC days as news_stats.full_days): pnl (price), car (+ = funding paid), cst
  (fees), unk, and g; the per-path channel series are already in bps (rc_read.py / rc_decomp.py caliber: x GM, no 1e4), r is a
  fraction (dbar multiplies it by 1e4). The closure g - (pnl - car - cst - unk) is REPORTED, not asserted (rc_decomp measured a
  residual up to ~1e-6).
usage: dlarch_f10d10_table.py <env-whitelist> <receipts_dir> <paired_d.json> <out.json> [<arm prefix, default D10>]
  rev 2: optional arm prefix (e.g. D10RR for the descriptive re-read cells DLARCH_D10RR_s<seed>); default keeps the D10 run's meaning.
"""
import glob, hashlib, json, os, sys, time
import numpy as np

WL = set(sys.argv[1].split(','))
_x = sorted(set(os.environ) - WL - {'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS'})
assert not _x, f'env outside whitelist: {_x}'
RD, PDP, OUT = sys.argv[2:5]; ARMP = sys.argv[5] if len(sys.argv) > 5 else 'D10'
ENG = '/dev/shm/news_2026-09-23/engine'; sys.path.insert(0, ENG)
NS_SHA = '7141ba42ab227b9f35b48acce62d5e2a2494f364fdf6a83189974cb2af67e03c'
CONTROL = 'DLARCH_REF_NC_s42X_scaled_rule_raw_UAFE'; SEEDS = (42, 2027, 7); DAY = 86400


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


assert sha(f'{ENG}/news_stats.py') == NS_SHA
import news_stats as NS, bt_tables as BT, bt_driver_lib as DL   # noqa: E402
NS.BT, NS.DL = BT, DL
GM = float(BT.GM) if hasattr(BT, 'GM') else float(DL.GM)


def one(pattern):
    hits = glob.glob(os.path.join(RD, pattern)); assert len(hits) == 1, (pattern, hits)
    d = hits[0]; rj = glob.glob(os.path.join(d, 'RETAIN_*.json')); assert len(rj) == 1, rj
    r = json.load(open(rj[0])); assert r['control_tag'] == CONTROL, (rj[0], r['control_tag'])
    return r, rj[0]


PD = json.load(open(PDP)); rec = {'device': 'dlarch_f10d10_table.py', 'self_sha256': sha(os.path.abspath(__file__)),
                                   'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'status': 'NUMBERS_ONLY_NO_VERDICT',
                                   'paired_d': {'path': PDP, 'sha256': sha(PDP)}, 'arm_prefix': ARMP, 'GM': GM, 'receipts': {}, 'per_seed': {}}
SEGS = ('2023H2', '2024', '2025', 'pre2026', '2026', '2026_frozen_truncated')
for s in SEEDS:
    ra, pa = one(f'RETAIN_{ARMP}_s{s}_2026-09-27.json')
    rb, pb = one(f'RETAIN_REFNC_s{s}_*2026-09-26.json')
    assert ra['tag'] == f'DLARCH_{ARMP}_s{s}_scaled_rule_raw_UAFE' and rb['tag'] == f'DLARCH_REF_NC_s{s}X_scaled_rule_raw_UAFE'
    rec['receipts'][str(s)] = {'arm': [pa, sha(pa)], 'nc': [pb, sha(pb)]}
    row = {'d_bps_day': {g: ra['dbar_vs_control'][g]['mean_bps_per_day'] - rb['dbar_vs_control'][g]['mean_bps_per_day'] for g in SEGS},
           'n_days': {g: ra['dbar_vs_control'][g]['n_days'] for g in SEGS}}
    for g in ('pre2026', '2026'):
        want = PD['per_baseline']['DLARCH_REF_NC_s']['segments'][g]['d_per_seed'][str(s)]
        assert abs(row['d_bps_day'][g] - want) < 1e-12, (s, g, row['d_bps_day'][g], want)
    Sa = np.load(ra['small_series']['path']); Sb = np.load(rb['small_series']['path'])
    assert sha(ra['small_series']['path']) == ra['small_series']['sha256'] and sha(rb['small_series']['path']) == rb['small_series']['sha256']
    A = Sa['anchors'].astype(np.int64); assert np.array_equal(A, Sb['anchors'].astype(np.int64))
    seg_masks = {g: NS.seg_mask(A, *NS.SEG[g]) for g in ('2023H2', '2024', '2025', 'pre2026')}
    seg_masks['2026'] = NS.seg_mask(A, '2026-01-01T00:00:00Z', time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(int(A[-1]))))
    seg_masks['2026_frozen_truncated'] = NS.seg_mask(A, *NS.SEG['2026'])
    # drawdown, fixed 2x per-anchor compounding, pre-2026
    m = seg_masks['pre2026']

    def dd2x(S):
        nav = np.cumprod(1.0 + S['r_per_path'][:, m], axis=1)   # r is ALREADY the NAV return at the fixed 2x gross (r*1e4 == GM*g, measured)
        peak = np.maximum.accumulate(np.concatenate([np.ones((nav.shape[0], 1)), nav], 1), axis=1)[:, 1:]
        return float(np.mean(np.max(1.0 - nav / peak, axis=1)))
    da, db = dd2x(Sa), dd2x(Sb)
    row['drawdown_pre2026'] = {'maxdd_2x_anchor_compounded_arm': da, 'maxdd_2x_anchor_compounded_nc': db,
                               'arm_minus_nc_pp_2x': 100 * (da - db), 'sign': '+ = arm drawdown DEEPER than NC',
                               'maxdd_5m_path_mean_arm': ra['judge_table']['pre2026']['paths']['maxdd_5m']['path_mean'],
                               'maxdd_5m_path_mean_nc': rb['judge_table']['pre2026']['paths']['maxdd_5m']['path_mean'],
                               'maxdd_5m_arm_minus_nc_pp': 100 * (ra['judge_table']['pre2026']['paths']['maxdd_5m']['path_mean']
                                                                   - rb['judge_table']['pre2026']['paths']['maxdd_5m']['path_mean']),
                               'maxdd_5m_sign': 'recorded as negative fractions: - = arm deeper'}
    day = (A // DAY) * DAY; ch = {}
    for g, mm in seg_masks.items():
        days = NS.full_days(A, mm); keep = mm & np.isin(day, days); c = {}
        for k in ('pnl', 'car', 'cst', 'unk', 'g'):
            x = Sa[k + '_per_path'].mean(0) - Sb[k + '_per_path'].mean(0)
            c[k] = float(GM * np.bincount(np.searchsorted(days, day[keep]), weights=x[keep], minlength=len(days)).mean())
        c['closure_g_minus_(pnl-car-cst-unk)'] = c['g'] - (c['pnl'] - c['car'] - c['cst'] - c['unk'])
        ch[g] = c
    row['channels_NAV_bps_day_arm_minus_nc'] = ch
    rec['per_seed'][str(s)] = row
nc = PD['per_baseline']['DLARCH_REF_NC_s']['segments']; t0 = PD['per_baseline']['DLARCH_T0_s']['segments']
rec['summary'] = {g: {'mean_d': nc[g]['mean_d'], 'n_positive': nc[g]['n_positive'], 'sd_d': nc[g]['sd_d'], 'sigma_ref': nc[g]['sigma_ref'],
                      'SE': nc[g]['SE'], 'SE_branch': nc[g]['branch_taken'], 'three_SE': nc[g]['three_SE'],
                      'T0_reference_mean_d': t0[g]['mean_d'], 'T0_reference_d_per_seed': t0[g]['d_per_seed']} for g in ('pre2026', '2026')}
rec['summary']['2026_frozen_truncated'] = {'mean_d': float(np.mean([rec['per_seed'][str(s)]['d_bps_day']['2026_frozen_truncated'] for s in SEEDS])),
                                           'd_per_seed': {str(s): rec['per_seed'][str(s)]['d_bps_day']['2026_frozen_truncated'] for s in SEEDS},
                                           'note': 'frozen SEG 2026 (to 08-31); SE / thresholds not recomputed for this segment'}
json.dump(rec, open(OUT + '.tmp', 'w'), indent=1, allow_nan=False)  # durable-exempt: receipt, parsed back and compared before the replace
assert json.load(open(OUT + '.tmp'))['self_sha256'] == rec['self_sha256']; os.replace(OUT + '.tmp', OUT)
print('F10D10_TABLE out=%s sha256=%s' % (OUT, sha(OUT)), flush=True)
