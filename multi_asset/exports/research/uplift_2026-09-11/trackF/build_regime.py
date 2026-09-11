"""Track F step 1: ex-ante regime variables on the v4 replay axis.
All variables at anchor i use ONLY panel row j(i) trailing features (f_* are trailing by
construction: f_rev_24h is the leg score of the REVERSAL leg, f_mom_7d/f_vol_7d/f_range_24h
are trailing windows) plus the funding rate known AT the anchor. No forward return enters.
Universe = meta members[i] INTERSECT the CRYPTO m1 umask (the same mask the judge's arms use).
Output: /workspace/uplift_2026-09-11/trackF/regime_vars.npz
"""
import numpy as np, time
B = "/workspace/review_scratch/health_check/dev_v4/pod_backup_2026-08-21"
MT = np.load(f"{B}/wide_fea_hist_meta.npz", allow_pickle=True)
E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]
PW = np.load(f"{B}/wide_panel_4h_hist_v2.npz", allow_pickle=True)
pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
SYM = [str(s) for s in PW["symbols"]]
UM = np.load("/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz", allow_pickle=True)
assert [str(x) for x in UM["symbols"]] == SYM, "umask symbols mismatch"
umap = {int(t): k for k, t in enumerate(UM["ts"].astype(np.int64))}
UMM = np.asarray(UM["mask"])
FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]; R24 = PW["f_rev_24h"]
V7 = PW["f_vol_7d"]; M7 = PW["f_mom_7d"]; RG = PW["f_range_24h"]
_IVf = np.where(np.isfinite(IV) & (IV > 0), IV, 8.0)
RN8 = FN * (8.0 / _IVf)            # 8h-equivalent funding rate, same formula as the device
ibtc = SYM.index("BTCUSDT")
rows = []; first_seen = {}
for i, t in enumerate(E_ts):
    j = pw_row.get(int(t))
    if j is None: continue
    m = members[i]
    k = umap.get(j)
    if k is not None: m = m[UMM[k][m]]
    if len(m) < 50: continue
    for s in m:
        if s not in first_seen: first_seen[s] = t
    young = float(np.mean([(t - first_seen[s]) < 30 * 86400 for s in m]))
    f = RN8[j, m]; f = f[np.isfinite(f)]
    r = R24[j, m]; r = r[np.isfinite(r)]
    v = V7[j, m]; v = v[np.isfinite(v)]
    mm = M7[j, m]; mm = mm[np.isfinite(mm)]
    rg = RG[j, m]; rg = rg[np.isfinite(rg)]
    nn = lambda a, fn: (float(fn(a)) if len(a) > 50 else np.nan)
    rows.append((int(t), len(m),
                 nn(f, lambda a: 1e4 * np.std(a)), nn(f, lambda a: 1e4 * np.mean(a)),
                 nn(f, lambda a: 1e4 * np.median(a)), nn(f, lambda a: np.mean(a < 0)),
                 nn(r, np.std), nn(r, np.mean), nn(r, lambda a: np.mean(a > 0)),
                 nn(v, np.median), nn(mm, lambda a: np.median(np.abs(a))), nn(rg, np.median),
                 float(R24[j, ibtc]), float(M7[j, ibtc]), float(V7[j, ibtc]), young))
COLS = ["ts", "nmem", "sig_fund", "fund_mean", "fund_med", "frac_neg", "disp24", "mean24",
        "breadth_up", "vol7_med", "absmom7_med", "range24_med", "btc_r24", "btc_m7", "btc_v7", "young30"]
A = np.array(rows, dtype=np.float64)
np.savez_compressed("/workspace/uplift_2026-09-11/trackF/regime_vars.npz", cols=np.array(COLS), V=A)
print("n", A.shape, "first", time.strftime("%F %HZ", time.gmtime(A[0, 0])), "last", time.strftime("%F %HZ", time.gmtime(A[-1, 0])))
yr = np.array([time.gmtime(int(t)).tm_year for t in A[:, 0]])
print("year      n " + " ".join(f"{c:>11s}" for c in COLS[2:]))
for y in range(2022, 2027):
    m = yr == y
    print(f"{y} {int(m.sum()):6d} " + " ".join(f"{np.nanmean(A[m, k]):11.4f}" for k in range(2, len(COLS))))
