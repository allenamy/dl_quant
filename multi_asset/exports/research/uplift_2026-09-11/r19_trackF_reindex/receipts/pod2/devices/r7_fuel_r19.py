"""R7 FUEL-2 step B: the FUEL GAUGE, per anchor.
Definition copied VERBATIM from /workspace/uplift_2026-09-11/r6j1_regime.py (which itself copies
trackF/build_regime.py + label_and_arsenal.py): sig_fund = 1e4 * cross-sectional SD of the 8h-EQUIVALENT
funding rate over the CRYPTO(m1)-masked member set of the anchor; disp24 = xsec SD of f_rev_24h.
Nothing about the definition is changed. Two trees are read:
  incumbent  = dev_v4/pod_backup_2026-08-21          (axis ends 2026-08-31 20Z)
  x0910      = dev_v4_x0910/pod_backup_2026-08-21    (axis ends 2026-09-10 20Z; the CRYPTO mask stops at
               2026-08-31 00Z so its last row is carried forward for September -- flagged, as in r6j1)
REGRESSION: the incumbent prefix of the x0910 run must reproduce the incumbent run's sig_fund BITWISE."""
import numpy as np, json, time, hashlib, os
OUT="/workspace/uplift_2026-09-11/r19_trackF_reindex/out_r7f2"
ENV_WL=[]  # this device reads NO environment variable (E-0826-D: enumerated and empty)
assert all(k not in os.environ for k in ENV_WL)
def run(base):
    MT = np.load(f"{base}/wide_fea_hist_meta.npz", allow_pickle=True)
    E_ts = MT["E_ts"].astype(np.int64); members = MT["members"]
    PW = np.load(f"{base}/wide_panel_4h_hist_v2.npz", allow_pickle=True)
    pw_row = {int(t): j for j, t in enumerate(PW["ts"].astype(np.int64))}
    SYM = [str(s) for s in PW["symbols"]]
    UM = np.load("/workspace/review_scratch/health_check/masks/umask_UPIT_CRYPTO.npz", allow_pickle=True)
    assert [str(x) for x in UM["symbols"]] == SYM
    umap = {int(t): k for k, t in enumerate(UM["ts"].astype(np.int64))}; UMM = np.asarray(UM["mask"])
    last_mask_ts = int(UM["ts"].astype(np.int64)[-1]); carried = 0
    FN = PW["f_fund_now"]; IV = PW["f_fund_iv"]; R24 = PW["f_rev_24h"]
    _IVf = np.where(np.isfinite(IV) & (IV > 0), IV, 8.0); RN8 = FN * (8.0 / _IVf)
    rows = []
    for i, t in enumerate(E_ts):
        j = pw_row.get(int(t))
        if j is None: continue
        m = members[i]; k = umap.get(int(t))
        if k is not None: m = m[UMM[k][m]]
        elif int(t) > last_mask_ts: m = m[UMM[-1][m]]; carried += 1
        if len(m) < 50: continue
        f = RN8[j, m]; f = f[np.isfinite(f)]; r = R24[j, m]; r = r[np.isfinite(r)]
        nn = lambda a, fn: (float(fn(a)) if len(a) > 50 else np.nan)
        # extra diagnostics (do NOT enter the label definition): xsec MEAN 8h rate, share negative, n
        rows.append((int(t), len(m), nn(f, lambda a: 1e4*np.std(a)), nn(r, np.std),
                     nn(f, lambda a: 1e4*np.mean(a)), nn(f, lambda a: float((a < 0).mean())), len(f)))
    A = np.array(rows, float)
    return A, carried
A0, c0 = run("/workspace/review_scratch/health_check/dev_v4/pod_backup_2026-08-21")
AX, cx = run("/workspace/review_scratch/health_check/dev_v4_x0910/pod_backup_2026-08-21")
n0 = A0.shape[0]
assert np.array_equal(AX[:n0,0].astype(np.int64), A0[:n0,0].astype(np.int64)), "axis prefix mismatch"
bw = bool(np.array_equal(np.isnan(AX[:n0,2]), np.isnan(A0[:,2])) and
          np.array_equal(AX[:n0,2][~np.isnan(A0[:,2])], A0[:,2][~np.isnan(A0[:,2])]))
print(f"PREFIX REGRESSION sig_fund bitwise: {bw}  (incumbent n={n0}, x0910 n={AX.shape[0]}, carried rows inc/x0910 {c0}/{cx})")
assert bw
F = lambda t: time.strftime("%Y-%m-%d %H:%MZ", time.gmtime(int(t)))
print("incumbent axis", F(A0[0,0]), "->", F(A0[-1,0]), " x0910 axis", F(AX[0,0]), "->", F(AX[-1,0]))
# monthly medians (reproduce the round-6 quoted numbers)
mon = {}
for r in AX:
    k = time.strftime("%Y-%m", time.gmtime(int(r[0])))
    mon.setdefault(k, []).append((r[2], r[4]))
MON = {k: {"n": len(v), "sig_fund_med": round(float(np.nanmedian([x[0] for x in v])),4),
           "mean8h_bps_mean": round(float(np.nanmean([x[1] for x in v])),4)} for k, v in sorted(mon.items())}
for k in ("2026-02","2026-07","2026-08","2026-09"):
    if k in MON: print(k, MON[k])
np.savez_compressed(f"{OUT}/R7_FUEL.npz", inc=A0, x0910=AX,
                    cols=np.array(["ts","n_members","sig_fund","disp24","mean8h_bps","frac_neg","n_fin"]))
json.dump({"self_sha256":hashlib.sha256(open(__file__,"rb").read()).hexdigest(),
           "env_whitelist":ENV_WL,"prefix_regression_bitwise":bw,
           "n_incumbent":int(n0),"n_x0910":int(AX.shape[0]),
           "carried_mask_rows":{"incumbent":c0,"x0910":cx},
           "axis":{"incumbent":[F(A0[0,0]),F(A0[-1,0])],"x0910":[F(AX[0,0]),F(AX[-1,0])]},
           "monthly":MON}, open(f"{OUT}/R7_FUEL_RECEIPT.json","w"), indent=1)
print("FUEL_DONE")
