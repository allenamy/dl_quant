#!/usr/bin/env python3
"""dlarch_ksr_book.py -- King serving refresh, BOOK-layer reader (DECISION_RULE_king_serving_refresh_2026-09-27.md, lead 5b4fc6cda +
revision 1 c1f9571b5). Transcribes §1 (book), §2 (book REJECT / NON_INFERIOR) and §3 (guard rails); sets no threshold of its own.
Committed before ANY KSR cell exists (fresh2's driver 65df8b070 has not started). Caliber = fresh2's rc_read.py (3dd2d635): frozen
news_stats (7141ba42) dbar per F10 seed vs the paired base cell, MBB block 30 with the frozen B / RNG, NAV channels x GM.

INPUT: a cell-map JSON {"S1": {"m0": "KSR_S1_m0", ...}, "S0": {"m0": "KSR_S0_m0", ...}, "RED": {"m0": "KSR_RED_m0"},
                       "HYB": {"SEAT_ONLY": "<cell>", "COMP_ONLY": "<cell>"}}   (RED / HYB optional)
  series = <series_dir>/SER_<cell>_s{42,2027}.npz (keys anchors, {r,pnl,car,cst,g}_per_path (32, n)); targets stats =
  <tstats_dir>/<cell>_s{seed}.npz (anchors, sum_abs_dw, WL, legs_E_ts) for the guard rails.
SEGMENTS: H1 years Y in 2023/2024/2025 = [Y-10-01, Y+1-01-01); H1 merged = their union; 2026F = [2026-07-01, last anchor]; carry-over
  (descriptive only, design §3.2) = [Y+1-01-01, Y+1-06-01) after each H1 window. Full UTC days only (news_stats.full_days).
§1 d_{m,s,seg} = dbar(S1 m, seed s) - dbar(S0 m, seed s), bps/day; 16 pairs (8 members x 2 seeds), each evaluated, never ensembled.
  SE_seg = max(MBB30_SE of the pair-averaged daily d series, sd(d_{m,s}) / sqrt(16)) (monthly rule §1, which this rule cites).
§2 book: REJECT iff (H1 merged or any H1 year) D < 0 and MBB95 upper < 0, or a §3 guard fails; NON_INFERIOR iff H1 merged
  D >= -max(0.5, 3.5 SE) and not REJECT. (IMPROVE is not assessed: rule §2 last line.) The overall OPTION_FOR_USER / UNDECIDED
  verdict also needs the IC gate and the 2026F IC point, which live in KSR_IC (dlarch_ksr_read.py); this device reports the book
  half only and says so.
§3 guards: (a) drawdown: per H1 year, maxDD of the fixed-2x per-anchor compounded NAV of each path (nav = cumprod(1 + r); rev 1: r is already
  the NAV return at the fixed 2x gross, r * 1e4 == GM * g measured on the NC s2027 series, so no extra GM factor) over
  the window's anchors), mean over paths and (m, s); then mean over the three years; FAIL iff S1 is worse than S0 by > 3 pp.
  (b) switch anchors: for every S1 cell and seed, sum|dw| and the seat change L1(WL_t - WL_{t-1}) at each window's first anchor and
  at the first anchor after it (hand-back), against the p99 of the same cell's non-switch anchors; any exceedance => the rule
  requires a hand-over smoothing design with any recommendation (reported as FLAG, not a verdict change).
Also reported (no gate): RED and HYB cells' D vs S0 m0 per segment with channels; per (m, s) table; carry-over segments.
usage: dlarch_ksr_book.py <env-whitelist> <cell_map.json> <series_dir> <tstats_dir> <out.json>
Terminal line: 'KSR_BOOK BOOK_REJECT=<bool> BOOK_NON_INFERIOR=<bool> ...' (line start).
"""
import calendar, hashlib, json, os, sys, time
import numpy as np

WL = set(sys.argv[1].split(','))
_x = sorted(set(os.environ) - WL - {'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS'})
assert not _x, f'env outside whitelist: {_x}'
CMAP, SDIR, TDIR, OUT = sys.argv[2:6]
ENG = '/dev/shm/news_2026-09-23/engine'; sys.path.insert(0, ENG)
NS_SHA = '7141ba42ab227b9f35b48acce62d5e2a2494f364fdf6a83189974cb2af67e03c'
SEEDS = ('42', '2027'); DAY = 86400; H1 = (2023, 2024, 2025)
T_ = lambda y, m, d=1: calendar.timegm((y, m, d, 0, 0, 0))
iso = lambda t: time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(int(t)))


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
cmap = json.load(open(CMAP))
MEM = sorted(cmap['S1']); assert MEM == [f'm{i}' for i in range(8)] and sorted(cmap['S0']) == MEM
rec = {'device': 'dlarch_ksr_book.py', 'self_sha256': sha(os.path.abspath(__file__)), 'utc': iso(time.time()), 'status': 'BOOK_HALF_OF_THE_VERDICT',
       'rule': 'DECISION_RULE_king_serving_refresh_2026-09-27.md 5b4fc6cda + revision 1 c1f9571b5, transcribed', 'GM': GM,
       'cell_map': {'path': CMAP, 'sha256': sha(CMAP), 'map': cmap}, 'inputs': {}}
Z = {}


def ser(cell, s):
    if (cell, s) not in Z:
        p = f'{SDIR}/SER_{cell}_s{s}.npz'; rec['inputs'][p] = sha(p); Z[(cell, s)] = np.load(p)
    return Z[(cell, s)]


A = ser(cmap['S0']['m0'], '42')['anchors'].astype(np.int64)
cells = [c for grp in ('S1', 'S0') for c in cmap[grp].values()] + list(cmap.get('RED', {}).values()) + list(cmap.get('HYB', {}).values())
for c in cells:
    for s in SEEDS: assert np.array_equal(ser(c, s)['anchors'].astype(np.int64), A), (c, s)
day = (A // DAY) * DAY
SEG = {f'H1_{y}': (A >= T_(y, 10)) & (A < T_(y + 1, 1)) for y in H1}
SEG['H1_merged'] = SEG['H1_2023'] | SEG['H1_2024'] | SEG['H1_2025']
SEG['2026F'] = A >= T_(2026, 7)
for y in H1: SEG[f'carryover_{y + 1}H1'] = (A >= T_(y + 1, 1)) & (A < T_(y + 1, 6))
rec['segments'] = {k: [iso(A[m][0]), iso(A[m][-1]), int(m.sum())] for k, m in SEG.items() if m.any()}
paths = lambda c, s: [{'A': A, 'r': ser(c, s)['r_per_path'][j]} for j in range(32)]


def mbb(x):   # verbatim statistic of rc_read.mbb / mr_read.mbb (frozen block 30, B, RNG)
    idx = BT.mbb_indices(len(x), 30, NS.B, NS.RNG); mb = x[idx].mean(1)
    return float(1e4 * mb.std(ddof=1)), [float(1e4 * np.percentile(mb, 2.5)), float(1e4 * np.percentile(mb, 97.5))]


def chan(c, b, ch, m, s):
    days = NS.full_days(A, m); keep = m & np.isin(day, days)
    x = ser(c, s)[ch + '_per_path'].mean(0) - ser(b, s)[ch + '_per_path'].mean(0)
    return float(GM * np.bincount(np.searchsorted(days, day[keep]), weights=x[keep], minlength=len(days)).mean())


def pair_table(pairs, seg):
    """pairs = [(arm cell, base cell, label)]; returns per-pair D, the pair-averaged daily series stats, and channels"""
    m = SEG[seg]; days = NS.full_days(A, m); per = {}; daily = []
    for c, b, lab in pairs:
        for s in SEEDS:
            x = NS.dbar(paths(c, s), paths(b, s), m, days)[0]; daily.append(x)
            per[f'{lab}_s{s}'] = {'D': float(1e4 * x.mean()), 'channels_NAV_bps_day': {ch: chan(c, b, ch, m, s) for ch in ('pnl', 'car', 'cst', 'g')}}
    avg = np.mean(daily, axis=0); se_b, ci = mbb(avg); ds = np.array([v['D'] for v in per.values()])
    return {'n_days': int(len(days)), 'n_pairs': len(ds), 'D': float(1e4 * avg.mean()), 'MBB30_SE': se_b, 'MBB95': ci,
            'sd_pairs': float(ds.std(ddof=1)) if len(ds) > 1 else None, 'pairs_positive': int((ds > 0).sum()), 'per_pair': per}


S1P = [(cmap['S1'][k], cmap['S0'][k], k) for k in MEM]
book = {seg: pair_table(S1P, seg) for seg in SEG if SEG[seg].any()}
for seg, t in book.items():
    t['SE_rule'] = max(t['MBB30_SE'], t['sd_pairs'] / np.sqrt(16)) if t['sd_pairs'] is not None else t['MBB30_SE']
rec['S1_vs_S0'] = book


# ---- §3 (a) drawdown: fixed 2x per-anchor compounded NAV inside each H1 window
def maxdd(c, s, m):
    r = ser(c, s)['r_per_path'][:, m]; nav = np.cumprod(1.0 + r, axis=1)   # rev 1: r is already the NAV return at the fixed 2x gross
    peak = np.maximum.accumulate(np.concatenate([np.ones((nav.shape[0], 1)), nav], 1), axis=1)[:, 1:]
    return float(np.mean(np.max(1.0 - nav / peak, axis=1)))


dd = {}
for y in H1:
    m = SEG[f'H1_{y}']
    dd[str(y)] = {'S1': float(np.mean([maxdd(cmap['S1'][k], s, m) for k in MEM for s in SEEDS])),
                  'S0': float(np.mean([maxdd(cmap['S0'][k], s, m) for k in MEM for s in SEEDS]))}
dd_s1 = float(np.mean([v['S1'] for v in dd.values()])); dd_s0 = float(np.mean([v['S0'] for v in dd.values()]))
guard_dd = {'per_year': dd, 'mean_S1': dd_s1, 'mean_S0': dd_s0, 'S1_minus_S0_pp': 100 * (dd_s1 - dd_s0),
            'FAIL': bool(100 * (dd_s1 - dd_s0) > 3.0), 'basis': 'maxDD of nav = cumprod(1 + r) per path over the window anchors (r = NAV return at fixed 2x); mean over 32 paths x 16 (m, s)'}

# ---- §3 (b) switch anchors
wins = [(T_(y, 10), T_(y + 1, 1)) for y in H1] + [(T_(2026, 7), None)]
sw_rows = {}
for k in MEM:
    for s in SEEDS:
        p = f"{TDIR}/{cmap['S1'][k]}_s{s}.npz"; rec['inputs'][p] = sha(p); t = np.load(p)
        ta = t['anchors'].astype(np.int64); sdw = t['sum_abs_dw'].astype(np.float64)
        la = t['legs_E_ts'].astype(np.int64); W_ = t['WL'].astype(np.float64)
        dseat = np.full(len(la), np.nan); dseat[1:] = np.abs(np.diff(W_, axis=0)).sum(1)
        sw_t = set(); sw_l = set()
        for lo, hi in wins:
            for edge in ([lo] + ([hi] if hi else [])):
                i = int(np.searchsorted(ta, edge)); j = int(np.searchsorted(la, edge))
                if i < len(ta): sw_t.add(i)
                if j < len(la): sw_l.add(j)
        nsw_t = np.array([i for i in range(len(ta)) if i not in sw_t and np.isfinite(sdw[i])])
        nsw_l = np.array([j for j in range(len(la)) if j not in sw_l and np.isfinite(dseat[j])])
        p99_t = float(np.percentile(sdw[nsw_t], 99)); p99_l = float(np.percentile(dseat[nsw_l], 99))
        ex_t = {iso(ta[i]): float(sdw[i]) for i in sorted(sw_t) if np.isfinite(sdw[i]) and sdw[i] > p99_t}
        ex_l = {iso(la[j]): float(dseat[j]) for j in sorted(sw_l) if np.isfinite(dseat[j]) and dseat[j] > p99_l}
        sw_rows[f'{k}_s{s}'] = {'p99_sum_abs_dw_nonswitch': p99_t, 'p99_seat_change_nonswitch': p99_l,
                                'switch_sum_abs_dw': {iso(ta[i]): (float(sdw[i]) if np.isfinite(sdw[i]) else None) for i in sorted(sw_t)},
                                'switch_seat_change': {iso(la[j]): (float(dseat[j]) if np.isfinite(dseat[j]) else None) for j in sorted(sw_l)},
                                'exceed_sum_abs_dw': ex_t, 'exceed_seat_change': ex_l}
guard_sw = {'per_pair': sw_rows, 'FLAG_handover_design_required': bool(any(v['exceed_sum_abs_dw'] or v['exceed_seat_change'] for v in sw_rows.values())),
            'note': 'rule §3: exceeding the non-switch p99 does not change the verdict; it obliges a hand-over smoothing design with any recommendation'}
rec['guards'] = {'drawdown': guard_dd, 'switch_anchors': guard_sw}

# ---- §2 book verdict (half)
h = book['H1_merged']
rej_seg = [seg for seg in ['H1_merged'] + [f'H1_{y}' for y in H1] if book[seg]['D'] < 0 and book[seg]['MBB95'][1] < 0]
REJECT = bool(rej_seg or guard_dd['FAIL'])
NI = bool((h['D'] >= -max(0.5, 3.5 * h['SE_rule'])) and not REJECT)
rec['BOOK'] = {'REJECT': REJECT, 'reject_segments': rej_seg, 'drawdown_guard_fail': guard_dd['FAIL'], 'NON_INFERIOR': NI,
               'NI_threshold': -max(0.5, 3.5 * h['SE_rule']), 'H1_merged_D': h['D'], 'H1_merged_SE_rule': h['SE_rule'],
               'IMPROVE': 'NOT ASSESSED (rule §2: no power; non-inferiority only)',
               'overall_verdict': 'NOT GIVEN HERE: needs the IC gate and the 2026F IC point (KSR_IC receipt); lead assembles'}

# ---- descriptive: RED and hybrid cells vs S0 m0
desc = {}
for grp in ('RED', 'HYB'):
    for lab, c in cmap.get(grp, {}).items():
        desc[f'{grp}_{lab}'] = {seg: pair_table([(c, cmap['S0']['m0'], lab)], seg) for seg in ('H1_merged', '2026F') + tuple(f'H1_{y}' for y in H1)}
rec['descriptive_vs_S0_m0'] = desc

json.dump(rec, open(OUT + '.tmp', 'w'), indent=1, allow_nan=False)  # durable-exempt: receipt, read back and compared before the atomic replace
back = json.load(open(OUT + '.tmp')); assert back['self_sha256'] == rec['self_sha256'] and back['BOOK'] == json.loads(json.dumps(rec['BOOK']))
os.replace(OUT + '.tmp', OUT)
print('KSR_BOOK BOOK_REJECT=%s BOOK_NON_INFERIOR=%s DD_FAIL=%s HANDOVER_FLAG=%s out=%s sha256=%s' % (
    REJECT, NI, guard_dd['FAIL'], guard_sw['FLAG_handover_design_required'], OUT, sha(OUT)), flush=True)
