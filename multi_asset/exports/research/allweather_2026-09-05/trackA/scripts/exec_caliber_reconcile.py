"""exec_caliber_reconcile.py — three price-P&L calibers of the SAME replay book (weights W from a w10 artifact, d30_n2_c42 arm), team-lead correction
2026-09-05: the invested book holds the previous anchor's weights w_{t-1} during [E, E+25min] and moves only the delta at N+23, so the executable
caliber is NOT "zero exposure for 25 min". For each anchor t (cache rows relative to E; row E+k = bar closing at E+5k min):
  (a) E-close (prod caliber, the device's own):  pnl_a = Σ_i w_{i,t} · (Π(1+r_i[E+1..E+48]) − 1)
  (b) zero-exposure variant (what dev_exec did):  pnl_b = Σ_i w_{i,t} · (Π(1+r_i[E+6..E+48]) − 1)
  (c) reconciled executable:                      pnl_c = Σ_i w_{i,t-1} · (Π(1+r_i[E+1..E+5]) − 1) + Σ_i w_{i,t} · (Π(1+r_i[E+6..E+48]) − 1)
net_x = pnl_x + (net_ex − pnl_ex from the device rec = carry − cost, identical across calibers); per gross = net / gross_total (health_metrics units chain).
Receipt first: pnl_a recomputed from W must match the device's pnl / pnl_ex column (max |diff| printed; which column matches is reported).
Also: first-25-min slice under old vs new weights, weight overlap 1 − Σ|w_t − w_{t-1}| / (2·Σ|w_t|), retention ratios (c)/(a) and (b)/(a) per window.
usage: exec_caliber_reconcile.py <out.json> <tag=artifact.npz> [...]"""
import sys, json, time, calendar, hashlib
import numpy as np
sys.path.insert(0, "/workspace")
from zload import zload
Z = zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True); CTS = Z["ts"].astype(np.int64); T0 = int(CTS[0]); RET = np.asarray(Z["data"][:, :, 0], np.float32); del Z
fin = np.isfinite(RET); CL = np.concatenate([np.zeros((1, 829)), np.cumsum(np.where(fin, np.log1p(np.clip(RET, -0.99, None)), 0), 0, dtype=np.float64)]); CN = np.concatenate([np.zeros((1, 829), int), np.cumsum(fin, 0)])
def R(Ei, a, b):   # Π(1+r) − 1 over rows Ei+a..Ei+b; 0 where any bar missing (device: nan_to_num on y)
    s = CL[Ei + b + 1] - CL[Ei + a]; n = CN[Ei + b + 1] - CN[Ei + a]; return np.where(n == (b - a + 1), np.expm1(s), 0.0)
COLS = ["ts", "net", "pnl", "carry", "cost", "gross_total", "gross_member", "gross_sel", "nsel", "nmember", "fires", "leg_king", "leg_rev24", "leg_fund", "w3_king", "w3_rev24", "w3_fund", "turnover", "net_ex", "pnl_ex", "carry_ex", "cost_ex", "netlong"]
C = {k: i for i, k in enumerate(COLS)}
def T(s): return int(calendar.timegm(time.strptime(s, "%Y-%m-%d")))
CUT = T("2026-08-10") + 20 * 3600; APY = 2190
WIN = {"2024": (T("2024-01-01"), T("2025-01-01")), "2025": (T("2025-01-01"), T("2026-01-01")), "2026->cut": (T("2026-01-01"), CUT + 1), "2024->26": (T("2024-01-01"), CUT + 1)}
def sharpe(x): return float(x.mean() / x.std(ddof=1) * np.sqrt(APY)) if len(x) > 2 and x.std(ddof=1) > 0 else float("nan")
out = {"self_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(), "artifacts": {}}
for kv in sys.argv[2:]:
    tag, p = kv.split("="); z = np.load(p, allow_pickle=True); assert [str(c) for c in z["cols"]] == COLS
    rec = np.asarray(z["d30_n2_c42_rec"], float); W = np.asarray(z["d30_n2_c42_W"], np.float64)
    ts = rec[:, C["ts"]].astype(np.int64); Ei = (ts - T0) // 300; assert np.all(CTS[Ei] == ts)
    R1_48 = R(Ei, 1, 48); R1_5 = R(Ei, 1, 5); R6_48 = R(Ei, 6, 48)
    Wp = np.vstack([np.zeros((1, 829)), W[:-1]])   # previous anchor's weights (first anchor: flat)
    pnl_a = (W * R1_48).sum(1) * 1e4; pnl_b = (W * R6_48).sum(1) * 1e4
    slice_new = (W * R1_5).sum(1) * 1e4; slice_old = (Wp * R1_5).sum(1) * 1e4; pnl_c = slice_old + pnl_b
    rp, rpx = rec[:, C["pnl"]], rec[:, C["pnl_ex"]]
    rcpt = {"max_abs_diff_vs_pnl": float(np.abs(pnl_a - rp).max()), "max_abs_diff_vs_pnl_ex": float(np.abs(pnl_a - rpx).max()),
            "corr_vs_pnl": float(np.corrcoef(pnl_a, rp)[0, 1]), "corr_vs_pnl_ex": float(np.corrcoef(pnl_a, rpx)[0, 1])}
    base_col = "pnl" if rcpt["max_abs_diff_vs_pnl"] <= rcpt["max_abs_diff_vs_pnl_ex"] else "pnl_ex"
    net_col = "net" if base_col == "pnl" else "net_ex"
    resid = rec[:, C[net_col]] - rec[:, C[base_col]]   # carry − cost (device's own), same for all calibers
    gt = rec[:, C["gross_total"]]
    ovl = 1.0 - np.abs(W - Wp).sum(1) / np.maximum(2 * np.abs(W).sum(1), 1e-12)
    res = {"receipt": rcpt, "weights_column_matches": base_col, "n_anchors": int(len(ts)), "windows": {}}
    for w, (lo, hi) in WIN.items():
        m = (ts >= lo) & (ts < hi)
        if m.sum() < 10: continue
        g = {k: (v[m] + resid[m]) / gt[m] for k, v in (("a_Eclose", pnl_a), ("b_zero_exposure_25m", pnl_b), ("c_reconciled_prev_weights", pnl_c))}
        d = {k: {"mean_bps_anchor_per_gross": round(float(x.mean()), 4), "sharpe_anchor": round(sharpe(x), 3)} for k, x in g.items()}
        ma = g["a_Eclose"].mean()
        d["retention_c_over_a"] = round(float(g["c_reconciled_prev_weights"].mean() / ma), 3) if abs(ma) > 1e-9 else None
        d["retention_b_over_a"] = round(float(g["b_zero_exposure_25m"].mean() / ma), 3) if abs(ma) > 1e-9 else None
        d["first25min_slice_per_gross"] = {"new_weights_w_t": round(float((slice_new[m] / gt[m]).mean()), 4), "prev_weights_w_t-1": round(float((slice_old[m] / gt[m]).mean()), 4)}
        d["device_net_per_gross"] = round(float((rec[m, C[net_col]] / gt[m]).mean()), 4)
        d["weight_overlap_mean"] = round(float(ovl[m].mean()), 4); d["n"] = int(m.sum())
        res["windows"][w] = d
        print(f"[{tag} {w}] n {m.sum()} device {d['device_net_per_gross']:+.4f} | a {d['a_Eclose']['mean_bps_anchor_per_gross']:+.4f} (S {d['a_Eclose']['sharpe_anchor']:.2f}) | b {d['b_zero_exposure_25m']['mean_bps_anchor_per_gross']:+.4f} | c {d['c_reconciled_prev_weights']['mean_bps_anchor_per_gross']:+.4f} (S {d['c_reconciled_prev_weights']['sharpe_anchor']:.2f}) | ret c/a {d['retention_c_over_a']} b/a {d['retention_b_over_a']} | 25m slice new {d['first25min_slice_per_gross']['new_weights_w_t']:+.4f} prev {d['first25min_slice_per_gross']['prev_weights_w_t-1']:+.4f} | overlap {d['weight_overlap_mean']:.3f}", flush=True)
    print(f"[{tag}] receipt {rcpt} -> weights match column {base_col}", flush=True)
    out["artifacts"][tag] = res
json.dump(out, open(sys.argv[1], "w"), indent=1); print("RECONCILE_DONE", flush=True)
