"""PREREG_king_clock_E_2026-09-09 AMENDMENT 2: baseline-guard decomposition for the E-version king.
The exporter's guard book (v1iv 3-leg msharpe, 2024->, cost tier b) prices P&L with the META's y4. v4's 2.30 used y4=[E, E+47]
(includes the bar that closed AT the anchor, i.e. before any trade); v4e's meta carries y4=[E+1, E+48]. So 2.26 vs 2.30 mixes a
LABEL-WINDOW effect with a PREDICTION effect. This device separates them with the VERBATIM book() of guard_decompose.py:
  R1 v3 (P3, M3)                      must reproduce the published 2.284 first (#20)
  R2 v4 (P4, M4)                      must reproduce 2.30
  R3 v4e (P4e, M4e)                   must reproduce the export's 2.26
  R4 v3 on the E label  (P3, M3|y4<-E) reference for the re-based band (AMENDMENT 2 rule)
  R5 v4 on the E label  (P4, M4|y4<-E) label effect on the incumbent king
  R6 v4e on the OLD label (P4e aligned to M4 axis, M4)   prediction effect alone
E-label for an old meta = M4e.y4 rows aligned by E_ts (same cache, same members as the old meta; NaN where the E axis lacks the anchor)."""
import numpy as np, time, json, calendar, sys, os
from scipy.stats import rankdata
def xz(v):
    ok = np.isfinite(v); out = np.full(len(v), np.nan); n = ok.sum()
    if n >= 10: out[ok] = rankdata(v[ok]) / max(n - 1, 1) - 0.5
    return out
COST_B = [(-0.25, 5.0, 0.85), (0.5, 6.0, 0.75), (2.0, 8.0, 0.55)]
def tier_of(q):
    t = np.full(len(q), 2, np.int8); t[q >= 1e6] = 1; t[q >= 5e6] = 0
    return t
# AMENDMENT 2 device note: the exporter's guard runs on EXPORT_PANEL=v3splice (2.284 / 2.30 / 2.26); run 1 of this device used v2ext (1.92 replica) and could not reproduce R1/R2 — panel is now an env with the exporter's default.
PANEL = os.environ.get("GUARD_PANEL", "/workspace/data/wide_panel_4h_v3splice.npz")
PW = np.load(PANEL, allow_pickle=True); pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
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
def with_label(MT, y4_src, E_src):
    """copy of meta MT whose y4 rows are replaced by y4_src aligned on E_ts (NaN where absent)."""
    E = MT["E_ts"].astype(np.int64); Y = align_pred(y4_src, E_src, E)
    return {"E_ts": E, "members": MT["members"], "y4": Y, "qvk": MT["qvk"]}
M3 = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True); M4 = np.load("/workspace/data/wide_fea_v4_meta.npz", allow_pickle=True); M4e = np.load("/workspace/data/wide_fea_v4e_meta.npz", allow_pickle=True)
P3 = np.load("/workspace/shadow_bundle_v3/slow_pred_pinned.npy"); P4 = np.load("/workspace/shadow_bundle_v4/slow_pred_pinned.npy"); P4e = np.load("/workspace/shadow_bundle_v4e/slow_pred_pinned.npy")
E3 = M3["E_ts"].astype(np.int64); E4 = M4["E_ts"].astype(np.int64); E4e = M4e["E_ts"].astype(np.int64); Y4e = M4e["y4"]
runs = {"R1 v3 (P3,M3) old label": (P3, M3), "R2 v4 (P4,M4) old label": (P4, M4), "R3 v4e (P4e,M4e) E label": (P4e, M4e),
        "R4 v3 on E label (P3, M3|y4<-E)": (P3, with_label(M3, Y4e, E4e)), "R5 v4 on E label (P4, M4|y4<-E)": (P4, with_label(M4, Y4e, E4e)),
        "R6 v4e on OLD label (P4e->M4 axis, M4)": (align_pred(P4e, E4e, E4), M4)}
PER = {"2024": (T(2024, 1, 1), T(2025, 1, 1)), "2025": (T(2025, 1, 1), T(2026, 1, 1)), "2026→08-10 20Z": (T(2026, 1, 1), T(2026, 8, 10, 20) + 1), "2024-01→2026-08-10 20Z": (T(2024, 1, 1), T(2026, 8, 10, 20) + 1)}
out = {}
for name, (P, MT) in runs.items():
    t0 = time.time(); rec, W3, LRa, idx = book(P, MT); ts = rec[:, 0].astype(np.int64); net = rec[:, 1]; m24 = ts >= T(2024, 1, 1)
    res = {"n_ge2024": int(m24.sum()), "sharpe_guard_ge2024": sharpe(net[m24]), "net_mean_ge2024": float(net[m24].mean()), "std_ge2024": float(net[m24].std()), "w3_king_mean_ge2024": float(W3[m24, 0].mean()) if len(W3) == len(net) else None}
    for w, (lo, hi) in PER.items():
        mm = (ts >= lo) & (ts < hi)
        if mm.any(): res[w] = {"n": int(mm.sum()), "net_mean": float(net[mm].mean()), "sharpe": sharpe(net[mm]), "pnl_mean": float(rec[mm, 2].mean()), "carry_mean": float(rec[mm, 3].mean()), "cost_mean": float(rec[mm, 4].mean())}
    out[name] = res
    print(f"== {name} ({time.time()-t0:.0f}s): guard Sharpe(>=2024) {res['sharpe_guard_ge2024']:.3f} net {res['net_mean_ge2024']:+.3f} std {res['std_ge2024']:.2f} n {res['n_ge2024']} | " + " ".join(f"{w}: S {res[w]['sharpe']:.2f} net {res[w]['net_mean']:+.3f}" for w in PER if w in res), flush=True)
# AMENDMENT 2 rule: re-based band = [ref' - (2.284 - 2.27), ref' + (2.57 - 2.284)] with ref' = R4 (v3 on the E label)
ref_old = out["R1 v3 (P3,M3) old label"]["sharpe_guard_ge2024"]; ref_new = out["R4 v3 on E label (P3, M3|y4<-E)"]["sharpe_guard_ge2024"]; ref_v4 = out["R2 v4 (P4,M4) old label"]["sharpe_guard_ge2024"]
band_new = (ref_new - (2.284 - 2.27), ref_new + (2.57 - 2.284)); s4e = out["R3 v4e (P4e,M4e) E label"]["sharpe_guard_ge2024"]
out["amendment2"] = {"ref_old_v3_reproduced": ref_old, "ref_old_reproduces_2.284": bool(abs(ref_old - 2.284) < 0.005), "v4_reproduces_2.30": bool(abs(ref_v4 - 2.30) < 0.005), "ref_new_v3_on_E_label": ref_new,
                     "label_effect_on_v3": ref_new - ref_old, "label_effect_on_v4": out["R5 v4 on E label (P4, M4|y4<-E)"]["sharpe_guard_ge2024"] - out["R2 v4 (P4,M4) old label"]["sharpe_guard_ge2024"],
                     "prediction_effect_v4e_vs_v4_on_old_label": out["R6 v4e on OLD label (P4e->M4 axis, M4)"]["sharpe_guard_ge2024"] - out["R2 v4 (P4,M4) old label"]["sharpe_guard_ge2024"],
                     "prediction_effect_v4e_vs_v4_on_E_label": s4e - out["R5 v4 on E label (P4, M4|y4<-E)"]["sharpe_guard_ge2024"],
                     "band_old": [2.27, 2.57], "band_rebased": list(band_new), "v4e_guard": s4e, "v4e_in_rebased_band": bool(band_new[0] <= s4e <= band_new[1])}
print("AMENDMENT2", json.dumps(out["amendment2"]), flush=True)
os.makedirs("/workspace/review_scratch/v4_gates", exist_ok=True); out["panel"] = PANEL; json.dump(out, open(os.environ.get("OUT", "/workspace/review_scratch/v4_gates/guard_decompose_v4e.json"), "w"), indent=1); print("GUARD_DECOMPOSE_V4E_DONE", flush=True)
