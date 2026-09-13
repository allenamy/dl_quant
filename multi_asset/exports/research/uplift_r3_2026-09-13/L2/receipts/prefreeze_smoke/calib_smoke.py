# SMOKE calibration on SYNTHETIC targets only: fixed smoke R_B / R_A scores, many iid synthetic target draws => true SD of G,
# vs the day-block bootstrap SE and the within-anchor day-consistent permutation null SD (single draw). Also the 00Z-only variant for B.
import sys, numpy as np
sys.path.insert(0, "/workspace/uplift_r3_2026-09-13/L2_smoke2/devices")
import l2_b_common as B
S = "/workspace/uplift_r3_2026-09-13/L2_smoke2"
Z = np.load(S + "/out/L2_B_data_s42.npz"); O = np.load(S + "/out/L2_B_oos_s42.npz")
I = Z["i"].astype(np.int64); Nn = Z["n"].astype(np.int64); YR = Z["year"].astype(np.int64); DAYv = Z["day"].astype(np.int64); E = Z["E"]
k = I + 138
meta = np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz")["y4"]; fin = np.isfinite(meta)
for T, only00 in (("A", False), ("B", False), ("B", True)):
    base_ok = (YR >= 2023) & (np.isfinite(Z["r" + T]))
    if only00: base_ok &= (E % 86400 == 0)
    idx, a, sizes, _ = B.anchor_index(I, base_ok); big = sizes[a] >= 10
    idx, a, sizes, _ = B.anchor_index(I, np.isin(np.arange(I.size), idx[big]))
    col = Nn[idx]; st = np.concatenate([[0], np.cumsum(sizes)[:-1]]); day_a = DAYv[idx][st]
    ud, dinv = np.unique(day_a, return_inverse=True); Cm = B.draw_counts(ud.size)
    p = O["p_R_%s_FULL" % T][idx]
    top, bot, m = B.decile_sets(p, a, sizes, col)
    Gs = []; ses = []
    kk = k[idx]; nn = Nn[idx]
    for d in range(120):
        g = np.random.default_rng([777, d]); Ysyn = np.where(fin, g.normal(0, 0.02, fin.shape), np.nan)
        if T == "A":
            r = Ysyn[kk, nn]
        else:
            r = np.prod(np.stack([1.0 + Ysyn[kk + q, nn] for q in range(6)], 1), 1) - 1.0
        s = -1e4 * r
        Dv, Hv = B.anchor_stats(s, a, sizes, top, bot)
        Gs.append(Dv.mean())
        if d < 5:
            ci = B.boot_ci(Cm, np.bincount(dinv, Dv, ud.size), np.bincount(dinv, None, ud.size)); ses.append((ci[1] - ci[0]) / 3.92)
    Gs = np.array(Gs)
    print(T, "only00" if only00 else "all", "anchors", sizes.size, "true SD(G) over draws %.3f mean %.3f" % (Gs.std(ddof=1), Gs.mean()), "day-block boot SE (5 draws) %s" % np.round(ses, 3), flush=True)
