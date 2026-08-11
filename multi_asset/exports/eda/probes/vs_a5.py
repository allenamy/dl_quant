"""A5 — asymmetric cap (gate on whether the BOOK can even hold tail information) + BAB mechanism check.

Part 1 — asymmetric cap. Production shape_position clips at the symmetric (1st, 99th) percentile.
A2 found tail information exists only on the SHORT side, so test tightening the long tail
(cap_hi in {90,95,97,99}) while loosening the short tail (cap_lo in {99, 99.5} -> lower clip at the
1st or 0.5th percentile). Zero training; positions rebuilt through the SAME chain.

Part 2 — BAB mechanism (free). If the long/short tail-recall asymmetry is the SAME phenomenon as the
book's persistent betting-against-beta tilt, then per anchor:
    beta of PREDICTED top5%  <  beta of ACTUAL top5%     (we avoid the high-beta names that win big)
    beta of PREDICTED bot5%  >  beta of ACTUAL/其余      (we concentrate shorts in high-beta names)
READ-ONLY; /tmp only.
"""
import sys, json
import numpy as np, pandas as pd
from scipy.stats import rankdata

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
sys.path.insert(0, MA); sys.path.insert(0, MA + "/engine/live")
sys.path.insert(0, "/mnt/storage/private/work_hsy/quant_research_multi_asset")
from engine.panel_source import PanelSource
from engine.signal_chain import SignalChain
from engine.netting import CrossLegNetting

PANEL = MA + "/exports/wide_dl_full_fundfix.npz"
src = PanelSource(panel=PANEL, king=MA + "/exports/eda/king_pred_panel.npz",
                  s2=MA + "/exports/eda/s2_pred_panel_cl4.npz")
zz = np.load(PANEL, allow_pickle=True)
chn = [str(c) for c in zz["ch_names"]]
BETA = zz["CH"][:, :, chn.index("beta_24h")].astype(np.float64)
A = np.sort(np.where((src.member & src.CL4 & np.isfinite(src.king)
                      & np.isfinite(src.s2)).any(1))[0])
yr = pd.to_datetime(src.ts[A], unit="ms", utc=True).year.to_numpy()
YEARS = (int(src.ts[A[-1]]) - int(src.ts[A[0]])) / (1000 * 3600 * 24 * 365.25)


class AsymCap(SignalChain):
    def __init__(self, *a, lo_pct=1.0, hi_pct=99.0, **k):
        super().__init__(*a, **k); self.lo_pct = lo_pct; self.hi_pct = hi_pct

    def shape_position(self, combo):
        mag = np.nan_to_num(np.asarray(combo, float))
        if mag.size >= 10 and np.isfinite(mag).any():
            lo = np.nanpercentile(mag, self.lo_pct); hi = np.nanpercentile(mag, self.hi_pct)
            mag = np.clip(mag, lo, hi)
        return mag - mag.mean()


def book(W, lo_pct, hi_pct):
    ch = AsymCap(src, weights=W, funding_mode="rank", pos_cap_pct=99.0,
                 lo_pct=lo_pct, hi_pct=hi_pct)
    res = CrossLegNetting(ch, W, cost_bps=1.9).run(A, src.ts, year_of=yr)
    bk = {int(t): (m, p / max(float(np.abs(p).sum()), 1e-12)) for (t, m, p) in res["net_positions"]}
    prev = np.zeros(src.N); g = tn = 0.0; ics = []; mx = []
    for t in A:
        ti = int(t); ret = src.Y4[ti]
        if not np.isfinite(ret).any():
            continue
        m, p = bk[ti]
        w = np.zeros(src.N); w[m] = p
        ok = np.isfinite(ret)
        g += float(np.where(ok, w * np.nan_to_num(ret), 0.0).sum())
        tn += float(np.abs(w - prev).sum()); prev = w
        mx.append(float(np.abs(p).max()))
        v = ok[m] & np.isfinite(p)
        if v.sum() >= 5:
            ics.append(np.corrcoef(rankdata(p[v]), rankdata(ret[m][v]))[0, 1])
    G = g / YEARS * 1e4; TN = tn / YEARS
    return dict(ic=float(np.nanmean(ics)), gross=G, turn=TN, maxw=float(np.mean(mx)),
                net19=G - TN * 1.9, net379=G - TN * 3.79, be=G / TN if TN > 0 else np.nan)


CUR = {"king": .595, "s2": .202, "funding": .202, "size": 0.0}
KO = {"king": 1.0, "s2": 0.0, "funding": 0.0, "size": 0.0}
ck = np.load("/tmp/vs_a1_cleanking.npz")
CONFIGS = [("SERVE_current4leg", "/tmp/vs_pred_king_SERVE.npz", "/tmp/vs_pred_s2_SERVE.npz", CUR),
           ("CLEANxattn_kingonly", None, None, KO)]

out = {}
for tag, kp, sp, W in CONFIGS:
    if kp:
        src.king = np.load(kp)["pred"].astype(np.float64)
        src.s2 = np.load(sp)["pred"].astype(np.float64)
    else:
        src.king = ck["xattn"].astype(np.float64)
    print("\n" + "=" * 104); print("CONFIG %s" % tag); print("=" * 104)
    print("%-18s %9s %8s %8s %9s %9s %8s %9s" %
          ("(cap_lo,cap_hi)", "book_IC", "gross", "turn", "net@1.9", "net@3.79", "BE", "mean maxw"))
    base = book(W, 1.0, 99.0)
    print("%-18s %+9.5f %8.0f %8.0f %9.0f %9.0f %8.3f %9.5f   <- baseline symmetric 99"
          % ("(99,99) sym", base["ic"], base["gross"], base["turn"], base["net19"], base["net379"],
             base["be"], base["maxw"]))
    out[tag] = {"baseline": base, "grid": {}}
    for cap_lo in (99.0, 99.5):
        for cap_hi in (90.0, 95.0, 97.0, 99.0):
            if cap_lo == 99.0 and cap_hi == 99.0:
                continue
            r = book(W, 100.0 - cap_lo, cap_hi)
            ic_drop = (base["ic"] - r["ic"]) / abs(base["ic"]) * 100
            ok = (r["net19"] > base["net19"] and r["net379"] > base["net379"]
                  and ic_drop <= 2.0 and r["maxw"] <= base["maxw"])
            print("%-18s %+9.5f %8.0f %8.0f %9.0f %9.0f %8.3f %9.5f   IC%+.1f%% %s"
                  % ("(%.1f,%.0f)" % (cap_lo, cap_hi), r["ic"], r["gross"], r["turn"],
                     r["net19"], r["net379"], r["be"], r["maxw"], -ic_drop,
                     "** PASSES **" if ok else ""))
            out[tag]["grid"]["%.1f_%.0f" % (cap_lo, cap_hi)] = dict(r, ic_drop_pct=ic_drop, passes=bool(ok))

# ---------------- Part 2: BAB mechanism ----------------
print("\n" + "=" * 104); print("BAB MECHANISM CHECK (per-anchor mean beta_24h of each group)"); print("=" * 104)
mech = {}
for tag, path in (("SERVE", "/tmp/vs_pred_king_SERVE.npz"), ("CLEAN_xattn", None)):
    pred = ck["xattn"].astype(np.float64) if path is None else np.load(path)["pred"].astype(np.float64)
    a_, b_, c_, d_ = [], [], [], []
    for t in np.where((src.member & src.CL4 & np.isfinite(src.Y4) & np.isfinite(pred)).any(1))[0]:
        bidx = np.where(src.member[t] & src.CL4[t] & np.isfinite(src.Y4[t])
                        & np.isfinite(pred[t]) & np.isfinite(BETA[t]))[0]
        n = bidx.size
        if n < 40:
            continue
        k = max(1, int(round(0.05 * n)))
        y = src.Y4[t, bidx]; p = pred[t, bidx]; be = BETA[t, bidx]
        op = np.argsort(p); oy = np.argsort(y)
        a_.append(be[op[-k:]].mean())          # predicted top 5%
        b_.append(be[oy[-k:]].mean())          # ACTUAL top 5%
        c_.append(be[op[:k]].mean())           # predicted bottom 5%
        d_.append(be[oy[:k]].mean())           # ACTUAL bottom 5%
    a_, b_, c_, d_ = map(np.array, (a_, b_, c_, d_))
    def pt(x, y_):
        d = x - y_
        return d.mean(), d.mean() / d.std() * np.sqrt(len(d))
    m1, t1 = pt(a_, b_); m2, t2 = pt(c_, d_)
    print("  [%s]  n=%d anchors" % (tag, len(a_)))
    print("     beta of PREDICTED top5% %.4f   vs ACTUAL top5% %.4f   diff %+.4f (t %+.1f)"
          % (a_.mean(), b_.mean(), m1, t1))
    print("     beta of PREDICTED bot5% %.4f   vs ACTUAL bot5% %.4f   diff %+.4f (t %+.1f)"
          % (c_.mean(), d_.mean(), m2, t2))
    print("     predicted bot5% beta - predicted top5% beta = %+.4f  (BAB tilt: >0 means shorts are higher-beta)"
          % (c_.mean() - a_.mean()))
    mech[tag] = dict(pred_top_beta=float(a_.mean()), actual_top_beta=float(b_.mean()),
                     pred_bot_beta=float(c_.mean()), actual_bot_beta=float(d_.mean()),
                     diff_top=float(m1), t_top=float(t1), diff_bot=float(m2), t_bot=float(t2),
                     bab_tilt=float(c_.mean() - a_.mean()), n=int(len(a_)))
out["bab_mechanism"] = mech
json.dump(out, open("/tmp/vs_a5_result.json", "w"), indent=1, default=float)
print("\nsaved /tmp/vs_a5_result.json", flush=True)
