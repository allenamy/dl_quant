"""hedge_decomp.py — docs/ANALYSIS_m3_hedge_value_decomposition_2026-09-23.md §1-§3 (frozen before numbers).
Decompose the M3b hedge leg's target-level gross return g_t = h_t * r_t into a drift term N*mean(h)*mean(r) and a timing term
sum((h-hbar)(r-rbar)) per segment. h_t = -beta_exec_c of the executed book at published anchors, forward-filled over HOLD anchors on
the 4h grid inside the windows; r_t = BTCUSDT simple return over (t, t+4h] on the certified raw price table (m2_lib.bars_4h); invalid
bars excluded and counted. usage: python -B hedge_decomp.py <m2_lib_dir> <exec_path_OLD.npz> <exec_path_NEW.npz> <out.json>"""
import sys, os, json, time, hashlib, calendar
import numpy as np
sys.path.insert(0, sys.argv[1]); import m2_lib as M
H4 = 14400; DAY = 86400
BT = "/workspace/baseline_tables_2026-09-19"
PRICE = (BT + "/work/price_full_raw_x0918r.npy", "23af32bd97c267d126c2109641815b92082b8688e35bcfbaaa1e88c2dc5bb5d8")
META = (BT + "/work/price_full_raw_x0918r_meta.npz", "d1e49cc9f0a7ddc4104feb52a42da3024ba1e66ad5891a26c96f00cff7ce5d90")
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()
def ts(s): return calendar.timegm(time.strptime(s, "%Y-%m-%d"))
SEG = {"2023H2": ("2023-06-30", "2024-01-01"), "2024": ("2024-01-01", "2025-01-01"), "2025": ("2025-01-01", "2026-01-01"),
       "2026_JanAug": ("2026-01-01", "2026-08-31"), "EXT_0831_0918": ("2026-08-31", "2026-09-19")}
JUDGE = ("2023H2", "2024", "2025", "2026_JanAug")
rec = {"device": "hedge_decomp.py", "self_sha256": sha(os.path.abspath(__file__)), "m2_lib_sha256": sha(os.path.join(sys.argv[1], "m2_lib.py")),
       "spec": "docs/ANALYSIS_m3_hedge_value_decomposition_2026-09-23.md §1-§3", "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
for p, s in (PRICE, META): assert sha(p) == s, ("pin", p)
PM = np.load(META[0], allow_pickle=True); syms = [str(x) for x in PM["symbols"]]; bj = syms.index("BTCUSDT")
LP = np.load(PRICE[0], mmap_mode="r"); grid = PM["grid"].astype(np.int64)
T, R, V = M.bars_4h(LP, grid, PM["first_fin"], PM["last_fin"], PM["unavail_grid_row"], PM["unavail_col"])
rB = R[:, bj]; vB = V[:, bj]
kof = {int(t): k for k, t in enumerate(T)}
def fwd_ret(t):                                   # BTC simple return over (t, t+4h] = bar ending at t+4h
    k = kof.get(int(t) + H4)
    return float(np.expm1(rB[k])) if (k is not None and vB[k]) else np.nan
out = {}
for base, path in (("OLD", sys.argv[2]), ("NEW_s42", sys.argv[3])):
    z = np.load(path); A = z["anchor"].astype(np.int64); h_pub = -z["beta_exec_c"].astype(np.float64); w = z["window"]
    assert np.all(np.diff(A) > 0) and np.all(A % H4 == 0) and np.all(np.isfinite(h_pub))
    rec.setdefault("inputs", {})[base] = {"path": path, "sha256": sha(path), "published": int(len(A))}
    # 4h grid inside each window, forward fill from the last published anchor of the SAME window (HOLD keeps the leg)
    rows = []
    for wc in np.unique(w):
        Aw = A[w == wc]; hw = h_pub[w == wc]
        g = np.arange(Aw[0], Aw[-1] + H4, H4, dtype=np.int64)
        idx = np.searchsorted(Aw, g, side="right") - 1
        for t, i in zip(g.tolist(), idx.tolist()): rows.append((t, hw[i], int(wc), t == int(Aw[i])))
    rows.sort(); tt = np.array([r[0] for r in rows]); hh = np.array([r[1] for r in rows]); pub = np.array([r[3] for r in rows])
    rr = np.array([fwd_ret(t) for t in tt]); ok = np.isfinite(rr)
    res = {"grid_anchors": int(len(tt)), "published": int(pub.sum()), "held_ffill": int((~pub).sum()), "invalid_btc_bars_excluded": int((~ok).sum())}
    seg = {}
    for s, (a, b) in SEG.items():
        m = ok & (tt >= ts(a)) & (tt < ts(b)); n = int(m.sum())
        if n == 0: seg[s] = {"n": 0}; continue
        h = hh[m]; r = rr[m]; g = h * r
        drift = n * h.mean() * r.mean(); timing = float(((h - h.mean()) * (r - r.mean())).sum())
        assert abs(g.sum() - drift - timing) < 1e-12, "identity"
        seg[s] = {"n": n, "sum_g_nav_pct": 200 * g.sum(), "drift_nav_pct": 200 * drift, "timing_nav_pct": 200 * timing,
                  "mean_h_gross": float(h.mean()), "btc_sum_simple_ret_pct": 100 * float(r.sum()), "btc_compound_ret_pct": 100 * float(np.prod(1 + r) - 1),
                  "corr_h_r": float(np.corrcoef(h, r)[0, 1])}
    res["segments"] = seg
    # whole judge window timing term + 30-day block bootstrap on daily sums of the centred products (report only)
    m = ok & (tt >= ts("2023-06-30")) & (tt < ts("2026-08-31")); h = hh[m]; r = rr[m]; t_ = tt[m]
    prod = (h - h.mean()) * (r - r.mean()); days = t_ // DAY; ud, inv = np.unique(days, return_inverse=True)
    dsum = np.bincount(inv, weights=prod); nd = len(dsum); blk = 30; rng = np.random.default_rng([20260923, 1])
    nb = -(-nd // blk); draws = np.empty(10000)
    for b in range(10000):
        st = rng.integers(0, nd - blk + 1, nb); ix = (st[:, None] + np.arange(blk)[None, :]).ravel()[:nd]; draws[b] = dsum[ix].sum()
    res["judge_window"] = {"n": int(m.sum()), "timing_nav_pct": 200 * float(prod.sum()), "timing_ci95_nav_pct": [200 * float(np.percentile(draws, 2.5)), 200 * float(np.percentile(draws, 97.5))],
                           "drift_nav_pct": 200 * float(len(h) * h.mean() * r.mean()), "sum_g_nav_pct": 200 * float((h * r).sum())}
    # state dependence: h vs BTC trailing 7d / 30d log return (bars ending at or before t)
    cum = np.nancumsum(np.where(vB, rB, 0.0))
    def trail(t, nb_):
        k = kof.get(int(t)); return float(cum[k] - cum[k - nb_]) if (k is not None and k - nb_ >= 0) else np.nan
    tr7 = np.array([trail(t, 42) for t in tt]); tr30 = np.array([trail(t, 180) for t in tt])
    q = np.isfinite(tr7) & np.isfinite(tr30)
    res["state"] = {"corr_h_trailing7d": float(np.corrcoef(hh[q], tr7[q])[0, 1]), "corr_h_trailing30d": float(np.corrcoef(hh[q], tr30[q])[0, 1]),
                    "last_anchor": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime(int(tt[-1]))), "last_h_gross": float(hh[-1]), "mean_h_last_30d": float(hh[tt >= tt[-1] - 30 * DAY].mean())}
    # frozen reading rule inputs
    tpos = sum(1 for s in JUDGE if seg[s]["timing_nav_pct"] >= 0)
    ddom = sum(1 for s in JUDGE if abs(seg[s]["drift_nav_pct"]) > abs(seg[s]["timing_nav_pct"]) and np.sign(seg[s]["drift_nav_pct"]) == np.sign(seg[s]["sum_g_nav_pct"]))
    res["rule_inputs"] = {"timing_nonneg_segments": tpos, "judge_timing_positive": res["judge_window"]["timing_nav_pct"] > 0, "drift_dominant_segments": ddom}
    out[base] = res
S = all(out[b]["rule_inputs"]["judge_timing_positive"] and out[b]["rule_inputs"]["timing_nonneg_segments"] >= 3 for b in out)
D = all(out[b]["rule_inputs"]["drift_dominant_segments"] >= 3 for b in out)
rec["results"] = out; rec["READING"] = "S_structural" if S else ("D_directional" if D else "M_mixed")
rec["READING_both_flags"] = {"S": S, "D": D}
json.dump(rec, open(sys.argv[4], "w"), indent=1, default=float)
print("HEDGE_DECOMP READING=" + rec["READING"], json.dumps(rec["READING_both_flags"]), "sha", sha(sys.argv[4])[:16], flush=True)
