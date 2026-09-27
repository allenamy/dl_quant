# ETA probe for l2n_judge.py MAIN: same anchor_ic and null-permutation code (copied verbatim), real s42 data, R model, 5 nulls.
import sys, time, json, numpy as np
from scipy.stats import spearmanr
L2="/workspace/uplift_r3_2026-09-13/L2"
def anchor_ic(x, y, i, day):
    ok = np.isfinite(x) & np.isfinite(y); o = np.argsort(i[ok], kind="stable"); xi, yi, ii, di = x[ok][o], y[ok][o], i[ok][o], day[ok][o]
    b = np.flatnonzero(np.diff(ii)) + 1; st = np.concatenate([[0], b]); en = np.concatenate([b, [ii.size]])
    ic, dd, aa = [], [], []
    for a, e in zip(st, en):
        if e - a >= 10:
            v = spearmanr(xi[a:e], yi[a:e])[0]
            if np.isfinite(v): ic.append(v); dd.append(di[a]); aa.append(ii[a])
    return np.array(ic), np.array(dd, np.int64), np.array(aa, np.int64)
D = np.load(f"{L2}/out/L2N_data_s42.npz"); O = np.load(f"{L2}/out/L2N_oos_s42.npz")
i = D["i"].astype(np.int64); day = D["day"].astype(np.int64); p = O["p_R_A"]
print("rows", i.size, "finite p", int(np.isfinite(p).sum()), "finite SF_A", int(np.isfinite(D["SF_A"]).sum()), "SA shape", D["SA"].shape, flush=True)
t = time.time(); ic, _, _ = anchor_ic(p, D["SF_A"], i, day); t_ic = time.time() - t
print("anchor_ic once", round(t_ic, 2), "s; anchors used", ic.size, flush=True)
ok = np.isfinite(D["SF_A"]); idx = np.flatnonzero(ok); o = idx[np.argsort(i[idx], kind="stable")]; b = np.flatnonzero(np.diff(i[o])) + 1; segs = np.split(o, b)
print("segments", len(segs), flush=True)
tp = []; ti = []
for r in range(5):
    t = time.time(); y2 = np.full(i.size, np.nan)
    for sg in segs:
        if sg.size: y2[sg] = D["SF_A"][sg][np.random.default_rng([20260927, 5, r, int(i[sg[0]])]).permutation(sg.size)]
    t1 = time.time(); v, _, _ = anchor_ic(p, y2, i, day); t2 = time.time()
    tp.append(t1 - t); ti.append(t2 - t1)
print(json.dumps({"perm_s": [round(x, 2) for x in tp], "ic_s": [round(x, 2) for x in ti]}), flush=True)
per_null = np.mean(tp) + np.mean(ti)
cell = 200 * per_null + 11 * t_ic   # 7 spectrum + 1 SF + A + B + Pneg (Pneg/decile smaller; upper bound)
print(f"per_null {per_null:.2f}s  per_cell ~{cell/60:.1f} min  total 4 cells ~{4*cell/3600:.2f} h", flush=True)
