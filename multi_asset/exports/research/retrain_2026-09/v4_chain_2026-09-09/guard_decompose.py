"""Baseline-guard decomposition (PREREG_v4 §2.3 guard band 2.27–2.57 read 1.96 on v4). The book below is a VERBATIM copy of
pod_export_bundle_v4.py L84–L160 (v1iv 3-leg msharpe book, no universe mask, EMA 0.1, cost tiers, IV carry), wrapped as a function of
(PRED, meta, panel). Runs: v3 (must reproduce the published 2.28 first), v4, and the two crosses (v4 PRED on v3 meta / v3 PRED on v4 meta),
then Sharpe with/without the 2026-08 hole neighbourhood and per-period means."""
import numpy as np, time, json, calendar, sys
from scipy.stats import rankdata
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan); n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out
COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]
def tier_of(q):
    t = np.full(len(q), 2, np.int8); t[q >= 1e6] = 1; t[q >= 5e6] = 0
    return t
PW = np.load("/workspace/data/wide_panel_4h_v2ext.npz", allow_pickle=True); pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]; R24 = PW["f_rev_24h"]; FE = PW["f_fund_ema_v1"]; NW = 829
def book(PRED, MT):
    E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]; y4 = MT["y4"]; qvk = MT["qvk"]; nA = len(E_ts)
    LR = {leg: [] for leg in ("king", "rev24", "fund")}; idx = []
    for i in range(nA):
        j = pw_row.get(int(E_ts[i]))
        if j is None: continue
        sc = {"king": PRED[i, members[i]], "rev24": -R24[j, members[i]], "fund": FE[j, members[i]]}; m = members[i]; ok = np.isfinite(y4[i, m])
        for leg in LR:
            z = np.nan_to_num(xz(sc[leg])); z = np.where(ok, z, 0.0); z -= z[ok].mean() if ok.sum() else 0; g = np.abs(z).sum()
            LR[leg].append(float((z / g * np.nan_to_num(y4[i, m], nan=0.0)).sum() * 1e4) if g > 1e-9 else 0.0)
        idx.append(i)
    LRa = {k: np.array(v) for k, v in LR.items()}; pos = {int(i): p for p, i in enumerate(idx)}
    def msharpe_w(i_pos):
        look = 900
        if i_pos < look: return (1/3, 1/3, 1/3)
        sl = slice(i_pos - look, i_pos); r = np.stack([LRa["king"][sl], LRa["rev24"][sl], LRa["fund"][sl]])
        shp = r.mean(1) / (r.std(1) + 1e-9); shp = np.maximum(shp, 0.0)
        return tuple(shp / shp.sum() if shp.sum() > 0 else np.array([1/3]*3))
    H = np.zeros(NW, np.float64); rec = []; W3 = []
    for i in range(nA):
        j = pw_row.get(int(E_ts[i]))
        if j is None: continue
        m = members[i]; sc = {"king": PRED[i, m], "rev24": -R24[j, m], "fund": FE[j, m]}; wk, wr, wf = msharpe_w(pos.get(int(i), 0))
        z = wk * np.nan_to_num(xz(sc["king"])) + wr * np.nan_to_num(xz(sc["rev24"])) + wf * np.nan_to_num(xz(sc["fund"]))
        ok = np.isfinite(y4[i, m]); qv4h = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48; sel = ok & (qv4h >= 2.5e5)
        if sel.sum() < 80: continue
        w = np.where(sel, z, 0.0); w -= w[sel].mean(); g = np.abs(w).sum()
        if g < 1e-9: continue
        w /= g; capw = 2.5 / max(sel.sum(), 1); w = np.clip(w, -capw, capw); g2_ = np.abs(w).sum()
        if g2_ > 1e-9: w /= g2_
        tgt = np.zeros(NW); tgt[m] = w; sm = H + 0.1 * (tgt - H); trade = sm - H; sm = np.where(np.abs(trade) < 2.5e-4, H, sm); trade = sm - H
        qvf = np.expm1(np.clip(qvk[i, m], 0, 30)) * 48; trm = tier_of(qvf); tabs = np.abs(trade[m])
        cb = sum(tabs[trm == tt].sum() * (fr * mk + (1 - fr) * tk) for tt, (mk, tk, fr) in enumerate(COST_B))
        yv = np.nan_to_num(y4[i, m], nan=0.0); fnow = np.nan_to_num(FN[j, m], nan=0.0); ivv = IV[j, m]; ivv = np.where(np.isfinite(ivv) & (ivv > 0), ivv, 8.0)
        car = (sm[m] * fnow * (4.0 / ivv)).sum() * 1e4; pnl = float((sm[m] * yv).sum() * 1e4); net = float(pnl - car - cb)
        rec.append((int(E_ts[i]), net, pnl, car, cb, int(sel.sum()), int(len(m)))); W3.append((wk, wr, wf)); H = sm
    return np.array(rec), np.array(W3), LRa, np.array(idx)
def T(*a): return calendar.timegm(a + (0,) * (6 - len(a)))
def sharpe(v): return float(v.mean() / (v.std() + 1e-12) * np.sqrt(6 * 365))
def align_pred(P, src_E, dst_E):
    out = np.full((len(dst_E), P.shape[1]), np.nan, np.float32); r = {int(t): i for i, t in enumerate(src_E)}
    for k, t in enumerate(dst_E):
        i = r.get(int(t))
        if i is not None: out[k] = P[i]
    return out
M3 = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True); M4 = np.load("/workspace/data/wide_fea_v4_meta.npz", allow_pickle=True)
P3 = np.load("/workspace/shadow_bundle_v3/slow_pred_pinned.npy"); P4 = np.load("/workspace/shadow_bundle_v4/slow_pred_pinned.npy")
E3 = M3["E_ts"].astype(np.int64); E4 = M4["E_ts"].astype(np.int64)
runs = {"v3 (P3,M3)": (P3, M3), "v4 (P4,M4)": (P4, M4), "cross P4 on M3": (align_pred(P4, E4, E3), M3), "cross P3 on M4": (align_pred(P3, E3, E4), M4)}
PER = {"2024-01→2026-08-10 20Z": (T(2024, 1, 1), T(2026, 8, 10, 20) + 1), "2026-08-11→08-11 20Z": (T(2026, 8, 11), T(2026, 8, 11, 20) + 1), "hole 08-12→08-24 04Z": (T(2026, 8, 12), T(2026, 8, 24, 4) + 1),
       "post 08-24 08Z→08-30 20Z": (T(2026, 8, 24, 8), T(2026, 8, 30, 20) + 1), "08-31 (6)": (T(2026, 8, 31), T(2026, 9, 1)), "2024": (T(2024, 1, 1), T(2025, 1, 1)), "2025": (T(2025, 1, 1), T(2026, 1, 1)), "2026→08-10": (T(2026, 1, 1), T(2026, 8, 10, 20) + 1)}
out = {}; series = {}
for name, (P, MT) in runs.items():
    t0 = time.time(); rec, W3, LRa, idx = book(P, MT); ts = rec[:, 0].astype(np.int64); net = rec[:, 1]; m24 = ts >= T(2024, 1, 1)
    res = {"n_ge2024": int(m24.sum()), "sharpe_guard_ge2024": sharpe(net[m24]), "net_mean_ge2024": float(net[m24].mean()), "std_ge2024": float(net[m24].std())}
    ex = m24 & ~((ts >= T(2026, 8, 11)) & (ts < T(2026, 9, 1))); res["sharpe_ge2024_excl_0811_0831"] = sharpe(net[ex]); res["n_excl"] = int(ex.sum())
    ex2 = m24 & (ts <= T(2026, 8, 10, 20)); res["sharpe_2024_to_0810"] = sharpe(net[ex2])
    for w, (lo, hi) in PER.items():
        mm = (ts >= lo) & (ts < hi)
        if mm.any(): res[w] = {"n": int(mm.sum()), "net_mean": float(net[mm].mean()), "net_sum": float(net[mm].sum()), "pnl_mean": float(rec[mm, 2].mean()), "carry_mean": float(rec[mm, 3].mean()), "cost_mean": float(rec[mm, 4].mean()), "nsel_mean": float(rec[mm, 5].mean()), "nmem_mean": float(rec[mm, 6].mean()), "w3_king_mean": float(W3[mm, 0].mean())}
    out[name] = res; series[name] = rec
    print(f"== {name} ({time.time()-t0:.0f}s): guard Sharpe(>=2024) {res['sharpe_guard_ge2024']:.3f} net {res['net_mean_ge2024']:+.3f} std {res['std_ge2024']:.2f} n {res['n_ge2024']} | excl 08-11..08-31: {res['sharpe_ge2024_excl_0811_0831']:.3f} | 2024→08-10: {res['sharpe_2024_to_0810']:.3f}", flush=True)
    for w in PER:
        if w in res: r = res[w]; print(f"   {w:28s} n {r['n']:5d} net {r['net_mean']:+8.3f} (sum {r['net_sum']:+9.1f}) pnl {r['pnl_mean']:+8.3f} carry {r['carry_mean']:+7.3f} cost {r['cost_mean']:6.3f} nsel {r['nsel_mean']:6.1f} nmem {r['nmem_mean']:6.1f} w3k {r['w3_king_mean']:.3f}", flush=True)
# paired per-anchor difference v4 - v3 on common anchors (>=2024), by period
r3 = series["v3 (P3,M3)"]; r4 = series["v4 (P4,M4)"]; c = np.intersect1d(r3[:, 0].astype(np.int64), r4[:, 0].astype(np.int64)); i3 = np.searchsorted(r3[:, 0].astype(np.int64), c); i4 = np.searchsorted(r4[:, 0].astype(np.int64), c)
d = r4[i4, 1] - r3[i3, 1]; out["paired_v4_minus_v3"] = {}
for w, (lo, hi) in PER.items():
    mm = (c >= lo) & (c < hi)
    if mm.any(): out["paired_v4_minus_v3"][w] = {"n": int(mm.sum()), "mean": float(d[mm].mean()), "sum": float(d[mm].sum()), "max_abs_anchor": float(np.abs(d[mm]).max())}; print(f"paired v4-v3 {w:28s} n {mm.sum():5d} mean {d[mm].mean():+8.3f} sum {d[mm].sum():+9.1f} max|Δ| {np.abs(d[mm]).max():8.1f}")
np.savez("/workspace/review_scratch/v4_gates/guard_series.npz", **{k.replace(" ", "_").replace("(", "").replace(")", "").replace(",", "_"): v for k, v in series.items()})
json.dump(out, open("/workspace/review_scratch/v4_gates/guard_decompose.json", "w"), indent=1); print("GUARD_DECOMPOSE_DONE", flush=True)
