"""0C — ARM-N1a fold0 EARLY SCREEN: xsec pred-corr vs king & s2. Criterion: BOTH <=0.36 -> continue; either >0.36 -> reskin, pull arm."""
import numpy as np, pandas as pd, glob, hashlib, json
from scipy.stats import rankdata
TR = "multi_asset/exports/train/"; EDA = "multi_asset/exports/eda/"
N1A = TR + "wideA_n1a_comovepre_c1"; S2 = TR + "wideA_s2_y24_5yr"


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""): h.update(c)
    return h.hexdigest()[:8]


def comp_panel(scores, member, CL, YR):
    T, N, K = scores.shape; C = np.full((T, N), np.nan)
    for t in np.where((member & CL & np.isfinite(YR)).any(1))[0]:
        b = np.where(member[t] & CL[t] & np.isfinite(YR[t]))[0]
        if b.size < 5: continue
        comp = np.zeros(b.size); nk = 0
        for k in range(K):
            col = scores[t, b, k]
            if np.isfinite(col).all() and col.std() > 1e-12: comp += (col - col.mean()) / col.std(); nk += 1
        if nk: C[t, b] = comp / nk
    return C


def ricorr(a, b): return np.corrcoef(rankdata(a), rankdata(b))[0, 1]


pr = np.load(N1A + "/panel_ref.npz", allow_pickle=True)
member, CL, YR = pr["member"].astype(bool), pr["CL"].astype(bool), pr["YR"].astype(np.float64)
T, N = YR.shape
kp = np.load(EDA + "king_pred_panel.npz", allow_pickle=True); king = kp["king_pred"].astype(np.float64)
prs2 = np.load(S2 + "/panel_ref.npz", allow_pickle=True); CL2, YR2 = prs2["CL"].astype(bool), prs2["YR"].astype(np.float64)
S2c = np.full((T, N), np.nan)
for f in sorted(glob.glob(S2 + "/fold_*_head_scores.npz")):
    C = comp_panel(np.load(f)["scores"], member, CL2, YR2); m = np.isfinite(C); S2c[m] = C[m]

z = np.load(N1A + "/fold_0_head_scores.npz"); te = z["te_rows"]
Cn = comp_panel(z["scores"], member, CL, YR)
print("N1a panel md5", md5(N1A + "/panel_ref.npz"), "fold0 te", te.shape[0])

kpc, s2pc, inc, s2cov = [], [], [], 0
for t in te:
    b = np.where(member[t] & CL[t] & np.isfinite(YR[t]) & np.isfinite(Cn[t]) & np.isfinite(king[t]))[0]
    if b.size < 8: continue
    s = Cn[t, b]
    inc.append(ricorr(s, YR[t, b])); kpc.append(ricorr(s, king[t, b]))
    if np.isfinite(S2c[t, b]).all() and S2c[t, b].std() > 1e-12:
        s2pc.append(ricorr(s, S2c[t, b])); s2cov += 1
kpc = np.array(kpc); s2pc = np.array(s2pc); inc = np.array(inc)
king_pc = float(kpc.mean()); s2_pc = float(s2pc.mean()) if s2pc.size else float("nan")
print(f"fold0 increment(IC vs YR12B) {inc.mean():+.4f} (n_ts={len(inc)})")
print(f"pred-corr vs KING  {king_pc:.3f}  (per-ts std {kpc.std():.3f})")
print(f"pred-corr vs S2    {s2_pc:.3f}  (cov {s2cov}/{len(inc)})")
verdict = "CONTINUE (both<=0.36)" if (king_pc <= 0.36 and (np.isnan(s2_pc) or s2_pc <= 0.36)) else "RESKIN-PULL (>0.36)"
print("VERDICT:", verdict)
json.dump(dict(arm="N1a", horizon=12, panel_md5=md5(N1A + "/panel_ref.npz"), fold0_increment=round(float(inc.mean()), 4),
               pred_corr_king=round(king_pc, 3), pred_corr_s2=round(s2_pc, 3), s2_cov=s2cov, n_ts=len(inc),
               criterion="both<=0.36", verdict=verdict),
          open(EDA + "arm_n1a_screen.json", "w"), indent=2)
print("SAVED " + EDA + "arm_n1a_screen.json")
