"""king does NOT regress on y4. pod_export_bundle_v3.py L41:
       rr = rankdata(yv[ok]) / max(ok.sum()-1,1) - 0.5
   The label is the per-anchor CROSS-SECTIONAL RANK of y4 scaled to [-0.5,+0.5].
   So the clip's MAGNITUDE distortion matters only insofar as it changes ORDER.
   Worst-case bound needs no new data: push every lo-clipped name to the bottom, every hi-clipped to the top."""
import numpy as np, time, sys
from scipy.stats import rankdata, spearmanr
sys.path.insert(0, "/workspace")
from zload import zload
MT = np.load("/workspace/data/wide_fea_v2ext_meta.npz", allow_pickle=True)
ets = MT["E_ts"].astype(np.int64); y4 = MT["y4"]; members = MT["members"]
F = np.load("/workspace/review_scratch/clip_flags.npz", allow_pickle=True)
fts = F["E_ts"].astype(np.int64); has = F["has"]; gi = {t: i for i, t in enumerate(fts)}
Z = zload("/workspace/data/dlnative_5m_wide829_f16_ext.npz", allow_pickle=True)
CTS = Z["ts"].astype(np.int64); r5 = Z["data"][:, :, 0].astype(np.float32); fin5 = np.isfinite(r5)
HI = np.float32(np.float16(0.3)); LO = np.float32(np.float16(-0.3))
NW = r5.shape[1]
CSlo = np.concatenate([np.zeros((1, NW), np.int32), np.cumsum((r5 == LO) & fin5, 0, dtype=np.int32)])
CShi = np.concatenate([np.zeros((1, NW), np.int32), np.cumsum((r5 == HI) & fin5, 0, dtype=np.int32)])
cidx = {int(t): i for i, t in enumerate(CTS)}
del r5, fin5
yrs = np.array([time.gmtime(int(t)).tm_year for t in ets])
tot_l2 = 0.0; bad_l2 = 0.0; n_tot = 0; n_bad = 0; wc_dl2 = 0.0; sp_list = []; nrow_aff = 0
for i in range(len(ets)):
    if yrs[i] >= 2026:
        continue
    m = members[i]; yv = y4[i, m]; ok = np.isfinite(yv)
    if ok.sum() < 50:
        continue
    n = int(ok.sum())
    rr = rankdata(yv[ok]) / max(n - 1, 1) - 0.5
    tot_l2 += float((rr ** 2).sum()); n_tot += n
    t = int(ets[i])
    if t not in gi or not has[gi[t]].any():
        continue
    E = cidx.get(t)
    if E is None:
        continue
    mm = m[ok]
    nlo = CSlo[E + 48, mm] - CSlo[E, mm]; nhi = CShi[E + 48, mm] - CShi[E, mm]
    aff = (nlo + nhi) > 0
    if not aff.any():
        continue
    nrow_aff += 1
    bad_l2 += float((rr[aff] ** 2).sum()); n_bad += int(aff.sum())
    ynew = yv[ok].astype(np.float64).copy()
    lo_a = aff & (nlo > 0); hi_a = aff & (nhi > 0)
    if lo_a.any():
        ynew[lo_a] = np.nanmin(yv[ok]) - 1.0 - np.arange(int(lo_a.sum()))
    if hi_a.any():
        ynew[hi_a] = np.nanmax(yv[ok]) + 1.0 + np.arange(int(hi_a.sum()))
    rr2 = rankdata(ynew) / max(n - 1, 1) - 0.5
    wc_dl2 += float(((rr2 - rr) ** 2).sum())
    sp_list.append(spearmanr(rr, rr2).correlation)
print("== king label = per-anchor cross-sectional RANK in [-0.5,+0.5]  (pod_export_bundle_v3.py L41) ==")
print("training window YRA<2026")
print("  member rows used                  : %d" % n_tot)
print("  rows on clip-affected names       : %d (%.4f%%)" % (n_bad, 100 * n_bad / max(n_tot, 1)))
print("  anchors touched                   : %d" % nrow_aff)
print("  L2 mass of rank labels, corrupted : %.4f%% of total" % (100 * bad_l2 / max(tot_l2, 1e-30)))
print("  *** WORST-CASE label change  sum(d_rr^2)/sum(rr^2) = %.4f%%" % (100 * wc_dl2 / max(tot_l2, 1e-30)))
if sp_list:
    s = np.array(sp_list)
    print("  *** worst-case per-anchor Spearman(recorded rank, corrected rank): min %.6f  p05 %.6f  median %.6f" % (s.min(), np.percentile(s, 5), np.median(s)))
