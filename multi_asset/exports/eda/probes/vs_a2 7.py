"""A2 — tail-recall diagnostic: is there INFORMATION in the tails, or only shape flattening?

The doc argues "ranking is fine but extremes are flattened -> add a distribution/tail head". Our book
caps at the 99th pct then L1-normalises, so better tail MAGNITUDE is largely discarded anyway. The
question that decides the whole class of change is therefore: IS THERE TAIL INFORMATION AT ALL?

(i)   tail recall     : of the names whose REALISED value lands in the top/bottom 5% of an anchor's
                        cross-section, what fraction is in the PREDICTED top/bottom 5%? vs 5% random.
                        Reported in TWO clearly separated versions, because they ask different things:
                          SIGNED    top5% of y   vs top5% of yhat   (who goes up most)
                          MAGNITUDE top5% of |y| vs top5% of |yhat| (who MOVES most)
(ii)  20-bucket E[y | predicted-rank bucket] monotonicity
(iii) calibration slope by prediction stratum (middle 80 / top10 / bottom10 / top2 / bottom2)
(iv)  isotonic vs linear: NOTE rank-IC is STRUCTURALLY invariant to any monotone map, so only the
      magnitude-dependent quantity (P&L) can move. Stated rather than "discovered".

★ Every statistic is PER-ANCHOR CROSS-SECTIONAL, then averaged over anchors. READ-ONLY; /tmp only.
"""
import sys, json, os
import numpy as np, pandas as pd
from scipy.stats import rankdata

MA = "/mnt/storage/private/work_hsy/quant_research_multi_asset/multi_asset"
z = np.load(MA + "/exports/wide_dl_full.npz", allow_pickle=True)
member = z["MEMBER110"]; CL4 = z["CL4"]; Y4 = z["Y4"].astype(np.float64)
T, N = member.shape

SRC = {"TRAIN": "/tmp/vs_pred_king_TRAIN.npz", "SERVE": "/tmp/vs_pred_king_SERVE.npz"}
P = {k: np.load(v)["pred"].astype(np.float64) for k, v in SRC.items()}
ck = np.load("/tmp/vs_a1_cleanking.npz")
P["CLEAN_xattn"] = ck["xattn"]; P["CLEAN_plain"] = ck["plain"]

out = {}
for cal, pred in P.items():
    rows = np.where((member & CL4 & np.isfinite(Y4) & np.isfinite(pred)).any(1))[0]
    rec_s_top = []; rec_s_bot = []; rec_m_top = []; base = []
    buck = np.zeros(20); buckn = np.zeros(20)
    strata = {"bot2": (0, .02), "bot10": (0, .10), "mid80": (.10, .90),
              "top10": (.90, 1.0), "top2": (.98, 1.0)}
    num = {k: 0.0 for k in strata}; den = {k: 0.0 for k in strata}
    for t in rows:
        b = np.where(member[t] & CL4[t] & np.isfinite(Y4[t]) & np.isfinite(pred[t]))[0]
        n = b.size
        if n < 40:
            continue
        y = Y4[t, b]; p = pred[t, b]
        k = max(1, int(round(0.05 * n)))
        oy = np.argsort(y); op = np.argsort(p)
        rec_s_top.append(len(np.intersect1d(oy[-k:], op[-k:])) / k)
        rec_s_bot.append(len(np.intersect1d(oy[:k], op[:k])) / k)
        oay = np.argsort(np.abs(y)); oap = np.argsort(np.abs(p))
        rec_m_top.append(len(np.intersect1d(oay[-k:], oap[-k:])) / k)
        base.append(k / n)
        # (ii) buckets by predicted rank; realised y demeaned within the anchor
        r = (rankdata(p) - 1) / (n - 1)
        yd = y - y.mean()
        idx = np.clip((r * 20).astype(int), 0, 19)
        np.add.at(buck, idx, yd); np.add.at(buckn, idx, 1)
        # (iii) calibration slope per stratum: y_demeaned on cross-sectionally standardised pred
        sp = p.std()
        if sp > 1e-12:
            zz = (p - p.mean()) / sp
            for nm, (lo, hi) in strata.items():
                s = (r >= lo) & (r < hi) if hi < 1.0 else (r >= lo)
                if s.sum() >= 3:
                    num[nm] += float(zz[s] @ yd[s]); den[nm] += float(zz[s] @ zz[s])
    rs_t = np.array(rec_s_top); rs_b = np.array(rec_s_bot); rm = np.array(rec_m_top); bs = np.array(base)
    def lift(a):
        d = a - bs
        return a.mean(), a.mean() / bs.mean(), d.mean() / d.std() * np.sqrt(len(d))
    print("\n" + "=" * 92); print("CALIBER %s   (n anchors = %d)" % (cal, len(rs_t))); print("=" * 92)
    print("  (i) TAIL RECALL vs random baseline %.4f" % bs.mean())
    for nm, a in (("SIGNED  top5%", rs_t), ("SIGNED  bot5%", rs_b), ("MAGNITUDE top5%|y|", rm)):
        m, lf, tt = lift(a)
        print("      %-20s recall %.4f   lift %.2fx   t(vs baseline) %+.1f" % (nm, m, lf, tt))
    bm = buck / np.maximum(buckn, 1)
    sp_mono = np.corrcoef(rankdata(np.arange(20)), rankdata(bm))[0, 1]
    print("  (ii) 20-bucket E[y|bucket] (bps, anchor-demeaned): monotonicity Spearman %+.3f" % sp_mono)
    print("      " + " ".join("%+.1f" % (v * 1e4) for v in bm))
    print("  (iii) calibration slope by prediction stratum (y_demeaned on xsec-standardised pred):")
    sl = {nm: (num[nm] / den[nm] if den[nm] > 0 else np.nan) for nm in strata}
    for nm in ("bot2", "bot10", "mid80", "top10", "top2"):
        print("      %-6s slope %+0.6f  (x mid80: %.2f)" % (nm, sl[nm], sl[nm] / sl["mid80"] if sl["mid80"] else np.nan))
    out[cal] = dict(baseline=float(bs.mean()),
                    recall_signed_top=float(rs_t.mean()), recall_signed_bot=float(rs_b.mean()),
                    recall_mag_top=float(rm.mean()),
                    lift_signed_top=float(rs_t.mean() / bs.mean()),
                    lift_signed_bot=float(rs_b.mean() / bs.mean()),
                    lift_mag_top=float(rm.mean() / bs.mean()),
                    bucket_mean_bps=[float(v * 1e4) for v in bm], bucket_monotonic=float(sp_mono),
                    slopes={k: float(v) for k, v in sl.items()}, n_anchors=int(len(rs_t)))

json.dump(out, open("/tmp/vs_a2_result.json", "w"), indent=1, default=float)
print("\n(iv) NOTE: rank-IC is invariant to ANY monotone transform, so isotonic-vs-linear can move")
print("     only magnitude-dependent quantities (P&L), never rank-IC. Not measured as if unknown.")
print("saved /tmp/vs_a2_result.json", flush=True)
