#!/usr/bin/env python3
"""dlarch_ksr_read.py -- King serving refresh, IC-layer reader and gates 1-2 (DECISION_RULE_king_serving_refresh_2026-09-27.md,
lead 5b4fc6cda; design 1eb29acae). Transcribes the rule; sets no threshold of its own. Committed before any arm is trained.

MODE gate12 <out.json> <S0_retrain_dir> <S1_m0_dir> <S1_m0_dup_dir> [serving_receipt.json]
  gate 1: dlarch_ksr_train.py --arm A0 --rs 0 must reproduce the in-service KING_OOF a10b8725 score arrays BITWISE (P, E_ts,
          symbols; model text shas are reported, not gated -- monthly-rule revision 1); the fold-2026 rows are reported separately
          (that fold's model is the SERVED model). The serving-side identity (booster file sha == the fold-2026 model) is fresh2's
          receipt (rule §8 item 5); if given, its path and sha are recorded here, not re-derived.
  gate 2: S1 m0 and its duplicate training: P bitwise equal.
MODE ic <out.json> <manifest.json>
  manifest = {"S0": {"m0": oof, ..., "m7": oof}, "arms": {ARM: {WINDOW: {"m0": oof, ...}}}}, WINDOW in 2023, 2024, 2025 (H1:
  Y-10-01 .. Y-12-31) and 2026F (2026-07-01 .. last T_net anchor). ARM in S1 (candidate), S2R, S2T (report only), RED (whatever
  the lead rules for gate 3 on the IC layer: S0 scores permuted within anchor inside the windows).
  Per window, member m: daily dIC_m(day) = IC(arm m) - IC(S0 m) on the window's days (T_net, frozen ic_series, MIN 20, one UTC
  day at a time); arm series = mean over members defined that day. H1 pooled = the three windows' days concatenated.
  RULE §1/§2 (transcribed): SE = max(MBB30 SE of the pooled arm series, sd_m / sqrt(8)) where sd_m = sd over members of the member
  means; z = mean / SE; IC gate = z >= 2.39 AND >= 2 of 3 H1 years with dIC > 0. 2026F: point estimate reported (rule: >= 0 for
  OPTION_FOR_USER). MBB: moving blocks over the concatenated days, B 2000, seed 20260927; blocks can straddle the gap between
  windows -- named, not corrected. y4s reported beside T_net. Age buckets: S1 model age (days since its training label end)
  [0,30) [30,60) [60,120); S0 age reported per window.
MODE spectrum <out.json> <manifest.json>
  offset spectrum IC(k), k in [-6, 6] (y4s, timestamp-aligned, members only), for S1 and S0 members over the H1 window rows, and the
  member-paired difference; peak location and k>0 points above k=0 (the A1 leak-audit L3 reading).
MODE h2 <out.json> <h2_manifest.json>
  h2_manifest = {"m0": [[cutoff_start_iso, oof], ...], ...}: monthly-cutoff models each scoring 12 months. Per member and day: the
  IC (T_net) of every model scoring that day, regressed on the model's age in days (>= 3 models that day); the day's slope is the
  mean over members; reported: mean slope per 30 days with MBB30 CI, by year, and the within-day demeaned IC by age month 0..11.
Terminal line (line start): 'KSR_READ <MODE> ...'.
"""
import calendar, hashlib, json, os, sys, time
import numpy as np

NS2 = '/dev/shm/news2_2026-09-23'; DL = '/workspace/dlarch_2026-09-24'
FEAT = f'{NS2}/work/NEWS_FEATURES.npz'; INSERV = f'{NS2}/work/king/KING_OOF.npz'
LAB = '/workspace/codex_research/QNT-2026-0907/combo_20260923/corrected_combo_v1d/data/dlw_targets.npz'
TNET, TREC = f'{DL}/king_fam_2026-09-27/T_NET.npz', f'{DL}/receipts/T_NET_2026-09-27.json'
PIN = {FEAT: '3c886a2bc0ff65c10b7e0a621c9468210bbd77ef58c90e625f0a29354d63c4d8',
       INSERV: 'a10b872506ca60afcd0f69b0e43d17a548cdd7c6956075000aac954b21e3df9a',
       LAB: 'ca479fccd3d3245e9438a8c82ba7b4a1950ab6e06607f28b25923c4526924d62',
       TNET: '929ff9f6c68280f1994ffb3c34c0c53114d96ad034686183f9dfd9b09b5c7a5c',
       f'{NS2}/devices/news2_diag1_score_ic.py': '291d800709650dddac72ba347cd151e71a8b0d22c730b535f3298e85bf6c79fc'}
DAY, H4, B, SEED, K = 86400, 14400, 2000, 20260927, 6
Z_GATE, YEARS_NEEDED = 2.39, 2
H1 = ('2023', '2024', '2025'); AGE_S1 = [0, 30, 60, 120]
T_ = lambda y, m, d=1: calendar.timegm((y, m, d, 0, 0, 0))
iso = lambda t: time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(int(t)))


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''):
            h.update(b)
    return h.hexdigest()


MODE, OUT = sys.argv[1], sys.argv[2]
for p, w in PIN.items():
    assert sha(p) == w, f'input moved: {p}'
sys.path.insert(0, f'{NS2}/devices')
from news2_diag1_score_ic import ic_series        # noqa: E402

F = np.load(FEAT); a = F['anchors'].astype(np.int64); off = F['off'].astype(np.int64); m_all = F['m'].astype(np.int64)
NA, NW = len(a), len(F['symbols'])


def on_axis(E_ts, arr):
    E = E_ts.astype(np.int64); ix = np.searchsorted(E, a); ok = (ix < len(E)) & (E[np.minimum(ix, len(E) - 1)] == a)
    assert np.array_equal(E[ix[ok]], a[ok])
    Y = np.full((NA, NW), np.nan)
    for i in np.flatnonzero(ok):
        mem = m_all[off[i]:off[i + 1]]; Y[i, mem] = arr[ix[i], mem]
    return Y


def load(p):
    z = np.load(p, allow_pickle=True); assert np.array_equal(z['E_ts'].astype(np.int64), a), p
    return z


def daily(P, Y, lo, hi):
    rows = np.flatnonzero((a >= lo) & (a < hi) & np.isfinite(P).any(1) & np.isfinite(Y).any(1)); dd = (a[rows] // DAY) * DAY; out = {}
    for u in np.unique(dd):
        ics, _, _ = ic_series(P, Y, rows[dd == u], rows[dd == u])
        if ics.size: out[int(u)] = float(ics.mean())
    return out


def mbb(x, block):
    rng = np.random.default_rng(SEED); n = len(x); nb = int(np.ceil(n / block)); m = np.empty(B)
    for b in range(B):
        st = rng.integers(0, max(1, n - block + 1), nb)
        m[b] = x[np.concatenate([np.arange(s, min(s + block, n)) for s in st])[:n]].mean()
    return float(m.std(ddof=1)), [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def clean(o):
    if isinstance(o, dict): return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [clean(v) for v in o]
    if isinstance(o, (float, np.floating)): return None if not np.isfinite(o) else float(o)
    if isinstance(o, np.integer): return int(o)
    if isinstance(o, np.bool_): return bool(o)
    return o


def write(rec, tag):
    rec = clean(rec); json.dump(rec, open(OUT + '.tmp', 'w'), indent=1, allow_nan=False); os.replace(OUT + '.tmp', OUT)
    assert json.load(open(OUT))['self_sha256'] == rec['self_sha256']
    print('KSR_READ %s %s out=%s sha256=%s' % (MODE, tag, OUT, sha(OUT)), flush=True)


rec = {'device': 'dlarch_ksr_read.py', 'self_sha256': sha(os.path.abspath(__file__)), 'mode': MODE, 'utc': iso(time.time()), 'inputs': PIN,
       'rule': 'DECISION_RULE_king_serving_refresh_2026-09-27.md (5b4fc6cda), transcribed'}
Tz = np.load(TNET, allow_pickle=True); YT = on_axis(Tz['E_ts'], Tz['T_net'])
last_T = int(a[np.flatnonzero(np.isfinite(YT).any(1))].max())
WIN = {y: (T_(int(y), 10), T_(int(y) + 1, 1)) for y in H1}; WIN['2026F'] = (T_(2026, 7), last_T + 1)
rec['windows'] = {k: [iso(v[0]), iso(v[1] - 1)] for k, v in WIN.items()}

if MODE == 'gate12':
    S0D, S1D, DUPD = sys.argv[3:6]; SERV = sys.argv[6] if len(sys.argv) > 6 else None
    ins = load(INSERV); r0 = load(f'{S0D}/KING_OOF.npz')
    g1 = {k: bool(ins[k].tobytes() == r0[k].tobytes()) for k in ('P', 'E_ts') } | {'symbols': bool(np.array_equal(ins['symbols'], r0['symbols']))}
    f26 = (a >= T_(2026, 1)); g1['P_fold2026_rows'] = bool(ins['P'][f26].tobytes() == r0['P'][f26].tobytes())
    g1['model_text_sha_equal_reported_not_gated'] = bool(np.array_equal(ins['model_sha256'], r0['model_sha256']))
    s1, dp = load(f'{S1D}/KING_OOF.npz'), load(f'{DUPD}/KING_OOF.npz')
    g2 = {'P': bool(s1['P'].tobytes() == dp['P'].tobytes()), 'model_text_sha_equal_reported_not_gated': bool(np.array_equal(s1['model_sha256'], dp['model_sha256']))}
    rec.update({'gate1_S0_reproduces_in_service': g1, 'GATE1_PASS': g1['P'] and g1['E_ts'] and g1['symbols'],
                'gate2_S1_determinism': g2, 'GATE2_PASS': g2['P'],
                'serving_receipt': {'path': SERV, 'sha256': sha(SERV)} if SERV else 'NOT GIVEN (fresh2, rule §8 item 5)',
                'S0_retrain_oof_sha256': sha(f'{S0D}/KING_OOF.npz'), 'S1_oof_sha256': sha(f'{S1D}/KING_OOF.npz'), 'dup_oof_sha256': sha(f'{DUPD}/KING_OOF.npz')})
    write(rec, 'GATE1_PASS=%s GATE2_PASS=%s' % (rec['GATE1_PASS'], rec['GATE2_PASS']))

elif MODE in ('ic', 'spectrum'):
    man = json.load(open(sys.argv[3])); rec['manifest'] = {'path': sys.argv[3], 'sha256': sha(sys.argv[3])}
    MEM = sorted(man['S0']); assert MEM == [f'm{i}' for i in range(8)], MEM
    S0 = {m: load(man['S0'][m]) for m in MEM}
    rec['S0_members'] = {m: {'path': man['S0'][m], 'sha256': sha(man['S0'][m])} for m in MEM}

if MODE == 'ic':
    Y4 = on_axis(np.load(LAB, allow_pickle=True)['E_ts'], np.load(LAB, allow_pickle=True)['y4s'])
    S0IC = {lbl: {m: {w: daily(S0[m]['P'].astype(np.float64), Y, *WIN[w]) for w in WIN} for m in MEM} for lbl, Y in (('T_net', YT), ('y4s', Y4))}
    res = {}
    for arm, byw in man['arms'].items():
        res[arm] = {}; keep = {}          # keep[(w, m)] = the member's daily dIC on T_net (the rule's quantity)
        for lbl, Y in (('T_net', YT), ('y4s', Y4)):
            per_w, pooled = {}, []
            for w, bym in byw.items():
                assert sorted(bym) == MEM, (arm, w)
                dI = {}
                for m in MEM:
                    P = load(bym[m])['P'].astype(np.float64)
                    rows = np.flatnonzero((a >= WIN[w][0]) & (a < WIN[w][1]))
                    assert np.isfinite(P[rows]).any(1).all(), f'{arm} {w} {m}: window not fully scored'
                    ic = daily(P, Y, *WIN[w]); base = S0IC[lbl][m][w]
                    dI[m] = {u: ic[u] - base[u] for u in ic if u in base}
                    if lbl == 'T_net': keep[(w, m)] = dI[m]
                days = sorted(set().union(*[set(v) for v in dI.values()]))
                ser = np.array([np.mean([dI[m][u] for m in MEM if u in dI[m]]) for u in days])
                mm = {m: float(np.mean(list(dI[m].values()))) for m in MEM}
                row = {'n_days': len(days), 'mean': float(ser.mean()), 'members_positive': int(sum(v > 0 for v in mm.values())), 'member_means': mm}
                if len(days) >= 30: row['MBB30_SE'], row['MBB30_ci95'] = mbb(ser, 30)
                rp = os.path.join(os.path.dirname(bym['m0']), 'TRAIN_RECEIPT.json')
                if os.path.exists(rp):     # S1-arm model age buckets (days since its training label end)
                    le = json.load(open(rp))['folds'][0]['max_train_label_end']; ag = np.array([(u - le) / DAY for u in days]); bk = {}
                    for b0, b1 in zip(AGE_S1[:-1], AGE_S1[1:]):
                        sel = (ag >= b0) & (ag < b1)
                        if sel.any(): bk[f'[{b0},{b1})'] = {'n_days': int(sel.sum()), 'mean': float(ser[sel].mean())}
                    row['by_arm_model_age_days'] = bk; row['arm_label_end'] = iso(le)
                row['S0_label_end_note'] = 'S0 = A0 fold of the window year; its age over the window is reported by the audit L5 convention'
                per_w[w] = row
                if w in H1: pooled.append(ser)
            h1 = {}
            if len(pooled) == len(H1):
                x = np.concatenate(pooled); se_b, ci = mbb(x, 30)
                h1 = {'n_days': int(len(x)), 'mean': float(x.mean()), 'MBB30_SE': se_b, 'MBB30_ci95': ci,
                      'note': 'moving blocks run over the concatenated window days and may straddle the gaps between windows (named)'}
            res[arm][lbl] = {'per_window': per_w, 'H1_pooled': h1}
        if all(w in byw for w in H1):   # rule §1/§2, T_net: SE = max(MBB30 SE, sd_m / sqrt(8)); member means over the pooled H1 days
            pmeans = [float(np.mean([v for w in H1 for v in keep[(w, m)].values()])) for m in MEM]
            h1 = res[arm]['T_net']['H1_pooled']; sdm = float(np.std(pmeans, ddof=1)) / np.sqrt(8)
            se = max(h1['MBB30_SE'], sdm); zz = h1['mean'] / se
            ypos = int(sum(res[arm]['T_net']['per_window'][w]['mean'] > 0 for w in H1))
            p26 = res[arm]['T_net']['per_window'].get('2026F', {}).get('mean')
            res[arm]['RULE'] = {'member_means_H1': pmeans, 'sd_m_over_sqrt8': sdm, 'SE': se, 'z': zz, 'z_gate': Z_GATE, 'years_positive': ypos,
                                'years_needed': YEARS_NEEDED, 'IC_GATE_PASS': bool(zz >= Z_GATE and ypos >= YEARS_NEEDED),
                                'point_2026F': p26, 'point_2026F_ge_0': (p26 >= 0) if p26 is not None else None}
    rec['arms'] = res
    write(rec, ' '.join('%s:IC_GATE_PASS=%s' % (k, v.get('RULE', {}).get('IC_GATE_PASS')) for k, v in res.items()))

elif MODE == 'spectrum':
    Y4 = on_axis(np.load(LAB, allow_pickle=True)['E_ts'], np.load(LAB, allow_pickle=True)['y4s'])
    rows = np.concatenate([np.flatnonzero((a >= WIN[w][0]) & (a < WIN[w][1])) for w in H1]); rows = rows[(rows - K >= 0) & (rows + K < NA)]

    def spec(P):
        out = {}
        for k in range(-K, K + 1):
            ics, _, _ = ic_series(P, Y4, rows, rows + k); out[k] = float(ics.mean())
        return out
    S1m = {m: None for m in MEM}
    # the S1 member score on the H1 rows = the three window OOFs combined
    for m in MEM:
        P = np.full((NA, NW), np.nan)
        for w in H1:
            z = load(man['arms']['S1'][w][m]); r = np.flatnonzero((a >= WIN[w][0]) & (a < WIN[w][1])); P[r] = z['P'][r]
        S1m[m] = P
    sp1 = {m: spec(S1m[m]) for m in MEM}; sp0 = {m: spec(S0[m]['P'].astype(np.float64)) for m in MEM}
    ks = list(range(-K, K + 1)); D = np.array([[sp1[m][k] - sp0[m][k] for k in ks] for m in MEM])
    mD = {k: float(D[:, i].mean()) for i, k in enumerate(ks)}
    pk = lambda d: max(d, key=d.get)
    rec.update({'n_anchors': int(len(rows)), 'S1_mean': {k: float(np.mean([sp1[m][k] for m in MEM])) for k in ks},
                'S0_mean': {k: float(np.mean([sp0[m][k] for m in MEM])) for k in ks}, 'D_mean': mD,
                'D_sd': {k: float(D[:, i].std(ddof=1)) for i, k in enumerate(ks)}, 'D_peak_k': pk(mD),
                'kpos_with_D_above_D0': [k for k in ks if k > 0 and mD[k] > mD[0]]})
    rec['S1_peak_k'] = pk(rec['S1_mean']); rec['S0_peak_k'] = pk(rec['S0_mean'])
    write(rec, 'D_peak_k=%s' % rec['D_peak_k'])

elif MODE == 'h2':
    man = json.load(open(sys.argv[3])); rec['manifest'] = {'path': sys.argv[3], 'sha256': sha(sys.argv[3])}
    slopes_by_day = {}; demeaned = {}
    for m, lst in man.items():
        per_day = {}
        for start_iso, p in lst:
            z = load(p); r = json.load(open(os.path.join(os.path.dirname(p), 'TRAIN_RECEIPT.json'))); le = r['folds'][0]['max_train_label_end']
            P = z['P'].astype(np.float64); sc = np.flatnonzero(np.isfinite(P).any(1))
            for u, v in daily(P, YT, int(a[sc[0]]), int(a[sc[-1]]) + 1).items():
                per_day.setdefault(u, []).append(((u - le) / DAY, v))
        for u, lst2 in per_day.items():
            if len(lst2) >= 3:
                ag = np.array([x[0] for x in lst2]); ic = np.array([x[1] for x in lst2])
                slopes_by_day.setdefault(u, []).append(float(np.polyfit(ag, ic, 1)[0]) * 30)
                for g, v in zip(ag, ic - ic.mean()): demeaned.setdefault(int(g // 30), []).append(float(v))
    days = sorted(slopes_by_day); x = np.array([np.mean(slopes_by_day[u]) for u in days])
    se, ci = mbb(x, 30)
    yr = lambda u: time.gmtime(u).tm_year
    rec.update({'slope_IC_per_30d': {'n_days': len(days), 'mean': float(x.mean()), 'MBB30_SE': se, 'MBB30_ci95': ci},
                'by_year': {str(y): {'n_days': int(sum(yr(u) == y for u in days)), 'mean': float(np.mean([v for u, v in zip(days, x) if yr(u) == y]))}
                            for y in sorted({yr(u) for u in days})},
                'within_day_demeaned_IC_by_age_month': {k: {'n': len(v), 'mean': float(np.mean(v))} for k, v in sorted(demeaned.items())}})
    write(rec, 'slope_per_30d=%.6f' % x.mean())
elif MODE != 'gate12':   # rev 1: gate12 is handled by the first if-chain; this chain must not reject it (first gates run exited 1 here AFTER writing a valid receipt)
    raise SystemExit('mode gate12|ic|spectrum|h2')
