"""0C — confirm the aux combo FAIL from fold scores (recompute honest ensemble, don't trust JSON) +
panel byte-check + dynamic share. Also confirm the xattn2 depth arm's panel if present."""
import numpy as np, json, glob, hashlib
from scipy.stats import rankdata
TR = "multi_asset/exports/train/"


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:8]


def ens(tag):
    d = TR + tag
    pr = np.load(d + "/panel_ref.npz", allow_pickle=True)
    member, CL, YR = pr["member"].astype(bool), pr["CL"].astype(bool), pr["YR"].astype(np.float64)
    res = []
    for f in sorted(glob.glob(d + "/fold_*_head_scores.npz"), key=lambda x: int(x.split("fold_")[1].split("_")[0])):
        sc = np.load(f)["scores"]; T, N, K = sc.shape
        ics = []
        for t in np.where((member & CL & np.isfinite(YR)).any(1))[0]:
            base = np.where(member[t] & CL[t] & np.isfinite(YR[t]))[0]
            if base.size < 5:
                continue
            comp = np.zeros(base.size); nk = 0
            for k in range(K):
                col = sc[t, base, k]
                if np.isfinite(col).all() and col.std() > 1e-12:
                    comp += (col - col.mean()) / col.std(); nk += 1
            if nk:
                ic = np.corrcoef(rankdata(comp / nk), rankdata(YR[t, base]))[0, 1]
                if np.isfinite(ic):
                    ics.append(ic)
        res.append(round(float(np.mean(ics)), 4))
    return res, md5(d + "/panel_ref.npz")


king, kmd5 = ens("wideA_lamorth0_xattn")
aux, amd5 = ens("wideA_xattn_aux_c1")
print(f"king (lam0+xattn): {king} mean {round(np.mean(king),4)} md5 {kmd5}")
print(f"aux combo:         {aux} mean {round(np.mean(aux),4)} md5 {amd5}")
print(f"Δ per-fold: {[round(a-k,4) for a,k in zip(aux,king)]}  Δmean {round(np.mean(aux)-np.mean(king),4)}")
print(f"all folds worse: {all(a<k for a,k in zip(aux,king))}  below seed-floor 0.0910: {round(np.mean(aux),4)<0.0910}")
print(f"panel byte-check: {'PASS' if amd5==kmd5 else 'MISMATCH'}")
