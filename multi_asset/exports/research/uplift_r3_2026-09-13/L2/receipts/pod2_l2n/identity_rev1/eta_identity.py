# Identity control for the minimal fix: hoist D["SF_A"] out of the per-anchor loop (the judge re-decompresses the npz member on every
# one of ~6,123 segments per null). Same rng seeds, same ops => the permuted target y2 and the null IC must be bitwise identical.
import time, json, hashlib, numpy as np
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
ok = np.isfinite(D["SF_A"]); idx = np.flatnonzero(ok); o = idx[np.argsort(i[idx], kind="stable")]; b = np.flatnonzero(np.diff(i[o])) + 1; segs = np.split(o, b)
SF = D["SF_A"]
out = {}
for r in (0, 1):
    t = time.time(); y_old = np.full(i.size, np.nan)
    for sg in segs:
        if sg.size: y_old[sg] = D["SF_A"][sg][np.random.default_rng([20260927, 5, r, int(i[sg[0]])]).permutation(sg.size)]
    t_old = time.time() - t
    t = time.time(); y_new = np.full(i.size, np.nan)
    for sg in segs:
        if sg.size: y_new[sg] = SF[sg][np.random.default_rng([20260927, 5, r, int(i[sg[0]])]).permutation(sg.size)]
    t_new = time.time() - t
    v_old = float(anchor_ic(p, y_old, i, day)[0].mean()); v_new = float(anchor_ic(p, y_new, i, day)[0].mean())
    out[r] = {"y_bitwise_equal": bool(np.array_equal(y_old, y_new, equal_nan=True)), "y_sha_old": hashlib.sha256(y_old.tobytes()).hexdigest()[:16],
              "y_sha_new": hashlib.sha256(y_new.tobytes()).hexdigest()[:16], "null_ic_old": v_old.hex(), "null_ic_new": v_new.hex(),
              "null_ic_equal": v_old == v_new, "t_perm_old_s": round(t_old, 1), "t_perm_new_s": round(t_new, 2)}
    print(r, json.dumps(out[r]), flush=True)
