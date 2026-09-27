#!/usr/bin/env python3
"""dlarch_ksr_splice.py -- King serving refresh (DECISION_RULE_king_serving_refresh_2026-09-27.md 5b4fc6cda), gate 4 of §0:
the book-layer King input is SPLICED the way production would see a refresh, never replaced wholesale.

WHY: the live seat is msharpe over the last 900 anchors (150 days) of leg returns. After a refresh, those 150 days are the OLD
model's leg returns followed by the NEW model's. A cell built from the refreshed model's scores over the WHOLE axis would give a
seat path production never has. Leg returns at anchor t are built from the King scores AT t, so splicing the SCORES (S0 outside
the refresh windows, the arm inside) makes every leg array follow production automatically -- which this device then asserts.

MODE build <S0_KING_OOF.npz> <out_dir> <arm_OOF.npz>...    (each arm OOF = one refresh window: its scored rows)
  out = S0 with, for each arm OOF, the rows it scored replaced by its rows (P and model_sha256). Asserted: windows disjoint; outside
  the windows every array is BITWISE S0; inside, BITWISE the arm. Writes KING_OOF.npz + SPLICE_RECEIPT.json (read back).
MODE legs <S0_legs.npz> <spliced_legs.npz> <SPLICE_RECEIPT.json> <out.json>
  every array of the spliced legs must be BITWISE equal to S0's legs at every anchor BEFORE the first window's first anchor; the
  first differing anchor of each array is reported (must be >= the first window anchor). Arrays that never differ are listed (a
  King-only splice that changes NO leg array would mean the splice did not reach the book -- that is a FAIL, not a pass).
MODE red <S0_KING_OOF.npz> <out_dir> <start YYYY-MM-DD> <end YYYY-MM-DD> <seed>
  the red-control arm for one window: S0's scores inside [start, end) permuted WITHIN each anchor over the finite cells (asset
  identity destroyed, the anchor's score multiset kept), NaN outside; model_sha256 = 'RED' inside. Used as an arm OOF by the IC
  reader and by 'build' (whatever layer the lead rules gate 3 on).
Terminal line: 'KSR_SPLICE PASS=<bool> ...' (line start).
"""
import hashlib, json, os, sys, time
import numpy as np


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 24), b''):
            h.update(b)
    return h.hexdigest()


def same(x, y):
    return x.dtype == y.dtype and x.shape == y.shape and x.tobytes() == y.tobytes()


MODE = sys.argv[1]
if MODE == 'build':
    S0P, OUTD, ARMS = sys.argv[2], sys.argv[3], sys.argv[4:]
    S = np.load(S0P, allow_pickle=True); keys = sorted(S.files); base = {k: S[k] for k in keys}
    assert set(keys) == {'P', 'E_ts', 'symbols', 'model_sha256'}, keys
    out = {k: v.copy() for k, v in base.items()}; used = np.zeros(len(base['E_ts']), bool); wins = []
    for p in ARMS:
        z = np.load(p, allow_pickle=True)
        assert same(z['E_ts'], base['E_ts']) and same(z['symbols'], base['symbols']) and z['P'].dtype == base['P'].dtype
        rows = np.flatnonzero(np.isfinite(z['P']).any(1)); assert len(rows) and np.all(np.diff(rows) == 1), f'{p}: window not contiguous'
        assert not used[rows].any(), f'{p}: windows overlap'
        used[rows] = True; out['P'][rows] = z['P'][rows]; out['model_sha256'][rows] = z['model_sha256'][rows]
        wins.append({'arm_oof': p, 'arm_oof_sha256': sha(p), 'first_anchor': int(base['E_ts'][rows[0]]), 'last_anchor': int(base['E_ts'][rows[-1]]),
                     'n_anchors': int(len(rows)), 'first_row': int(rows[0])})
        assert same(out['P'][rows], z['P'][rows]) and np.array_equal(out['model_sha256'][rows], z['model_sha256'][rows])
    ok_out = all(same(out[k][~used], base[k][~used]) for k in ('P', 'model_sha256')) and same(out['E_ts'], base['E_ts']) and same(out['symbols'], base['symbols'])
    assert ok_out, 'outside the windows the splice is not bitwise S0'
    os.makedirs(OUTD, exist_ok=False); fo = os.path.join(OUTD, 'KING_OOF.npz'); np.savez_compressed(fo, **out)
    back = np.load(fo, allow_pickle=True)
    assert all(same(back[k], out[k]) if back[k].dtype != object else np.array_equal(back[k], out[k]) for k in keys), 'read-back differs'
    rec = {'device': 'dlarch_ksr_splice.py', 'self_sha256': sha(os.path.abspath(__file__)), 'mode': 'build', 'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
           'S0': S0P, 'S0_sha256': sha(S0P), 'windows': sorted(wins, key=lambda w: w['first_anchor']), 'out': fo, 'out_sha256': sha(fo),
           'outside_windows_bitwise_S0': True, 'inside_windows_bitwise_arm': True, 'rows_replaced': int(used.sum())}
    rp = os.path.join(OUTD, 'SPLICE_RECEIPT.json'); json.dump(rec, open(rp + '.tmp', 'w'), indent=1); os.replace(rp + '.tmp', rp)
    assert json.load(open(rp))['out_sha256'] == rec['out_sha256']
    print('KSR_SPLICE PASS=True mode=build rows=%d windows=%d out_sha256=%s' % (used.sum(), len(wins), rec['out_sha256']), flush=True)
elif MODE == 'legs':
    L0p, L1p, RP, OUT = sys.argv[2:6]
    L0, L1 = np.load(L0p, allow_pickle=True), np.load(L1p, allow_pickle=True); rec_s = json.load(open(RP))
    assert sorted(L0.files) == sorted(L1.files)
    E = L0['E_ts'].astype(np.int64); assert same(L0['E_ts'], L1['E_ts'])
    w0 = min(w['first_anchor'] for w in rec_s['windows']); i0 = int(np.searchsorted(E, w0)); assert E[i0] == w0
    rows = {}
    for k in sorted(L0.files):
        x, y = L0[k], L1[k]
        if x.ndim == 0 or x.shape[0] != len(E):
            rows[k] = {'axis0_is_anchor': False, 'bitwise_equal': same(x, y) if x.dtype != object else bool(np.array_equal(x, y))}; continue
        eq = np.array([(x[i].tobytes() == y[i].tobytes()) for i in range(len(E))]) if x.dtype != object else np.array([np.array_equal(x[i], y[i]) for i in range(len(E))])
        first = int(np.argmin(eq)) if not eq.all() else None
        rows[k] = {'axis0_is_anchor': True, 'first_differing_anchor': int(E[first]) if first is not None else None,
                   'pre_window_bitwise_equal': bool(eq[:i0].all()), 'n_anchors_differing': int((~eq).sum())}
    pre_ok = all(v.get('pre_window_bitwise_equal', True) for v in rows.values())
    nonanchor_ok = all(v['bitwise_equal'] for v in rows.values() if not v['axis0_is_anchor'])
    reached = any(v.get('n_anchors_differing', 0) > 0 for v in rows.values())
    PASS = bool(pre_ok and nonanchor_ok and reached)
    rec = {'device': 'dlarch_ksr_splice.py', 'self_sha256': sha(os.path.abspath(__file__)), 'mode': 'legs', 'utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
           'S0_legs': L0p, 'S0_legs_sha256': sha(L0p), 'spliced_legs': L1p, 'spliced_legs_sha256': sha(L1p), 'splice_receipt_sha256': sha(RP),
           'first_window_anchor': w0, 'arrays': rows, 'pre_window_all_bitwise': pre_ok, 'non_anchor_arrays_bitwise': nonanchor_ok,
           'splice_reached_the_legs': reached, 'PASS': PASS}
    json.dump(rec, open(OUT + '.tmp', 'w'), indent=1); os.replace(OUT + '.tmp', OUT); assert json.load(open(OUT))['PASS'] == PASS
    print('KSR_SPLICE PASS=%s mode=legs first_window=%d reached=%s' % (PASS, w0, reached), flush=True)
    sys.exit(0 if PASS else 2)
elif MODE == 'red':
    import calendar
    S0P, OUTD, st, en, seed = sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], int(sys.argv[6])
    d = lambda x: calendar.timegm(time.strptime(x, '%Y-%m-%d'))
    S = np.load(S0P, allow_pickle=True); E = S['E_ts'].astype(np.int64); P = np.full(S['P'].shape, np.nan, S['P'].dtype)
    ms = np.array([''] * len(E), dtype=S['model_sha256'].dtype); rows = np.flatnonzero((E >= d(st)) & (E < d(en))); rng = np.random.default_rng(seed)
    for i in rows:
        g = np.flatnonzero(np.isfinite(S['P'][i])); P[i, g] = S['P'][i, g[rng.permutation(len(g))]]; ms[i] = 'RED'
    assert all(np.array_equal(np.sort(P[i][np.isfinite(P[i])]), np.sort(S['P'][i][np.isfinite(S['P'][i])])) for i in rows), 'multiset not kept'
    os.makedirs(OUTD, exist_ok=False); fo = os.path.join(OUTD, 'KING_OOF.npz'); np.savez_compressed(fo, P=P, E_ts=S['E_ts'], symbols=S['symbols'], model_sha256=ms)
    rec = {'device': 'dlarch_ksr_splice.py', 'self_sha256': sha(os.path.abspath(__file__)), 'mode': 'red', 'S0': S0P, 'S0_sha256': sha(S0P),
           'start': st, 'end': en, 'seed': seed, 'rows': int(len(rows)), 'out_sha256': sha(fo)}
    json.dump(rec, open(os.path.join(OUTD, 'RED_RECEIPT.json'), 'w'), indent=1)
    print('KSR_SPLICE PASS=True mode=red rows=%d out_sha256=%s' % (len(rows), rec['out_sha256']), flush=True)
else:
    raise SystemExit('mode build|legs|red')
