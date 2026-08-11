"""A3 — free uncertainty: disagreement among the 6 factor heads.

u(anchor, name) = std across the 6 CROSS-SECTIONALLY Z-SCORED head columns (same z-scoring the
composite already uses, so u is on the composite's own scale).

(i)   per-anchor xsec corr(u, |realised y|) and corr(u, rvol_72h)
(ii)  rank-IC within u-terciles (is the model more accurate where its heads agree?)
(iii) edge = sign(mu) * max(|mu| - k*u, 0)  -> king_only book rank-IC + P&L, k in {0.25,0.5,1.0}

★ CALIBER LIMIT: head columns exist on disk only for runs whose head_scores were exported, i.e. the
  DIRTY champion and the S1 CLEAN runs. There is no SERVE-caliber u without re-running inference
  (~75 min) because vs_infer.py stored only the composite, not the 6 columns. Stated, not hidden.
READ-ONLY; /tmp only.
"""
import sys, json, glob
import numpy as np, pandas as pd
from scipy.stats import rankdata

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
from engine.panel_source import PanelSource
from engine.signal_chain import SignalChain
from engine.netting import CrossLegNetting

z = np.load(MA + "/exports/wide_dl_full.npz", allow_pickle=True)
member = z["MEMBER110"]; CL4 = z["CL4"]; Y4 = z["Y4"].astype(np.float64); YR4 = z["YR4"]
chn = [str(c) for c in z["ch_names"]]
SIG = z["CH"][:, :, chn.index("rvol_72h")].astype(np.float64)
T, N = member.shape
TR = MA + "/exports/train/"
RUNS = {"DIRTY_champ": TR + "wideA_lamorth0_xattn_5yr",
        "CLEAN_xattn": TR + "wideA_lamorth0_xattn_5yr_causal_v1",
        "CLEAN_plain": TR + "wideA_lamorth0_5yr_causal_v1"}


def comp_and_u(d):
    """composite mu and head-disagreement u, both from the recorded head_scores."""
    MU = np.full((T, N), np.nan); U = np.full((T, N), np.nan)
    for f in sorted(glob.glob(d + "/fold_*_head_scores.npz")):
        sc = np.load(f)["scores"]
        for t in np.where((member & CL4 & np.isfinite(YR4)).any(1))[0]:
            b = np.where(member[t] & CL4[t] & np.isfinite(YR4[t]))[0]
            if b.size < 5:
                continue
            cols = []
            for k in range(sc.shape[2]):
                col = sc[t, b, k]
                if np.isfinite(col).all() and col.std() > 1e-12:
                    cols.append((col - col.mean()) / col.std())
            if cols:
                Z = np.stack(cols)                    # (n_live, n_names) z-scored heads
                MU[t, b] = Z.mean(0)
                U[t, b] = Z.std(0) if Z.shape[0] > 1 else 0.0
    return MU, U


PANEL = MA + "/exports/wide_dl_full_fundfix.npz"
src = PanelSource(panel=PANEL, king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")
A = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king)
                      & np.isfinite(src.s2)).any(1))[0])
yr = pd.to_datetime(src.ts[A], unit="ms", utc=True).year.to_numpy()
YEARS = (int(src.ts[A[-1]]) - int(src.ts[A[0]])) / (1000 * 3600 * 24 * 365.25)
KO = {"king": 1.0, "s2": 0.0, "funding": 0.0, "size": 0.0}


def book(pred):
    src.king = pred
    ch = SignalChain(src, weights=KO, funding_mode="rank", pos_cap_pct=99.0)
    res = CrossLegNetting(ch, KO, cost_bps=1.9).run(A, src.ts, year_of=yr)
    bk = {int(t): (m, p / max(float(np.abs(p).sum()), 1e-12)) for (t, m, p) in res["net_positions"]}
    prev = np.zeros(src.N); g = tn = 0.0; ics = []
    for t in A:
        ti = int(t); ret = src.Y4[ti]
        if not np.isfinite(ret).any():
            continue
        m, p = bk[ti]
        w = np.zeros(src.N); w[m] = p
        ok = np.isfinite(ret)
        g += float(np.where(ok, w * np.nan_to_num(ret), 0.0).sum())
        tn += float(np.abs(w - prev).sum()); prev = w
        v = ok[m] & np.isfinite(p)
        if v.sum() >= 5:
            ics.append(np.corrcoef(rankdata(p[v]), rankdata(ret[m][v]))[0, 1])
    return float(np.nanmean(ics)), g / YEARS * 1e4, (g - tn * 1.9e-4) / YEARS * 1e4, tn / YEARS


out = {}
for nm, d in RUNS.items():
    MU, U = comp_and_u(d)
    rows = np.where((member & CL4 & np.isfinite(Y4) & np.isfinite(MU) & np.isfinite(U)).any(1))[0]
    c_uy, c_us, ic_lo, ic_mid, ic_hi = [], [], [], [], []
    for t in rows:
        b = np.where(member[t] & CL4[t] & np.isfinite(Y4[t]) & np.isfinite(MU[t]) & np.isfinite(U[t]))[0]
        if b.size < 30:
            continue
        u = U[t, b]; y = Y4[t, b]; mu = MU[t, b]; s = SIG[t, b]
        if u.std() > 1e-12:
            c_uy.append(np.corrcoef(rankdata(u), rankdata(np.abs(y)))[0, 1])
            ok = np.isfinite(s)
            if ok.sum() > 20 and s[ok].std() > 1e-12:
                c_us.append(np.corrcoef(rankdata(u[ok]), rankdata(s[ok]))[0, 1])
        q = np.quantile(u, [1 / 3, 2 / 3])
        for sel, box in ((u <= q[0], ic_lo), ((u > q[0]) & (u <= q[1]), ic_mid), (u > q[1], ic_hi)):
            if sel.sum() >= 5 and mu[sel].std() > 1e-12:
                box.append(np.corrcoef(rankdata(mu[sel]), rankdata(y[sel]))[0, 1])
    print("\n" + "=" * 88); print("RUN %s" % nm); print("=" * 88)
    print("  (i) per-anchor xsec corr(u, |y|)      = %+.4f   (n=%d)" % (np.mean(c_uy), len(c_uy)))
    print("      per-anchor xsec corr(u, rvol_72h) = %+.4f   (n=%d)" % (np.mean(c_us), len(c_us)))
    lo, mid, hi = np.mean(ic_lo), np.mean(ic_mid), np.mean(ic_hi)
    dif = np.array(ic_lo[:min(len(ic_lo), len(ic_hi))]) - np.array(ic_hi[:min(len(ic_lo), len(ic_hi))])
    print("  (ii) rank-IC by u-tercile:  LOW-u %+.5f | MID %+.5f | HIGH-u %+.5f | low-high %+.5f (t %+.1f)"
          % (lo, mid, hi, lo - hi, dif.mean() / dif.std() * np.sqrt(len(dif))))
    print("  (iii) edge = sign(mu)*max(|mu| - k*u, 0)  on the king_only book:")
    base = book(MU.copy())
    print("       %-8s bookIC %+0.5f  gross %8.1f  net %8.1f  turn %7.0f" % ("k=0 (raw)", *base))
    rec = {"corr_u_absy": float(np.mean(c_uy)), "corr_u_sigma": float(np.mean(c_us)),
           "ic_low_u": float(lo), "ic_mid_u": float(mid), "ic_high_u": float(hi),
           "ic_low_minus_high": float(lo - hi),
           "t_low_minus_high": float(dif.mean() / dif.std() * np.sqrt(len(dif))),
           "edge": {"0": list(base)}}
    for k in (0.25, 0.5, 1.0):
        E = np.sign(MU) * np.maximum(np.abs(MU) - k * U, 0.0)
        r = book(E)
        print("       k=%-5.2f bookIC %+0.5f  gross %8.1f  net %8.1f  turn %7.0f" % (k, *r))
        rec["edge"][str(k)] = list(r)
    out[nm] = rec

json.dump(out, open("/tmp/vs_a3_result.json", "w"), indent=1, default=float)
print("\nsaved /tmp/vs_a3_result.json", flush=True)
