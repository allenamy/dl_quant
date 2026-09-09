"""A0p FPRED: the F10 yearly OOS preds of the SAME vintage the published RAW_M1 arm used (dev_raw -> /workspace/port_w10/f8_2026-08-22/preds/f10_V2MAIN_s*.npy,
axis = port_w10/dlw_2026-08-22 targets), aligned by E_ts to the v4 DL axis (10212). Reports whether that vintage equals the in-service f8_ext preds."""
import numpy as np, hashlib, os, json
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
V4 = np.load("/workspace/dlw_v4raw/data/dlw_targets.npz", allow_pickle=True)["E_ts"].astype(np.int64)
PT = np.load("/workspace/port_w10/dlw_2026-08-22/data/dlw_targets.npz", allow_pickle=True); EP = PT["E_ts"].astype(np.int64)
EX = np.load("/workspace/dlw_ext/data/dlw_targets.npz", allow_pickle=True)["E_ts"].astype(np.int64)
rep = {}
for s in ("42", "2027"):
    a = f"/workspace/port_w10/f8_2026-08-22/preds/f10_V2MAIN_s{s}.npy"; b = f"/workspace/f8_ext/preds/f10_V2MAIN_s{s}.npy"; A = np.load(a); B = np.load(b)
    rep[s] = {"port_w10": {"path": a, "sha16": sha(a), "shape": list(A.shape), "axis_end": int(EP[-1])}, "f8_ext": {"path": b, "sha16": sha(b), "shape": list(B.shape), "axis_end": int(EX[-1])}}
    n = min(len(EP), len(EX)); com = np.intersect1d(EP, EX); ia = np.searchsorted(EP, com); ib = np.searchsorted(EX, com); da = A[ia]; db = B[ib]; ok = np.isfinite(da) & np.isfinite(db)
    rep[s]["common_rows"] = int(len(com)); rep[s]["finite_pattern_equal"] = bool(np.array_equal(np.isfinite(da), np.isfinite(db))); rep[s]["maxabs_common"] = float(np.abs(da[ok] - db[ok]).max()) if ok.any() else None; rep[s]["share_exact"] = float(np.mean(da[ok] == db[ok])) if ok.any() else None
    o = np.full((len(V4), A.shape[1]), np.nan, np.float32); r = {int(t): i for i, t in enumerate(EP)}; n_al = 0
    for k, t in enumerate(V4):
        i = r.get(int(t))
        if i is not None: o[k] = A[i]; n_al += 1
    p = f"/workspace/review_scratch/health_check/dev_v4/f8_2026-08-22/preds/f10_A0p_s{s}.npy"; np.save(p, o); rep[s]["A0p"] = {"path": p, "rows_aligned": n_al, "finite_rows": int(np.isfinite(o).any(1).sum())}
print(json.dumps(rep, indent=1)); json.dump(rep, open("/workspace/review_scratch/v4_gates/a0p_vintage.json", "w"), indent=1)
