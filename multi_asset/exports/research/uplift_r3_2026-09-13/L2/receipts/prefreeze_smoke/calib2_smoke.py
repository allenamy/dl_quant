# SMOKE calibration 2 (SYNTHETIC targets only): B all anchors — block bootstrap SE with 1/2/3-day blocks vs true SD over draws;
# circular day-shift null SD (common shift of the target time axis by whole days) vs true SD; A for reference.
import sys, numpy as np
sys.path.insert(0, "/workspace/uplift_r3_2026-09-13/L2_smoke2/devices")
import l2_b_common as B
S = "/workspace/uplift_r3_2026-09-13/L2_smoke2"
Z = np.load(S + "/out/L2_B_data_s42.npz"); O = np.load(S + "/out/L2_B_oos_s42.npz")
I = Z["i"].astype(np.int64); Nn = Z["n"].astype(np.int64); YR = Z["year"].astype(np.int64); DAYv = Z["day"].astype(np.int64)
meta = np.load("/workspace/review_scratch/refute_C6_2/altrun/meta_newprod_v4.npz")["y4"]; fin = np.isfinite(meta)
g0 = np.random.default_rng([777, 0]); Y0 = np.where(fin, g0.normal(0, 0.02, fin.shape), np.nan)
def targ(Y, T, kk, nn):
    if T == "A":
        return Y[kk, nn]
    ok = kk + 5 < Y.shape[0]; out = np.full(kk.size, np.nan)
    out[ok] = np.prod(np.stack([1.0 + Y[kk[ok] + q, nn[ok]] for q in range(6)], 1), 1) - 1.0
    return out
for T in ("A", "B"):
    ok0 = (YR >= 2023) & np.isfinite(Z["r" + T])
    idx, a, sizes, _ = B.anchor_index(I, ok0); big = sizes[a] >= 10
    idx, a, sizes, _ = B.anchor_index(I, np.isin(np.arange(I.size), idx[big]))
    col = Nn[idx]; st = np.concatenate([[0], np.cumsum(sizes)[:-1]]); day_a = DAYv[idx][st]
    p = O["p_R_%s_FULL" % T][idx]; top, bot, m = B.decile_sets(p, a, sizes, col)
    kk = I[idx] + 138; nn = Nn[idx]
    s0 = -1e4 * targ(Y0, T, kk, nn); D0, _ = B.anchor_stats(s0, a, sizes, top, bot)
    for L in (1, 2, 3):
        blk = (day_a - day_a.min()) // L; ub, binv = np.unique(blk, return_inverse=True); Cm = B.draw_counts(ub.size)
        ci = B.boot_ci(Cm, np.bincount(binv, D0, ub.size), np.bincount(binv, None, ub.size))
        print(T, "block %dd boot SE %.3f" % (L, (ci[1] - ci[0]) / 3.92), flush=True)
    # circular day-shift null: target at anchor rec-row i taken from rec-row i + 6*Ld (wrap within test rows window)
    rows_i = I[idx]; lo_i = rows_i.min(); hi_i = rows_i.max(); span = hi_i - lo_i + 1
    Gn = []
    rng = np.random.default_rng([20260913, 8]); shifts = rng.choice(np.arange(30, span // 6 - 30), size=100, replace=False)
    for sh in shifts:
        ii2 = lo_i + ((rows_i - lo_i + 6 * sh) % span)
        s2 = -1e4 * targ(Y0, T, ii2 + 138, nn)
        okr = np.isfinite(s2)
        # recompute per-anchor stats over rows with finite shifted target, keeping the original top flags
        aa = a[okr]; ss = s2[okr]; tt = top[okr]
        na = sizes.size; cnt = np.bincount(aa, None, na); ct = np.bincount(aa, tt.astype(float), na)
        good = (cnt >= 10) & (ct > 0)
        Dn = np.bincount(aa, ss * tt, na)[good] / ct[good] - np.bincount(aa, ss, na)[good] / cnt[good]
        Gn.append(Dn.mean())
    print(T, "circular day-shift null SD %.3f mean %.3f (100 shifts)" % (np.std(Gn, ddof=1), np.mean(Gn)), flush=True)
